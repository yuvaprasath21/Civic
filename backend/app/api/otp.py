"""
OTP endpoints (all under /api/auth):
  POST /auth/send-otp          — send OTPs to an email, a mobile, or both
  POST /auth/resend-otp        — same, subject to the resend cooldown
  POST /auth/verify-email-otp  — verify the emailed code
  POST /auth/verify-mobile-otp — verify the SMS code
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.schemas.common import MessageResponse
from app.schemas.otp import OtpSentResponse, SendOtpRequest, VerifyEmailOtpRequest, VerifyMobileOtpRequest
from app.services.otp_service import CHANNEL_EMAIL, CHANNEL_SMS, OtpService

router = APIRouter(prefix="/auth", tags=["otp"])


def _send(payload: SendOtpRequest, db: Session) -> OtpSentResponse:
    email_sent, mobile_sent = OtpService(db).send(email=payload.email, mobile=payload.mobile)
    return OtpSentResponse(
        message="OTP sent successfully",
        email_sent=email_sent,
        mobile_sent=mobile_sent,
        expires_in_seconds=settings.OTP_EXPIRE_MINUTES * 60,
    )


@router.post("/send-otp", response_model=OtpSentResponse)
@limiter.limit("5/minute")
def send_otp(request: Request, payload: SendOtpRequest, db: Session = Depends(get_db)):
    return _send(payload, db)


@router.post("/resend-otp", response_model=OtpSentResponse)
@limiter.limit("5/minute")
def resend_otp(request: Request, payload: SendOtpRequest, db: Session = Depends(get_db)):
    return _send(payload, db)


@router.post("/verify-email-otp", response_model=MessageResponse)
@limiter.limit("10/minute")
def verify_email_otp(request: Request, payload: VerifyEmailOtpRequest, db: Session = Depends(get_db)):
    OtpService(db).verify(CHANNEL_EMAIL, payload.email.lower(), payload.otp)
    return MessageResponse(message="Email verified successfully.")


@router.post("/verify-mobile-otp", response_model=MessageResponse)
@limiter.limit("10/minute")
def verify_mobile_otp(request: Request, payload: VerifyMobileOtpRequest, db: Session = Depends(get_db)):
    OtpService(db).verify(CHANNEL_SMS, payload.mobile, payload.otp)
    return MessageResponse(message="Mobile number verified successfully.")
