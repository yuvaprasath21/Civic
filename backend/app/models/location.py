from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import IDMixin, TimestampMixin


class Location(Base, IDMixin, TimestampMixin):
    __tablename__ = "locations"

    latitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    address_text: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    landmark: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ward: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)


class RiskZone(Base, IDMixin, TimestampMixin):
    __tablename__ = "risk_zones"

    zone_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    radius_meters: Mapped[float] = mapped_column(Float, default=200.0, nullable=False)
    risk_weight: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
