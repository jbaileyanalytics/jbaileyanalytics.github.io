import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'pipelines'))
from refresh_from_kaggle import refresh


class KaggleRefreshTests(unittest.TestCase):
    def test_builds_candidate_from_download_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'download'
            source.mkdir()
            (source / 'ABC.csv').write_text(
                'ticker,date,open,high,low,close\nABC,2024-01-02,10,12,9,11\n', encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                result = refresh(lambda handle: source, root / 'run', minimum_files=1)
            self.assertEqual(result, {'source_files': 1, 'stocks': 1, 'market_date': '2024-01-02'})
            with self.assertRaises(FileExistsError):
                refresh(lambda handle: source, root / 'run', minimum_files=1)

    def test_rejects_incomplete_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'download'
            source.mkdir()
            (source / 'ABC.csv').write_text('ticker,date,open,high,low,close\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'expected at least 2'):
                refresh(lambda handle: source, root / 'run', minimum_files=2)
            self.assertFalse((root / 'run/candidate/site').exists())


if __name__ == '__main__':
    unittest.main()
