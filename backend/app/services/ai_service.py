from typing import Optional

from sqlalchemy.orm import Session

from ai.inference.base import AIProvider, AIProviderError
from ai.inference.mock_provider import MockAIProvider
from ai.inference.yolo_provider import YOLOProvider
from app.core.config import settings
from app.core.enums import IssueCategory, SeverityLevel
from app.core.exceptions import AppError
from app.models.ai_prediction import AIPrediction
from app.schemas.ai import AIAnalysisResponse


def get_ai_provider() -> AIProvider:
    if settings.AI_PROVIDER == "mock":
        return MockAIProvider()
    if settings.AI_PROVIDER == "yolo":
        return YOLOProvider(model_path=settings.AI_MODEL_PATH)
    raise ValueError(f"Unknown AI_PROVIDER '{settings.AI_PROVIDER}'. Expected 'mock' or 'yolo'.")


class AIAnalysisError(AppError):
    status_code = 503
    error_code = "AI_ANALYSIS_UNAVAILABLE"


class AIService:
    def __init__(self, db: Session, provider: Optional[AIProvider] = None):
        self.db = db
        self.provider = provider or get_ai_provider()

    async def analyze(self, image_bytes: bytes, content_type: str) -> AIAnalysisResponse:
        try:
            result = await self.provider.analyze(image_bytes, content_type)
        except AIProviderError as exc:
            raise AIAnalysisError(str(exc))

        return AIAnalysisResponse(
            category=result.category,
            confidence=result.confidence,
            severity=result.severity,
            detected_objects=result.detected_objects,
            model_version=result.model_version,
        )

    async def analyze_and_store(
        self, *, issue_id: int, issue_image_id: Optional[int], image_bytes: bytes, content_type: str
    ) -> AIPrediction:
        result = await self.provider.analyze(image_bytes, content_type)

        predicted_category = IssueCategory(result.category)
        predicted_severity = SeverityLevel(result.severity)

        prediction = AIPrediction(
            issue_id=issue_id,
            issue_image_id=issue_image_id,
            predicted_category=predicted_category,
            confidence=result.confidence,
            predicted_severity=predicted_severity,
            detected_objects=result.detected_objects,
            model_version=result.model_version,
            provider=self.provider.provider_name,
            inference_time_ms=result.inference_time_ms,
        )
        self.db.add(prediction)
        self.db.flush()
        return prediction
