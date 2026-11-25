from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.profile_repository import CitizenProfileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.profile import CitizenProfileResponse, UpdateCitizenProfileRequest
from app.services.audit_service import AuditService
from app.utils.file_upload import save_uploaded_image


class ProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.profiles = CitizenProfileRepository(db)
        self.audit = AuditService(db)

    def get_my_profile(self, user: User) -> CitizenProfileResponse:
        profile = self.profiles.get_by_user_id(user.id)
        if profile is None:
            raise NotFoundError("Citizen profile not found.", error_code="PROFILE_NOT_FOUND")
        return self._to_response(user, profile)

    def update_my_profile(self, user: User, payload: UpdateCitizenProfileRequest) -> CitizenProfileResponse:
        profile = self.profiles.get_by_user_id(user.id)
        if profile is None:
            raise NotFoundError("Citizen profile not found.", error_code="PROFILE_NOT_FOUND")

        data = payload.model_dump(exclude_unset=True)

        if "full_name" in data and data["full_name"] is not None:
            user.full_name = data.pop("full_name").strip()
        else:
            data.pop("full_name", None)

        if "phone_number" in data:
            user.phone_number = data.pop("phone_number")

        for field in ("address_line", "city", "state", "pincode", "default_latitude", "default_longitude"):
            if field in data:
                setattr(profile, field, data[field])

        self.db.add(user)
        profile = self.profiles.save(profile)

        self.audit.record(actor_id=user.id, action="PROFILE_UPDATED", entity_type="user", entity_id=user.id)

        return self._to_response(user, profile)

    async def update_profile_image(self, user: User, file: UploadFile) -> str:
        saved = await save_uploaded_image(file, subdirectory="profile_images")
        user.profile_image_url = saved.url
        self.db.add(user)
        self.db.commit()

        self.audit.record(
            actor_id=user.id,
            action="PROFILE_IMAGE_UPDATED",
            entity_type="user",
            entity_id=user.id,
            details={"size_bytes": saved.size_bytes, "content_type": saved.content_type},
        )
        return saved.url

    @staticmethod
    def _to_response(user: User, profile) -> CitizenProfileResponse:
        return CitizenProfileResponse(
            id=user.uuid,
            full_name=user.full_name,
            email=user.email,
            phone_number=user.phone_number,
            profile_image_url=user.profile_image_url,
            is_active=user.is_active,
            is_email_verified=user.is_email_verified,
            created_at=user.created_at,
            address_line=profile.address_line,
            city=profile.city,
            state=profile.state,
            pincode=profile.pincode,
            default_latitude=profile.default_latitude,
            default_longitude=profile.default_longitude,
            total_reports_submitted=profile.total_reports_submitted,
            reputation_score=profile.reputation_score,
        )
