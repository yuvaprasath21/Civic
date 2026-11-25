from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.profile import CitizenProfile


class CitizenProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id: int) -> Optional[CitizenProfile]:
        stmt = select(CitizenProfile).where(CitizenProfile.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def save(self, profile: CitizenProfile) -> CitizenProfile:
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
