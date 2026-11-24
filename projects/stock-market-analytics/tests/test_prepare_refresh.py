import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_refresh', PROJECT / 'pipelines/prepare_refresh.py')
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


class RefreshTests(unittest.TestCase):
    def test_snapshot_build_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'input'
            source.mkdir()
            (source / 'ABC.csv').write_text(
                'ticker,date,open,high,low,close\nABC,2024-01-02,10,12,9,10\nABC,2024-01-03,12,13,10,11\n',
                encoding='utf-8')
            result = refresh.run(source, root / 'candidate')
            self.assertEqual(result['stocks'], 1)
            self.assertEqual(result['market_date'], '2024-01-03')
            overview = json.loads((root / 'candidate/site/data/market-overview.json').read_text())
            self.assertEqual(overview['stocks'][0]['ticker'], 'ABC')
            self.assertAlmostEqual(float(overview['stocks'][0]['change_pct']), -100 / 12)
            self.assertEqual(float(overview['stocks'][0]['previous_close_change_pct']), 10.0)
            self.assertEqual(overview['stocks'][0]['previous_close_date'], '2024-01-02')
            with self.assertRaises(FileExistsError):
                refresh.run(source, root / 'candidate')


if __name__ == '__main__':
    unittest.main()
