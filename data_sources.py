"""Official-source downloads and transformations for the Canada FX dashboard."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from html import unescape
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd


START_DATE = "2015-01-01"
BOC_URL = "https://www.bankofcanada.ca/valet/observations"
FED_H10_FX_URL = "https://www.federalreserve.gov/releases/h10/hist/dat00_ca.htm"
STATCAN_URL = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods"
BLS_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
NYFED_URL = "https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json"
TREASURY_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"

BOC_SERIES = ("V39079", "BD.CDN.10YR.DQ.YLD")
STATCAN_REQUESTS = (
    {"productId": 18100004, "coordinate": "2.2.0.0.0.0.0.0.0.0", "latestN": 150},
    {"productId": 12100011, "coordinate": "1.3.2.2.1.0.0.0.0.0", "latestN": 150},
    {"productId": 36100104, "coordinate": "1.1.1.30.0.0.0.0.0.0", "latestN": 60},
    {"productId": 14100287, "coordinate": "1.7.1.1.1.1.0.0.0.0", "latestN": 150},
)

RAW_SERIES = {
    "H10_CADUSD": "Federal Reserve Board H.10 — Canadian dollars per U.S. dollar spot rate",
    "V39079": "Bank of Canada — target for the overnight rate",
    "BD.CDN.10YR.DQ.YLD": "Bank of Canada — Government of Canada 10-year benchmark yield",
    "41690973": "Statistics Canada — Canada all-items CPI index (published reference base)",
    "87008984": "Statistics Canada — merchandise trade balance, balance-of-payments basis",
    "62305752": "Statistics Canada — real GDP at market prices, chained 2017 dollars",
    "2062815": "Statistics Canada — unemployment rate, Canada, seasonally adjusted",
    "CUUR0000SA0": "U.S. Bureau of Labor Statistics — CPI-U, all items, U.S. city average, not seasonally adjusted",
    "EFFR": "Federal Reserve Bank of New York — effective federal funds rate",
    "US10Y": "U.S. Department of the Treasury — daily 10-year par yield",
}

SOURCE_LINKS = {
    "H10_CADUSD": FED_H10_FX_URL,
    "V39079": "https://www.bankofcanada.ca/valet/observations/V39079/json?start_date=2015-01-01",
    "BD.CDN.10YR.DQ.YLD": "https://www.bankofcanada.ca/valet/observations/BD.CDN.10YR.DQ.YLD/json?start_date=2015-01-01",
    "41690973": "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods",
    "87008984": "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods",
    "62305752": "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods",
    "2062815": "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods",
    "CUUR0000SA0": "https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SA0",
    "EFFR": "https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json",
    "US10Y": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=2026",
}

ATOM = "{http://www.w3.org/2005/Atom}"
DATA = "{http://schemas.microsoft.com/ado/2007/08/dataservices}"
METADATA = "{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}"


def _request_bytes(
    url: str,
    *,
    payload: dict[str, Any] | list[dict[str, Any]] | None = None,
    timeout: int = 45,
    retries: int = 2,
) -> bytes:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"User-Agent": "CanadaInternationalFinanceDashboard/1.0", "Accept": "application/json, application/xml, text/xml, */*"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if body is not None else "GET")
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.7 * (attempt + 1))
    raise RuntimeError(f"Could not retrieve {url}: {last_error}") from last_error


def _get_json(url: str, *, payload: Any = None) -> Any:
    return json.loads(_request_bytes(url, payload=payload).decode("utf-8"))


def _series_frame(rows: list[tuple[str, Any]], name: str) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=["date", name])
    if frame.empty:
        return pd.DataFrame(columns=[name], index=pd.DatetimeIndex([], name="date"))
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame[name] = pd.to_numeric(frame[name], errors="coerce")
    frame = frame.dropna(subset=["date"]).drop_duplicates("date", keep="last")
    return frame.set_index("date").sort_index()


def _fetch_boc() -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, Any]]]:
    names = ",".join(BOC_SERIES)
    url = f"{BOC_URL}/{names}/json?start_date={START_DATE}"
    body = _get_json(url)
    rows: dict[str, list[tuple[str, Any]]] = {name: [] for name in BOC_SERIES}
    for observation in body.get("observations", []):
        for name in BOC_SERIES:
            value = observation.get(name, {}).get("v")
            if value not in (None, ""):
                rows[name].append((observation["d"], value))
    frames = {name: _series_frame(series_rows, name) for name, series_rows in rows.items()}
    details = body.get("seriesDetail", {})
    for name, frame in frames.items():
        if frame.empty:
            raise RuntimeError(f"Bank of Canada returned no observations for {name}.")
        detail = details.get(name, {})
        if not detail:
            raise RuntimeError(f"Bank of Canada response omitted metadata for {name}.")
    return frames, details


def _fetch_h10_fx() -> pd.DataFrame:
    """Read the Fed's official historical H.10 daily CAD-per-USD table."""
    html = _request_bytes(FED_H10_FX_URL).decode("utf-8", errors="replace")
    # The Federal Reserve's historical release provides a compact, dated HTML table.
    # Pull only its two cells per row and leave ND observations missing.
    table_start = html.find("Historical Rates for the Canadian Dollar")
    table_start = html.find("<table", table_start)
    table_end = html.find("</table>", table_start)
    if table_start < 0 or table_end < 0:
        raise RuntimeError("Federal Reserve H.10 historical CAD table was not found.")
    table = html[table_start:table_end]
    rows: list[tuple[str, Any]] = []
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", table, flags=re.I | re.S):
        cells = re.findall(r"<(?:th|td)\b[^>]*>(.*?)</(?:th|td)>", row, flags=re.I | re.S)
        if len(cells) < 2:
            continue
        values = [unescape(re.sub(r"<[^>]+>", " ", cell)).strip() for cell in cells[:2]]
        try:
            observed = datetime.strptime(values[0], "%d-%b-%y").date()
        except ValueError:
            continue
        value = values[1].strip()
        rows.append((observed.isoformat(), value if value.upper() != "ND" else None))
    frame = _series_frame(rows, "fx_usdcad")
    frame = frame.loc[frame.index >= pd.Timestamp(START_DATE)]
    if frame.empty:
        raise RuntimeError("Federal Reserve H.10 returned no CAD/USD observations from 2015 onward.")
    return frame


def _fetch_statcan() -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, Any]]]:
    response = _get_json(STATCAN_URL, payload=list(STATCAN_REQUESTS))
    frames: dict[str, pd.DataFrame] = {}
    details: dict[str, dict[str, Any]] = {}
    for item in response:
        obj = item.get("object")
        if item.get("status") != "SUCCESS" or not isinstance(obj, dict):
            raise RuntimeError(f"Statistics Canada WDS response was not successful: {item}")
        product_id = str(obj.get("productId"))
        vector_id = str(obj.get("vectorId"))
        frequency = obj.get("frequencyCode")
        rows = []
        for point in obj.get("vectorDataPoint", []):
            value = point.get("value")
            # A non-zero status can mark a suppressed, preliminary, or otherwise flagged value.
            # Keep the date and mark the observation unavailable instead of inferring a number.
            if point.get("statusCode", 0) != 0 or value in (None, ""):
                value = None
            date_value = point.get("refPerRaw") or point.get("refPer")
            rows.append((date_value, value, point.get("releaseTime"), point.get("statusCode", 0)))
        if not rows:
            raise RuntimeError(f"Statistics Canada returned no data for product {product_id}.")
        frame = pd.DataFrame(rows, columns=["date", "value", "release_time", "status_code"])
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        # Quarterly GDP has a period start in refPer and a quarter-end month in refPerRaw.
        if int(frequency or 0) == 9:
            frame["date"] = frame["date"].dt.to_period("Q").dt.end_time.dt.normalize()
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        frame = frame.dropna(subset=["date"]).drop_duplicates("date", keep="last").sort_values("date")
        frame = frame.set_index("date")
        frames[product_id] = frame
        details[product_id] = {
            "vector_id": vector_id,
            "coordinate": obj.get("coordinate"),
            "frequency_code": frequency,
            "product_id": product_id,
            "latest_release_time": frame["release_time"].dropna().max() if not frame.empty else None,
        }
    expected = {"18100004", "12100011", "36100104", "14100287"}
    missing = expected - set(frames)
    if missing:
        raise RuntimeError(f"Statistics Canada omitted product(s): {', '.join(sorted(missing))}")
    return frames, details


def _fetch_bls_cpi() -> pd.DataFrame:
    rows: dict[str, float] = {}
    # BLS v1 accepts up to a 10-year date span without a key; split the requested history.
    for start_year, end_year in (("2015", "2024"), ("2025", str(date.today().year))):
        body = _get_json(BLS_URL, payload={"seriesid": ["CUUR0000SA0"], "startyear": start_year, "endyear": end_year})
        if body.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError(f"BLS API did not succeed: {body.get('message')}")
        series_list = body.get("Results", {}).get("series", [])
        series = next((s for s in series_list if s.get("seriesID") == "CUUR0000SA0"), None)
        if not series:
            raise RuntimeError("BLS response omitted CUUR0000SA0.")
        for point in series.get("data", []):
            if point.get("period", "").startswith("M") and point.get("period") != "M13" and point.get("value") not in (None, "", "-"):
                month = int(point["period"][1:])
                rows[f"{point['year']}-{month:02d}-01"] = float(point["value"])
    frame = _series_frame(list(rows.items()), "us_cpi")
    if frame.empty:
        raise RuntimeError("BLS API returned no CPI observations.")
    return frame


def _fetch_effr() -> pd.DataFrame:
    params = urllib.parse.urlencode({"startDate": START_DATE, "endDate": date.today().isoformat()})
    body = _get_json(f"{NYFED_URL}?{params}")
    points = body.get("refRates", [])
    rows = [(point.get("effectiveDate"), point.get("percentRate")) for point in points if point.get("type") == "EFFR"]
    frame = _series_frame(rows, "us_effr")
    if frame.empty:
        raise RuntimeError("New York Fed API returned no EFFR observations.")
    return frame


def _fetch_us_10y() -> pd.DataFrame:
    year = date.today().year
    frames = []
    for requested_year in range(2015, year + 1):
        params = urllib.parse.urlencode({"data": "daily_treasury_yield_curve", "field_tdr_date_value": requested_year})
        root = ET.fromstring(_request_bytes(f"{TREASURY_URL}?{params}"))
        rows = []
        for entry in root.findall(f"{ATOM}entry"):
            content = entry.find(f"{ATOM}content")
            props = content.find(f"{METADATA}properties") if content is not None else None
            if props is None:
                continue
            raw_date = props.findtext(f"{DATA}NEW_DATE")
            raw_yield = props.findtext(f"{DATA}BC_10YEAR")
            if raw_date and raw_yield not in (None, "", "N/A"):
                rows.append((raw_date[:10], raw_yield))
        if rows:
            frames.append(_series_frame(rows, "us_10y"))
    if not frames:
        raise RuntimeError("U.S. Treasury feed returned no 10-year yields.")
    frame = pd.concat(frames).sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    return frame


def _monthly_mean(frame: pd.DataFrame, column: str) -> tuple[pd.Series, pd.Series]:
    series = frame[column].dropna().copy()
    if series.empty:
        empty = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
        return empty, empty
    period = series.index.to_period("M")
    values = series.groupby(period).mean()
    last_dates = pd.Series(series.index, index=period).groupby(level=0).max()
    values.index = values.index.to_timestamp()
    last_dates.index = last_dates.index.to_timestamp()
    return values.sort_index(), last_dates.sort_index()


def _statcan_monthly(frame: pd.DataFrame, column: str = "value") -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    values = frame[column].dropna().copy()
    values.index = values.index.to_period("M").to_timestamp()
    return values[~values.index.duplicated(keep="last")].sort_index()


def _as_monthly_index(series: pd.Series) -> pd.Series:
    values = series.dropna().copy()
    if values.empty:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    values.index = values.index.to_period("M").to_timestamp()
    return values[~values.index.duplicated(keep="last")].sort_index()


def year_over_year_percent_change(index: pd.Series) -> pd.Series:
    """Return monthly CPI inflation from an index, in percent year over year."""
    return index.pct_change(12, fill_method=None) * 100


def real_exchange_rate_index(
    fx_cad_per_usd: pd.Series,
    us_cpi: pd.Series,
    canada_cpi: pd.Series,
    *,
    base_year: int = 2016,
) -> pd.Series:
    """Course convention: FX(CAD/USD) * U.S. CPI / Canada CPI, rebased to 100."""
    relative_price = fx_cad_per_usd * us_cpi / canada_cpi
    base = relative_price.loc[f"{base_year}-01-01":f"{base_year}-12-01"].mean()
    if pd.isna(base) or base == 0:
        return pd.Series(float("nan"), index=relative_price.index, name="rer_index")
    return (100 * relative_price / base).rename("rer_index")


def annualized_quarterly_growth(real_gdp: pd.Series) -> pd.Series:
    """Annualize quarter-on-quarter growth in a real GDP level series."""
    return (((real_gdp / real_gdp.shift(1)) ** 4 - 1) * 100).rename("gdp_growth_annualized")


def _latest_raw(raw: dict[str, pd.DataFrame]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    column_aliases = {"H10_CADUSD": "fx_usdcad", "CUUR0000SA0": "us_cpi", "EFFR": "us_effr", "US10Y": "us_10y"}
    for key, frame in raw.items():
        numeric_column = column_aliases.get(key, key)
        if numeric_column not in frame.columns:
            numeric_column = "value"
        data = frame[numeric_column].dropna() if numeric_column in frame else pd.Series(dtype=float)
        if data.empty:
            results[key] = {"date": None, "value": None}
        else:
            latest_date = data.index.max()
            results[key] = {"date": latest_date.date().isoformat(), "value": float(data.loc[latest_date])}
    return results


def fetch_dashboard_data() -> dict[str, Any]:
    """Fetch official observations; return partial data plus explicit source errors."""
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    errors: dict[str, str] = {}
    boc: dict[str, pd.DataFrame] = {}
    statcan: dict[str, pd.DataFrame] = {}
    statcan_details: dict[str, dict[str, Any]] = {}
    raw: dict[str, pd.DataFrame] = {}

    try:
        boc, _ = _fetch_boc()
        raw.update(boc)
    except Exception as exc:
        errors["Bank of Canada"] = str(exc)
    h10_fx = pd.DataFrame()
    try:
        h10_fx = _fetch_h10_fx()
        raw["H10_CADUSD"] = h10_fx
    except Exception as exc:
        errors["Federal Reserve Board H.10"] = str(exc)
    try:
        statcan, statcan_details = _fetch_statcan()
        raw.update({
            "41690973": statcan["18100004"].rename(columns={"value": "value"}),
            "87008984": statcan["12100011"].rename(columns={"value": "value"}),
            "62305752": statcan["36100104"].rename(columns={"value": "value"}),
            "2062815": statcan["14100287"].rename(columns={"value": "value"}),
        })
    except Exception as exc:
        errors["Statistics Canada"] = str(exc)
    us_cpi = pd.DataFrame()
    try:
        us_cpi = _fetch_bls_cpi()
        raw["CUUR0000SA0"] = us_cpi
    except Exception as exc:
        errors["U.S. Bureau of Labor Statistics"] = str(exc)
    effr = pd.DataFrame()
    try:
        effr = _fetch_effr()
        raw["EFFR"] = effr
    except Exception as exc:
        errors["Federal Reserve Bank of New York"] = str(exc)
    us_10y = pd.DataFrame()
    try:
        us_10y = _fetch_us_10y()
        raw["US10Y"] = us_10y
    except Exception as exc:
        errors["U.S. Department of the Treasury"] = str(exc)

    monthly = pd.DataFrame()
    quarterly = pd.DataFrame()
    month_parts: dict[str, pd.Series] = {}
    if not h10_fx.empty:
        month_parts["fx_usdcad"] = _monthly_mean(h10_fx, "fx_usdcad")[0]
    for key, column in (("V39079", "ca_policy"), ("BD.CDN.10YR.DQ.YLD", "ca_10y")):
        if key in boc:
            mean, _ = _monthly_mean(boc[key], key)
            month_parts[column] = mean
    if "us_cpi" in us_cpi:
        month_parts["us_cpi"] = _as_monthly_index(us_cpi["us_cpi"])
    if "us_effr" in effr:
        month_parts["us_effr"] = _monthly_mean(effr, "us_effr")[0]
    if "us_10y" in us_10y:
        month_parts["us_10y"] = _monthly_mean(us_10y, "us_10y")[0]
    if "18100004" in statcan:
        month_parts["ca_cpi"] = _statcan_monthly(statcan["18100004"])
    if "12100011" in statcan:
        month_parts["trade_balance"] = _statcan_monthly(statcan["12100011"])
    if "14100287" in statcan:
        month_parts["unemployment"] = _statcan_monthly(statcan["14100287"])
    if month_parts:
        monthly = pd.concat(month_parts, axis=1).sort_index()
        if "ca_cpi" in monthly:
            monthly["ca_inflation"] = year_over_year_percent_change(monthly["ca_cpi"])
        if "us_cpi" in monthly:
            monthly["us_inflation"] = year_over_year_percent_change(monthly["us_cpi"])
        if {"ca_inflation", "us_inflation"}.issubset(monthly.columns):
            monthly["inflation_gap"] = monthly["ca_inflation"] - monthly["us_inflation"]
        if {"fx_usdcad", "us_cpi", "ca_cpi"}.issubset(monthly.columns):
            monthly["rer_index"] = real_exchange_rate_index(monthly["fx_usdcad"], monthly["us_cpi"], monthly["ca_cpi"])
        if {"ca_policy", "us_effr"}.issubset(monthly.columns):
            monthly["policy_gap"] = monthly["ca_policy"] - monthly["us_effr"]
        if {"ca_10y", "us_10y"}.issubset(monthly.columns):
            monthly["yield_gap"] = monthly["ca_10y"] - monthly["us_10y"]
        if "fx_usdcad" in monthly:
            monthly["fx_change_pct"] = monthly["fx_usdcad"].pct_change(fill_method=None) * 100
        if "trade_balance" in monthly:
            monthly["trade_change_m"] = monthly["trade_balance"].diff()

    if "36100104" in statcan:
        gdp = statcan["36100104"]["value"].dropna().sort_index()
        quarterly = pd.DataFrame(index=gdp.index)
        quarterly.index.name = "date"
        quarterly["real_gdp_level"] = gdp
        quarterly["gdp_growth_annualized"] = annualized_quarterly_growth(gdp)

    # Each raw series receives its own last observation date. Do not backfill gaps.
    raw_latest = _latest_raw(raw)
    return {
        "monthly": monthly,
        "quarterly": quarterly,
        "raw_latest": raw_latest,
        "raw_labels": RAW_SERIES,
        "source_links": SOURCE_LINKS,
        "statcan_details": statcan_details,
        "errors": errors,
        "fetched_at_utc": fetched_at,
        "all_sources_ok": not errors and len(raw_latest) == len(RAW_SERIES),
    }


def read_refresh_status(path: str | Path | None = None) -> dict[str, Any]:
    status_path = Path(path) if path else Path(__file__).parent / "data" / "refresh_status.json"
    try:
        return json.loads(status_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def write_refresh_status(
    bundle: dict[str, Any],
    *,
    path: str | Path | None = None,
    check_type: str = "manual verification check",
) -> dict[str, Any]:
    status_path = Path(path) if path else Path(__file__).parent / "data" / "refresh_status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    prior = read_refresh_status(status_path)
    current = bundle["raw_latest"]
    previous = prior.get("raw_latest", {})
    changed = [key for key, value in current.items() if value != previous.get(key)]
    if not previous:
        change_note = "baseline check; no prior scheduled check to compare"
    elif changed:
        change_note = f"new or revised observations: {', '.join(changed)}"
    else:
        change_note = "no new or revised observations since the previous check"
    status = {
        "last_success_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "check_type": check_type,
        "change_note": change_note,
        "raw_latest": current,
        "source_count": len(current),
    }
    status_path.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log_path = status_path.parent.parent / "docs" / "refresh_evidence.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"{status['last_success_utc']} | SUCCESS | {change_note} | {len(current)}/{len(RAW_SERIES)} raw series checked\n")
        for key, observation in sorted(current.items()):
            log.write(f"  {key}: {observation.get('date')} = {observation.get('value')}\n")
    return status


def strict_refresh() -> dict[str, Any]:
    bundle = fetch_dashboard_data()
    missing = set(RAW_SERIES) - set(bundle["raw_latest"])
    empty = [key for key in RAW_SERIES if bundle["raw_latest"].get(key, {}).get("value") is None]
    if bundle["errors"] or missing or empty:
        problems = [f"{source}: {message}" for source, message in bundle["errors"].items()]
        if missing:
            problems.append(f"missing raw series: {', '.join(sorted(missing))}")
        if empty:
            problems.append(f"no current observation: {', '.join(empty)}")
        raise RuntimeError("; ".join(problems))
    return bundle
