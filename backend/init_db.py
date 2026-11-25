"""Database initialization and baseline seed script."""
from sqlalchemy.orm import Session
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.core.enums import UserRole, IssueCategory, SeverityLevel
from app.models import (
    User,
    CitizenProfile,
    Department,
    IssueCategoryMapping,
    RiskZone,
)


def init_db():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # 1. Seed Departments if not exist
        if db.query(Department).count() == 0:
            print("Seeding departments...")
            departments = [
                Department(name="Roads & Infrastructure", code="ROADS", description="Road repairs, potholes, signs", sla_hours=48),
                Department(name="Solid Waste Management", code="SWM", description="Garbage collection and sanitation", sla_hours=24),
                Department(name="Electrical & Lighting", code="ELEC", description="Streetlights and public electrical infrastructure", sla_hours=36),
                Department(name="Water Supply & Sewerage", code="WATER", description="Drainage, water leaks, sewerage", sla_hours=24),
            ]
            db.add_all(departments)
            db.commit()

            # 2. Seed Issue Category Mappings
            roads_dept = db.query(Department).filter_by(code="ROADS").first()
            swm_dept = db.query(Department).filter_by(code="SWM").first()
            elec_dept = db.query(Department).filter_by(code="ELEC").first()
            water_dept = db.query(Department).filter_by(code="WATER").first()

            mappings = [
                IssueCategoryMapping(category=IssueCategory.POTHOLE.value, display_name="Pothole", department_id=roads_dept.id, default_severity=SeverityLevel.MEDIUM.value),
                IssueCategoryMapping(category=IssueCategory.DAMAGED_SIGN.value, display_name="Damaged Signboard", department_id=roads_dept.id, default_severity=SeverityLevel.LOW.value),
                IssueCategoryMapping(category=IssueCategory.CONSTRUCTION_OBSTRUCTION.value, display_name="Construction Obstruction", department_id=roads_dept.id, default_severity=SeverityLevel.MEDIUM.value),
                IssueCategoryMapping(category=IssueCategory.GARBAGE.value, display_name="Garbage Dump", department_id=swm_dept.id, default_severity=SeverityLevel.MEDIUM.value),
                IssueCategoryMapping(category=IssueCategory.ILLEGAL_DUMPING.value, display_name="Illegal Dumping", department_id=swm_dept.id, default_severity=SeverityLevel.HIGH.value),
                IssueCategoryMapping(category=IssueCategory.BROKEN_STREETLIGHT.value, display_name="Broken Streetlight", department_id=elec_dept.id, default_severity=SeverityLevel.LOW.value),
                IssueCategoryMapping(category=IssueCategory.WATER_LEAKAGE.value, display_name="Water Pipeline Leakage", department_id=water_dept.id, default_severity=SeverityLevel.HIGH.value),
                IssueCategoryMapping(category=IssueCategory.DRAINAGE.value, display_name="Blocked Drainage", department_id=water_dept.id, default_severity=SeverityLevel.HIGH.value),
                IssueCategoryMapping(category=IssueCategory.WATERLOGGING.value, display_name="Waterlogging", department_id=water_dept.id, default_severity=SeverityLevel.HIGH.value),
                IssueCategoryMapping(category=IssueCategory.FALLEN_TREE.value, display_name="Fallen Tree / Branch", department_id=roads_dept.id, default_severity=SeverityLevel.HIGH.value),
                IssueCategoryMapping(category=IssueCategory.OTHER.value, display_name="Other Issue", department_id=roads_dept.id, default_severity=SeverityLevel.LOW.value),
            ]
            db.add_all(mappings)
            db.commit()
            print("Departments and category mappings seeded.")

        # 3. Seed Risk Zones
        if db.query(RiskZone).count() == 0:
            print("Seeding sample risk zones...")
            risk_zones = [
                RiskZone(zone_type="HOSPITAL", name="City Central Hospital", latitude=12.9716, longitude=77.5946, radius_meters=300.0, risk_weight=15.0),
                RiskZone(zone_type="SCHOOL", name="St. Mary's Public School", latitude=12.9750, longitude=77.5990, radius_meters=200.0, risk_weight=12.0),
                RiskZone(zone_type="MAJOR_ROAD", name="MG Road Junction", latitude=12.9740, longitude=77.6010, radius_meters=150.0, risk_weight=10.0),
            ]
            db.add_all(risk_zones)
            db.commit()
            print("Risk zones seeded.")

        # Add perceptual_hash column to issue_images if missing in existing SQLite database
        try:
            db.execute("ALTER TABLE issue_images ADD COLUMN perceptual_hash VARCHAR(16)")
            db.commit()
        except Exception:
            db.rollback()

        # 4. Seed demo citizen user if none exists
        demo_email = "citizen@example.com"
        if not db.query(User).filter_by(email=demo_email).first():
            print("Seeding demo citizen user...")
            user = User(
                full_name="Demo Citizen",
                email=demo_email,
                phone_number="+919876543210",
                hashed_password=hash_password("Password123!"),
                role=UserRole.CITIZEN,
                is_email_verified=True,
                is_phone_verified=True,
            )
            db.add(user)
            db.flush()
            profile = CitizenProfile(user_id=user.id)
            db.add(profile)
            db.commit()
            print("Demo user created: citizen@example.com / Password123!")

        # 5. Seed demo admin user if none exists
        admin_email = "admin@example.com"
        if not db.query(User).filter_by(email=admin_email).first():
            print("Seeding demo admin user...")
            admin_user = User(
                full_name="Department Admin",
                email=admin_email,
                phone_number="+919876543211",
                hashed_password=hash_password("Password123!"),
                role=UserRole.DEPARTMENT_ADMIN,
                is_email_verified=True,
                is_phone_verified=True,
            )
            db.add(admin_user)
            db.commit()
            print("Demo admin created: admin@example.com / Password123!")

        print("Database initialization complete.")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
