"""Tests for multi-provider model client infrastructure."""

from __future__ import annotations

import argparse
import os
import sys
import types
import unittest
from unittest.mock import patch

from siege.cli import build_parser
from siege.models import (
    AnthropicClient,
    GroqClient,
    ModelConfigurationError,
    OllamaClient,
    OpenAIClient,
    create_model_client,
    parse_model_spec,
)
from siege.models.base import resolve_api_key


class ModelSpecTests(unittest.TestCase):
    """Unit tests for provider/model parsing."""

    def test_parse_model_spec_accepts_provider_model_strings(self) -> None:
        """Provider/model strings parse into normalized provider specs."""
        examples = {
            "groq/llama3": ("groq", "llama3"),
            "openai/gpt-4o": ("openai", "gpt-4o"),
            "anthropic/claude-3-5": ("anthropic", "claude-3-5"),
            "ollama/mistral": ("ollama", "mistral"),
        }

        for value, expected in examples.items():
            with self.subTest(value=value):
                spec = parse_model_spec(value)
                self.assertEqual((spec.provider, spec.model), expected)

    def test_parse_model_spec_rejects_invalid_values(self) -> None:
        """Invalid model specs fail loudly."""
        with self.assertRaises(ValueError):
            parse_model_spec("llama3")

    def test_factory_creates_ollama_without_api_key(self) -> None:
        """Ollama can be constructed without hosted-provider API keys."""
        client = create_model_client("ollama/mistral")

        self.assertIsInstance(client, OllamaClient)
        self.assertEqual(client.model, "mistral")

    def test_factory_creates_hosted_clients_from_environment_keys(self) -> None:
        """Hosted providers load API keys from environment variables."""
        env = {
            "GROQ_API_KEY": "groq-key",
            "OPENAI_API_KEY": "openai-key",
            "ANTHROPIC_API_KEY": "anthropic-key",
        }

        with patch.dict(os.environ, env, clear=False):
            groq = create_model_client("groq/llama3")
            openai = create_model_client("openai/gpt-4o")
            anthropic = create_model_client("anthropic/claude-3-5")

        self.assertIsInstance(groq, GroqClient)
        self.assertIsInstance(openai, OpenAIClient)
        self.assertIsInstance(anthropic, AnthropicClient)
        self.assertEqual(groq.api_key, "groq-key")
        self.assertEqual(openai.api_key, "openai-key")
        self.assertEqual(anthropic.api_key, "anthropic-key")

    def test_missing_hosted_api_key_raises_configuration_error(self) -> None:
        """Hosted providers require an API key."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ModelConfigurationError):
                create_model_client("openai/gpt-4o")

    def test_dotenv_loader_can_supply_api_keys(self) -> None:
        """API key resolution calls python-dotenv when available."""
        dotenv_module = types.ModuleType("dotenv")

        def fake_load_dotenv() -> None:
            os.environ["GROQ_API_KEY"] = "from-dotenv"

        dotenv_module.load_dotenv = fake_load_dotenv

        with patch.dict(os.environ, {}, clear=True):
            with patch.dict(sys.modules, {"dotenv": dotenv_module}):
                api_key = resolve_api_key(
                    explicit_api_key=None,
                    environment_variable="GROQ_API_KEY",
                    provider_name="Groq",
                )

        self.assertEqual(api_key, "from-dotenv")

    def test_dotenv_loader_can_supply_ollama_base_url(self) -> None:
        """Ollama base URL can come from dotenv-loaded environment."""
        dotenv_module = types.ModuleType("dotenv")

        def fake_load_dotenv() -> None:
            os.environ["OLLAMA_BASE_URL"] = "http://ollama.example:11434"

        dotenv_module.load_dotenv = fake_load_dotenv

        with patch.dict(os.environ, {}, clear=True):
            with patch.dict(sys.modules, {"dotenv": dotenv_module}):
                client = create_model_client("ollama/mistral")

        self.assertEqual(client.base_url, "http://ollama.example:11434")

    def test_cli_model_flag_accepts_provider_model_examples(self) -> None:
        """The CLI accepts provider/model values through --model."""
        parser = build_parser()

        for value in (
            "groq/llama3",
            "openai/gpt-4o",
            "anthropic/claude-3-5",
            "ollama/mistral",
        ):
            with self.subTest(value=value):
                args = parser.parse_args(["--model", value])
                self.assertEqual(args.model, value)

    def test_cli_model_flag_rejects_missing_provider(self) -> None:
        """The CLI rejects model values without provider/model format."""
        parser = build_parser()

        with self.assertRaises(SystemExit):
            with patch.object(argparse.ArgumentParser, "exit") as exit_mock:
                exit_mock.side_effect = SystemExit(2)
                parser.parse_args(["--model", "llama3"])


if __name__ == "__main__":
    unittest.main()
