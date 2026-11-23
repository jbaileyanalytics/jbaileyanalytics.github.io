# Source assessment: historical stock prices

## Observed local snapshot

The [read-only source assessment notebook](../notebooks/source_assessment.ipynb) runs the project's profiler against a local snapshot and displays aggregate results without saving a profile or exposing raw records. Results may differ for a newer snapshot.

The supplied folder contains 499 CSV files, one named for each ticker, totaling 118,730,017 bytes. The profile scanned **2,740,359 records**. All files have the same six-column header: `ticker`, `date`, `open`, `high`, `low`, and `close`. The earliest observed date is January 2, 1962; the latest is November 16, 2026. Those endpoints describe the combined dataset, not every stock.

The latest date appears in 498 of 499 files. `NWE.csv` ends November 13, 2026. That is a coverage observation, not proof that a trading-day record is missing: the reason has not been investigated. The generated full profile, kept locally and excluded from Git, records each file's row count, first and last date, and SHA-256 hash. It can be regenerated using the profiler in the project README.

There are 439 files with a first observation at least five calendar years before the combined latest date. That does not prove continuous coverage or availability of an eligible five-year return baseline. Company histories have different start dates, and a security's observed ticker is not necessarily a permanent identifier.

## Quality findings

The profiler detected **102,324 nonpositive price cells**, all in `open`, across 78 files. It also identified **102,329 rows** where open or close falls outside the day's low/high range or low exceeds high. These categories overlap heavily; they are not additive. Most flagged rows are historical, with the latest flagged year in this snapshot 2011. A sample is `ADBE.csv` line 2, where open is `0.0` while low is `0.21`, high is `0.22`, and close is `0.21`.

The profiler found no invalid dates, within-file duplicate ticker/date pairs, ticker/filename mismatches, non-finite or unparseable prices, or out-of-order dates. These are checks of this snapshot, not proof of accuracy or completeness. Duplicate detection is per file; a cross-file conflict check will be required when records are combined. The script stops processing rows in a file if required columns are missing and reports the file as unprofiled.

The zero opens should not be interpreted as real trading prices or replaced with guessed values. The source may contain usable closes on some flagged rows, but we have not verified the independent accuracy of any field. The initial local build uses field-level nulls and records the original invalid values and rules in a separate audit table. This is a documented initial policy that directly affects weekly/monthly OHLC and price-return coverage; downstream metrics still need explicit eligibility rules.

## Information not established by the files

- License, upstream price provider, universe selection, and update/version policy for the [Kaggle dataset](https://www.kaggle.com/datasets/svaningelgem/nasdaq-daily-stock-prices).
- Whether prices are adjusted for splits, dividends, or other corporate actions; the level of historical rounding; and the currency of each security.
- A full exchange calendar, listing/delisting history, symbol changes, or a stable external security identifier.
- Trading volume, company fundamentals, distributions, or a verified benchmark. These cannot be inferred from the six fields.

Accordingly, we cannot yet label returns as total returns, establish split-safe comparisons, represent the data as live, or assume the 499 stocks are a point-in-time historical Nasdaq universe. Obtain and document authoritative dataset metadata before choosing return semantics or distributing source data.

## Profiling limits

Checks are lexical, date, value, and within-file checks. They do not compare values to an independent market-data provider, verify business calendars, detect all missing days, or establish corporate-action adjustments. Hashes detect file changes but do not explain what changed. The profiler emits at most ten examples per issue type; aggregate counts include all observed occurrences.
