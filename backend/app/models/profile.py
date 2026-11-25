from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IDMixin, TimestampMixin


class CitizenProfile(Base, IDMixin, TimestampMixin):
    __tablename__ = "citizen_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    address_line: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    default_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    default_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_reports_submitted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reputation_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    user: Mapped["User"] = relationship(back_populates="citizen_profile")


class StaffProfile(Base, IDMixin, TimestampMixin):
    __tablename__ = "staff_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    employee_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_available: Mapped[bool] = mapped_column(default=True, nullable=False)
    current_workload: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_resolved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_resolution_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship(back_populates="staff_profile")
    department: Mapped[Optional["Department"]] = relationship(back_populates="staff_members")
