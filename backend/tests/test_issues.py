import io

from PIL import Image


def _register(client, email="anita.desai@example.com", password="SecurePass123", full_name="Anita Desai"):
    r = client.post("/api/auth/register", json={"full_name": full_name, "email": email, "password": password})
    assert r.status_code == 201
    return r.json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _png_bytes(size=(80, 80), color=(200, 30, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _create_issue(client, token, **overrides):
    form = {
        "title": "Large pothole on MG Road",
        "description": "Deep pothole causing traffic slowdown near the junction.",
        "category": "POTHOLE",
        "severity": "HIGH",
        "latitude": 26.8467,
        "longitude": 80.9462,
        "address_text": "MG Road, near City Junction",
        "city": "Lucknow",
        **overrides,
    }
    files = [("images", ("pothole.png", _png_bytes(), "image/png"))]
    return client.post("/api/issues", data=form, files=files, headers=_headers(token))


def test_create_issue_success(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)

    r = _create_issue(client, token)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["reference_code"].startswith("CIV-")
    assert body["status"] == "AI_ANALYZED"
    assert body["category"] == "POTHOLE"
    assert body["severity"] == "HIGH"
    assert len(body["images"]) == 1
    assert body["images"][0]["url"].startswith("/uploads/issue_images/")
    assert body["reporter_name"] == "Anita Desai"
    assert body["location"]["city"] == "Lucknow"
    assert len(body["status_history"]) == 2
    assert body["status_history"][0]["to_status"] == "REPORTED"
    assert body["status_history"][1]["to_status"] == "AI_ANALYZED"


def test_create_issue_requires_at_least_one_image(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)

    form = {
        "title": "Large pothole on MG Road",
        "category": "POTHOLE",
        "latitude": 26.8467,
        "longitude": 80.9462,
    }
    r = client.post("/api/issues", data=form, files=[], headers=_headers(token))
    assert r.status_code in (400, 422)


def test_create_issue_requires_citizen_role(client):
    r = client.post("/api/issues", data={}, files=[])
    assert r.status_code == 401


def test_get_issue_detail(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)
    issue_uuid = _create_issue(client, token).json()["id"]

    r = client.get(f"/api/issues/{issue_uuid}", headers=_headers(token))
    assert r.status_code == 200
    assert r.json()["reference_code"].startswith("CIV-")


def test_get_issue_not_found(client):
    token = _register(client)
    r = client.get("/api/issues/00000000-0000-0000-0000-000000000000", headers=_headers(token))
    assert r.status_code == 404
    assert r.json()["error_code"] == "ISSUE_NOT_FOUND"


def test_list_my_issues(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)
    _create_issue(client, token)
    _create_issue(client, token, title="Broken streetlight near the park")

    r = client.get("/api/my/issues", headers=_headers(token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


def test_list_my_issues_only_shows_own(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token_a = _register(client, email="a@example.com", full_name="Citizen A")
    token_b = _register(client, email="b@example.com", full_name="Citizen B")
    _create_issue(client, token_a)
    _create_issue(client, token_b)

    r = client.get("/api/my/issues", headers=_headers(token_a))
    assert r.json()["total"] == 1


def test_list_issues_filters_by_category(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)
    _create_issue(client, token, category="POTHOLE")
    _create_issue(client, token, category="GARBAGE", title="Garbage pile near market")

    r = client.get("/api/issues?category=GARBAGE", headers=_headers(token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["category"] == "GARBAGE"


def test_nearby_issues(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)
    _create_issue(client, token, latitude=26.8467, longitude=80.9462)
    _create_issue(client, token, latitude=19.0760, longitude=72.8777, title="Mumbai issue far away")

    r = client.get(
        "/api/issues/nearby", params={"latitude": 26.8467, "longitude": 80.9462, "radius_km": 5}, headers=_headers(token)
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert "Mumbai" not in body["items"][0]["title"]


def test_update_issue_before_verification(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)
    issue_uuid = _create_issue(client, token).json()["id"]

    r = client.put(f"/api/issues/{issue_uuid}", json={"title": "Updated pothole title"}, headers=_headers(token))
    assert r.status_code == 200
    assert r.json()["title"] == "Updated pothole title"


def test_update_issue_rejected_when_not_owner(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token_a = _register(client, email="a@example.com", full_name="Citizen A")
    token_b = _register(client, email="b@example.com", full_name="Citizen B")
    issue_uuid = _create_issue(client, token_a).json()["id"]

    r = client.put(f"/api/issues/{issue_uuid}", json={"title": "Hijacked title"}, headers=_headers(token_b))
    assert r.status_code == 403
    assert r.json()["error_code"] == "NOT_ISSUE_OWNER"


def test_update_issue_rejected_after_verification(client, monkeypatch, tmp_path, db_session):
    from app.core.config import settings
    from app.core.enums import IssueStatus
    from app.models.civic_issue import CivicIssue

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)
    issue_uuid = _create_issue(client, token).json()["id"]

    issue = db_session.query(CivicIssue).filter(CivicIssue.uuid == issue_uuid).first()
    issue.status = IssueStatus.VERIFIED
    db_session.commit()

    r = client.put(f"/api/issues/{issue_uuid}", json={"title": "Too late"}, headers=_headers(token))
    assert r.status_code == 409
    assert r.json()["error_code"] == "ISSUE_NOT_EDITABLE"


def test_add_comment(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)
    issue_uuid = _create_issue(client, token).json()["id"]

    r = client.post(f"/api/issues/{issue_uuid}/comments", json={"body": "Any update on this?"}, headers=_headers(token))
    assert r.status_code == 201
    assert r.json()["body"] == "Any update on this?"
    assert r.json()["is_internal"] is False


def test_citizen_cannot_post_internal_comment(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)
    issue_uuid = _create_issue(client, token).json()["id"]

    r = client.post(
        f"/api/issues/{issue_uuid}/comments",
        json={"body": "trying to sneak an internal note", "is_internal": True},
        headers=_headers(token),
    )
    assert r.status_code == 201
    assert r.json()["is_internal"] is False


def test_feedback_requires_resolved_status(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)
    issue_uuid = _create_issue(client, token).json()["id"]

    r = client.post(f"/api/issues/{issue_uuid}/feedback", json={"rating": 5}, headers=_headers(token))
    assert r.status_code == 409
    assert r.json()["error_code"] == "ISSUE_NOT_RESOLVED"


def test_feedback_success_after_resolution(client, monkeypatch, tmp_path, db_session):
    from app.core.config import settings
    from app.core.enums import IssueStatus
    from app.models.civic_issue import CivicIssue

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)
    issue_uuid = _create_issue(client, token).json()["id"]

    issue = db_session.query(CivicIssue).filter(CivicIssue.uuid == issue_uuid).first()
    issue.status = IssueStatus.RESOLVED
    db_session.commit()

    r = client.post(
        f"/api/issues/{issue_uuid}/feedback", json={"rating": 4, "comment": "Fixed quickly, thanks!"}, headers=_headers(token)
    )
    assert r.status_code == 201
    assert r.json()["rating"] == 4

    r = client.post(f"/api/issues/{issue_uuid}/feedback", json={"rating": 5}, headers=_headers(token))
    assert r.status_code == 409
    assert r.json()["error_code"] == "FEEDBACK_EXISTS"


def test_feedback_only_by_reporter(client, monkeypatch, tmp_path, db_session):
    from app.core.config import settings
    from app.core.enums import IssueStatus
    from app.models.civic_issue import CivicIssue

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token_a = _register(client, email="a@example.com", full_name="Citizen A")
    token_b = _register(client, email="b@example.com", full_name="Citizen B")
    issue_uuid = _create_issue(client, token_a).json()["id"]

    issue = db_session.query(CivicIssue).filter(CivicIssue.uuid == issue_uuid).first()
    issue.status = IssueStatus.RESOLVED
    db_session.commit()

    r = client.post(f"/api/issues/{issue_uuid}/feedback", json={"rating": 3}, headers=_headers(token_b))
    assert r.status_code == 403
    assert r.json()["error_code"] == "NOT_ISSUE_OWNER"


def test_create_issue_runs_ai_analysis_and_transitions_status(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)

    r = _create_issue(client, token)
    assert r.status_code == 201, r.text
    body = r.json()

    assert body["status"] == "AI_ANALYZED"
    assert body["ai_prediction"] is not None
    assert body["ai_prediction"]["provider"] == "mock"
    assert body["ai_prediction"]["model_version"] == "mock-v1.0"
    assert 0.0 <= body["ai_prediction"]["confidence"] <= 1.0

    history_statuses = [h["to_status"] for h in body["status_history"]]
    assert history_statuses == ["REPORTED", "AI_ANALYZED"]


def test_create_issue_persists_ai_prediction_row(client, monkeypatch, tmp_path, db_session):
    from app.core.config import settings
    from app.models.ai_prediction import AIPrediction
    from app.models.civic_issue import CivicIssue

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)
    issue_uuid = _create_issue(client, token).json()["id"]

    issue = db_session.query(CivicIssue).filter(CivicIssue.uuid == issue_uuid).first()
    predictions = db_session.query(AIPrediction).filter(AIPrediction.issue_id == issue.id).all()
    assert len(predictions) == 1
    assert predictions[0].provider == "mock"
    assert predictions[0].issue_image_id is not None


def test_is_citizen_edited_category_flag_reflects_ai_disagreement(client, monkeypatch, tmp_path):
    from app.core.config import settings
    from app.core.enums import IssueCategory

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    token = _register(client)

    image_bytes = _png_bytes(color=(77, 133, 201))
    preview = client.post(
        "/api/ai/analyze-image",
        headers=_headers(token),
        files={"image": ("photo.png", image_bytes, "image/png")},
    )
    predicted_category = preview.json()["category"]

    r_match = client.post(
        "/api/issues",
        data={
            "title": "Issue matching AI category",
            "category": predicted_category,
            "severity": "MEDIUM",
            "latitude": 26.8467,
            "longitude": 80.9462,
        },
        files=[("images", ("photo.png", image_bytes, "image/png"))],
        headers=_headers(token),
    )
    assert r_match.status_code == 201, r_match.text
    assert r_match.json()["is_citizen_edited_category"] is False

    different_category = next(c.value for c in IssueCategory if c.value != predicted_category)
    r_diff = client.post(
        "/api/issues",
        data={
            "title": "Issue overriding AI category",
            "category": different_category,
            "severity": "MEDIUM",
            "latitude": 26.8467,
            "longitude": 80.9462,
        },
        files=[("images", ("photo.png", image_bytes, "image/png"))],
        headers=_headers(token),
    )
    assert r_diff.status_code == 201, r_diff.text
    assert r_diff.json()["is_citizen_edited_category"] is True


def test_create_issue_succeeds_even_if_ai_provider_unavailable(client, monkeypatch, tmp_path):
    from app.core.config import settings
    from ai.inference.base import AIProviderError

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))

    async def _broken_analyze(self, issue_id, issue_image_id, image_bytes, content_type):
        raise AIProviderError("Simulated AI outage for testing.")

    from app.services.ai_service import AIService

    monkeypatch.setattr(AIService, "analyze_and_store", _broken_analyze)

    token = _register(client)
    r = _create_issue(client, token)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "REPORTED"
    assert body["ai_prediction"] is None
