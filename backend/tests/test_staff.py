"""
Phase 8: assignment + field-staff workflow (accept, start, notes, progress,
before/after photos, resolve) and the rules around it.
"""
import io

import pytest
from PIL import Image

from app.core.enums import UserRole

LAT, LON = 26.8467, 80.9462


def _png(color=(120, 60, 60)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (80, 80), color).save(buf, format="PNG")
    return buf.getvalue()


def _h(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _uploads(monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))


# ------------------------------------------------------------------ helpers
def _make_user(db, client, *, role, email, name, department=None, available=True, active=True, profile=True):
    from app.core.security import hash_password
    from app.models.profile import StaffProfile
    from app.models.user import User

    user = User(full_name=name, email=email, hashed_password=hash_password("StrongPass123"), role=role, is_active=active)
    db.add(user)
    db.flush()
    if role == UserRole.FIELD_STAFF and profile:
        db.add(
            StaffProfile(
                user_id=user.id, employee_code=f"EMP-{user.id:04d}", is_available=available,
                department_id=department.id if department else None,
            )
        )
    db.commit()
    r = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123"})
    token = r.json().get("access_token") if r.status_code == 200 else None
    return user, token


def _department(db, code="ROADS", name="Roads"):
    from app.models.department import Department

    d = Department(name=name, code=code)
    db.add(d)
    db.commit()
    return d


@pytest.fixture()
def admin(client, db_session):
    return _make_user(db_session, client, role=UserRole.DEPARTMENT_ADMIN, email="admin@example.com", name="Dept Admin")


@pytest.fixture()
def staff(client, db_session):
    return _make_user(db_session, client, role=UserRole.FIELD_STAFF, email="ravi@example.com", name="Ravi Kumar")


@pytest.fixture()
def staff2(client, db_session):
    return _make_user(db_session, client, role=UserRole.FIELD_STAFF, email="sunita@example.com", name="Sunita Rao")


@pytest.fixture()
def citizen(client):
    r = client.post("/api/auth/register", json={"full_name": "Meera Iyer", "email": "meera@example.com", "password": "SecurePass123"})
    return r.json()["access_token"]


_counter = {"n": 0}


def _report(client, token, *, severity="MEDIUM", category="POTHOLE"):
    """Each report goes to its own far-apart location so duplicate detection never links them."""
    _counter["n"] += 1
    r = client.post(
        "/api/issues",
        data={
            "title": f"Issue number {_counter['n']} on the road", "category": category, "severity": severity,
            "latitude": LAT + _counter["n"] * 0.05, "longitude": LON,
        },
        files=[("images", ("p.png", _png(), "image/png"))],
        headers=_h(token),
    )
    assert r.status_code == 201, r.text
    return r.json()


def _verified_issue(client, citizen, admin, **kw):
    issue = _report(client, citizen, **kw)
    r = client.put(f"/api/admin/issues/{issue['id']}/verify", headers=_h(admin[1]))
    assert r.status_code == 200, r.text
    return issue


def _assigned_issue(client, citizen, admin, staff, **kw):
    issue = _verified_issue(client, citizen, admin, **kw)
    r = client.put(f"/api/admin/issues/{issue['id']}/assign", json={"staff_id": staff[0].uuid}, headers=_h(admin[1]))
    assert r.status_code == 200, r.text
    return issue


def _accepted(client, citizen, admin, staff, **kw):
    issue = _assigned_issue(client, citizen, admin, staff, **kw)
    assert client.put(f"/api/staff/issues/{issue['id']}/accept", headers=_h(staff[1])).status_code == 200
    return issue


def _in_progress(client, citizen, admin, staff, **kw):
    issue = _accepted(client, citizen, admin, staff, **kw)
    assert client.put(f"/api/staff/issues/{issue['id']}/start", headers=_h(staff[1])).status_code == 200
    return issue


def _photo(client, token, issue_id, image_type, n=1, content=None, content_type="image/png"):
    files = [("images", (f"w{i}.png", content or _png((i * 40 % 255, 90, 90)), content_type)) for i in range(n)]
    return client.post(f"/api/staff/issues/{issue_id}/photos", data={"image_type": image_type}, files=files, headers=_h(token))


def _detail(client, token, issue_id):
    return client.get(f"/api/issues/{issue_id}", headers=_h(token)).json()


def _notifications(db, user, type_):
    from app.models.notification import Notification

    return db.query(Notification).filter(Notification.recipient_id == user.id, Notification.type == type_).count()


def _audit(db, action):
    from app.models.notification import AuditLog

    return db.query(AuditLog).filter(AuditLog.action == action).count()


# ================================================================ authorization
def test_staff_endpoints_require_staff_role(client, citizen, admin):
    assert client.get("/api/staff/issues").status_code == 401
    assert client.get("/api/staff/issues", headers=_h(citizen)).status_code == 403
    assert client.get("/api/staff/issues", headers=_h(admin[1])).status_code == 403


def test_admin_assignment_endpoints_require_admin(client, citizen, staff):
    issue = _report(client, citizen)
    assert client.put(f"/api/admin/issues/{issue['id']}/verify", headers=_h(citizen)).status_code == 403
    assert client.put(f"/api/admin/issues/{issue['id']}/verify", headers=_h(staff[1])).status_code == 403
    assert client.put(f"/api/admin/issues/{issue['id']}/assign", json={"staff_id": staff[0].uuid}, headers=_h(staff[1])).status_code == 403
    assert client.get("/api/admin/staff", headers=_h(citizen)).status_code == 403


# ================================================================ verify
def test_verify_moves_issue_to_verified_and_notifies(client, db_session, citizen, admin):
    issue = _report(client, citizen)
    r = client.put(f"/api/admin/issues/{issue['id']}/verify", json={"note": "Looks valid"}, headers=_h(admin[1]))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "VERIFIED" and body["is_ai_verified"] is True
    assert body["status_history"][-1]["note"] == "Looks valid"
    assert _audit(db_session, "ISSUE_VERIFIED") == 1


def test_verify_twice_and_verify_of_flagged_duplicate_are_rejected(client, citizen, admin):
    issue = _verified_issue(client, citizen, admin)
    r = client.put(f"/api/admin/issues/{issue['id']}/verify", headers=_h(admin[1]))
    assert r.status_code == 409 and r.json()["error_code"] == "INVALID_STATUS_TRANSITION"

    # a report filed ~on top of an existing one is flagged POTENTIAL_DUPLICATE and can't be verified yet
    first = _report(client, citizen)
    dup = client.post(
        "/api/issues",
        data={"title": "Same pothole again", "category": "POTHOLE", "severity": "LOW",
              "latitude": LAT + _counter["n"] * 0.05 + 0.0001, "longitude": LON},
        files=[("images", ("p.png", _png(), "image/png"))], headers=_h(citizen),
    ).json()
    assert dup["status"] == "POTENTIAL_DUPLICATE" and first["id"]
    r = client.put(f"/api/admin/issues/{dup['id']}/verify", headers=_h(admin[1]))
    assert r.status_code == 409


# ================================================================ assign
def test_assign_requires_a_verified_issue(client, citizen, admin, staff):
    issue = _report(client, citizen)  # AI_ANALYZED, not verified
    r = client.put(f"/api/admin/issues/{issue['id']}/assign", json={"staff_id": staff[0].uuid}, headers=_h(admin[1]))
    assert r.status_code == 409 and r.json()["error_code"] == "INVALID_STATUS_TRANSITION"


def test_assign_creates_pending_assignment_and_notifies_everyone(client, db_session, citizen, admin, staff):
    issue = _assigned_issue(client, citizen, admin, staff)
    detail = _detail(client, citizen, issue["id"])
    assert detail["status"] == "ASSIGNED"
    assert detail["assigned_to_name"] == "Ravi Kumar"
    assert detail["status_history"][-1]["note"] == "Assigned to Ravi Kumar."

    db_session.refresh(staff[0])
    assert staff[0].staff_profile.current_workload == 1
    assert _notifications(db_session, staff[0], "ISSUE_ASSIGNED") == 1
    assert _audit(db_session, "ISSUE_ASSIGNED") == 1

    listing = client.get("/api/admin/staff", headers=_h(admin[1])).json()
    assert listing[0]["full_name"] == "Ravi Kumar" and listing[0]["current_workload"] == 1


@pytest.mark.parametrize(
    "kwargs, status, code",
    [
        ({"active": False}, 409, "STAFF_INACTIVE"),
        ({"available": False}, 409, "STAFF_UNAVAILABLE"),
        ({"profile": False}, 422, "STAFF_PROFILE_MISSING"),
    ],
)
def test_assign_rejects_unusable_staff(client, db_session, citizen, admin, kwargs, status, code):
    bad = _make_user(db_session, client, role=UserRole.FIELD_STAFF, email="bad@example.com", name="Bad Staff", **kwargs)
    issue = _verified_issue(client, citizen, admin)
    r = client.put(f"/api/admin/issues/{issue['id']}/assign", json={"staff_id": bad[0].uuid}, headers=_h(admin[1]))
    assert r.status_code == status and r.json()["error_code"] == code


def test_assign_rejects_non_staff_and_unknown_users(client, citizen, admin):
    issue = _verified_issue(client, citizen, admin)
    me = client.get("/api/auth/me", headers=_h(citizen)).json()["id"]
    r = client.put(f"/api/admin/issues/{issue['id']}/assign", json={"staff_id": me}, headers=_h(admin[1]))
    assert r.status_code == 422 and r.json()["error_code"] == "NOT_FIELD_STAFF"
    r = client.put(f"/api/admin/issues/{issue['id']}/assign", json={"staff_id": "nope"}, headers=_h(admin[1]))
    assert r.status_code == 404 and r.json()["error_code"] == "STAFF_NOT_FOUND"


def test_assign_enforces_department_match_and_fills_missing_department(client, db_session, citizen, admin):
    from app.models.civic_issue import CivicIssue

    roads, water = _department(db_session, "ROADS", "Roads"), _department(db_session, "WATER", "Water Supply")
    water_staff = _make_user(db_session, client, role=UserRole.FIELD_STAFF, email="w@example.com", name="Water Man", department=water)
    roads_staff = _make_user(db_session, client, role=UserRole.FIELD_STAFF, email="r@example.com", name="Road Man", department=roads)

    issue = _verified_issue(client, citizen, admin)
    row = db_session.query(CivicIssue).filter(CivicIssue.uuid == issue["id"]).one()
    row.department_id = roads.id
    db_session.commit()

    r = client.put(f"/api/admin/issues/{issue['id']}/assign", json={"staff_id": water_staff[0].uuid}, headers=_h(admin[1]))
    assert r.status_code == 409 and r.json()["error_code"] == "DEPARTMENT_MISMATCH"

    # an issue with no department adopts the assignee's department
    other = _verified_issue(client, citizen, admin)
    assert client.put(f"/api/admin/issues/{other['id']}/assign", json={"staff_id": water_staff[0].uuid}, headers=_h(admin[1])).status_code == 200
    assert _detail(client, citizen, other["id"])["department_name"] == "Water Supply"
    assert roads_staff[0].id


def test_assigning_same_staff_twice_is_rejected(client, citizen, admin, staff):
    issue = _assigned_issue(client, citizen, admin, staff)
    r = client.put(f"/api/admin/issues/{issue['id']}/assign", json={"staff_id": staff[0].uuid}, headers=_h(admin[1]))
    assert r.status_code == 409 and r.json()["error_code"] == "ALREADY_ASSIGNED"


# ================================================================ reassign
def test_reassign_before_acceptance_hands_over_cleanly(client, db_session, citizen, admin, staff, staff2):
    issue = _assigned_issue(client, citizen, admin, staff)
    r = client.put(f"/api/admin/issues/{issue['id']}/assign", json={"staff_id": staff2[0].uuid}, headers=_h(admin[1]))
    assert r.status_code == 200

    db_session.refresh(staff[0]); db_session.refresh(staff2[0])
    assert staff[0].staff_profile.current_workload == 0 and staff2[0].staff_profile.current_workload == 1
    assert _detail(client, citizen, issue["id"])["assigned_to_name"] == "Sunita Rao"
    assert _notifications(db_session, staff[0], "ASSIGNMENT_CHANGED") == 1
    assert _audit(db_session, "ISSUE_REASSIGNED") == 1

    # the previous owner can no longer act; the new one can
    assert client.put(f"/api/staff/issues/{issue['id']}/accept", headers=_h(staff[1])).status_code == 403
    assert client.put(f"/api/staff/issues/{issue['id']}/accept", headers=_h(staff2[1])).status_code == 200
    # ...and the old assignment shows up in the previous owner's history
    hist = client.get("/api/staff/history", headers=_h(staff[1])).json()
    assert hist["total"] == 1 and hist["items"][0]["assignment_status"] == "REASSIGNED"


def test_reassign_mid_work_sends_the_issue_back_to_assigned(client, citizen, admin, staff, staff2):
    issue = _in_progress(client, citizen, admin, staff)
    assert client.put(f"/api/admin/issues/{issue['id']}/assign", json={"staff_id": staff2[0].uuid}, headers=_h(admin[1])).status_code == 200
    detail = _detail(client, citizen, issue["id"])
    assert detail["status"] == "ASSIGNED" and detail["assigned_to_name"] == "Sunita Rao"
    assert client.put(f"/api/staff/issues/{issue['id']}/resolve", headers=_h(staff[1])).status_code == 403


# ================================================================ staff worklist
def test_worklist_shows_only_my_active_work_most_urgent_first(client, citizen, admin, staff, staff2):
    low = _assigned_issue(client, citizen, admin, staff, severity="LOW")
    crit = _assigned_issue(client, citizen, admin, staff, severity="CRITICAL")
    high = _assigned_issue(client, citizen, admin, staff, severity="HIGH")
    _assigned_issue(client, citizen, admin, staff2, severity="CRITICAL")  # someone else's

    body = client.get("/api/staff/issues", headers=_h(staff[1])).json()
    assert body["total"] == 3
    assert [i["id"] for i in body["items"]] == [crit["id"], high["id"], low["id"]]
    assert all(i["assignment_status"] == "PENDING" for i in body["items"])

    only_high = client.get("/api/staff/issues?priority=HIGH", headers=_h(staff[1])).json()
    assert [i["id"] for i in only_high["items"]] == [high["id"]]

    client.put(f"/api/staff/issues/{crit['id']}/accept", headers=_h(staff[1]))
    accepted = client.get("/api/staff/issues?status=ACCEPTED", headers=_h(staff[1])).json()
    assert [i["id"] for i in accepted["items"]] == [crit["id"]]


# ================================================================ the happy path
def test_full_field_workflow_end_to_end(client, db_session, citizen, admin, staff):
    issue = _assigned_issue(client, citizen, admin, staff, severity="HIGH")
    iid, tok = issue["id"], staff[1]

    assert client.put(f"/api/staff/issues/{iid}/accept", headers=_h(tok)).json()["issue_status"] == "ACCEPTED"
    assert _photo(client, tok, iid, "BEFORE_WORK", n=2).status_code == 201
    assert client.put(f"/api/staff/issues/{iid}/start", headers=_h(tok)).json()["assignment_status"] == "IN_PROGRESS"

    r = client.post(f"/api/staff/issues/{iid}/notes", json={"body": "Needs two bags of asphalt"}, headers=_h(tok))
    assert r.status_code == 201 and r.json()["is_internal"] is True

    r = client.put(f"/api/staff/issues/{iid}/progress", json={"percent": 60, "note": "Surface cleared"}, headers=_h(tok))
    assert r.status_code == 200 and r.json()["progress_percent"] == 60
    assert _detail(client, citizen, iid)["progress_percent"] == 60

    assert _photo(client, tok, iid, "AFTER_WORK").status_code == 201
    r = client.put(f"/api/staff/issues/{iid}/resolve", json={"notes": "Patched and compacted"}, headers=_h(tok))
    assert r.status_code == 200
    assert r.json()["issue_status"] == "RESOLVED" and r.json()["assignment_status"] == "COMPLETED"

    detail = _detail(client, citizen, iid)
    assert detail["status"] == "RESOLVED" and detail["resolved_at"] is not None
    assert [h["to_status"] for h in detail["status_history"]] == [
        "REPORTED", "AI_ANALYZED", "VERIFIED", "ASSIGNED", "ACCEPTED", "IN_PROGRESS", "RESOLVED",
    ]
    types = sorted(i["image_type"] for i in detail["images"])
    assert types == ["AFTER_WORK", "BEFORE_WORK", "BEFORE_WORK", "REPORT"]
    assert detail["assigned_to_name"] is None  # no longer active

    # stats and notifications
    db_session.refresh(staff[0])
    profile = staff[0].staff_profile
    assert profile.current_workload == 0 and profile.total_resolved_count == 1
    assert profile.average_resolution_hours is not None and profile.average_resolution_hours >= 0
    me = client.get("/api/staff/me", headers=_h(tok)).json()
    assert me["total_resolved"] == 1 and me["current_workload"] == 0
    assert _notifications(db_session, citizen_user(db_session), "WORK_STARTED") == 1
    assert _notifications(db_session, citizen_user(db_session), "ISSUE_RESOLVED") == 1
    for action in ("ASSIGNMENT_ACCEPTED", "WORK_STARTED", "ISSUE_RESOLVED"):
        assert _audit(db_session, action) == 1

    # work history + leaves the active list
    assert client.get("/api/staff/issues", headers=_h(tok)).json()["total"] == 0
    hist = client.get("/api/staff/history", headers=_h(tok)).json()
    assert hist["total"] == 1 and hist["items"][0]["assignment_status"] == "COMPLETED"

    # business rule 10: the citizen can now rate it
    r = client.post(f"/api/issues/{iid}/feedback", json={"rating": 5}, headers=_h(citizen))
    assert r.status_code == 201


def citizen_user(db):
    from app.models.user import User
    return db.query(User).filter(User.email == "meera@example.com").one()


# ================================================================ rules
def test_status_cannot_skip_steps(client, citizen, admin, staff):
    issue = _assigned_issue(client, citizen, admin, staff)
    iid, tok = issue["id"], staff[1]
    for verb in ("start", "resolve"):
        r = client.put(f"/api/staff/issues/{iid}/{verb}", headers=_h(tok))
        assert r.status_code == 409 and r.json()["error_code"] == "INVALID_ASSIGNMENT_STATE", verb
    client.put(f"/api/staff/issues/{iid}/accept", headers=_h(tok))
    r = client.put(f"/api/staff/issues/{iid}/accept", headers=_h(tok))
    assert r.status_code == 409 and r.json()["error_code"] == "INVALID_ASSIGNMENT_STATE"
    r = client.put(f"/api/staff/issues/{iid}/resolve", headers=_h(tok))
    assert r.status_code == 409


def test_resolving_requires_an_after_photo(client, citizen, admin, staff):
    """Business rule 4."""
    issue = _in_progress(client, citizen, admin, staff)
    iid, tok = issue["id"], staff[1]
    r = client.put(f"/api/staff/issues/{iid}/resolve", headers=_h(tok))
    assert r.status_code == 422 and r.json()["error_code"] == "RESOLUTION_EVIDENCE_REQUIRED"

    _photo(client, tok, iid, "BEFORE_WORK")  # a BEFORE photo is not evidence of resolution
    r = client.put(f"/api/staff/issues/{iid}/resolve", headers=_h(tok))
    assert r.status_code == 422 and r.json()["error_code"] == "RESOLUTION_EVIDENCE_REQUIRED"
    assert _detail(client, citizen, iid)["status"] == "IN_PROGRESS"

    _photo(client, tok, iid, "AFTER_WORK")
    assert client.put(f"/api/staff/issues/{iid}/resolve", headers=_h(tok)).status_code == 200


def test_photo_rules(client, citizen, admin, staff):
    issue = _assigned_issue(client, citizen, admin, staff)
    iid, tok = issue["id"], staff[1]
    # not accepted yet
    assert _photo(client, tok, iid, "BEFORE_WORK").json()["error_code"] == "PHOTO_NOT_ALLOWED_NOW"
    client.put(f"/api/staff/issues/{iid}/accept", headers=_h(tok))
    assert _photo(client, tok, iid, "BEFORE_WORK").status_code == 201
    # AFTER photos need work to have started
    assert _photo(client, tok, iid, "AFTER_WORK").json()["error_code"] == "PHOTO_NOT_ALLOWED_NOW"
    client.put(f"/api/staff/issues/{iid}/start", headers=_h(tok))
    # wrong type, bad file, too many
    assert _photo(client, tok, iid, "PROFILE").json()["error_code"] == "INVALID_IMAGE_TYPE"
    bad = _photo(client, tok, iid, "AFTER_WORK", content=b"not an image")
    assert bad.status_code == 400 and bad.json()["error_code"] == "INVALID_IMAGE"
    assert _photo(client, tok, iid, "AFTER_WORK", n=6).json()["error_code"] == "TOO_MANY_IMAGES"
    assert _photo(client, tok, iid, "AFTER_WORK", content_type="application/pdf").json()["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_progress_rules(client, citizen, admin, staff):
    issue = _accepted(client, citizen, admin, staff)
    iid, tok = issue["id"], staff[1]
    r = client.put(f"/api/staff/issues/{iid}/progress", json={"percent": 30}, headers=_h(tok))
    assert r.status_code == 409  # work hasn't started
    client.put(f"/api/staff/issues/{iid}/start", headers=_h(tok))
    assert client.put(f"/api/staff/issues/{iid}/progress", json={"percent": 100}, headers=_h(tok)).status_code == 422
    assert client.put(f"/api/staff/issues/{iid}/progress", json={"percent": -1}, headers=_h(tok)).status_code == 422
    assert client.put(f"/api/staff/issues/{iid}/progress", json={"percent": 25}, headers=_h(tok)).status_code == 200


def test_only_the_assigned_staff_member_can_act(client, citizen, admin, staff, staff2):
    """Business rule 3: everything below is attempted by staff2 on staff's issue."""
    issue = _in_progress(client, citizen, admin, staff)
    iid, other = issue["id"], staff2[1]
    for method, path, kw in [
        ("put", "accept", {}), ("put", "start", {}), ("put", "resolve", {}),
        ("put", "progress", {"json": {"percent": 10}}), ("post", "notes", {"json": {"body": "hi"}}),
    ]:
        r = getattr(client, method)(f"/api/staff/issues/{iid}/{path}", headers=_h(other), **kw)
        assert r.status_code == 403 and r.json()["error_code"] == "NOT_ASSIGNED", path
    assert _photo(client, other, iid, "BEFORE_WORK").status_code == 403
    assert client.get(f"/api/staff/issues/{iid}", headers=_h(other)).status_code == 403


def test_staff_cannot_touch_unassigned_or_missing_issues(client, citizen, admin, staff):
    issue = _verified_issue(client, citizen, admin)  # verified but never assigned
    assert client.put(f"/api/staff/issues/{issue['id']}/accept", headers=_h(staff[1])).status_code == 403
    r = client.put("/api/staff/issues/00000000-0000-0000-0000-000000000000/accept", headers=_h(staff[1]))
    assert r.status_code == 404 and r.json()["error_code"] == "ISSUE_NOT_FOUND"


def test_staff_detail_includes_assignment_state(client, citizen, admin, staff):
    issue = _accepted(client, citizen, admin, staff)
    d = client.get(f"/api/staff/issues/{issue['id']}", headers=_h(staff[1])).json()
    assert d["assignment_status"] == "ACCEPTED" and d["accepted_at"] is not None and d["started_at"] is None
    assert d["reference_code"] == issue["reference_code"]


# ================================================================ note visibility
def test_internal_notes_are_not_visible_to_the_citizen(client, citizen, admin, staff):
    """
    Regression: the API used to return every comment (including internal
    ones) to every viewer and rely on the React page to hide them.
    """
    issue = _accepted(client, citizen, admin, staff)
    iid, tok = issue["id"], staff[1]
    client.post(f"/api/staff/issues/{iid}/notes", json={"body": "SECRET gate code is 4411"}, headers=_h(tok))
    client.post(f"/api/staff/issues/{iid}/notes", json={"body": "Crew arrives tomorrow", "visible_to_citizen": True}, headers=_h(tok))

    as_citizen = _detail(client, citizen, iid)
    bodies = [c["body"] for c in as_citizen["comments"]]
    assert "Crew arrives tomorrow" in bodies
    assert "SECRET gate code is 4411" not in bodies
    assert "SECRET" not in str(as_citizen)

    as_staff = client.get(f"/api/staff/issues/{iid}", headers=_h(tok)).json()
    assert "SECRET gate code is 4411" in [c["body"] for c in as_staff["comments"]]
    as_admin = _detail(client, admin[1], iid)
    assert "SECRET gate code is 4411" in [c["body"] for c in as_admin["comments"]]


def test_citizen_can_see_assigned_staff_and_visible_progress(client, citizen, admin, staff):
    issue = _in_progress(client, citizen, admin, staff)
    client.put(f"/api/staff/issues/{issue['id']}/progress", json={"percent": 40, "note": "Digging out"}, headers=_h(staff[1]))
    d = _detail(client, citizen, issue["id"])
    assert d["assigned_to_name"] == "Ravi Kumar"
    assert any("Progress update (40%): Digging out" in c["body"] for c in d["comments"])


# ================================================================ create_user CLI helper
def test_create_user_helper(db_session):
    from app.core.exceptions import AppError  # noqa: F401
    from app.utils.create_user import CreateUserError, create_user

    dept = _department(db_session)
    user = create_user(
        db_session, role=UserRole.FIELD_STAFF, email="New.Staff@Example.com", full_name="New Staff",
        password="StrongPass123", department_code="roads",
    )
    assert user.email == "new.staff@example.com" and user.staff_profile.department_id == dept.id
    assert user.staff_profile.employee_code.startswith("EMP-")

    admin_user = create_user(db_session, role=UserRole.SUPER_ADMIN, email="boss@example.com", full_name="Boss", password="StrongPass123")
    assert admin_user.staff_profile is None

    with pytest.raises(CreateUserError, match="already exists"):
        create_user(db_session, role=UserRole.FIELD_STAFF, email="new.staff@example.com", full_name="X", password="StrongPass123")
    with pytest.raises(CreateUserError, match="Password"):
        create_user(db_session, role=UserRole.FIELD_STAFF, email="weak@example.com", full_name="X", password="short")
    with pytest.raises(CreateUserError, match="Citizens"):
        create_user(db_session, role=UserRole.CITIZEN, email="c@example.com", full_name="X", password="StrongPass123")
    with pytest.raises(CreateUserError, match="No department"):
        create_user(db_session, role=UserRole.FIELD_STAFF, email="d@example.com", full_name="X", password="StrongPass123", department_code="NOPE")
