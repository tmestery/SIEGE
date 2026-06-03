"""Example attack implementation for authors building SEIGE modules."""

from __future__ import annotations

from typing import Any

from siege.attacks.base import Attack, AttackResult


class StubAttack(Attack):
    """Example attack that demonstrates the attack module interface."""

    @property
    def name(self) -> str:
        """Return the attack name."""
        return "stub"

    @property
    def description(self) -> str:
        """Return the attack description."""
        return "Example attack stub for validating the module interface."

    @property
    def severity(self) -> str:
        """Return the attack severity."""
        return "informational"

    def run(self, model: Any, prompt: str) -> AttackResult:
        """Run the example attack and return a placeholder result."""
        del model
        return AttackResult(
            prompt=prompt,
            response="",
            passed=True,
            severity=self.severity,
            notes="Stub attack did not execute a real model evaluation.",
        )
