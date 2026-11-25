import hashlib
import random
import time
from typing import Dict, List

from ai.inference.base import AIAnalysisResult, AIProvider
from ai.preprocessing.image_utils import decode_and_normalize

MODEL_VERSION = "mock-v1.0"

_CATEGORY_WEIGHTS: Dict[str, float] = {
    "POTHOLE": 22,
    "GARBAGE": 20,
    "BROKEN_STREETLIGHT": 12,
    "WATER_LEAKAGE": 8,
    "DRAINAGE": 8,
    "WATERLOGGING": 7,
    "FALLEN_TREE": 6,
    "DAMAGED_SIGN": 6,
    "ILLEGAL_DUMPING": 6,
    "CONSTRUCTION_OBSTRUCTION": 4,
    "OTHER": 1,
}

_SEVERITY_WEIGHTS_BY_CATEGORY: Dict[str, Dict[str, float]] = {
    "POTHOLE": {"LOW": 5, "MEDIUM": 25, "HIGH": 45, "CRITICAL": 25},
    "GARBAGE": {"LOW": 15, "MEDIUM": 45, "HIGH": 30, "CRITICAL": 10},
    "BROKEN_STREETLIGHT": {"LOW": 35, "MEDIUM": 40, "HIGH": 20, "CRITICAL": 5},
    "WATER_LEAKAGE": {"LOW": 10, "MEDIUM": 35, "HIGH": 40, "CRITICAL": 15},
    "DRAINAGE": {"LOW": 10, "MEDIUM": 30, "HIGH": 40, "CRITICAL": 20},
    "WATERLOGGING": {"LOW": 5, "MEDIUM": 25, "HIGH": 40, "CRITICAL": 30},
    "FALLEN_TREE": {"LOW": 5, "MEDIUM": 20, "HIGH": 45, "CRITICAL": 30},
    "DAMAGED_SIGN": {"LOW": 40, "MEDIUM": 40, "HIGH": 17, "CRITICAL": 3},
    "ILLEGAL_DUMPING": {"LOW": 15, "MEDIUM": 40, "HIGH": 35, "CRITICAL": 10},
    "CONSTRUCTION_OBSTRUCTION": {"LOW": 15, "MEDIUM": 45, "HIGH": 30, "CRITICAL": 10},
    "OTHER": {"LOW": 25, "MEDIUM": 50, "HIGH": 20, "CRITICAL": 5},
}

_DETECTED_OBJECT_LABELS: Dict[str, List[str]] = {
    "POTHOLE": ["pothole", "road surface damage"],
    "GARBAGE": ["garbage pile", "waste debris"],
    "BROKEN_STREETLIGHT": ["streetlight pole", "damaged fixture"],
    "WATER_LEAKAGE": ["water pipe", "leak"],
    "DRAINAGE": ["drain", "blocked drainage"],
    "WATERLOGGING": ["standing water", "flooded surface"],
    "FALLEN_TREE": ["fallen tree", "tree branch"],
    "DAMAGED_SIGN": ["road sign", "damaged signage"],
    "ILLEGAL_DUMPING": ["dumped waste", "debris pile"],
    "CONSTRUCTION_OBSTRUCTION": ["construction material", "barrier"],
    "OTHER": ["unidentified object"],
}


class MockAIProvider(AIProvider):
    @property
    def provider_name(self) -> str:
        return "mock"

    async def analyze(self, image_bytes: bytes, content_type: str) -> AIAnalysisResult:
        start = time.perf_counter()

        decode_and_normalize(image_bytes)

        digest = hashlib.sha256(image_bytes).digest()
        rng = random.Random(digest)

        category = _weighted_choice(rng, _CATEGORY_WEIGHTS)
        severity = _weighted_choice(rng, _SEVERITY_WEIGHTS_BY_CATEGORY[category])

        if category == "OTHER":
            confidence = round(rng.uniform(0.30, 0.55), 2)
        else:
            confidence = round(rng.uniform(0.62, 0.97), 2)

        detected_objects = list(_DETECTED_OBJECT_LABELS[category])
        if rng.random() < 0.35 and len(detected_objects) > 1:
            detected_objects = detected_objects[:1]

        elapsed_ms = (time.perf_counter() - start) * 1000

        return AIAnalysisResult(
            category=category,
            confidence=confidence,
            severity=severity,
            detected_objects=detected_objects,
            model_version=MODEL_VERSION,
            inference_time_ms=round(elapsed_ms, 2),
        )


def _weighted_choice(rng: random.Random, weights: Dict[str, float]) -> str:
    keys = list(weights.keys())
    values = list(weights.values())
    return rng.choices(keys, weights=values, k=1)[0]
