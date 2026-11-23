"""Create a compact market overview for the latest recorded dataset date."""
import argparse
import json
from decimal import Decimal
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]


def export(database, output):
    database, output = Path(database), Path(output)
    if output.exists():
        raise FileExistsError('Overview already exists; preserve the previous export.')
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as db:
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
            if opening is None or close is None or Decimal(opening) <= 0 or Decimal(close) <= 0:
                continue
            change = (Decimal(close) / Decimal(opening) - 1) * 100
            data.append({'stock_id': stock_id, 'ticker': ticker, 'open': opening,
                         'close': close, 'change_pct': str(change)})
        if not data:
            raise ValueError('No eligible prices for the latest market date')
        result = {'date': day, 'total_symbols': total, 'observed_symbols': len(rows),
                  'eligible_symbols': len(data),
                  'method': '(close / open - 1) * 100; same session; positive valid prices only',
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
