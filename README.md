# Canada International Finance Dashboard

An MBA-course dashboard for exploring whether the Canadian dollar is gaining or losing price competitiveness and how exchange rates move alongside inflation, interest rates, trade, GDP, and unemployment.

## Run locally

Use Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python refresh_data.py
streamlit run app.py
```

The app retrieves live observations from official public endpoints. It caches a fetch for up to six hours, shows the live fetch time and the latest observation date for every indicator, and reports source errors without filling missing observations.

## Deploy with GitHub and Streamlit Community Cloud

1. Create a GitHub repository and add these project files to its default branch.
2. In the repository, open **Settings → Actions → General** and allow GitHub Actions to read and write repository contents. The included workflow needs this permission to record refresh timestamps and verification evidence.
3. Push the project to GitHub. The workflow at `.github/workflows/refresh-data.yml` runs on weekdays at 22:00 UTC and can also be started with **Actions → Refresh economic data → Run workflow**.
4. In Streamlit Community Cloud, choose **Create app**, select the repository and branch, and set the app file to `app.py`. Keep Python at 3.11.
5. The GitHub workflow updates `data/refresh_status.json` and the verification evidence after a successful check. A failed source check leaves the previous successful timestamp in place and appears in the GitHub Actions run log.

No API keys or Streamlit secrets are required.

## Project files

- `app.py` — interactive Streamlit dashboard and charts.
- `data_sources.py` — API retrieval, transformations, and source metadata.
- `refresh_data.py` — strict source check and evidence writer used by the scheduled workflow.
- `.github/workflows/refresh-data.yml` — weekday refresh schedule.
- `docs/data_sources.md` — source series, units, formulas, and interpretation.
- `docs/data_verification.md` and `.csv` — observations checked against official source endpoints.
- `docs/refresh_evidence.log` — successful refresh runs, including checks where no new observations were released.

## Measures and interpretation

The spot quote is **Canadian dollars per U.S. dollar (CAD/USD in the price-quote sense)** and uses the Federal Reserve Board's H.10 historical daily series. A rising quote means one U.S. dollar costs more Canadian dollars, so the Canadian dollar has weakened. The real exchange-rate index follows the course-guide convention `S × P_US / P_CA`, using `S` in CAD per USD, monthly CPI levels, and a 2016 average of 100. Under this definition, a higher real index indicates that U.S. prices expressed in CAD have risen relative to Canadian prices; that is consistent with improved Canadian price competitiveness. It is a relative-price indicator, not a claim of overvaluation or a forecast.

The interest-rate gaps use the Bank of Canada's overnight target versus the New York Fed's effective federal funds rate, and the monthly mean of Canada and U.S. 10-year government yields. Rates are shown in percent and their gaps in percentage points. Trade is Canada's seasonally adjusted merchandise balance on a balance-of-payments basis, not the broader goods-and-services current account. Details and caveats are in `docs/data_sources.md`.

The charts are descriptive. Correlation does not identify cause: exchange rates, trade, inflation, and interest rates can respond to common shocks and expectations.
