import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'pipelines' / 'profile_sources.py'
spec = importlib.util.spec_from_file_location('profile_sources', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProfileTests(unittest.TestCase):
    def test_detects_quality_issues_and_tracks_file_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            with (folder / 'ABC.csv').open('w', newline='', encoding='utf-8') as stream:
                writer = csv.writer(stream)
                writer.writerow(module.EXPECTED)
                writer.writerow(['ABC', '2024-01-02', 10, 12, 9, 11])
                writer.writerow(['ABC', '2024-01-02', 10, 8, 9, 11])
                writer.writerow(['OTHER', 'not-a-date', 1, 1, 1, 1])
            result = module.profile(folder)
            self.assertEqual(result['counts']['rows'], 3)
            self.assertEqual(result['counts']['duplicate_ticker_date'], 1)
            self.assertEqual(result['counts']['ohlc_range_inconsistent'], 1)
            self.assertEqual(result['counts']['ticker_filename_mismatch'], 1)
            self.assertEqual(result['counts']['invalid_date'], 1)
            self.assertEqual(result['date_range']['first'], '2024-01-02')
            self.assertEqual(len(result['files'][0]['sha256']), 64)

    def test_missing_columns_are_not_silently_processed(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'ABC.csv').write_text('ticker,date\nABC,2024-01-01\n', encoding='utf-8')
            result = module.profile(folder)
            self.assertEqual(result['counts']['unexpected_header'], 1)
            self.assertIsNone(result['files'][0]['rows'])


if __name__ == '__main__':
    unittest.main()
