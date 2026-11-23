"""Read-only historical price analytics for the local stock data product.

Returns are price returns only; the source's adjustment and currency are unverified.
"""
import argparse
import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path
import sqlite3

DATABASE = Path(__file__).resolve().parents[1] / 'results' / 'market-data.sqlite'
MAX_BASELINE_AGE_DAYS = 7


def shift_months(day, months):
    index = day.year * 12 + day.month - 1 + months
    year, month0 = divmod(index, 12)
    return date(year, month0 + 1, min(day.day, calendar.monthrange(year, month0 + 1)[1]))


def read_prices(connection, ticker):
    rows = connection.execute('''SELECT d.calendar_date, f.open, f.high, f.low, f.close
        FROM fact_daily_price f JOIN dim_stock s ON s.stock_id=f.stock_id
        JOIN dim_date d ON d.date_id=f.date_id WHERE s.ticker=? ORDER BY d.calendar_date''',
        (ticker.strip().upper(),)).fetchall()
    if not rows:
        raise ValueError(f'No observations for ticker: {ticker}')
    return [{'date': date.fromisoformat(r[0]), **{name: Decimal(value) if value is not None else None
             for name, value in zip(('open','high','low','close'), r[1:])}} for r in rows]


def price_return(rows, boundary, end):
    """Return a cumulative price change using the latest close on/before boundary.

    Reject a baseline older than seven calendar days; this is a project policy,
    not proof that the source contains every expected trading session.
    """
    if end['close'] is None:
        return {'percent': None, 'reason': 'ending close unavailable', 'baseline_date': None}
    candidates = [r for r in rows if r['date'] <= boundary and r['close'] is not None]
    if not candidates:
        return {'percent': None, 'reason': 'insufficient history', 'baseline_date': None}
    baseline = candidates[-1]
    if (boundary - baseline['date']).days > MAX_BASELINE_AGE_DAYS:
        return {'percent': None, 'reason': 'baseline older than seven calendar days',
                'baseline_date': baseline['date'].isoformat()}
    return {'percent': str((end['close'] / baseline['close'] - 1) * 100), 'reason': None,
            'baseline_date': baseline['date'].isoformat()}


def period_prices(rows, frequency):
    if frequency not in ('daily', 'weekly', 'monthly'):
        raise ValueError('frequency must be daily, weekly, or monthly')
    groups = defaultdict(list)
    for row in rows:
        day = row['date']
        key = day if frequency == 'daily' else day - timedelta(days=day.weekday()) if frequency == 'weekly' else day.replace(day=1)
        groups[key].append(row)
    result = []
    for start, group in sorted(groups.items()):
        # Missing values invalidate aggregate extremes rather than silently hiding gaps.
        highs = [r['high'] for r in group]
        lows = [r['low'] for r in group]
        end = start if frequency == 'daily' else start + timedelta(days=6) if frequency == 'weekly' else shift_months(start, 1) - timedelta(days=1)
        result.append({'period_start': start.isoformat(), 'period_end': end.isoformat(),
                       'first_observation': group[0]['date'].isoformat(), 'last_observation': group[-1]['date'].isoformat(),
                       'open': str(group[0]['open']) if group[0]['open'] is not None else None,
                       'high': str(max(highs)) if all(v is not None for v in highs) else None,
                       'low': str(min(lows)) if all(v is not None for v in lows) else None,
                       'close': str(group[-1]['close']) if group[-1]['close'] is not None else None,
                       'observations': len(group),
                       'period_ends_after_latest_observation': end > rows[-1]['date']})
    return result


def analyze(rows, ticker):
    latest = rows[-1]
    as_of = latest['date']
    previous = next((r for r in reversed(rows[:-1]) if r['close'] is not None), None)
    periods = {'YTD': date(as_of.year - 1, 12, 31), '1 month': shift_months(as_of, -1),
               '3 months': shift_months(as_of, -3), '1 year': shift_months(as_of, -12),
               '3 years': shift_months(as_of, -36), '5 years': shift_months(as_of, -60),
               '10 years': shift_months(as_of, -120)}
    start = as_of - timedelta(days=364)
    window = [r for r in rows if start < r['date'] <= as_of]
    highs = [r['high'] for r in window]
    lows = [r['low'] for r in window]
    annual = []
    for year in range(rows[0]['date'].year, as_of.year + 1):
        year_rows = [r for r in rows if r['date'].year == year and r['close'] is not None]
        if year_rows:
            endpoint = year_rows[-1]
            result = price_return(rows, date(year - 1, 12, 31), endpoint)
            if year < as_of.year and (date(year, 12, 31) - endpoint['date']).days > MAX_BASELINE_AGE_DAYS:
                result.update(percent=None, reason='year-end close older than seven calendar days')
            annual.append({'year': year, 'end_date': endpoint['date'].isoformat(), 'partial': year == as_of.year, **result})
    return {'ticker': ticker.strip().upper(), 'latest_observation_date': as_of.isoformat(),
            'latest_close': str(latest['close']) if latest['close'] is not None else None,
            'previous_close': str(previous['close']) if previous else None,
            'previous_close_date': previous['date'].isoformat() if previous else None,
            'latest_open': str(latest['open']) if latest['open'] is not None else None,
            'latest_high': str(latest['high']) if latest['high'] is not None else None,
            'latest_low': str(latest['low']) if latest['low'] is not None else None,
            'returns': {name: price_return(rows, boundary, latest) for name, boundary in periods.items()},
            'annual_price_returns': annual,
            'range_52_weeks': {'start_exclusive': start.isoformat(), 'end_inclusive': as_of.isoformat(),
                 'high': str(max(highs)) if highs and all(v is not None for v in highs) else None,
                 'low': str(min(lows)) if lows and all(v is not None for v in lows) else None,
                 'observations': len(window), 'starts_within_window': rows[0]['date'] > start,
                 'missing_highs': sum(v is None for v in highs), 'missing_lows': sum(v is None for v in lows)},
            'history_52_weeks': [{'date': r['date'].isoformat(), 'close': str(r['close']) if r['close'] is not None else None} for r in window],
            'disclaimer': 'Historical price returns; currency, splits, and dividend adjustments are unverified.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ticker')
    parser.add_argument('--database', type=Path, default=DATABASE)
    parser.add_argument('--frequency', choices=['daily', 'weekly', 'monthly'])
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error('Database not found. Build the local snapshot first.')
    with sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True) as connection:
        rows = read_prices(connection, args.ticker)
    data = period_prices(rows, args.frequency) if args.frequency else analyze(rows, args.ticker)
    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()
