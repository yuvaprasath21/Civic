from datetime import datetime, timedelta, timezone


def test_severity_alone_determines_score_with_no_other_factors():
    from app.services.priority_service import calculate_priority
    from app.core.enums import SeverityLevel

    low = calculate_priority(severity=SeverityLevel.LOW, duplicate_count=0, location_risk_score=0, age_hours=0)
    medium = calculate_priority(severity=SeverityLevel.MEDIUM, duplicate_count=0, location_risk_score=0, age_hours=0)
    high = calculate_priority(severity=SeverityLevel.HIGH, duplicate_count=0, location_risk_score=0, age_hours=0)
    critical = calculate_priority(severity=SeverityLevel.CRITICAL, duplicate_count=0, location_risk_score=0, age_hours=0)

    assert low.final_score == 20
    assert medium.final_score == 40
    assert high.final_score == 70
    assert critical.final_score == 100


def test_priority_level_thresholds_at_boundaries():
    from app.services.priority_service import level_for_score
    from app.core.enums import PriorityLevel

    assert level_for_score(0) == PriorityLevel.LOW
    assert level_for_score(30) == PriorityLevel.LOW
    assert level_for_score(31) == PriorityLevel.MEDIUM
    assert level_for_score(60) == PriorityLevel.MEDIUM
    assert level_for_score(61) == PriorityLevel.HIGH
    assert level_for_score(80) == PriorityLevel.HIGH
    assert level_for_score(81) == PriorityLevel.CRITICAL
    assert level_for_score(100) == PriorityLevel.CRITICAL


def test_frequency_score_increases_with_duplicates_and_caps():
    from app.services.priority_service import calculate_priority
    from app.core.enums import SeverityLevel

    zero_dupes = calculate_priority(severity=SeverityLevel.LOW, duplicate_count=0, location_risk_score=0, age_hours=0)
    some_dupes = calculate_priority(severity=SeverityLevel.LOW, duplicate_count=2, location_risk_score=0, age_hours=0)
    many_dupes = calculate_priority(severity=SeverityLevel.LOW, duplicate_count=50, location_risk_score=0, age_hours=0)

    assert zero_dupes.frequency_score == 0
    assert some_dupes.frequency_score == 6
    assert many_dupes.frequency_score == 15


def test_location_risk_score_is_capped():
    from app.services.priority_service import calculate_priority
    from app.core.enums import SeverityLevel

    result = calculate_priority(severity=SeverityLevel.LOW, duplicate_count=0, location_risk_score=999, age_hours=0)
    assert result.location_risk_score == 15


def test_age_score_increases_with_time_and_caps():
    from app.services.priority_service import calculate_priority
    from app.core.enums import SeverityLevel

    fresh = calculate_priority(severity=SeverityLevel.LOW, duplicate_count=0, location_risk_score=0, age_hours=0)
    five_days = calculate_priority(severity=SeverityLevel.LOW, duplicate_count=0, location_risk_score=0, age_hours=120)
    very_old = calculate_priority(severity=SeverityLevel.LOW, duplicate_count=0, location_risk_score=0, age_hours=24 * 100)

    assert fresh.age_score == 0
    assert five_days.age_score == 5
    assert very_old.age_score == 10


def test_final_score_is_clamped_to_100():
    from app.services.priority_service import calculate_priority
    from app.core.enums import SeverityLevel

    result = calculate_priority(
        severity=SeverityLevel.CRITICAL, duplicate_count=50, location_risk_score=999, age_hours=24 * 100
    )
    assert result.raw_score == 140
    assert result.final_score == 100
    assert result.level.value == "CRITICAL"


def test_low_severity_can_escalate_to_medium_with_other_factors():
    from app.services.priority_service import calculate_priority
    from app.core.enums import SeverityLevel

    result = calculate_priority(severity=SeverityLevel.LOW, duplicate_count=10, location_risk_score=20, age_hours=72)
    assert result.final_score == 53
    assert result.level.value == "MEDIUM"


def test_location_risk_score_sums_zones_within_radius(db_session):
    from app.services.priority_service import PriorityService
    from app.models.location import RiskZone

    db_session.add(
        RiskZone(zone_type="SCHOOL", name="Test School", latitude=26.8470, longitude=80.9465, radius_meters=200, risk_weight=8)
    )
    db_session.add(
        RiskZone(zone_type="HOSPITAL", name="Distant Hospital", latitude=19.0760, longitude=72.8777, radius_meters=200, risk_weight=10)
    )
    db_session.commit()

    service = PriorityService(db_session)
    score = service.location_risk_score(26.8467, 80.9462)
    assert score == 8


def test_location_risk_score_ignores_inactive_zones(db_session):
    from app.services.priority_service import PriorityService
    from app.models.location import RiskZone

    db_session.add(
        RiskZone(
            zone_type="SCHOOL", name="Closed School", latitude=26.8467, longitude=80.9462,
            radius_meters=500, risk_weight=8, is_active=False,
        )
    )
    db_session.commit()

    service = PriorityService(db_session)
    score = service.location_risk_score(26.8467, 80.9462)
    assert score == 0


def test_location_risk_score_sums_multiple_overlapping_zones(db_session):
    from app.services.priority_service import PriorityService
    from app.models.location import RiskZone

    db_session.add_all(
        [
            RiskZone(zone_type="SCHOOL", name="School A", latitude=26.8467, longitude=80.9462, radius_meters=300, risk_weight=8),
            RiskZone(zone_type="MAJOR_ROAD", name="Highway", latitude=26.8468, longitude=80.9463, radius_meters=300, risk_weight=5),
        ]
    )
    db_session.commit()

    service = PriorityService(db_session)
    score = service.location_risk_score(26.8467, 80.9462)
    assert score == 13


def _register(client, email="priya.nair@example.com", password="SecurePass123"):
    r = client.post("/api/auth/register", json={"full_name": "Priya Nair", "email": email, "password": password})
    assert r.status_code == 201
    return r.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _create_issue(client, token, **overrides):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (80, 80), (100, 50, 50)).save(buf, format="PNG")

    form = {
        "title": "Deep pothole outside the school gate",
        "category": "POTHOLE",
        "severity": "CRITICAL",
        "latitude": 26.8467,
        "longitude": 80.9462,
        **overrides,
    }
    files = [("images", ("photo.png", buf.getvalue(), "image/png"))]
    return client.post("/api/issues", data=form, files=files, headers=_headers(token))


def test_issue_creation_sets_priority_score_from_severity(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)

    r = _create_issue(client, token, severity="CRITICAL")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["priority_score"] == 100
    assert body["priority_level"] == "CRITICAL"


def test_issue_creation_low_severity_gives_low_priority(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)

    r = _create_issue(client, token, severity="LOW")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["priority_score"] == 20
    assert body["priority_level"] == "LOW"


def test_issue_creation_picks_up_nearby_risk_zone(client, monkeypatch, tmp_path, db_session):
    from app.core.config import settings
    from app.models.location import RiskZone

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))

    db_session.add(
        RiskZone(zone_type="SCHOOL", name="Nearby School", latitude=26.8467, longitude=80.9462, radius_meters=300, risk_weight=8)
    )
    db_session.commit()

    token = _register(client)
    r = _create_issue(client, token, severity="LOW", latitude=26.8467, longitude=80.9462)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["priority_score"] == 28
    assert body["priority_level"] == "LOW"


def test_update_issue_severity_recomputes_priority(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)

    issue = _create_issue(client, token, severity="LOW").json()
    assert issue["priority_score"] == 20

    r = client.put(f"/api/issues/{issue['id']}", json={"severity": "CRITICAL"}, headers=_headers(token))
    assert r.status_code == 200
    body = r.json()
    assert body["priority_score"] == 100
    assert body["priority_level"] == "CRITICAL"


def test_update_issue_without_severity_change_leaves_priority_untouched(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)

    issue = _create_issue(client, token, severity="HIGH").json()
    original_score = issue["priority_score"]

    r = client.put(f"/api/issues/{issue['id']}", json={"description": "Adding more detail."}, headers=_headers(token))
    assert r.status_code == 200
    assert r.json()["priority_score"] == original_score
