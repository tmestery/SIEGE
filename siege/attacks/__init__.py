"""Attack module interfaces and examples."""

from siege.attacks.base import Attack, AttackResult
from siege.attacks.prompt_injection import (
    DEFAULT_PROMPT_INJECTION_CASES,
    PromptInjectionAttack,
    PromptInjectionCase,
)
from siege.attacks.stub import StubAttack

__all__ = [
    "Attack",
    "AttackResult",
    "DEFAULT_PROMPT_INJECTION_CASES",
    "PromptInjectionAttack",
    "PromptInjectionCase",
    "StubAttack",
]
