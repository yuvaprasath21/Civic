from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.enums import IssueCategory, IssueStatus, PriorityLevel, SeverityLevel
from app.schemas.ai import AIPredictionSummary


class LocationInput(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address_text: Optional[str] = Field(default=None, max_length=500)
    landmark: Optional[str] = Field(default=None, max_length=255)
    ward: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    pincode: Optional[str] = Field(default=None, max_length=10)


class LocationResponse(BaseModel):
    latitude: float
    longitude: float
    address_text: Optional[str] = None
    landmark: Optional[str] = None
    ward: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None


class CreateIssueRequest(BaseModel):
    title: str = Field(min_length=5, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    category: IssueCategory
    severity: SeverityLevel = SeverityLevel.MEDIUM
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address_text: Optional[str] = Field(default=None, max_length=500)
    landmark: Optional[str] = Field(default=None, max_length=255)
    ward: Optional[str] = Field(default=None, max_length=100)
    city: Optional[str] = Field(default=None, max_length=100)
    pincode: Optional[str] = Field(default=None, max_length=10)


class UpdateIssueRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=5, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    category: Optional[IssueCategory] = None
    severity: Optional[SeverityLevel] = None


class IssueImageResponse(BaseModel):
    id: int
    image_type: str
    url: str
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: datetime


class StatusHistoryEntryResponse(BaseModel):
    from_status: Optional[IssueStatus] = None
    to_status: IssueStatus
    note: Optional[str] = None
    changed_by_name: Optional[str] = None
    created_at: datetime


class CreateCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    is_internal: bool = False


class CommentResponse(BaseModel):
    id: int
    author_name: str
    author_role: str
    body: str
    is_internal: bool
    created_at: datetime


class CreateFeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    rating: int
    comment: Optional[str] = None
    created_at: datetime


class IssueSummaryResponse(BaseModel):
    id: str
    reference_code: str
    title: str
    category: IssueCategory
    severity: SeverityLevel
    status: IssueStatus
    priority_level: PriorityLevel
    priority_score: float
    location: LocationResponse
    thumbnail_url: Optional[str] = None
    created_at: datetime
    department_name: Optional[str] = None


class PaginatedIssuesResponse(BaseModel):
    items: List[IssueSummaryResponse]
    total: int
    page: int
    page_size: int


class IssueDetailResponse(BaseModel):
    id: str
    reference_code: str
    title: str
    description: Optional[str] = None
    category: IssueCategory
    severity: SeverityLevel
    status: IssueStatus
    priority_level: PriorityLevel
    priority_score: float
    is_ai_verified: bool
    is_citizen_edited_category: bool
    location: LocationResponse
    department_name: Optional[str] = None
    reporter_name: str
    reporter_id: str
    images: List[IssueImageResponse]
    video_url: Optional[str] = None
    ai_prediction: Optional[AIPredictionSummary] = None
    status_history: List[StatusHistoryEntryResponse]
    comments: List[CommentResponse]
    feedback: Optional[FeedbackResponse] = None
    assigned_to_name: Optional[str] = None   # current field staff member, if any
    progress_percent: Optional[int] = None   # progress of the active assignment
    duplicate_count: int
    report_count: int = 1  # master + its duplicates, e.g. "Reports: 3"
    master_issue_id: Optional[str] = None  # set when this report is a duplicate
    master_reference_code: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
