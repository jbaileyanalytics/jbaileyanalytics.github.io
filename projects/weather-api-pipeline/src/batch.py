"""Process configured locations and record run outcomes in PostgreSQL."""
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid
from urllib.error import HTTPError

from forecast import fetch, normalize
from storage import save_snapshot

PROJECT = Path(__file__).resolve().parents[1]
LOCK_ID = 284973530113


def log(event, **fields):
    print(json.dumps({'event': event, **fields}, default=str), flush=True)


def safe_error(exc):
    # Avoid leaking environment variables or connection credentials into audit logs.
    return f'{type(exc).__name__}' + (f' HTTP {exc.code}' if isinstance(exc, HTTPError) else '')


def validate_locations(locations):
    if not isinstance(locations, list) or not locations:
        raise ValueError('configuration must contain at least one location')
    codes = [location.get('location_code') for location in locations if isinstance(location, dict)]
    if len(codes) != len(locations) or any(not isinstance(code, str) or not code.strip() for code in codes) or len(set(codes)) != len(codes):
        raise ValueError('location codes must be nonempty and unique')


def run_batch(connect, locations, capture_dir=PROJECT/'results/captures', fetcher=fetch):
    validate_locations(locations)
    token = uuid.uuid4()
    run_id = None
    acquired = False
    with connect(autocommit=True) as control:
        with control.cursor() as cursor:
            cursor.execute('SELECT pg_try_advisory_lock(%s)', (LOCK_ID,))
            acquired = cursor.fetchone()[0]
            if not acquired:
                cursor.execute('''INSERT INTO pipeline_run(run_token,started_at_utc,finished_at_utc,status,locations_total,error_message)
                                  VALUES (%s,now(),now(),'skipped_overlap',%s,'Another run holds the pipeline lock')''', (token, len(locations)))
                log('run_skipped_overlap', run_token=token)
                return {'status':'skipped_overlap','run_token':str(token),'succeeded':0,'failed':0,'rows':0}
            cursor.execute("UPDATE pipeline_run SET status='failed', finished_at_utc=now(), error_message='Previous run interrupted' WHERE status='running'")
            cursor.execute("INSERT INTO pipeline_run(run_token,started_at_utc,status,locations_total) VALUES (%s,now(),'running',%s) RETURNING pipeline_run_id", (token,len(locations)))
            run_id = cursor.fetchone()[0]
        succeeded = failed = rows = 0
        try:
            for location in locations:
                code, capture_token = location['location_code'], None
                try:
                    payload, retrieved = fetcher(location)
                    snapshot = normalize(location, payload, retrieved)
                    capture_token = uuid.uuid4()
                    capture_dir.mkdir(parents=True, exist_ok=True)
                    path = capture_dir / (str(capture_token)+'.json')
                    with path.open('x', encoding='utf-8') as stream:
                        json.dump({'capture_token':str(capture_token),'location':location,
                                   'retrieved_at_utc':retrieved.isoformat(),'payload':payload},stream,indent=2)
                        stream.write('\n')
                    with connect() as connection:
                        result = save_snapshot(connection, snapshot, capture_token)
                        with connection.cursor() as cursor:
                            cursor.execute('''INSERT INTO pipeline_run_location(pipeline_run_id,location_code,status,capture_token,forecast_snapshot_id,rows_loaded)
                                              VALUES (%s,%s,'succeeded',%s,%s,%s)''',
                                           (run_id,code,capture_token,result['forecast_snapshot_id'],result['hours']))
                    succeeded += 1
                    rows += result['hours']
                    log('location_succeeded',run_token=token,location=code,hours=result['hours'],capture_token=capture_token)
                except Exception as exc:
                    failed += 1
                    error = safe_error(exc)
                    with control.cursor() as cursor:
                        cursor.execute("INSERT INTO pipeline_run_location(pipeline_run_id,location_code,status,capture_token,error_message) VALUES (%s,%s,'failed',%s,%s)", (run_id,code,capture_token,error))
                    log('location_failed',run_token=token,location=code,error=error,capture_token=capture_token)
            status = 'succeeded' if not failed else 'partial' if succeeded else 'failed'
            with control.cursor() as cursor:
                cursor.execute('''UPDATE pipeline_run SET finished_at_utc=now(),status=%s,locations_succeeded=%s,
                                  locations_failed=%s,rows_loaded=%s WHERE pipeline_run_id=%s''', (status,succeeded,failed,rows,run_id))
            result = {'status':status,'run_token':str(token),'succeeded':succeeded,'failed':failed,'rows':rows}
            log('run_finished',**result)
            return result
        except BaseException as exc:
            try:
                with control.cursor() as cursor:
                    cursor.execute("UPDATE pipeline_run SET finished_at_utc=now(),status='failed',error_message=%s WHERE pipeline_run_id=%s", (safe_error(exc),run_id))
            except Exception:
                pass
            raise
        finally:
            if acquired:
                try:
                    with control.cursor() as cursor:
                        cursor.execute('SELECT pg_advisory_unlock(%s)', (LOCK_ID,))
                except Exception:
                    pass
