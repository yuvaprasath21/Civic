from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import AssignmentStatus, IssueStatus
from app.models.mixins import IDMixin, TimestampMixin


class IssueAssignment(Base, IDMixin, TimestampMixin):
    __tablename__ = "issue_assignments"

    issue_id: Mapped[int] = mapped_column(ForeignKey("civic_issues.id", ondelete="CASCADE"), nullable=False)
    staff_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assigned_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[AssignmentStatus] = mapped_column(
        SAEnum(AssignmentStatus), default=AssignmentStatus.PENDING, nullable=False
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    staff_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    issue: Mapped["CivicIssue"] = relationship(back_populates="assignments")
    staff: Mapped["User"] = relationship(foreign_keys=[staff_id])


class IssueStatusHistory(Base, IDMixin, TimestampMixin):
    __tablename__ = "issue_status_history"

    issue_id: Mapped[int] = mapped_column(ForeignKey("civic_issues.id", ondelete="CASCADE"), nullable=False)
    changed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    from_status: Mapped[Optional[IssueStatus]] = mapped_column(SAEnum(IssueStatus), nullable=True)
    to_status: Mapped[IssueStatus] = mapped_column(SAEnum(IssueStatus), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    issue: Mapped["CivicIssue"] = relationship(back_populates="status_history")
    changed_by: Mapped[Optional["User"]] = relationship(foreign_keys=[changed_by_id])


class IssueComment(Base, IDMixin, TimestampMixin):
    __tablename__ = "issue_comments"

    issue_id: Mapped[int] = mapped_column(ForeignKey("civic_issues.id", ondelete="CASCADE"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    issue: Mapped["CivicIssue"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(foreign_keys=[author_id])


class IssueDuplicate(Base, IDMixin, TimestampMixin):
    __tablename__ = "issue_duplicates"

    master_issue_id: Mapped[int] = mapped_column(ForeignKey("civic_issues.id", ondelete="CASCADE"), nullable=False)
    duplicate_issue_id: Mapped[int] = mapped_column(
        ForeignKey("civic_issues.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    distance_meters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_delta_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    image_similarity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    matched_automatically: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    merged_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class IssueFeedback(Base, IDMixin, TimestampMixin):
    __tablename__ = "issue_feedback"

    issue_id: Mapped[int] = mapped_column(
        ForeignKey("civic_issues.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    citizen_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    issue: Mapped["CivicIssue"] = relationship(back_populates="feedback")
