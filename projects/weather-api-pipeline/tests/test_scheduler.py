from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src'))
spec=importlib.util.spec_from_file_location('scheduler',PROJECT/'pipelines/scheduler.py')
scheduler=importlib.util.module_from_spec(spec)
spec.loader.exec_module(scheduler)

class SchedulerTests(unittest.TestCase):
    def test_central_noon_schedule_follows_daylight_saving(self):
        central = ZoneInfo('America/Chicago')
        self.assertEqual(scheduler.next_run(datetime(2026, 3, 7, 19, 0, tzinfo=timezone.utc), '12:30', central), datetime(2026, 3, 8, 17, 30, tzinfo=timezone.utc))
        self.assertEqual(scheduler.next_run(datetime(2026, 10, 31, 19, 0, tzinfo=timezone.utc), '12:30', central), datetime(2026, 11, 1, 18, 30, tzinfo=timezone.utc))
    def test_next_run_uses_utc_and_rolls_to_next_day(self):
        self.assertEqual(scheduler.next_run(datetime(2026,11,18,12,59,tzinfo=timezone.utc),'13:00'),datetime(2026,11,18,13,tzinfo=timezone.utc))
        self.assertEqual(scheduler.next_run(datetime(2026,11,18,13,tzinfo=timezone.utc),'13:00'),datetime(2026,11,19,13,tzinfo=timezone.utc))
    def test_invalid_schedules_and_naive_time_rejected(self):
        for value in ('25:00','1:00','12:99','noon'):
            with self.subTest(value=value), self.assertRaises(ValueError): scheduler.next_run(datetime.now(timezone.utc),value)
        with self.assertRaises(ValueError): scheduler.next_run(datetime(2026,1,1),'13:00')

    def test_scheduler_waits_until_target_then_executes(self):
        class StopAfterRun:
            stopped=False
            def is_set(self): return self.stopped
            def wait(self, seconds):
                self.seconds=seconds
                return False
        stop=StopAfterRun()
        calls=[]
        def execute():
            calls.append('run')
            stop.stopped=True
        scheduler.run_schedule(stop,'13:00',execute,lambda: datetime(2026,11,18,12,59,tzinfo=timezone.utc))
        self.assertEqual(stop.seconds,60)
        self.assertEqual(calls,['run'])

if __name__=='__main__': unittest.main()
