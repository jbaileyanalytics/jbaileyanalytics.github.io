"""Export the existing SQLite snapshot to Parquet and reconcile with DuckDB.

This is a separate batch output. It never updates the SQLite source.
"""
import argparse
import json
from pathlib import Path
import sqlite3

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT = Path(__file__).resolve().parents[1]
COLUMNS = ['daily_price_id', 'stock_id', 'date_id', 'ticker', 'calendar_date', 'open', 'high', 'low', 'close']
QUERY = '''SELECT p.daily_price_id, p.stock_id, p.date_id, s.ticker, d.calendar_date,
                  p.open, p.high, p.low, p.close
           FROM fact_daily_price p JOIN dim_stock s ON s.stock_id=p.stock_id
           JOIN dim_date d ON d.date_id=p.date_id ORDER BY p.daily_price_id'''
BASELINE = '''SELECT s.ticker, COUNT(*), MIN(d.calendar_date), MAX(d.calendar_date),
                     SUM(CASE WHEN p.close IS NULL THEN 1 ELSE 0 END)
              FROM fact_daily_price p JOIN dim_stock s ON s.stock_id=p.stock_id
              JOIN dim_date d ON d.date_id=p.date_id GROUP BY s.ticker ORDER BY s.ticker'''
SCHEMA = pa.schema([(name, pa.int64() if name.endswith('_id') else pa.string()) for name in COLUMNS])

def export(database, destination, batch_size=50000):
    database, destination = Path(database).resolve(), Path(destination)
    if not database.is_file():
        raise FileNotFoundError('SQLite source does not exist')
    if batch_size < 1:
        raise ValueError('batch size must be positive')
    destination.mkdir(parents=True, exist_ok=False)
    parquet = destination / 'daily_prices.parquet'
    db = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    try:
        expected_rows = db.execute('SELECT COUNT(*) FROM fact_daily_price').fetchone()[0]
        baseline = db.execute(BASELINE).fetchall()
        cursor = db.execute(QUERY)
        written = 0
        with pq.ParquetWriter(parquet, SCHEMA, compression='zstd') as writer:
            while rows := cursor.fetchmany(batch_size):
                arrays = [pa.array([row[i] for row in rows], type=SCHEMA.field(i).type) for i in range(len(COLUMNS))]
                writer.write_table(pa.Table.from_arrays(arrays, schema=SCHEMA))
                written += len(rows)
        connection = duckdb.connect(':memory:')
        try:
            escaped_path = str(parquet).replace("'", "''")
            connection.execute(f"CREATE VIEW prices AS SELECT * FROM read_parquet('{escaped_path}')")
            actual = connection.execute('''SELECT ticker, count(*), min(calendar_date), max(calendar_date),
                       count(*) FILTER (WHERE close IS NULL) FROM prices GROUP BY ticker ORDER BY ticker''').fetchall()
            actual_rows = connection.execute('SELECT count(*) FROM prices').fetchone()[0]
            duplicates = connection.execute('SELECT count(*)-count(DISTINCT daily_price_id) FROM prices').fetchone()[0]
        finally:
            connection.close()
        if written != expected_rows or actual_rows != expected_rows or baseline != actual or duplicates:
            raise ValueError('Reconciliation failed: inspect the incomplete output before retrying in a new directory')
        summary = {'status':'reconciled', 'daily_rows':actual_rows, 'tickers':len(actual),
                   'missing_close_rows':sum(row[4] for row in actual), 'duplicate_daily_price_ids':duplicates,
                   'prices_type':'decimal strings; no float conversion', 'source':'existing SQLite snapshot',
                   'checks':['row count', 'unique daily_price_id', 'per-ticker count, date bounds, null closes']}
        (destination/'reconciliation.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        return summary
    finally:
        db.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=PROJECT/'results/market-data.sqlite')
    parser.add_argument('--output', type=Path, default=PROJECT/'results/parquet-batch-v1')
    args = parser.parse_args()
    print(json.dumps(export(args.database,args.output),indent=2))
