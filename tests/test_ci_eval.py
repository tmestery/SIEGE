"""Tests for CI evaluation artifact generation."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from siege.ci_eval import (
    create_ci_model_client,
    main,
    parse_model_list,
    run_evaluation,
)


class CiEvalTests(unittest.TestCase):
    """Unit tests for scheduled evaluation helpers."""

    def test_parse_model_list_requires_at_least_one_model(self) -> None:
        """Empty model lists fail clearly."""
        with self.assertRaises(ValueError):
            parse_model_list(" , ")

    def test_local_safe_models_can_be_created(self) -> None:
        """Local deterministic CI models do not require provider credentials."""
        refusing = create_ci_model_client("local/refusing")
        leaking = create_ci_model_client("local/leaking")

        self.assertIn("cannot comply", refusing.complete("prompt"))
        self.assertIn("Canary leaked", leaking.complete("prompt"))

    def test_invalid_model_spec_exits_clearly(self) -> None:
        """Invalid provider/model specs are converted to CI failures."""
        with self.assertRaises(SystemExit):
            create_ci_model_client("not-a-model-spec")

    def test_missing_hosted_provider_config_exits_clearly(self) -> None:
        """Missing hosted provider credentials become clear CI failures."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(SystemExit, "Provider configuration error"):
                create_ci_model_client("openai/gpt-4o")

    def test_ci_eval_writes_reports_and_index(self) -> None:
        """The fixed CI suite writes valid JSON reports."""
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            reports = run_evaluation(["local/refusing"], output_dir)
            main(["--models", "local/refusing", "--output-dir", str(output_dir)])

            report_paths = sorted(output_dir.glob("*.json"))

        self.assertEqual(len(reports), 6)
        self.assertEqual(len(report_paths), 7)
        self.assertIn("index.json", {path.name for path in report_paths})

    def test_ci_eval_artifact_payload_is_valid(self) -> None:
        """Generated artifacts contain expected report fields."""
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            run_evaluation(["local/leaking"], output_dir)
            payload = json.loads(
                (output_dir / "local_leaking_data_exfiltration.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(payload["model"], "local/leaking")
        self.assertEqual(payload["metadata"]["suite"], "nightly-fixed-v1")
        self.assertIn("category_scores", payload)


if __name__ == "__main__":
    unittest.main()
