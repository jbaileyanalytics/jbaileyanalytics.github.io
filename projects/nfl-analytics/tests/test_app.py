import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from pipeline import normalize_csv, aggregate_players

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'streamlit' / 'app.py'

@unittest.skipUnless((ROOT / 'data/current_2025.json').is_file(), 'Local 2025 snapshot is not available; run ingestion first')
class DashboardTests(unittest.TestCase):
    def test_default_reconciles_to_source(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        if len(app.selectbox(key='snapshot').options) > 1:
            app.selectbox(key='snapshot').select('2025').run()
        self.assertEqual(len(app.exception), 0)
        manifest = json.loads((ROOT / 'data/current_2025.json').read_text())
        frame, _ = normalize_csv((ROOT / 'data' / manifest['normalized_path']).read_bytes(), 2025)
        frame = frame[frame.position.isin(['WR', 'TE', 'RB'])]
        players = aggregate_players(frame, 'Receiving', 30)
        self.assertEqual(app.metric[0].value, f'{len(players):,}')
        self.assertEqual(app.metric[1].value, f"{players['opportunities'].sum():,}")
        self.assertEqual(app.metric[2].value, f"{players['yards'].sum():,}")

    def test_focus_changes_and_empty_cohort(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.selectbox(key='focus').set_value('Passing').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[1].label, 'Pass attempts')
        app.selectbox(key='focus').set_value('Rushing').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[1].label, 'Carries')
        app.multiselect(key='positions_Rushing').set_value([]).run()
        self.assertEqual(len(app.metric), 0)
        self.assertIn('No players qualify', app.info[0].value)

    def test_week_filter_and_upload_wait(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.slider[0].set_value((1, 3)).run()
        self.assertEqual(len(app.exception), 0)
        app.selectbox[0].set_value('Upload player-week CSV').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.metric), 0)

if __name__ == '__main__':
    unittest.main()
