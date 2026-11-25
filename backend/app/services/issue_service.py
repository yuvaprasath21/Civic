"""
Core issue lifecycle logic.

Not yet implemented here (later phases plug into this same model):
  - Duplicate detection (Phase 7) — duplicate_count stays 0 until then,
    so the priority engine's frequency term is correctly 0 for now.
  - Field staff assignment and resolution (Phase 8).
  - Admin verification (Phase 9).
"""
from typing import List, Optional
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from ai.inference.base import AIProviderError
from app.core.enums import AssignmentStatus, IssueStatus, NotificationType, UserRole
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models.civic_issue import CivicIssue
from app.models.department import IssueCategoryMapping
from app.models.issue_image import IssueImage
from app.models.issue_workflow import IssueStatusHistory
from app.models.user import User
from app.repositories.comment_feedback_repository import IssueCommentRepository, IssueFeedbackRepository
from app.repositories.issue_repository import IssueRepository
from app.repositories.location_repository import LocationRepository
from app.schemas.ai import AIPredictionSummary
from app.schemas.issue import (
    CommentResponse,
    CreateCommentRequest,
    CreateFeedbackRequest,
    CreateIssueRequest,
    FeedbackResponse,
    IssueDetailResponse,
    IssueImageResponse,
    IssueSummaryResponse,
    LocationInput,
    LocationResponse,
    PaginatedIssuesResponse,
    StatusHistoryEntryResponse,
    UpdateIssueRequest,
)
from app.services.ai_service import AIService
from app.services.audit_service import AuditService
from app.services.duplicate_service import DuplicateService
from app.services.notification_service import NotificationService
from app.services.priority_service import PriorityService
from app.utils.file_upload import save_uploaded_image, save_uploaded_video, get_upload_url
from app.utils.file_upload import save_uploaded_image, save_uploaded_video
from app.utils.image_hash import dhash

MAX_IMAGES_PER_ISSUE = 5
EDITABLE_STATUSES = {IssueStatus.REPORTED, IssueStatus.AI_ANALYZED, IssueStatus.POTENTIAL_DUPLICATE}
FEEDBACK_ELIGIBLE_STATUSES = {IssueStatus.RESOLVED, IssueStatus.CLOSED}


class IssueService:
    def __init__(self, db: Session):
        self.db = db
        self.issues = IssueRepository(db)
        self.locations = LocationRepository(db)
        self.comments = IssueCommentRepository(db)
        self.feedback_repo = IssueFeedbackRepository(db)
        self.audit = AuditService(db)
        self.notifications = NotificationService(db)
        self.ai = AIService(db)
        self.priority = PriorityService(db)
        self.duplicates = DuplicateService(db)

    async def create_issue(
        self,
        reporter: User,
        payload: CreateIssueRequest,
        images: List[UploadFile],
        video: Optional[UploadFile],
    ) -> IssueDetailResponse:
        if not images:
            raise ValidationAppError("At least one image is required to report an issue.", error_code="IMAGE_REQUIRED")
        if len(images) > MAX_IMAGES_PER_ISSUE:
            raise ValidationAppError(
                f"A maximum of {MAX_IMAGES_PER_ISSUE} images is allowed per report.", error_code="TOO_MANY_IMAGES"
            )

        location = self.locations.create(
            LocationInput(
                latitude=payload.latitude,
                longitude=payload.longitude,
                address_text=payload.address_text,
                landmark=payload.landmark,
                ward=payload.ward,
                city=payload.city,
                pincode=payload.pincode,
            )
        )

        department_id = self._resolve_department_for_category(payload.category)

        issue = CivicIssue(
            reporter_id=reporter.id,
            location_id=location.id,
            department_id=department_id,
            title=payload.title.strip(),
            description=payload.description,
            category=payload.category,
            severity=payload.severity,
            status=IssueStatus.REPORTED,
            reference_code=f"TMP{uuid4().hex[:12]}",
        )
        self.issues.create(issue)
        issue.reference_code = self.issues.next_reference_code(issue.id)
        issue.location = location

        first_image_bytes: Optional[bytes] = None
        first_image_content_type: Optional[str] = None
        created_images: List[IssueImage] = []

        for idx, upload in enumerate(images):
            if idx == 0:
                first_image_bytes = await upload.read()
                first_image_content_type = upload.content_type
                await upload.seek(0)

            saved = await save_uploaded_image(upload, subdirectory="issue_images")
            image = IssueImage(
                issue_id=issue.id,
                uploaded_by_id=reporter.id,
                file_path=saved.relative_path,
                original_filename=upload.filename,
                content_type=saved.content_type,
                file_size_bytes=saved.size_bytes,
                width=saved.width,
                height=saved.height,
            )
            if idx == 0 and first_image_bytes is not None:
                image.perceptual_hash = dhash(first_image_bytes)
            self.db.add(image)
            created_images.append(image)

        self.db.flush()

        if video is not None:
            saved_video = await save_uploaded_video(video, subdirectory="issue_videos")
            issue.video_path = saved_video.relative_path

        self.db.add(
            IssueStatusHistory(
                issue_id=issue.id,
                changed_by_id=reporter.id,
                from_status=None,
                to_status=IssueStatus.REPORTED,
                note="Issue reported by citizen.",
            )
        )

        if first_image_bytes is not None:
            try:
                prediction = await self.ai.analyze_and_store(
                    issue_id=issue.id,
                    issue_image_id=created_images[0].id,
                    image_bytes=first_image_bytes,
                    content_type=first_image_content_type or "application/octet-stream",
                )
                issue.is_citizen_edited_category = payload.category.value != prediction.predicted_category.value
                issue.status = IssueStatus.AI_ANALYZED
                self.db.add(
                    IssueStatusHistory(
                        issue_id=issue.id,
                        changed_by_id=None,
                        from_status=IssueStatus.REPORTED,
                        to_status=IssueStatus.AI_ANALYZED,
                        note=(
                            f"AI suggested {prediction.predicted_category.value} "
                            f"({prediction.confidence:.0%} confidence, {prediction.predicted_severity.value} severity)."
                        ),
                    )
                )
                self.notifications.create(
                    recipient_id=reporter.id,
                    type=NotificationType.AI_ANALYSIS_COMPLETE,
                    title="AI analysis complete",
                    message=f"AI analysis for {issue.reference_code} is complete.",
                    issue_id=issue.id,
                )
            except AIProviderError as exc:
                self.audit.record(
                    actor_id=reporter.id,
                    action="AI_ANALYSIS_FAILED",
                    entity_type="civic_issue",
                    entity_id=issue.id,
                    details={"error": str(exc)},
                )

        # --- duplicate detection (Phase 7) ---
        # After AI so the status history reads REPORTED -> AI_ANALYZED ->
        # POTENTIAL_DUPLICATE. Also re-scores the master (its report
        # count just went up) inside this same transaction.
        match = self.duplicates.flag_if_duplicate(
            issue, image_hash=created_images[0].perceptual_hash if created_images else None
        )

        self.priority.compute_and_apply(issue)

        self.db.commit()
        self.db.refresh(issue)

        self.audit.record(
            actor_id=reporter.id, action="ISSUE_CREATED", entity_type="civic_issue", entity_id=issue.id
        )
        self.notifications.create(
            recipient_id=reporter.id,
            type=NotificationType.ISSUE_SUBMITTED,
            title="Issue reported",
            message=f"Your report {issue.reference_code} has been submitted and is pending review.",
            issue_id=issue.id,
        )
        if match is not None:
            self.audit.record(
                actor_id=reporter.id, action="DUPLICATE_FLAGGED", entity_type="civic_issue", entity_id=issue.id,
                details={
                    "master_id": match.master.id,
                    "distance_meters": match.distance_meters,
                    "image_similarity": match.image_similarity,
                },
            )

        return self.get_issue(issue.uuid, current_user=reporter)

    def get_issue(self, issue_uuid: str, current_user: User) -> IssueDetailResponse:
        issue = self.issues.get_by_uuid(issue_uuid)
        if issue is None:
            raise NotFoundError("Issue not found.", error_code="ISSUE_NOT_FOUND")
        return self._to_detail_response(issue, viewer=current_user)

    def list_issues(
        self,
        *,
        current_user: Optional[User] = None,
        only_mine: bool = False,
        category=None,
        status=None,
        severity=None,
        city: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedIssuesResponse:
        page_size = min(page_size, 100)
        reporter_id = current_user.id if (only_mine and current_user) else None

        items, total = self.issues.list_filtered(
            reporter_id=reporter_id,
            category=category,
            status=status,
            severity=severity,
            city=city,
            search=search,
            page=page,
            page_size=page_size,
        )
        return PaginatedIssuesResponse(
            items=[self._to_summary_response(i) for i in items], total=total, page=page, page_size=page_size
        )

    def list_nearby(
        self, *, latitude: float, longitude: float, radius_km: float, page: int = 1, page_size: int = 20
    ) -> PaginatedIssuesResponse:
        page_size = min(page_size, 100)
        items, total = self.issues.list_near(
            latitude=latitude, longitude=longitude, radius_km=radius_km, page=page, page_size=page_size
        )
        return PaginatedIssuesResponse(
            items=[self._to_summary_response(i) for i in items], total=total, page=page, page_size=page_size
        )

    def update_issue(self, issue_uuid: str, current_user: User, payload: UpdateIssueRequest) -> IssueDetailResponse:
        issue = self.issues.get_by_uuid(issue_uuid)
        if issue is None:
            raise NotFoundError("Issue not found.", error_code="ISSUE_NOT_FOUND")

        if issue.reporter_id != current_user.id:
            raise ForbiddenError("You can only edit issues you reported.", error_code="NOT_ISSUE_OWNER")

        if issue.status not in EDITABLE_STATUSES:
            raise ConflictError(
                "This issue can no longer be edited because it has already been verified.",
                error_code="ISSUE_NOT_EDITABLE",
            )

        data = payload.model_dump(exclude_unset=True)
        severity_or_category_changed = False

        if "title" in data and data["title"] is not None:
            issue.title = data["title"].strip()
        if "description" in data:
            issue.description = data["description"]
        if "category" in data and data["category"] is not None:
            issue.category = data["category"]
            issue.is_citizen_edited_category = True
            issue.department_id = self._resolve_department_for_category(data["category"]) or issue.department_id
            severity_or_category_changed = True
        if "severity" in data and data["severity"] is not None:
            issue.severity = data["severity"]
            severity_or_category_changed = True

        if severity_or_category_changed:
            self.priority.compute_and_apply(issue)

        self.db.add(issue)
        self.db.commit()
        self.db.refresh(issue)

        self.audit.record(
            actor_id=current_user.id, action="ISSUE_UPDATED", entity_type="civic_issue", entity_id=issue.id
        )

        return self.get_issue(issue.uuid, current_user)

    def add_comment(self, issue_uuid: str, current_user: User, payload: CreateCommentRequest) -> CommentResponse:
        issue = self.issues.get_by_uuid(issue_uuid)
        if issue is None:
            raise NotFoundError("Issue not found.", error_code="ISSUE_NOT_FOUND")

        is_internal = payload.is_internal and current_user.role != UserRole.CITIZEN

        comment = self.comments.create(
            issue_id=issue.id, author_id=current_user.id, body=payload.body.strip(), is_internal=is_internal
        )
        return CommentResponse(
            id=comment.id,
            author_name=current_user.full_name,
            author_role=current_user.role.value,
            body=comment.body,
            is_internal=comment.is_internal,
            created_at=comment.created_at,
        )

    def add_feedback(self, issue_uuid: str, current_user: User, payload: CreateFeedbackRequest) -> FeedbackResponse:
        issue = self.issues.get_by_uuid(issue_uuid)
        if issue is None:
            raise NotFoundError("Issue not found.", error_code="ISSUE_NOT_FOUND")

        if issue.reporter_id != current_user.id:
            raise ForbiddenError("Only the reporter can leave feedback on this issue.", error_code="NOT_ISSUE_OWNER")

        if issue.status not in FEEDBACK_ELIGIBLE_STATUSES:
            raise ConflictError(
                "Feedback can only be left once an issue is resolved or closed.", error_code="ISSUE_NOT_RESOLVED"
            )

        if self.feedback_repo.get_by_issue_id(issue.id) is not None:
            raise ConflictError("Feedback has already been submitted for this issue.", error_code="FEEDBACK_EXISTS")

        feedback = self.feedback_repo.create(
            issue_id=issue.id, citizen_id=current_user.id, rating=payload.rating, comment=payload.comment
        )
        self.audit.record(
            actor_id=current_user.id, action="FEEDBACK_SUBMITTED", entity_type="civic_issue", entity_id=issue.id
        )
        return FeedbackResponse(rating=feedback.rating, comment=feedback.comment, created_at=feedback.created_at)

    def _resolve_department_for_category(self, category) -> Optional[int]:
        mapping = (
            self.db.query(IssueCategoryMapping)
            .filter(IssueCategoryMapping.category == category.value, IssueCategoryMapping.is_active.is_(True))
            .first()
        )
        return mapping.department_id if mapping else None

    @staticmethod
    def _to_summary_response(issue: CivicIssue) -> IssueSummaryResponse:
        thumbnail_url = get_upload_url(issue.images[0].file_path) if issue.images else None
        return IssueSummaryResponse(
            id=issue.uuid,
            reference_code=issue.reference_code,
            title=issue.title,
            category=issue.category,
            severity=issue.severity,
            status=issue.status,
            priority_level=issue.priority_level,
            priority_score=issue.priority_score,
            location=LocationResponse(
                latitude=issue.location.latitude,
                longitude=issue.location.longitude,
                address_text=issue.location.address_text,
                landmark=issue.location.landmark,
                ward=issue.location.ward,
                city=issue.location.city,
                pincode=issue.location.pincode,
            ),
            thumbnail_url=thumbnail_url,
            created_at=issue.created_at,
            department_name=issue.department.name if issue.department else None,
        )

    @staticmethod
    def _to_detail_response(issue: CivicIssue, viewer: Optional[User] = None) -> IssueDetailResponse:
        # Internal notes are for staff and admins only. Filtering happens
        # here, on the server — never rely on the client to hide them.
        # No viewer (or a citizen) gets the safe default: internal hidden.
        can_see_internal = viewer is not None and viewer.role in (
            UserRole.FIELD_STAFF, UserRole.DEPARTMENT_ADMIN, UserRole.SUPER_ADMIN
        )
        latest_prediction = (
            max(issue.ai_predictions, key=lambda p: (p.created_at, p.id)) if issue.ai_predictions else None
        )
        active_assignments = [
            a for a in issue.assignments
            if a.status in (AssignmentStatus.PENDING, AssignmentStatus.ACCEPTED, AssignmentStatus.IN_PROGRESS)
        ]
        active_assignment = max(active_assignments, key=lambda a: a.id) if active_assignments else None
        return IssueDetailResponse(
            id=issue.uuid,
            reference_code=issue.reference_code,
            title=issue.title,
            description=issue.description,
            category=issue.category,
            severity=issue.severity,
            status=issue.status,
            priority_level=issue.priority_level,
            priority_score=issue.priority_score,
            is_ai_verified=issue.is_ai_verified,
            is_citizen_edited_category=issue.is_citizen_edited_category,
            location=LocationResponse(
                latitude=issue.location.latitude,
                longitude=issue.location.longitude,
                address_text=issue.location.address_text,
                landmark=issue.location.landmark,
                ward=issue.location.ward,
                city=issue.location.city,
                pincode=issue.location.pincode,
            ),
            department_name=issue.department.name if issue.department else None,
            reporter_name=issue.reporter.full_name,
            reporter_id=issue.reporter.uuid,
            images=[
                IssueImageResponse(
                    id=img.id,
                    image_type=img.image_type.value,
                    url=get_upload_url(img.file_path),
                    width=img.width,
                    height=img.height,
                    created_at=img.created_at,
                )
                for img in sorted(issue.images, key=lambda i: i.created_at)
            ],
            video_url=get_upload_url(issue.video_path) if issue.video_path else None,
            ai_prediction=(
                AIPredictionSummary(
                    category=latest_prediction.predicted_category,
                    confidence=latest_prediction.confidence,
                    severity=latest_prediction.predicted_severity,
                    detected_objects=latest_prediction.detected_objects,
                    model_version=latest_prediction.model_version,
                    provider=latest_prediction.provider,
                )
                if latest_prediction
                else None
            ),
            status_history=[
                StatusHistoryEntryResponse(
                    from_status=h.from_status,
                    to_status=h.to_status,
                    note=h.note,
                    changed_by_name=h.changed_by.full_name if h.changed_by_id and h.changed_by else None,
                    created_at=h.created_at,
                )
                for h in sorted(issue.status_history, key=lambda h: (h.created_at, h.id))
            ],
            comments=[
                CommentResponse(
                    id=c.id,
                    author_name=c.author.full_name if c.author else "Unknown",
                    author_role=c.author.role.value if c.author else "",
                    body=c.body,
                    is_internal=c.is_internal,
                    created_at=c.created_at,
                )
                for c in sorted(issue.comments, key=lambda c: (c.created_at, c.id))
                if can_see_internal or not c.is_internal
            ],
            feedback=(
                FeedbackResponse(
                    rating=issue.feedback.rating, comment=issue.feedback.comment, created_at=issue.feedback.created_at
                )
                if issue.feedback
                else None
            ),
            assigned_to_name=active_assignment.staff.full_name if active_assignment else None,
            progress_percent=active_assignment.progress_percent if active_assignment else None,
            duplicate_count=issue.duplicate_count,
            report_count=issue.duplicate_count + 1,
            master_issue_id=issue.master_issue.uuid if issue.master_issue else None,
            master_reference_code=issue.master_issue.reference_code if issue.master_issue else None,
            created_at=issue.created_at,
            resolved_at=issue.resolved_at,
        )
