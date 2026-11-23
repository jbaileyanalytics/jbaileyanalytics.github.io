# Large-file batch: baseline and next steps

The existing local dataset contains 499 stock references and approximately 2.74 million historical daily observations. It is a snapshot, not a live feed. Preserve the existing SQLite database and its assigned IDs; the initial builder intentionally refuses to overwrite it.

## Verified comparison baseline

`sql/source_coverage_baseline.sql` calculates observed rows, first and last available dates, and null closing-price counts by symbol from the existing SQLite model. It does not infer missing trading days, source licensing, price adjustment, currency, or investment returns. Use it to reconcile any later Parquet/DuckDB export.

## Implemented first batch export

`pipelines/export_parquet.py` reads the existing SQLite database in read-only mode and writes a separate Zstandard-compressed Parquet file in bounded batches. It keeps assigned IDs and preserves OHLC values as decimal strings instead of converting them to floating point. DuckDB compares total rows, unique daily-price IDs, and per-ticker row counts, date boundaries and null close counts against SQLite. This verifies those checks, not every value or trading-day completeness.

A local Docker run reconciled **2,740,359 rows across 499 symbols**, with **3 null closing prices** and **0 duplicate daily-price IDs**. Results are stored under ignored `results/parquet-batch-v1/`. The source database and dashboard were not changed.

## Row-level audit and query measurements

A subsequent local audit compared every exported row with the SQLite snapshot, in ID order, including IDs, symbol, date and all four original decimal strings. All **2,740,359 rows matched**. It also checked that each price row has a source-file lineage record and that the sum of recorded source rows matches the price count. Lineage remains in SQLite; it is not included in the Parquet export, and these checks do not independently validate the source's accuracy.

Nulls in the audited snapshot: **102,326 open**, **0 high**, **0 low**, and **3 close**. Null values reflect the existing quality rules, not proof of what the market price was.

The following measurements are illustrative, not a general database benchmark. They ran in a local Linux Docker container against the same mounted snapshot, using SQLite 3.46.1 and DuckDB 1.3.2. Each query returned daily OHLC rows for one symbol and date range, with equivalent results fetched into memory. Values are the median of three sequential runs in one process; SQLite ran before DuckDB, caches were not controlled, and the workload and storage layout differ. Machine resources and cold-cache behavior were not controlled.

| Symbol | Dates | Rows | SQLite median | DuckDB / Parquet median |
| --- | --- | ---: | ---: | ---: |
| AAPL | 2021–2025 | 1,255 | 2.582 ms | 36.226 ms |
| MSFT | 2000–2025 | 6,539 | 9.963 ms | 38.467 ms |
| ABNB | 2024–2025 | 502 | 0.734 ms | 46.805 ms |

In these particular tests, SQLite was faster. SQLite has indexed relational tables; the Parquet export is a single file in daily-price-ID order. This does not establish how either approach performs for broad scans, other hardware, partitioned files, cold caches or different workloads.

To rerun the audit with a **new** output filename:

```powershell
docker compose -f projects/stock-market-analytics/compose.batch.yaml run --build --rm --entrypoint python batch /app/audit_batch.py --database /input/market-data.sqlite --parquet /output/parquet-batch-v1/daily_prices.parquet --output /output/parquet-batch-v1/value-audit-next.json
```

The audit refuses to overwrite its results. It is read-only for the source database and Parquet file.

From the repository root with Docker Desktop running:

```powershell
docker compose -f projects/stock-market-analytics/compose.batch.yaml run --build --rm batch
```

The command refuses to overwrite its output directory. Preserve or choose a new output path for a future run. A missing `reconciliation.json` means the export was not successfully reconciled.

## Remaining work

1. Design incremental and corrected-record handling after examining source-version behavior. A Kaggle download and full local rebuild have been tested; the prepared scheduled workflow has not yet been verified on GitHub and does not implement incremental updates.
2. Independently verify source adjustment methodology before presenting price changes as split-safe, and validate the website and report against the data.
3. If analytical scan performance is a goal, define broader workloads and compare deliberately organized Parquet files under controlled conditions.
