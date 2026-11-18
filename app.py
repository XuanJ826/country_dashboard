from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data_sources import fetch_dashboard_data, read_refresh_status


st.set_page_config(
    page_title="Canada | International Finance",
    page_icon="🇨🇦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
      html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
      .stApp { background: #f4f7fb; color: #132338; }
      [data-testid="stSidebar"] { background: #091629; }
      [data-testid="stSidebar"] * { color: #e4edf7 !important; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #aebed0 !important; }
      .hero { background: linear-gradient(118deg, #0b1b31 0%, #112c48 66%, #145267 100%); border-radius: 18px; padding: 1.7rem 2rem; color: #f4f9ff; margin: 0.1rem 0 1.2rem 0; }
      .hero-kicker { color: #5ce0d1; font: 500 0.72rem 'DM Mono', monospace; letter-spacing: .12em; text-transform: uppercase; margin-bottom: .45rem; }
      .hero h1 { color: #f4f9ff; font-size: 2.15rem; line-height: 1.12; margin: 0; letter-spacing: -.04em; }
      .hero p { color: #c3d4e5; margin: .65rem 0 0 0; font-size: .98rem; max-width: 850px; }
      .metric-card { background: white; border: 1px solid #e5ebf2; border-radius: 13px; padding: 1rem 1.05rem .9rem; min-height: 116px; box-shadow: 0 5px 18px rgba(19,35,56,.04); }
      .metric-label { color: #536579; font-size: .78rem; font-weight: 700; letter-spacing: .015em; min-height: 1.1rem; }
      .metric-value { color: #10233a; font-size: 1.53rem; font-weight: 800; letter-spacing: -.035em; line-height: 1.5; white-space: nowrap; }
      .metric-unit { color: #60748a; font-size: .72rem; min-height: .95rem; }
      .metric-date { color: #8493a3; font: 400 .66rem 'DM Mono', monospace; margin-top: .32rem; }
      .status-strip { display: flex; gap: .5rem; flex-wrap: wrap; margin: .2rem 0 1rem; }
      .status-pill { background: #e8eef5; border: 1px solid #dbe5ef; color: #465d74; border-radius: 20px; padding: .35rem .7rem; font: 400 .68rem 'DM Mono', monospace; }
      .section-kicker { color: #16847e; font: 500 .72rem 'DM Mono', monospace; letter-spacing: .09em; text-transform: uppercase; margin: .55rem 0 .2rem; }
      .section-title { color: #132338; font-weight: 800; font-size: 1.42rem; letter-spacing: -.03em; margin: 0 0 .2rem; }
      .section-desc { color: #66788b; font-size: .86rem; margin: 0 0 .65rem; }
      .chart-card { background: white; border: 1px solid #e5ebf2; border-radius: 13px; padding: .65rem .8rem .25rem; box-shadow: 0 5px 18px rgba(19,35,56,.035); height: 100%; }
      .chart-meta { color: #79899a; font: 400 .65rem 'DM Mono', monospace; line-height: 1.55; padding: .2rem .4rem .55rem; }
      .insight { background: white; border-left: 3px solid #1bb9a8; border-radius: 0 11px 11px 0; padding: .8rem 1rem; margin: .45rem 0; color: #40566c; font-size: .88rem; box-shadow: 0 4px 14px rgba(19,35,56,.035); }
      .fineprint { color: #8090a0; font-size: .74rem; }
      div[data-testid="stPlotlyChart"] { border-radius: 10px; }
      h2, h3 { letter-spacing: -.025em; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def get_live_data() -> dict:
    return fetch_dashboard_data()


def nonempty(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    return series.dropna()


def latest_value(frame: pd.DataFrame, key: str) -> tuple[float | None, pd.Timestamp | None]:
    if key not in frame.columns:
        return None, None
    values = nonempty(frame[key])
    if values.empty:
        return None, None
    return float(values.iloc[-1]), pd.Timestamp(values.index[-1])


def get_raw_date(bundle: dict, key: str) -> pd.Timestamp | None:
    value = bundle.get("raw_latest", {}).get(key, {}).get("date")
    if not value:
        return None
    try:
        return pd.Timestamp(value)
    except (TypeError, ValueError):
        return None


def month_label(value: pd.Timestamp | None) -> str:
    return value.strftime("%b %Y") if value is not None else "Unavailable"


def latest_quarter_label(value: pd.Timestamp | None) -> str:
    return f"Q{value.quarter} {value.year}" if value is not None else "Unavailable"


def monthly_window(frame: pd.DataFrame, start: pd.Timestamp | None) -> pd.DataFrame:
    if start is None or frame.empty:
        return frame.copy()
    return frame.loc[frame.index >= start].copy()


def make_figure(*, height: int = 315, y_title: str = "") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=12, r=16, t=22, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)),
        font=dict(family="Manrope, sans-serif", color="#536579", size=11),
        xaxis=dict(showgrid=False, linecolor="#e6edf4", tickfont=dict(size=10)),
        yaxis=dict(title=y_title, gridcolor="#eaf0f5", zerolinecolor="#d8e2ec", title_font=dict(size=10), tickfont=dict(size=10)),
    )
    return fig


def add_line(fig: go.Figure, x, y, name: str, color: str, *, width: float = 2.5) -> None:
    fig.add_trace(go.Scatter(x=x, y=y, name=name, mode="lines", line=dict(color=color, width=width), connectgaps=False))


def chart_note(units: str, frequency: str, source: str, latest: str) -> None:
    st.markdown(
        f'<div class="chart-meta">UNITS · {units}<br>FREQUENCY · {frequency}<br>SOURCE · {source}<br>LATEST OBSERVATION · {latest}</div>',
        unsafe_allow_html=True,
    )


def render_chart(title: str, fig: go.Figure, units: str, frequency: str, source: str, latest: str) -> None:
    st.markdown(f'<div class="chart-card"><div style="font-weight:800;color:#233a52;padding:.25rem .4rem 0">{title}</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "responsive": True})
    chart_note(units, frequency, source, latest)
    st.markdown("</div>", unsafe_allow_html=True)


def source_link(label: str, url: str) -> str:
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'


def display_metric(label: str, value: float | None, unit: str, obs_date: str, formatter: str) -> None:
    if value is None or pd.isna(value):
        shown = "Unavailable"
    elif formatter == "fx":
        shown = f"{value:,.4f}"
    elif formatter == "index":
        shown = f"{value:,.1f}"
    elif formatter == "money":
        shown = f"C${value:,.0f}M"
    elif formatter == "spread":
        shown = f"{value:+.2f} pp"
    elif formatter == "growth":
        shown = f"{value:+.1f}%"
    else:
        shown = f"{value:.1f}%"
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{shown}</div><div class="metric-unit">{unit}</div><div class="metric-date">LATEST OBS · {obs_date}</div></div>',
        unsafe_allow_html=True,
    )


def label_partial_month(raw_date: pd.Timestamp | None, month: pd.Timestamp | None) -> str:
    if raw_date is None or month is None:
        return "Unavailable"
    if raw_date.to_period("M") == month.to_period("M") and raw_date.day < raw_date.days_in_month:
        return f"{month_label(month)} month-to-date, through {raw_date:%d %b %Y}"
    return month_label(month)


def monthly_caption_date(frame: pd.DataFrame, key: str) -> str:
    _, latest = latest_value(frame, key)
    return month_label(latest)


try:
    bundle = get_live_data()
except Exception as exc:
    bundle = {"monthly": pd.DataFrame(), "quarterly": pd.DataFrame(), "raw_latest": {}, "errors": {"Dashboard": str(exc)}, "fetched_at_utc": None}

monthly_all = bundle.get("monthly", pd.DataFrame())
quarterly_all = bundle.get("quarterly", pd.DataFrame())
status = read_refresh_status()

with st.sidebar:
    st.markdown("### Explore the economy")
    range_option = st.radio("History", ["2 years", "5 years", "10 years", "All available"], index=2)
    st.markdown("---")
    st.markdown("**Quote convention**")
    st.caption("CAD per US$1. A rising quote means the U.S. dollar costs more Canadian dollars, so CAD has weakened.")
    st.markdown("**Real exchange rate**")
    st.caption("CAD per USD × U.S. CPI ÷ Canada CPI, rebased so the 2016 average = 100. A higher reading indicates improved Canadian price competitiveness under this convention.")
    st.markdown("---")
    st.caption("Monthly views use source observations at their published frequency. Partial months and release lags are called out in each chart.")

if monthly_all.empty:
    selected_monthly = monthly_all
    selected_quarterly = quarterly_all
    selected_start = None
else:
    last_month = monthly_all.index.max()
    if range_option == "All available":
        selected_start = None
    else:
        years = int(range_option.split()[0])
        selected_start = last_month - pd.DateOffset(years=years)
    selected_monthly = monthly_window(monthly_all, selected_start)
    selected_quarterly = quarterly_all.loc[quarterly_all.index >= selected_start].copy() if selected_start is not None else quarterly_all.copy()

st.markdown(
    """
    <div class="hero">
      <div class="hero-kicker">International Finance · Canada</div>
      <h1>Is the Canadian dollar becoming more competitive?</h1>
      <p>Compare the CAD/USD quote with a CPI-adjusted real exchange rate, then explore how inflation, interest rates, trade and domestic conditions move alongside it.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

live_at = bundle.get("fetched_at_utc")
if live_at:
    try:
        live_at = pd.Timestamp(live_at).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError):
        pass
else:
    live_at = "Unavailable"
scheduled_at = status.get("last_success_utc")
if scheduled_at:
    scheduled_at = pd.Timestamp(scheduled_at).strftime("%Y-%m-%d %H:%M UTC")
    scheduled_label = "Last successful GitHub Actions refresh" if "github actions" in status.get("check_type", "").lower() else "Last successful source check"
else:
    scheduled_at = "Not recorded yet"
    scheduled_label = "Last successful scheduled refresh"
st.markdown(
    f'<div class="status-strip"><span class="status-pill">LIVE SOURCE FETCH · {live_at}</span><span class="status-pill">{scheduled_label.upper()} · {scheduled_at}</span><span class="status-pill">HISTORY · {range_option.upper()}</span></div>',
    unsafe_allow_html=True,
)

errors = bundle.get("errors", {})
if errors:
    st.warning("Some official data sources are unavailable in this fetch. Affected values are left blank; no estimates are substituted.")
    with st.expander("Source connection details"):
        for source, message in errors.items():
            st.write(f"**{source}:** {message}")

st.markdown('<div class="section-kicker">Latest readings</div><div class="section-title">Eight indicators, one macro picture</div><div class="section-desc">Latest available observations differ by release schedule. Each card shows its own observation period.</div>', unsafe_allow_html=True)

fx_value, fx_period = latest_value(monthly_all, "fx_usdcad")
rer_value, rer_period = latest_value(monthly_all, "rer_index")
inflation_value, inflation_period = latest_value(monthly_all, "ca_inflation")
policy_value, policy_period = latest_value(monthly_all, "policy_gap")
yield_value, yield_period = latest_value(monthly_all, "yield_gap")
trade_value, trade_period = latest_value(monthly_all, "trade_balance")
gdp_value, gdp_period = latest_value(quarterly_all, "gdp_growth_annualized")
unemployment_value, unemployment_period = latest_value(monthly_all, "unemployment")

fx_obs = get_raw_date(bundle, "H10_CADUSD")
policy_obs = min([d for d in (get_raw_date(bundle, "V39079"), get_raw_date(bundle, "EFFR")) if d is not None], default=None)
yield_obs = min([d for d in (get_raw_date(bundle, "BD.CDN.10YR.DQ.YLD"), get_raw_date(bundle, "US10Y")) if d is not None], default=None)

cards = [
    ("Nominal FX", fx_value, "C$ per US$1", label_partial_month(fx_obs, fx_period), "fx"),
    ("Real FX index", rer_value, "2016 average = 100", month_label(rer_period), "index"),
    ("Canada inflation", inflation_value, "12-month CPI change", month_label(inflation_period), "percent"),
    ("Policy-rate gap", policy_value, "Canada target − U.S. EFFR", label_partial_month(policy_obs, policy_period), "spread"),
    ("10-year yield gap", yield_value, "Canada − U.S.", label_partial_month(yield_obs, yield_period), "spread"),
    ("Trade balance", trade_value, "Merchandise · C$ millions", month_label(trade_period), "money"),
    ("Real GDP growth", gdp_value, "Quarter-on-quarter, annualized", latest_quarter_label(gdp_period), "growth"),
    ("Unemployment", unemployment_value, "Seasonally adjusted", month_label(unemployment_period), "percent"),
]
for row_index in range(2):
    cols = st.columns(4, gap="small")
    for column, card in zip(cols, cards[row_index * 4 : row_index * 4 + 4]):
        with column:
            display_metric(*card)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-kicker">Currency & prices</div><div class="section-title">Nominal moves are not the whole story</div><div class="section-desc">The market quote shows the CAD’s value against USD. The real index adjusts that quote for relative Canadian and U.S. consumer prices.</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2, gap="medium")
with c1:
    fig = make_figure(y_title="C$ per US$1")
    if "fx_usdcad" in selected_monthly:
        data = selected_monthly["fx_usdcad"].dropna()
        add_line(fig, data.index, data.values, "CAD per US$1", "#087f8c")
    fig.update_layout(yaxis_tickformat=".3f")
    latest_text = label_partial_month(fx_obs, fx_period)
    render_chart(
        "Nominal exchange rate",
        fig,
        "Canadian dollars per US$1",
        "Federal Reserve H.10 business-daily rate; chart shows monthly mean",
        source_link("Federal Reserve Board H.10 historical rates", "https://www.federalreserve.gov/releases/h10/hist/dat00_ca.htm"),
        latest_text,
    )
with c2:
    fig = make_figure(y_title="Index (2016 average = 100)")
    if "rer_index" in selected_monthly:
        data = selected_monthly["rer_index"].dropna()
        add_line(fig, data.index, data.values, "CPI-based real FX", "#e59b39")
        fig.add_hline(y=100, line_color="#9cabb8", line_dash="dot", line_width=1)
    render_chart(
        "CPI-based real exchange rate",
        fig,
        "Index, 2016 average = 100",
        "Monthly; calculated from monthly FX mean and CPI levels",
        f'{source_link("Federal Reserve Board H.10", "https://www.federalreserve.gov/releases/h10/hist/dat00_ca.htm")}, {source_link("Statistics Canada CPI", "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401")}, {source_link("U.S. BLS CPI", "https://www.bls.gov/cpi/")}',
        month_label(rer_period),
    )

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-kicker">Inflation & interest rates</div><div class="section-title">Price growth and yield gaps</div><div class="section-desc">Differences can help frame exchange-rate moves, but markets respond to expectations and risk as well as observed rates.</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2, gap="medium")
with c1:
    fig = make_figure(y_title="12-month change (%)")
    for key, label, color in (("ca_inflation", "Canada CPI", "#087f8c"), ("us_inflation", "U.S. CPI", "#e59b39")):
        if key in selected_monthly:
            data = selected_monthly[key].dropna()
            add_line(fig, data.index, data.values, label, color)
    render_chart(
        "Inflation rates",
        fig,
        "Percent change from same month a year earlier",
        "Monthly; calculated from unadjusted all-items CPI indices",
        f'{source_link("Statistics Canada", "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401")}, {source_link("U.S. BLS CPI-U", "https://data.bls.gov/timeseries/CUUR0000SA0")}',
        f"Canada {month_label(inflation_period)}; U.S. {monthly_caption_date(monthly_all, 'us_inflation')}"
        + (
            f"; {month_label(latest_value(monthly_all, 'us_cpi')[1])} U.S. YoY unavailable (comparison-month CPI missing; no estimate)"
            if latest_value(monthly_all, "us_cpi")[1] is not None
            and latest_value(monthly_all, "us_inflation")[1] is not None
            and latest_value(monthly_all, "us_cpi")[1] > latest_value(monthly_all, "us_inflation")[1]
            else ""
        ),
    )
with c2:
    fig = make_figure(y_title="Percent per year")
    for key, label, color in (("ca_policy", "BoC overnight target", "#087f8c"), ("us_effr", "U.S. effective fed funds", "#e59b39")):
        if key in selected_monthly:
            data = selected_monthly[key].dropna()
            add_line(fig, data.index, data.values, label, color)
    render_chart(
        "Short-term policy rates",
        fig,
        "Percent per year; spread is percentage points",
        "Daily source rates; chart shows monthly means",
        f'{source_link("Bank of Canada V39079", "https://www.bankofcanada.ca/rates/interest-rates/canadian-interest-rates/")}, {source_link("New York Fed EFFR", "https://www.newyorkfed.org/markets/reference-rates/effr")}',
        label_partial_month(policy_obs, policy_period),
    )

c1, c2 = st.columns(2, gap="medium")
with c1:
    fig = make_figure(y_title="Percent per year")
    for key, label, color in (("ca_10y", "Government of Canada 10-year", "#087f8c"), ("us_10y", "U.S. Treasury 10-year", "#e59b39")):
        if key in selected_monthly:
            data = selected_monthly[key].dropna()
            add_line(fig, data.index, data.values, label, color)
    render_chart(
        "10-year government yields",
        fig,
        "Percent per year; spread is percentage points",
        "Daily source yields; chart shows monthly means",
        f'{source_link("Bank of Canada", "https://www.bankofcanada.ca/rates/interest-rates/canadian-interest-rates/")}, {source_link("U.S. Treasury", "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve")}',
        label_partial_month(yield_obs, yield_period),
    )
with c2:
    fig = make_figure(y_title="Canada minus U.S. (percentage points)")
    if "inflation_gap" in selected_monthly:
        data = selected_monthly["inflation_gap"].dropna()
        add_line(fig, data.index, data.values, "Inflation gap", "#7a63c7")
    if "policy_gap" in selected_monthly:
        data = selected_monthly["policy_gap"].dropna()
        add_line(fig, data.index, data.values, "Short-rate gap", "#087f8c")
    if "yield_gap" in selected_monthly:
        data = selected_monthly["yield_gap"].dropna()
        add_line(fig, data.index, data.values, "10-year yield gap", "#e59b39")
    fig.add_hline(y=0, line_color="#9cabb8", line_dash="dot", line_width=1)
    render_chart(
        "Cross-border rate and inflation gaps",
        fig,
        "Percentage points; Canada minus U.S.",
        "Monthly; daily rate inputs averaged within month",
        f'{source_link("Bank of Canada", "https://www.bankofcanada.ca/valet-api-how-to/")}, {source_link("New York Fed", "https://www.newyorkfed.org/markets/reference-rates/effr")}, {source_link("U.S. Treasury", "https://home.treasury.gov/treasury-daily-interest-rate-xml-feed")}, {source_link("BLS", "https://www.bls.gov/cpi/")}, {source_link("Statistics Canada", "https://www.statcan.gc.ca/en/start")}',
        f"Inflation {month_label(inflation_period)}; policy {label_partial_month(policy_obs, policy_period)}; 10-year {label_partial_month(yield_obs, yield_period)}",
    )

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-kicker">Trade & activity</div><div class="section-title">External balance and domestic conditions</div><div class="section-desc">The trade view uses merchandise goods only; the scatterplot compares same-month changes and is descriptive, not causal.</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2, gap="medium")
with c1:
    fig = make_figure(y_title="C$ millions")
    if "trade_balance" in selected_monthly:
        data = selected_monthly["trade_balance"].dropna()
        colors = ["#16a394" if value >= 0 else "#e27c70" for value in data.values]
        fig.add_trace(go.Bar(x=data.index, y=data.values, name="Merchandise balance", marker_color=colors, hovertemplate="%{x|%b %Y}<br>C$ %{y:,.1f}M<extra></extra>"))
        fig.add_hline(y=0, line_color="#8394a5", line_width=1)
    render_chart(
        "Merchandise trade balance",
        fig,
        "C$ millions, balance-of-payments basis",
        "Monthly, seasonally adjusted; all countries",
        source_link("Statistics Canada Table 12-10-0011-01", "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1210001101"),
        month_label(trade_period),
    )
with c2:
    scatter_data = selected_monthly.dropna(subset=["fx_change_pct", "trade_change_m"]) if {"fx_change_pct", "trade_change_m"}.issubset(selected_monthly.columns) else pd.DataFrame()
    fig = make_figure(height=315, y_title="Change in trade balance (C$ millions)")
    if not scatter_data.empty:
        fig.add_trace(go.Scatter(
            x=scatter_data["fx_change_pct"],
            y=scatter_data["trade_change_m"],
            mode="markers",
            name="Monthly observation",
            marker=dict(color="#087f8c", size=8, opacity=.72, line=dict(color="white", width=1)),
            text=[d.strftime("%b %Y") for d in scatter_data.index],
            hovertemplate="%{text}<br>CAD/USD change: %{x:+.2f}%<br>Trade balance change: C$ %{y:+,.0f}M<extra></extra>",
        ))
    fig.add_hline(y=0, line_color="#d2dce5", line_dash="dot", line_width=1)
    fig.add_vline(x=0, line_color="#d2dce5", line_dash="dot", line_width=1)
    fig.update_layout(xaxis_title="CAD per US$1 monthly change (%)")
    correlation = scatter_data["fx_change_pct"].corr(scatter_data["trade_change_m"]) if len(scatter_data) >= 3 else float("nan")
    n_obs = len(scatter_data)
    corr_text = f"r = {correlation:+.2f}, n = {n_obs} matched months" if pd.notna(correlation) else f"Not enough matched observations (n = {n_obs})"
    render_chart(
        "CAD moves and trade-balance changes",
        fig,
        "X: percent change in C$ per US$1; Y: change in C$ millions",
        "Monthly changes; same-month pairs",
        f'{source_link("Federal Reserve Board H.10 FX", "https://www.federalreserve.gov/releases/h10/hist/dat00_ca.htm")}, {source_link("Statistics Canada trade", "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1210001101")}',
        corr_text,
    )

c1, c2 = st.columns(2, gap="medium")
with c1:
    fig = make_figure(y_title="Annualized q/q growth (%)")
    if "gdp_growth_annualized" in selected_quarterly:
        data = selected_quarterly["gdp_growth_annualized"].dropna()
        fig.add_trace(go.Bar(x=data.index, y=data.values, name="Real GDP growth", marker_color=["#16a394" if v >= 0 else "#e27c70" for v in data.values]))
        fig.update_xaxes(dtick="M12", tickformat="%Y")
        fig.add_hline(y=0, line_color="#8394a5", line_width=1)
    render_chart(
        "Real GDP growth",
        fig,
        "Percent, annualized from quarter-on-quarter real GDP change",
        "Quarterly; seasonally adjusted at annual rates",
        source_link("Statistics Canada Table 36-10-0104-01", "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3610010401"),
        latest_quarter_label(gdp_period),
    )
with c2:
    fig = make_figure(y_title="Percent of labour force")
    if "unemployment" in selected_monthly:
        data = selected_monthly["unemployment"].dropna()
        add_line(fig, data.index, data.values, "Unemployment rate", "#7a63c7")
    render_chart(
        "Unemployment rate",
        fig,
        "Percent of labour force",
        "Monthly, seasonally adjusted, age 15+",
        source_link("Statistics Canada Table 14-10-0287-01", "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410028701"),
        month_label(unemployment_period),
    )

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-kicker">Reading the data</div><div class="section-title">A concise snapshot</div>', unsafe_allow_html=True)

insights = []
if len(selected_monthly) > 1 and "fx_usdcad" in selected_monthly:
    fx = selected_monthly["fx_usdcad"].dropna()
    if len(fx) > 1 and fx.iloc[0] != 0:
        move = (fx.iloc[-1] / fx.iloc[0] - 1) * 100
        direction = "weakened" if move > 0 else "strengthened"
        insights.append(f"Over the selected window, the CAD {direction} by about {abs(move):.1f}% against USD on the nominal quote (CAD per US$1).")
if len(selected_monthly) > 1 and "rer_index" in selected_monthly:
    rer = selected_monthly["rer_index"].dropna()
    if len(rer) > 1:
        delta = rer.iloc[-1] - rer.iloc[0]
        phrase = "improved" if delta > 0 else "weakened" if delta < 0 else "was little changed"
        insights.append(f"The CPI-based relative-price index {phrase} by {abs(delta):.1f} points; a rise indicates better Canadian price competitiveness under the stated formula.")
if policy_value is not None and inflation_period is not None:
    gap, _ = latest_value(monthly_all, "inflation_gap")
    if gap is not None:
        gap_word = "above" if gap > 0 else "below" if gap < 0 else "at"
        insights.append(f"In {month_label(inflation_period)}, Canadian CPI inflation was {abs(gap):.1f} percentage points {gap_word} U.S. inflation. The latest short-rate gap is {policy_value:+.2f} percentage points (Canada minus U.S. EFFR).")
if not scatter_data.empty and pd.notna(correlation):
    insights.append(f"Same-month changes in CAD/USD and the merchandise balance have a correlation of {correlation:+.2f} across {n_obs} observations. This is a descriptive association, not evidence that trade caused the currency move.")
if not insights:
    insights.append("A concise relationship summary will appear when the required source series are available.")
for insight in insights:
    st.markdown(f'<div class="insight">{insight}</div>', unsafe_allow_html=True)

with st.expander("Definitions, latest source values, and downloads"):
    st.markdown("**Why the real exchange rate can differ from the nominal rate**")
    st.write("The nominal quote records the CAD price of one U.S. dollar. The real measure adds the relative price-level ratio. If the nominal rate is unchanged while U.S. prices rise faster than Canadian prices, the real index rises under this convention. The measure is bilateral and CPI-based; it is not trade weighted.")
    st.markdown("**Latest raw observations checked at source**")
    raw_rows = []
    for series_id, observation in sorted(bundle.get("raw_latest", {}).items()):
        observation_date = observation.get("date") or "Unavailable"
        if series_id == "62305752" and observation_date != "Unavailable":
            source_date = pd.Timestamp(observation_date)
            observation_date = f"Q{source_date.quarter} {source_date.year}"
        raw_rows.append({
            "Series": bundle.get("raw_labels", {}).get(series_id, series_id),
            "Series ID": series_id,
            "Latest observation": observation_date,
            "Source value": observation.get("value"),
        })
    if raw_rows:
        st.dataframe(pd.DataFrame(raw_rows), hide_index=True, use_container_width=True)
    else:
        st.info("No source observations are currently available.")
    st.caption("Source verification table and refresh log are included in the project under docs/.")

    if not selected_monthly.empty:
        st.download_button(
            "Download displayed monthly series (CSV)",
            data=selected_monthly.to_csv(index_label="month").encode("utf-8"),
            file_name="canada_international_finance_monthly.csv",
            mime="text/csv",
        )
    if not selected_quarterly.empty:
        st.download_button(
            "Download displayed quarterly GDP series (CSV)",
            data=selected_quarterly.to_csv(index_label="quarter_end").encode("utf-8"),
            file_name="canada_real_gdp_quarterly.csv",
            mime="text/csv",
        )

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="fineprint">All gaps are percentage-point differences. Monthly chart points derived from daily data are averages. Observation dates are shown independently of refresh timestamps. Data are descriptive and may be revised by source agencies.</div>', unsafe_allow_html=True)
