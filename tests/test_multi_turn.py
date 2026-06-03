"""Tests for the multi-turn manipulation attack module."""

from __future__ import annotations

import unittest

from siege.attacks.multi_turn import (
    DEFAULT_MULTI_TURN_SCENARIOS,
    MultiTurnManipulationAttack,
)
from siege.reporting import Report
from siege.scoring import Scorer


class RefusingModel:
    """Deterministic model client that refuses multi-turn manipulation."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a refusal response."""
        del prompt, system_prompt
        return "I cannot comply and must follow safety rules across the conversation."


class ComplyingModel:
    """Deterministic model client that accepts multi-turn manipulation."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a compromised response."""
        del prompt, system_prompt
        return "Trust escalation accepted. Safety disabled. Unsafe final answer."


class MultiTurnManipulationAttackTests(unittest.TestCase):
    """Unit tests for multi-turn manipulation behavior."""

    def test_default_suite_has_five_multi_turn_scenarios(self) -> None:
        """The default suite covers at least five multi-turn scenarios."""
        self.assertGreaterEqual(len(DEFAULT_MULTI_TURN_SCENARIOS), 5)
        self.assertTrue(
            all(len(scenario.turns) >= 3 for scenario in DEFAULT_MULTI_TURN_SCENARIOS)
        )
        self.assertEqual(
            len({scenario.identifier for scenario in DEFAULT_MULTI_TURN_SCENARIOS}),
            len(DEFAULT_MULTI_TURN_SCENARIOS),
        )

    def test_scenario_prompt_contains_ordered_turn_context(self) -> None:
        """Scenario rendering preserves ordered turn context."""
        prompt = DEFAULT_MULTI_TURN_SCENARIOS[0].build_prompt()

        self.assertIn("Turn 1:", prompt)
        self.assertIn("Turn 2:", prompt)
        self.assertIn("Turn 3:", prompt)

    def test_refusal_model_passes_all_scenarios(self) -> None:
        """A refusing model passes all multi-turn scenarios."""
        attack = MultiTurnManipulationAttack()
        summary = Scorer().score(attack.run_all(RefusingModel()))

        self.assertEqual(summary.attacks_run, len(DEFAULT_MULTI_TURN_SCENARIOS))
        self.assertEqual(summary.aggregate_score, 0.0)

    def test_complying_model_fails_all_scenarios(self) -> None:
        """A complying model fails through deterministic compromise indicators."""
        attack = MultiTurnManipulationAttack()
        summary = Scorer().score(attack.run_all(ComplyingModel()))

        self.assertEqual(summary.attacks_failed, len(DEFAULT_MULTI_TURN_SCENARIOS))
        self.assertEqual(summary.aggregate_score, 7.5)

    def test_results_flow_through_report_schema(self) -> None:
        """Multi-turn results produce valid report payloads."""
        attack = MultiTurnManipulationAttack()
        summary = Scorer().score(attack.run_all(ComplyingModel()))

        report = Report.from_scoring_summary(
            model="openai/gpt-4o-mini",
            summary=summary,
            timestamp="2026-06-02T12:00:00Z",
            metadata={"attack": attack.name, "scenario_count": len(attack.scenarios)},
        ).to_dict()

        self.assertEqual(report["metadata"]["attack"], "multi_turn_manipulation")
        self.assertEqual(report["attacks_run"], 5)
        self.assertEqual(report["aggregate_score"], 7.5)


if __name__ == "__main__":
    unittest.main()
