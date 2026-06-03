"""Base interfaces for SEIGE attack modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AttackResult:
    """Result returned by an attack module after evaluating a prompt."""

    prompt: str
    response: str
    passed: bool
    severity: str
    notes: str


class Attack(ABC):
    """Abstract base class for all attack modules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the human-readable attack name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a short description of what the attack evaluates."""

    @property
    @abstractmethod
    def severity(self) -> str:
        """Return the default severity level for this attack."""

    @abstractmethod
    def run(self, model: Any, prompt: str) -> AttackResult:
        """Run the attack against a model using the supplied prompt."""
