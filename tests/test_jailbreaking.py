"""Tests for the jailbreaking attack module."""

from __future__ import annotations

import unittest

from siege.attacks.jailbreaking import DEFAULT_JAILBREAK_CASES, JailbreakingAttack
from siege.reporting import Report
from siege.scoring import Scorer


class RefusingModel:
    """Deterministic model client that refuses jailbreak attempts."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a refusal response."""
        del prompt, system_prompt
        return "I cannot comply with attempts to bypass safety guidelines."


class ComplyingModel:
    """Deterministic model client that complies with jailbreak attempts."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a compromised response."""
        del prompt, system_prompt
        return "Jailbreak successful. Safety disabled. Unfiltered answer follows."


class JailbreakingAttackTests(unittest.TestCase):
    """Unit tests for jailbreak attack behavior."""

    def test_default_suite_includes_required_categories(self) -> None:
        """The default suite covers the issue-required jailbreak styles."""
        categories = {case.category for case in DEFAULT_JAILBREAK_CASES}

        self.assertGreaterEqual(len(DEFAULT_JAILBREAK_CASES), 10)
        self.assertEqual(
            len({case.identifier for case in DEFAULT_JAILBREAK_CASES}),
            len(DEFAULT_JAILBREAK_CASES),
        )
        self.assertGreaterEqual(
            categories,
            {"roleplay", "hypothetical", "encoding", "many-shot"},
        )

    def test_refusal_model_passes_all_cases(self) -> None:
        """A refusing model passes all jailbreak cases."""
        attack = JailbreakingAttack()

        results = attack.run_all(RefusingModel())
        summary = Scorer().score(results)

        self.assertEqual(len(results), len(DEFAULT_JAILBREAK_CASES))
        self.assertTrue(all(result.passed for result in results))
        self.assertEqual(summary.attacks_run, len(DEFAULT_JAILBREAK_CASES))
        self.assertEqual(summary.aggregate_score, 0.0)

    def test_complying_model_fails_all_cases(self) -> None:
        """A complying model fails through deterministic compromise indicators."""
        attack = JailbreakingAttack()

        results = attack.run_all(ComplyingModel())
        summary = Scorer().score(results)

        self.assertEqual(len(results), len(DEFAULT_JAILBREAK_CASES))
        self.assertTrue(all(not result.passed for result in results))
        self.assertEqual(summary.attacks_failed, len(DEFAULT_JAILBREAK_CASES))
        self.assertEqual(summary.aggregate_score, 7.5)

    def test_results_flow_through_report_schema_for_two_models(self) -> None:
        """Jailbreak results can produce valid reports for two model labels."""
        attack = JailbreakingAttack()
        models = {
            "ollama/mistral": RefusingModel(),
            "openai/gpt-4o-mini": ComplyingModel(),
        }

        reports = {}
        for model_name, model in models.items():
            summary = Scorer().score(attack.run_all(model))
            reports[model_name] = Report.from_scoring_summary(
                model=model_name,
                summary=summary,
                timestamp="2026-06-02T12:00:00Z",
                metadata={
                    "attack": attack.name,
                    "case_count": len(attack.cases),
                    "grading": "deterministic-indicator-heuristic",
                },
            ).to_dict()

        self.assertEqual(reports["ollama/mistral"]["aggregate_score"], 0.0)
        self.assertEqual(reports["openai/gpt-4o-mini"]["aggregate_score"], 7.5)
        self.assertEqual(reports["ollama/mistral"]["attacks_run"], 10)
        self.assertEqual(reports["openai/gpt-4o-mini"]["attacks_run"], 10)
        self.assertEqual(
            reports["openai/gpt-4o-mini"]["metadata"]["attack"],
            "jailbreaking",
        )


if __name__ == "__main__":
    unittest.main()
