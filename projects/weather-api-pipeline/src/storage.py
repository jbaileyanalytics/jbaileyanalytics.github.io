"""Transactionally store one validated forecast snapshot in PostgreSQL."""
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo


def number(value):
    return None if value is None else Decimal(str(value))


def save_snapshot(connection, snapshot, capture_token):
    """Store once per capture token; reject reuse with different content.

    The caller owns the transaction. No commits occur inside this function.
    """
    location = snapshot['location']
    ZoneInfo(location['timezone'])
    loc_values = (location['location_code'], location['name'], number(location['latitude']),
                  number(location['longitude']), location['timezone'])
    with connection.cursor() as cursor:
        cursor.execute('''INSERT INTO dim_location(location_code,name,requested_latitude,requested_longitude,display_timezone)
                          VALUES (%s,%s,%s,%s,%s) ON CONFLICT(location_code) DO NOTHING''', loc_values)
        cursor.execute('''SELECT location_id,name,requested_latitude,requested_longitude,display_timezone
                          FROM dim_location WHERE location_code=%s FOR UPDATE''', (location['location_code'],))
        row = cursor.fetchone()
        if row is None or row[1:] != loc_values[1:]:
            raise ValueError('Existing location configuration differs; changes require explicit handling')
        location_id = row[0]
        retrieved = datetime.fromisoformat(snapshot['retrieved_at_utc'])
        if retrieved.tzinfo is None or retrieved.utcoffset() is None:
            raise ValueError('retrieval time must have a timezone')
        metadata = (location_id, retrieved, number(snapshot['returned_latitude']),
                    number(snapshot['returned_longitude']), snapshot['provider'], None)
        cursor.execute('''INSERT INTO forecast_snapshot(location_id,capture_token,retrieved_at_utc,returned_latitude,
                           returned_longitude,provider,forecast_issue_time) VALUES (%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT(capture_token) DO NOTHING RETURNING forecast_snapshot_id''',
                       (metadata[0], capture_token, *metadata[1:]))
        inserted = cursor.fetchone()
        values = [(datetime.fromisoformat(hour['valid_at_utc']), number(hour['temperature_2m']),
                   number(hour['precipitation_probability']), number(hour['precipitation']), number(hour['wind_speed_10m']))
                  for hour in snapshot['hours']]
        if not inserted:
            cursor.execute('''SELECT forecast_snapshot_id,location_id,retrieved_at_utc,returned_latitude,
                              returned_longitude,provider,forecast_issue_time FROM forecast_snapshot WHERE capture_token=%s''', (capture_token,))
            existing = cursor.fetchone()
            if existing is None or existing[1:] != metadata:
                raise ValueError('Capture token is already associated with a different snapshot')
            cursor.execute('''SELECT valid_at_utc,temperature_c,precipitation_probability_pct,precipitation_mm,wind_speed_kmh
                              FROM fact_hourly_forecast WHERE forecast_snapshot_id=%s ORDER BY valid_at_utc''', (existing[0],))
            if cursor.fetchall() != values:
                raise ValueError('Capture token is already associated with different hourly data')
            return {'status':'already_loaded', 'forecast_snapshot_id':existing[0], 'hours':len(values)}
        snapshot_id = inserted[0]
        cursor.executemany('''INSERT INTO fact_hourly_forecast(forecast_snapshot_id,location_id,valid_at_utc,
                              temperature_c,precipitation_probability_pct,precipitation_mm,wind_speed_kmh)
                              VALUES (%s,%s,%s,%s,%s,%s,%s)''', [(snapshot_id, location_id, *v) for v in values])
        return {'status':'loaded', 'forecast_snapshot_id':snapshot_id, 'hours':len(values)}
