"""Base model provider interface for SEIGE."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass


class ModelConfigurationError(RuntimeError):
    """Raised when a model client cannot be configured."""


@dataclass(frozen=True)
class ModelSpec:
    """Parsed provider/model identifier from CLI-style model strings."""

    provider: str
    model: str


class ModelClient(ABC):
    """Abstract base class for all model provider clients."""

    def __init__(self, model: str) -> None:
        """Create a model client for a provider-specific model name."""
        self.model = model

    @abstractmethod
    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a completion for a prompt using an optional system prompt."""


def parse_model_spec(model_spec: str) -> ModelSpec:
    """Parse a `provider/model` string into a model specification."""
    provider, separator, model = model_spec.strip().partition("/")
    if not separator or not provider or not model:
        raise ValueError(
            "Model must use 'provider/model' format, such as 'groq/llama3'."
        )

    return ModelSpec(provider=provider.lower(), model=model)


def load_environment() -> None:
    """Load API keys from `.env` using python-dotenv when installed."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv()


def resolve_api_key(
    *,
    explicit_api_key: str | None,
    environment_variable: str,
    provider_name: str,
) -> str:
    """Return an explicit or environment API key for a provider."""
    load_environment()
    api_key = explicit_api_key or os.getenv(environment_variable)
    if not api_key:
        raise ModelConfigurationError(
            f"{provider_name} requires {environment_variable}. "
            "Set it in the environment or in a .env file."
        )
    return api_key
