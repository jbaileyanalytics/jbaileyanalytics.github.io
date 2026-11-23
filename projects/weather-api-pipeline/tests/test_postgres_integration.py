"""Integration tests run only against the disposable Docker test database."""
from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src'))
from forecast import normalize
from storage import save_snapshot
from batch import LOCK_ID, run_batch
from test_forecast import PAYLOAD

@unittest.skipUnless(os.environ.get('WEATHER_INTEGRATION_DB')=='1', 'requires disposable PostgreSQL test service')
class PostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        self.psycopg=psycopg
        self.location={'location_code':'TEST-'+uuid.uuid4().hex[:8], 'name':'Test location',
                       'latitude':41.8781,'longitude':-87.6298,'timezone':'America/Chicago'}
        self.when=datetime(2026,11,18,tzinfo=timezone.utc)
        self.snapshot=normalize(self.location,deepcopy(PAYLOAD),self.when)

    def test_transactional_replay_conflict_and_constraints(self):
        token=uuid.uuid4()
        with self.psycopg.connect() as db: first=save_snapshot(db,self.snapshot,token)
        with self.psycopg.connect() as db: second=save_snapshot(db,self.snapshot,token)
        self.assertEqual(first['status'],'loaded')
        self.assertEqual(second['status'],'already_loaded')
        altered=deepcopy(self.snapshot); altered['hours'][0]['temperature_2m']=99
        with self.assertRaises(ValueError):
            with self.psycopg.connect() as db: save_snapshot(db,altered,token)
        with self.psycopg.connect() as db:
            with db.cursor() as c:
                c.execute('SELECT count(*) FROM fact_hourly_forecast WHERE forecast_snapshot_id=%s',(first['forecast_snapshot_id'],))
                self.assertEqual(c.fetchone()[0],2)
        with self.assertRaises(self.psycopg.errors.CheckViolation):
            with self.psycopg.connect() as db:
                with db.cursor() as c:
                    c.execute('UPDATE fact_hourly_forecast SET precipitation_probability_pct=101 WHERE forecast_snapshot_id=%s',(first['forecast_snapshot_id'],))
        with self.psycopg.connect() as db:
            with db.cursor() as c:
                c.execute('SELECT count(*) FROM fact_hourly_forecast WHERE forecast_snapshot_id=%s',(first['forecast_snapshot_id'],))
                self.assertEqual(c.fetchone()[0],2)

    def test_partial_failure_is_recorded_and_other_location_loads(self):
        other=deepcopy(self.location); other['location_code'] += '-FAIL'
        def fake(location):
            if location is other: raise TimeoutError('public API unavailable')
            return deepcopy(PAYLOAD),self.when
        with tempfile.TemporaryDirectory() as tmp:
            result=run_batch(self.psycopg.connect,[self.location,other],Path(tmp),fake)
            recovered=run_batch(self.psycopg.connect,[self.location,other],Path(tmp),lambda _: (deepcopy(PAYLOAD),self.when))
        self.assertEqual((result['status'],result['succeeded'],result['failed'],result['rows']),('partial',1,1,2))
        self.assertEqual((recovered['status'],recovered['succeeded'],recovered['failed'],recovered['rows']),('succeeded',2,0,4))
        with self.psycopg.connect() as db:
            with db.cursor() as c:
                c.execute('SELECT status, locations_succeeded, locations_failed FROM pipeline_run WHERE run_token=%s',(uuid.UUID(result['run_token']),))
                self.assertEqual(c.fetchone(),('partial',1,1))
                c.execute('SELECT status,count(*) FROM pipeline_run_location WHERE pipeline_run_id=(SELECT pipeline_run_id FROM pipeline_run WHERE run_token=%s) GROUP BY status',(uuid.UUID(result['run_token']),))
                self.assertEqual(dict(c.fetchall()),{'succeeded':1,'failed':1})

    def test_overlapping_run_is_skipped(self):
        with self.psycopg.connect(autocommit=True) as lock:
            with lock.cursor() as c: c.execute('SELECT pg_advisory_lock(%s)',(LOCK_ID,))
            try:
                result=run_batch(self.psycopg.connect,[self.location],fetcher=lambda _: self.fail('must not fetch'))
                self.assertEqual(result['status'],'skipped_overlap')
            finally:
                with lock.cursor() as c: c.execute('SELECT pg_advisory_unlock(%s)',(LOCK_ID,))

    def test_database_unavailable_surfaces_error(self):
        def unavailable(**kwargs): raise ConnectionError('offline')
        with self.assertRaises(ConnectionError): run_batch(unavailable,[self.location])

if __name__=='__main__': unittest.main()
