"""Provider-specific model clients."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from siege.models.base import ModelClient, load_environment, resolve_api_key


class GroqClient(ModelClient):
    """Model client for Groq chat completions."""

    def __init__(self, model: str, api_key: str | None = None) -> None:
        """Create a Groq client."""
        super().__init__(model)
        self.api_key = resolve_api_key(
            explicit_api_key=api_key,
            environment_variable="GROQ_API_KEY",
            provider_name="Groq",
        )

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a Groq completion."""
        try:
            from groq import Groq
        except ImportError as exc:
            raise ImportError("Install the 'groq' package to use GroqClient.") from exc

        client = Groq(api_key=self.api_key)
        completion = client.chat.completions.create(
            model=self.model,
            messages=_chat_messages(prompt, system_prompt),
        )
        return completion.choices[0].message.content or ""


class OpenAIClient(ModelClient):
    """Model client for OpenAI chat completions."""

    def __init__(self, model: str, api_key: str | None = None) -> None:
        """Create an OpenAI client."""
        super().__init__(model)
        self.api_key = resolve_api_key(
            explicit_api_key=api_key,
            environment_variable="OPENAI_API_KEY",
            provider_name="OpenAI",
        )

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return an OpenAI completion."""
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai' package to use OpenAIClient."
            ) from exc

        client = OpenAI(api_key=self.api_key)
        completion = client.chat.completions.create(
            model=self.model,
            messages=_chat_messages(prompt, system_prompt),
        )
        return completion.choices[0].message.content or ""


class AnthropicClient(ModelClient):
    """Model client for Anthropic messages."""

    def __init__(self, model: str, api_key: str | None = None) -> None:
        """Create an Anthropic client."""
        super().__init__(model)
        self.api_key = resolve_api_key(
            explicit_api_key=api_key,
            environment_variable="ANTHROPIC_API_KEY",
            provider_name="Anthropic",
        )

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return an Anthropic completion."""
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ImportError(
                "Install the 'anthropic' package to use AnthropicClient."
            ) from exc

        client = Anthropic(api_key=self.api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
        )
        return _anthropic_text(message.content)


class HuggingFaceClient(ModelClient):
    """Model client for HuggingFace hosted inference."""

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """Create a HuggingFace inference client."""
        super().__init__(model)
        self.api_key = resolve_api_key(
            explicit_api_key=api_key,
            environment_variable="HUGGINGFACE_API_KEY",
            provider_name="HuggingFace",
        )
        default_base_url = (
            base_url
            or os.getenv("HUGGINGFACE_BASE_URL")
            or "https://api-inference.huggingface.co/models"
        )
        self.base_url = default_base_url.rstrip("/")

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a HuggingFace inference completion."""
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        payload = {"inputs": full_prompt, "parameters": {"return_full_text": False}}
        request = urllib.request.Request(
            f"{self.base_url}/{self.model}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"Could not reach HuggingFace inference API at {self.base_url}."
            ) from exc

        return _huggingface_text(body)


class OllamaClient(ModelClient):
    """Model client for local Ollama chat completions."""

    def __init__(self, model: str, base_url: str | None = None) -> None:
        """Create an Ollama client."""
        super().__init__(model)
        load_environment()
        default_base_url = os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434"
        self.base_url = (base_url or default_base_url).rstrip("/")

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return an Ollama completion."""
        payload = {
            "model": self.model,
            "messages": _chat_messages(prompt, system_prompt),
            "stream": False,
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Could not reach Ollama at {self.base_url}.") from exc

        return str(body.get("message", {}).get("content", ""))


def _chat_messages(prompt: str, system_prompt: str | None = None) -> list[dict[str, str]]:
    """Build common chat messages for chat-completion providers."""
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return messages


def _anthropic_text(content: Any) -> str:
    """Extract text from Anthropic message content blocks."""
    parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    return "".join(parts)


def _huggingface_text(body: Any) -> str:
    """Extract generated text from common HuggingFace inference responses."""
    if isinstance(body, list) and body:
        first = body[0]
        if isinstance(first, dict):
            return str(first.get("generated_text", ""))
    if isinstance(body, dict):
        if "generated_text" in body:
            return str(body["generated_text"])
        if "error" in body:
            raise RuntimeError(f"HuggingFace inference error: {body['error']}")
    return ""
