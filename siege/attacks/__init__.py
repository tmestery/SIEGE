"""Attack module interfaces and examples."""

from siege.attacks.base import Attack, AttackResult
from siege.attacks.stub import StubAttack

__all__ = ["Attack", "AttackResult", "StubAttack"]
