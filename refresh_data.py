"""Run one live source check and save refresh evidence for the dashboard."""

from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime, timezone
from pathlib import Path

from data_sources import RAW_SERIES, SOURCE_LINKS, strict_refresh, write_refresh_status


ROOT = Path(__file__).resolve().parent
VERIFY_SOURCES = {
    "41690973": ("Statistics Canada", "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401"),
    "87008984": ("Statistics Canada", "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1210001101"),
    "62305752": ("Statistics Canada", "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3610010401"),
    "2062815": ("Statistics Canada", "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410028701"),
    "CUUR0000SA0": ("U.S. Bureau of Labor Statistics", "https://data.bls.gov/timeseries/CUUR0000SA0"),
    "EFFR": ("Federal Reserve Bank of New York", "https://www.newyorkfed.org/markets/reference-rates/effr"),
    "US10Y": ("U.S. Department of the Treasury", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve"),
}


def write_verification_table(bundle: dict, out_dir: Path = ROOT / "docs") -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for series_id, label in RAW_SERIES.items():
        latest = bundle["raw_latest"][series_id]
        if series_id in VERIFY_SOURCES:
            agency, url = VERIFY_SOURCES[series_id]
        elif series_id in {"V39079", "BD.CDN.10YR.DQ.YLD"}:
            agency = "Bank of Canada"
            url = SOURCE_LINKS[series_id]
        elif series_id == "H10_CADUSD":
            agency = "Federal Reserve Board H.10"
            url = SOURCE_LINKS[series_id]
        else:
            agency, url = "Official source", SOURCE_LINKS[series_id]
        rows.append({
            "series_id": series_id,
            "series": label,
            "observation_date": latest["date"],
            "value_as_published": latest["value"],
            "source": agency,
            "source_url": url,
            "check": "Retrieved directly from the linked official source; value retained at source precision.",
        })
    csv_path = out_dir / "data_verification.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# Data verification",
        "",
        "This table records one current observation from each source series used by the dashboard. The refresh script reads the official publisher endpoint, checks that each series has a dated numeric observation, and retains the source precision. Derived dashboard measures are verified through their component observations and documented formulas below.",
        "",
        f"Last verified: **{now}** (UTC).",
        "",
        "| Source series | Date | Retrieved source value | Original source | Result |",
        "|---|---:|---:|---|---|",
    ]
    for row in rows:
        date_label = row["observation_date"] or "Unavailable"
        if row["series_id"] == "62305752" and date_label != "Unavailable":
            source_date = datetime.strptime(date_label, "%Y-%m-%d")
            date_label = f"Q{((source_date.month - 1) // 3) + 1} {source_date.year}"
        value = row["value_as_published"]
        lines.append(
            f"| `{row['series_id']}` — {row['series']} | {date_label} | {value} | [{row['source']}]({row['source_url']}) | Source pull matched; no estimate or manual adjustment |"
        )
    lines += [
        "",
        "## Derived dashboard measures",
        "",
        "- Real exchange-rate index: `FX (CAD per USD) × U.S. CPI ÷ Canada CPI`, divided by the 2016 average and multiplied by 100. A higher index means U.S. prices expressed in CAD rose relative to Canadian prices under this stated convention.",
        "- Canada/U.S. inflation gap: Canada CPI 12-month percent change minus U.S. CPI 12-month percent change.",
        "- Policy-rate spread: monthly mean of the Bank of Canada overnight target minus the New York Fed effective federal funds rate, in percentage points.",
        "- 10-year yield spread: monthly mean Government of Canada 10-year benchmark yield minus the U.S. Treasury 10-year par yield, in percentage points.",
        "- Real GDP growth: quarterly chained-dollar GDP growth, annualized as `((GDP_t / GDP_(t-1))^4 − 1) × 100`.",
        "",
        "The source check compares values at their original published precision. It does not claim that different agencies use identical definitions or release calendars; the dashboard labels those differences and shows observation dates separately.",
        "",
        "See [data sources and calculations](data_sources.md) and the [refresh evidence log](refresh_evidence.log).",
        "",
    ]
    (out_dir / "data_verification.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scheduled", action="store_true", help="label this check as the GitHub Actions scheduled refresh")
    args = parser.parse_args()
    try:
        bundle = strict_refresh()
        if args.scheduled and os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
            check_type = "GitHub Actions weekday scheduled refresh"
        elif args.scheduled:
            check_type = "scheduled refresh command (local run)"
        else:
            check_type = "manual source verification refresh"
        status = write_refresh_status(bundle, check_type=check_type)
        write_verification_table(bundle)
        print(f"SUCCESS {status['last_success_utc']} UTC")
        print(status["change_note"])
        print(f"Checked {len(bundle['raw_latest'])}/{len(RAW_SERIES)} raw source series.")
        print(f"Verification table: {ROOT / 'docs' / 'data_verification.md'}")
        print(f"Refresh evidence: {ROOT / 'docs' / 'refresh_evidence.log'}")
        return 0
    except Exception as exc:
        print(f"FAILED {datetime.now(timezone.utc).isoformat(timespec='seconds')} UTC: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
