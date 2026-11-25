from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import ImageType
from app.models.mixins import IDMixin, TimestampMixin


class IssueImage(Base, IDMixin, TimestampMixin):
    __tablename__ = "issue_images"

    issue_id: Mapped[int] = mapped_column(ForeignKey("civic_issues.id", ondelete="CASCADE"), nullable=False)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    image_type: Mapped[ImageType] = mapped_column(SAEnum(ImageType), default=ImageType.REPORT, nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    perceptual_hash: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # dHash, for duplicate detection

    issue: Mapped["CivicIssue"] = relationship(back_populates="images")
