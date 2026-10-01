import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RefreshWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = (
            ROOT / ".github" / "workflows" / "refresh-public-snapshot.yml"
        ).read_text(encoding="utf-8")
        cls.runner = (
            ROOT / "scripts" / "refresh_public_snapshot.py"
        ).read_text(encoding="utf-8")
        cls.smoke = (
            ROOT / "scripts" / "site_smoke.py"
        ).read_text(encoding="utf-8")

    def test_workflow_supports_manual_and_scheduled_refresh(self):
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn('cron: "30 7 * * 1-5"', self.workflow)
        self.assertIn('cron: "30 22 * * 1-5"', self.workflow)

    def test_workflow_can_commit_only_after_release_command(self):
        self.assertIn("contents: write", self.workflow)
        refresh = self.workflow.index(
            "python scripts/refresh_public_snapshot.py"
        )
        commit = self.workflow.index("git commit")
        push = self.workflow.index("git push origin HEAD:main")
        self.assertLess(refresh, commit)
        self.assertLess(commit, push)
        self.assertIn("git add data/generated", self.workflow)

    def test_runner_uses_release_allowlist_and_clean_output(self):
        self.assertIn('"--clean-output"', self.runner)
        for series_id in (
            "nfci",
            "nfci_risk",
            "nfci_credit",
            "nfci_nonfinancial_leverage",
            "us_recession",
            "fed_target_legacy",
            "fed_target_upper",
        ):
            self.assertIn(f'"{series_id}"', self.runner)
        for flag in (
            '"--cboe-vix"',
            '"--finra-file"',
            '"--shiller-file"',
            '"--twse-current"',
            '"--taiwan-macro-file"',
            '"--cbc-rate-file"',
        ):
            self.assertIn(flag, self.runner)

    def test_runner_fails_closed_and_restores_previous_generated_tree(self):
        self.assertIn("seed_macro_retention_floor(", self.runner)
        self.assertIn("taiwan-macro-audit.json", self.runner)
        self.assertIn("restore_generated(backup_dir, output_dir)", self.runner)
        self.assertIn('"scripts/validate_data.py"', self.runner)
        self.assertIn('"scripts/check_publish_policy.py"', self.runner)
        self.assertIn('"scripts/site_smoke.py"', self.runner)

    def test_pages_smoke_allows_only_refresh_workflow(self):
        self.assertIn(
            'allowed_workflows = {"refresh-public-snapshot.yml"}',
            self.smoke,
        )
        self.assertIn("unexpected GitHub Actions workflows", self.smoke)


if __name__ == "__main__":
    unittest.main()
