from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class AIAnalysisResult:
    category: str
    confidence: float
    severity: str
    detected_objects: List[str] = field(default_factory=list)
    model_version: str = "unknown"
    inference_time_ms: float = 0.0


class AIProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    async def analyze(self, image_bytes: bytes, content_type: str) -> AIAnalysisResult:
        ...


class AIProviderError(Exception):
    pass
