"""Fetch and validate one Open-Meteo forecast without requiring a database."""
from datetime import datetime, timedelta, timezone
import json
import math
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ENDPOINT = 'https://api.open-meteo.com/v1/forecast'
FIELDS = ('temperature_2m', 'precipitation_probability', 'precipitation', 'wind_speed_10m')
UNITS = {'time':'iso8601', 'temperature_2m':'°C', 'precipitation_probability':'%',
         'precipitation':'mm', 'wind_speed_10m':'km/h'}


def fetch(location, timeout=15, attempts=3):
    if attempts < 1:
        raise ValueError('attempts must be at least one')
    params = {'latitude': location['latitude'], 'longitude': location['longitude'],
              'hourly': ','.join(FIELDS), 'forecast_days': 2, 'timezone': 'GMT',
              'temperature_unit': 'celsius', 'wind_speed_unit': 'kmh', 'precipitation_unit': 'mm'}
    request = Request(ENDPOINT + '?' + urlencode(params), headers={'User-Agent': 'WeatherPortfolioPipeline/1.0'})
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
            return payload, datetime.now(timezone.utc)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
        except (URLError, TimeoutError):
            if attempt == attempts - 1:
                raise
        time.sleep(min(2 ** attempt, 4))


def normalize(location, payload, retrieved_at):
    """Return validated hourly rows. The retrieval time is not a model issue time."""
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise ValueError('retrieval timestamp must include a timezone')
    if not isinstance(payload, dict) or payload.get('error'):
        raise ValueError('provider returned an error or non-object payload')
    if payload.get('utc_offset_seconds') != 0 or payload.get('timezone') not in ('GMT', 'UTC'):
        raise ValueError('forecast timestamps must be returned in UTC')
    units, hourly = payload.get('hourly_units'), payload.get('hourly')
    if not isinstance(units, dict) or any(units.get(k) != v for k, v in UNITS.items()):
        raise ValueError('missing or unexpected hourly units')
    if not isinstance(hourly, dict) or not all(isinstance(hourly.get(k), list) for k in ('time', *FIELDS)):
        raise ValueError('missing hourly arrays')
    count = len(hourly['time'])
    if not count or any(len(hourly[k]) != count for k in FIELDS):
        raise ValueError('hourly arrays must be nonempty and equal length')
    rows, previous = [], None
    for i, timestamp in enumerate(hourly['time']):
        try:
            valid = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc)
        except (ValueError, TypeError) as exc:
            raise ValueError('invalid hourly timestamp') from exc
        if previous is not None and valid != previous + timedelta(hours=1):
            raise ValueError('hourly timestamps must be unique, ordered, and consecutive')
        previous = valid
        values = {}
        for field in FIELDS:
            value = hourly[field][i]
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError(f'invalid numeric value for {field} at {timestamp}')
            if value is not None and ((field == 'precipitation_probability' and not 0 <= value <= 100) or
                                      (field in ('precipitation', 'wind_speed_10m') and value < 0)):
                raise ValueError(f'out-of-range value for {field} at {timestamp}')
            values[field] = value
        rows.append({'valid_at_utc': valid.isoformat(), **values})
    for key, low, high in [('latitude', -90, 90), ('longitude', -180, 180)]:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'invalid returned {key}')
    return {'location': location, 'retrieved_at_utc': retrieved_at.astimezone(timezone.utc).isoformat(),
            'provider': 'Open-Meteo', 'returned_latitude': payload['latitude'],
            'returned_longitude': payload['longitude'], 'units': dict(UNITS),
            'forecast_issue_time': None, 'hours': rows}
