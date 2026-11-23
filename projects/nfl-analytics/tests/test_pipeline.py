import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from pipeline import FIELDS, COUNTS, YARDS, DataError, normalize_csv, aggregate_players, weekly_metrics
from ingest import publish

def fixture():
    rows = []
    for pid, name, pos, week, team, targets, receptions, rec_yards in [
        ('A', 'Fixture Receiver A', 'WR', 1, 'AAA', 10, 6, 100),
        ('A', 'Fixture Receiver A', 'WR', 2, 'BBB', 2, 1, 10),
        ('B', 'Fixture Receiver B', 'WR', 1, 'AAA', 4, 3, 24),
        ('Q', 'Fixture Quarterback', 'QB', 1, 'AAA', 0, 0, 0)]:
        row = {col: 0 for col in COUNTS + YARDS}
        row.update(player_id=pid, player_display_name=name, position=pos, season=2025,
            week=week, season_type='REG', game_id=f'fixture-{week}', team=team, opponent_team='CCC',
            targets=targets, receptions=receptions, receiving_yards=rec_yards)
        if pid == 'Q':
            row.update(attempts=20, completions=12, passing_yards=200, passing_tds=2, passing_interceptions=1,
                carries=2, rushing_yards=-1)
        rows.append(row)
    return pd.DataFrame(rows)[FIELDS]

def encoded(frame):
    return frame.to_csv(index=False).encode()

class PipelineTests(unittest.TestCase):
    def test_weighted_rates_and_player_identity(self):
        frame, _ = normalize_csv(encoded(fixture()), 2025)
        players = aggregate_players(frame, 'Receiving', 1).set_index('player_id')
        self.assertAlmostEqual(players.loc['A', 'yards_per_opportunity'], 110 / 12)
        self.assertAlmostEqual(players.loc['A', 'catch_rate'], 7 / 12)
        self.assertEqual(players.loc['A', 'team'], 'BBB')
        self.assertEqual(players.loc['A', 'teams_in_scope'], 'AAA, BBB')
        self.assertEqual(players.loc['B', 'observed_weeks'], 1)
        self.assertNotIn('Q', players.index)

    def test_weekly_reconciliation_and_filters(self):
        frame, _ = normalize_csv(encoded(fixture()), 2025)
        players = aggregate_players(frame, 'Receiving', 5)
        self.assertEqual(players['player_id'].tolist(), ['A'])
        weekly = weekly_metrics(frame[frame.player_id.isin(players.player_id)], 'Receiving')
        self.assertEqual(weekly['yards'].sum(), players['yards'].sum())
        self.assertEqual(weekly['opportunities'].sum(), players['opportunities'].sum())
        self.assertEqual(aggregate_players(frame[frame.team == 'AAA'], 'Receiving', 1).set_index('player_id').loc['A', 'yards'], 100)

    def test_negative_yardage_and_zero_denominators(self):
        frame, _ = normalize_csv(encoded(fixture()), 2025)
        passing = aggregate_players(frame, 'Passing', 1).iloc[0]
        self.assertEqual(passing['yards_per_opportunity'], 10)
        self.assertTrue(pd.isna(passing['catch_rate']))
        rushing = aggregate_players(frame, 'Rushing', 1).iloc[0]
        self.assertEqual(rushing['yards_per_opportunity'], -.5)

    def test_schema_duplicates_and_invalid_counts(self):
        base = fixture()
        bad_frames = [base.drop(columns=['targets']), pd.concat([base, base.head(1)], ignore_index=True)]
        for col, value in [('targets', -1), ('week', 19), ('completions', 100),
                           ('receptions', 100), ('receiving_yards', 'NaN'), ('season', 2024), ('player_id', '')]:
            bad = base.copy().astype(object)
            bad.loc[0, col] = value
            bad_frames.append(bad)
        for bad in bad_frames:
            with self.subTest(columns=list(bad.columns)), self.assertRaises(DataError):
                normalize_csv(encoded(bad), 2025)

    def test_scope_exclusions_are_counted(self):
        base = fixture()
        post = base.head(1).copy()
        post['season_type'] = 'POST'
        frame, quality = normalize_csv(encoded(pd.concat([base, post])), 2025)
        self.assertEqual(len(frame), 4)
        self.assertEqual(quality['excluded_scope_rows'], 1)

    def test_idempotent_publication_and_failed_input_preserves_pointer(self):
        payload = encoded(fixture())
        metadata = {'season': 2025, 'sha256': hashlib.sha256(payload).hexdigest(), 'source_url': 'fixture'}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            first = publish(payload, metadata, output)
            second = publish(payload, metadata, output)
            self.assertEqual(first['normalized_sha256'], second['normalized_sha256'])
            pointer = (output / 'current_2025.json').read_bytes()
            with self.assertRaises(DataError):
                publish(b'invalid\n', metadata, output)
            self.assertEqual(pointer, (output / 'current_2025.json').read_bytes())
            csv_path = output / first['normalized_path']
            partitions = list(csv_path.parent.glob('week=*/*.parquet'))
            self.assertEqual(sum(len(pd.read_parquet(p)) for p in partitions), 4)

    def test_bundled_snapshot_checksum_and_counts(self):
        root = Path(__file__).resolve().parents[1] / 'data'
        if not (root / 'current_2025.json').is_file():
            self.skipTest('Local 2025 snapshot is not available; run ingestion first')
        manifest = json.loads((root / 'current_2025.json').read_text())
        payload = (root / manifest['normalized_path']).read_bytes()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), manifest['normalized_sha256'])
        frame, _ = normalize_csv(payload, 2025)
        self.assertEqual(len(frame), manifest['quality']['accepted_rows'])
        self.assertEqual(frame.week.nunique(), 18)

if __name__ == '__main__':
    unittest.main()
