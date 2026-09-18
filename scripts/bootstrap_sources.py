#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html.parser
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

FINRA_URL = "https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx"
FINRA_PAGE = "https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics"
SHILLER_PAGE = "https://shillerdata.com/"


class LinkParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


def fetch_bytes(url: str, *, timeout: int = 60) -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Market-Risk-Monitor/0.1 "
                "(historical-data bootstrap; https://github.com/world4jason/Market-Risk-Monitor)"
            )
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def download(url: str, destination: Path) -> Path:
    data = fetch_bytes(url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(destination)
    print(f"downloaded {url} -> {destination}")
    return destination


def discover_shiller_workbook_url() -> str:
    page = fetch_bytes(SHILLER_PAGE).decode("utf-8", errors="replace")
    parser = LinkParser()
    parser.feed(page)

    candidates = [
        urljoin(SHILLER_PAGE, href)
        for href in parser.links
        if "ie_data.xls" in href.lower()
    ]
    if not candidates:
        raise RuntimeError(
            "Could not discover the live ie_data.xls URL on shillerdata.com. "
            "Download it manually from https://shillerdata.com/ and pass it "
            "to scripts/refresh_data.py --shiller-file."
        )
    return candidates[0]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap official market-risk source files and run the no-GHA refresh pipeline."
        )
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / ".cache" / "market-risk-monitor",
    )
    parser.add_argument("--skip-public", action="store_true")
    parser.add_argument("--skip-finra", action="store_true")
    parser.add_argument("--skip-shiller", action="store_true")
    args = parser.parse_args()

    refresh_args = [sys.executable, str(ROOT / "scripts" / "refresh_data.py")]
    selected_any = False

    if not args.skip_public:
        refresh_args.append("--public")
        selected_any = True

    if not args.skip_finra:
        finra_path = args.cache_dir / "margin-statistics.xlsx"
        try:
            download(FINRA_URL, finra_path)
            refresh_args.extend(["--finra-file", str(finra_path)])
            selected_any = True
        except Exception as exc:
            print(
                "FINRA automatic download failed. FINRA sometimes protects the "
                "workbook with edge/CDN controls.",
                file=sys.stderr,
            )
            print(f"reason: {exc}", file=sys.stderr)
            print(
                f"Manual fallback: open {FINRA_PAGE}, download the historical Excel, "
                "then run:\n"
                "  python scripts/refresh_data.py "
                "--finra-file /path/to/margin-statistics.xlsx",
                file=sys.stderr,
            )

    if not args.skip_shiller:
        shiller_path = args.cache_dir / "ie_data.xls"
        try:
            shiller_url = discover_shiller_workbook_url()
            download(shiller_url, shiller_path)
            refresh_args.extend(["--shiller-file", str(shiller_path)])
            selected_any = True
        except Exception as exc:
            print(f"Shiller automatic download failed: {exc}", file=sys.stderr)
            print(
                "Manual fallback: download ie_data.xls from https://shillerdata.com/ "
                "and run:\n"
                "  python scripts/refresh_data.py --shiller-file /path/to/ie_data.xls",
                file=sys.stderr,
            )

    if not selected_any:
        raise SystemExit("No source selected or successfully downloaded.")

    run(refresh_args)
    run([sys.executable, str(ROOT / "scripts" / "validate_data.py")])
    run([sys.executable, str(ROOT / "scripts" / "site_smoke.py")])

    print("\nBootstrap complete. Review data/generated/refresh-report.json before committing.")


if __name__ == "__main__":
    main()
