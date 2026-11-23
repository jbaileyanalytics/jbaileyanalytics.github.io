# Historical price analytics: implemented definitions

These calculations use the local snapshot and the per-field quality rules in the daily-price mapping. They are price-only measures. Currency, split treatment and dividend adjustments remain unverified; results are not verified total returns or investment advice. The Python analytics layer supplies reporting exports used by the locally previewed static website. The public deployment and scheduled refresh have not yet been verified on GitHub.

## Closing price and returns

- **Latest close:** close on the stock's most recent recorded date. If the close is unavailable, report it as unavailable rather than silently moving to an earlier date. The previous valid close is separately labeled with its date.
- **Cumulative price return:** `(ending close / baseline close - 1) × 100`. Both prices must be positive and valid. The output includes the baseline date and a reason when unavailable. Multi-year values are cumulative, not annualized.
- **YTD:** baseline is the last valid close on or before December 31 of the prior calendar year.
- **Trailing periods:** 1 month, 3 months, 1 year, 3 years, 5 years, and 10 years use the last valid close on or before the corresponding calendar boundary. Month-end and leap-day boundaries clamp to the last valid day of the target month.
- **Stale baseline policy:** if the baseline is more than seven calendar days before its boundary, the result is unavailable. Seven days is an explicit provisional guardrail, not an exchange calendar or a guarantee of complete data. No observation before the boundary means insufficient history.
- **Annual price return:** compares the last valid close in each calendar year to the last valid close on or before the preceding December 31. A completed year's endpoint must also be within seven calendar days of year end. The dataset's latest year is labeled partial. Years without any valid close have no row.

## 52-week history and range

The window includes observations after `(latest observed date - 364 days)` through the latest observed date, inclusive. The historical line uses valid close values and leaves missing values null. The high is the maximum daily high and the low is the minimum daily low; if any high or low in the window is unavailable, the corresponding range is unavailable. The result reports missing counts and whether the stock's observed history begins inside the window, so a short history is not presented as a complete 52-week history. These checks cannot establish that no trading days are missing.

## Historical OHLC summaries

Daily groups are calendar dates; weekly groups start Monday and end Sunday; monthly groups are calendar months. Each group reports its period boundaries and first and last available observation dates. Open is the first observed row's valid open, and close is the last observed row's valid close. High is the maximum high and low is the minimum low only if every observed row in the group has that field; otherwise the affected aggregate is null. The period-end indicator means the calendar period ends after the stock's latest observation; it does not prove completeness or incompleteness against a trading calendar. Filtering aggregated periods requires care: this implementation aggregates the rows provided to it, so calculate from complete periods before applying a display filter.

## Examples and operation

From the portfolio root, `python projects/stock-market-analytics/src/analytics.py AAPL` prints a JSON overview. Add `--frequency weekly`, `monthly`, or `daily` for historical OHLC summaries. Output uses decimal strings and ISO dates to avoid hidden floating-point rounding; a presentation layer must format them. Missing values are JSON nulls. The command is read-only and requires the local SQLite product.

In the November 16, 2026 snapshot, the calculation returns an AAPL close of 352.78 and a YTD price change of approximately 29.89%, with December 31, 2025 as the baseline. ARXS has insufficient history for YTD and 1-, 3-, and 5-year returns, and its available 52-week window is marked as starting within the window. These are calculations from the supplied historical source, not independently verified market figures.
