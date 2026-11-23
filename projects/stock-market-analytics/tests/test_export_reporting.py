import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

builder = load('build_local', PROJECT / 'pipelines/build_local.py')
reporting = load('export_reporting', PROJECT / 'pipelines/export_reporting.py')


class ReportingExportTests(unittest.TestCase):
    def test_exports_matching_website_and_report_with_quality_nulls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            source.mkdir()
            (source / 'ABC.csv').write_text('ticker,date,open,high,low,close\n'
                'ABC,2023-12-29,10,11,9,10\nABC,2024-12-31,0,13,10,12\n', encoding='utf-8')
            database = root / 'market.sqlite'
            builder.build(source, database)
            output = root / 'reporting'
            manifest = reporting.export(database, output)
            self.assertEqual(manifest['counts']['daily_prices'], 2)
            self.assertEqual(manifest['counts']['trailing_returns'], 7)
            index = json.loads((output / 'website/stocks.json').read_text())
            payload = json.loads((output / 'website' / index[0]['data_file']).read_text())
            with (output / 'powerbi/daily_prices.csv').open(newline='', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[-1]['open'], '')
            self.assertIsNone(payload['daily'][-1][1])
            self.assertEqual(payload['quality_summary']['open: nonpositive_or_invalid'], 1)
            with (output / 'powerbi/quality_issues.csv').open(newline='', encoding='utf-8') as f:
                self.assertEqual(next(csv.DictReader(f))['source_value'], '0')
            with (output / 'powerbi/trailing_returns.csv').open(newline='', encoding='utf-8') as f:
                returns = {r['period']: r for r in csv.DictReader(f)}
            self.assertEqual(returns['YTD']['percent'], payload['overview']['returns']['YTD']['percent'])
            self.assertEqual(returns['5 years']['reason'], 'insufficient history')
            with self.assertRaises(FileExistsError):
                reporting.export(database, output)


if __name__ == '__main__':
    unittest.main()
