"""Export one consistent stock snapshot for analytical reporting and the website.

An existing output directory is never replaced. Run against a completed local build.
"""
import argparse
from contextlib import ExitStack, closing
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'src'))
from analytics import analyze, period_prices, read_prices

DATABASE = PROJECT / 'results' / 'market-data.sqlite'
OUTPUT = PROJECT / 'results' / 'reporting-v1'
PERIOD_FIELDS = ['period_start', 'period_end', 'first_observation', 'last_observation',
                 'open', 'high', 'low', 'close', 'observations', 'period_ends_after_latest_observation']


def export(database=DATABASE, output=OUTPUT):
    database, output = Path(database).resolve(), Path(output).resolve()
    if not database.is_file():
        raise FileNotFoundError(f'Database not found: {database}')
    if output.exists():
        raise FileExistsError(f'Reporting directory already exists: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.reporting-stage-', dir=output.parent))
    try:
        pbi, site = staging / 'powerbi', staging / 'website' / 'stocks'
        pbi.mkdir(parents=True)
        site.mkdir(parents=True)
        counts = {'stocks': 0, 'daily_prices': 0, 'period_prices': 0, 'trailing_returns': 0, 'annual_returns': 0, 'quality_issues': 0}
        with closing(sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True)) as db, ExitStack() as stack:
            db.execute('BEGIN')  # All exported tables use a single SQLite read snapshot.
            securities = db.execute('SELECT stock_id,ticker FROM dim_stock ORDER BY ticker').fetchall()
            expected_rows = db.execute('SELECT COUNT(*) FROM fact_daily_price').fetchone()[0]
            sources = db.execute('SELECT file_name,sha256,source_rows FROM audit_source_file ORDER BY file_name').fetchall()
            source_digest = hashlib.sha256(json.dumps(sources, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()

            def writer(name, fields):
                stream = stack.enter_context((pbi / (name + '.csv')).open('w', encoding='utf-8', newline=''))
                result = csv.DictWriter(stream, fieldnames=fields, extrasaction='raise')
                result.writeheader()
                return result

            stocks = writer('stocks', ['stock_id', 'ticker', 'latest_observation_date', 'latest_close',
                'previous_close_date', 'previous_close', 'latest_open', 'latest_high', 'latest_low',
                'range_start_exclusive', 'range_end_inclusive', 'range_high', 'range_low', 'range_observations',
                'history_starts_within_window', 'missing_highs', 'missing_lows'])
            daily = writer('daily_prices', ['stock_id', 'date', 'open', 'high', 'low', 'close'])
            periods = writer('period_prices', ['stock_id', 'frequency', *PERIOD_FIELDS])
            returns = writer('trailing_returns', ['stock_id', 'period', 'percent', 'baseline_date', 'reason'])
            annual = writer('annual_returns', ['stock_id', 'year', 'end_date', 'partial', 'percent', 'baseline_date', 'reason'])
            quality = writer('quality_issues', ['stock_id', 'date', 'field', 'rule', 'source_value', 'source_file', 'source_line'])
            quality_by_stock = {}
            for stock_id, day, field, rule, value, name, line in db.execute('''
                SELECT f.stock_id,d.calendar_date,q.field,q.rule,q.source_value,s.file_name,l.source_line
                FROM audit_quality_issue q JOIN fact_daily_price f ON f.daily_price_id=q.daily_price_id
                JOIN dim_date d ON d.date_id=f.date_id
                JOIN audit_price_lineage l ON l.daily_price_id=f.daily_price_id
                JOIN audit_source_file s ON s.source_file_id=l.source_file_id
                ORDER BY f.stock_id,d.calendar_date,q.quality_issue_id'''):
                quality.writerow({'stock_id': stock_id, 'date': day, 'field': field, 'rule': rule,
                                  'source_value': value, 'source_file': name, 'source_line': line})
                bucket = quality_by_stock.setdefault(stock_id, {})
                label = f'{field}: {rule}'
                bucket[label] = bucket.get(label, 0) + 1
                counts['quality_issues'] += 1
            index = []
            for stock_id, ticker in securities:
                rows = read_prices(db, ticker)
                overview = analyze(rows, ticker)
                range_data = overview['range_52_weeks']
                stocks.writerow({'stock_id': stock_id, 'ticker': ticker,
                    **{field: overview[field] for field in ['latest_observation_date','latest_close','previous_close_date',
                                                          'previous_close','latest_open','latest_high','latest_low']},
                    'range_start_exclusive': range_data['start_exclusive'], 'range_end_inclusive': range_data['end_inclusive'],
                    'range_high': range_data['high'], 'range_low': range_data['low'],
                    'range_observations': range_data['observations'], 'history_starts_within_window': range_data['starts_within_window'],
                    'missing_highs': range_data['missing_highs'], 'missing_lows': range_data['missing_lows']})
                counts['stocks'] += 1
                compact_daily = []
                for row in rows:
                    item = [row['date'].isoformat(), *[str(row[field]) if row[field] is not None else None
                                                     for field in ('open', 'high', 'low', 'close')]]
                    compact_daily.append(item)
                    daily.writerow(dict(zip(['date', 'open', 'high', 'low', 'close'], item), stock_id=stock_id))
                    counts['daily_prices'] += 1
                aggregated = {}
                for frequency in ('weekly', 'monthly'):
                    aggregated[frequency] = period_prices(rows, frequency)
                    for period in aggregated[frequency]:
                        periods.writerow({'stock_id': stock_id, 'frequency': frequency, **period})
                        counts['period_prices'] += 1
                for name, data in overview['returns'].items():
                    returns.writerow({'stock_id': stock_id, 'period': name, **data})
                    counts['trailing_returns'] += 1
                for data in overview['annual_price_returns']:
                    annual.writerow({'stock_id': stock_id, **data})
                    counts['annual_returns'] += 1
                # IDs, rather than symbols, make safe portable filenames.
                payload = {'stock_id': stock_id, 'overview': overview, 'quality_summary': quality_by_stock.get(stock_id, {}),
                    'daily_columns': ['date', 'open', 'high', 'low', 'close'], 'daily': compact_daily,
                    'weekly': aggregated['weekly'], 'monthly': aggregated['monthly']}
                (site / f'{stock_id}.json').write_text(json.dumps(payload, separators=(',', ':')) + '\n', encoding='utf-8')
                index.append({'stock_id': stock_id, 'ticker': ticker, 'latest_observation_date': overview['latest_observation_date'],
                              'data_file': f'stocks/{stock_id}.json'})
            if counts['daily_prices'] != expected_rows or counts['stocks'] != len(securities):
                raise ValueError('Export did not reconcile to the database snapshot')
            if counts['trailing_returns'] != counts['stocks'] * 7:
                raise ValueError('Trailing-return coverage did not reconcile')
            if counts['quality_issues'] != db.execute('SELECT COUNT(*) FROM audit_quality_issue').fetchone()[0]:
                raise ValueError('Quality issue coverage did not reconcile')
            (staging / 'website' / 'stocks.json').write_text(json.dumps(index, separators=(',', ':')) + '\n', encoding='utf-8')
            manifest = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'source_manifest_sha256': source_digest,
                'source_files': len(sources), 'counts': counts, 'schema_version': 1,
                'notes': ['Historical snapshot, not live.', 'Price-return percentages are percentage points, not fractions.',
                          'Currency, split and dividend adjustment treatment are unverified.',
                          'Stock-specific latest observation dates can differ.']}
            (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        if output.exists():
            raise FileExistsError(f'Reporting directory already exists: {output}')
        os.rename(staging, output)
        return manifest
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DATABASE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(export(args.database, args.output), indent=2))
