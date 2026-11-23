# Mapping: daily stock prices

Grain: one current accepted observation for one ticker on one source date. Primary key: `daily_price_id`; foreign keys: `stock_id`, `date_id`.

| Target | Source | Rule |
| --- | --- | --- |
| daily_price_id | ticker and date | Assign an auto-incrementing integer on initial build. The current builder refuses to overwrite the database; future incremental ID reuse is not implemented. |
| stock_id | `ticker` | Resolve the observed stock reference; flag missing or inconsistent labels. |
| date_id | `date` | Parse ISO date and resolve date reference. |
| open, high, low, close | corresponding source fields | Parse as positive finite decimals, stored as text to retain decimal precision. Invalid values become null and are captured in the audit table. An open or close outside a valid high/low range becomes null; high and low become null if low exceeds high. Other valid fields are retained. |

The separate pipeline audit tables link observations to a source filename, hash, and CSV line and record field-specific issues and original values. Duplicate stock/date observations or invalid identities and dates stop the build; they do not publish a partial database. These initial field-level rules are explicit assumptions, not independent verification of valid-looking fields. If high or low is unavailable, an open or close cannot be checked against that day's range. Historical revisions and incremental updates are not implemented.
