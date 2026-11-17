"""Google Mail (Gmail API & Google SMTP) email sending service.

Supports two Google authentication/sending methods:
1. Google Cloud Console - Gmail API (OAuth 2.0):
   Requires: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET.
   The user can connect with a single click at /api/google-mail/authorize without
   needing to manually generate or paste a refresh token.
2. Google Mail SMTP:
   Requires: GOOGLE_MAIL_USER, GOOGLE_MAIL_APP_PASSWORD.
   Connects to smtp.gmail.com (port 587 STARTTLS or 465 SSL) using an App Password.
"""

import base64
import json
import logging
import smtplib
import ssl
import time
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

import httpx
from src.core.config import settings

logger = logging.getLogger(__name__)

# Token file for storing OAuth credentials locally
TOKEN_FILE = Path(__file__).resolve().parent.parent.parent / "google_mail_token.json"

# Token caching for Google Cloud OAuth2
_cached_access_token: str | None = None
_token_expires_at: float = 0.0

GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
GMAIL_UPLOAD_URL = "https://gmail.googleapis.com/upload/gmail/v1/users/me/messages/send?uploadType=media"


def _read_token_file() -> dict:
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.warning("Could not read %s", TOKEN_FILE, exc_info=True)
    return {}


def has_stored_token() -> bool:
    """Check if a refresh token or valid access token is available."""
    if settings.GOOGLE_MAIL_REFRESH_TOKEN:
        return True
    data = _read_token_file()
    return bool(data.get("refresh_token") or data.get("access_token"))


def get_stored_refresh_token() -> str | None:
    """Return the refresh token from settings or local token file."""
    if settings.GOOGLE_MAIL_REFRESH_TOKEN:
        return settings.GOOGLE_MAIL_REFRESH_TOKEN
    data = _read_token_file()
    return data.get("refresh_token")


def get_stored_email() -> str | None:
    """Return the authenticated user email stored in local token file."""
    data = _read_token_file()
    return data.get("email")


def save_stored_tokens(token_data: dict) -> None:
    """Persist OAuth tokens and user info to google_mail_token.json."""
    global _cached_access_token, _token_expires_at
    try:
        existing = _read_token_file()
        merged = {**existing, **token_data}
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)

        access_token = merged.get("access_token")
        if access_token:
            _cached_access_token = access_token
            expires_in = merged.get("expires_in", 3600)
            _token_expires_at = time.time() + float(expires_in)
    except Exception:
        logger.exception("Failed to save tokens to %s", TOKEN_FILE)


def clear_stored_tokens() -> None:
    """Delete stored tokens to disconnect Google Mail."""
    global _cached_access_token, _token_expires_at
    _cached_access_token = None
    _token_expires_at = 0.0
    if TOKEN_FILE.exists():
        try:
            TOKEN_FILE.unlink()
        except Exception:
            logger.exception("Failed to delete %s", TOKEN_FILE)


def is_google_mail_configured() -> bool:
    """Check if either Google OAuth2 or Google SMTP credentials are configured."""
    return settings.google_mail_configured


def get_google_mail_mode() -> str:
    """Return the active Google Mail sending mode: 'oauth', 'smtp', or 'none'."""
    if settings.google_mail_oauth_configured:
        return "oauth"
    if settings.google_mail_smtp_configured:
        return "smtp"
    return "none"


def get_sender_email() -> str:
    """Return the sender email address to use for Google Mail."""
    return (
        settings.GOOGLE_MAIL_FROM_EMAIL
        or settings.GOOGLE_MAIL_USER
        or get_stored_email()
        or ""
    )


def get_sender_name() -> str:
    """Return the default sender name for Google Mail."""
    return settings.GOOGLE_MAIL_FROM_NAME or "Simple Invoicing"


def _refresh_oauth_access_token() -> str:
    """Refresh Google OAuth2 access token using client credentials and refresh token."""
    global _cached_access_token, _token_expires_at

    now = time.time()
    # Return cached token if valid for at least another 60 seconds
    if _cached_access_token and now < (_token_expires_at - 60):
        return _cached_access_token

    client_id = settings.effective_google_client_id
    client_secret = settings.effective_google_client_secret
    refresh_token = get_stored_refresh_token()

    if not client_id or not client_secret:
        raise RuntimeError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are not set in .env")

    if not refresh_token:
        raise RuntimeError(
            "Google Mail is not authorized yet. Please open http://localhost:8000/api/google-mail/authorize "
            "in your browser to connect your Google account with 1 click."
        )

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    try:
        response = httpx.post(GMAIL_TOKEN_URL, data=payload, timeout=15.0)
    except Exception as exc:
        logger.exception("Failed to connect to Google OAuth2 token endpoint")
        raise RuntimeError(f"Could not connect to Google OAuth2: {exc}") from exc

    if response.status_code != 200:
        error_detail = response.text
        logger.error("Google OAuth token refresh failed (%d): %s", response.status_code, error_detail)
        raise RuntimeError(f"Google OAuth2 token refresh failed: {error_detail}")

    data = response.json()
    access_token = data.get("access_token")
    if not access_token:
        raise RuntimeError("Google OAuth2 response did not contain access_token")

    expires_in = data.get("expires_in", 3600)
    _cached_access_token = access_token
    _token_expires_at = now + float(expires_in)

    # Persist updated access_token
    save_stored_tokens({"access_token": access_token, "expires_in": expires_in})

    return _cached_access_token


def _send_via_gmail_api(msg: Message, recipients: list[str]) -> None:
    """Send an email using the Gmail REST API (OAuth 2.0)."""
    access_token = _refresh_oauth_access_token()
    raw_bytes = msg.as_bytes()

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    # For messages under 4MB, standard JSON body with base64url 'raw' is standard
    if len(raw_bytes) < 4 * 1024 * 1024:
        headers["Content-Type"] = "application/json"
        encoded_raw = base64.urlsafe_b64encode(raw_bytes).decode("ascii")
        body = {"raw": encoded_raw}

        try:
            response = httpx.post(GMAIL_SEND_URL, json=body, headers=headers, timeout=20.0)
        except Exception as exc:
            logger.exception("Failed to send message via Gmail API")
            raise RuntimeError(f"Failed to connect to Gmail API: {exc}") from exc
    else:
        # For larger payloads (attachments up to ~35MB), use media upload endpoint
        headers["Content-Type"] = "message/rfc822"
        try:
            response = httpx.post(GMAIL_UPLOAD_URL, content=raw_bytes, headers=headers, timeout=30.0)
        except Exception as exc:
            logger.exception("Failed to upload message via Gmail API media endpoint")
            raise RuntimeError(f"Failed to upload message to Gmail API: {exc}") from exc

    if response.status_code not in (200, 201):
        error_detail = response.text
        logger.error("Gmail API rejected message (%d): %s", response.status_code, error_detail)
        raise RuntimeError(f"Gmail API error: {error_detail}")

    result = response.json()
    logger.info("Email successfully sent via Gmail API, message ID: %s", result.get("id"))


def _send_via_google_smtp(msg: Message, recipients: list[str]) -> None:
    """Send an email using Google SMTP (smtp.gmail.com)."""
    host = settings.GOOGLE_MAIL_HOST or "smtp.gmail.com"
    port = settings.GOOGLE_MAIL_PORT or 587
    user = settings.GOOGLE_MAIL_USER
    password = settings.GOOGLE_MAIL_APP_PASSWORD or ""
    use_starttls = settings.GOOGLE_MAIL_USE_STARTTLS

    if not user or not password:
        raise RuntimeError("Google Mail SMTP requires GOOGLE_MAIL_USER and GOOGLE_MAIL_APP_PASSWORD")

    try:
        context = ssl.create_default_context()
        if port == 465 or not use_starttls:
            with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as server:
                server.login(user, password)
                server.send_message(msg, to_addrs=recipients)
        else:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.starttls(context=context)
                server.login(user, password)
                server.send_message(msg, to_addrs=recipients)
        logger.info("Email successfully sent via Google SMTP (%s:%d)", host, port)
    except Exception as exc:
        logger.exception("Failed to send email via Google SMTP %s", host)
        raise RuntimeError(f"Google SMTP delivery failed: {exc}") from exc


def send_google_mail(msg: Message, recipients: list[str]) -> None:
    """Deliver an email message using whichever Google Mail mode is configured."""
    mode = get_google_mail_mode()
    if mode == "oauth":
        _send_via_gmail_api(msg, recipients)
    elif mode == "smtp":
        _send_via_google_smtp(msg, recipients)
    else:
        raise RuntimeError(
            "Google Mail is not configured. Please set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET "
            "or GOOGLE_MAIL_USER / GOOGLE_MAIL_APP_PASSWORD in your .env file."
        )


def send_test_google_mail(to_email: str) -> None:
    """Send a test email to verify Google Mail configuration."""
    from_email = get_sender_email()
    from_name = get_sender_name()

    msg = MIMEMultipart()
    msg["Subject"] = "Test Email from Simple Invoicing (Google Mail)"
    msg["From"] = formataddr((from_name, from_email))
    msg["To"] = to_email

    body = (
        f"Hello,\n\n"
        f"This is a test email sent from Simple Invoicing using your Google Mail configuration.\n"
        f"Mode: {get_google_mail_mode().upper()}\n"
        f"Sender: {from_email}\n\n"
        f"Your Google Mail integration is working properly!\n"
    )
    msg.attach(MIMEText(body, "plain"))

    send_google_mail(msg, [to_email])
