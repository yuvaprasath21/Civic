from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.issue import IssueSummaryResponse


class MergeIssuesRequest(BaseModel):
    duplicate_ids: List[str] = Field(min_length=1, max_length=50, description="UUIDs of issues to merge into the master")


class MergeResultResponse(BaseModel):
    success: bool = True
    message: str
    master_id: str
    master_reference_code: str
    report_count: int  # master + all merged/linked duplicates
    priority_score: float
    priority_level: str


class DuplicateListResponse(BaseModel):
    master_reference_code: str
    report_count: int
    duplicates: List[IssueSummaryResponse]


class VerifyIssueRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=1000)


class AssignIssueRequest(BaseModel):
    staff_id: str = Field(description="UUID of the field staff user")


class AssignmentResponse(BaseModel):
    success: bool = True
    message: str
    issue_id: str
    issue_status: str
    staff_id: str
    staff_name: str


class StaffListItem(BaseModel):
    id: str
    full_name: str
    email: str
    employee_code: Optional[str] = None
    department_name: Optional[str] = None
    is_active: bool
    is_available: bool
    current_workload: int
    total_resolved: int
