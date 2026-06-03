"""Factory helpers for model clients."""

from __future__ import annotations

from siege.models.base import ModelClient, parse_model_spec
from siege.models.providers import (
    AnthropicClient,
    GroqClient,
    OllamaClient,
    OpenAIClient,
)


def create_model_client(model_spec: str) -> ModelClient:
    """Create a model client from a `provider/model` string."""
    spec = parse_model_spec(model_spec)
    if spec.provider == "groq":
        return GroqClient(spec.model)
    if spec.provider == "openai":
        return OpenAIClient(spec.model)
    if spec.provider == "anthropic":
        return AnthropicClient(spec.model)
    if spec.provider == "ollama":
        return OllamaClient(spec.model)

    raise ValueError(
        f"Unsupported model provider '{spec.provider}'. "
        "Expected one of: anthropic, groq, ollama, openai."
    )
