import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


def _validate_e164(value: str) -> str:
    cleaned = re.sub(r"[\s-]", "", value)
    if not E164_PATTERN.match(cleaned):
        raise ValueError("Mobile number must be in international format, e.g. +919876543210")
    return cleaned


class SendOtpRequest(BaseModel):
    """Provide email, mobile, or both. Each gets its own independent OTP."""
    email: Optional[EmailStr] = None
    mobile: Optional[str] = None

    @field_validator("mobile")
    @classmethod
    def mobile_format(cls, v: Optional[str]) -> Optional[str]:
        return _validate_e164(v) if v else v


class VerifyEmailOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=8, pattern=r"^\d+$")


class VerifyMobileOtpRequest(BaseModel):
    mobile: str
    otp: str = Field(min_length=4, max_length=8, pattern=r"^\d+$")

    @field_validator("mobile")
    @classmethod
    def mobile_format(cls, v: str) -> str:
        return _validate_e164(v)


class OtpSentResponse(BaseModel):
    success: bool = True
    message: str
    email_sent: bool = False
    mobile_sent: bool = False
    expires_in_seconds: int
    # NOTE: the OTP itself is deliberately never part of any response.
