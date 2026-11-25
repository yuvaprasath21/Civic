"""
Phase 7: duplicate detection (automatic flagging) and admin merge/dismiss.
"""
import io
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image

LAT, LON = 26.8467, 80.9462
# ~0.0001 degrees of latitude is ~11 m
M = 0.0001 / 11.1


def _png(color=(120, 60, 60)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (80, 80), color).save(buf, format="PNG")
    return buf.getvalue()


def _gradient(reverse=False) -> bytes:
    img = Image.new("L", (90, 80))
    img.putdata([(255 - x * 2 if reverse else x * 2) for _y in range(80) for x in range(90)])
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _register(client, email, name="Citizen"):
    r = client.post("/api/auth/register", json={"full_name": name, "email": email, "password": "SecurePass123"})
    assert r.status_code == 201
    return r.json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _report(client, token, *, lat=LAT, lon=LON, category="POTHOLE", severity="LOW", image=None, title="Pothole near the market"):
    r = client.post(
        "/api/issues",
        data={"title": title, "category": category, "severity": severity, "latitude": lat, "longitude": lon},
        files=[("images", ("p.png", image or _png(), "image/png"))],
        headers=_h(token),
    )
    assert r.status_code == 201, r.text
    return r.json()


def _meters_north(m):
    return LAT + m / 111_000


@pytest.fixture(autouse=True)
def _uploads(monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))


@pytest.fixture()
def citizens(client):
    return _register(client, "a@example.com", "Asha"), _register(client, "b@example.com", "Bhavna"), _register(client, "c@example.com", "Chetan")


def _admin_token(client, db_session, email="admin@example.com"):
    from app.core.enums import UserRole
    from app.core.security import hash_password
    from app.models.user import User

    db_session.add(User(full_name="Dept Admin", email=email, hashed_password=hash_password("AdminPass123"), role=UserRole.DEPARTMENT_ADMIN))
    db_session.commit()
    r = client.post("/api/auth/login", json={"email": email, "password": "AdminPass123"})
    assert r.status_code == 200
    return r.json()["access_token"]


# ---------------------------------------------------------------- hashing

def test_dhash_identical_images_are_fully_similar():
    from app.utils.image_hash import dhash, similarity

    assert similarity(dhash(_gradient()), dhash(_gradient())) == 1.0


def test_dhash_opposite_images_are_dissimilar():
    from app.utils.image_hash import dhash, similarity

    assert similarity(dhash(_gradient()), dhash(_gradient(reverse=True))) < 0.2


def test_dhash_handles_garbage_and_missing():
    from app.utils.image_hash import dhash, similarity

    assert dhash(b"not an image") is None
    assert similarity(None, "ffffffffffffffff") is None


# -------------------------------------------------------- auto detection

def test_nearby_same_category_report_is_flagged_as_duplicate(client, citizens):
    a, b, _ = citizens
    master = _report(client, a, title="Pothole at market")
    dup = _report(client, b, lat=_meters_north(30), title="Same pothole at market")

    assert dup["status"] == "POTENTIAL_DUPLICATE"
    assert dup["master_reference_code"] == master["reference_code"]
    assert dup["master_issue_id"] == master["id"]
    assert [h["to_status"] for h in dup["status_history"]] == ["REPORTED", "AI_ANALYZED", "POTENTIAL_DUPLICATE"]

    refreshed = client.get(f"/api/issues/{master['id']}", headers=_h(a)).json()
    assert refreshed["duplicate_count"] == 1
    assert refreshed["report_count"] == 2
    assert refreshed["status"] != "POTENTIAL_DUPLICATE"  # the master itself is untouched


def test_different_category_is_not_a_duplicate(client, citizens):
    a, b, _ = citizens
    _report(client, a, category="POTHOLE")
    other = _report(client, b, category="GARBAGE", lat=_meters_north(10))
    assert other["status"] != "POTENTIAL_DUPLICATE"


def test_report_outside_radius_is_not_a_duplicate(client, citizens):
    a, b, _ = citizens
    _report(client, a)
    far = _report(client, b, lat=_meters_north(200))
    assert far["status"] != "POTENTIAL_DUPLICATE"


def test_report_just_inside_radius_is_a_duplicate(client, citizens):
    a, b, _ = citizens
    _report(client, a)
    near = _report(client, b, lat=_meters_north(60))
    assert near["status"] == "POTENTIAL_DUPLICATE"


def test_radius_is_configurable(client, citizens, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DUPLICATE_RADIUS_METERS", 300)
    a, b, _ = citizens
    _report(client, a)
    assert _report(client, b, lat=_meters_north(200))["status"] == "POTENTIAL_DUPLICATE"


def test_old_master_outside_time_window_is_not_matched(client, citizens, db_session):
    from app.models.civic_issue import CivicIssue

    a, b, _ = citizens
    master = _report(client, a)
    row = db_session.query(CivicIssue).filter(CivicIssue.uuid == master["id"]).one()
    row.created_at = datetime.now(timezone.utc) - timedelta(days=30)
    db_session.commit()

    assert _report(client, b, lat=_meters_north(10))["status"] != "POTENTIAL_DUPLICATE"


@pytest.mark.parametrize("closed_status", ["RESOLVED", "CLOSED", "REJECTED"])
def test_finished_master_is_not_matched(client, citizens, db_session, closed_status):
    from app.core.enums import IssueStatus
    from app.models.civic_issue import CivicIssue

    a, b, _ = citizens
    master = _report(client, a)
    db_session.query(CivicIssue).filter(CivicIssue.uuid == master["id"]).one().status = IssueStatus(closed_status)
    db_session.commit()

    # A new report at an already-fixed spot is a recurrence, not a duplicate.
    assert _report(client, b, lat=_meters_north(10))["status"] != "POTENTIAL_DUPLICATE"


def test_third_report_links_to_master_not_to_the_duplicate(client, citizens):
    a, b, c = citizens
    master = _report(client, a)
    _report(client, b, lat=_meters_north(20))
    third = _report(client, c, lat=_meters_north(40))

    assert third["master_reference_code"] == master["reference_code"]
    assert client.get(f"/api/issues/{master['id']}", headers=_h(a)).json()["report_count"] == 3


def test_nearest_master_wins(client, citizens, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "DUPLICATE_RADIUS_METERS", 200)
    a, b, c = citizens
    near = _report(client, a, lat=_meters_north(0))
    far = _report(client, b, lat=_meters_north(280))  # outside 200 m of `near`, so its own master
    assert far["status"] != "POTENTIAL_DUPLICATE"

    new = _report(client, c, lat=_meters_north(100))  # 100 m from near, 180 m from far
    assert new["master_reference_code"] == near["reference_code"]


def test_duplicates_raise_master_priority(client, citizens):
    a, b, c = citizens
    master = _report(client, a, severity="LOW")
    assert master["priority_score"] == 20

    _report(client, b, lat=_meters_north(10), severity="LOW")
    after_one = client.get(f"/api/issues/{master['id']}", headers=_h(a)).json()
    assert after_one["priority_score"] == 23  # 20 + 1 duplicate * 3

    _report(client, c, lat=_meters_north(20), severity="LOW")
    after_two = client.get(f"/api/issues/{master['id']}", headers=_h(a)).json()
    assert after_two["priority_score"] == 26


def test_image_similarity_recorded_but_never_vetoes(client, citizens, db_session):
    from app.models.issue_workflow import IssueDuplicate

    a, b, c = citizens
    _report(client, a, image=_gradient())
    same = _report(client, b, lat=_meters_north(10), image=_gradient())
    different_angle = _report(client, c, lat=_meters_north(15), image=_gradient(reverse=True))

    assert same["status"] == "POTENTIAL_DUPLICATE"
    assert different_angle["status"] == "POTENTIAL_DUPLICATE"  # dissimilar photo is still flagged

    scores = sorted(row.image_similarity_score for row in db_session.query(IssueDuplicate).all())
    assert scores[0] < 0.2 and scores[1] == 1.0


def test_citizen_can_still_edit_a_potential_duplicate(client, citizens):
    a, b, _ = citizens
    _report(client, a)
    dup = _report(client, b, lat=_meters_north(10))
    r = client.put(f"/api/issues/{dup['id']}", json={"description": "More detail"}, headers=_h(b))
    assert r.status_code == 200


# ------------------------------------------------------------ admin merge

def test_merge_requires_admin(client, citizens):
    a, b, _ = citizens
    master = _report(client, a)
    dup = _report(client, b, lat=_meters_north(10))
    r = client.post(f"/api/admin/issues/{master['id']}/merge", json={"duplicate_ids": [dup["id"]]}, headers=_h(a))
    assert r.status_code == 403
    assert client.post(f"/api/admin/issues/{master['id']}/merge", json={"duplicate_ids": [dup["id"]]}).status_code == 401


def test_admin_confirms_automatic_duplicate(client, citizens, db_session):
    from app.models.issue_workflow import IssueDuplicate
    from app.models.notification import AuditLog

    a, b, _ = citizens
    admin = _admin_token(client, db_session)
    master = _report(client, a)
    dup = _report(client, b, lat=_meters_north(10))

    r = client.post(f"/api/admin/issues/{master['id']}/merge", json={"duplicate_ids": [dup["id"]]}, headers=_h(admin))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["master_reference_code"] == master["reference_code"]
    assert body["report_count"] == 2  # not double counted: it was already linked automatically

    merged = client.get(f"/api/issues/{dup['id']}", headers=_h(b)).json()
    assert merged["status"] == "CLOSED"
    assert merged["status_history"][-1]["note"] == f"Merged into {master['reference_code']}."
    assert db_session.query(IssueDuplicate).one().merged_by_id is not None
    assert db_session.query(AuditLog).filter(AuditLog.action == "ISSUES_MERGED").count() == 1


def test_admin_merges_manually_selected_issues_into_one_group(client, citizens, db_session):
    """The spec's example: CIV-1001/1002/1003 all the same pothole -> master with Reports: 3."""
    a, b, c = citizens
    admin = _admin_token(client, db_session)
    # Far apart, so none are auto-flagged; the admin recognises them as one problem.
    i1 = _report(client, a, lat=_meters_north(0), severity="LOW")
    i2 = _report(client, b, lat=_meters_north(500), severity="LOW")
    i3 = _report(client, c, lat=_meters_north(1000), severity="LOW")
    assert {i1["status"], i2["status"], i3["status"]} == {"AI_ANALYZED"}

    r = client.post(
        f"/api/admin/issues/{i1['id']}/merge", json={"duplicate_ids": [i2["id"], i3["id"]]}, headers=_h(admin)
    )
    assert r.status_code == 200, r.text
    assert r.json()["report_count"] == 3
    assert r.json()["priority_score"] == 26  # 20 + 2 duplicates * 3

    listing = client.get(f"/api/admin/issues/{i1['id']}/duplicates", headers=_h(admin)).json()
    assert listing["report_count"] == 3
    assert {d["reference_code"] for d in listing["duplicates"]} == {i2["reference_code"], i3["reference_code"]}


def test_merge_is_idempotent(client, citizens, db_session):
    a, b, _ = citizens
    admin = _admin_token(client, db_session)
    master = _report(client, a)
    dup = _report(client, b, lat=_meters_north(10))
    body = {"duplicate_ids": [dup["id"]]}
    client.post(f"/api/admin/issues/{master['id']}/merge", json=body, headers=_h(admin))
    r = client.post(f"/api/admin/issues/{master['id']}/merge", json=body, headers=_h(admin))
    assert r.status_code == 200
    assert r.json()["report_count"] == 2


def test_merge_validation_errors(client, citizens, db_session):
    a, b, c = citizens
    admin = _admin_token(client, db_session)
    master = _report(client, a)
    dup = _report(client, b, lat=_meters_north(10))

    # into itself
    r = client.post(f"/api/admin/issues/{master['id']}/merge", json={"duplicate_ids": [master["id"]]}, headers=_h(admin))
    assert r.status_code == 422 and r.json()["error_code"] == "SELF_MERGE"
    # target is itself a duplicate
    other = _report(client, c, lat=_meters_north(900))
    r = client.post(f"/api/admin/issues/{dup['id']}/merge", json={"duplicate_ids": [other["id"]]}, headers=_h(admin))
    assert r.status_code == 409 and r.json()["error_code"] == "MASTER_IS_DUPLICATE"
    # unknown issue
    r = client.post(
        f"/api/admin/issues/{master['id']}/merge",
        json={"duplicate_ids": ["00000000-0000-0000-0000-000000000000"]},
        headers=_h(admin),
    )
    assert r.status_code == 404 and r.json()["error_code"] == "ISSUE_NOT_FOUND"
    # empty list
    assert client.post(f"/api/admin/issues/{master['id']}/merge", json={"duplicate_ids": []}, headers=_h(admin)).status_code == 422


def test_merge_is_all_or_nothing(client, citizens, db_session):
    from app.models.civic_issue import CivicIssue

    a, b, c = citizens
    admin = _admin_token(client, db_session)
    group_master = _report(client, a, lat=_meters_north(0))
    _report(client, b, lat=_meters_north(10))  # makes group_master a master WITH a child
    target = _report(client, c, lat=_meters_north(2000))
    loose = _report(client, c, lat=_meters_north(4000))

    # `loose` is fine; `group_master` has children so it can't be merged -> whole request must fail.
    r = client.post(
        f"/api/admin/issues/{target['id']}/merge",
        json={"duplicate_ids": [loose["id"], group_master["id"]]},
        headers=_h(admin),
    )
    assert r.status_code == 409 and r.json()["error_code"] == "ISSUE_HAS_DUPLICATES"

    db_session.expire_all()
    assert db_session.query(CivicIssue).filter(CivicIssue.uuid == target["id"]).one().duplicate_count == 0
    assert db_session.query(CivicIssue).filter(CivicIssue.uuid == loose["id"]).one().master_issue_id is None


def test_merge_rehomes_a_duplicate_from_another_master(client, citizens, db_session):
    from app.models.civic_issue import CivicIssue

    a, b, c = citizens
    admin = _admin_token(client, db_session)
    m1 = _report(client, a, lat=_meters_north(0))
    dup = _report(client, b, lat=_meters_north(10))  # auto-linked to m1
    m2 = _report(client, c, lat=_meters_north(3000))

    r = client.post(f"/api/admin/issues/{m2['id']}/merge", json={"duplicate_ids": [dup["id"]]}, headers=_h(admin))
    assert r.status_code == 200
    db_session.expire_all()
    assert db_session.query(CivicIssue).filter(CivicIssue.uuid == m1["id"]).one().duplicate_count == 0
    assert db_session.query(CivicIssue).filter(CivicIssue.uuid == m2["id"]).one().duplicate_count == 1


# ------------------------------------------------------- not a duplicate

def test_admin_can_dismiss_a_false_positive(client, citizens, db_session):
    from app.models.issue_workflow import IssueDuplicate
    from app.models.notification import AuditLog

    a, b, _ = citizens
    admin = _admin_token(client, db_session)
    master = _report(client, a, severity="LOW")
    dup = _report(client, b, lat=_meters_north(10))
    assert client.get(f"/api/issues/{master['id']}", headers=_h(a)).json()["priority_score"] == 23

    r = client.post(f"/api/admin/issues/{dup['id']}/not-duplicate", headers=_h(admin))
    assert r.status_code == 200, r.text
    freed = r.json()
    assert freed["status"] == "AI_ANALYZED"  # back to where it was in the normal workflow
    assert freed["master_issue_id"] is None
    assert freed["status_history"][-1]["note"] == "Admin reviewed: not a duplicate."

    back = client.get(f"/api/issues/{master['id']}", headers=_h(a)).json()
    assert back["duplicate_count"] == 0 and back["priority_score"] == 20  # rolled back
    assert db_session.query(IssueDuplicate).count() == 0
    assert db_session.query(AuditLog).filter(AuditLog.action == "DUPLICATE_DISMISSED").count() == 1


def test_dismiss_rejects_non_duplicates_and_merged_ones(client, citizens, db_session):
    a, b, _ = citizens
    admin = _admin_token(client, db_session)
    master = _report(client, a)
    dup = _report(client, b, lat=_meters_north(10))

    r = client.post(f"/api/admin/issues/{master['id']}/not-duplicate", headers=_h(admin))
    assert r.status_code == 409 and r.json()["error_code"] == "NOT_A_DUPLICATE"

    client.post(f"/api/admin/issues/{master['id']}/merge", json={"duplicate_ids": [dup["id"]]}, headers=_h(admin))
    r = client.post(f"/api/admin/issues/{dup['id']}/not-duplicate", headers=_h(admin))
    assert r.status_code == 409 and r.json()["error_code"] == "ALREADY_MERGED"


def test_dismiss_requires_admin(client, citizens):
    a, b, _ = citizens
    _report(client, a)
    dup = _report(client, b, lat=_meters_north(10))
    assert client.post(f"/api/admin/issues/{dup['id']}/not-duplicate", headers=_h(b)).status_code == 403
