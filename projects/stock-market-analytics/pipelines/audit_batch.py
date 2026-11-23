"""Verify an existing Parquet export against SQLite and time equivalent reads."""
import argparse
import json
from pathlib import Path
import sqlite3
import statistics
import time

import duckdb
import pyarrow.parquet as pq

from export_parquet import COLUMNS, QUERY

def audit(database, parquet, output):
    database, parquet, output = Path(database).resolve(), Path(parquet).resolve(), Path(output)
    if not database.is_file() or not parquet.is_file():
        raise FileNotFoundError('Both the SQLite snapshot and Parquet export must exist')
    if output.exists():
        raise FileExistsError('Audit output already exists; choose a new file')
    db = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    engine = duckdb.connect(':memory:')
    try:
        db.execute('BEGIN')
        sql_cursor = db.execute(QUERY)
        nulls = dict.fromkeys(('open', 'high', 'low', 'close'), 0)
        compared = 0
        for batch in pq.ParquetFile(parquet).iter_batches(batch_size=50000, columns=COLUMNS):
            columns = [c.to_pylist() for c in batch.columns]
            for actual in zip(*columns):
                expected = sql_cursor.fetchone()
                if expected != actual:
                    raise ValueError(f'Parquet differs from SQLite at ordered row {compared + 1}')
                for field in nulls:
                    nulls[field] += actual[COLUMNS.index(field)] is None
                compared += 1
        if sql_cursor.fetchone() is not None:
            raise ValueError('Parquet has fewer rows than SQLite')
        lineage = db.execute('''SELECT
            (SELECT COUNT(*) FROM fact_daily_price),
            (SELECT COUNT(*) FROM audit_price_lineage),
            (SELECT COUNT(*) FROM fact_daily_price p LEFT JOIN audit_price_lineage l
                ON p.daily_price_id=l.daily_price_id WHERE l.daily_price_id IS NULL),
            (SELECT COUNT(*) FROM audit_price_lineage l LEFT JOIN audit_source_file f
                ON l.source_file_id=f.source_file_id WHERE f.source_file_id IS NULL),
            (SELECT COALESCE(SUM(source_rows),0) FROM audit_source_file)''').fetchone()
        if lineage[0] != compared or lineage[1] != compared or lineage[2] or lineage[3] or lineage[4] != compared:
            raise ValueError('Source lineage coverage does not reconcile')
        sql = '''SELECT d.calendar_date,p.open,p.high,p.low,p.close FROM fact_daily_price p
                 JOIN dim_stock s ON p.stock_id=s.stock_id JOIN dim_date d ON p.date_id=d.date_id
                 WHERE s.ticker=? AND d.calendar_date>=? AND d.calendar_date<=? ORDER BY d.calendar_date'''
        duck = '''SELECT calendar_date,"open",high,low,"close" FROM read_parquet(?)
                  WHERE ticker=? AND calendar_date>=? AND calendar_date<=? ORDER BY calendar_date'''
        timings = []
        for ticker, start, end in [('AAPL','2021-01-01','2025-12-31'), ('MSFT','2000-01-01','2025-12-31'), ('ABNB','2024-01-01','2025-12-31')]:
            samples = {'sqlite':[], 'duckdb_parquet':[]}
            for _ in range(3):
                t = time.perf_counter(); a = db.execute(sql,(ticker,start,end)).fetchall(); samples['sqlite'].append(time.perf_counter()-t)
                t = time.perf_counter(); b = engine.execute(duck,(str(parquet),ticker,start,end)).fetchall(); samples['duckdb_parquet'].append(time.perf_counter()-t)
                if a != b:
                    raise ValueError(f'Benchmark result mismatch for {ticker}')
            timings.append({'ticker':ticker,'start':start,'end':end,'rows':len(a),
                            'sqlite_median_seconds':round(statistics.median(samples['sqlite']),6),
                            'duckdb_parquet_median_seconds':round(statistics.median(samples['duckdb_parquet']),6)})
        result = {'status':'passed','rows_compared':compared,'null_ohlc':nulls,
                  'lineage_rows':lineage[1],'source_rows_recorded':lineage[4],
                  'method':'exact ordered comparison of IDs, ticker, date, and all four price strings; source-file lineage coverage',
                  'benchmark':{'method':'3 sequential warm-process runs per query; includes result fetch; SQLite then DuckDB; no cache control',
                               'sqlite_version':sqlite3.sqlite_version,'duckdb_version':duckdb.__version__,'queries':timings}}
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('x',encoding='utf-8') as f:
            json.dump(result,f,indent=2); f.write('\n')
        return result
    finally:
        engine.close(); db.close()

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--parquet',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(audit(args.database,args.parquet,args.output),indent=2))
