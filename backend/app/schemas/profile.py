from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CitizenProfileResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone_number: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_active: bool
    is_email_verified: bool
    created_at: datetime

    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    default_latitude: Optional[float] = None
    default_longitude: Optional[float] = None
    total_reports_submitted: int
    reputation_score: int


class UpdateCitizenProfileRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    address_line: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    pincode: Optional[str] = Field(default=None, max_length=10)
    default_latitude: Optional[float] = None
    default_longitude: Optional[float] = None


class ProfileImageResponse(BaseModel):
    success: bool = True
    message: str
    profile_image_url: str
