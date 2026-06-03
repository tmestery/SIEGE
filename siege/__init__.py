"""SEIGE package."""

from siege.models import (
    AnthropicClient,
    GroqClient,
    HuggingFaceClient,
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
from siege.scoring import AttackScore, CategoryScore, Scorer, ScoringSummary
from siege.dataset_export import (
    DatasetExportError,
    discover_report_paths,
    report_to_rows,
    reports_to_rows,
    write_jsonl,
    write_parquet,
)

__all__ = [
    "AnthropicClient",
    "AttackScore",
    "CategoryScore",
    "DatasetExportError",
    "GroqClient",
    "HuggingFaceClient",
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
    "discover_report_paths",
    "load_environment",
    "parse_model_spec",
    "report_to_rows",
    "reports_to_rows",
    "write_jsonl",
    "write_parquet",
]
