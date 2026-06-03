"""Tests for deterministic attack scoring."""

from __future__ import annotations

import unittest

from siege.attacks.base import AttackResult
from siege.scoring import Scorer


class ScorerTests(unittest.TestCase):
    """Unit tests for the scoring interface."""

    def test_scores_each_attack_and_aggregate_model_risk(self) -> None:
        """Failed attacks contribute severity risk; passed attacks do not."""
        results = [
            AttackResult(
                prompt="benign prompt",
                response="safe response",
                passed=True,
                severity="critical",
                notes="model resisted the attack",
            ),
            AttackResult(
                prompt="malicious prompt",
                response="unsafe response",
                passed=False,
                severity="high",
                notes="model complied with the attack",
            ),
        ]

        summary = Scorer().score(results)

        self.assertEqual(summary.attacks_run, 2)
        self.assertEqual(summary.attacks_passed, 1)
        self.assertEqual(summary.attacks_failed, 1)
        self.assertEqual(summary.results[0].severity_score, 10.0)
        self.assertEqual(summary.results[0].risk_score, 0.0)
        self.assertEqual(summary.results[1].severity_score, 7.5)
        self.assertEqual(summary.results[1].risk_score, 7.5)
        self.assertEqual(summary.aggregate_score, 3.75)

    def test_empty_result_set_scores_zero(self) -> None:
        """No attacks run produces a zero aggregate score."""
        summary = Scorer().score([])

        self.assertEqual(summary.aggregate_score, 0.0)
        self.assertEqual(summary.attacks_run, 0)
        self.assertEqual(summary.results, ())

    def test_numeric_severity_strings_are_supported(self) -> None:
        """Numeric severity strings can be used directly on the 0-10 scale."""
        result = AttackResult(
            prompt="prompt",
            response="response",
            passed=False,
            severity="8.25",
            notes="custom severity",
        )

        summary = Scorer().score([result])

        self.assertEqual(summary.results[0].severity_score, 8.25)
        self.assertEqual(summary.aggregate_score, 8.25)

    def test_unknown_severity_raises_value_error(self) -> None:
        """Unknown severity labels fail loudly instead of guessing a score."""
        result = AttackResult(
            prompt="prompt",
            response="response",
            passed=False,
            severity="severe-ish",
            notes="invalid severity",
        )

        with self.assertRaises(ValueError):
            Scorer().score([result])


if __name__ == "__main__":
    unittest.main()
