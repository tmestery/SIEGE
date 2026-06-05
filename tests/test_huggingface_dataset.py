"""Tests for HuggingFace dataset preparation."""

from __future__ import annotations

import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

from siege.dataset_export import DatasetExportError, report_to_rows

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from prepare_huggingface_dataset import (  # noqa: E402
    build_dataset_card,
    prepare_package,
    resolve_report_paths,
    validate_rows,
)


class HuggingFaceDatasetTests(unittest.TestCase):
    """Unit tests for HuggingFace dataset package preparation."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.sample_report = Path("examples/report.json")

    def test_validate_rows_requires_core_fields(self) -> None:
        """Validation fails when required dataset fields are missing."""
        rows = report_to_rows(self.sample_report, run_id="hf-run")
        with self.assertRaisesRegex(DatasetExportError, "missing required fields"):
            validate_rows([{key: value for key, value in rows[0].items() if key != "model"}])

    def test_prepare_package_writes_parquet_manifest_and_readme(self) -> None:
        """Package preparation writes the expected HuggingFace layout."""
        try:
            import pyarrow  # noqa: F401
        except ImportError:
            self.skipTest("pyarrow is not installed")

        rows = report_to_rows(self.sample_report, run_id="hf-run")
        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory) / "local_ollama_sweep"
            package = prepare_package(
                rows=rows,
                output_root=output_root,
                config_name="local_ollama_sweep",
                run_id="hf-run",
                manifest={"model_count": 1},
                repo_id="tmestery/seige-attack-evals",
            )

            parquet_path = Path(package["parquet_path"])
            jsonl_gz_path = Path(package["jsonl_gz_path"])
            manifest_path = Path(package["manifest_path"])
            readme_path = Path(package["readme_path"])

            self.assertTrue(parquet_path.exists())
            self.assertTrue(jsonl_gz_path.exists())
            self.assertTrue(manifest_path.exists())
            self.assertTrue(readme_path.exists())
            self.assertIn("configs:", readme_path.read_text(encoding="utf-8"))
            self.assertEqual(package["row_count"], 2)

            with gzip.open(jsonl_gz_path, "rt", encoding="utf-8") as handle:
                lines = handle.read().strip().splitlines()
            self.assertEqual(len(lines), 2)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["row_count"], 2)
            self.assertIn("run_id", manifest["schema"]["required_fields"])

    def test_dataset_card_includes_config_and_repo(self) -> None:
        """Dataset card includes config metadata for HuggingFace loading."""
        card = build_dataset_card(
            config_name="local_ollama_sweep",
            run_id="hf-run",
            row_count=495,
            model_count=9,
            repo_id="tmestery/seige-attack-evals",
            manifest={
                "models": [{"model": "ollama/mistral:7b"}],
            },
        )
        self.assertIn("config_name: local_ollama_sweep", card)
        self.assertIn("tmestery/seige-attack-evals", card)
        self.assertIn("ollama/mistral:7b", card)

    def test_resolve_report_paths_uses_completed_manifest_models_only(self) -> None:
        """Manifest filtering excludes partial or failed model directories."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            completed_dir = root / "completed"
            partial_dir = root / "partial"
            completed_dir.mkdir()
            partial_dir.mkdir()
            completed_report = completed_dir / "completed_report.json"
            partial_report = partial_dir / "partial_report.json"
            payload = json.loads(self.sample_report.read_text(encoding="utf-8"))
            completed_report.write_text(json.dumps(payload), encoding="utf-8")
            partial_report.write_text(json.dumps(payload), encoding="utf-8")
            manifest = {
                "models": [
                    {
                        "model": "ollama/mistral:7b",
                        "status": "completed",
                        "output_dir": str(completed_dir),
                    },
                    {
                        "model": "ollama/gemma4:31b",
                        "status": "partial_failed",
                        "output_dir": str(partial_dir),
                    },
                ]
            }

            report_paths = resolve_report_paths(root, manifest)

        self.assertEqual(report_paths, (completed_report,))


if __name__ == "__main__":
    unittest.main()
