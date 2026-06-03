"""Attack module interfaces and examples."""

from siege.attacks.adversarial_suffix import (
    DEFAULT_ADVERSARIAL_SUFFIX_CASES,
    AdversarialSuffixAttack,
    AdversarialSuffixCase,
)
from siege.attacks.base import Attack, AttackResult
from siege.attacks.jailbreaking import (
    DEFAULT_JAILBREAK_CASES,
    JailbreakCase,
    JailbreakingAttack,
)
from siege.attacks.prompt_injection import (
    DEFAULT_PROMPT_INJECTION_CASES,
    PromptInjectionAttack,
    PromptInjectionCase,
)
from siege.attacks.stub import StubAttack

__all__ = [
    "Attack",
    "AttackResult",
    "AdversarialSuffixAttack",
    "AdversarialSuffixCase",
    "DEFAULT_ADVERSARIAL_SUFFIX_CASES",
    "DEFAULT_JAILBREAK_CASES",
    "DEFAULT_PROMPT_INJECTION_CASES",
    "JailbreakCase",
    "JailbreakingAttack",
    "PromptInjectionAttack",
    "PromptInjectionCase",
    "StubAttack",
]
