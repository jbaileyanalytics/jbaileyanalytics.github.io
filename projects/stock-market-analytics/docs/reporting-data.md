# Shared reporting data

The export takes one read-only SQLite transaction and uses the same analytics functions for both sets of output. It writes into a new directory; an existing reporting directory is never replaced. The default location is `results/reporting-v1/`, which is ignored by Git and is not a public website or hosted report.

## Analytical CSV files

| File | Grain | Main fields |
| --- | --- | --- |
| `stocks.csv` | One stock | `stock_id`, ticker, latest observation and OHLC, previous close, 52-week range and coverage flags. |
| `daily_prices.csv` | One stock and observed date | `stock_id`, date, open, high, low, close. |
| `period_prices.csv` | One stock, frequency and calendar period | `stock_id`, weekly/monthly boundaries, first/last observation, OHLC, count and latest-period flag. |
| `trailing_returns.csv` | One stock and trailing period | `stock_id`, period, cumulative price-return percent, baseline date and unavailable reason. |
| `annual_returns.csv` | One stock and year with a valid close | `stock_id`, year, endpoint, partial-year flag, price-return percent, baseline date and unavailable reason. |
| `quality_issues.csv` | One stock, observation and flagged field/rule | `stock_id`, date, field, rule, original value, source filename and line. |

Use `stocks[stock_id]` as the one-side key when modeling relationships. Prices and returns are decimal strings in CSV and must be explicitly typed on import. Return values are **percentage points**: for example, `20` means 20%, not 2,000%. Divide by 100 before applying Power BI's percentage format. A blank represents an unavailable measure, not zero. A calendar table can be created in the report when date filtering is designed; do not assume every observed security traded on every calendar date.

## Website files

`website/stocks.json` is a ticker index with integer IDs and per-stock file paths. Each `website/stocks/<stock_id>.json` contains the same overview and calculated returns, a summary of quality issues by field and rule, compact daily rows with `daily_columns` defining their order, and weekly/monthly summaries. The static website loads the selected stock's file. Decimal values are strings, dates are ISO strings, and unavailable values are JSON null. The website retains the as-of date and coverage/quality warnings.

## Provenance and limitations

`manifest.json` includes counts, creation time, and a SHA-256 digest of the ordered source filename/hash/row-count inventory from SQLite. This identifies the audited source inventory, not a verified Kaggle version or independent confirmation of accuracy. Each stock has its own latest observation date; don't label them all as having the same trading date. The underlying currency, adjustments for corporate actions, dividends and license remain unverified. These are price returns and cannot be represented as total returns.

Exporting does not publish data. The local website can use `results/reporting-v1`; a separate export will not update it automatically. Before sharing source-derived files, verify the Kaggle dataset's license and redistribution terms. See [business metrics](business-metrics.md) for the seven-day baseline policy, partial periods, missing data and calculation boundaries.

## Generate a separate export

From the portfolio root: `python projects/stock-market-analytics/pipelines/export_reporting.py`. To create another version without replacing the original, specify `--output` followed by a new directory path. The exporter checks daily row counts and return coverage before writing the folder. A separate full-rebuild refresh is prepared; incremental updates and correction history remain future work.
