"""Create a first local SQLite snapshot from the supplied CSVs.

This initial builder deliberately refuses to overwrite an existing database.
Incremental loads and revisions require a separate design and are not supported.
"""
import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import os
from pathlib import Path
import sqlite3
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT.parents[1] / 'datasets' / 'Stocks - Nasdaq'
OUTPUT = PROJECT / 'results' / 'market-data.sqlite'
FIELDS = ('ticker', 'date', 'open', 'high', 'low', 'close')


def build(source=SOURCE, output=OUTPUT):
    source, output = Path(source), Path(output)
    files = sorted(source.glob('*.csv'))
    if not files:
        raise ValueError('No source CSV files found')
    if output.exists():
        raise FileExistsError('Database already exists; incremental updates are not implemented')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, filename = tempfile.mkstemp(prefix='market-build-', suffix='.sqlite', dir=output.parent)
    os.close(fd)
    temporary = Path(filename)
    db = sqlite3.connect(temporary)
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.executescript('''
        CREATE TABLE dim_stock (stock_id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL UNIQUE);
        CREATE TABLE dim_date (date_id INTEGER PRIMARY KEY AUTOINCREMENT, calendar_date TEXT NOT NULL UNIQUE,
            year INTEGER NOT NULL, quarter INTEGER NOT NULL, month INTEGER NOT NULL, day INTEGER NOT NULL);
        CREATE TABLE fact_daily_price (daily_price_id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_id INTEGER NOT NULL REFERENCES dim_stock(stock_id), date_id INTEGER NOT NULL REFERENCES dim_date(date_id),
            open TEXT, high TEXT, low TEXT, close TEXT, UNIQUE(stock_id,date_id));
        CREATE TABLE audit_source_file (source_file_id INTEGER PRIMARY KEY AUTOINCREMENT, file_name TEXT NOT NULL UNIQUE,
            sha256 TEXT NOT NULL, source_rows INTEGER NOT NULL);
        CREATE TABLE audit_price_lineage (daily_price_id INTEGER PRIMARY KEY REFERENCES fact_daily_price(daily_price_id),
            source_file_id INTEGER NOT NULL REFERENCES audit_source_file(source_file_id), source_line INTEGER NOT NULL,
            UNIQUE(source_file_id,source_line));
        CREATE TABLE audit_quality_issue (quality_issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            daily_price_id INTEGER NOT NULL REFERENCES fact_daily_price(daily_price_id),
            field TEXT NOT NULL, rule TEXT NOT NULL, source_value TEXT NOT NULL);
        ''')
        dates = {}
        total = issues = 0
        for file in files:
            digest = hashlib.sha256()
            with file.open('rb') as raw:
                for block in iter(lambda: raw.read(1024 * 1024), b''):
                    digest.update(block)
            file_id = db.execute('INSERT INTO audit_source_file(file_name,sha256,source_rows) VALUES (?,?,0)',
                                 (file.name, digest.hexdigest())).lastrowid
            stock_id = db.execute('INSERT INTO dim_stock(ticker) VALUES (?)', (file.stem,)).lastrowid
            count = 0
            with file.open(encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                if tuple(reader.fieldnames or ()) != FIELDS:
                    raise ValueError(f'{file.name}: unexpected columns')
                for row in reader:
                    line = reader.line_num
                    if row['ticker'] != file.stem:
                        raise ValueError(f'{file.name}:{line}: ticker mismatch')
                    day = date.fromisoformat(row['date'])
                    if day.isoformat() != row['date']:
                        raise ValueError(f'{file.name}:{line}: date must be ISO formatted')
                    if day not in dates:
                        dates[day] = db.execute('INSERT INTO dim_date(calendar_date,year,quarter,month,day) VALUES (?,?,?,?,?)',
                            (day.isoformat(), day.year, (day.month - 1)//3 + 1, day.month, day.day)).lastrowid
                    values = {}
                    raw_prices = {field: (row[field] or '').strip() for field in FIELDS[2:]}
                    flags = []
                    for field, raw in raw_prices.items():
                        try:
                            value = Decimal(raw)
                            if not value.is_finite() or value <= 0:
                                raise ValueError('price must be positive and finite')
                            values[field] = value
                        except (InvalidOperation, ValueError):
                            values[field] = None
                            flags.append((field, 'nonpositive_or_invalid', raw))
                    if values['high'] is not None and values['low'] is not None:
                        if values['low'] > values['high']:
                            for field in ('low', 'high'):
                                values[field] = None
                                flags.append((field, 'low_above_high', raw_prices[field]))
                        else:
                            for field in ('open', 'close'):
                                if values[field] is not None and not values['low'] <= values[field] <= values['high']:
                                    values[field] = None
                                    flags.append((field, 'outside_day_range', raw_prices[field]))
                    price_id = db.execute('INSERT INTO fact_daily_price(stock_id,date_id,open,high,low,close) VALUES (?,?,?,?,?,?)',
                        (stock_id, dates[day], *(str(values[f]) if values[f] is not None else None for f in FIELDS[2:]))).lastrowid
                    db.execute('INSERT INTO audit_price_lineage VALUES (?,?,?)', (price_id, file_id, line))
                    db.executemany('INSERT INTO audit_quality_issue(daily_price_id,field,rule,source_value) VALUES (?,?,?,?)',
                                   [(price_id, *flag) for flag in flags])
                    count += 1
                    issues += len(flags)
            db.execute('UPDATE audit_source_file SET source_rows=? WHERE source_file_id=?', (count, file_id))
            total += count
        if db.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Foreign key integrity check failed')
        db.commit()
        db.close()
        # Both publication methods fail if the destination already exists.
        if os.name == 'nt':
            os.rename(temporary, output)
        else:
            os.link(temporary, output)
            temporary.unlink()
        return {'files': len(files), 'rows': total, 'quality_issues': issues, 'database': str(output)}
    except BaseException:
        db.close()
        temporary.unlink(missing_ok=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(build(args.source, args.output))
