import os

from ai.inference.base import AIAnalysisResult, AIProvider, AIProviderError
from ai.preprocessing.image_utils import decode_and_normalize


class YOLOProvider(AIProvider):
    def __init__(self, model_path: str):
        self._model_path = model_path
        self._model = None

    @property
    def provider_name(self) -> str:
        return "yolo"

    async def analyze(self, image_bytes: bytes, content_type: str) -> AIAnalysisResult:
        if not os.path.isfile(self._model_path):
            raise AIProviderError(
                f"No YOLO model found at '{self._model_path}'. Set AI_PROVIDER=mock for development, "
                f"or place a trained model at AI_MODEL_PATH to use this provider."
            )

        decode_and_normalize(image_bytes)

        raise AIProviderError(
            "YOLOProvider inference is not yet implemented. This is a defined integration point, "
            "not a functioning detector — see ai/inference/yolo_provider.py for what's needed."
        )
