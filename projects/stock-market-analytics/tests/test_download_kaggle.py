import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'pipelines' / 'download_kaggle.py'
spec = importlib.util.spec_from_file_location('download_kaggle', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DownloadTests(unittest.TestCase):
    def test_inventory_records_hash_and_preserves_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'snapshot'
            source.mkdir()
            data = source / 'AAPL.csv'
            data.write_text('ticker,date\nAAPL,2024-01-01\n', encoding='utf-8')
            original = data.read_bytes()
            result, manifest_path, count = module.download_and_manifest(lambda handle: source, root / 'audit')
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            self.assertEqual(result, source)
            self.assertEqual(count, 1)
            self.assertEqual(manifest['dataset'], module.HANDLE)
            self.assertEqual(manifest['files'][0]['path'], 'AAPL.csv')
            self.assertEqual(len(manifest['files'][0]['sha256']), 64)
            self.assertEqual(data.read_bytes(), original)

    def test_empty_download_does_not_create_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                module.download_and_manifest(lambda handle: root, root / 'audit')
            self.assertFalse((root / 'audit').exists())


if __name__ == '__main__':
    unittest.main()
