import importlib.util
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compare_snapshots', PROJECT / 'pipelines/compare_snapshots.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def create_snapshot(path, stock_id, rows):
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript('''CREATE TABLE dim_stock(stock_id INTEGER, ticker TEXT);
            CREATE TABLE dim_date(date_id INTEGER, calendar_date TEXT);
            CREATE TABLE fact_daily_price(stock_id INTEGER, date_id INTEGER,
                open TEXT, high TEXT, low TEXT, close TEXT);''')
        db.execute('INSERT INTO dim_stock VALUES (?,?)', (stock_id, 'ABC'))
        for date_id, (day, prices) in enumerate(rows, 1):
            db.execute('INSERT INTO dim_date VALUES (?,?)', (date_id, day))
            db.execute('INSERT INTO fact_daily_price VALUES (?,?,?,?,?,?)', (stock_id, date_id, *prices))


class ComparisonTests(unittest.TestCase):
    def test_business_keys_and_numeric_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / 'first.sqlite', root / 'second.sqlite'
            create_snapshot(first, 1, [
                ('2024-01-01', ('1.0', '3', '1', '2')),
                ('2024-01-02', ('1', '3', '1', '2')),
                ('2024-01-03', ('1', '3', '1', '2')),
            ])
            create_snapshot(second, 99, [
                ('2024-01-01', ('1.00', '3', '1', '2')),
                ('2024-01-02', (None, '3', '1', '2.5')),
                ('2024-01-04', ('1', '3', '1', '2')),
            ])
            result = module.compare(first, second)
            self.assertEqual((result['unchanged'], result['changed'], result['added'], result['removed']), (1, 1, 1, 1))
            self.assertEqual(result['changed_fields'], {'open': 1, 'close': 1})
            self.assertEqual(result['newly_missing'], {'open': 1})
            self.assertEqual(result['samples']['changed'][0]['date'], '2024-01-02')


if __name__ == '__main__':
    unittest.main()
