"""
OTP generation, delivery and verification for email and mobile.

Security properties:
  - Codes come from `secrets` (cryptographically secure), never `random`.
  - Only an HMAC-SHA256 of the code (keyed with JWT_SECRET and bound to
    channel + destination) is stored, never the code itself.
  - Codes expire (OTP_EXPIRE_MINUTES), are single-use, and lock after
    OTP_MAX_ATTEMPTS wrong guesses.
  - Resend is throttled per destination (OTP_RESEND_COOLDOWN_SECONDS).
  - Issuing a new code invalidates any earlier unused one.
  - Verification compares in constant time.
  - The code is never returned by the API.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppError, ValidationAppError
from app.models.otp import OtpVerification
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.delivery.base import DeliveryError
from app.services.delivery.factory import get_email_provider, get_sms_provider

CHANNEL_EMAIL = "EMAIL"
CHANNEL_SMS = "SMS"


class OtpCooldownError(AppError):
    status_code = 429
    error_code = "OTP_RESEND_COOLDOWN"


class OtpDeliveryError(AppError):
    status_code = 502
    error_code = "OTP_DELIVERY_FAILED"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def generate_code(length: int) -> str:
    # Uniform over all codes including those with leading zeros.
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def hash_code(channel: str, destination: str, code: str) -> str:
    message = f"{channel}:{destination}:{code}".encode("utf-8")
    return hmac.new(settings.JWT_SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()


class OtpService:
    def __init__(self, db: Session):
        self.db = db
        self.audit = AuditService(db)

    # ------------------------------------------------------------------
    def send(self, *, email: Optional[str], mobile: Optional[str]) -> tuple[bool, bool]:
        if not email and not mobile:
            raise ValidationAppError("Provide an email, a mobile number, or both.", error_code="NO_DESTINATION")

        email_sent = mobile_sent = False
        if email:
            self._issue(CHANNEL_EMAIL, email.lower())
            email_sent = True
        if mobile:
            self._issue(CHANNEL_SMS, mobile)
            mobile_sent = True
        return email_sent, mobile_sent

    def _issue(self, channel: str, destination: str) -> None:
        latest = self._latest(channel, destination)
        if latest is not None:
            elapsed = (_utcnow() - _as_utc(latest.created_at)).total_seconds()
            if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
                wait = int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed) + 1
                raise OtpCooldownError(f"Please wait {wait}s before requesting another code.")

        code = generate_code(settings.OTP_LENGTH)

        # Invalidate any earlier unused codes for this destination.
        self.db.execute(
            update(OtpVerification)
            .where(
                OtpVerification.channel == channel,
                OtpVerification.destination == destination,
                OtpVerification.is_used.is_(False),
            )
            .values(is_used=True)
        )
        record = OtpVerification(
            channel=channel,
            destination=destination,
            code_hash=hash_code(channel, destination, code),
            expires_at=_utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        )
        self.db.add(record)
        self.db.commit()

        text = (
            f"Your CivicPulse verification code is {code}. "
            f"It is valid for {settings.OTP_EXPIRE_MINUTES} minutes. Do not share it with anyone."
        )
        try:
            if channel == CHANNEL_EMAIL:
                get_email_provider().send(destination, "Your CivicPulse verification code", text)
            else:
                get_sms_provider().send(destination, text)
        except DeliveryError as exc:
            # Don't leave a live code behind that the user never received.
            record.is_used = True
            self.db.commit()
            self.audit.record(
                actor_id=None, action="OTP_DELIVERY_FAILED", entity_type="otp", entity_id=record.id,
                details={"channel": channel, "reason": str(exc)},
            )
            raise OtpDeliveryError(
                f"Could not send the {'email' if channel == CHANNEL_EMAIL else 'SMS'} code. "
                "Please check the address/number and try again.",
            ) from exc

        self.audit.record(
            actor_id=None, action="OTP_SENT", entity_type="otp", entity_id=record.id, details={"channel": channel}
        )

    # ------------------------------------------------------------------
    def verify(self, channel: str, destination: str, code: str) -> None:
        record = self._latest(channel, destination, only_active=True)

        if record is None or _as_utc(record.expires_at) < _utcnow():
            raise ValidationAppError("This code is invalid or has expired. Request a new one.", error_code="OTP_INVALID_OR_EXPIRED")

        if record.attempts >= settings.OTP_MAX_ATTEMPTS:
            record.is_used = True
            self.db.commit()
            raise ValidationAppError(
                "Too many incorrect attempts. Request a new code.", error_code="OTP_TOO_MANY_ATTEMPTS"
            )

        expected = record.code_hash
        provided = hash_code(channel, destination, code)
        if not hmac.compare_digest(expected, provided):
            record.attempts += 1
            self.db.commit()
            remaining = settings.OTP_MAX_ATTEMPTS - record.attempts
            raise ValidationAppError(
                f"Incorrect code. {max(remaining, 0)} attempt(s) left.", error_code="OTP_INCORRECT"
            )

        record.is_used = True
        record.verified_at = _utcnow()
        self.db.commit()

        self._mark_user_verified(channel, destination)
        self.audit.record(
            actor_id=None, action="OTP_VERIFIED", entity_type="otp", entity_id=record.id, details={"channel": channel}
        )

    # ------------------------------------------------------------------
    def _mark_user_verified(self, channel: str, destination: str) -> None:
        if channel == CHANNEL_EMAIL:
            user = self.db.execute(select(User).where(User.email == destination, User.is_deleted.is_(False))).scalar_one_or_none()
            if user:
                user.is_email_verified = True
        else:
            user = self.db.execute(
                select(User).where(User.phone_number == destination, User.is_deleted.is_(False))
            ).scalar_one_or_none()
            if user:
                user.is_phone_verified = True
        self.db.commit()

    def _latest(self, channel: str, destination: str, only_active: bool = False) -> Optional[OtpVerification]:
        stmt = select(OtpVerification).where(
            OtpVerification.channel == channel, OtpVerification.destination == destination
        )
        if only_active:
            stmt = stmt.where(OtpVerification.is_used.is_(False))
        stmt = stmt.order_by(OtpVerification.id.desc()).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()
