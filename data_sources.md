# Data sources and calculations

The dashboard requests public observations directly from the issuing statistical agencies or central banks. It does not forecast or impute missing observations. Raw source frequency, display frequency, units, and the latest observation date appear below the relevant chart and in the dashboard's indicator cards.

## Indicators

| Dashboard indicator | Official series and source | Source frequency / display frequency | Units and calculation |
|---|---|---|---|
| Nominal exchange rate | Federal Reserve Board H.10 historical Canadian-dollar spot series | Business daily / monthly mean of daily values | Canadian dollars per US$1. The quote rises when CAD weakens against USD. |
| CPI-based real exchange rate | Federal Reserve Board H.10 CAD/USD rate; Statistics Canada Table 18-10-0004-01 all-items CPI; U.S. BLS `CUUR0000SA0` CPI-U | FX daily and CPI monthly / monthly | `RER_t = FX_t × CPI_US,t ÷ CPI_CA,t`; divide by the average of this measure over 2016 and multiply by 100. A higher index means U.S. prices in CAD rose relative to Canadian prices under this convention. It is not a PPP valuation verdict. |
| Inflation | Statistics Canada Table 18-10-0004-01; U.S. BLS `CUUR0000SA0` | Monthly / monthly | 12-month percent change in each unadjusted all-items CPI index. The dashboard also shows the Canada minus U.S. inflation gap in percentage points. |
| Policy-rate gap | Bank of Canada Valet `V39079`; Federal Reserve Bank of New York EFFR API | Business daily / monthly mean | BoC target overnight rate minus the effective federal funds rate, in percentage points. The EFFR is a market rate, not the FOMC target midpoint. |
| 10-year yield gap | Bank of Canada Valet `BD.CDN.10YR.DQ.YLD`; U.S. Treasury Daily Treasury Par Yield Curve Rates (`BC_10YEAR`) | Business daily / monthly mean | Government of Canada 10-year benchmark yield minus U.S. Treasury 10-year par yield, in percentage points. The two benchmark methodologies are not identical. |
| Merchandise trade balance | Statistics Canada Table 12-10-0011-01; Trade Balance, Balance of payments, Seasonally adjusted, All countries | Monthly / monthly | Canadian dollars, millions as published. A positive value is a surplus; a negative value is a deficit. This measure covers merchandise trade, not services. |
| Real GDP growth | Statistics Canada Table 36-10-0104-01; GDP at market prices, chained 2017 dollars, seasonally adjusted at annual rates | Quarterly / quarterly | Quarterly growth annualized as `((GDP_t / GDP_(t-1))^4 − 1) × 100`. The GDP level is not shown as a nominal dollar amount. |
| Unemployment rate | Statistics Canada Table 14-10-0287-01; Canada, total gender, age 15+, estimate, seasonally adjusted | Monthly / monthly | Percent of the labour force. |

## Source links

- [Federal Reserve Board H.10 historical Canadian-dollar series](https://www.federalreserve.gov/releases/h10/hist/dat00_ca.htm) and [weekly H.10 release schedule](https://www.federalreserve.gov/releases/h10/).
- [Bank of Canada Valet API guide](https://www.bankofcanada.ca/valet-api-how-to/) for the Canadian interest-rate series.
- [Statistics Canada CPI table 18-10-0004-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401).
- [Statistics Canada international merchandise trade table 12-10-0011-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1210001101).
- [Statistics Canada quarterly GDP table 36-10-0104-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3610010401).
- [Statistics Canada labour force table 14-10-0287-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410028701).
- [U.S. BLS CPI series identifier](https://www.bls.gov/cpi/factsheets/cpi-series-ids.htm) and [Public Data API](https://www.bls.gov/developers/).
- [New York Fed effective federal funds rate](https://www.newyorkfed.org/markets/reference-rates/effr) and [Markets Data APIs](https://markets.newyorkfed.org/static/docs/markets-api.html).
- [U.S. Treasury daily rates and XML feed](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed) and [yield-curve methodology](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/yield-methodology).

## Refresh and missing data

The Streamlit app checks live sources when its six-hour cache expires. GitHub Actions also checks the sources on weekdays at 22:00 UTC. The workflow saves a UTC timestamp, latest raw observation dates, verification table, and log to the repository. If any required source fails, the workflow exits unsuccessfully and does not replace the last successful refresh status. The dashboard shows unavailable indicators when a source fetch fails; it never carries forward a value as if it were newly observed. H.10 is normally released weekly, while other sources publish at daily, monthly, or quarterly intervals.

Some indicators update monthly or quarterly, so multiple successful daily refreshes can have no new observation for those series. The refresh log records that result separately from the last successful refresh time.

## Analysis limits

The real exchange-rate index is one bilateral CPI-based measure, not a trade-weighted real effective exchange rate. CPI baskets and coverage differ between Canada and the United States. H.10 is the Federal Reserve's published CAD-per-USD spot series. Interest spreads can change with expectations, risk premia, and policy; they are not direct FX forecasts. The trade scatterplot uses same-month changes and is descriptive, not causal.
