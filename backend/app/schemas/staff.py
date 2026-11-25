from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.core.enums import AssignmentStatus, ImageType
from app.schemas.issue import IssueDetailResponse, IssueImageResponse, IssueSummaryResponse


class StaffIssueSummary(IssueSummaryResponse):
    assignment_status: AssignmentStatus
    progress_percent: int
    assigned_at: datetime


class PaginatedStaffIssues(BaseModel):
    items: List[StaffIssueSummary]
    total: int
    page: int
    page_size: int


class StaffIssueDetail(IssueDetailResponse):
    assignment_status: AssignmentStatus
    accepted_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    staff_notes: Optional[str] = None


class AssignmentActionResponse(BaseModel):
    success: bool = True
    message: str
    assignment_status: AssignmentStatus
    issue_status: str
    progress_percent: int


class AddNoteRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    visible_to_citizen: bool = False  # internal by default


class ProgressUpdateRequest(BaseModel):
    percent: int = Field(ge=0, le=99, description="0-99; 100% is reached by resolving the issue")
    note: Optional[str] = Field(default=None, max_length=1000)


class ResolveRequest(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=2000)


class PhotoUploadResponse(BaseModel):
    success: bool = True
    image_type: ImageType
    images: List[IssueImageResponse]


class StaffStatsResponse(BaseModel):
    employee_code: Optional[str] = None
    designation: Optional[str] = None
    department_name: Optional[str] = None
    current_workload: int
    total_resolved: int
    average_resolution_hours: Optional[float] = None
    pending: int
    accepted: int
    in_progress: int
