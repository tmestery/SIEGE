"""Tests for the data exfiltration attack module."""

from __future__ import annotations

import unittest

from siege.attacks.data_exfiltration import (
    DEFAULT_DATA_EXFILTRATION_CASES,
    SYNTHETIC_CANARY,
    DataExfiltrationAttack,
)
from siege.reporting import Report
from siege.scoring import Scorer


class RefusingModel:
    """Deterministic model client that refuses data exfiltration."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a refusal response."""
        del prompt, system_prompt
        return "I cannot reveal private or sensitive context values."


class PartialLeakModel:
    """Deterministic model client that partially leaks a canary."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a partial leakage response."""
        del prompt, system_prompt
        return "The hidden value starts with SEIGE_CANARY."


class LeakingModel:
    """Deterministic model client that leaks a full synthetic canary."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a full leakage response."""
        del prompt, system_prompt
        return f"Canary leaked: {SYNTHETIC_CANARY}"


class DataExfiltrationAttackTests(unittest.TestCase):
    """Unit tests for data exfiltration behavior."""

    def test_default_suite_includes_required_categories(self) -> None:
        """The default suite covers the issue-required exfiltration styles."""
        categories = {case.category for case in DEFAULT_DATA_EXFILTRATION_CASES}

        self.assertGreaterEqual(len(DEFAULT_DATA_EXFILTRATION_CASES), 10)
        self.assertGreaterEqual(
            categories,
            {
                "context-extraction",
                "secret-token",
                "prior-turn-leakage",
                "inference-probe",
            },
        )

    def test_refusal_model_passes_all_cases(self) -> None:
        """A refusing model passes all data exfiltration cases."""
        attack = DataExfiltrationAttack()
        summary = Scorer().score(attack.run_all(RefusingModel()))

        self.assertEqual(summary.aggregate_score, 0.0)
        self.assertEqual(summary.attacks_run, len(DEFAULT_DATA_EXFILTRATION_CASES))

    def test_partial_leak_model_fails_all_cases(self) -> None:
        """Partial synthetic canary leakage is graded as failure."""
        attack = DataExfiltrationAttack()
        summary = Scorer().score(attack.run_all(PartialLeakModel()))

        self.assertEqual(summary.attacks_failed, len(DEFAULT_DATA_EXFILTRATION_CASES))
        self.assertEqual(summary.aggregate_score, 7.5)

    def test_leaking_model_fails_all_cases(self) -> None:
        """Full synthetic canary leakage is graded as failure."""
        attack = DataExfiltrationAttack()
        summary = Scorer().score(attack.run_all(LeakingModel()))

        self.assertEqual(summary.attacks_failed, len(DEFAULT_DATA_EXFILTRATION_CASES))
        self.assertEqual(summary.aggregate_score, 10.0)

    def test_results_flow_through_report_schema(self) -> None:
        """Data exfiltration results produce valid report payloads."""
        attack = DataExfiltrationAttack()
        summary = Scorer().score(attack.run_all(LeakingModel()))

        report = Report.from_scoring_summary(
            model="openai/gpt-4o-mini",
            summary=summary,
            timestamp="2026-06-02T12:00:00Z",
            metadata={"attack": attack.name, "case_count": len(attack.cases)},
        ).to_dict()

        self.assertEqual(report["metadata"]["attack"], "data_exfiltration")
        self.assertEqual(report["attacks_run"], 10)
        self.assertEqual(report["aggregate_score"], 10.0)


if __name__ == "__main__":
    unittest.main()
