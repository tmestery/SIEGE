"""Dataset export helpers for SEIGE report JSON files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


JsonObject = dict[str, Any]


class DatasetExportError(RuntimeError):
    """Raised when dataset export cannot be completed."""


def main(argv: list[str] | None = None) -> int:
    """Run the dataset exporter CLI."""
    args = build_parser().parse_args(argv)
    report_paths = discover_report_paths(args.input)
    rows = reports_to_rows(report_paths, run_id=args.run_id)

    if args.format == "jsonl":
        write_jsonl(rows, args.output)
    elif args.format == "parquet":
        write_parquet(rows, args.output)
    else:
        raise DatasetExportError(f"Unsupported export format: {args.format}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the dataset export CLI parser."""
    parser = argparse.ArgumentParser(prog="python -m siege.dataset_export")
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Report JSON file or directory containing report JSON files.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Dataset output path, usually .jsonl or .parquet.",
    )
    parser.add_argument(
        "--format",
        choices=("jsonl", "parquet"),
        default="jsonl",
        help="Dataset output format. Defaults to jsonl.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run identifier applied to every exported row.",
    )
    return parser


def discover_report_paths(path: Path) -> tuple[Path, ...]:
    """Return report JSON paths from a file or directory."""
    if not path.exists():
        raise DatasetExportError(f"Input path does not exist: {path}")

    if path.is_file():
        if path.name == "index.json":
            raise DatasetExportError(
                f"Index files are not report payloads: {path}"
            )
        return (path,)

    report_paths = sorted(
        candidate
        for candidate in path.rglob("*.json")
        if candidate.name != "index.json"
    )
    if not report_paths:
        raise DatasetExportError(f"No report JSON files found under: {path}")
    return tuple(report_paths)


def reports_to_rows(
    report_paths: Iterable[Path],
    *,
    run_id: str | None = None,
) -> list[JsonObject]:
    """Convert report JSON files into dataset rows."""
    rows: list[JsonObject] = []
    for report_path in report_paths:
        rows.extend(report_to_rows(report_path, run_id=run_id))
    return rows


def report_to_rows(
    report_path: Path,
    *,
    run_id: str | None = None,
) -> list[JsonObject]:
    """Convert one report JSON file into dataset rows."""
    payload = load_report(report_path)
    model = str(payload.get("model", "unknown"))
    timestamp = str(payload.get("timestamp", ""))
    aggregate_score = float(payload.get("aggregate_score", 0.0))
    report_metadata = payload.get("metadata") or {}
    resolved_run_id = run_id or derive_run_id(
        model=model,
        timestamp=timestamp,
        report_path=report_path,
        report_metadata=report_metadata,
    )
    results = payload.get("results") or []
    if not isinstance(results, list):
        raise DatasetExportError(
            f"Report results must be a list in {report_path}"
        )

    rows: list[JsonObject] = []
    for index, result in enumerate(results):
        if not isinstance(result, dict):
            raise DatasetExportError(
                f"Report result at index {index} must be an object in {report_path}"
            )
        rows.append(
            result_to_row(
                result=result,
                model=model,
                timestamp=timestamp,
                aggregate_score=aggregate_score,
                run_id=resolved_run_id,
                report_path=report_path,
                report_metadata=report_metadata,
                result_index=index,
            )
        )
    return rows


def result_to_row(
    *,
    result: JsonObject,
    model: str,
    timestamp: str,
    aggregate_score: float,
    run_id: str,
    report_path: Path,
    report_metadata: JsonObject,
    result_index: int,
) -> JsonObject:
    """Convert one report result into a dataset row."""
    metadata = dict(result.get("metadata") or {})
    category = str(result.get("category") or metadata.get("category") or "unknown")
    attack = str(metadata.get("attack") or category)

    return {
        "run_id": run_id,
        "model": model,
        "attack": attack,
        "prompt": str(result.get("prompt", "")),
        "response": str(result.get("response", "")),
        "passed": bool(result.get("passed", False)),
        "risk_score": float(result.get("risk_score", 0.0)),
        "metadata": metadata,
        "severity": str(result.get("severity", "")),
        "severity_score": float(result.get("severity_score", 0.0)),
        "weighted_risk_score": float(result.get("weighted_risk_score", 0.0)),
        "category": category,
        "category_weight": float(result.get("category_weight", 1.0)),
        "strength": str(result.get("strength", "")),
        "strength_score": float(result.get("strength_score", 0.0)),
        "notes": str(result.get("notes", "")),
        "timestamp": timestamp,
        "aggregate_score": aggregate_score,
        "report_path": str(report_path),
        "result_index": result_index,
        "report_metadata": dict(report_metadata),
    }


def derive_run_id(
    *,
    model: str,
    timestamp: str,
    report_path: Path,
    report_metadata: JsonObject,
) -> str:
    """Return a stable run identifier for one report."""
    explicit = report_metadata.get("run_id")
    if explicit:
        return str(explicit)

    digest = hashlib.sha256(
        f"{model}|{timestamp}|{report_path.resolve()}".encode("utf-8")
    ).hexdigest()
    return digest[:16]


def load_report(report_path: Path) -> JsonObject:
    """Load and validate one report JSON file."""
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetExportError(
            f"Invalid JSON in report file: {report_path}"
        ) from exc

    if not isinstance(payload, dict):
        raise DatasetExportError(
            f"Report JSON root must be an object: {report_path}"
        )
    if "results" not in payload:
        raise DatasetExportError(
            f"Report JSON missing results array: {report_path}"
        )
    return payload


def write_jsonl(rows: Iterable[JsonObject], output_path: Path) -> Path:
    """Write dataset rows to a JSONL file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")
    return output_path


def write_parquet(rows: Iterable[JsonObject], output_path: Path) -> Path:
    """Write dataset rows to a Parquet file."""
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise DatasetExportError(
            "Parquet export requires pyarrow. Install it with: pip install pyarrow"
        ) from exc

    row_list = list(rows)
    if not row_list:
        raise DatasetExportError("Cannot write Parquet dataset with zero rows.")

    table = pa.Table.from_pylist(row_list)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output_path)
    return output_path


if __name__ == "__main__":
    raise SystemExit(main())
