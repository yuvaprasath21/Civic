from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.models.profile import CitizenProfile
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.get(User, user_id)

    def get_by_uuid(self, user_uuid: str) -> Optional[User]:
        stmt = select(User).where(User.uuid == user_uuid, User.is_deleted.is_(False))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower(), User.is_deleted.is_(False))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_reset_token(self, hashed_token: str) -> Optional[User]:
        stmt = select(User).where(User.reset_token == hashed_token, User.is_deleted.is_(False))
        return self.db.execute(stmt).scalar_one_or_none()

    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    def create_citizen(self, *, full_name: str, email: str, phone_number: Optional[str], hashed_password: str) -> User:
        user = User(
            full_name=full_name.strip(),
            email=email.lower().strip(),
            phone_number=phone_number,
            hashed_password=hashed_password,
            role=UserRole.CITIZEN,
        )
        self.db.add(user)
        self.db.flush()

        profile = CitizenProfile(user_id=user.id)
        self.db.add(profile)

        self.db.commit()
        self.db.refresh(user)
        return user

    def set_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(timezone.utc)
        self.db.add(user)
        self.db.commit()

    def set_reset_token(self, user: User, hashed_token: Optional[str], expires_at: Optional[datetime]) -> None:
        user.reset_token = hashed_token
        user.reset_token_expires_at = expires_at
        self.db.add(user)
        self.db.commit()

    def update_password(self, user: User, hashed_password: str) -> None:
        user.hashed_password = hashed_password
        user.reset_token = None
        user.reset_token_expires_at = None
        self.db.add(user)
        self.db.commit()
