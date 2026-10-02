import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.validate import validate_refresh_report
from scripts.refresh_public_snapshot import (
    annotate_refresh_report_source_failures,
    refresh_seeded_source_with_fallback,
    run_refresh_allow_preserved_errors,
)


class RefreshPublicSnapshotFallbackTests(unittest.TestCase):
    def test_failed_live_macro_fetch_restores_retained_seed(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "ndc.csv"
            output.write_text("retained\n", encoding="utf-8")

            def fail_run(*_args):
                output.write_text("partial-corruption\n", encoding="utf-8")
                raise subprocess.CalledProcessError(1, ["bootstrap"])

            with patch(
                "scripts.refresh_public_snapshot.run",
                side_effect=fail_run,
            ):
                message = refresh_seeded_source_with_fallback(
                    label="NDC business cycle",
                    script="scripts/bootstrap_ndc_business_cycle.py",
                    output_path=output,
                )

            self.assertEqual(output.read_text(encoding="utf-8"), "retained\n")
            self.assertIn("retained previous verified snapshot", message)

    def test_failed_live_macro_fetch_without_seed_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "missing.csv"
            with patch(
                "scripts.refresh_public_snapshot.run",
                side_effect=subprocess.CalledProcessError(1, ["bootstrap"]),
            ):
                with self.assertRaises(subprocess.CalledProcessError):
                    refresh_seeded_source_with_fallback(
                        label="NDC business cycle",
                        script="scripts/bootstrap_ndc_business_cycle.py",
                        output_path=output,
                    )

    def test_refresh_exit_one_is_allowed_only_for_preserved_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            report_path = output_dir / "refresh-report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-10-02T00:00:00Z",
                        "results": [
                            {
                                "metric": "nfci",
                                "status": "error",
                                "error": "timeout",
                                "preserved_previous": True,
                            },
                            {
                                "metric": "vix",
                                "status": "updated",
                                "path": "data/generated/vix.json",
                            },
                        ],
                        "removed_artifacts": [],
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.CompletedProcess(
                args=["python", "refresh_data.py"],
                returncode=1,
            )
            with patch(
                "scripts.refresh_public_snapshot.subprocess.run",
                return_value=completed,
            ):
                run_refresh_allow_preserved_errors(
                    "scripts/refresh_data.py",
                    output_dir=output_dir,
                )

    def test_refresh_exit_one_rejects_unpreserved_error(self):
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            (output_dir / "refresh-report.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-10-02T00:00:00Z",
                        "results": [
                            {
                                "metric": "nfci",
                                "status": "error",
                                "error": "timeout",
                                "preserved_previous": False,
                            }
                        ],
                        "removed_artifacts": [],
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.CompletedProcess(
                args=["python", "refresh_data.py"],
                returncode=1,
            )
            with patch(
                "scripts.refresh_public_snapshot.subprocess.run",
                return_value=completed,
            ):
                with self.assertRaises(subprocess.CalledProcessError):
                    run_refresh_allow_preserved_errors(
                        "scripts/refresh_data.py",
                        output_dir=output_dir,
                    )

    def test_refresh_report_marks_retained_source_as_error(self):
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            report_path = output_dir / "refresh-report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-10-02T00:00:00Z",
                        "results": [
                            {
                                "metric": "tw_ndc_leading_index",
                                "status": "updated",
                                "path": "data/generated/tw_ndc_leading_index.json",
                            },
                            {
                                "metric": "vix",
                                "status": "updated",
                                "path": "data/generated/vix.json",
                            },
                        ],
                        "removed_artifacts": [],
                    }
                ),
                encoding="utf-8",
            )

            annotate_refresh_report_source_failures(
                output_dir,
                [
                    (
                        ["tw_ndc_leading_index"],
                        "NDC live refresh failed; retained previous verified snapshot",
                    )
                ],
            )

            payload = json.loads(report_path.read_text(encoding="utf-8"))
            validate_refresh_report(payload)
            by_metric = {
                item["metric"]: item
                for item in payload["results"]
            }
            self.assertEqual(
                by_metric["tw_ndc_leading_index"]["status"],
                "error",
            )
            self.assertTrue(
                by_metric["tw_ndc_leading_index"]["preserved_previous"]
            )
            self.assertEqual(by_metric["vix"]["status"], "updated")


if __name__ == "__main__":
    unittest.main()
