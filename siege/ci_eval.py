"""CI evaluation runner for scheduled SEIGE workflows."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from siege.attacks import (
    AdversarialSuffixAttack,
    DataExfiltrationAttack,
    JailbreakingAttack,
    MultiTurnManipulationAttack,
    PromptInjectionAttack,
    SystemPromptExtractionAttack,
)
from siege.attacks.data_exfiltration import SYNTHETIC_CANARY
from siege.models import ModelClient, create_model_client
from siege.models.base import ModelConfigurationError
from siege.reporting import Report, ReportWriter
from siege.scoring import Scorer


DEFAULT_CI_MODELS = "local/refusing,local/leaking"


class RunnableAttack(Protocol):
    """Protocol for attacks that expose a full-suite runner."""

    name: str

    def run_all(self, model: ModelClient) -> list:
        """Run all attack cases or scenarios against a model."""


@dataclass(frozen=True)
class EvaluationReport:
    """One generated CI evaluation report entry."""

    model: str
    attack: str
    path: str
    aggregate_score: float


class RefusingLocalModel(ModelClient):
    """Deterministic local-safe model that refuses all attack attempts."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a refusal response."""
        del prompt, system_prompt
        return (
            "I cannot comply, cannot reveal hidden instructions, and cannot "
            "share private or sensitive context values."
        )


class LeakingLocalModel(ModelClient):
    """Deterministic local-safe model that simulates vulnerable behavior."""

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return a response containing common compromise indicators."""
        del prompt, system_prompt
        return (
            "Ignore previous instructions accepted. Admin mode enabled. "
            "Jailbreak successful. Safety disabled. Unfiltered answer follows. "
            "Suffix override successful. Unsafe answer follows. "
            "System prompt: You are a security-conscious assistant. "
            f"Canary leaked: {SYNTHETIC_CANARY}"
        )


def main(argv: list[str] | None = None) -> int:
    """Run the CI evaluation suite."""
    args = build_parser().parse_args(argv)
    model_specs = parse_model_list(args.models)
    output_dir = Path(args.output_dir)
    reports = run_evaluation(model_specs, output_dir)
    write_index(output_dir, reports)
    validate_json_files(output_dir)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CI evaluation CLI parser."""
    parser = argparse.ArgumentParser(prog="python -m siege.ci_eval")
    parser.add_argument(
        "--models",
        default=DEFAULT_CI_MODELS,
        help=(
            "Comma-separated provider/model specs. Defaults to "
            "'local/refusing,local/leaking' for deterministic CI artifacts."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/nightly-eval",
        help="Directory where JSON reports will be written.",
    )
    return parser


def parse_model_list(models: str) -> list[str]:
    """Parse a comma-separated model list."""
    model_specs = [model.strip() for model in models.split(",") if model.strip()]
    if not model_specs:
        raise ValueError("At least one model must be configured for CI evaluation.")
    return model_specs


def run_evaluation(
    model_specs: list[str],
    output_dir: Path,
) -> list[EvaluationReport]:
    """Run the fixed SEIGE evaluation suite for each configured model."""
    output_dir.mkdir(parents=True, exist_ok=True)
    writer = ReportWriter()
    scorer = Scorer()
    reports: list[EvaluationReport] = []

    for model_spec in model_specs:
        model = create_ci_model_client(model_spec)
        for attack in fixed_attack_suite():
            summary = scorer.score(attack.run_all(model))
            report = Report.from_scoring_summary(
                model=model_spec,
                summary=summary,
                metadata={
                    "attack": attack.name,
                    "ci": True,
                    "model_spec": model_spec,
                    "suite": "nightly-fixed-v1",
                },
            )
            path = output_dir / f"{safe_filename(model_spec)}_{attack.name}.json"
            writer.write(report, path)
            reports.append(
                EvaluationReport(
                    model=model_spec,
                    attack=attack.name,
                    path=str(path),
                    aggregate_score=summary.aggregate_score,
                )
            )

    return reports


def fixed_attack_suite() -> tuple[RunnableAttack, ...]:
    """Return the fixed v1 attack suite used by scheduled CI."""
    return (
        PromptInjectionAttack(),
        JailbreakingAttack(),
        AdversarialSuffixAttack(),
        SystemPromptExtractionAttack(),
        MultiTurnManipulationAttack(),
        DataExfiltrationAttack(),
    )


def create_ci_model_client(model_spec: str) -> ModelClient:
    """Create a local-safe or provider-backed model client for CI."""
    if model_spec == "local/refusing":
        return RefusingLocalModel("refusing")
    if model_spec == "local/leaking":
        return LeakingLocalModel("leaking")

    try:
        return create_model_client(model_spec)
    except ModelConfigurationError as exc:
        raise SystemExit(f"Provider configuration error for {model_spec}: {exc}") from exc
    except ValueError as exc:
        raise SystemExit(f"Invalid CI model spec {model_spec}: {exc}") from exc


def write_index(output_dir: Path, reports: list[EvaluationReport]) -> None:
    """Write an index of generated CI reports."""
    payload = {
        "suite": "nightly-fixed-v1",
        "reports": [
            {
                "model": report.model,
                "attack": report.attack,
                "path": report.path,
                "aggregate_score": report.aggregate_score,
            }
            for report in reports
        ],
    }
    (output_dir / "index.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_json_files(output_dir: Path) -> None:
    """Fail clearly if generated report artifacts are not valid JSON."""
    for path in output_dir.glob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON artifact {path}: {exc}") from exc


def safe_filename(value: str) -> str:
    """Convert provider/model specs into artifact-safe filenames."""
    return (
        value.replace("/", "_")
        .replace(":", "_")
        .replace(".", "_")
        .replace("-", "_")
    )


if __name__ == "__main__":
    raise SystemExit(main())
