"""Create a compact market overview for the latest recorded dataset date."""
import argparse
from contextlib import closing
import json
from decimal import Decimal
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]


def export(database, output):
    database, output = Path(database), Path(output)
    if output.exists():
        raise FileExistsError('Overview already exists; preserve the previous export.')
    with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.execute('BEGIN')
        day = db.execute('SELECT MAX(calendar_date) FROM dim_date').fetchone()[0]
        if not day:
            raise ValueError('No market dates found')
        rows = db.execute('''SELECT s.stock_id,s.ticker,p.open,p.close FROM fact_daily_price p
           JOIN dim_stock s ON s.stock_id=p.stock_id JOIN dim_date d ON d.date_id=p.date_id
           WHERE d.calendar_date=? ORDER BY s.ticker''', (day,)).fetchall()
        total = db.execute('SELECT COUNT(*) FROM dim_stock').fetchone()[0]
        data = []
        for stock_id, ticker, opening, close in rows:
            previous = db.execute('''SELECT p.close,d.calendar_date FROM fact_daily_price p
                JOIN dim_date d ON d.date_id=p.date_id
                WHERE p.stock_id=? AND d.calendar_date<? AND p.close IS NOT NULL
                ORDER BY d.calendar_date DESC LIMIT 1''', (stock_id, day)).fetchone()
            previous_close, previous_date = previous if previous else (None, None)
            def change_from(baseline):
                if baseline is None or close is None or Decimal(baseline) <= 0 or Decimal(close) <= 0:
                    return None
                return str((Decimal(close) / Decimal(baseline) - 1) * 100)
            session_change = change_from(opening)
            previous_change = change_from(previous_close)
            data.append({'stock_id': stock_id, 'ticker': ticker, 'open': opening,
                         'close': close, 'previous_close': previous_close, 'previous_close_date': previous_date,
                         'change_pct': session_change, 'previous_close_change_pct': previous_change})
        eligible = sum(item['change_pct'] is not None for item in data)
        previous_eligible = sum(item['previous_close_change_pct'] is not None for item in data)
        if not eligible:
            raise ValueError('No eligible prices for the latest market date')
        result = {'date': day, 'total_symbols': total, 'observed_symbols': len(rows),
                  'eligible_symbols': eligible, 'previous_close_eligible_symbols': previous_eligible,
                  'method': 'Open-to-close: (close / open - 1) * 100; previous-close-to-close: (close / previous valid close - 1) * 100; positive valid prices only',
                  'stocks': data}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, separators=(',', ':'))
        stream.write('\n')
    return {key: value for key, value in result.items() if key != 'stocks'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT / 'results/market-data.sqlite')
    parser.add_argument('--output', type=Path, default=ROOT / 'results/reporting-v1/website/market-overview.json')
    args = parser.parse_args()
    print(json.dumps(export(args.database, args.output), indent=2))
