import csv
import io
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from pipeline.cier_pmi import (
    CIER_PMI_URL,
    HEADLINE_SERIES_ID,
    CierPmiError,
    merge_macro_rows,
    parse_cier_pmi_html,
    to_macro_rows,
    validate_rolling_window,
)
from pipeline.taiwan_macro import build_macro_metrics, parse_taiwan_macro_csv
from pipeline.validate import validate_metric


FIXTURE = Path(__file__).parent / "fixtures" / "cier_pmi_trend.html"

MINIMAL_TABLE = """<html><body><table>
<thead><tr>
<th>月份</th><th>臺灣製造業PMI</th><th>電子暨光學</th>
</tr></thead>
<tbody>
{rows}
</tbody></table></body></html>"""


def table(*rows: str) -> str:
    body = "\n".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row.split("|")) + "</tr>"
        for row in rows
    )
    return MINIMAL_TABLE.format(rows=body)


class CierPmiParseTests(unittest.TestCase):
    def test_parses_official_page_fixture(self):
        rows = parse_cier_pmi_html(FIXTURE.read_text(encoding="utf-8"))

        # The official table is a rolling 12-month window.
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0]["date"], "2025-09-01")
        self.assertEqual(rows[-1]["date"], "2026-08-01")

        latest = rows[-1]
        self.assertAlmostEqual(latest["headline_pmi"], 62.5)
        self.assertEqual(latest["source_month"], "2026/08")
        self.assertAlmostEqual(latest["sectors"]["電子暨光學"], 65.2)
        self.assertAlmostEqual(latest["sectors"]["交通工具"], 50.6)

        earliest = rows[0]
        self.assertAlmostEqual(earliest["headline_pmi"], 48.3)
        self.assertAlmostEqual(earliest["sectors"]["食品暨紡織"], 41.3)

    def test_rows_are_ascending_by_date(self):
        # The page lists newest first; downstream contracts require ascending.
        rows = parse_cier_pmi_html(FIXTURE.read_text(encoding="utf-8"))
        dates = [row["date"] for row in rows]
        self.assertEqual(dates, sorted(dates))

    def test_month_is_normalized_to_first_of_month(self):
        rows = parse_cier_pmi_html(table("2026/08|62.5％|65.2％"))
        self.assertEqual(rows[0]["date"], "2026-08-01")

    def test_accepts_halfwidth_percent_and_thousands_separator(self):
        rows = parse_cier_pmi_html(
            table("2026/08|62.5%|65.2", "2026/07|61.5 ％|1,065.5")
        )
        self.assertAlmostEqual(rows[1]["headline_pmi"], 62.5)
        self.assertAlmostEqual(rows[0]["headline_pmi"], 61.5)
        self.assertAlmostEqual(rows[0]["sectors"]["電子暨光學"], 1065.5)

    def test_empty_table_is_rejected(self):
        with self.assertRaises(CierPmiError):
            parse_cier_pmi_html(table())

    def test_page_without_pmi_table_is_rejected(self):
        # The same page also carries a trade-statistics table. Matching the
        # header is what stops us silently parsing the wrong one.
        other = """<html><body><table><thead><tr>
        <th>成交統計</th><th>成交金額(元)</th><th>成交股數(股)</th>
        </tr></thead><tbody><tr>
        <td>1.一般股票</td><td>1,060,401,174,750</td><td>5,860,392,347</td>
        </tr></tbody></table></body></html>"""
        with self.assertRaises(CierPmiError):
            parse_cier_pmi_html(other)

    def test_duplicate_month_is_rejected(self):
        with self.assertRaises(CierPmiError):
            parse_cier_pmi_html(table("2026/08|62.5％|65.2％", "2026/08|60.0％|64.0％"))

    def test_out_of_range_headline_is_rejected(self):
        # PMI is a diffusion index bounded by 0 and 100.
        with self.assertRaises(CierPmiError):
            parse_cier_pmi_html(table("2026/08|162.5％|65.2％"))
        with self.assertRaises(CierPmiError):
            parse_cier_pmi_html(table("2026/08|-1％|65.2％"))

    def test_missing_headline_value_is_rejected_not_zeroed(self):
        with self.assertRaises(CierPmiError):
            parse_cier_pmi_html(table("2026/08|—|65.2％"))

    def test_truncated_row_is_rejected_not_silently_dropped(self):
        # Silently skipping the row would hand back 1 month where the source
        # served 2, and the bootstrap would still report success.
        with self.assertRaises(CierPmiError):
            parse_cier_pmi_html(table("2026/08|62.5％|65.2％", "2026/07"))

    def test_malformed_month_is_rejected_not_silently_dropped(self):
        with self.assertRaises(CierPmiError):
            parse_cier_pmi_html(
                table("2026/08|62.5％|65.2％", "2026-07|61.5％|65.5％")
            )

    def test_missing_month_in_valid_rows_is_rejected(self):
        with self.assertRaisesRegex(CierPmiError, "not contiguous"):
            parse_cier_pmi_html(
                table("2026/08|62.5％|65.2％", "2026/06|60.0％|64.0％")
            )

    def test_bootstrap_window_guard_rejects_short_complete_page(self):
        rows = parse_cier_pmi_html(
            table("2026/08|62.5％|65.2％", "2026/07|61.5％|65.5％")
        )
        with self.assertRaisesRegex(CierPmiError, "expected at least 12"):
            validate_rolling_window(rows)

    def test_blank_spacer_row_is_ignored(self):
        # An all-empty row is layout, not mangled data.
        rows = parse_cier_pmi_html(
            table("2026/08|62.5％|65.2％", "||", "2026/07|61.5％|65.5％")
        )
        self.assertEqual([row["date"] for row in rows], ["2026-07-01", "2026-08-01"])


class CierPmiMacroContractTests(unittest.TestCase):
    def setUp(self):
        self.rows = parse_cier_pmi_html(FIXTURE.read_text(encoding="utf-8"))
        self.observed_at = date(2026, 9, 21)

    def test_emits_only_the_canonical_headline_series(self):
        macro = to_macro_rows(self.rows, observed_at=self.observed_at)
        self.assertEqual({row["series_id"] for row in macro}, {HEADLINE_SERIES_ID})
        self.assertEqual(len(macro), 12)
        self.assertEqual(macro[0]["provider"], "CIER")
        self.assertEqual(macro[0]["unit"], "index")
        self.assertEqual(macro[0]["source_url"], CIER_PMI_URL)

    def test_release_date_is_the_observed_upper_bound_not_invented(self):
        # The page carries no publication date. Claiming one would corrupt
        # no-look-ahead analysis, so we record when we verified it was public.
        macro = to_macro_rows(self.rows, observed_at=self.observed_at)
        for row in macro:
            self.assertEqual(row["release_date"], "2026-09-21")
            self.assertLess(row["date"], row["release_date"])

    def test_output_satisfies_the_taiwan_macro_csv_contract(self):
        macro = to_macro_rows(self.rows, observed_at=self.observed_at)

        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "date",
                "provider",
                "series_id",
                "value",
                "unit",
                "release_date",
                "source_url",
            ],
        )
        writer.writeheader()
        writer.writerows(macro)

        parsed = parse_taiwan_macro_csv(buffer.getvalue())
        self.assertEqual(len(parsed), 12)

        metrics = build_macro_metrics(
            parsed,
            datetime(2026, 9, 21, tzinfo=timezone.utc),
        )
        self.assertIn(HEADLINE_SERIES_ID, metrics)
        metric = metrics[HEADLINE_SERIES_ID]
        self.assertAlmostEqual(metric["latest"]["value"], 62.5)
        self.assertEqual(metric["latest"]["as_of"], "2026-08-01")
        validate_metric(metric)


class CierPmiMergeTests(unittest.TestCase):
    def row(self, month, value, release):
        return {
            "date": month,
            "provider": "CIER",
            "series_id": HEADLINE_SERIES_ID,
            "value": value,
            "unit": "index",
            "release_date": release,
            "source_url": CIER_PMI_URL,
        }

    def test_window_accumulates_into_longer_history(self):
        # The page only ever shows 12 months, so coverage has to be built by
        # merging successive observations.
        first = [self.row("2025-09-01", 48.3, "2025-10-05")]
        second = [self.row("2026-08-01", 62.5, "2026-09-21")]

        merged = merge_macro_rows(first, second)
        self.assertEqual(
            [row["date"] for row in merged],
            ["2025-09-01", "2026-08-01"],
        )

    def test_rolling_window_never_truncates_accumulated_history(self):
        existing = [
            self.row(
                f"{year:04d}-{month:02d}-01",
                50.0 + index / 10,
                "2026-01-15",
            )
            for index, (year, month) in enumerate(
                [
                    (2025, month) for month in range(1, 13)
                ]
                + [(2026, month) for month in range(1, 7)]
            )
        ]
        incoming = [
            self.row(
                f"{year:04d}-{month:02d}-01",
                55.0 + index / 10,
                "2026-09-21",
            )
            for index, (year, month) in enumerate(
                [(2025, month) for month in range(9, 13)]
                + [(2026, month) for month in range(1, 9)]
            )
        ]

        merged = merge_macro_rows(existing, incoming)

        self.assertEqual(len(existing), 18)
        self.assertEqual(len(incoming), 12)
        self.assertEqual(len(merged), 20)
        self.assertEqual(merged[0]["date"], "2025-01-01")
        self.assertEqual(merged[-1]["date"], "2026-08-01")

    def test_reobserving_an_unchanged_month_keeps_the_earliest_release_date(self):
        first = [self.row("2026-08-01", 62.5, "2026-09-21")]
        later = [self.row("2026-08-01", 62.5, "2026-11-30")]

        merged = merge_macro_rows(first, later)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["release_date"], "2026-09-21")

    def test_a_revised_value_takes_the_newer_release_date(self):
        # A revised figure was demonstrably not available at the earlier date,
        # so it must not inherit it.
        first = [self.row("2026-08-01", 62.5, "2026-09-21")]
        revised = [self.row("2026-08-01", 61.9, "2026-11-30")]

        merged = merge_macro_rows(first, revised)
        self.assertEqual(len(merged), 1)
        self.assertAlmostEqual(merged[0]["value"], 61.9)
        self.assertEqual(merged[0]["release_date"], "2026-11-30")

    def test_older_conflicting_vintage_is_rejected(self):
        existing = [self.row("2026-08-01", 61.9, "2026-11-30")]
        older = [self.row("2026-08-01", 62.5, "2026-09-21")]

        with self.assertRaisesRegex(CierPmiError, "out-of-order CIER revision"):
            merge_macro_rows(existing, older)

    def test_same_release_date_conflicting_value_is_rejected(self):
        existing = [self.row("2026-08-01", 61.9, "2026-11-30")]
        conflicting = [self.row("2026-08-01", 62.5, "2026-11-30")]

        with self.assertRaisesRegex(CierPmiError, "out-of-order CIER revision"):
            merge_macro_rows(existing, conflicting)

    def test_merged_output_still_satisfies_the_macro_contract(self):
        merged = merge_macro_rows(
            [self.row("2025-09-01", 48.3, "2025-10-05")],
            to_macro_rows(
                parse_cier_pmi_html(FIXTURE.read_text(encoding="utf-8")),
                observed_at=date(2026, 9, 21),
            ),
        )
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "date",
                "provider",
                "series_id",
                "value",
                "unit",
                "release_date",
                "source_url",
            ],
        )
        writer.writeheader()
        writer.writerows(merged)

        parsed = parse_taiwan_macro_csv(buffer.getvalue())
        self.assertEqual(len(parsed), 12)
        # The pre-existing 2025-09 row kept its own earlier release date.
        september = [r for r in parsed if r["date"] == "2025-09-01"][0]
        self.assertEqual(september["release_date"], "2025-10-05")


if __name__ == "__main__":
    unittest.main()
