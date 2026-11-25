import httpx

from app.core.config import settings
from app.services.delivery.base import DeliveryError, SMSProvider


class TwilioSMSProvider(SMSProvider):
    """
    Calls Twilio's REST API directly with httpx (no extra SDK needed).
    `to_number` must be E.164, e.g. +919876543210. Trial accounts can
    only text numbers verified in the Twilio console.
    """

    def send(self, to_number: str, body: str) -> None:
        if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_PHONE_NUMBER):
            raise DeliveryError(
                "Twilio is not configured: set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER."
            )

        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
        try:
            response = httpx.post(
                url,
                data={"To": to_number, "From": settings.TWILIO_PHONE_NUMBER, "Body": body},
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                timeout=15,
            )
        except httpx.HTTPError as exc:
            raise DeliveryError("SMS delivery failed: could not reach Twilio.") from exc

        if response.status_code >= 400:
            # Twilio's error JSON includes a human-readable message but
            # never our credentials, so it's safe to surface its code.
            try:
                code = response.json().get("code")
            except ValueError:
                code = None
            raise DeliveryError(f"SMS delivery failed (Twilio status {response.status_code}, code {code}).")
