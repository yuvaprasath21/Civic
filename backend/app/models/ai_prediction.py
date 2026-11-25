from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Float, ForeignKey, JSON, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import IssueCategory, SeverityLevel
from app.models.mixins import IDMixin, TimestampMixin


class AIPrediction(Base, IDMixin, TimestampMixin):
    __tablename__ = "ai_predictions"

    issue_id: Mapped[int] = mapped_column(ForeignKey("civic_issues.id", ondelete="CASCADE"), nullable=False)
    issue_image_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("issue_images.id", ondelete="SET NULL"), nullable=True
    )

    predicted_category: Mapped[IssueCategory] = mapped_column(SAEnum(IssueCategory), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_severity: Mapped[SeverityLevel] = mapped_column(SAEnum(SeverityLevel), nullable=False)
    detected_objects: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    raw_output: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    inference_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    issue: Mapped["CivicIssue"] = relationship(back_populates="ai_predictions")
