"""
Field-staff endpoints. Every route requires the FIELD_STAFF role, and every
write additionally requires that the caller holds the issue's active
assignment (checked in AssignmentService, business rule 3).

  GET  /api/staff/me                       — my profile + workload stats
  GET  /api/staff/issues                   — my active assignments (filter by priority/status)
  GET  /api/staff/history                  — completed / handed-over work
  GET  /api/staff/issues/{id}              — issue detail with my assignment state
  PUT  /api/staff/issues/{id}/accept
  PUT  /api/staff/issues/{id}/start
  POST /api/staff/issues/{id}/notes        — internal (default) or citizen-visible note
  PUT  /api/staff/issues/{id}/progress     — progress % + note (visible to citizen)
  POST /api/staff/issues/{id}/photos       — BEFORE_WORK / AFTER_WORK photos
  PUT  /api/staff/issues/{id}/resolve      — requires >= 1 AFTER_WORK photo
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import ImageType, IssueStatus, PriorityLevel
from app.middleware.auth import require_field_staff
from app.models.issue_workflow import IssueAssignment
from app.models.user import User
from app.schemas.issue import CommentResponse, IssueImageResponse
from app.schemas.staff import (
    AddNoteRequest,
    AssignmentActionResponse,
    PaginatedStaffIssues,
    PhotoUploadResponse,
    ProgressUpdateRequest,
    ResolveRequest,
    StaffIssueDetail,
    StaffIssueSummary,
    StaffStatsResponse,
)
from app.services.assignment_service import AssignmentService
from app.services.issue_service import IssueService
from app.utils.file_upload import get_upload_url

router = APIRouter(prefix="/staff", tags=["staff"])


def _summary(assignment: IssueAssignment) -> StaffIssueSummary:
    base = IssueService._to_summary_response(assignment.issue)
    return StaffIssueSummary(
        **base.model_dump(),
        assignment_status=assignment.status,
        progress_percent=assignment.progress_percent,
        assigned_at=assignment.created_at,
    )


def _action(assignment: IssueAssignment, message: str, db: Session) -> AssignmentActionResponse:
    db.refresh(assignment)
    return AssignmentActionResponse(
        message=message,
        assignment_status=assignment.status,
        issue_status=assignment.issue.status.value,
        progress_percent=assignment.progress_percent,
    )


@router.get("/me", response_model=StaffStatsResponse)
def my_stats(staff: User = Depends(require_field_staff), db: Session = Depends(get_db)):
    return AssignmentService(db).stats(staff)


@router.get("/issues", response_model=PaginatedStaffIssues)
def my_issues(
    priority: Optional[PriorityLevel] = None,
    status: Optional[IssueStatus] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    staff: User = Depends(require_field_staff),
    db: Session = Depends(get_db),
):
    rows, total = AssignmentService(db).list_assigned(
        staff, priority_level=priority, status=status, page=page, page_size=page_size
    )
    return PaginatedStaffIssues(items=[_summary(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/history", response_model=PaginatedStaffIssues)
def my_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    staff: User = Depends(require_field_staff),
    db: Session = Depends(get_db),
):
    rows, total = AssignmentService(db).work_history(staff, page=page, page_size=page_size)
    return PaginatedStaffIssues(items=[_summary(r) for r in rows], total=total, page=page, page_size=page_size)


@router.get("/issues/{issue_uuid}", response_model=StaffIssueDetail)
def issue_detail(issue_uuid: str, staff: User = Depends(require_field_staff), db: Session = Depends(get_db)):
    issue, assignment = AssignmentService(db).assignment_for_detail(issue_uuid, staff)
    detail = IssueService(db).get_issue(issue.uuid, staff)
    return StaffIssueDetail(
        **detail.model_dump(),
        assignment_status=assignment.status,
        accepted_at=assignment.accepted_at,
        started_at=assignment.started_at,
        completed_at=assignment.completed_at,
        staff_notes=assignment.staff_notes,
    )


@router.put("/issues/{issue_uuid}/accept", response_model=AssignmentActionResponse)
def accept(issue_uuid: str, staff: User = Depends(require_field_staff), db: Session = Depends(get_db)):
    return _action(AssignmentService(db).accept(issue_uuid, staff), "Assignment accepted.", db)


@router.put("/issues/{issue_uuid}/start", response_model=AssignmentActionResponse)
def start(issue_uuid: str, staff: User = Depends(require_field_staff), db: Session = Depends(get_db)):
    return _action(AssignmentService(db).start(issue_uuid, staff), "Work started.", db)


@router.post("/issues/{issue_uuid}/notes", response_model=CommentResponse, status_code=201)
def add_note(
    issue_uuid: str, payload: AddNoteRequest, staff: User = Depends(require_field_staff), db: Session = Depends(get_db)
):
    comment = AssignmentService(db).add_note(issue_uuid, staff, payload.body, payload.visible_to_citizen)
    return CommentResponse(
        id=comment.id, author_name=staff.full_name, author_role=staff.role.value, body=comment.body,
        is_internal=comment.is_internal, created_at=comment.created_at,
    )


@router.put("/issues/{issue_uuid}/progress", response_model=AssignmentActionResponse)
def update_progress(
    issue_uuid: str, payload: ProgressUpdateRequest, staff: User = Depends(require_field_staff), db: Session = Depends(get_db)
):
    assignment = AssignmentService(db).update_progress(issue_uuid, staff, payload.percent, payload.note)
    return _action(assignment, "Progress updated.", db)


@router.post("/issues/{issue_uuid}/photos", response_model=PhotoUploadResponse, status_code=201)
async def upload_photos(
    issue_uuid: str,
    image_type: ImageType = Form(..., description="BEFORE_WORK or AFTER_WORK"),
    images: List[UploadFile] = File(...),
    staff: User = Depends(require_field_staff),
    db: Session = Depends(get_db),
):
    created = await AssignmentService(db).add_photos(issue_uuid, staff, images, image_type)
    return PhotoUploadResponse(
        image_type=image_type,
        images=[
            IssueImageResponse(
                id=i.id, image_type=i.image_type.value, url=get_upload_url(i.file_path),
                width=i.width, height=i.height, created_at=i.created_at,
            )
            for i in created
        ],
    )


@router.put("/issues/{issue_uuid}/resolve", response_model=AssignmentActionResponse)
def resolve(
    issue_uuid: str,
    payload: ResolveRequest = ResolveRequest(),
    staff: User = Depends(require_field_staff),
    db: Session = Depends(get_db),
):
    assignment = AssignmentService(db).resolve(issue_uuid, staff, payload.notes)
    return _action(assignment, "Issue marked as resolved.", db)
