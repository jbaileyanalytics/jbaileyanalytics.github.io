# Historical Stock Market Analytics

This project turns historical stock-price files into a documented daily market-data product and an interactive website. The reviewed Kaggle snapshot contained 499 files; it is not a live market feed. Visitors can explore individual stocks, historical prices, and carefully defined price-performance measures.

## Current status

The original local SQLite product contains 499 stock references, 2,740,359 daily observations, source lineage, and 102,329 field-level quality findings. A separate batch export produced Parquet and reconciled its row counts, IDs, per-symbol coverage and missing closes using DuckDB. A shared analytics module calculates closing-price changes, 52-week history and OHLC summaries. The interactive website uses the shared reporting export and has been previewed locally. A real Kaggle download and isolated full rebuild have been tested. Incremental refresh is not implemented, and the prepared GitHub Pages deployment has not yet been verified.

- [Source assessment](docs/source-assessment.md); the detailed generated profile and file manifest are kept locally and excluded from Git.
- [Read-only source assessment notebook](notebooks/source_assessment.ipynb)
- [Data model](docs/data-model.md) and [source-to-target mappings](docs/mappings/)
- [Implemented analytics definitions](docs/business-metrics.md)
- [Reporting data and website export](docs/reporting-data.md)
- [Architecture and next steps](docs/architecture.md)
- [Project structure](docs/project-structure.md)

See the [large-file batch implementation and next steps](docs/batch-next-steps.md) and [SQLite source-coverage baseline](sql/source_coverage_baseline.sql).

## Reproduce the profile

Obtain the dataset separately and place its CSV files in `datasets/Stocks - Nasdaq/` (the dataset folder is not in Git). From the portfolio root, using Python 3.10 or later:

```powershell
python projects/stock-market-analytics/pipelines/profile_sources.py
python -m unittest discover -s projects/stock-market-analytics/tests -v
```

The profiler reads `datasets/Stocks - Nasdaq/` without modifying its files and replaces the Git-ignored `docs/source-profile.json` with a new assessment. Compare or preserve the existing profile first if you need the previous snapshot's manifest. The profiling script uses the Python standard library. The full test suite includes optional DuckDB and PyArrow tests, which are skipped if those packages are unavailable.

## Local data product

The initial build is `results/market-data.sqlite`. Keep and back up this database: it contains the assigned surrogate IDs. The initial builder is `python projects/stock-market-analytics/pipelines/build_local.py`; it refuses to overwrite an existing database because incremental loads and correction handling are not implemented. To build a separate copy for testing, specify `--output` with a new file path. The source files remain unchanged. Decimal prices are stored as text in SQLite to preserve precision; a reporting layer must cast them deliberately.

Invalid field values are set to null in the data product and preserved with their specific rule in the audit tables. This is a documented first-pass policy, not independent verification of the other price fields. Review the [daily price mapping](docs/mappings/fact_daily_price.md) before using them.

To inspect the analytics output for a ticker, run `python projects/stock-market-analytics/src/analytics.py AAPL`. Add `--frequency weekly` for period prices. Run `python projects/stock-market-analytics/pipelines/export_reporting.py` to create a shared set of reporting files in a new `results/reporting-v1/` directory. These local files are not published.

## Local website

The website's stock data is generated locally and is not included in a fresh checkout. First build the SQLite data product and run `export_reporting.py` and `export_market_overview.py` as described above and below, or create a separate refresh candidate. With Node.js available in Windows, double-click `website/run-dashboard.cmd`. It opens the browser after starting the server and keeps a command window open. If the reviewed November 18 candidate is present, it serves that candidate at `http://127.0.0.1:8767/`; otherwise it serves the local reporting export at `http://127.0.0.1:8765/website/`. Press Ctrl+C in the command window to stop the server. Opening the HTML file directly will not load the stock files because browsers restrict local-file requests. If Node.js is unavailable or the port is already in use, the window displays an error.

The market overview uses one equal-sized symbol heatmap with a comparison toggle. **Previous close → close** shows `(close / previous valid recorded close - 1) × 100`; **Open → close** shows `(close / open - 1) × 100` for the latest date observed in the dataset. The gainers and losers follow the selected comparison. Values require positive, valid prices; unavailable comparisons are shown as N/A and excluded from the rankings. A previous recorded close may be older than the previous trading day. Symbols with no row on the latest dataset date are not shown. The heatmap is not market-cap weighted or organized by sector; the dataset has neither field. Select a symbol to explore its daily close chart across 5 observations, 1 month, 6 months, year-to-date, 1 year, 5 years, or all available history. Hover over the chart or use the arrow keys to inspect individual observations; the source has no intraday prices or volume.

After creating the reporting export, generate the market overview from the same SQLite snapshot with `python projects/stock-market-analytics/pipelines/export_market_overview.py`. It refuses to overwrite an existing overview. The overview and individual-stock export must be regenerated from the same snapshot; the local website does not update automatically when Kaggle changes. In the reviewed snapshot, 498 of 499 symbols had valid same-day prices on November 16, 2026. No historical return is presented as verified total return.

### Static hosting preview

Run `python projects/stock-market-analytics/pipelines/prepare_static_site.py` from the repository root after generating both exports. The command creates `results/public-preview/`, a self-contained static copy with the historical data under `data/`. It will not overwrite an existing preview. Serve that directory with an HTTP server to test it; opening the HTML directly is not sufficient. This generated directory is ignored by Git and is not itself a deployment.

The reviewed preview contains 499 stock files and approximately 315 MB of JSON. The prepared GitHub Pages workflow is designed to rebuild the stock snapshot daily and carry forward the published NFL snapshots, with NFL refreshes on Tuesday and Thursday. It is designed to publish both dashboards as one artifact without committing regenerated histories to Git. The workflow has not yet been deployed or verified on GitHub; dataset redistribution terms remain unclear. See the NFL project's README for its refresh safeguards.

## Data provenance

The source is [NASDAQ Daily Stock Prices on Kaggle](https://www.kaggle.com/datasets/svaningelgem/nasdaq-daily-stock-prices), published by Steven Van Ingelgem (`svaningelgem`). Credit is due to the original data owners as well; the dataset description does not identify the upstream websites or owners. The dataset is described as updated daily. Kaggle lists its license as “Data files © Original Authors”; the underlying redistribution terms remain unclear. Price adjustment treatment, currency, stock universe selection, and historical correction policy still need verification. Do not claim a live feed or total return without resolving the relevant questions.

## Optional: download an updated snapshot

Install `kagglehub` in a Python environment and, from the portfolio root, run `python projects/stock-market-analytics/pipelines/download_kaggle.py`. The command uses KaggleHub's cache and writes a separate inventory of CSV filenames and hashes to `results/acquisitions/`; it does not overwrite the existing local dataset or load data into the model. Authentication or consent may be required in other environments; keep any credentials outside the repository. On November 19, 2026, a real download of Kaggle version 841 succeeded without a credential prompt and contained 499 CSV files.

For a refresh rehearsal, `pipelines/prepare_refresh.py --source <csv-directory> --output <new-output-directory>` rebuilds the database, reporting exports, and static preview in a separate new directory. It does not download, schedule, or deploy. It is a full rebuild, not an incremental load: generated database IDs may change between runs and must not be treated as stable across snapshots. A successful build alone is not sufficient for publication; refresh safeguards, public-sharing terms, and GitHub Pages deployment still need verification.

### November 19 local refresh comparison

Kaggle version 841 produced a separate candidate with 499 stocks and 2,741,355 daily observations, with a market overview through November 18, 2026. Compared with the original November 16 snapshot, all 2,740,359 matching ticker/date records retained the same validated numerical OHLC values, 996 records were added, and none were removed. These checks compare the stored, validated fields, not the original raw strings or source accuracy. Quality issue counts remained 102,329; AAPL, MSFT and AMZN's latest website OHLC values matched their candidate database rows. The existing dashboard and database were not replaced.

`pipelines/compare_snapshots.py --previous <old-sqlite> --candidate <new-sqlite> --output <new-json>` performs a read-only comparison by ticker and date, independently of assigned surrogate IDs. It reports added, removed, changed and unchanged rows, field changes, missing-value transitions and limited key samples. The output is created only if it does not already exist. The comparison is a local manual check and is not yet part of the scheduled GitHub workflow.

The repository also contains `.github/workflows/stock-refresh-check.yml`, a GitHub Actions workflow that builds and deploys the portfolio and refreshed stock dashboard on pushes to `main`, on demand, and daily at 6:00 a.m. Central time. GitHub Pages must be configured to use **GitHub Actions** as its build and deployment source. The Pages artifact contains selected tracked public-facing portfolio assets and the generated stock website and historical data; raw CSVs, local manifests, and the SQLite database are not included. Data inside a published website is publicly downloadable. The download and separate local rebuild succeeded, but the complete workflow has not yet been run on GitHub.

The build checks at least 400 source files, at least 90% eligible symbols, matching counts, and that the market date and symbol count do not regress substantially compared with the published stock overview. These checks are not proof of freshness, stable IDs, data quality, or permission to redistribute. A failed build prevents deployment, leaving the previous Pages deployment in place. GitHub can delay scheduled runs, and the upstream update might not be complete by the run time. On first deployment there is no published stock overview to compare. The homepage resume at `assets/resume/John-Bailey-II-Resume.pdf` must be tracked for the clean runner to include it. Review the artifact allowlist in `pipelines/assemble_portfolio_site.py` and the complete portfolio before the first deployment.
