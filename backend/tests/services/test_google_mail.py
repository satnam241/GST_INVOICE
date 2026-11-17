import base64
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import ANY, MagicMock, patch

import pytest
from src.core.config import settings
from src.services import google_mail, mail, platform_mail


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def dummy_msg():
    msg = MIMEMultipart()
    msg["To"] = "recipient@example.com"
    msg["Subject"] = "Test Subject"
    msg.attach(MIMEText("Test Body", "plain"))
    return msg


def test_google_mail_detection(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_MAIL_CLIENT_ID", None)
    monkeypatch.setattr(settings, "GOOGLE_MAIL_CLIENT_SECRET", None)
    monkeypatch.setattr(settings, "GOOGLE_MAIL_REFRESH_TOKEN", None)
    monkeypatch.setattr(settings, "GOOGLE_MAIL_USER", None)
    monkeypatch.setattr(settings, "GOOGLE_MAIL_APP_PASSWORD", None)

    assert not google_mail.is_google_mail_configured()
    assert google_mail.get_google_mail_mode() == "none"

    # Test OAuth2 mode
    monkeypatch.setattr(settings, "GOOGLE_MAIL_CLIENT_ID", "dummy-client-id")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_CLIENT_SECRET", "dummy-secret")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_REFRESH_TOKEN", "dummy-refresh-token")

    assert google_mail.is_google_mail_configured()
    assert google_mail.get_google_mail_mode() == "oauth"

    # Test SMTP mode (when OAuth2 is not complete)
    monkeypatch.setattr(settings, "GOOGLE_MAIL_CLIENT_ID", None)
    monkeypatch.setattr(settings, "GOOGLE_MAIL_USER", "user@gmail.com")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_APP_PASSWORD", "abcd efgh ijkl mnop")

    assert google_mail.is_google_mail_configured()
    assert google_mail.get_google_mail_mode() == "smtp"


def test_oauth2_token_refresh(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_MAIL_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_CLIENT_SECRET", "csec")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_REFRESH_TOKEN", "rtok")

    # Reset cache
    google_mail._cached_access_token = None
    google_mail._token_expires_at = 0.0

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": "ya29.mock_token", "expires_in": 3600}

    with patch("httpx.post", return_value=mock_resp) as mock_post:
        token = google_mail._refresh_oauth_access_token()
        assert token == "ya29.mock_token"
        mock_post.assert_called_once()

        # Second call should use cached token
        token2 = google_mail._refresh_oauth_access_token()
        assert token2 == "ya29.mock_token"
        assert mock_post.call_count == 1


def test_oauth2_token_refresh_failure(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_MAIL_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_CLIENT_SECRET", "csec")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_REFRESH_TOKEN", "rtok")

    google_mail._cached_access_token = None
    google_mail._token_expires_at = 0.0

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "invalid_grant"

    with patch("httpx.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="Google OAuth2 token refresh failed"):
            google_mail._refresh_oauth_access_token()


def test_send_via_gmail_api(monkeypatch, dummy_msg):
    monkeypatch.setattr(settings, "GOOGLE_MAIL_CLIENT_ID", "cid")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_CLIENT_SECRET", "csec")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_REFRESH_TOKEN", "rtok")

    with patch.object(google_mail, "_refresh_oauth_access_token", return_value="ya29.test_token"):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "18f92a_mock_id"}

        with patch("httpx.post", return_value=mock_resp) as mock_post:
            google_mail._send_via_gmail_api(dummy_msg, ["recipient@example.com"])
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == google_mail.GMAIL_SEND_URL
            assert "raw" in kwargs["json"]
            assert kwargs["headers"]["Authorization"] == "Bearer ya29.test_token"


def test_send_via_google_smtp_starttls(monkeypatch, dummy_msg):
    monkeypatch.setattr(settings, "GOOGLE_MAIL_USER", "test@gmail.com")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_APP_PASSWORD", "secret_app_pw")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_HOST", "smtp.gmail.com")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_PORT", 587)
    monkeypatch.setattr(settings, "GOOGLE_MAIL_USE_STARTTLS", True)

    with patch("smtplib.SMTP") as mock_smtp:
        server_instance = mock_smtp.return_value.__enter__.return_value
        google_mail._send_via_google_smtp(dummy_msg, ["recipient@example.com"])

        mock_smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=15)
        server_instance.starttls.assert_called_once()
        server_instance.login.assert_called_once_with("test@gmail.com", "secret_app_pw")
        server_instance.send_message.assert_called_once_with(dummy_msg, to_addrs=["recipient@example.com"])


def test_send_via_google_smtp_ssl(monkeypatch, dummy_msg):
    monkeypatch.setattr(settings, "GOOGLE_MAIL_USER", "test@gmail.com")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_APP_PASSWORD", "secret_app_pw")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_HOST", "smtp.gmail.com")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_PORT", 465)
    monkeypatch.setattr(settings, "GOOGLE_MAIL_USE_STARTTLS", False)

    with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        server_instance = mock_smtp_ssl.return_value.__enter__.return_value
        google_mail._send_via_google_smtp(dummy_msg, ["recipient@example.com"])

        mock_smtp_ssl.assert_called_once_with("smtp.gmail.com", 465, timeout=15, context=ANY)
        server_instance.login.assert_called_once_with("test@gmail.com", "secret_app_pw")
        server_instance.send_message.assert_called_once_with(dummy_msg, to_addrs=["recipient@example.com"])


@pytest.mark.anyio
async def test_send_email_uses_google_mail_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_MAIL_USER", "test@gmail.com")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_APP_PASSWORD", "secret_app_pw")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_FROM_NAME", "My Invoicing")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_FROM_EMAIL", None)

    mock_db = MagicMock()
    # Mock company query returning None
    mock_db.query().filter().first.return_value = None

    with patch("src.services.mail.send_google_mail") as mock_send_google:
        await mail.send_email(
            db=mock_db,
            to="buyer@example.com",
            subject="Invoice INV-001",
            html_body="<p>Please pay</p>",
            cc=["accountant@example.com"],
        )

        mock_send_google.assert_called_once()
        msg, recipients = mock_send_google.call_args[0]
        assert recipients == ["buyer@example.com", "accountant@example.com"]
        assert msg["To"] == "buyer@example.com"
        assert msg["Cc"] == "accountant@example.com"
        assert "My Invoicing" in msg["From"]
        assert "test@gmail.com" in msg["From"]

        # Ensure EmailLog committed as sent
        log_entry = mock_db.add.call_args[0][0]
        assert log_entry.status == "sent"
        assert log_entry.to_email == "buyer@example.com"


@pytest.mark.anyio
async def test_send_email_google_mail_failure_handling(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_MAIL_USER", "test@gmail.com")
    monkeypatch.setattr(settings, "GOOGLE_MAIL_APP_PASSWORD", "secret_app_pw")

    mock_db = MagicMock()
    mock_db.query().filter().first.return_value = None

    with patch("src.services.mail.send_google_mail", side_effect=RuntimeError("Auth failed")):
        with pytest.raises(RuntimeError, match="Could not send email via Google Mail"):
            await mail.send_email(
                db=mock_db,
                to="buyer@example.com",
                subject="Test",
                html_body="<p>Test</p>",
            )

        log_entry = mock_db.add.call_args[0][0]
        assert log_entry.status == "failed"
        assert "Auth failed" in log_entry.error_message
