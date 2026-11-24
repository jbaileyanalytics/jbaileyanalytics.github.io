import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, PROJECT / 'pipelines' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


publication = load('validate_publication')
assembly = load('assemble_portfolio_site')


class PublicationTests(unittest.TestCase):
    def test_only_explicit_public_assets_are_included(self):
        self.assertTrue(assembly.allowed('index.html'))
        self.assertTrue(assembly.allowed('images/projects/chart.png'))
        self.assertTrue(assembly.allowed('assets/resume/John-Bailey-II-Resume.pdf'))
        self.assertTrue(assembly.allowed('projects/weather-api-pipeline/docs/weather-data-model.svg'))
        self.assertTrue(assembly.allowed('projects/nfl-analytics/website/data/2026.json'))
        self.assertFalse(assembly.allowed('projects/nfl-analytics/website/data/local-notes.json'))
        self.assertFalse(assembly.allowed('datasets/prices.csv'))
        self.assertFalse(assembly.allowed('projects/stock-market-analytics/results/secret.json'))
        self.assertFalse(assembly.allowed('assets/css/../../.env'))
        self.assertFalse(assembly.allowed('assets/css/settings.json'))

    def test_rejects_regression_and_insufficient_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary) / 'data'
            data.mkdir()
            (data / 'stocks.json').write_text(json.dumps([{}] * 400), encoding='utf-8')
            overview = {'date': '2024-01-02', 'total_symbols': 400, 'observed_symbols': 400,
                        'eligible_symbols': 400, 'previous_close_eligible_symbols': 400,
                        'stocks': [{'change_pct': '1', 'previous_close_change_pct': '1'}] * 400}
            (data / 'market-overview.json').write_text(json.dumps(overview), encoding='utf-8')
            self.assertEqual(publication.validate(temporary)['symbols'], 400)
            with self.assertRaisesRegex(ValueError, 'older'):
                publication.validate(temporary, {'date': '2024-01-03', 'total_symbols': 400})
            overview['eligible_symbols'] = 300
            overview['stocks'] = [{'change_pct': '1', 'previous_close_change_pct': '1'}] * 300
            overview['observed_symbols'] = 300
            overview['previous_close_eligible_symbols'] = 300
            (data / 'market-overview.json').write_text(json.dumps(overview), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'coverage'):
                publication.validate(temporary)

    def test_assembles_nfl_dashboard_and_excludes_unlisted_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo, candidate, output = root / 'repo', root / 'stock', root / 'artifact'
            repo.mkdir()
            (candidate / 'data').mkdir(parents=True)
            (candidate / 'index.html').write_text('stock', encoding='utf-8')
            (candidate / 'data/market-overview.json').write_text('{}', encoding='utf-8')
            names = ['index.html', 'projects/nfl-analytics/website/index.html',
                     'projects/nfl-analytics/website/styles.css', 'projects/nfl-analytics/website/app.js',
                     'projects/nfl-analytics/website/data/seasons.json',
                     'projects/nfl-analytics/website/data/2025.json',
                     'projects/nfl-analytics/website/data/2026.json',
                     'projects/nfl-analytics/website/data/private.json']
            for name in names:
                path = repo / name
                path.parent.mkdir(parents=True, exist_ok=True)
                content = ('projects/nfl-analytics/website/' if name == 'index.html' else
                           '[{"season":2025},{"season":2026}]' if name.endswith('seasons.json') else 'example')
                path.write_text(content, encoding='utf-8')
            tracked = ('\0'.join(names) + '\0').encode('utf-8')
            with patch.object(assembly.subprocess, 'check_output', return_value=tracked):
                assembly.assemble(repo, candidate, output)
            self.assertTrue((output / 'projects/nfl-analytics/website/data/2026.json').is_file())
            self.assertFalse((output / 'projects/nfl-analytics/website/data/private.json').exists())
            self.assertTrue((output / 'projects/stock-market-analytics/website/data/market-overview.json').is_file())

    def test_missing_nfl_snapshot_blocks_deployment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo, candidate = root / 'repo', root / 'stock'
            repo.mkdir()
            (repo / 'index.html').write_text('projects/nfl-analytics/website/', encoding='utf-8')
            (candidate / 'data').mkdir(parents=True)
            (candidate / 'index.html').write_text('stock', encoding='utf-8')
            (candidate / 'data/market-overview.json').write_text('{}', encoding='utf-8')
            with patch.object(assembly.subprocess, 'check_output', return_value=b'index.html\0'):
                with self.assertRaisesRegex(ValueError, 'NFL dashboard'):
                    assembly.assemble(repo, candidate, root / 'artifact')

    def test_prepared_nfl_snapshot_overrides_tracked_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo, candidate, nfl, output = (root / name for name in ('repo', 'stock', 'nfl', 'artifact'))
            repo.mkdir()
            (candidate / 'data').mkdir(parents=True)
            (candidate / 'index.html').write_text('stock')
            (candidate / 'data/market-overview.json').write_text('{}')
            nfl.mkdir()
            (nfl / 'seasons.json').write_text('[{"season":2027}]')
            (nfl / '2027.json').write_text('new snapshot')
            (nfl / 'private.json').write_text('not public')
            names = ['index.html', 'projects/nfl-analytics/website/index.html',
                     'projects/nfl-analytics/website/styles.css', 'projects/nfl-analytics/website/app.js',
                     'projects/nfl-analytics/website/data/2026.json']
            for name in names:
                path = repo / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('projects/nfl-analytics/website/' if name == 'index.html' else 'old')
            with patch.object(assembly.subprocess, 'check_output', return_value=('\0'.join(names) + '\0').encode()):
                assembly.assemble(repo, candidate, output, nfl)
            data = output / 'projects/nfl-analytics/website/data'
            self.assertEqual((data / '2027.json').read_text(), 'new snapshot')
            self.assertFalse((data / '2026.json').exists())
            self.assertFalse((data / 'private.json').exists())


if __name__ == '__main__':
    unittest.main()
