"""Read-only staff directory for assigning work. Staff management (create, edit,
activate/deactivate, performance) arrives with the Phase 9 admin tools."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import UserRole
from app.middleware.auth import require_any_admin
from app.models.user import User
from app.schemas.admin_issue import StaffListItem

router = APIRouter(prefix="/admin/staff", tags=["admin-staff"])


@router.get("", response_model=List[StaffListItem])
def list_staff(admin: User = Depends(require_any_admin), db: Session = Depends(get_db)):
    users = db.execute(
        select(User).where(User.role == UserRole.FIELD_STAFF, User.is_deleted.is_(False)).order_by(User.full_name)
    ).scalars().all()
    items = []
    for u in users:
        p = u.staff_profile
        items.append(
            StaffListItem(
                id=u.uuid, full_name=u.full_name, email=u.email,
                employee_code=p.employee_code if p else None,
                department_name=p.department.name if p and p.department else None,
                is_active=u.is_active, is_available=p.is_available if p else False,
                current_workload=p.current_workload if p else 0, total_resolved=p.total_resolved_count if p else 0,
            )
        )
    return items
