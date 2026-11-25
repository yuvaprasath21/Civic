from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import IssueCategory, IssueStatus, SeverityLevel
from app.middleware.auth import get_current_user, require_citizen
from app.models.user import User
from app.schemas.issue import (
    CommentResponse,
    CreateCommentRequest,
    CreateFeedbackRequest,
    CreateIssueRequest,
    FeedbackResponse,
    IssueDetailResponse,
    PaginatedIssuesResponse,
    UpdateIssueRequest,
)
from app.services.issue_service import IssueService

router = APIRouter(tags=["issues"])


@router.post("/issues", response_model=IssueDetailResponse, status_code=201)
async def create_issue(
    title: str = Form(..., min_length=5, max_length=200),
    description: Optional[str] = Form(default=None),
    category: IssueCategory = Form(...),
    severity: SeverityLevel = Form(default=SeverityLevel.MEDIUM),
    latitude: float = Form(...),
    longitude: float = Form(...),
    address_text: Optional[str] = Form(default=None),
    landmark: Optional[str] = Form(default=None),
    ward: Optional[str] = Form(default=None),
    city: Optional[str] = Form(default=None),
    pincode: Optional[str] = Form(default=None),
    images: List[UploadFile] = File(...),
    video: Optional[UploadFile] = File(default=None),
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    payload = CreateIssueRequest(
        title=title,
        description=description,
        category=category,
        severity=severity,
        latitude=latitude,
        longitude=longitude,
        address_text=address_text,
        landmark=landmark,
        ward=ward,
        city=city,
        pincode=pincode,
    )
    return await IssueService(db).create_issue(current_user, payload, images, video)


@router.get("/issues", response_model=PaginatedIssuesResponse)
def list_issues(
    category: Optional[IssueCategory] = None,
    status: Optional[IssueStatus] = None,
    severity: Optional[SeverityLevel] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).list_issues(
        current_user=current_user,
        only_mine=False,
        category=category,
        status=status,
        severity=severity,
        city=city,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/issues/nearby", response_model=PaginatedIssuesResponse)
def list_nearby_issues(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=2.0, gt=0, le=50),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).list_nearby(
        latitude=latitude, longitude=longitude, radius_km=radius_km, page=page, page_size=page_size
    )


@router.get("/my/issues", response_model=PaginatedIssuesResponse)
def list_my_issues(
    status: Optional[IssueStatus] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    return IssueService(db).list_issues(
        current_user=current_user, only_mine=True, status=status, page=page, page_size=page_size
    )


@router.get("/issues/{issue_uuid}", response_model=IssueDetailResponse)
def get_issue(issue_uuid: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return IssueService(db).get_issue(issue_uuid, current_user)


@router.put("/issues/{issue_uuid}", response_model=IssueDetailResponse)
def update_issue(
    issue_uuid: str,
    payload: UpdateIssueRequest,
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    return IssueService(db).update_issue(issue_uuid, current_user, payload)


@router.post("/issues/{issue_uuid}/comments", response_model=CommentResponse, status_code=201)
def add_comment(
    issue_uuid: str,
    payload: CreateCommentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return IssueService(db).add_comment(issue_uuid, current_user, payload)


@router.post("/issues/{issue_uuid}/feedback", response_model=FeedbackResponse, status_code=201)
def add_feedback(
    issue_uuid: str,
    payload: CreateFeedbackRequest,
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    return IssueService(db).add_feedback(issue_uuid, current_user, payload)
