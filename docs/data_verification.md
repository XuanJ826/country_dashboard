# Data verification

This table records one current observation from each source series used by the dashboard. The refresh script reads the official publisher endpoint, checks that each series has a dated numeric observation, and retains the source precision. Derived dashboard measures are verified through their component observations and documented formulas below.

Last verified: **2026-11-25T04:46:01+00:00** (UTC).

| Source series | Date | Retrieved source value | Original source | Result |
|---|---:|---:|---|---|
| `H10_CADUSD` — Federal Reserve Board H.10 — Canadian dollars per U.S. dollar spot rate | 2026-11-20 | 1.4323 | [Federal Reserve Board H.10](https://www.federalreserve.gov/releases/h10/hist/dat00_ca.htm) | Source pull matched; no estimate or manual adjustment |
| `V39079` — Bank of Canada — target for the overnight rate | 2026-11-23 | 2.5 | [Bank of Canada](https://www.bankofcanada.ca/valet/observations/V39079/json?start_date=2015-01-01) | Source pull matched; no estimate or manual adjustment |
| `BD.CDN.10YR.DQ.YLD` — Bank of Canada — Government of Canada 10-year benchmark yield | 2026-11-23 | 3.68 | [Bank of Canada](https://www.bankofcanada.ca/valet/observations/BD.CDN.10YR.DQ.YLD/json?start_date=2015-01-01) | Source pull matched; no estimate or manual adjustment |
| `41690973` — Statistics Canada — Canada all-items CPI index (published reference base) | 2026-10-01 | 170.4 | [Statistics Canada](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401) | Source pull matched; no estimate or manual adjustment |
| `87008984` — Statistics Canada — merchandise trade balance, balance-of-payments basis | 2026-09-01 | 5350.1 | [Statistics Canada](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1210001101) | Source pull matched; no estimate or manual adjustment |
| `62305752` — Statistics Canada — real GDP at market prices, chained 2017 dollars | Q2 2026 | 2524127.0 | [Statistics Canada](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3610010401) | Source pull matched; no estimate or manual adjustment |
| `2062815` — Statistics Canada — unemployment rate, Canada, seasonally adjusted | 2026-10-01 | 6.7 | [Statistics Canada](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410028701) | Source pull matched; no estimate or manual adjustment |
| `CUUR0000SA0` — U.S. Bureau of Labor Statistics — CPI-U, all items, U.S. city average, not seasonally adjusted | 2026-10-01 | 337.511 | [U.S. Bureau of Labor Statistics](https://data.bls.gov/timeseries/CUUR0000SA0) | Source pull matched; no estimate or manual adjustment |
| `EFFR` — Federal Reserve Bank of New York — effective federal funds rate | 2026-11-23 | 3.88 | [Federal Reserve Bank of New York](https://www.newyorkfed.org/markets/reference-rates/effr) | Source pull matched; no estimate or manual adjustment |
| `US10Y` — U.S. Department of the Treasury — daily 10-year par yield | 2026-11-24 | 4.91 | [U.S. Department of the Treasury](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve) | Source pull matched; no estimate or manual adjustment |

## Derived dashboard measures

- Real exchange-rate index: `FX (CAD per USD) × U.S. CPI ÷ Canada CPI`, divided by the 2016 average and multiplied by 100. A higher index means U.S. prices expressed in CAD rose relative to Canadian prices under this stated convention.
- Canada/U.S. inflation gap: Canada CPI 12-month percent change minus U.S. CPI 12-month percent change.
- Policy-rate spread: monthly mean of the Bank of Canada overnight target minus the New York Fed effective federal funds rate, in percentage points.
- 10-year yield spread: monthly mean Government of Canada 10-year benchmark yield minus the U.S. Treasury 10-year par yield, in percentage points.
- Real GDP growth: quarterly chained-dollar GDP growth, annualized as `((GDP_t / GDP_(t-1))^4 − 1) × 100`.

The source check compares values at their original published precision. It does not claim that different agencies use identical definitions or release calendars; the dashboard labels those differences and shows observation dates separately.

See [data sources and calculations](data_sources.md) and the [refresh evidence log](refresh_evidence.log).
