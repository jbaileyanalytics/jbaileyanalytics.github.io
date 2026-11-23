"""Small-fixture checks for exact value and lineage reconciliation."""
import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

HAS_DEPS = importlib.util.find_spec('duckdb') is not None and importlib.util.find_spec('pyarrow') is not None
if HAS_DEPS:
    PIPELINES = Path(__file__).resolve().parents[1] / 'pipelines'
    sys.path.insert(0, str(PIPELINES))
    spec = importlib.util.spec_from_file_location('audit_batch', PIPELINES / 'audit_batch.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    import pyarrow as pa
    import pyarrow.parquet as pq

@unittest.skipUnless(HAS_DEPS, 'requires duckdb and pyarrow')
class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / 'data.sqlite'
        with sqlite3.connect(self.db) as db:
            db.executescript('''CREATE TABLE dim_stock(stock_id INTEGER,ticker TEXT);
                CREATE TABLE dim_date(date_id INTEGER,calendar_date TEXT);
                CREATE TABLE fact_daily_price(daily_price_id INTEGER,stock_id INTEGER,date_id INTEGER,open TEXT,high TEXT,low TEXT,close TEXT);
                CREATE TABLE audit_source_file(source_file_id INTEGER,source_rows INTEGER);
                CREATE TABLE audit_price_lineage(daily_price_id INTEGER,source_file_id INTEGER);
                INSERT INTO dim_stock VALUES(1,'AAPL'); INSERT INTO dim_date VALUES(1,'2025-01-02');
                INSERT INTO fact_daily_price VALUES(1,1,1,'1.01','2.00','1.00','1.50');
                INSERT INTO audit_source_file VALUES(1,1); INSERT INTO audit_price_lineage VALUES(1,1);''')
        self.parquet = self.root / 'prices.parquet'

    def write_row(self, close):
        row = {'daily_price_id':1,'stock_id':1,'date_id':1,'ticker':'AAPL','calendar_date':'2025-01-02',
               'open':'1.01','high':'2.00','low':'1.00','close':close}
        pq.write_table(pa.Table.from_pylist([row]),self.parquet)

    def test_matching_prices_and_lineage_pass(self):
        self.write_row('1.50')
        result = module.audit(self.db,self.parquet,self.root/'result.json')
        self.assertEqual(result['rows_compared'],1)
        self.assertEqual(result['lineage_rows'],1)

    def test_changed_price_fails_without_success_output(self):
        self.write_row('1.51')
        with self.assertRaisesRegex(ValueError,'differs'):
            module.audit(self.db,self.parquet,self.root/'result.json')
        self.assertFalse((self.root/'result.json').exists())

if __name__ == '__main__': unittest.main()
