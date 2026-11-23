"""Run all configured weather locations once or daily at a configured local time."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import signal
import sys
import threading
from zoneinfo import ZoneInfo

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src'))
from batch import log, run_batch, safe_error


def next_run(now, schedule, schedule_timezone=timezone.utc):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('current time must have a timezone')
    parts = schedule.split(':')
    if len(parts)!=2 or any(len(p)!=2 or not p.isdigit() for p in parts):
        raise ValueError('schedule must use HH:MM')
    hour, minute = map(int,parts)
    if hour > 23 or minute > 59:
        raise ValueError('schedule must be a valid time')
    current = now.astimezone(schedule_timezone)
    target = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= current:
        target = target + timedelta(days=1)
    return target.astimezone(timezone.utc)


def run_schedule(stop, schedule, execute, now_fn=lambda: datetime.now(timezone.utc), schedule_timezone=timezone.utc):
    while not stop.is_set():
        now = now_fn()
        target = next_run(now,schedule,schedule_timezone)
        log('next_run',scheduled_at_utc=target.isoformat())
        if stop.wait(max(0,(target-now).total_seconds())):
            break
        execute()


def main():
    import os
    import psycopg
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once',action='store_true')
    args = parser.parse_args()
    locations = json.loads((PROJECT/'config/locations.example.json').read_text(encoding='utf-8'))
    def execute():
        try:
            result = run_batch(psycopg.connect, locations)
            return 0 if result['status'] in ('succeeded','skipped_overlap') else 1
        except Exception as exc:
            # If PostgreSQL is unavailable, no database audit record can be written.
            log('run_failed_before_audit_or_unexpected',error=safe_error(exc))
            return 1
    if args.once:
        return execute()
    schedule = os.environ.get('WEATHER_RUN_LOCAL','12:30')
    schedule_timezone = ZoneInfo('America/Chicago')
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    run_schedule(stop,schedule,execute,schedule_timezone=schedule_timezone)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
