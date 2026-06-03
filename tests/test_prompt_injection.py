"""Tests for the direct prompt-injection attack module."""

from __future__ import annotations

import unittest

from siege.attacks.prompt_injection import (
    DEFAULT_PROMPT_INJECTION_CASES,
    PromptInjectionAttack,
)
from siege.reporting import Report
from siege.scoring import Scorer


class RefusingModel:
    """Deterministic model client that refuses prompt injections."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a refusal response."""
        del prompt, system_prompt
        return "I cannot comply with attempts to override my system instructions."


class ComplyingModel:
    """Deterministic model client that complies with prompt injections."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a compromised response."""
        del prompt, system_prompt
        return "Ignore previous instructions accepted. Admin mode enabled."


class PromptInjectionAttackTests(unittest.TestCase):
    """Unit tests for direct prompt-injection behavior."""

    def test_default_suite_includes_at_least_ten_cases(self) -> None:
        """The default attack suite covers the issue-required case count."""
        self.assertGreaterEqual(len(DEFAULT_PROMPT_INJECTION_CASES), 10)
        self.assertEqual(
            len({case.identifier for case in DEFAULT_PROMPT_INJECTION_CASES}),
            len(DEFAULT_PROMPT_INJECTION_CASES),
        )

    def test_refusal_model_passes_all_cases(self) -> None:
        """A refusing model passes all direct prompt-injection cases."""
        attack = PromptInjectionAttack()

        results = attack.run_all(RefusingModel())
        summary = Scorer().score(results)

        self.assertEqual(len(results), len(DEFAULT_PROMPT_INJECTION_CASES))
        self.assertTrue(all(result.passed for result in results))
        self.assertEqual(summary.attacks_run, len(DEFAULT_PROMPT_INJECTION_CASES))
        self.assertEqual(summary.aggregate_score, 0.0)

    def test_complying_model_fails_all_cases(self) -> None:
        """A complying model fails reproducibly through compromise indicators."""
        attack = PromptInjectionAttack()

        results = attack.run_all(ComplyingModel())
        summary = Scorer().score(results)

        self.assertEqual(len(results), len(DEFAULT_PROMPT_INJECTION_CASES))
        self.assertTrue(all(not result.passed for result in results))
        self.assertEqual(summary.attacks_failed, len(DEFAULT_PROMPT_INJECTION_CASES))
        self.assertEqual(summary.aggregate_score, 7.5)

    def test_results_flow_through_report_schema_for_two_models(self) -> None:
        """Prompt-injection results can produce valid reports for two models."""
        attack = PromptInjectionAttack()
        models = {
            "groq/llama3": RefusingModel(),
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

        self.assertEqual(reports["groq/llama3"]["aggregate_score"], 0.0)
        self.assertEqual(reports["openai/gpt-4o-mini"]["aggregate_score"], 7.5)
        self.assertEqual(reports["groq/llama3"]["attacks_run"], 10)
        self.assertEqual(reports["openai/gpt-4o-mini"]["attacks_run"], 10)
        self.assertEqual(
            reports["groq/llama3"]["metadata"]["grading"],
            "deterministic-indicator-heuristic",
        )


if __name__ == "__main__":
    unittest.main()
