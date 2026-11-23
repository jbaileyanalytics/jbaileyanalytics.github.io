import importlib.util
from datetime import date
from decimal import Decimal
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('analytics', Path(__file__).resolve().parents[1] / 'src/analytics.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(day, opening, high, low, close):
    return {'date': date.fromisoformat(day), **{k: Decimal(str(v)) if v is not None else None
            for k, v in [('open', opening), ('high', high), ('low', low), ('close', close)]}}


class AnalyticsTests(unittest.TestCase):
    def test_ytd_and_anniversary_use_prior_available_close(self):
        rows = [row('2023-12-29', 100, 101, 99, 100), row('2024-01-02', 100, 111, 99, 110),
                row('2024-12-31', 110, 122, 108, 120)]
        result = module.analyze(rows, 'abc')
        self.assertEqual(Decimal(result['returns']['YTD']['percent']), Decimal(20))
        self.assertEqual(result['returns']['YTD']['baseline_date'], '2023-12-29')
        self.assertIsNone(result['returns']['3 years']['percent'])

    def test_stale_baseline_and_missing_endpoint_are_not_returns(self):
        rows = [row('2023-12-01', 10, 11, 9, 10), row('2024-12-31', 10, 12, 9, 11)]
        self.assertIsNone(module.price_return(rows, date(2023, 12, 31), rows[-1])['percent'])
        rows[-1]['close'] = None
        self.assertEqual(module.price_return(rows, date(2023, 12, 1), rows[-1])['reason'], 'ending close unavailable')

    def test_weekly_ohlc_uses_boundaries_and_does_not_hide_missing_values(self):
        rows = [row('2024-01-01', None, 12, 9, 11), row('2024-01-02', 11, 14, 10, 13)]
        week = module.period_prices(rows, 'weekly')[0]
        self.assertIsNone(week['open'])
        self.assertEqual((week['high'], week['low'], week['close']), ('14', '9', '13'))
        self.assertTrue(week['period_ends_after_latest_observation'])
        rows[1]['high'] = None
        self.assertIsNone(module.period_prices(rows, 'weekly')[0]['high'])

    def test_52_week_window_and_leap_year(self):
        rows = [row('2023-03-02', 10, 20, 8, 10), row('2023-03-03', 10, 14, 9, 12),
                row('2024-02-29', 12, 16, 11, 14)]
        result = module.analyze(rows, 'abc')
        self.assertEqual(result['range_52_weeks']['start_exclusive'], '2023-03-02')
        self.assertEqual(result['range_52_weeks']['high'], '16')
        self.assertEqual(module.shift_months(date(2024, 2, 29), -12), date(2023, 2, 28))


if __name__ == '__main__':
    unittest.main()
