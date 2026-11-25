import asyncio
import io

import pytest
from PIL import Image

from app.core.enums import IssueCategory, SeverityLevel


def _png_bytes(size=(80, 80), color=(60, 90, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_mock_provider_returns_valid_category_and_severity():
    from ai.inference.mock_provider import MockAIProvider

    provider = MockAIProvider()
    result = asyncio.run(provider.analyze(_png_bytes(), "image/png"))

    assert result.category in {c.value for c in IssueCategory}
    assert result.severity in {s.value for s in SeverityLevel}
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.detected_objects, list)
    assert len(result.detected_objects) >= 1
    assert result.model_version == "mock-v1.0"
    assert result.inference_time_ms >= 0


def test_mock_provider_is_deterministic_for_same_image():
    from ai.inference.mock_provider import MockAIProvider

    provider = MockAIProvider()
    image_bytes = _png_bytes(color=(10, 200, 40))

    result_a = asyncio.run(provider.analyze(image_bytes, "image/png"))
    result_b = asyncio.run(provider.analyze(image_bytes, "image/png"))

    assert result_a.category == result_b.category
    assert result_a.severity == result_b.severity
    assert result_a.confidence == result_b.confidence
    assert result_a.detected_objects == result_b.detected_objects


def test_mock_provider_differs_for_different_images():
    from ai.inference.mock_provider import MockAIProvider

    provider = MockAIProvider()
    categories = set()
    for i in range(15):
        img = _png_bytes(color=(i * 15 % 255, i * 47 % 255, i * 91 % 255))
        result = asyncio.run(provider.analyze(img, "image/png"))
        categories.add(result.category)

    assert len(categories) > 1


def test_mock_provider_rejects_invalid_image():
    from ai.inference.base import AIProviderError
    from ai.inference.mock_provider import MockAIProvider

    provider = MockAIProvider()
    with pytest.raises(AIProviderError):
        asyncio.run(provider.analyze(b"not an image", "image/png"))


def test_yolo_provider_raises_clear_error_without_model_file(tmp_path):
    from ai.inference.base import AIProviderError
    from ai.inference.yolo_provider import YOLOProvider

    provider = YOLOProvider(model_path=str(tmp_path / "nonexistent.pt"))
    with pytest.raises(AIProviderError, match="No YOLO model found"):
        asyncio.run(provider.analyze(_png_bytes(), "image/png"))


def test_get_ai_provider_returns_mock_by_default(monkeypatch):
    from app.core.config import settings
    from app.services.ai_service import get_ai_provider
    from ai.inference.mock_provider import MockAIProvider

    monkeypatch.setattr(settings, "AI_PROVIDER", "mock")
    provider = get_ai_provider()
    assert isinstance(provider, MockAIProvider)


def test_get_ai_provider_rejects_unknown_provider(monkeypatch):
    from app.core.config import settings
    from app.services.ai_service import get_ai_provider

    monkeypatch.setattr(settings, "AI_PROVIDER", "not-a-real-provider")
    with pytest.raises(ValueError):
        get_ai_provider()


def _register_and_login(client, email="vikram.rao@example.com", password="SecurePass123"):
    r = client.post("/api/auth/register", json={"full_name": "Vikram Rao", "email": email, "password": password})
    assert r.status_code == 201
    return r.json()["access_token"]


def test_analyze_image_endpoint_returns_expected_shape(client):
    token = _register_and_login(client)
    r = client.post(
        "/api/ai/analyze-image",
        headers={"Authorization": f"Bearer {token}"},
        files={"image": ("photo.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == {"category", "confidence", "severity", "detected_objects", "model_version"}
    assert body["category"] in {c.value for c in IssueCategory}
    assert body["severity"] in {s.value for s in SeverityLevel}
    assert 0.0 <= body["confidence"] <= 1.0


def test_analyze_image_requires_authentication(client):
    r = client.post("/api/ai/analyze-image", files={"image": ("photo.png", _png_bytes(), "image/png")})
    assert r.status_code == 401


def test_analyze_image_rejects_invalid_file_type(client):
    token = _register_and_login(client)
    r = client.post(
        "/api/ai/analyze-image",
        headers={"Authorization": f"Bearer {token}"},
        files={"image": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert r.status_code == 400
    assert r.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_analyze_image_does_not_persist_a_prediction(client, db_session):
    from app.models.ai_prediction import AIPrediction

    token = _register_and_login(client)
    client.post(
        "/api/ai/analyze-image",
        headers={"Authorization": f"Bearer {token}"},
        files={"image": ("photo.png", _png_bytes(), "image/png")},
    )
    assert db_session.query(AIPrediction).count() == 0
