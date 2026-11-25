"""
Duplicate detection and grouping.

Detection (automatic, on issue creation). A new issue is flagged
POTENTIAL_DUPLICATE of an existing "master" issue when ALL hold:
  - same category,
  - within DUPLICATE_RADIUS_METERS,
  - the master was reported within DUPLICATE_TIME_WINDOW_HOURS,
  - the master is still open (not RESOLVED / CLOSED / REJECTED — a new
    report at a spot that was already fixed is a recurrence, not a dupe),
  - the master is itself a master (never chain duplicates of duplicates).
If several masters qualify, the nearest wins. Image similarity (dHash) is
recorded when both sides have a photo hash but is deliberately NOT a
veto: the same pothole photographed from another angle can score low.

Grouping. Each flagged duplicate is linked to its master by an
issue_duplicates row and counted in master.duplicate_count, which feeds
the priority engine's report-frequency term (so a master that several
citizens keep reporting climbs in priority). "Reports: N" = 1 + duplicate_count.

Admin correction. An admin can confirm/merge duplicates into a master
(the merged report is closed with a timeline note) or mark a flagged
report as NOT a duplicate (it returns to the normal workflow and the
master's count/priority are rolled back).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.enums import IssueStatus
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.civic_issue import CivicIssue
from app.models.issue_workflow import IssueDuplicate, IssueStatusHistory
from app.models.location import Location
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.priority_service import PriorityService
from app.utils.geo import bounding_box_deltas, haversine_km
from app.utils.image_hash import similarity

# Open masters only: a repeat report after resolution is a recurrence.
NON_MASTER_STATUSES = {IssueStatus.RESOLVED, IssueStatus.CLOSED, IssueStatus.REJECTED}


@dataclass
class DuplicateMatch:
    master: CivicIssue
    distance_meters: float
    time_delta_hours: float
    image_similarity: Optional[float]


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _first_hash(issue: CivicIssue) -> Optional[str]:
    for image in sorted(issue.images, key=lambda i: i.id):
        if image.perceptual_hash:
            return image.perceptual_hash
    return None


class DuplicateService:
    def __init__(self, db: Session):
        self.db = db
        self.priority = PriorityService(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------
    def find_match(self, issue: CivicIssue, *, image_hash: Optional[str] = None) -> Optional[DuplicateMatch]:
        radius_m = settings.DUPLICATE_RADIUS_METERS
        lat, lon = issue.location.latitude, issue.location.longitude
        lat_delta, lon_delta = bounding_box_deltas(lat, radius_m / 1000)

        stmt = (
            select(CivicIssue)
            .join(Location, CivicIssue.location_id == Location.id)
            .where(
                CivicIssue.is_deleted.is_(False),
                CivicIssue.id != issue.id,
                CivicIssue.category == issue.category,
                CivicIssue.master_issue_id.is_(None),
                Location.latitude.between(lat - lat_delta, lat + lat_delta),
                Location.longitude.between(lon - lon_delta, lon + lon_delta),
            )
            .options(joinedload(CivicIssue.location), joinedload(CivicIssue.images))
        )
        candidates = self.db.execute(stmt).unique().scalars().all()

        now = datetime.now(timezone.utc)
        window = timedelta(hours=settings.DUPLICATE_TIME_WINDOW_HOURS)
        best: Optional[DuplicateMatch] = None

        for candidate in candidates:
            if candidate.status in NON_MASTER_STATUSES:
                continue
            age = now - _as_utc(candidate.created_at)
            if age > window:
                continue
            distance_m = haversine_km(lat, lon, candidate.location.latitude, candidate.location.longitude) * 1000
            if distance_m > radius_m:
                continue
            if best is None or distance_m < best.distance_meters:
                best = DuplicateMatch(
                    master=candidate,
                    distance_meters=round(distance_m, 1),
                    time_delta_hours=round(age.total_seconds() / 3600, 2),
                    image_similarity=similarity(image_hash, _first_hash(candidate)),
                )
        return best

    def flag_if_duplicate(
        self, issue: CivicIssue, *, image_hash: Optional[str] = None
    ) -> Optional[DuplicateMatch]:
        """
        Called during issue creation (inside its transaction — does not
        commit). Marks the issue POTENTIAL_DUPLICATE and links it to its
        master when a match is found.
        """
        match = self.find_match(issue, image_hash=image_hash)
        if match is None:
            return None

        previous_status = issue.status
        issue.master_issue_id = match.master.id
        issue.status = IssueStatus.POTENTIAL_DUPLICATE

        self.db.add(
            IssueDuplicate(
                master_issue_id=match.master.id,
                duplicate_issue_id=issue.id,
                distance_meters=match.distance_meters,
                time_delta_hours=match.time_delta_hours,
                image_similarity_score=match.image_similarity,
                matched_automatically=True,
            )
        )
        self.db.add(
            IssueStatusHistory(
                issue_id=issue.id,
                changed_by_id=None,
                from_status=previous_status,
                to_status=IssueStatus.POTENTIAL_DUPLICATE,
                note=(
                    f"Possible duplicate of {match.master.reference_code} "
                    f"({match.distance_meters:.0f} m away, same category). Pending admin review."
                ),
            )
        )
        self._bump_master(match.master, +1)
        return match

    # ------------------------------------------------------------------
    # Admin actions
    # ------------------------------------------------------------------
    def merge(self, *, master_uuid: str, duplicate_uuids: List[str], admin: User) -> CivicIssue:
        if not duplicate_uuids:
            raise ValidationAppError("Provide at least one duplicate issue to merge.", error_code="NO_DUPLICATES_GIVEN")

        master = self._get(master_uuid)
        if master.master_issue_id is not None:
            raise ConflictError(
                "The target issue is itself a duplicate. Merge into its master instead.", error_code="MASTER_IS_DUPLICATE"
            )
        if master.status in NON_MASTER_STATUSES:
            raise ConflictError(
                "The target issue is already resolved, closed or rejected and cannot absorb reports.",
                error_code="MASTER_NOT_OPEN",
            )

        seen = set()
        audit_entries: List[dict] = []
        try:
            for dup_uuid in duplicate_uuids:
                if dup_uuid in seen:
                    continue
                seen.add(dup_uuid)
                if dup_uuid == master_uuid:
                    raise ValidationAppError("An issue cannot be merged into itself.", error_code="SELF_MERGE")
                duplicate = self._get(dup_uuid)
                entry = self._merge_one(master, duplicate, admin)
                if entry:
                    audit_entries.append(entry)
        except Exception:
            self.db.rollback()  # all-or-nothing
            raise

        # One transaction for the whole merge: either every duplicate is
        # merged or (if any raised above) none are.
        self.db.commit()
        for entry in audit_entries:
            self.audit.record(
                actor_id=admin.id, action="ISSUES_MERGED", entity_type="civic_issue", entity_id=master.id, details=entry
            )
        self.db.refresh(master)
        return master

    def mark_not_duplicate(self, *, issue_uuid: str, admin: User) -> CivicIssue:
        issue = self._get(issue_uuid)
        link = self._link_for(issue)
        if issue.master_issue_id is None or link is None:
            raise ConflictError("This issue is not currently linked as a duplicate.", error_code="NOT_A_DUPLICATE")
        if link.merged_by_id is not None:
            raise ConflictError(
                "This duplicate was already confirmed and merged; it can no longer be dismissed.",
                error_code="ALREADY_MERGED",
            )

        master = self.db.get(CivicIssue, issue.master_issue_id)
        self.db.delete(link)
        issue.master_issue_id = None
        previous = issue.status
        # Back into the normal workflow, to the stage it had reached.
        issue.status = IssueStatus.AI_ANALYZED if issue.ai_predictions else IssueStatus.REPORTED
        self.db.add(
            IssueStatusHistory(
                issue_id=issue.id,
                changed_by_id=admin.id,
                from_status=previous,
                to_status=issue.status,
                note="Admin reviewed: not a duplicate.",
            )
        )
        if master is not None:
            self._bump_master(master, -1)

        self.db.commit()
        self.audit.record(
            actor_id=admin.id, action="DUPLICATE_DISMISSED", entity_type="civic_issue", entity_id=issue.id,
            details={"former_master_id": master.id if master else None},
        )
        self.db.refresh(issue)
        return issue

    def list_duplicates(self, master_uuid: str) -> List[CivicIssue]:
        master = self._get(master_uuid)
        stmt = (
            select(CivicIssue)
            .where(CivicIssue.master_issue_id == master.id, CivicIssue.is_deleted.is_(False))
            .options(joinedload(CivicIssue.location), joinedload(CivicIssue.images), joinedload(CivicIssue.department))
            .order_by(CivicIssue.created_at)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    # ------------------------------------------------------------------
    def _merge_one(self, master: CivicIssue, duplicate: CivicIssue, admin: User) -> Optional[dict]:
        has_children = self.db.execute(
            select(CivicIssue.id).where(CivicIssue.master_issue_id == duplicate.id).limit(1)
        ).first()
        if has_children:
            raise ConflictError(
                f"{duplicate.reference_code} has duplicates of its own. Merge those first.",
                error_code="ISSUE_HAS_DUPLICATES",
            )

        link = self._link_for(duplicate)
        if link is not None and link.merged_by_id is not None and duplicate.master_issue_id == master.id:
            return None  # already merged into this master — idempotent

        if link is not None and duplicate.master_issue_id != master.id:
            # Re-home from the old master to this one.
            old_master = self.db.get(CivicIssue, duplicate.master_issue_id)
            if old_master is not None:
                self._bump_master(old_master, -1)
            self.db.delete(link)
            self.db.flush()
            link = None

        if link is None:
            self.db.add(
                IssueDuplicate(
                    master_issue_id=master.id,
                    duplicate_issue_id=duplicate.id,
                    matched_automatically=False,
                    merged_by_id=admin.id,
                )
            )
            self._bump_master(master, +1)
        else:
            link.merged_by_id = admin.id  # confirms an automatic match

        previous = duplicate.status
        duplicate.master_issue_id = master.id
        duplicate.status = IssueStatus.CLOSED
        self.db.add(
            IssueStatusHistory(
                issue_id=duplicate.id,
                changed_by_id=admin.id,
                from_status=previous,
                to_status=IssueStatus.CLOSED,
                note=f"Merged into {master.reference_code}.",
            )
        )
        self.db.add(
            IssueStatusHistory(
                issue_id=master.id,
                changed_by_id=admin.id,
                from_status=master.status,
                to_status=master.status,
                note=f"{duplicate.reference_code} merged into this issue.",
            )
        )
        return {"duplicate_id": duplicate.id, "duplicate_reference": duplicate.reference_code}

    def _bump_master(self, master: CivicIssue, delta: int) -> None:
        master.duplicate_count = max(master.duplicate_count + delta, 0)
        # Report frequency is part of the priority score, so re-score.
        self.priority.compute_and_apply(master)

    def _link_for(self, issue: CivicIssue) -> Optional[IssueDuplicate]:
        return self.db.execute(
            select(IssueDuplicate).where(IssueDuplicate.duplicate_issue_id == issue.id)
        ).scalar_one_or_none()

    def _get(self, issue_uuid: str) -> CivicIssue:
        issue = self.db.execute(
            select(CivicIssue)
            .where(CivicIssue.uuid == issue_uuid, CivicIssue.is_deleted.is_(False))
            .options(joinedload(CivicIssue.location), joinedload(CivicIssue.ai_predictions))
        ).unique().scalar_one_or_none()
        if issue is None:
            raise NotFoundError("Issue not found.", error_code="ISSUE_NOT_FOUND")
        return issue
