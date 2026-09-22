# Stock Insights

Stock Insights is an educational Streamlit dashboard for exploring historical Indian equity data, with a focus on Nifty-style company tickers. It combines PostgreSQL storage, Yahoo Finance daily data, pandas calculations, and Plotly/Streamlit visualizations in one interactive application.

The dashboard is intended for learning and analysis. Its trend labels and forecasts are heuristic signals, not investment advice or guaranteed predictions.

## Contents

- [What the project solves](#what-the-project-solves)
- [Key capabilities and USP](#key-capabilities-and-usp)
- [Architecture and data flow](#architecture-and-data-flow)
- [Application walkthrough](#application-walkthrough)
- [Data and calculations](#data-and-calculations)
- [Project files](#project-files)
- [Database schema](#database-schema)
- [Setup and execution](#setup-and-execution)
- [Browser verification](#browser-verification)
- [Operational notes and limitations](#operational-notes-and-limitations)
- [Recommended improvements](#recommended-improvements)

## What the project solves

The project provides a single learning-oriented workspace for questions that normally require several separate tools:

1. How has a selected stock's price moved over a chosen period?
2. Is the current movement part of a broader trend or a sudden price event?
3. How much volatility and relative risk does the stock exhibit?
4. Which selected stocks move together, and how do their normalized prices compare?
5. What simple, rule-based trend signals and budget-based share estimates can be derived from recent history?

The application solves these questions by storing a reusable OHLCV history in PostgreSQL and recalculating indicators when the user changes the selected tickers, dates, or analysis controls.

## Key capabilities and USP

### Core USP

- **One workflow from ingestion to insight:** Yahoo Finance data is fetched, upserted into PostgreSQL, queried by ticker/date, transformed with pandas, and displayed in Streamlit.
- **Multiple analysis lenses:** price trends, abrupt moves, volatility, risk, comparison, correlation, and heuristic forecasting are available as separate tabs.
- **Learning-first explanations:** each major tab explains what the metric means and why it may matter, rather than showing charts without context.
- **User-controlled analysis:** users can select multiple companies, choose a date range, change indicator display modes, set abrupt-change and volatility thresholds, and test budget/horizon scenarios.
- **Downloadable results:** indicator tables and comparison data can be downloaded as CSV files directly from the interface.
- **Idempotent storage:** company insertion uses ticker uniqueness, and price ingestion uses `(company_id, trade_date)` upserts, so repeated syncs update existing rows instead of duplicating them.

## Architecture and data flow

```text
Yahoo Finance (yfinance)
          |
          v
data_fetcher.py -- fetch new/overlapping daily OHLCV rows
          |
          v
PostgreSQL: companies + stock_prices
          |
          v
calculations.py -- SQL reads, indicators, risk, correlation, comparison
          |
          v
app.py -- Streamlit controls, tabs, Plotly charts, CSV downloads
          |
          v
User-facing dashboard at http://localhost:8501
```

### Startup sequence

When `app.py` runs:

1. Streamlit configures the page and initializes the Dark/Light theme state.
2. `silent_update()` calls `run_fetching()` through `st.cache_resource(ttl=24 * 60 * 60)`. This means the automatic sync is intended to run at most once per Streamlit cache lifetime.
3. `get_company_list()` reads the PostgreSQL `companies` table. If it is empty, the default company list is inserted automatically.
4. The sidebar loads ticker, start-date, and end-date controls.
5. Each tab queries data and computes only the analysis required for that view.

## Application walkthrough

The sidebar is shared by all tabs. It contains the theme switcher, company multiselect, start/end date inputs, data staleness information, selected-stock sectors, and the displayed date range.

### Tab 1: Price Trends

**Purpose:** Understand historical price behavior and common technical indicators for each selected ticker.

**User controls:**

- `Overlay on Chart` or `Separate Panels` display mode.
- Moving averages: 20 SMA, 50 SMA, 200 SMA, 20 EMA, and 50 EMA.
- Oscillators: RSI (14) and MACD.
- Shared company and date-range filters from the sidebar.

**What it displays:**

- Latest closing price metric.
- Close-price chart with optional moving-average overlays.
- Separate close/indicator charts when panel mode is selected.
- RSI (14) and MACD charts when enabled.
- Full enriched indicator data in an expandable table.
- CSV downloads for overlay data and indicator data.

**Indicators and learning insight:**

- **SMA:** average close over a fixed window; it smooths noise and helps show direction.
- **EMA:** weighted moving average that reacts faster to recent prices.
- **RSI (14):** momentum oscillator. The interface explains values above 70 as potentially overbought and values below 30 as potentially oversold. Values are not treated as guarantees.
- **MACD:** difference between 12-period and 26-period EMAs, with a 9-period signal EMA and histogram.
- **Golden_Cross:** a binary column indicating whether SMA 50 is above SMA 200. It is calculated and included in the data table, although it is not separately plotted in the current UI.

**Solution provided:** This tab brings trend, momentum, and moving-average context together so a learner can inspect direction and momentum without manually calculating indicators.

### Tab 2: Abrupt Changes

**Purpose:** Detect unusually large one-day percentage price moves that may deserve investigation.

**User control:** A threshold slider from 3% to 20%, defaulting to 7%.

**What it displays:**

- A per-ticker Plotly bar chart of daily percentage movements.
- A table containing rows whose absolute daily percentage change exceeds the selected threshold.
- An informational state when no qualifying movement is found.

**Calculation:** `close.pct_change()` is computed and rows satisfying `abs(pct_change) > threshold` are retained. The slider value is converted from a displayed percentage to a decimal fraction before the calculation.

**Solution provided:** This view turns a long historical series into an event list, helping users investigate possible news, volume, breakout, or fear-driven days. It identifies events; it does not explain their cause because the application does not ingest news or corporate-event data.

### Tab 3: Risk & Volatility

**Purpose:** Show how unstable recent prices have been and provide a relative risk series.

**User control:** Rolling volatility window from 5 to 55 trading observations, defaulting to 20.

**What it displays:** For each selected ticker, a line chart with `volatility` and `risk`.

**Calculation:**

- `volatility = close.rolling(window).std()`
- `risk = volatility / close`

The current implementation uses rolling standard deviation of price levels, not annualized return volatility. The risk series is a simple price-relative ratio.

**Solution provided:** This tab helps users see periods of changing uncertainty and relate higher movement to capital-protection or position-sizing decisions. It is an exploratory risk view, not a portfolio risk model.

### Tab 4: Compare & Correlate

**Purpose:** Compare selected stocks on a common scale and inspect how their historical prices move together.

**Requirement:** At least two companies must be selected for the comparison view to produce output.

**What it displays:**

- A normalized price comparison chart for the selected tickers.
- A CSV download of the comparison data.
- A pandas correlation matrix with a color gradient.
- A Plotly correlation heatmap.

**How it works:** `compare_companies()` loads each ticker, indexes its close series by `trade_date`, and concatenates series using an inner join. The current function returns aligned raw close prices; it does not itself divide each series by its first value, even though the UI labels the chart as normalized. `correlation_analysis()` uses the same date-aligned price series and pandas `.corr()`.

**Solution provided:** This view supports relative visual comparison and diversification-oriented exploration. A high positive correlation means the selected price series historically moved together; correlation is historical and does not prove future behavior or causality.

### Tab 5: Smart Insights

**Purpose:** Convert recent trend statistics into an easy-to-read heuristic signal, a confidence score, a budget-based share estimate, and a simple linear future tendency.

**User controls:**

- Budget presets from INR 0 to INR 1,000,000.
- `Short Term` or `Long Term` horizon.
- Forecast window shown as 15 business days for short term or 60 business days for long term.

**Per-ticker output:**

- Signal: `Strong Buy`, `Buy`, `Hold`, or `Risky / Avoid`.
- Confidence percentage, clamped between 5% and 95%.
- Trend percentage over the selected lookback.
- Recent price volatility percentage.
- Approximate whole shares purchasable with the selected budget.
- Chart containing historical close, SMA, and future buy/sell markers.
- Expandable tables of forecasted buy and sell opportunities.

**Signal logic:**

- Short Term uses up to the last 60 rows; Long Term uses up to the last 180 rows.
- A linear regression slope and first-to-last percentage change are calculated.
- Confidence starts at 50 and is adjusted by `pct_change / 2 - volatility / 4`, then clamped to 5-95.
- Positive change above 5% with positive slope gives `Strong Buy`.
- Positive change above 1% with positive slope gives `Buy`.
- Negative change below -5% with negative slope gives `Risky / Avoid`.
- All other cases give `Hold`.

**Forecast logic:** A straight-line fit is applied to recent closing prices. The future line is generated for 15 or 60 business dates. Future rows below their rolling 20-period SMA are labeled buy opportunities; rows above it are labeled sell opportunities.

**Solution provided:** This tab makes trend mathematics approachable for scenario learning, especially by connecting a budget to an approximate share count. It is not a machine-learning model, does not model fundamentals, and should not be used as an autonomous trading strategy.

## Data and calculations

### Stored fields

Each price row contains:

- Company relationship and ticker metadata.
- Trading date.
- Open, high, low, and close prices.
- Trading volume.

`fetch_prices()` aliases PostgreSQL columns to the standard dataframe fields `open`, `high`, `low`, `close`, and `volume`, converts them to numeric values, removes rows without a close, and sorts by date ascending.

### Data ingestion behavior

`data_fetcher.py` downloads daily adjusted data from Yahoo Finance using `yfinance.download()`.

- Initial history begins at `2015-01-01`.
- Existing tickers are fetched from seven calendar days before their latest stored date. This overlap helps repair small gaps.
- Rows are written with `ON CONFLICT (company_id, trade_date) DO UPDATE`.
- A 0.3-second pause is applied between tickers.
- Recent yfinance MultiIndex column shapes are handled when reading Open, High, Low, Close, and Volume.

### Helper calculations in `calculations.py`

The module also contains reusable helpers used directly or indirectly by the dashboard:

- `get_close_price_column()` locates the close column case-insensitively.
- `compute_sma()` adds a configurable SMA column, default 20.
- `compute_ema()` adds a configurable EMA column, default 20.
- `detect_abrupt_changes()` returns rows over a percentage threshold.
- `fetch_current_price()` retrieves the latest stored close for a ticker.
- `fetch_company_info()` retrieves company name and ticker metadata.
- `best_time_to_invest()` returns rows where close is above SMA; it is currently a reusable helper and is not called by the visible dashboard.

## Project files

| File                                 | Responsibility                                                                                                                 |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| `app.py`                           | Main Streamlit application, sidebar, theme, five tabs, charts, controls, and CSV download buttons.                             |
| `calculations.py`                  | PostgreSQL reads and pandas calculations for indicators, abrupt moves, volatility, correlation, comparison, and trend helpers. |
| `data_fetcher.py`                  | Loads company tickers, downloads Yahoo Finance history, and upserts OHLCV rows into PostgreSQL.                                |
| `db_config.py`                     | PostgreSQL connection settings and`create_connection()`.                                                                     |
| `schema.sql`                       | Creates the`companies` and `stock_prices` tables plus the company/date index.                                              |
| `insert_companies.py`              | Defines and idempotently inserts the default ticker list.                                                                      |
| `check_data.py`                    | Prints companies and stored row counts for database inspection.                                                                |
| `export.py`                        | Exports joined company and price data to a CSV file.                                                                           |
| `plotting.py`                      | Renders the Plotly correlation heatmap in Streamlit.                                                                           |
| `sql_bg_querries.sql`              | Example SQL queries documenting filtering, latest-price, date-range, comparison, and latest-date scenarios.                    |
| `stock_prices_export.csv`          | Generated/exported snapshot of stored stock prices; not the live source used by the app.                                       |
| `data_fetch_log.txt`               | Historical runtime log from an earlier ingestion/dashboard run.                                                                |
| `solution.pdf`                     | Project reference/solution document included with the folder.                                                                  |
| `Stock_Analysis_Documentation.pdf` | Additional project documentation/reference artifact.                                                                           |
| `tempCodeRunnerFile.py`            | Editor-generated scratch file; it is not part of the application and currently contains an indentation error.                  |
| `__pycache__/`                     | Python bytecode cache; generated and not required as source.                                                                   |

## Database schema

`schema.sql` creates two tables:

### `companies`

- `company_id SERIAL PRIMARY KEY`
- `company_name VARCHAR(100) NOT NULL`
- `ticker_symbol VARCHAR(200) UNIQUE NOT NULL`

### `stock_prices`

- `id SERIAL PRIMARY KEY`
- `company_id` foreign key to `companies(company_id)` with cascade delete
- `trade_date DATE NOT NULL`
- `open_price`, `high_price`, `low_price`, `close_price` as numeric values
- `volume BIGINT`
- Unique constraint on `(company_id, trade_date)`

An index on `(company_id, trade_date)` supports ticker/date history reads.

## Setup and execution

### Prerequisites

- Windows PowerShell.
- PostgreSQL running locally.
- A PostgreSQL database named `DemoDb`, unless the configuration is changed.
- Python dependencies installed in the parent project virtual environment.
- Network access to Yahoo Finance for data synchronization.

### Configure PostgreSQL

Edit `db_config.py` for the local PostgreSQL host, port, database, user, and password. The current file contains a hard-coded password placeholder/value, so credentials should be moved to environment variables before sharing or deploying the project.

Create the schema from the PostgreSQL client of your choice:

```powershell
psql -U postgres -d DemoDb -f schema.sql
```

### Activate the provided virtual environment and run

The virtual environment is one directory above `Stock-Insights-`, under `Python_GUI\venv`:

```powershell
cd C:\Users\Shruti\jk\Python\Python_GUI
.\venv\Scripts\Activate.ps1
cd C:\Users\Shruti\jk\Python\Python_GUI\Stock-Insights-\Stocks_predictor
streamlit run app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`.

## Browser verification

The live dashboard was checked at `http://localhost:8502` with two selected tickers (`ADANIENT.NS` and `ADANIPORTS.NS`) and the date range `2024-01-13` through `2026-09-23`.

| Tab                 | Runtime result | Observed output                                                                                                                                                                         |
| ------------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Price Trends        | Passed         | Latest close metrics, price/MA chart, indicator controls, RSI selection, and explanatory content rendered.                                                                              |
| Abrupt Changes      | Passed         | Threshold slider rendered at 7%, and abrupt-movement charts/tables rendered for both tickers.                                                                                           |
| Risk & Volatility   | Passed         | Volatility window rendered at 20, with a volatility-versus-risk visualization for both tickers.                                                                                         |
| Compare & Correlate | Passed         | Price comparison, CSV download control, correlation matrix, and heatmap rendered. The observed correlation for the test pair was approximately`0.8690`.                               |
| Smart Insights      | Passed         | Budget selector at INR 40,000, short-term 15-day horizon, signal/confidence/trend/volatility metrics, share estimate, forecast chart, and forecast expanders rendered for both tickers. |

The sidebar also rendered the Dark/Light theme controls, ticker multiselect, date inputs, freshness message, selected-stock sectors, and date-range summary. The page responded successfully over HTTP with status `200`.

The browser console emitted non-blocking Plotly/Vega warnings such as `Infinite extent for field` during Streamlit rerenders, and one transient `Unrecognized data set` page error while charts updated. These did not prevent any tab from rendering, but they are worth investigating if chart flicker, blank states, or noisy browser logs become a concern.

### Populate and refresh data manually

```powershell
cd C:\Users\Shruti\jk\Python\Python_GUI\Stock-Insights-\Stocks_predictor
python insert_companies.py
python data_fetcher.py
```

The dashboard also calls the updater on startup through its daily Streamlit cache. A manual run is useful for diagnosing ingestion independently of the UI.

### Inspect and export data

```powershell
python check_data.py
python export.py
python export.py --output my_stock_snapshot.csv
```

## Operational notes and limitations

- **Database is required at startup.** Every main data path calls `create_connection()`. If PostgreSQL is unavailable or credentials are wrong, the dashboard cannot load normally.
- **No dependency manifest is included.** The project currently relies on the pre-existing `venv`; a `requirements.txt` or `pyproject.toml` would make setup reproducible.
- **Automatic updates are expensive.** On an empty database, the first sync requests history from 2015 for every default ticker. Yahoo Finance availability and rate limits can affect results.
- **Branding says Nifty50, but the default list is finite and maintained in code.** The actual selectable universe is the list in `insert_companies.py`, not a dynamically retrieved index constituent list.
- **Several views intentionally ignore the sidebar date range.** The Risk tab, Correlation analysis, and Smart Insights call `fetch_prices(ticker)` without passing `start_date` and `end_date`, so those views use all stored history.
- **The comparison is labeled normalized but currently returns aligned raw closes.** True normalization would require a baseline transformation such as each series divided by its first aligned value.
- **Risk is a heuristic.** It is rolling price-level standard deviation divided by price, not annualized return volatility, beta, Value at Risk, or portfolio drawdown risk.
- **Forecasts are linear extrapolations.** They do not use a trained forecasting model, fundamentals, news, macroeconomic variables, or transaction costs.
- **Data freshness is informational.** The sidebar compares each ticker's latest stored date with the current date and flags delays of two or more days; market holidays and source delays can produce legitimate gaps.
- **`check_data.py` contains a schema mismatch.** Its count query refers to `sp.price_id`, while `schema.sql` defines the primary key as `stock_prices.id`. The query should use `COUNT(sp.id)` before relying on that diagnostic script.
- **Scratch and generated artifacts are not runtime dependencies.** The CSV, log, PDFs, `__pycache__`, and `tempCodeRunnerFile.py` should not be treated as application source.
- **Educational disclaimer:** The application itself labels its output as educational and not financial advice. Users should independently validate data and decisions.

## Recommended improvements

1. Add a `requirements.txt` or `pyproject.toml` covering Streamlit, pandas, NumPy, Plotly, yfinance, psycopg2, and any related runtime packages.
2. Move database credentials to environment variables or a secrets manager and remove credentials from source control.
3. Fix `check_data.py` to count `sp.id`.
4. Pass the sidebar date range consistently to Risk, Correlation, and Smart Insights.
5. Normalize comparison series explicitly and label the chart according to the actual transformation.
6. Replace repeated per-ticker database connections with a managed connection/pool and close connections using context managers.
7. Add tests for indicator values, threshold boundaries, empty data, date filters, and forecast behavior.
8. Add structured error handling for PostgreSQL failures, Yahoo Finance failures, and partial ticker updates.
9. Separate dashboard rendering from business logic to make the Streamlit UI easier to test.
10. Add a data-quality report for missing trading days, null OHLCV values, duplicate constraints, and last successful synchronization.

## Project status

The Streamlit server has been launched successfully from the supplied virtual environment and is listening on port `8501`. The application source modules are the supported runtime path; the editor scratch file has a known indentation error and should be excluded from project validation or removed when no longer needed.
