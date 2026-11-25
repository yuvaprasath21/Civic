"""
Assignment and field-work logic.

Admin side:  verify an issue, assign it to a field staff member (or
             reassign it).
Staff side:  accept -> start -> (notes / progress / before+after photos)
             -> resolve.

Rules enforced here, server-side (not just in the UI):
  - Only the staff member holding the ACTIVE assignment can act on the
    issue (business rule 3). An issue has at most one active assignment.
  - Status only moves along workflow.ALLOWED_TRANSITIONS, and every move
    is written to issue_status_history (business rule 9).
  - Resolving requires at least one AFTER_WORK photo (business rule 4).
  - Staff workload / resolved-count / average resolution time are kept
    in step with each assignment change.
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import AssignmentStatus, ImageType, IssueStatus, NotificationType, UserRole
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models.civic_issue import CivicIssue
from app.models.issue_image import IssueImage
from app.models.issue_workflow import IssueAssignment, IssueComment, IssueStatusHistory
from app.models.profile import StaffProfile
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.workflow import transition
from app.utils.file_upload import save_uploaded_image

ACTIVE_ASSIGNMENT_STATUSES = (AssignmentStatus.PENDING, AssignmentStatus.ACCEPTED, AssignmentStatus.IN_PROGRESS)
MAX_PHOTOS_PER_UPLOAD = 5


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class AssignmentService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditService(db)
        self.notifications = NotificationService(db)

    # ==================================================================
    # Admin: verify + assign
    # ==================================================================
    def verify(self, issue_uuid: str, admin: User, note: Optional[str] = None) -> CivicIssue:
        issue = self._load_issue(issue_uuid)
        transition(self.db, issue, IssueStatus.VERIFIED, actor_id=admin.id, note=note or "Verified by administrator.")
        issue.is_ai_verified = True
        self.db.commit()

        self.audit.record(actor_id=admin.id, action="ISSUE_VERIFIED", entity_type="civic_issue", entity_id=issue.id)
        self.notifications.create(
            recipient_id=issue.reporter_id, type=NotificationType.ISSUE_VERIFIED, title="Issue verified",
            message=f"Your report {issue.reference_code} has been verified.", issue_id=issue.id,
        )
        return issue

    def assign(self, issue_uuid: str, staff_uuid: str, admin: User) -> IssueAssignment:
        issue = self._load_issue(issue_uuid)
        staff, profile = self._load_assignable_staff(staff_uuid)

        if issue.department_id and profile.department_id and issue.department_id != profile.department_id:
            raise ConflictError(
                "This staff member belongs to a different department than the issue.", error_code="DEPARTMENT_MISMATCH"
            )

        current = self._active_assignment(issue.id)
        previous_staff: Optional[User] = None

        if current is not None:
            if current.staff_id == staff.id:
                raise ConflictError("This issue is already assigned to that staff member.", error_code="ALREADY_ASSIGNED")
            previous_staff = self.users.get_by_id(current.staff_id)
            current.status = AssignmentStatus.REASSIGNED
            self._adjust_workload(current.staff_id, -1)

        note = f"Assigned to {staff.full_name}." if current is None else f"Reassigned to {staff.full_name}."
        if issue.status == IssueStatus.ASSIGNED:
            # Reassigning before the previous person accepted: status is
            # unchanged, but the timeline should still show it happened.
            self.db.add(
                IssueStatusHistory(
                    issue_id=issue.id, changed_by_id=admin.id, from_status=IssueStatus.ASSIGNED,
                    to_status=IssueStatus.ASSIGNED, note=note,
                )
            )
        else:
            transition(self.db, issue, IssueStatus.ASSIGNED, actor_id=admin.id, note=note)

        assignment = IssueAssignment(
            issue_id=issue.id,
            staff_id=staff.id,
            assigned_by_id=admin.id,
            department_id=issue.department_id or profile.department_id,
            status=AssignmentStatus.PENDING,
        )
        self.db.add(assignment)
        if issue.department_id is None and profile.department_id:
            issue.department_id = profile.department_id
        profile.current_workload += 1
        self.db.commit()

        self.audit.record(
            actor_id=admin.id, action="ISSUE_ASSIGNED" if current is None else "ISSUE_REASSIGNED",
            entity_type="civic_issue", entity_id=issue.id, details={"staff_id": staff.id},
        )
        self.notifications.create(
            recipient_id=staff.id, type=NotificationType.ISSUE_ASSIGNED, title="New assignment",
            message=f"{issue.reference_code} has been assigned to you.", issue_id=issue.id,
        )
        self.notifications.create(
            recipient_id=issue.reporter_id, type=NotificationType.ISSUE_ASSIGNED, title="Issue assigned",
            message=f"{issue.reference_code} has been assigned to {staff.full_name}.", issue_id=issue.id,
        )
        if previous_staff is not None:
            self.notifications.create(
                recipient_id=previous_staff.id, type=NotificationType.ASSIGNMENT_CHANGED, title="Assignment changed",
                message=f"{issue.reference_code} has been reassigned to someone else.", issue_id=issue.id,
            )
        return assignment

    # ==================================================================
    # Staff: work the issue
    # ==================================================================
    def accept(self, issue_uuid: str, staff: User) -> IssueAssignment:
        issue, assignment = self._mine(issue_uuid, staff)
        self._require_assignment_status(assignment, AssignmentStatus.PENDING, "accept")
        transition(self.db, issue, IssueStatus.ACCEPTED, actor_id=staff.id, note=f"Accepted by {staff.full_name}.")
        assignment.status = AssignmentStatus.ACCEPTED
        assignment.accepted_at = _utcnow()
        self.db.commit()
        self.audit.record(actor_id=staff.id, action="ASSIGNMENT_ACCEPTED", entity_type="civic_issue", entity_id=issue.id)
        return assignment

    def start(self, issue_uuid: str, staff: User) -> IssueAssignment:
        issue, assignment = self._mine(issue_uuid, staff)
        self._require_assignment_status(assignment, AssignmentStatus.ACCEPTED, "start")
        transition(self.db, issue, IssueStatus.IN_PROGRESS, actor_id=staff.id, note="Work started.")
        assignment.status = AssignmentStatus.IN_PROGRESS
        assignment.started_at = _utcnow()
        self.db.commit()
        self.audit.record(actor_id=staff.id, action="WORK_STARTED", entity_type="civic_issue", entity_id=issue.id)
        self.notifications.create(
            recipient_id=issue.reporter_id, type=NotificationType.WORK_STARTED, title="Work has started",
            message=f"Work on {issue.reference_code} has started.", issue_id=issue.id,
        )
        return assignment

    def add_note(self, issue_uuid: str, staff: User, body: str, visible_to_citizen: bool) -> IssueComment:
        issue, _ = self._mine(issue_uuid, staff)
        comment = IssueComment(
            issue_id=issue.id, author_id=staff.id, body=body.strip(), is_internal=not visible_to_citizen
        )
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def update_progress(self, issue_uuid: str, staff: User, percent: int, note: Optional[str]) -> IssueAssignment:
        issue, assignment = self._mine(issue_uuid, staff)
        self._require_assignment_status(assignment, AssignmentStatus.IN_PROGRESS, "update progress on")
        assignment.progress_percent = percent
        text = f"Progress update ({percent}%)" + (f": {note.strip()}" if note and note.strip() else ".")
        # Visible to the citizen, so they can follow the work.
        self.db.add(IssueComment(issue_id=issue.id, author_id=staff.id, body=text, is_internal=False))
        self.db.commit()
        return assignment

    async def add_photos(
        self, issue_uuid: str, staff: User, files: List[UploadFile], image_type: ImageType
    ) -> List[IssueImage]:
        if image_type not in (ImageType.BEFORE_WORK, ImageType.AFTER_WORK):
            raise ValidationAppError("Photo type must be BEFORE_WORK or AFTER_WORK.", error_code="INVALID_IMAGE_TYPE")
        if not files:
            raise ValidationAppError("Attach at least one photo.", error_code="IMAGE_REQUIRED")
        if len(files) > MAX_PHOTOS_PER_UPLOAD:
            raise ValidationAppError(
                f"A maximum of {MAX_PHOTOS_PER_UPLOAD} photos per upload is allowed.", error_code="TOO_MANY_IMAGES"
            )

        issue, assignment = self._mine(issue_uuid, staff)
        if image_type == ImageType.BEFORE_WORK:
            allowed = (AssignmentStatus.ACCEPTED, AssignmentStatus.IN_PROGRESS)
            hint = "Accept the assignment before uploading 'before' photos."
        else:
            allowed = (AssignmentStatus.IN_PROGRESS,)
            hint = "Start work before uploading 'after' photos."
        if assignment.status not in allowed:
            raise ConflictError(hint, error_code="PHOTO_NOT_ALLOWED_NOW")

        created: List[IssueImage] = []
        for upload in files:
            saved = await save_uploaded_image(upload, subdirectory="work_images")
            image = IssueImage(
                issue_id=issue.id, uploaded_by_id=staff.id, image_type=image_type,
                file_path=saved.relative_path, original_filename=upload.filename, content_type=saved.content_type,
                file_size_bytes=saved.size_bytes, width=saved.width, height=saved.height,
            )
            self.db.add(image)
            created.append(image)
        self.db.commit()
        for image in created:
            self.db.refresh(image)
        return created

    def resolve(self, issue_uuid: str, staff: User, notes: Optional[str]) -> IssueAssignment:
        issue, assignment = self._mine(issue_uuid, staff)
        self._require_assignment_status(assignment, AssignmentStatus.IN_PROGRESS, "resolve")

        after_photo = self.db.execute(
            select(IssueImage.id).where(IssueImage.issue_id == issue.id, IssueImage.image_type == ImageType.AFTER_WORK).limit(1)
        ).first()
        if after_photo is None:
            raise ValidationAppError(
                "Upload at least one 'after' photo as evidence before marking the issue resolved.",
                error_code="RESOLUTION_EVIDENCE_REQUIRED",
            )

        now = _utcnow()
        note = "Marked resolved by field staff." + (f" {notes.strip()}" if notes and notes.strip() else "")
        transition(self.db, issue, IssueStatus.RESOLVED, actor_id=staff.id, note=note)
        issue.resolved_at = now
        assignment.status = AssignmentStatus.COMPLETED
        assignment.completed_at = now
        assignment.progress_percent = 100
        if notes and notes.strip():
            assignment.staff_notes = notes.strip()

        profile = staff.staff_profile
        if profile is not None:
            hours = max((now - _as_utc(issue.created_at)).total_seconds() / 3600, 0.0)
            done = profile.total_resolved_count
            profile.average_resolution_hours = round(
                ((profile.average_resolution_hours or 0.0) * done + hours) / (done + 1), 2
            )
            profile.total_resolved_count = done + 1
            profile.current_workload = max(profile.current_workload - 1, 0)
        self.db.commit()

        self.audit.record(actor_id=staff.id, action="ISSUE_RESOLVED", entity_type="civic_issue", entity_id=issue.id)
        self.notifications.create(
            recipient_id=issue.reporter_id, type=NotificationType.ISSUE_RESOLVED, title="Issue resolved",
            message=f"{issue.reference_code} has been resolved. Please rate the outcome.", issue_id=issue.id,
        )
        return assignment

    # ==================================================================
    # Staff: reads
    # ==================================================================
    def _issue_options(self):
        return (
            joinedload(IssueAssignment.issue).joinedload(CivicIssue.location),
            joinedload(IssueAssignment.issue).joinedload(CivicIssue.images),
            joinedload(IssueAssignment.issue).joinedload(CivicIssue.department),
        )

    def list_assigned(
        self, staff: User, *, priority_level=None, status: Optional[IssueStatus] = None, page: int = 1, page_size: int = 20
    ):
        stmt = (
            select(IssueAssignment)
            .join(CivicIssue, IssueAssignment.issue_id == CivicIssue.id)
            .where(
                IssueAssignment.staff_id == staff.id,
                IssueAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES),
                CivicIssue.is_deleted.is_(False),
            )
            .options(*self._issue_options())
        )
        if priority_level is not None:
            stmt = stmt.where(CivicIssue.priority_level == priority_level)
        if status is not None:
            stmt = stmt.where(CivicIssue.status == status)
        # Most urgent first; oldest first among equals.
        stmt = stmt.order_by(CivicIssue.priority_score.desc(), CivicIssue.created_at.asc())
        return self._paginate(stmt, page, page_size)

    def work_history(self, staff: User, *, page: int = 1, page_size: int = 20):
        stmt = (
            select(IssueAssignment)
            .join(CivicIssue, IssueAssignment.issue_id == CivicIssue.id)
            .where(
                IssueAssignment.staff_id == staff.id,
                IssueAssignment.status.in_((AssignmentStatus.COMPLETED, AssignmentStatus.REASSIGNED)),
            )
            .options(*self._issue_options())
            .order_by(IssueAssignment.id.desc())
        )
        return self._paginate(stmt, page, page_size)

    def assignment_for_detail(self, issue_uuid: str, staff: User) -> tuple[CivicIssue, IssueAssignment]:
        """Detail access: the staff member's current assignment, or their most recent past one."""
        issue = self._load_issue(issue_uuid)
        assignment = self.db.execute(
            select(IssueAssignment)
            .where(IssueAssignment.issue_id == issue.id, IssueAssignment.staff_id == staff.id)
            .order_by(IssueAssignment.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        if assignment is None:
            raise ForbiddenError("This issue is not assigned to you.", error_code="NOT_ASSIGNED")
        return issue, assignment

    def stats(self, staff: User) -> dict:
        profile = staff.staff_profile
        active = self.db.execute(
            select(IssueAssignment).where(
                IssueAssignment.staff_id == staff.id, IssueAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES)
            )
        ).scalars().all()
        by_status = {s.value: 0 for s in ACTIVE_ASSIGNMENT_STATUSES}
        for a in active:
            by_status[a.status.value] += 1
        return {
            "employee_code": profile.employee_code if profile else None,
            "designation": profile.designation if profile else None,
            "department_name": profile.department.name if profile and profile.department else None,
            "current_workload": profile.current_workload if profile else 0,
            "total_resolved": profile.total_resolved_count if profile else 0,
            "average_resolution_hours": profile.average_resolution_hours if profile else None,
            "pending": by_status["PENDING"],
            "accepted": by_status["ACCEPTED"],
            "in_progress": by_status["IN_PROGRESS"],
        }

    # ==================================================================
    # helpers
    # ==================================================================
    def _paginate(self, stmt, page: int, page_size: int):
        page_size = min(max(page_size, 1), 100)
        total = self.db.execute(select(func.count()).select_from(stmt.order_by(None).subquery())).scalar_one()
        rows = self.db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).unique().scalars().all()
        return rows, total

    def _load_issue(self, issue_uuid: str) -> CivicIssue:
        issue = self.db.execute(
            select(CivicIssue)
            .where(CivicIssue.uuid == issue_uuid, CivicIssue.is_deleted.is_(False))
            .options(joinedload(CivicIssue.location))
        ).unique().scalar_one_or_none()
        if issue is None:
            raise NotFoundError("Issue not found.", error_code="ISSUE_NOT_FOUND")
        return issue

    def _active_assignment(self, issue_id: int) -> Optional[IssueAssignment]:
        return self.db.execute(
            select(IssueAssignment)
            .where(IssueAssignment.issue_id == issue_id, IssueAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES))
            .order_by(IssueAssignment.id.desc())
            .limit(1)
        ).scalar_one_or_none()

    def _mine(self, issue_uuid: str, staff: User) -> tuple[CivicIssue, IssueAssignment]:
        """The issue plus the caller's ACTIVE assignment — or 403 (business rule 3)."""
        issue = self._load_issue(issue_uuid)
        assignment = self._active_assignment(issue.id)
        if assignment is None or assignment.staff_id != staff.id:
            raise ForbiddenError("This issue is not assigned to you.", error_code="NOT_ASSIGNED")
        return issue, assignment

    @staticmethod
    def _require_assignment_status(assignment: IssueAssignment, expected: AssignmentStatus, verb: str) -> None:
        if assignment.status != expected:
            raise ConflictError(
                f"You can only {verb} an assignment that is {expected.value}; it is currently {assignment.status.value}.",
                error_code="INVALID_ASSIGNMENT_STATE",
            )

    def _load_assignable_staff(self, staff_uuid: str) -> tuple[User, StaffProfile]:
        staff = self.users.get_by_uuid(staff_uuid)
        if staff is None:
            raise NotFoundError("Staff member not found.", error_code="STAFF_NOT_FOUND")
        if staff.role != UserRole.FIELD_STAFF:
            raise ValidationAppError("That user is not a field staff member.", error_code="NOT_FIELD_STAFF")
        if not staff.is_active:
            raise ConflictError("That staff account is deactivated.", error_code="STAFF_INACTIVE")
        profile = staff.staff_profile
        if profile is None:
            raise ValidationAppError("That staff member has no staff profile.", error_code="STAFF_PROFILE_MISSING")
        if not profile.is_available:
            raise ConflictError("That staff member is marked unavailable.", error_code="STAFF_UNAVAILABLE")
        return staff, profile

    def _adjust_workload(self, staff_user_id: int, delta: int) -> None:
        user = self.users.get_by_id(staff_user_id)
        if user is not None and user.staff_profile is not None:
            user.staff_profile.current_workload = max(user.staff_profile.current_workload + delta, 0)
