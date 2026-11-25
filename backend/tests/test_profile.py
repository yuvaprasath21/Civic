import io

import pytest
from PIL import Image


def _register_and_login(client, email="rohan.verma@example.com", password="SecurePass123"):
    r = client.post(
        "/api/auth/register",
        json={"full_name": "Rohan Verma", "email": email, "password": password},
    )
    assert r.status_code == 201
    return r.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_png_bytes(size=(64, 64), color=(255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_get_my_profile(client):
    token = _register_and_login(client)
    r = client.get("/api/citizens/me", headers=_auth_headers(token))
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "rohan.verma@example.com"
    assert body["total_reports_submitted"] == 0
    assert body["reputation_score"] == 100


def test_profile_requires_citizen_role(client):
    r = client.get("/api/citizens/me")
    assert r.status_code == 401
    assert r.json()["error_code"] == "MISSING_TOKEN"


def test_update_profile_partial_fields_only(client):
    token = _register_and_login(client)
    headers = _auth_headers(token)

    r = client.put("/api/citizens/me", json={"city": "Lucknow", "state": "Uttar Pradesh"}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["city"] == "Lucknow"
    assert body["state"] == "Uttar Pradesh"
    assert body["full_name"] == "Rohan Verma"

    r = client.put("/api/citizens/me", json={"pincode": "226001"}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["pincode"] == "226001"
    assert body["city"] == "Lucknow"


def test_update_full_name(client):
    token = _register_and_login(client)
    headers = _auth_headers(token)
    r = client.put("/api/citizens/me", json={"full_name": "Rohan K. Verma"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["full_name"] == "Rohan K. Verma"


def test_upload_profile_image_success(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))

    token = _register_and_login(client)
    headers = _auth_headers(token)

    png_bytes = _make_png_bytes()
    r = client.post(
        "/api/citizens/me/profile-image",
        headers=headers,
        files={"file": ("avatar.png", png_bytes, "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["profile_image_url"].startswith("/uploads/profile_images/")

    r = client.get("/api/citizens/me", headers=headers)
    assert r.json()["profile_image_url"] == body["profile_image_url"]

    saved_files = list((tmp_path / "profile_images").iterdir())
    assert len(saved_files) == 1


def test_upload_profile_image_rejects_disallowed_type(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))

    token = _register_and_login(client)
    r = client.post(
        "/api/citizens/me/profile-image",
        headers=_auth_headers(token),
        files={"file": ("doc.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert r.status_code == 400
    assert r.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_upload_profile_image_rejects_fake_image_with_spoofed_content_type(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))

    token = _register_and_login(client)
    r = client.post(
        "/api/citizens/me/profile-image",
        headers=_auth_headers(token),
        files={"file": ("fake.png", b"not actually a png file at all", "image/png")},
    )
    assert r.status_code == 400
    assert r.json()["error_code"] == "INVALID_IMAGE"


def test_upload_profile_image_rejects_oversized_file(client, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "UPLOAD_DIRECTORY", str(tmp_path))
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE", 1024)

    token = _register_and_login(client)
    large_png = _make_png_bytes(size=(500, 500))
    assert len(large_png) > 1024

    r = client.post(
        "/api/citizens/me/profile-image",
        headers=_auth_headers(token),
        files={"file": ("avatar.png", large_png, "image/png")},
    )
    assert r.status_code == 400
    assert r.json()["error_code"] == "FILE_TOO_LARGE"
