from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import UserRole
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import TokenError, safe_decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Authentication required.", error_code="MISSING_TOKEN")

    try:
        payload = safe_decode_token(credentials.credentials)
    except TokenError:
        raise UnauthorizedError("Invalid or expired token.", error_code="INVALID_TOKEN")

    if payload.get("type") != "access":
        raise UnauthorizedError("Token is not an access token.", error_code="INVALID_TOKEN")

    user = UserRepository(db).get_by_uuid(payload.get("sub", ""))
    if user is None:
        raise UnauthorizedError("Account no longer exists.", error_code="ACCOUNT_NOT_FOUND")
    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated.", error_code="ACCOUNT_DEACTIVATED")

    return user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError(
                "You do not have permission to perform this action.", error_code="INSUFFICIENT_PERMISSIONS"
            )
        return current_user

    return _dependency


require_citizen = require_roles(UserRole.CITIZEN)
require_field_staff = require_roles(UserRole.FIELD_STAFF)
require_department_admin = require_roles(UserRole.DEPARTMENT_ADMIN, UserRole.SUPER_ADMIN)
require_super_admin = require_roles(UserRole.SUPER_ADMIN)
require_any_admin = require_roles(UserRole.DEPARTMENT_ADMIN, UserRole.SUPER_ADMIN)
require_staff_or_admin = require_roles(UserRole.FIELD_STAFF, UserRole.DEPARTMENT_ADMIN, UserRole.SUPER_ADMIN)
