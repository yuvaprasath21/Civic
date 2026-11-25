import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings
from app.services.delivery.base import DeliveryError, EmailProvider


class SMTPEmailProvider(EmailProvider):
    """
    Works with Gmail (smtp.gmail.com:587 + an App Password) or any SMTP
    server. Credentials come from environment variables only.
    """

    def send(self, to_email: str, subject: str, body: str) -> None:
        if not (settings.SMTP_USERNAME and settings.SMTP_PASSWORD and settings.SMTP_FROM):
            raise DeliveryError("SMTP is not configured: set SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM.")

        message = EmailMessage()
        message["From"] = settings.SMTP_FROM
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            raise DeliveryError(f"Email delivery failed: {exc.__class__.__name__}") from exc
