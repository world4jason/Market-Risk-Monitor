import subprocess
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

from pipeline.fred import build_metric, fetch_fred_csv, parse_fred_csv
from pipeline.validate import validate_metric


class FredTests(unittest.TestCase):
    def test_fetch_falls_back_to_curl_when_urllib_fails(self):
        fixture = b"observation_date,NFCI\\n2026-01-01,-0.5\\n"
        completed = subprocess.CompletedProcess(
            args=["curl"],
            returncode=0,
            stdout=fixture,
            stderr=b"",
        )
        with patch(
            "pipeline.fred.urlopen",
            side_effect=TimeoutError("urllib timeout"),
        ), patch(
            "pipeline.fred.shutil.which",
            return_value="/usr/bin/curl",
        ), patch(
            "pipeline.fred.subprocess.run",
            return_value=completed,
        ) as run:
            text = fetch_fred_csv("NFCI", timeout=30)

        self.assertEqual(text, fixture.decode("utf-8"))
        self.assertIn("--max-time", run.call_args.args[0])

    def test_parse_and_build(self):
        text="DATE,NFCI\n2026-01-02,-0.5\n2026-01-09,.\n2026-01-16,-0.2\n"
        obs=parse_fred_csv(text,"NFCI")
        self.assertEqual(obs[1]["value"],None)
        config={
            "id":"nfci","name":"NFCI","description":"test","pillar":"financial_stress",
            "units":"index","frequency":"weekly","polarity":"higher_is_riskier",
            "dataset":"National Financial Conditions Index","series_id":"NFCI",
            "max_age_days":14,"expected_observation_lag_days":5,
            "redistribution":"allowed","license_note":"fixture",
            "baselines":[]
        }
        metric=build_metric(config,obs,datetime(2026,1,20,tzinfo=timezone.utc))
        self.assertEqual(metric["latest"]["as_of"],"2026-01-16")
        self.assertEqual(metric["freshness"]["state"],"fresh")
        validate_metric(metric)


if __name__=="__main__":
    unittest.main()
