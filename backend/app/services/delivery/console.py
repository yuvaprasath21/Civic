"""
Development-only providers: print the message to the server console
instead of sending it. Lets the whole OTP flow be exercised without any
Gmail/Twilio credentials. Refuses to run outside APP_ENV=development so
a misconfigured production deploy fails loudly rather than silently
"sending" OTPs nowhere.
"""
import logging

from app.core.config import settings
from app.services.delivery.base import DeliveryError, EmailProvider, SMSProvider

logger = logging.getLogger("civic.delivery.console")


def _guard() -> None:
    if settings.APP_ENV != "development":
        raise DeliveryError(
            "Console delivery is only allowed when APP_ENV=development. "
            "Set EMAIL_PROVIDER=smtp and SMS_PROVIDER=twilio for real delivery."
        )


class ConsoleEmailProvider(EmailProvider):
    def send(self, to_email: str, subject: str, body: str) -> None:
        _guard()
        logger.warning("[DEV EMAIL] to=%s subject=%s\n%s", to_email, subject, body)


class ConsoleSMSProvider(SMSProvider):
    def send(self, to_number: str, body: str) -> None:
        _guard()
        logger.warning("[DEV SMS] to=%s\n%s", to_number, body)
