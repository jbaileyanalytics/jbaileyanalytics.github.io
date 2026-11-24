import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
def load(name):
    spec = importlib.util.spec_from_file_location(name, PROJECT / 'pipelines' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

build = load('build_local')
overview = load('export_market_overview')

class MarketOverviewTests(unittest.TestCase):
    def test_comparisons_and_missing_baselines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            (source / 'ABC.csv').write_text('ticker,date,open,high,low,close\nABC,2024-01-02,100,110,90,100\nABC,2024-01-03,120,125,105,110\n', encoding='utf-8')
            (source / 'NEW.csv').write_text('ticker,date,open,high,low,close\nNEW,2024-01-03,10,12,9,11\n', encoding='utf-8')
            (source / 'NOOPEN.csv').write_text('ticker,date,open,high,low,close\nNOOPEN,2024-01-02,10,12,9,10\nNOOPEN,2024-01-03,0,12,9,11\n', encoding='utf-8')
            db, output = root / 'data.sqlite', root / 'overview.json'
            build.build(source, db)
            overview.export(db, output)
            result = json.loads(output.read_text(encoding='utf-8'))
            stocks = {row['ticker']: row for row in result['stocks']}
            self.assertAlmostEqual(float(stocks['ABC']['change_pct']), -100 / 12)
            self.assertEqual(float(stocks['ABC']['previous_close_change_pct']), 10.0)
            self.assertEqual(stocks['ABC']['previous_close_date'], '2024-01-02')
            self.assertIsNone(stocks['NEW']['previous_close_change_pct'])
            self.assertIsNone(stocks['NOOPEN']['change_pct'])
            self.assertEqual(float(stocks['NOOPEN']['previous_close_change_pct']), 10.0)
            self.assertEqual(result['eligible_symbols'], 2)
            self.assertEqual(result['previous_close_eligible_symbols'], 2)

if __name__ == '__main__':
    unittest.main()
