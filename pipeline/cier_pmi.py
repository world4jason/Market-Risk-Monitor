from __future__ import annotations

import html
import re
from datetime import date
from html.parser import HTMLParser
from urllib.request import Request, urlopen


CIER_PMI_URL = "https://www.cier.edu.tw/pmi-trend/"

HEADLINE_SERIES_ID = "tw_manufacturing_pmi"
HEADLINE_COLUMN = "臺灣製造業PMI"
MONTH_COLUMN = "月份"
PROVIDER = "CIER"
UNIT = "index"

# A diffusion index cannot leave [0, 100]. A parse that produces something
# outside it has read the wrong column, not an extreme reading.
PMI_MIN = 0.0
PMI_MAX = 100.0
EXPECTED_ROLLING_WINDOW_MONTHS = 12

_MONTH_PATTERN = re.compile(r"^(\d{4})/(\d{1,2})$")
# The page uses the full-width percent sign; be tolerant of the ASCII one too.
_PERCENT_CHARS = "％%"


class CierPmiError(RuntimeError):
    pass


class _TableParser(HTMLParser):
    """Collect every table on the page as a list of rows of cell text."""

    def __init__(self):
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] = []
        self._cell_parts: list[str] = []
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "table":
            self._table = []
        elif tag in {"td", "th"}:
            self._in_cell = True
            self._cell_parts = []

    def handle_data(self, data):
        if self._in_cell:
            self._cell_parts.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"td", "th"} and self._in_cell:
            text = " ".join("".join(self._cell_parts).split())
            self._row.append(html.unescape(text))
            self._in_cell = False
            self._cell_parts = []
        elif tag == "tr":
            if self._row and self._table is not None:
                self._table.append(self._row)
            self._row = []
        elif tag == "table":
            if self._table is not None:
                self.tables.append(self._table)
            self._table = None


def _parse_number(text: str) -> float | None:
    cleaned = text.strip().strip(_PERCENT_CHARS).strip()
    cleaned = cleaned.replace(",", "").replace("％", "").replace("%", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _select_pmi_table(tables: list[list[list[str]]]) -> tuple[list[str], list[list[str]]]:
    """
    Pick the PMI table by its own header, never by position.

    The CIER page carries more than one table, and the PMI table is a
    JetEngine dynamic widget whose index is not guaranteed. Matching on the
    header is what stops a layout change from silently feeding some other
    table's numbers into a macro series.
    """
    for table in tables:
        if not table:
            continue
        header = table[0]
        if MONTH_COLUMN in header and HEADLINE_COLUMN in header:
            return header, table[1:]
    raise CierPmiError(
        f"no CIER PMI table found: expected header columns "
        f"{MONTH_COLUMN!r} and {HEADLINE_COLUMN!r}"
    )


def _next_month_start(obs_date: str) -> str:
    current = date.fromisoformat(obs_date)
    if current.month == 12:
        return date(current.year + 1, 1, 1).isoformat()
    return date(current.year, current.month + 1, 1).isoformat()


def validate_rolling_window(
    rows: list[dict],
    *,
    min_months: int = EXPECTED_ROLLING_WINDOW_MONTHS,
) -> None:
    if len(rows) < min_months:
        raise CierPmiError(
            f"CIER PMI rolling window has {len(rows)} months; "
            f"expected at least {min_months}"
        )


def parse_cier_pmi_html(text: str) -> list[dict]:
    """
    Parse the official CIER PMI table into ascending monthly rows.

    The table is a rolling window (12 months at time of writing), not a full
    history, so callers must treat coverage as forward-accumulating.
    """
    parser = _TableParser()
    parser.feed(text)

    header, body = _select_pmi_table(parser.tables)
    month_index = header.index(MONTH_COLUMN)
    headline_index = header.index(HEADLINE_COLUMN)
    sector_columns = {
        index: name
        for index, name in enumerate(header)
        if index not in {month_index, headline_index} and name
    }

    rows: list[dict] = []
    seen: set[str] = set()
    required_columns = max(month_index, headline_index) + 1
    for line_no, cells in enumerate(body, start=2):
        # An all-empty row is layout, not data.
        if not any(cell.strip() for cell in cells):
            continue

        # Everything else in the body must parse. Skipping a mangled row would
        # hand back fewer months than the source served while the bootstrap
        # still reported success -- a silently half-populated series is worse
        # than a failed run.
        if len(cells) < required_columns:
            raise CierPmiError(
                f"row {line_no}: expected at least {required_columns} columns, "
                f"got {len(cells)}"
            )
        month_text = cells[month_index].strip()
        match = _MONTH_PATTERN.match(month_text)
        if not match:
            raise CierPmiError(
                f"row {line_no}: unrecognized month {month_text!r}"
            )

        year, month = int(match.group(1)), int(match.group(2))
        try:
            observation_date = date(year, month, 1).isoformat()
        except ValueError as exc:
            raise CierPmiError(
                f"row {line_no}: invalid month {month_text!r}"
            ) from exc

        headline = _parse_number(cells[headline_index])
        if headline is None:
            raise CierPmiError(
                f"row {line_no}: missing {HEADLINE_COLUMN} value for {month_text}"
            )
        if not PMI_MIN <= headline <= PMI_MAX:
            raise CierPmiError(
                f"row {line_no}: {HEADLINE_COLUMN} {headline} outside "
                f"[{PMI_MIN:g}, {PMI_MAX:g}] for {month_text}"
            )

        if observation_date in seen:
            raise CierPmiError(f"row {line_no}: duplicate month {month_text}")
        seen.add(observation_date)

        sectors = {}
        for index, name in sector_columns.items():
            if index < len(cells):
                value = _parse_number(cells[index])
                if value is not None:
                    sectors[name] = value

        rows.append(
            {
                "date": observation_date,
                "source_month": month_text,
                "headline_pmi": headline,
                "sectors": sectors,
            }
        )

    if not rows:
        raise CierPmiError("CIER PMI table contained no parsable monthly rows")

    # The page lists newest first; downstream contracts require ascending.
    rows.sort(key=lambda row: row["date"])
    for previous, current in zip(rows, rows[1:]):
        expected = _next_month_start(previous["date"])
        if current["date"] != expected:
            raise CierPmiError(
                "CIER PMI table months are not contiguous: "
                f"expected {expected} after {previous['date']}, "
                f"got {current['date']}"
            )
    return rows


def to_macro_rows(
    rows: list[dict],
    *,
    observed_at: date,
    source_url: str = CIER_PMI_URL,
) -> list[dict]:
    """
    Convert parsed rows into the normalized Taiwan macro CSV contract.

    Only the headline PMI is emitted. The sector series are parsed and
    available, but they are not canonical metric ids, and inventing ids for
    them here would put series into the contract that nothing else defines.

    `release_date` is the date we verified the value was publicly available,
    not a publication date: the page carries none. Recording the observation
    date as an upper bound keeps no-look-ahead analysis conservative, whereas
    guessing an earlier publication date would make backtests read data before
    it can be shown to have existed.
    """
    macro = []
    for row in rows:
        if row["date"] >= observed_at.isoformat():
            raise CierPmiError(
                f"observation {row['date']} is not older than the observation "
                f"date {observed_at.isoformat()}"
            )
        macro.append(
            {
                "date": row["date"],
                "provider": PROVIDER,
                "series_id": HEADLINE_SERIES_ID,
                "value": row["headline_pmi"],
                "unit": UNIT,
                "release_date": observed_at.isoformat(),
                "source_url": source_url,
            }
        )
    return macro


def merge_macro_rows(
    existing: list[dict],
    incoming: list[dict],
) -> list[dict]:
    """
    Accumulate the rolling window into a growing history.

    The official table only exposes the last 12 months, so coverage is built
    by merging successive observations rather than by backfilling.

    Ingestion is forward-only by verified release date. An incoming vintage
    older than the currently stored vintage is rejected even if its numeric
    value happens to match the current value; this prevents a value reversion
    chain from being rolled back by replaying an older snapshot.

    Re-observing the current value at the same or a later verification date
    keeps the stored release date. A changed value is accepted only at a
    strictly newer verification date and then becomes the new current vintage.
    """
    merged: dict[tuple[str, str], dict] = {
        (row["series_id"], row["date"]): dict(row) for row in existing
    }

    for row in incoming:
        key = (row["series_id"], row["date"])
        previous = merged.get(key)
        if previous is None:
            merged[key] = dict(row)
            continue
        previous_release = date.fromisoformat(previous["release_date"])
        incoming_release = date.fromisoformat(row["release_date"])
        if incoming_release < previous_release:
            raise CierPmiError(
                "out-of-order CIER observation for "
                f"{row['date']}: stored vintage verified "
                f"{previous['release_date']}, incoming vintage verified "
                f"{row['release_date']}"
            )

        if float(previous["value"]) == float(row["value"]):
            # Forward re-observation of an unchanged value does not move its
            # verified availability date. Equal-date replay is idempotent.
            merged[key] = {
                **dict(row),
                "release_date": previous["release_date"],
            }
        else:
            if incoming_release == previous_release:
                raise CierPmiError(
                    "same-date conflicting CIER revision for "
                    f"{row['date']}: existing value {previous['value']} "
                    f"and incoming value {row['value']} both claim "
                    f"{row['release_date']}"
                )
            merged[key] = dict(row)

    return [merged[key] for key in sorted(merged, key=lambda k: (k[0], k[1]))]


def fetch_cier_pmi_page(url: str = CIER_PMI_URL, timeout: int = 30) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Market-Risk-Monitor/0.3 "
                "(CIER official manufacturing PMI adapter)"
            )
        },
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read()
            encoding = response.headers.get_content_charset() or "utf-8"
            return raw.decode(encoding, errors="replace")
    except Exception as exc:
        raise CierPmiError(f"failed to fetch CIER PMI page {url}: {exc}") from exc


def fetch_cier_pmi_rows(
    url: str = CIER_PMI_URL,
    timeout: int = 30,
) -> list[dict]:
    return parse_cier_pmi_html(fetch_cier_pmi_page(url, timeout=timeout))
