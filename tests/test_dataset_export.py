"""Tests for dataset export helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from siege.dataset_export import (
    DatasetExportError,
    discover_report_paths,
    main,
    report_to_rows,
    reports_to_rows,
    write_jsonl,
    write_parquet,
)


class DatasetExportTests(unittest.TestCase):
    """Unit tests for report-to-dataset export."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.examples_dir = Path("examples")
        cls.sample_report = cls.examples_dir / "report.json"

    def test_report_to_rows_includes_required_fields(self) -> None:
        """Each exported row includes the dataset contract fields."""
        rows = report_to_rows(self.sample_report, run_id="manual-run")

        self.assertEqual(len(rows), 2)
        row = rows[0]
        self.assertEqual(row["run_id"], "manual-run")
        self.assertEqual(row["model"], "example/provider-model")
        self.assertEqual(row["attack"], "prompt_injection")
        self.assertIn("prompt", row)
        self.assertIn("response", row)
        self.assertIn("passed", row)
        self.assertIn("risk_score", row)
        self.assertIn("metadata", row)
        self.assertEqual(row["category"], "prompt_injection")
        self.assertEqual(row["weighted_risk_score"], 0.0)

    def test_write_jsonl_round_trip(self) -> None:
        """JSONL export writes one JSON object per line."""
        rows = report_to_rows(self.sample_report, run_id="jsonl-run")
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "dataset.jsonl"
            write_jsonl(rows, output_path)
            lines = output_path.read_text(encoding="utf-8").strip().splitlines()

        self.assertEqual(len(lines), 2)
        first = json.loads(lines[0])
        self.assertEqual(first["run_id"], "jsonl-run")
        self.assertEqual(first["attack"], "prompt_injection")

    def test_discover_nested_reports_skips_index(self) -> None:
        """Nested report discovery ignores index.json files."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "ollama" / "gemma"
            nested.mkdir(parents=True)
            report_path = nested / "jailbreaking_report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "model": "ollama/gemma",
                        "timestamp": "2026-06-02T12:00:00Z",
                        "aggregate_score": 1.0,
                        "results": [
                            {
                                "category": "jailbreaking",
                                "metadata": {"category": "jailbreaking"},
                                "prompt": "prompt",
                                "response": "response",
                                "passed": True,
                                "risk_score": 0.0,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "index.json").write_text("{}", encoding="utf-8")

            discovered = discover_report_paths(root)

        self.assertEqual(discovered, (report_path,))

    def test_missing_reports_raise_clear_error(self) -> None:
        """Empty directories fail with a clear export error."""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(DatasetExportError, "No report JSON files"):
                discover_report_paths(Path(directory))

    def test_run_id_comes_from_report_metadata(self) -> None:
        """Report metadata run_id overrides generated identifiers."""
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "model": "ollama/gemma",
                        "timestamp": "2026-06-02T12:00:00Z",
                        "aggregate_score": 0.0,
                        "metadata": {"run_id": "nightly-2026-06-02"},
                        "results": [
                            {
                                "category": "jailbreaking",
                                "metadata": {"category": "jailbreaking"},
                                "prompt": "prompt",
                                "response": "response",
                                "passed": False,
                                "risk_score": 5.0,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            rows = report_to_rows(report_path)

        self.assertEqual(rows[0]["run_id"], "nightly-2026-06-02")

    def test_reports_to_rows_across_directory(self) -> None:
        """Directory export flattens all report rows."""
        rows = reports_to_rows(discover_report_paths(self.examples_dir))
        self.assertGreater(len(rows), 10)
        self.assertTrue(all("run_id" in row for row in rows))

    def test_cli_exports_jsonl(self) -> None:
        """CLI entry point writes JSONL output."""
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "dataset.jsonl"
            exit_code = main(
                [
                    "--input",
                    str(self.sample_report),
                    "--output",
                    str(output_path),
                    "--format",
                    "jsonl",
                    "--run-id",
                    "cli-run",
                ]
            )
            lines = output_path.read_text(encoding="utf-8").strip().splitlines()

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["run_id"], "cli-run")

    def test_parquet_export_requires_pyarrow(self) -> None:
        """Parquet export fails clearly when pyarrow is unavailable."""
        rows = report_to_rows(self.sample_report, run_id="parquet-run")
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "dataset.parquet"
            with mock.patch.dict("sys.modules", {"pyarrow": None}):
                with self.assertRaisesRegex(DatasetExportError, "requires pyarrow"):
                    write_parquet(rows, output_path)

    def test_parquet_export_when_pyarrow_available(self) -> None:
        """Parquet export succeeds when pyarrow is installed."""
        try:
            import pyarrow  # noqa: F401
        except ImportError:
            self.skipTest("pyarrow is not installed")

        rows = report_to_rows(self.sample_report, run_id="parquet-run")
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "dataset.parquet"
            write_parquet(rows, output_path)

        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
