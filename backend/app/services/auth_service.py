import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError, ValidationAppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    safe_decode_token,
    verify_password,
    TokenError,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from app.services.audit_service import AuditService

RESET_TOKEN_TTL_MINUTES = 30


def _hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditService(db)

    def register(self, payload: RegisterRequest, ip_address: Optional[str] = None) -> TokenResponse:
        if self.users.email_exists(payload.email):
            raise ConflictError("An account with this email already exists.", error_code="EMAIL_ALREADY_REGISTERED")

        user = self.users.create_citizen(
            full_name=payload.full_name,
            email=payload.email,
            phone_number=payload.phone_number,
            hashed_password=hash_password(payload.password),
        )

        self.audit.record(
            actor_id=user.id, action="USER_REGISTERED", entity_type="user", entity_id=user.id, ip_address=ip_address
        )

        return self._issue_tokens(user)

    def login(self, email: str, password: str, ip_address: Optional[str] = None) -> TokenResponse:
        user = self.users.get_by_email(email)

        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.", error_code="INVALID_CREDENTIALS")

        if not user.is_active:
            raise UnauthorizedError("This account has been deactivated.", error_code="ACCOUNT_DEACTIVATED")

        self.users.set_last_login(user)
        self.audit.record(
            actor_id=user.id, action="USER_LOGIN", entity_type="user", entity_id=user.id, ip_address=ip_address
        )

        return self._issue_tokens(user)

    def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = safe_decode_token(refresh_token)
        except TokenError:
            raise UnauthorizedError("Invalid or expired refresh token.", error_code="INVALID_REFRESH_TOKEN")

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Token is not a refresh token.", error_code="INVALID_REFRESH_TOKEN")

        user = self.users.get_by_uuid(payload.get("sub", ""))
        if user is None or not user.is_active:
            raise UnauthorizedError("Account not found or inactive.", error_code="INVALID_REFRESH_TOKEN")

        return self._issue_tokens(user)

    def forgot_password(self, email: str) -> Optional[str]:
        user = self.users.get_by_email(email)
        if user is None:
            return None

        raw_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
        self.users.set_reset_token(user, _hash_reset_token(raw_token), expires_at)

        self.audit.record(actor_id=user.id, action="PASSWORD_RESET_REQUESTED", entity_type="user", entity_id=user.id)
        return raw_token

    def reset_password(self, token: str, new_password: str) -> None:
        hashed = _hash_reset_token(token)
        user = self.users.get_by_reset_token(hashed)

        if user is None:
            raise ValidationAppError("Invalid or expired reset token.", error_code="INVALID_RESET_TOKEN")

        expires_at = user.reset_token_expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at is None or expires_at < datetime.now(timezone.utc):
            raise ValidationAppError("Invalid or expired reset token.", error_code="INVALID_RESET_TOKEN")

        self.users.update_password(user, hash_password(new_password))
        self.audit.record(actor_id=user.id, action="PASSWORD_RESET_COMPLETED", entity_type="user", entity_id=user.id)

    def _issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(subject=user.uuid, role=user.role.value)
        refresh_token = create_refresh_token(subject=user.uuid, role=user.role.value)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=to_user_response(user),
        )


def to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.uuid,
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        role=user.role,
        profile_image_url=user.profile_image_url,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        is_phone_verified=user.is_phone_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )
