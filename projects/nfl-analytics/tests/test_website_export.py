"""Check that local website snapshots preserve validated player-week data."""
import csv
import io
import json
from pathlib import Path
import unittest

PROJECT = Path(__file__).resolve().parents[1]


class WebsiteExportTests(unittest.TestCase):
    def test_web_records_match_validated_snapshots(self):
        data = PROJECT / 'website/data'
        if not (data / 'seasons.json').is_file():
            self.skipTest('Local website snapshots have not been generated')
        seasons = json.loads((data / 'seasons.json').read_text(encoding='utf-8'))
        for item in seasons:
            season = item['season']
            with self.subTest(season=season):
                pointer = PROJECT / 'data' / f'current_{season}.json'
                if not pointer.is_file():
                    self.skipTest('Local source snapshot is unavailable')
                manifest = json.loads(pointer.read_text(encoding='utf-8'))
                source = (PROJECT / 'data' / manifest['normalized_path']).read_bytes()
                raw = list(csv.DictReader(io.StringIO(source.decode('utf-8-sig'))))
                web = json.loads((data / f'{season}.json').read_text(encoding='utf-8'))
                self.assertIn('passing_interceptions', web['fields'])
                self.assertEqual(len(web['records']), len(raw))
                for source_row, browser_row in zip(raw, web['records']):
                    browser = dict(zip(web['fields'], browser_row))
                    for field in ('player_id', 'week', 'team', 'attempts', 'completions',
                                  'passing_yards', 'passing_tds', 'passing_interceptions',
                                  'targets', 'receptions', 'receiving_yards', 'receiving_tds'):
                        self.assertEqual(str(browser[field]), source_row[field])


if __name__ == '__main__':
    unittest.main()
