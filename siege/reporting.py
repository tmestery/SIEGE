"""Structured JSON reports for SEIGE evaluation runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from siege.scoring import AttackScore, ScoringSummary


JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ReportResult:
    """Serializable result entry for one scored attack."""

    prompt: str
    response: str
    passed: bool
    severity: str
    severity_score: float
    category: str
    category_weight: float
    strength: str
    strength_score: float
    risk_score: float
    weighted_risk_score: float
    notes: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_attack_score(cls, score: AttackScore) -> ReportResult:
        """Create a report result from a scored attack."""
        return cls(
            prompt=score.prompt,
            response=score.response,
            passed=score.passed,
            severity=score.severity,
            severity_score=score.severity_score,
            category=score.category,
            category_weight=score.category_weight,
            strength=score.strength,
            strength_score=score.strength_score,
            risk_score=score.risk_score,
            weighted_risk_score=score.weighted_risk_score,
            notes=score.notes,
            metadata=dict(score.metadata),
        )

    def to_dict(self) -> JsonObject:
        """Return this result as a JSON-serializable dictionary."""
        return {
            "prompt": self.prompt,
            "response": self.response,
            "passed": self.passed,
            "severity": self.severity,
            "severity_score": self.severity_score,
            "category": self.category,
            "category_weight": self.category_weight,
            "strength": self.strength,
            "strength_score": self.strength_score,
            "risk_score": self.risk_score,
            "weighted_risk_score": self.weighted_risk_score,
            "notes": self.notes,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class Report:
    """JSON-serializable schema for a complete SEIGE evaluation run."""

    model: str
    timestamp: str
    attacks_run: int
    results: tuple[ReportResult, ...]
    aggregate_score: float
    category_scores: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_scoring_summary(
        cls,
        *,
        model: str,
        summary: ScoringSummary,
        timestamp: datetime | str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Report:
        """Build a report from scoring output."""
        return cls(
            model=model,
            timestamp=cls._format_timestamp(timestamp),
            attacks_run=summary.attacks_run,
            results=tuple(
                ReportResult.from_attack_score(result) for result in summary.results
            ),
            aggregate_score=summary.aggregate_score,
            category_scores={
                category: {
                    "score": score.score,
                    "attacks_run": score.attacks_run,
                    "attacks_passed": score.attacks_passed,
                    "attacks_failed": score.attacks_failed,
                }
                for category, score in summary.category_scores.items()
            },
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> JsonObject:
        """Return this report as a JSON-serializable dictionary."""
        return {
            "model": self.model,
            "timestamp": self.timestamp,
            "attacks_run": self.attacks_run,
            "results": [result.to_dict() for result in self.results],
            "aggregate_score": self.aggregate_score,
            "category_scores": dict(self.category_scores),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def _format_timestamp(timestamp: datetime | str | None) -> str:
        """Return an ISO 8601 UTC timestamp string."""
        if timestamp is None:
            timestamp = datetime.now(UTC)
        if isinstance(timestamp, str):
            return timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        return timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")


class ReportWriter:
    """Write SEIGE reports as valid, deterministic JSON files."""

    def write(self, report: Report, path: str | Path) -> Path:
        """Write a report to a JSON file and return the resolved path."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output_path
