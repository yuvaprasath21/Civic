"""
Admin issue actions needed by earlier phases (the rest of /api/admin/* arrives in Phase 9).

  PUT  /api/admin/issues/{id}/verify             — verify (REPORTED/AI_ANALYZED -> VERIFIED)
  PUT  /api/admin/issues/{id}/assign             — assign / reassign to a field staff member

  GET  /api/admin/issues/{id}/duplicates         — reports grouped under a master
  POST /api/admin/issues/{id}/merge              — merge duplicates INTO master {id}
  POST /api/admin/issues/{id}/not-duplicate      — reject an automatic duplicate flag on {id}
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.auth import require_any_admin
from app.models.user import User
from app.schemas.admin_issue import (
    AssignIssueRequest,
    AssignmentResponse,
    DuplicateListResponse,
    MergeIssuesRequest,
    MergeResultResponse,
    VerifyIssueRequest,
)
from app.schemas.issue import IssueDetailResponse
from app.services.assignment_service import AssignmentService
from app.services.duplicate_service import DuplicateService
from app.services.issue_service import IssueService

router = APIRouter(prefix="/admin/issues", tags=["admin-duplicates"])


@router.get("/{master_uuid}/duplicates", response_model=DuplicateListResponse)
def list_duplicates(master_uuid: str, admin: User = Depends(require_any_admin), db: Session = Depends(get_db)):
    service = DuplicateService(db)
    duplicates = service.list_duplicates(master_uuid)
    master = service._get(master_uuid)
    return DuplicateListResponse(
        master_reference_code=master.reference_code,
        report_count=master.duplicate_count + 1,
        duplicates=[IssueService._to_summary_response(d) for d in duplicates],
    )


@router.post("/{master_uuid}/merge", response_model=MergeResultResponse)
def merge_issues(
    master_uuid: str,
    payload: MergeIssuesRequest,
    admin: User = Depends(require_any_admin),
    db: Session = Depends(get_db),
):
    master = DuplicateService(db).merge(master_uuid=master_uuid, duplicate_uuids=payload.duplicate_ids, admin=admin)
    return MergeResultResponse(
        message=f"Merged into {master.reference_code}.",
        master_id=master.uuid,
        master_reference_code=master.reference_code,
        report_count=master.duplicate_count + 1,
        priority_score=master.priority_score,
        priority_level=master.priority_level.value,
    )


@router.post("/{issue_uuid}/not-duplicate", response_model=IssueDetailResponse)
def mark_not_duplicate(issue_uuid: str, admin: User = Depends(require_any_admin), db: Session = Depends(get_db)):
    issue = DuplicateService(db).mark_not_duplicate(issue_uuid=issue_uuid, admin=admin)
    return IssueService(db).get_issue(issue.uuid, admin)


@router.put("/{issue_uuid}/verify", response_model=IssueDetailResponse)
def verify_issue(
    issue_uuid: str,
    payload: VerifyIssueRequest = VerifyIssueRequest(),
    admin: User = Depends(require_any_admin),
    db: Session = Depends(get_db),
):
    issue = AssignmentService(db).verify(issue_uuid, admin, payload.note)
    return IssueService(db).get_issue(issue.uuid, admin)


@router.put("/{issue_uuid}/assign", response_model=AssignmentResponse)
def assign_issue(
    issue_uuid: str,
    payload: AssignIssueRequest,
    admin: User = Depends(require_any_admin),
    db: Session = Depends(get_db),
):
    assignment = AssignmentService(db).assign(issue_uuid, payload.staff_id, admin)
    db.refresh(assignment)
    return AssignmentResponse(
        message=f"Assigned to {assignment.staff.full_name}.",
        issue_id=issue_uuid,
        issue_status=assignment.issue.status.value,
        staff_id=assignment.staff.uuid,
        staff_name=assignment.staff.full_name,
    )
