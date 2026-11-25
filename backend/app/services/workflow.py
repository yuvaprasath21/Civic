"""
Issue status state machine.

Every status change that goes through `transition()` is validated against
this table and recorded in issue_status_history — so a status can't
skip steps (e.g. ASSIGNED straight to RESOLVED) and the timeline can't
be bypassed.

Wired so far:
    REPORTED / AI_ANALYZED -> VERIFIED         (admin verify)
    VERIFIED               -> ASSIGNED         (admin assign)
    ASSIGNED               -> ACCEPTED         (field staff accept)
    ACCEPTED               -> IN_PROGRESS      (field staff start)
    IN_PROGRESS            -> RESOLVED         (field staff resolve, evidence required)
    ACCEPTED / IN_PROGRESS -> ASSIGNED         (admin reassigns to someone else)

Automatic steps (REPORTED -> AI_ANALYZED -> POTENTIAL_DUPLICATE and the
duplicate merge/dismiss moves) are recorded where they happen. REJECTED,
REOPENED and CLOSED transitions are added with the Phase 9 admin tools.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.core.enums import IssueStatus
from app.core.exceptions import ConflictError
from app.models.civic_issue import CivicIssue
from app.models.issue_workflow import IssueStatusHistory

S = IssueStatus

ALLOWED_TRANSITIONS: dict[IssueStatus, set[IssueStatus]] = {
    S.REPORTED: {S.VERIFIED},
    S.AI_ANALYZED: {S.VERIFIED},
    S.VERIFIED: {S.ASSIGNED},
    S.ASSIGNED: {S.ACCEPTED},
    S.ACCEPTED: {S.IN_PROGRESS, S.ASSIGNED},
    S.IN_PROGRESS: {S.RESOLVED, S.ASSIGNED},
}


def transition(
    db: Session, issue: CivicIssue, to_status: IssueStatus, *, actor_id: Optional[int], note: Optional[str] = None
) -> None:
    """Validates and applies a status change and records it. Does not commit."""
    if to_status not in ALLOWED_TRANSITIONS.get(issue.status, set()):
        raise ConflictError(
            f"Cannot move an issue from {issue.status.value} to {to_status.value}.",
            error_code="INVALID_STATUS_TRANSITION",
        )
    db.add(
        IssueStatusHistory(
            issue_id=issue.id, changed_by_id=actor_id, from_status=issue.status, to_status=to_status, note=note
        )
    )
    issue.status = to_status
