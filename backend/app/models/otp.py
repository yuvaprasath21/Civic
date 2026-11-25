from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import IDMixin, TimestampMixin


class OtpVerification(Base, IDMixin, TimestampMixin):
    """
    One row per issued OTP. The code itself is never stored — only an
    HMAC of it — so a database leak doesn't expose usable codes.
    A new send for the same (channel, destination) invalidates older rows.
    """
    __tablename__ = "otp_verifications"

    channel: Mapped[str] = mapped_column(String(10), nullable=False)  # "EMAIL" | "SMS"
    destination: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
