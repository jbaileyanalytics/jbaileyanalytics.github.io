import csv
from contextlib import closing
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('build_local', Path(__file__).resolve().parents[1] / 'pipelines/build_local.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LocalBuildTests(unittest.TestCase):
    def test_preserves_unaffected_prices_and_audits_invalid_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source'
            source.mkdir()
            (source / 'ABC.csv').write_text('ticker,date,open,high,low,close\nABC,2024-01-02,0,12.125,9,11\n', encoding='utf-8')
            output = Path(tmp) / 'output.sqlite'
            result = module.build(source, output)
            self.assertEqual((result['rows'], result['quality_issues']), (1, 1))
            with closing(sqlite3.connect(output)) as db:
                self.assertEqual(db.execute('SELECT open,high,low,close FROM fact_daily_price').fetchone(), (None, '12.125', '9', '11'))
                self.assertEqual(db.execute('SELECT field,source_value FROM audit_quality_issue').fetchone(), ('open', '0'))
                self.assertEqual(db.execute('SELECT source_line FROM audit_price_lineage').fetchone(), (2,))
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            with self.assertRaises(FileExistsError):
                module.build(source, output)

    def test_duplicate_observations_do_not_publish_partial_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source'
            source.mkdir()
            (source / 'ABC.csv').write_text('ticker,date,open,high,low,close\nABC,2024-01-02,10,12,9,11\nABC,2024-01-02,10,12,9,11\n', encoding='utf-8')
            output = Path(tmp) / 'output.sqlite'
            with self.assertRaises(sqlite3.IntegrityError):
                module.build(source, output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
