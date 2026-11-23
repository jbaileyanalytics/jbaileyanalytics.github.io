import json
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_published_data as refresh


def baseline(season=2026, weeks=(1,)):
    rows = []
    for week in weeks:
        row = {'player_id': 'player1', 'player_display_name': 'Player One', 'position': 'QB',
               'season': season, 'week': week, 'team': 'KC', 'opponent_team': 'BUF'}
        row.update({field: 0 for field in refresh.FIELDS[7:]})
        rows.append([row[field] for field in refresh.FIELDS])
    meta = {'season': season, 'weeks': list(weeks), 'players': 1, 'records': len(rows)}
    return meta, {'fields': refresh.FIELDS, 'records': rows}


class NFLPublishingTests(unittest.TestCase):
    def setUp(self):
        self.meta, self.snapshot = baseline()
        self.old_meta, self.old_snapshot = baseline(2025)
        self.data = ([self.old_meta, self.meta], {2025: self.old_snapshot, 2026: self.snapshot})
        self.now = datetime(2026, 11, 24)

    def test_stock_only_run_retains_published_nfl(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'output'
            result = refresh.prepare(out, loader=lambda: self.data, downloader=lambda _: self.fail('unexpected download'))
            self.assertEqual(result['seasons'], [2025, 2026])
            self.assertEqual(json.loads((out / '2026.json').read_text()), self.snapshot)

    def test_new_nfl_week_replaces_only_current_season(self):
        new_meta, new_snapshot = baseline(2026, (1, 2))
        with tempfile.TemporaryDirectory() as folder, patch.object(refresh, 'candidate_snapshot', return_value=(new_meta, new_snapshot)):
            out = Path(folder) / 'output'
            result = refresh.prepare(out, True, loader=lambda: self.data, now=self.now)
            self.assertIn('week 2', result['status'])
            self.assertEqual(json.loads((out / '2026.json').read_text()), new_snapshot)
            self.assertEqual(json.loads((out / '2025.json').read_text()), self.old_snapshot)

    def test_failed_or_regressing_refresh_preserves_baseline(self):
        older_meta, older_snapshot = baseline(2026, (1,))
        existing_meta, existing_snapshot = baseline(2026, (1, 2))
        data = ([existing_meta], {2026: existing_snapshot})
        for candidate in (RuntimeError('unavailable'), (older_meta, older_snapshot)):
            with self.subTest(candidate=type(candidate)), tempfile.TemporaryDirectory() as folder:
                out = Path(folder) / 'output'
                side_effect = candidate if isinstance(candidate, Exception) else None
                with patch.object(refresh, 'candidate_snapshot', return_value=candidate, side_effect=side_effect):
                    result = refresh.prepare(out, True, loader=lambda: data, now=self.now)
                self.assertIn('baseline preserved', result['status'])
                self.assertEqual(json.loads((out / '2026.json').read_text()), existing_snapshot)

    def test_invalid_baseline_blocks_output(self):
        bad = dict(self.meta, records=100)
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'output'
            with self.assertRaises(ValueError):
                refresh.prepare(out, loader=lambda: ([bad], {2026: self.snapshot}))
            self.assertFalse(out.exists())

    def test_only_missing_index_allows_first_deployment_fallback(self):
        missing = HTTPError('https://example.org', 404, 'missing', None, None)
        with patch.object(refresh, 'read_url', side_effect=missing):
            self.assertIsNone(refresh.load_published())
        with patch.object(refresh, 'read_url', side_effect=[[self.meta], missing]):
            with self.assertRaises(HTTPError):
                refresh.load_published()

    def test_season_rollover(self):
        self.assertEqual(refresh.current_season(datetime(2027, 1, 1)), 2026)
        self.assertEqual(refresh.current_season(datetime(2027, 7, 1)), 2027)


if __name__ == '__main__':
    unittest.main()
