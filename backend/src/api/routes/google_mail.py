"""Google Mail OAuth authorization and management endpoints.

Allows connecting Google Mail using only GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
via a 1-click browser flow, eliminating the need to manually supply a refresh token.
"""

import logging
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from src.core.config import settings
from src.services.google_mail import (
    clear_stored_tokens,
    get_google_mail_mode,
    get_sender_email,
    get_sender_name,
    has_stored_token,
    is_google_mail_configured,
    save_stored_tokens,
    send_test_google_mail,
)

logger = logging.getLogger(__name__)

router = APIRouter()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def _callback_url(request: Request) -> str:
    """Build the callback redirect URL."""
    base = settings.PUBLIC_API_BASE_URL.rstrip("/") if settings.PUBLIC_API_BASE_URL else str(request.base_url).rstrip("/")
    if base.endswith("/api"):
        return f"{base}/google-mail/callback"
    return f"{base}/api/google-mail/callback"


@router.get("/authorize")
def authorize_google_mail(request: Request):
    """Start the Google OAuth consent flow to connect Gmail for outgoing invoices/emails."""
    client_id = settings.effective_google_client_id
    if not client_id:
        raise HTTPException(
            status_code=400,
            detail="GOOGLE_CLIENT_ID is not configured in .env. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET first.",
        )

    redirect_uri = _callback_url(request)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://mail.google.com/ email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/callback")
def google_mail_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
):
    """Receive the authorization code from Google, exchange for tokens, and save them."""
    if error:
        logger.warning("Google Mail authorization rejected: %s", error)
        return HTMLResponse(
            content=f"""
            <html><body style="font-family: sans-serif; padding: 40px; text-align: center;">
                <h2 style="color: #ef4444;">❌ Google Authorization Failed</h2>
                <p>Google returned an error: <strong>{error}</strong></p>
                <p><a href="/api/google-mail/authorize">Try Again</a></p>
            </body></html>
            """,
            status_code=400,
        )

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code from Google")

    client_id = settings.effective_google_client_id
    client_secret = settings.effective_google_client_secret
    redirect_uri = _callback_url(request)

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }

    try:
        token_resp = httpx.post(GOOGLE_TOKEN_URL, data=payload, timeout=20.0)
    except Exception as exc:
        logger.exception("Failed to connect to Google OAuth token endpoint")
        raise HTTPException(status_code=502, detail=f"Failed to connect to Google: {exc}")

    if token_resp.status_code != 200:
        logger.error("Token exchange failed (%d): %s", token_resp.status_code, token_resp.text)
        return HTMLResponse(
            content=f"""
            <html><body style="font-family: sans-serif; padding: 40px; text-align: center;">
                <h2 style="color: #ef4444;">❌ Token Exchange Failed</h2>
                <p>Google response: <code>{token_resp.text}</code></p>
                <p><a href="/api/google-mail/authorize">Try Again</a></p>
            </body></html>
            """,
            status_code=400,
        )

    data = token_resp.json()
    access_token = data.get("access_token")

    # Fetch user's email address
    user_email = ""
    if access_token:
        try:
            info_resp = httpx.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            if info_resp.status_code == 200:
                user_email = info_resp.json().get("email", "")
                data["email"] = user_email
        except Exception:
            logger.warning("Could not fetch userinfo for Google Mail account", exc_info=True)

    save_stored_tokens(data)
    logger.info("Successfully connected Google Mail for account %s", user_email)

    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Google Mail Connected</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    background: #f8fafc;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                    margin: 0;
                }}
                .card {{
                    background: white;
                    border-radius: 12px;
                    padding: 36px 40px;
                    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
                    max-width: 460px;
                    text-align: center;
                }}
                .badge {{
                    display: inline-block;
                    background: #ecfdf5;
                    color: #059669;
                    font-weight: 600;
                    padding: 4px 12px;
                    border-radius: 9999px;
                    font-size: 13px;
                    margin-bottom: 12px;
                }}
                h1 {{
                    font-size: 22px;
                    color: #0f172a;
                    margin: 0 0 10px;
                }}
                p {{
                    color: #475569;
                    font-size: 14px;
                    line-height: 1.6;
                    margin: 0 0 20px;
                }}
                .email-box {{
                    background: #f1f5f9;
                    padding: 10px 16px;
                    border-radius: 8px;
                    font-weight: 600;
                    color: #1e293b;
                    font-size: 15px;
                    margin-bottom: 24px;
                    word-break: break-all;
                }}
                .btn {{
                    display: inline-block;
                    background: #2563eb;
                    color: white;
                    text-decoration: none;
                    font-weight: 500;
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <span class="badge">Connected</span>
                <h1>Google Mail Connected!</h1>
                <p>Your Google account has been successfully connected to Simple Invoicing:</p>
                <div class="email-box">{user_email or 'Google Account'}</div>
                <p>All outgoing invoices, statements, and payment reminders will now be sent from this email address. You may safely close this window.</p>
                <a href="/" class="btn">Go to Dashboard</a>
            </div>
        </body>
        </html>
        """
    )


@router.get("/status")
def google_mail_status():
    """Get the connection status of Google Mail."""
    has_creds = bool(settings.effective_google_client_id and settings.effective_google_client_secret)
    is_ready = is_google_mail_configured()
    mode = get_google_mail_mode()
    email = get_sender_email()

    return {
        "configured": is_ready,
        "mode": mode,
        "sender_email": email,
        "from_name": get_sender_name(),
        "has_client_credentials": has_creds,
        "has_stored_token": has_stored_token(),
        "authorize_url": "/api/google-mail/authorize" if has_creds else None,
    }


class SendTestRequest(BaseModel):
    to: str


@router.post("/test")
def send_test_email(payload: SendTestRequest):
    """Send a test email using Google Mail."""
    if not is_google_mail_configured():
        raise HTTPException(
            status_code=400,
            detail="Google Mail is not configured. Please open /api/google-mail/authorize to connect your Google account.",
        )
    try:
        send_test_google_mail(payload.to.strip())
        return {"detail": f"Test email sent successfully to {payload.to.strip()} via Google Mail."}
    except Exception as exc:
        logger.exception("Failed to send test email via Google Mail")
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/disconnect")
def disconnect_google_mail():
    """Clear any saved Google Mail OAuth tokens."""
    clear_stored_tokens()
    return {"detail": "Google Mail disconnected successfully."}
