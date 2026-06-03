"""SEIGE package."""

from siege.models import (
    AnthropicClient,
    GroqClient,
    ModelClient,
    ModelConfigurationError,
    ModelSpec,
    OllamaClient,
    OpenAIClient,
    create_model_client,
    load_environment,
    parse_model_spec,
)
from siege.reporting import Report, ReportResult, ReportWriter
from siege.scoring import AttackScore, Scorer, ScoringSummary

__all__ = [
    "AnthropicClient",
    "AttackScore",
    "GroqClient",
    "ModelClient",
    "ModelConfigurationError",
    "ModelSpec",
    "OllamaClient",
    "OpenAIClient",
    "Report",
    "ReportResult",
    "ReportWriter",
    "Scorer",
    "ScoringSummary",
    "create_model_client",
    "load_environment",
    "parse_model_spec",
]
