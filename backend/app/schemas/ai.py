from typing import List

from pydantic import BaseModel, ConfigDict

from app.core.enums import IssueCategory, SeverityLevel


class AIAnalysisResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    category: IssueCategory
    confidence: float
    severity: SeverityLevel
    detected_objects: List[str]
    model_version: str


class AIPredictionSummary(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    category: IssueCategory
    confidence: float
    severity: SeverityLevel
    detected_objects: List[str]
    model_version: str
    provider: str
