from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import IssueCategory, IssueStatus, SeverityLevel
from app.models.civic_issue import CivicIssue
from app.models.issue_workflow import IssueAssignment
from app.models.location import Location
from app.utils.geo import bounding_box_deltas, haversine_km


class IssueRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, issue: CivicIssue) -> CivicIssue:
        self.db.add(issue)
        self.db.flush()
        return issue

    def commit_refresh(self, issue: CivicIssue) -> CivicIssue:
        self.db.commit()
        self.db.refresh(issue)
        return issue

    def get_by_uuid(self, issue_uuid: str) -> Optional[CivicIssue]:
        stmt = (
            select(CivicIssue)
            .where(CivicIssue.uuid == issue_uuid, CivicIssue.is_deleted.is_(False))
            .options(
                joinedload(CivicIssue.location),
                joinedload(CivicIssue.department),
                joinedload(CivicIssue.reporter),
                joinedload(CivicIssue.images),
                joinedload(CivicIssue.status_history),
                joinedload(CivicIssue.comments),
                joinedload(CivicIssue.feedback),
                joinedload(CivicIssue.ai_predictions),
                joinedload(CivicIssue.master_issue),
                joinedload(CivicIssue.assignments).joinedload(IssueAssignment.staff),
            )
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def list_filtered(
        self,
        *,
        reporter_id: Optional[int] = None,
        category: Optional[IssueCategory] = None,
        status: Optional[IssueStatus] = None,
        severity: Optional[SeverityLevel] = None,
        city: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[CivicIssue], int]:
        stmt = (
            select(CivicIssue)
            .join(Location, CivicIssue.location_id == Location.id)
            .where(CivicIssue.is_deleted.is_(False))
            .options(joinedload(CivicIssue.location), joinedload(CivicIssue.department), joinedload(CivicIssue.images))
        )

        if reporter_id is not None:
            stmt = stmt.where(CivicIssue.reporter_id == reporter_id)
        if category is not None:
            stmt = stmt.where(CivicIssue.category == category)
        if status is not None:
            stmt = stmt.where(CivicIssue.status == status)
        if severity is not None:
            stmt = stmt.where(CivicIssue.severity == severity)
        if city:
            stmt = stmt.where(Location.city.ilike(f"%{city}%"))
        if search:
            stmt = stmt.where(CivicIssue.title.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(CivicIssue.id).order_by(None).subquery())
        total = self.db.execute(count_stmt).scalar_one()

        stmt = stmt.order_by(CivicIssue.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items = self.db.execute(stmt).unique().scalars().all()

        return list(items), total

    def list_near(
        self, *, latitude: float, longitude: float, radius_km: float, page: int = 1, page_size: int = 20
    ) -> Tuple[List[CivicIssue], int]:
        lat_delta, lon_delta = bounding_box_deltas(latitude, radius_km)

        stmt = (
            select(CivicIssue)
            .join(Location, CivicIssue.location_id == Location.id)
            .where(
                CivicIssue.is_deleted.is_(False),
                Location.latitude.between(latitude - lat_delta, latitude + lat_delta),
                Location.longitude.between(longitude - lon_delta, longitude + lon_delta),
            )
            .options(joinedload(CivicIssue.location), joinedload(CivicIssue.department), joinedload(CivicIssue.images))
        )
        candidates = self.db.execute(stmt).unique().scalars().all()

        def distance_km(issue: CivicIssue) -> float:
            return haversine_km(latitude, longitude, issue.location.latitude, issue.location.longitude)

        within_radius = sorted((i for i in candidates if distance_km(i) <= radius_km), key=distance_km)
        total = len(within_radius)
        start = (page - 1) * page_size
        return within_radius[start : start + page_size], total

    def next_reference_code(self, issue_id: int) -> str:
        return f"CIV-{1000 + issue_id}"
