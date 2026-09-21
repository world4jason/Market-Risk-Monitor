from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.request import Request, urlopen


CBC_RATE_PAGES = [
    "https://www.cbc.gov.tw/en/lp-695-2.html",
    "https://www.cbc.gov.tw/en/lp-695-2-2-20.html",
    "https://www.cbc.gov.tw/en/lp-695-2-3-20.html",
]


class CbcHtmlError(RuntimeError):
    pass


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_cell = False
        self.cell_parts = []
        self.current_row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"td", "th"}:
            self.in_cell = True
            self.cell_parts = []

    def handle_data(self, data):
        if self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"td", "th"} and self.in_cell:
            text = " ".join("".join(self.cell_parts).split())
            self.current_row.append(html.unescape(text))
            self.in_cell = False
            self.cell_parts = []
        elif tag == "tr":
            if self.current_row:
                self.rows.append(self.current_row)
            self.current_row = []


def fetch_cbc_page(url: str, timeout: int = 30) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Market-Risk-Monitor/0.3 "
                "(CBC official policy-rate history adapter)"
            )
        },
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read()
            encoding = response.headers.get_content_charset() or "utf-8"
            return raw.decode(encoding, errors="replace")
    except Exception as exc:
        raise CbcHtmlError(f"failed to fetch CBC page {url}: {exc}") from exc


def parse_cbc_rate_html(text: str, source_url: str) -> list[dict]:
    parser = _TableParser()
    parser.feed(text)

    rows = []
    for cells in parser.rows:
        if len(cells) < 4:
            continue
        date_text = cells[0].strip()
        if not re.fullmatch(r"\d{4}/\d{1,2}/\d{1,2}", date_text):
            continue
        try:
            year, month, day = [int(x) for x in date_text.split("/")]
            iso = f"{year:04d}-{month:02d}-{day:02d}"
            discount = float(cells[1].replace(",", ""))
            collateral = float(cells[2].replace(",", ""))
            short_term = float(cells[3].replace(",", ""))
        except ValueError:
            continue
        rows.append(
            {
                "date": iso,
                "discount_rate": discount,
                "collateral_rate": collateral,
                "short_term_rate": short_term,
                "source_url": source_url,
            }
        )
    return rows


def fetch_cbc_rate_history(
    pages: list[str] | None = None,
    timeout: int = 30,
) -> list[dict]:
    pages = pages or CBC_RATE_PAGES
    by_date = {}
    for page in pages:
        parsed = parse_cbc_rate_html(
            fetch_cbc_page(page, timeout=timeout),
            page,
        )
        for row in parsed:
            by_date[row["date"]] = row

    rows = [by_date[d] for d in sorted(by_date)]
    if not rows:
        raise CbcHtmlError("no CBC rate rows parsed from official pages")
    return rows
