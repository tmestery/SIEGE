"""Run a local Ollama model sweep for SEIGE dataset collection."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from siege.ci_eval import run_evaluation, safe_filename
from siege.dataset_export import discover_report_paths, reports_to_rows, write_jsonl


DEFAULT_MODELS: tuple[str, ...] = (
    "ollama/gemma3:4b-it-qat",
    "ollama/gemma3:12b",
    "ollama/gemma4:31b",
    "ollama/codellama:13b",
    "ollama/devstral-small-2:latest",
    "ollama/llama3.2:3b",
    "ollama/llama3.1:8b",
    "ollama/mistral:7b",
    "ollama/qwen2.5:7b",
    "ollama/qwen2.5:14b",
    "ollama/phi4:14b",
    "ollama/deepseek-r1:8b",
)


@dataclass(frozen=True)
class SweepResult:
    """Manifest entry for one evaluated model."""

    model: str
    status: str
    output_dir: str
    report_count: int
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return this result as manifest JSON."""
        payload: dict[str, object] = {
            "model": self.model,
            "status": self.status,
            "output_dir": self.output_dir,
            "report_count": self.report_count,
        }
        if self.error:
            payload["error"] = self.error
        return payload


def main(argv: list[str] | None = None) -> int:
    """Run the local model sweep."""
    args = build_parser().parse_args(argv)
    models = parse_model_list(args.models) if args.models else list(DEFAULT_MODELS)
    run_id = args.run_id or f"local-ollama-sweep-{datetime.now(UTC).date()}"
    output_root = args.output_root or Path("artifacts/local-ollama-sweep") / run_id
    reports_root = output_root / "reports"
    dataset_path = output_root / "datasets" / "local-ollama-sweep.jsonl"
    manifest_path = output_root / "manifest.json"

    started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    sweep_results: list[SweepResult] = []

    for model in models:
        model_output_dir = reports_root / safe_filename(model)
        print(f"=== evaluating {model} ===", flush=True)
        try:
            reports = run_evaluation([model], model_output_dir)
        except Exception as exc:  # noqa: BLE001 - manifest should capture failures.
            sweep_results.append(
                SweepResult(
                    model=model,
                    status="failed",
                    output_dir=str(model_output_dir),
                    report_count=0,
                    error=str(exc),
                )
            )
            print(f"FAILED {model}: {exc}", flush=True)
            continue

        sweep_results.append(
            SweepResult(
                model=model,
                status="completed",
                output_dir=str(model_output_dir),
                report_count=len(reports),
            )
        )

    dataset_rows = []
    if any(result.status == "completed" for result in sweep_results):
        report_paths = discover_report_paths(reports_root)
        dataset_rows = reports_to_rows(report_paths, run_id=run_id)
        write_jsonl(dataset_rows, dataset_path)

    finished_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    manifest = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "model_count": len(models),
        "completed_count": sum(1 for result in sweep_results if result.status == "completed"),
        "failed_count": sum(1 for result in sweep_results if result.status == "failed"),
        "row_count": len(dataset_rows),
        "output_root": str(output_root),
        "reports_root": str(reports_root),
        "dataset_path": str(dataset_path),
        "models": [result.to_dict() for result in sweep_results],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote manifest: {manifest_path}", flush=True)
    print(f"Wrote dataset rows: {len(dataset_rows)}", flush=True)

    return 0 if manifest["completed_count"] else 1


def build_parser() -> argparse.ArgumentParser:
    """Build the sweep CLI parser."""
    parser = argparse.ArgumentParser(
        description="Run SEIGE against a local Ollama model sweep."
    )
    parser.add_argument(
        "--models",
        help="Comma-separated model specs. Defaults to the issue #36 model set.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        help="Artifact root for reports, dataset export, and manifest.",
    )
    parser.add_argument(
        "--run-id",
        help="Run identifier used in the dataset export and default output path.",
    )
    return parser


def parse_model_list(value: str) -> list[str]:
    """Parse a comma-separated model list."""
    models = [model.strip() for model in value.split(",") if model.strip()]
    if not models:
        raise ValueError("At least one model is required.")
    return models


if __name__ == "__main__":
    raise SystemExit(main())
