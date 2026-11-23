-- SQLite source-coverage baseline; a later Parquet comparison must retain these semantics.
SELECT s.ticker, COUNT(*) AS observed_rows,
       MIN(d.calendar_date) AS first_date, MAX(d.calendar_date) AS last_date,
       SUM(CASE WHEN p.close IS NULL THEN 1 ELSE 0 END) AS missing_close_rows
FROM fact_daily_price p
JOIN dim_stock s ON s.stock_id = p.stock_id
JOIN dim_date d ON d.date_id = p.date_id
GROUP BY s.ticker
ORDER BY observed_rows DESC, s.ticker;
