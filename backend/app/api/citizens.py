from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.auth import require_citizen
from app.models.user import User
from app.schemas.profile import CitizenProfileResponse, ProfileImageResponse, UpdateCitizenProfileRequest
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/citizens", tags=["citizens"])


@router.get("/me", response_model=CitizenProfileResponse)
def get_my_profile(current_user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    return ProfileService(db).get_my_profile(current_user)


@router.put("/me", response_model=CitizenProfileResponse)
def update_my_profile(
    payload: UpdateCitizenProfileRequest,
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    return ProfileService(db).update_my_profile(current_user, payload)


@router.post("/me/profile-image", response_model=ProfileImageResponse)
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_citizen),
    db: Session = Depends(get_db),
):
    url = await ProfileService(db).update_profile_image(current_user, file)
    return ProfileImageResponse(message="Profile image updated.", profile_image_url=url)
