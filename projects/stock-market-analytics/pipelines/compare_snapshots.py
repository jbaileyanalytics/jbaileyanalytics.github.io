"""Compare two SQLite stock snapshots by ticker and calendar date, read-only."""
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import sqlite3

FIELDS = ('open', 'high', 'low', 'close')
QUERY = '''SELECT s.ticker, d.calendar_date, p.open, p.high, p.low, p.close
           FROM fact_daily_price p
           JOIN dim_stock s ON s.stock_id = p.stock_id
           JOIN dim_date d ON d.date_id = p.date_id
           ORDER BY s.ticker, d.calendar_date'''


def numeric(value):
    return None if value is None else Decimal(str(value))


def compare(previous, candidate, sample_limit=10):
    """Return aggregate changes; compare business keys rather than surrogate IDs."""
    if sample_limit < 0:
        raise ValueError('sample_limit must be nonnegative')
    connections = []
    try:
        for filename in (previous, candidate):
            path = Path(filename).resolve()
            if not path.is_file():
                raise FileNotFoundError('Snapshot database does not exist')
            db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
            connections.append(db)
            db.execute('BEGIN')
        cursors = [iter(db.execute(QUERY)) for db in connections]
        rows = [next(cursor, None) for cursor in cursors]
        counts, field_changes = Counter(), Counter()
        newly_missing, newly_present = Counter(), Counter()
        samples = {'added': [], 'removed': [], 'changed': []}
        while rows[0] is not None or rows[1] is not None:
            left, right = rows
            if left is None or (right is not None and right[:2] < left[:2]):
                category, record = 'added', right
                rows[1] = next(cursors[1], None)
            elif right is None or left[:2] < right[:2]:
                category, record = 'removed', left
                rows[0] = next(cursors[0], None)
            else:
                changes = []
                for field, before, after in zip(FIELDS, left[2:], right[2:]):
                    if numeric(before) != numeric(after):
                        changes.append(field)
                        field_changes[field] += 1
                        if before is not None and after is None:
                            newly_missing[field] += 1
                        elif before is None and after is not None:
                            newly_present[field] += 1
                category = 'changed' if changes else 'unchanged'
                record = left
                rows[0], rows[1] = next(cursors[0], None), next(cursors[1], None)
            counts[category] += 1
            if category != 'unchanged' and len(samples[category]) < sample_limit:
                sample = {'ticker': record[0], 'date': record[1]}
                if category == 'changed':
                    sample['changed_fields'] = changes
                samples[category].append(sample)
        return {
            'comparison_key': ['ticker', 'calendar_date'],
            'previous_rows': counts['unchanged'] + counts['changed'] + counts['removed'],
            'candidate_rows': counts['unchanged'] + counts['changed'] + counts['added'],
            'unchanged': counts['unchanged'], 'changed': counts['changed'],
            'added': counts['added'], 'removed': counts['removed'],
            'changed_fields': dict(field_changes), 'newly_missing': dict(newly_missing),
            'newly_present': dict(newly_present), 'samples': samples,
            'note': 'Compares validated stored prices, not raw source values or the reason for a change.',
        }
    finally:
        for db in connections:
            db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sample-limit', type=int, default=10)
    args = parser.parse_args()
    result = compare(args.previous, args.candidate, args.sample_limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))
