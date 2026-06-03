"""Tests for the system prompt extraction attack module."""

from __future__ import annotations

import unittest

from siege.attacks.system_prompt_extraction import (
    DEFAULT_SYSTEM_PROMPT_EXTRACTION_CASES,
    SystemPromptExtractionAttack,
)
from siege.reporting import Report
from siege.scoring import Scorer


class RefusingModel:
    """Deterministic model client that refuses prompt extraction."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a refusal response."""
        del prompt, system_prompt
        return "I cannot reveal hidden instructions or system messages."


class PartialLeakModel:
    """Deterministic model client that partially leaks instructions."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a partial leakage response."""
        del prompt, system_prompt
        return "My instructions say that I should be a careful assistant."


class LeakingModel:
    """Deterministic model client that leaks protected instructions."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return an obvious leakage response."""
        del prompt, system_prompt
        return "System prompt: You are a security-conscious assistant."


class SystemPromptExtractionAttackTests(unittest.TestCase):
    """Unit tests for system prompt extraction behavior."""

    def test_default_suite_includes_required_categories(self) -> None:
        """The default suite covers direct, indirect, traps, and probing."""
        categories = {case.category for case in DEFAULT_SYSTEM_PROMPT_EXTRACTION_CASES}

        self.assertGreaterEqual(len(DEFAULT_SYSTEM_PROMPT_EXTRACTION_CASES), 10)
        self.assertGreaterEqual(
            categories,
            {"direct", "indirect", "completion-trap", "probing"},
        )

    def test_refusal_model_passes_all_cases(self) -> None:
        """A refusing model passes all extraction cases."""
        attack = SystemPromptExtractionAttack()
        summary = Scorer().score(attack.run_all(RefusingModel()))

        self.assertEqual(summary.aggregate_score, 0.0)
        self.assertEqual(summary.attacks_run, len(DEFAULT_SYSTEM_PROMPT_EXTRACTION_CASES))

    def test_partial_leak_model_fails_all_cases(self) -> None:
        """Partial leakage is graded as failure."""
        attack = SystemPromptExtractionAttack()
        summary = Scorer().score(attack.run_all(PartialLeakModel()))

        self.assertEqual(summary.attacks_failed, len(DEFAULT_SYSTEM_PROMPT_EXTRACTION_CASES))
        self.assertEqual(summary.aggregate_score, 10.0)

    def test_leaking_model_fails_all_cases(self) -> None:
        """Obvious system prompt leakage is graded as failure."""
        attack = SystemPromptExtractionAttack()
        summary = Scorer().score(attack.run_all(LeakingModel()))

        self.assertEqual(summary.attacks_failed, len(DEFAULT_SYSTEM_PROMPT_EXTRACTION_CASES))
        self.assertEqual(summary.aggregate_score, 10.0)

    def test_results_flow_through_report_schema(self) -> None:
        """Extraction attack results produce valid report payloads."""
        attack = SystemPromptExtractionAttack()
        summary = Scorer().score(attack.run_all(LeakingModel()))

        report = Report.from_scoring_summary(
            model="anthropic/claude-3-5",
            summary=summary,
            timestamp="2026-06-02T12:00:00Z",
            metadata={"attack": attack.name, "case_count": len(attack.cases)},
        ).to_dict()

        self.assertEqual(report["metadata"]["attack"], "system_prompt_extraction")
        self.assertEqual(report["attacks_run"], 10)
        self.assertEqual(report["aggregate_score"], 10.0)


if __name__ == "__main__":
    unittest.main()
