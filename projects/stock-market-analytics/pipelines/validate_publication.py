"""Guard a stock candidate against empty coverage and published-date regression."""
import argparse
from datetime import date
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

PUBLISHED = 'https://jbaileyanalytics.github.io/projects/stock-market-analytics/website/data/market-overview.json'


def validate(candidate, previous=None):
    overview = json.loads((Path(candidate) / 'data/market-overview.json').read_text(encoding='utf-8'))
    index = json.loads((Path(candidate) / 'data/stocks.json').read_text(encoding='utf-8'))
    current_date = date.fromisoformat(overview['date'])
    total = len(index)
    if total < 400 or overview['total_symbols'] != total:
        raise ValueError('Candidate symbol count is too small or inconsistent')
    if overview['observed_symbols'] != len(overview['stocks']) or overview['eligible_symbols'] != sum(s.get('change_pct') is not None for s in overview['stocks']) or overview['eligible_symbols'] < total * 0.90:
        raise ValueError('Candidate has insufficient eligible market coverage')
    if overview['previous_close_eligible_symbols'] != sum(s.get('previous_close_change_pct') is not None for s in overview['stocks']):
        raise ValueError('Candidate previous-close coverage is inconsistent')
    if previous is not None:
        if current_date < date.fromisoformat(previous['date']):
            raise ValueError('Candidate market date is older than the published dashboard')
        if total < int(previous['total_symbols']) * 0.90:
            raise ValueError('Candidate has substantially fewer symbols than the published dashboard')
    return {'market_date': current_date.isoformat(), 'symbols': total,
            'eligible': len(overview['stocks']), 'compared_to_published': previous is not None}


def load_previous(url=PUBLISHED):
    request = Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'MarketScope-refresh-check'})
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.candidate, load_previous()), indent=2))
