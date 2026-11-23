from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

path = Path(__file__).resolve().parents[1] / 'src/forecast.py'
spec = importlib.util.spec_from_file_location('forecast', path)
forecast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forecast)

LOCATION = {'location_code':'CHI','latitude':41.8781,'longitude':-87.6298}
PAYLOAD = {'latitude':41.879498,'longitude':-87.64974,'timezone':'GMT','utc_offset_seconds':0,
           'hourly_units':dict(forecast.UNITS),
           'hourly':{'time':['2026-11-18T00:00','2026-11-18T01:00'], 'temperature_2m':[6.6, None],
                     'precipitation_probability':[0,20], 'precipitation':[0.0,0.1], 'wind_speed_10m':[6.8,5.1]}}
NOW = datetime(2026,11,18,tzinfo=timezone.utc)


class ForecastTests(unittest.TestCase):
    def test_normalizes_utc_preserves_null_and_returned_coordinates(self):
        result = forecast.normalize(LOCATION, PAYLOAD, NOW)
        self.assertEqual(result['hours'][0]['valid_at_utc'], '2026-11-18T00:00:00+00:00')
        self.assertIsNone(result['hours'][1]['temperature_2m'])
        self.assertIsNone(result['forecast_issue_time'])
        self.assertNotEqual(result['returned_longitude'], LOCATION['longitude'])

    def test_rejects_bad_units_length_time_and_probability(self):
        for mutate in (
            lambda p: p['hourly_units'].__setitem__('temperature_2m', '°F'),
            lambda p: p['hourly']['wind_speed_10m'].pop(),
            lambda p: p['hourly']['time'].__setitem__(1, '2026-11-18T02:00'),
            lambda p: p['hourly']['precipitation_probability'].__setitem__(0, 101),
            lambda p: p.__setitem__('utc_offset_seconds', 3600),
        ):
            payload = deepcopy(PAYLOAD)
            mutate(payload)
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                forecast.normalize(LOCATION, payload, NOW)

    def test_rejects_naive_retrieval_time(self):
        with self.assertRaises(ValueError):
            forecast.normalize(LOCATION, PAYLOAD, datetime(2026,11,18))

    def test_retry_is_bounded_and_client_errors_are_not_retried(self):
        with patch.object(forecast, 'urlopen', side_effect=URLError('offline')) as request, patch.object(forecast.time, 'sleep'):
            with self.assertRaises(URLError):
                forecast.fetch(LOCATION, attempts=3)
            self.assertEqual(request.call_count, 3)
        with patch.object(forecast, 'urlopen', side_effect=HTTPError('url', 400, 'bad request', {}, None)) as request:
            with self.assertRaises(HTTPError):
                forecast.fetch(LOCATION, attempts=3)
            self.assertEqual(request.call_count, 1)


if __name__ == '__main__':
    unittest.main()
