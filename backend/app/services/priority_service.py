"""
Priority scoring engine.

Formula (per spec):
    Priority Score = Severity Score + Report Frequency + Location Risk + Complaint Age
    normalized to 0-100.

Design notes:
  - Severity score alone can already reach 100 (CRITICAL), so it is the
    dominant term. The other three factors are capped at smaller
    contributions (15 / 15 / 10) so a LOW-severity issue with heavy
    duplicate reports, high location risk, and old age can escalate
    into MEDIUM/HIGH territory, but a CRITICAL report is never
    outranked by a pile of LOW-severity duplicates.
  - Report Frequency is driven by CivicIssue.duplicate_count, which is
    populated by the Phase 7 duplicate-detection service. Until that
    phase runs, every issue's duplicate_count is 0 and this term
    contributes nothing — that's correct, not a bug: there is no
    frequency signal to score yet.
  - Location Risk sums the risk_weight of every active RiskZone within
    its radius_meters of the issue's location (schools, hospitals,
    major roads, transit hubs, high-population zones — see the
    risk_zones table). Until Phase 12 seeds that table, this term is
    also 0 for every issue in a fresh database, which is expected.
  - Complaint Age grows with time since the issue was reported. It is
    computed correctly here, but nothing in the codebase yet re-runs
    this calculation on a schedule (that would be a Phase 13 background
    job) — today it is recomputed whenever an issue is created or when
    its category/severity is edited by the citizen. An issue that sits
    untouched will not see its age score increase until one of those
    triggers fires again.

This is a pure, dependency-injected service: given the inputs, it
returns a deterministic score. Nothing here queries state that isn't
explicitly passed in or fetched via the one documented risk-zone query,
which makes it straightforward to unit test.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import PriorityLevel, SeverityLevel
from app.models.civic_issue import CivicIssue
from app.models.location import RiskZone
from app.utils.geo import haversine_km

SEVERITY_SCORES: dict[SeverityLevel, float] = {
    SeverityLevel.LOW: 20,
    SeverityLevel.MEDIUM: 40,
    SeverityLevel.HIGH: 70,
    SeverityLevel.CRITICAL: 100,
}

FREQUENCY_POINTS_PER_DUPLICATE = 3.0
FREQUENCY_CAP = 15.0

LOCATION_RISK_CAP = 15.0

AGE_POINTS_PER_DAY = 1.0
AGE_CAP = 10.0

PRIORITY_LEVEL_THRESHOLDS: list[tuple[float, PriorityLevel]] = [
    (30, PriorityLevel.LOW),
    (60, PriorityLevel.MEDIUM),
    (80, PriorityLevel.HIGH),
    (100, PriorityLevel.CRITICAL),
]


@dataclass
class PriorityBreakdown:
    severity_score: float
    frequency_score: float
    location_risk_score: float
    age_score: float
    raw_score: float
    final_score: float
    level: PriorityLevel


def level_for_score(score: float) -> PriorityLevel:
    for threshold, level in PRIORITY_LEVEL_THRESHOLDS:
        if score <= threshold:
            return level
    return PriorityLevel.CRITICAL


def calculate_priority(
    *,
    severity: SeverityLevel,
    duplicate_count: int,
    location_risk_score: float,
    age_hours: float,
) -> PriorityBreakdown:
    severity_score = SEVERITY_SCORES[severity]

    frequency_score = min(max(duplicate_count, 0) * FREQUENCY_POINTS_PER_DUPLICATE, FREQUENCY_CAP)

    location_risk_score = min(max(location_risk_score, 0.0), LOCATION_RISK_CAP)

    age_days = max(age_hours, 0.0) / 24.0
    age_score = min(age_days * AGE_POINTS_PER_DAY, AGE_CAP)

    raw_score = severity_score + frequency_score + location_risk_score + age_score
    final_score = min(max(raw_score, 0.0), 100.0)

    return PriorityBreakdown(
        severity_score=severity_score,
        frequency_score=frequency_score,
        location_risk_score=location_risk_score,
        age_score=age_score,
        raw_score=raw_score,
        final_score=round(final_score, 2),
        level=level_for_score(final_score),
    )


class PriorityService:
    def __init__(self, db: Session):
        self.db = db

    def location_risk_score(self, latitude: float, longitude: float) -> float:
        zones = self.db.execute(select(RiskZone).where(RiskZone.is_active.is_(True))).scalars().all()

        total = 0.0
        for zone in zones:
            distance_m = haversine_km(latitude, longitude, zone.latitude, zone.longitude) * 1000
            if distance_m <= zone.radius_meters:
                total += zone.risk_weight
        return total

    def compute_for_issue(self, issue: CivicIssue, *, as_of: Optional[datetime] = None) -> PriorityBreakdown:
        now = as_of or datetime.now(timezone.utc)
        created_at = issue.created_at
        if created_at is not None and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_hours = max((now - created_at).total_seconds() / 3600, 0.0) if created_at else 0.0

        location_risk = self.location_risk_score(issue.location.latitude, issue.location.longitude)

        return calculate_priority(
            severity=issue.severity,
            duplicate_count=issue.duplicate_count,
            location_risk_score=location_risk,
            age_hours=age_hours,
        )

    def compute_and_apply(self, issue: CivicIssue, *, as_of: Optional[datetime] = None) -> PriorityBreakdown:
        breakdown = self.compute_for_issue(issue, as_of=as_of)
        issue.priority_score = breakdown.final_score
        issue.priority_level = breakdown.level
        return breakdown
