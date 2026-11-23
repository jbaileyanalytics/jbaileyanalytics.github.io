"""Profile the local stock CSV snapshot without modifying the source files.

Run from the repository root: python projects/stock-market-analytics/pipelines/profile_sources.py
"""
from collections import Counter
import csv
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[1]
SOURCE = REPO / 'datasets' / 'Stocks - Nasdaq'
OUTPUT = PROJECT / 'docs' / 'source-profile.json'
EXPECTED = ['ticker', 'date', 'open', 'high', 'low', 'close']
PRICE_FIELDS = EXPECTED[2:]


def profile(source=SOURCE):
    paths = sorted(source.glob('*.csv'))
    if not paths:
        raise ValueError(f'No CSV files found in {source}')
    counts, examples, headers = Counter(), {}, Counter()
    nonpositive_by_field, range_by_year = Counter(), Counter()
    affected_files = set()
    manifest = []
    first_date = last_date = None
    starts, ends = [], []

    def flag(name, file_name, row_number, detail):
        counts[name] += 1
        if len(examples.setdefault(name, [])) < 10:
            examples[name].append({'file': file_name, 'line': row_number, 'detail': detail})

    for path in paths:
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        file_rows = 0
        file_first = file_last = None
        seen = set()
        previous_date = None
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            columns = reader.fieldnames or []
            headers[tuple(columns)] += 1
            if columns != EXPECTED:
                flag('unexpected_header', path.name, 1, columns)
            if not set(EXPECTED).issubset(columns):
                manifest.append({'file': path.name, 'sha256': digest.hexdigest(), 'rows': None,
                                 'error': 'Required columns missing; rows not profiled'})
                continue
            for number, row in enumerate(reader, start=2):
                file_rows += 1
                ticker = (row.get('ticker') or '').strip()
                raw_date = (row.get('date') or '').strip()
                if ticker != path.stem:
                    flag('ticker_filename_mismatch', path.name, number, ticker)
                if not ticker:
                    flag('blank_ticker', path.name, number, '')
                try:
                    day = date.fromisoformat(raw_date)
                except ValueError:
                    flag('invalid_date', path.name, number, raw_date)
                    continue
                if day.isoformat() != raw_date:
                    flag('noncanonical_date', path.name, number, raw_date)
                key = (ticker, day.isoformat())
                if key in seen:
                    flag('duplicate_ticker_date', path.name, number, list(key))
                seen.add(key)
                if previous_date is not None and day < previous_date:
                    flag('out_of_order_date', path.name, number, raw_date)
                previous_date = day
                file_first = min(file_first, day) if file_first else day
                file_last = max(file_last, day) if file_last else day
                values = {}
                for field in PRICE_FIELDS:
                    raw = (row.get(field) or '').strip()
                    try:
                        value = Decimal(raw)
                        if not value.is_finite():
                            raise ValueError('nonfinite')
                        values[field] = value
                        if value <= 0:
                            nonpositive_by_field[field] += 1
                            affected_files.add(path.name)
                            flag('nonpositive_price', path.name, number, {'field': field, 'value': raw})
                    except (InvalidOperation, ValueError):
                        flag('invalid_price', path.name, number, {'field': field, 'value': raw})
                if len(values) == 4 and (values['low'] > values['high'] or
                    not values['low'] <= values['open'] <= values['high'] or
                    not values['low'] <= values['close'] <= values['high']):
                    range_by_year[str(day.year)] += 1
                    if values['open'] <= 0:
                        counts['ohlc_inconsistent_with_nonpositive_open'] += 1
                    flag('ohlc_range_inconsistent', path.name, number,
                         {field: str(values[field]) for field in PRICE_FIELDS})
        counts['rows'] += file_rows
        if file_first:
            starts.append(file_first)
            ends.append(file_last)
            first_date = min(first_date, file_first) if first_date else file_first
            last_date = max(last_date, file_last) if last_date else file_last
        manifest.append({'file': path.name, 'sha256': digest.hexdigest(), 'rows': file_rows,
                         'first_date': file_first.isoformat() if file_first else None,
                         'last_date': file_last.isoformat() if file_last else None})
    return {'profiled_at_utc': datetime.now(timezone.utc).isoformat(),
            'file_count': len(paths), 'total_bytes': sum(p.stat().st_size for p in paths),
            'date_range': {'first': first_date.isoformat() if first_date else None,
                           'last': last_date.isoformat() if last_date else None},
            'files_ending_on_latest_date': sum(day == last_date for day in ends),
            'files_with_five_year_history_at_latest': sum((last_date.year - d.year, last_date.month, last_date.day) >= (5, d.month, d.day) for d in starts) if last_date else 0,
            'headers': [{'columns': list(k), 'file_count': v} for k, v in headers.items()],
            'nonpositive_by_field': dict(nonpositive_by_field),
            'files_with_nonpositive_prices': len(affected_files),
            'ohlc_inconsistent_by_year': dict(sorted(range_by_year.items())),
            'counts': dict(counts), 'examples': examples, 'files': manifest}


if __name__ == '__main__':
    result = profile()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"Profiled {result['file_count']} files and {result['counts'].get('rows', 0):,} rows; wrote {OUTPUT}")
