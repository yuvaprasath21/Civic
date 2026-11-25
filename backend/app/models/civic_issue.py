from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import IssueCategory, IssueStatus, PriorityLevel, SeverityLevel
from app.models.mixins import IDMixin, TimestampMixin, UUIDMixin, SoftDeleteMixin


class CivicIssue(Base, IDMixin, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "civic_issues"

    reference_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)

    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    category: Mapped[IssueCategory] = mapped_column(SAEnum(IssueCategory), nullable=False, index=True)
    severity: Mapped[SeverityLevel] = mapped_column(SAEnum(SeverityLevel), nullable=False, index=True)
    status: Mapped[IssueStatus] = mapped_column(
        SAEnum(IssueStatus), default=IssueStatus.REPORTED, nullable=False, index=True
    )

    priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    priority_level: Mapped[PriorityLevel] = mapped_column(
        SAEnum(PriorityLevel), default=PriorityLevel.LOW, nullable=False, index=True
    )

    is_ai_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_citizen_edited_category: Mapped[bool] = mapped_column(default=False, nullable=False)

    master_issue_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("civic_issues.id", ondelete="SET NULL"), nullable=True
    )
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_sla_breached: Mapped[bool] = mapped_column(default=False, nullable=False)

    reporter: Mapped["User"] = relationship(foreign_keys=[reporter_id])
    location: Mapped["Location"] = relationship()
    department: Mapped[Optional["Department"]] = relationship()

    master_issue: Mapped[Optional["CivicIssue"]] = relationship(remote_side="CivicIssue.id")

    images: Mapped[List["IssueImage"]] = relationship(back_populates="issue", cascade="all, delete-orphan")
    ai_predictions: Mapped[List["AIPrediction"]] = relationship(back_populates="issue", cascade="all, delete-orphan")
    assignments: Mapped[List["IssueAssignment"]] = relationship(back_populates="issue", cascade="all, delete-orphan")
    status_history: Mapped[List["IssueStatusHistory"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan", order_by="IssueStatusHistory.created_at"
    )
    comments: Mapped[List["IssueComment"]] = relationship(back_populates="issue", cascade="all, delete-orphan")
    feedback: Mapped[Optional["IssueFeedback"]] = relationship(
        back_populates="issue", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CivicIssue {self.reference_code} status={self.status}>"
