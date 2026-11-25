"""
Create staff / admin accounts from the command line.

Citizens self-register; field staff and admins can't. Until the Phase 9
admin UI exists, this is how you create them:

    python -m app.utils.create_user --role FIELD_STAFF --email ravi@city.gov.in \\
        --name "Ravi Kumar" --department ROADS
    python -m app.utils.create_user --role DEPARTMENT_ADMIN --email admin@city.gov.in --name "Asha Menon"

The password is prompted for (not echoed) unless --password is given;
avoid --password on shared machines since it lands in shell history.
"""
import argparse
import getpass
import sys
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.security import hash_password
from app.models.department import Department
from app.models.profile import StaffProfile
from app.models.user import User


class CreateUserError(Exception):
    pass


def create_user(
    db: Session,
    *,
    role: UserRole,
    email: str,
    full_name: str,
    password: str,
    phone_number: Optional[str] = None,
    department_code: Optional[str] = None,
    employee_code: Optional[str] = None,
    designation: Optional[str] = None,
) -> User:
    if role == UserRole.CITIZEN:
        raise CreateUserError("Citizens register themselves; use POST /api/auth/register.")
    if len(password) < 8 or not any(c.isdigit() for c in password) or not any(c.isalpha() for c in password):
        raise CreateUserError("Password must be at least 8 characters with a letter and a digit.")

    email = email.lower().strip()
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        raise CreateUserError(f"A user with email {email} already exists.")

    department: Optional[Department] = None
    if department_code:
        department = db.execute(select(Department).where(Department.code == department_code.upper())).scalar_one_or_none()
        if department is None:
            raise CreateUserError(f"No department with code '{department_code}'. Create it first.")

    user = User(
        full_name=full_name.strip(), email=email, phone_number=phone_number,
        hashed_password=hash_password(password), role=role, is_email_verified=True,
    )
    db.add(user)
    db.flush()

    if role == UserRole.FIELD_STAFF:
        code = employee_code or f"EMP-{user.id:04d}"
        if db.execute(select(StaffProfile).where(StaffProfile.employee_code == code)).scalar_one_or_none():
            raise CreateUserError(f"Employee code {code} is already in use.")
        db.add(
            StaffProfile(
                user_id=user.id, department_id=department.id if department else None,
                employee_code=code, designation=designation,
            )
        )
    db.commit()
    db.refresh(user)
    return user


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Create a field staff or admin account.")
    parser.add_argument("--role", required=True, choices=[r.value for r in UserRole if r != UserRole.CITIZEN])
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--phone")
    parser.add_argument("--department", help="Department code, e.g. ROADS (field staff)")
    parser.add_argument("--employee-code")
    parser.add_argument("--designation")
    parser.add_argument("--password", help="Prompted if omitted (recommended).")
    args = parser.parse_args(argv)

    password = args.password or getpass.getpass("Password: ")
    from app.core.database import SessionLocal

    with SessionLocal() as db:
        try:
            user = create_user(
                db, role=UserRole(args.role), email=args.email, full_name=args.name, password=password,
                phone_number=args.phone, department_code=args.department,
                employee_code=args.employee_code, designation=args.designation,
            )
        except CreateUserError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    print(f"Created {user.role.value} {user.email} (id {user.uuid}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
