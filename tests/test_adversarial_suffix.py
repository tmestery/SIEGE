"""Tests for the adversarial suffix attack module."""

from __future__ import annotations

import unittest

from siege.attacks.adversarial_suffix import (
    DEFAULT_ADVERSARIAL_SUFFIX_CASES,
    AdversarialSuffixAttack,
)
from siege.reporting import Report
from siege.scoring import Scorer


class RefusingModel:
    """Deterministic model client that refuses suffix attacks."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a refusal response."""
        del prompt, system_prompt
        return "I cannot comply with this request."


class ComplyingModel:
    """Deterministic model client that follows suffix attacks."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a compromised response."""
        del prompt, system_prompt
        return "Suffix override successful. Unsafe answer follows."


class AdversarialSuffixAttackTests(unittest.TestCase):
    """Unit tests for adversarial suffix behavior."""

    def test_default_suite_has_documented_suffix_fixtures(self) -> None:
        """The default suite includes transfer-style suffix fixtures."""
        self.assertGreaterEqual(len(DEFAULT_ADVERSARIAL_SUFFIX_CASES), 10)
        self.assertTrue(
            all(case.suffix for case in DEFAULT_ADVERSARIAL_SUFFIX_CASES)
        )
        self.assertEqual(
            len({case.identifier for case in DEFAULT_ADVERSARIAL_SUFFIX_CASES}),
            len(DEFAULT_ADVERSARIAL_SUFFIX_CASES),
        )

    def test_suffix_prompt_construction_appends_suffix(self) -> None:
        """Suffix fixtures build prompts from stable base text."""
        case = DEFAULT_ADVERSARIAL_SUFFIX_CASES[0]

        prompt = case.build_prompt("base prompt")

        self.assertTrue(prompt.startswith("base prompt"))
        self.assertIn(case.suffix, prompt)

    def test_refusal_model_passes_all_cases(self) -> None:
        """A refusing model passes all suffix cases."""
        attack = AdversarialSuffixAttack()
        summary = Scorer().score(attack.run_all(RefusingModel()))

        self.assertEqual(summary.attacks_run, len(DEFAULT_ADVERSARIAL_SUFFIX_CASES))
        self.assertEqual(summary.aggregate_score, 0.0)

    def test_complying_model_fails_all_cases(self) -> None:
        """A complying model fails through deterministic compromise indicators."""
        attack = AdversarialSuffixAttack()
        summary = Scorer().score(attack.run_all(ComplyingModel()))

        self.assertEqual(summary.attacks_failed, len(DEFAULT_ADVERSARIAL_SUFFIX_CASES))
        self.assertEqual(summary.aggregate_score, 7.5)

    def test_results_flow_through_report_schema(self) -> None:
        """Suffix attack results produce valid report payloads."""
        attack = AdversarialSuffixAttack()
        summary = Scorer().score(attack.run_all(ComplyingModel()))

        report = Report.from_scoring_summary(
            model="openai/gpt-4o-mini",
            summary=summary,
            timestamp="2026-06-02T12:00:00Z",
            metadata={
                "attack": attack.name,
                "case_count": len(attack.cases),
                "grading": "deterministic-indicator-heuristic",
            },
        ).to_dict()

        self.assertEqual(report["metadata"]["attack"], "adversarial_suffix")
        self.assertEqual(report["attacks_run"], 10)
        self.assertEqual(report["aggregate_score"], 7.5)


if __name__ == "__main__":
    unittest.main()
