from app.core.config import settings
from app.services.delivery.base import EmailProvider, SMSProvider
from app.services.delivery.console import ConsoleEmailProvider, ConsoleSMSProvider
from app.services.delivery.smtp_email import SMTPEmailProvider
from app.services.delivery.twilio_sms import TwilioSMSProvider


def get_email_provider() -> EmailProvider:
    if settings.EMAIL_PROVIDER == "smtp":
        return SMTPEmailProvider()
    if settings.EMAIL_PROVIDER == "console":
        return ConsoleEmailProvider()
    raise ValueError(f"Unknown EMAIL_PROVIDER '{settings.EMAIL_PROVIDER}'. Expected 'smtp' or 'console'.")


def get_sms_provider() -> SMSProvider:
    if settings.SMS_PROVIDER == "twilio":
        return TwilioSMSProvider()
    if settings.SMS_PROVIDER == "console":
        return ConsoleSMSProvider()
    raise ValueError(f"Unknown SMS_PROVIDER '{settings.SMS_PROVIDER}'. Expected 'twilio' or 'console'.")
