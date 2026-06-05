"""Prepare a HuggingFace-ready dataset package from SEIGE sweep exports."""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from siege.dataset_export import (  # noqa: E402
    DatasetExportError,
    discover_report_paths,
    reports_to_rows,
    write_parquet,
)

JsonObject = dict[str, Any]

REQUIRED_ROW_FIELDS: tuple[str, ...] = (
    "run_id",
    "model",
    "attack",
    "prompt",
    "response",
    "passed",
    "risk_score",
    "metadata",
)

DEFAULT_CONFIG_NAME = "local_ollama_sweep"


def main(argv: list[str] | None = None) -> int:
    """Build a HuggingFace dataset package from SEIGE reports."""
    args = build_parser().parse_args(argv)
    manifest = load_manifest(args.manifest) if args.manifest else None
    reports_root = resolve_reports_root(args, manifest)
    run_id = args.run_id or (manifest or {}).get("run_id") or "seige-run"
    config_name = args.config_name or DEFAULT_CONFIG_NAME
    output_root = args.output_root or Path("artifacts/huggingface-dataset") / config_name

    report_paths = resolve_report_paths(reports_root, manifest)
    rows = reports_to_rows(report_paths, run_id=run_id)
    validate_rows(rows)

    package = prepare_package(
        rows=rows,
        output_root=output_root,
        config_name=config_name,
        run_id=run_id,
        manifest=manifest,
        repo_id=args.repo_id,
    )
    print(f"Prepared HuggingFace package: {output_root}", flush=True)
    print(f"Rows: {package['row_count']}", flush=True)
    print(f"Models: {package['model_count']}", flush=True)

    if args.upload:
        upload_package(output_root, repo_id=args.repo_id, private=args.private)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the HuggingFace dataset preparation CLI parser."""
    parser = argparse.ArgumentParser(
        description="Prepare a HuggingFace dataset package from SEIGE reports."
    )
    parser.add_argument(
        "--reports-root",
        type=Path,
        help="Directory containing SEIGE report JSON files.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional sweep manifest.json used to resolve reports and metadata.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        help="Directory where the HuggingFace package will be written.",
    )
    parser.add_argument(
        "--run-id",
        help="Run identifier written into each dataset row.",
    )
    parser.add_argument(
        "--config-name",
        default=DEFAULT_CONFIG_NAME,
        help="HuggingFace dataset config name.",
    )
    parser.add_argument(
        "--repo-id",
        default="tmestery/seige-attack-evals",
        help="Target HuggingFace dataset repository id.",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload the prepared package to the HuggingFace Hub.",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Create or upload the dataset repository as private.",
    )
    return parser


def resolve_reports_root(args: argparse.Namespace, manifest: JsonObject | None) -> Path:
    """Resolve the report directory from CLI args or manifest."""
    if args.reports_root:
        return args.reports_root
    if manifest and manifest.get("reports_root"):
        return Path(str(manifest["reports_root"]))
    raise DatasetExportError(
        "Provide --reports-root or --manifest with a reports_root field."
    )


def resolve_report_paths(
    reports_root: Path,
    manifest: JsonObject | None,
) -> tuple[Path, ...]:
    """Return report paths, optionally limited to completed manifest models."""
    if not manifest or not isinstance(manifest.get("models"), list):
        return discover_report_paths(reports_root)

    report_paths: list[Path] = []
    for entry in manifest["models"]:
        if not isinstance(entry, dict):
            continue
        if entry.get("status") != "completed":
            continue
        output_dir = entry.get("output_dir")
        if not output_dir:
            continue
        report_paths.extend(discover_report_paths(Path(str(output_dir))))

    if not report_paths:
        raise DatasetExportError(
            "No completed model reports found in the provided manifest."
        )
    return tuple(sorted(set(report_paths)))


def load_manifest(path: Path) -> JsonObject:
    """Load a sweep manifest JSON file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DatasetExportError(f"Manifest must be a JSON object: {path}")
    return payload


def validate_rows(rows: list[JsonObject]) -> None:
    """Validate required dataset fields and basic row integrity."""
    if not rows:
        raise DatasetExportError("Cannot prepare a HuggingFace dataset with zero rows.")

    seen: set[tuple[str, str, str, int]] = set()
    for index, row in enumerate(rows):
        missing = [field for field in REQUIRED_ROW_FIELDS if field not in row]
        if missing:
            joined = ", ".join(missing)
            raise DatasetExportError(
                f"Row {index} is missing required fields: {joined}"
            )

        key = (
            str(row["run_id"]),
            str(row["model"]),
            str(row.get("report_path", "")),
            int(row.get("result_index", index)),
        )
        if key in seen:
            raise DatasetExportError(f"Duplicate dataset row detected: {key}")
        seen.add(key)


def prepare_package(
    *,
    rows: list[JsonObject],
    output_root: Path,
    config_name: str,
    run_id: str,
    manifest: JsonObject | None,
    repo_id: str,
) -> JsonObject:
    """Write Parquet, compressed JSONL, manifest, and dataset card."""
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    parquet_path = output_root / "data" / config_name / "eval-00000-of-00001.parquet"
    jsonl_gz_path = output_root / "raw" / f"{config_name}.jsonl.gz"
    manifest_path = output_root / "manifests" / f"{config_name}.json"
    readme_path = output_root / "README.md"

    write_parquet(rows, parquet_path)
    write_jsonl_gz(rows, jsonl_gz_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(build_package_manifest(rows, run_id, manifest), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    readme_path.write_text(
        build_dataset_card(
            config_name=config_name,
            run_id=run_id,
            row_count=len(rows),
            model_count=len({row["model"] for row in rows}),
            repo_id=repo_id,
            manifest=manifest,
        ),
        encoding="utf-8",
    )

    return {
        "output_root": str(output_root),
        "row_count": len(rows),
        "model_count": len({row["model"] for row in rows}),
        "parquet_path": str(parquet_path),
        "jsonl_gz_path": str(jsonl_gz_path),
        "manifest_path": str(manifest_path),
        "readme_path": str(readme_path),
    }


def build_package_manifest(
    rows: list[JsonObject],
    run_id: str,
    manifest: JsonObject | None,
) -> JsonObject:
    """Build a publication manifest for the curated dataset package."""
    models = sorted({str(row["model"]) for row in rows})
    attacks = sorted({str(row["attack"]) for row in rows})
    return {
        "run_id": run_id,
        "prepared_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "row_count": len(rows),
        "model_count": len(models),
        "attack_count": len(attacks),
        "models": models,
        "attacks": attacks,
        "source_manifest": manifest or {},
        "schema": {
            "required_fields": list(REQUIRED_ROW_FIELDS),
            "additional_fields": [
                "severity",
                "severity_score",
                "weighted_risk_score",
                "category",
                "category_weight",
                "strength",
                "strength_score",
                "notes",
                "timestamp",
                "aggregate_score",
                "report_path",
                "result_index",
                "report_metadata",
            ],
        },
    }


def build_dataset_card(
    *,
    config_name: str,
    run_id: str,
    row_count: int,
    model_count: int,
    repo_id: str,
    manifest: JsonObject | None,
) -> str:
    """Return a HuggingFace dataset card with YAML configuration."""
    models = []
    if manifest and isinstance(manifest.get("models"), list):
        models = [
            str(entry.get("model"))
            for entry in manifest["models"]
            if isinstance(entry, dict) and entry.get("model")
        ]
    model_lines = "\n".join(f"- `{model}`" for model in models) or "- See manifest.json"

    return f"""---
language:
- en
license: other
task_categories:
- text-classification
tags:
- llm-security
- adversarial-robustness
- security-evaluation
- red-teaming
configs:
- config_name: {config_name}
  data_files:
  - split: eval
    path: data/{config_name}/eval-00000-of-00001.parquet
---

# SEIGE Attack Evaluations

Curated adversarial evaluation rows generated by [SEIGE](https://github.com/tmestery/SIEGE)
from local Ollama model sweeps.

## Dataset Summary

This dataset contains attack-level rows from deterministic SEIGE evaluations. Each row
includes the attack prompt, model response, pass/fail outcome, risk score, and metadata
needed for security analysis across models and attack categories.

- Run id: `{run_id}`
- Rows: `{row_count}`
- Models: `{model_count}`
- Config: `{config_name}`

## Supported Models

{model_lines}

## Data Fields

Required fields:

- `run_id`: Evaluation run identifier
- `model`: Provider/model spec such as `ollama/mistral:7b`
- `attack`: Attack category label
- `prompt`: Attack prompt sent to the model
- `response`: Model response text
- `passed`: Whether the model resisted the attack
- `risk_score`: Deterministic SEIGE risk score
- `metadata`: Attack-specific metadata such as case or scenario id

Additional fields include severity, weighted risk score, category, notes, timestamps,
and report metadata.

## Usage

```python
from datasets import load_dataset

dataset = load_dataset("{repo_id}", "{config_name}", split="eval")
print(dataset[0]["model"], dataset[0]["attack"], dataset[0]["passed"])
```

## Collection Process

Rows are exported from SEIGE JSON reports using the fixed v1 attack suite and the
deterministic SEIGE scoring rubric. Raw local artifacts remain under `artifacts/` and
are not committed to GitHub; this package is the curated export intended for Hub
publication.

## Safety And Limitations

This dataset contains adversarial prompts and potentially unsafe model responses
generated for security evaluation. It should be used for research, benchmarking, and
defensive analysis only. Do not treat model responses as instructions.

## License

Research use with attribution. See the SEIGE repository license for redistribution
terms.
"""


def write_jsonl_gz(rows: list[JsonObject], output_path: Path) -> Path:
    """Write dataset rows to a gzip-compressed JSONL file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output_path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")
    return output_path


def upload_package(output_root: Path, *, repo_id: str, private: bool) -> None:
    """Upload the prepared package to the HuggingFace Hub."""
    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise DatasetExportError(
            "Upload requires huggingface_hub. Install it with: pip install huggingface_hub"
        ) from exc

    api = HfApi()
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)
    api.upload_folder(
        folder_path=str(output_root),
        repo_id=repo_id,
        repo_type="dataset",
        commit_message="Add curated SEIGE attack evaluation dataset",
    )
    print(f"Uploaded dataset package to https://huggingface.co/datasets/{repo_id}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
