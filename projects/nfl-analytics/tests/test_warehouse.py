import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import sqlite3
import unittest
from pathlib import Path
import pandas as pd
from pipeline import COUNTS,YARDS,DataError,normalize_csv,aggregate_players
from test_pipeline import fixture,encoded
from warehouse import connect_model,load_snapshot,read_snapshot

ROOT=Path(__file__).resolve().parents[1]

class ModelTests(unittest.TestCase):
    def setUp(self):
        self.conn=connect_model()
        self.payload=encoded(fixture())

    def tearDown(self):
        self.conn.close()

    def test_all_source_fields_and_totals_survive_joins(self):
        key,quality=load_snapshot(self.conn,self.payload,2025)
        expected,_=normalize_csv(self.payload,2025)
        pd.testing.assert_frame_equal(read_snapshot(self.conn,key),expected)
        self.assertEqual(quality['accepted_rows'],4)
        self.assertEqual(self.conn.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_bundled_snapshot_reconciles_and_sql_rates_match(self):
        if not (ROOT/'data/current_2025.json').is_file():
            self.skipTest('Local 2025 snapshot is not available; run ingestion first')
        manifest=json.loads((ROOT/'data/current_2025.json').read_text())
        payload=(ROOT/'data'/manifest['normalized_path']).read_bytes()
        key,_=load_snapshot(self.conn,payload,2025)
        frame,_=normalize_csv(payload,2025)
        actual=read_snapshot(self.conn,key)
        pd.testing.assert_frame_equal(actual,frame)
        self.assertEqual(len(actual),manifest['quality']['accepted_rows'])
        self.assertEqual(actual.player_id.nunique(),manifest['quality']['players'])
        reference=aggregate_players(frame,'Receiving',1).set_index('player_id')
        for row in self.conn.execute('SELECT * FROM v_player_season_totals WHERE snapshot_key=? AND targets>0',(key,)):
            self.assertAlmostEqual(row['yards_per_target'],reference.loc[row['player_id'],'yards_per_opportunity'])

    def test_trade_context_and_parameterized_filters(self):
        key,_=load_snapshot(self.conn,self.payload)
        first=read_snapshot(self.conn,key,teams=['AAA'],positions=['WR'],week_start=1,week_end=2)
        self.assertEqual(first.receiving_yards.sum(),124)
        totals=self.conn.execute("SELECT * FROM v_player_season_totals WHERE player_id='A'").fetchone()
        self.assertEqual(totals['receiving_yards'],110)
        self.assertAlmostEqual(totals['yards_per_target'],110/12)
        self.assertTrue(read_snapshot(self.conn,key,teams=["AAA' OR 1=1 --"]).empty)
        self.assertTrue(read_snapshot(self.conn,key,positions=[]).empty)

    def test_identical_reruns_reuse_snapshot_and_dimensions(self):
        first,_=load_snapshot(self.conn,self.payload)
        shuffled=encoded(fixture().iloc[::-1])
        second,_=load_snapshot(self.conn,shuffled)
        self.assertEqual(first,second)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM fact_player_week').fetchone()[0],4)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM dim_player').fetchone()[0],3)

    def test_revision_preserves_observed_profiles_and_prior_results(self):
        first,_=load_snapshot(self.conn,self.payload)
        revised=fixture()
        revised.loc[revised.player_id=='A','player_display_name']='Revised display name'
        revised.loc[0,'receiving_yards']=101
        second,_=load_snapshot(self.conn,encoded(revised))
        self.assertNotEqual(first,second)
        self.assertEqual(read_snapshot(self.conn,first).receiving_yards.sum(),134)
        self.assertEqual(read_snapshot(self.conn,second).receiving_yards.sum(),135)
        self.assertEqual(read_snapshot(self.conn,first).iloc[0].player_display_name,'Fixture Receiver A')
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM dim_player').fetchone()[0],3)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM dim_player_profile').fetchone()[0],4)

    def test_negative_yards_and_missing_denominators(self):
        key,_=load_snapshot(self.conn,self.payload)
        qb=self.conn.execute("SELECT * FROM v_player_season_totals WHERE player_id='Q'").fetchone()
        self.assertEqual(qb['yards_per_carry'],-.5)
        self.assertIsNone(qb['yards_per_target'])
        self.assertEqual(read_snapshot(self.conn,key).rushing_yards.sum(),-1)

    def test_invalid_load_and_mid_load_failure_leave_no_partial_rows(self):
        with self.assertRaises(DataError):
            load_snapshot(self.conn,self.payload,2024)
        self.conn.executescript("CREATE TRIGGER fail_test BEFORE INSERT ON fact_player_week BEGIN SELECT RAISE(ABORT,'test failure'); END;")
        with self.assertRaises(sqlite3.IntegrityError):
            load_snapshot(self.conn,self.payload)
        for table in ['model_snapshot','dim_player','dim_player_profile','dim_team','dim_season_week','fact_player_week']:
            self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0,table)

    def test_constraints_reject_orphans_duplicates_and_wrong_profile(self):
        key,_=load_snapshot(self.conn,self.payload)
        for update in ['team_key=99999','profile_key=99999','receptions=targets+1','attempts=-1']:
            with self.assertRaises(sqlite3.IntegrityError),self.conn:
                self.conn.execute('UPDATE fact_player_week SET '+update)
        with self.assertRaises(sqlite3.IntegrityError),self.conn:
            self.conn.execute('INSERT INTO fact_player_week SELECT * FROM fact_player_week WHERE snapshot_key=?',(key,))
        wrong=self.conn.execute("SELECT profile_key FROM dim_player_profile WHERE player_display_name='Fixture Receiver B'").fetchone()[0]
        with self.assertRaises(sqlite3.IntegrityError),self.conn:
            self.conn.execute('UPDATE fact_player_week SET profile_key=? WHERE player_key=(SELECT player_key FROM dim_player WHERE player_id=?)',(wrong,'A'))

    def test_seasons_and_week_numbers_are_distinct(self):
        both=pd.concat([fixture(),fixture().assign(season=2024)],ignore_index=True)
        key,_=load_snapshot(self.conn,encoded(both))
        self.assertEqual(len(read_snapshot(self.conn,key,season=2024)),4)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM dim_season_week').fetchone()[0],4)

if __name__=='__main__':
    unittest.main()
