"""Preserve published NFL snapshots and optionally refresh the current season.

Writes an isolated Pages input directory. It does not publish or change the
tracked snapshots. A failed source refresh retains the verified baseline.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from export_website import FIELDS
from fetch_source import download
from pipeline import normalize_csv

ROOT = Path(__file__).resolve().parent
PUBLISHED = 'https://jbaileyanalytics.github.io/projects/nfl-analytics/website/data/'
MAX_BYTES = 15 * 1024 * 1024


def read_url(url):
    request = Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'NFLPlayerAnalytics-refresh/1.0'})
    with urlopen(request, timeout=30) as response:
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError('Published NFL file exceeds the size limit')
    return json.loads(payload)


def load_published():
    try:
        index = read_url(PUBLISHED + 'seasons.json')
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    validate_index(index)
    return index, {item['season']: read_url(PUBLISHED + str(item['season']) + '.json') for item in index}


def validate_index(index):
    if not isinstance(index, list) or not index:
        raise ValueError('NFL season index is empty')
    seen = set()
    for item in index:
        season = item.get('season')
        if type(season) is not int or not 1999 <= season <= 2100 or season in seen:
            raise ValueError('Invalid or duplicate NFL season')
        seen.add(season)


def validate_snapshot(meta, snapshot):
    if snapshot.get('fields') != FIELDS or not isinstance(snapshot.get('records'), list):
        raise ValueError('NFL snapshot has an unexpected schema')
    rows = snapshot['records']
    if not rows or len(rows) != meta.get('records'):
        raise ValueError('NFL snapshot row count does not match its index')
    seen, weeks, players = set(), set(), set()
    for row in rows:
        if not isinstance(row, list) or len(row) != len(FIELDS):
            raise ValueError('NFL snapshot contains an invalid row')
        record = dict(zip(FIELDS, row))
        if (record['season'] != meta['season'] or type(record['week']) is not int or
                not 1 <= record['week'] <= 18 or not record['player_id'] or
                record['position'] not in ('QB', 'RB', 'WR', 'TE')):
            raise ValueError('NFL snapshot contains an invalid player-week')
        if any(type(record[field]) is not int for field in FIELDS[7:]):
            raise ValueError('NFL snapshot contains a non-integer statistic')
        key = (record['player_id'], record['week'])
        if key in seen:
            raise ValueError('NFL snapshot has duplicate player-week records')
        seen.add(key); weeks.add(record['week']); players.add(record['player_id'])
    if sorted(weeks) != meta.get('weeks') or len(players) != meta.get('players'):
        raise ValueError('NFL snapshot coverage does not match its index')


def load_repo_data():
    directory = ROOT / 'website/data'
    index = json.loads((directory / 'seasons.json').read_text(encoding='utf-8'))
    validate_index(index)
    return index, {item['season']: json.loads((directory / f"{item['season']}.json").read_text(encoding='utf-8')) for item in index}


def current_season(now):
    return now.year if now.month >= 7 else now.year - 1


def candidate_snapshot(season, downloader):
    payload, metadata = downloader(season)
    frame, quality = normalize_csv(payload, expected_season=season)
    normalized = frame.to_csv(index=False, lineterminator='\n').encode('utf-8')
    records = [[int(row[field]) if field in FIELDS[3:5] or field in FIELDS[7:] else row[field]
                for field in FIELDS] for row in frame.to_dict('records')]
    meta = {'season': season, 'weeks': quality['weeks'], 'players': quality['players'],
            'records': len(records), 'retrieved_at_utc': metadata['retrieved_at_utc'],
            'normalized_sha256': hashlib.sha256(normalized).hexdigest(), 'source_url': metadata['source_url']}
    snapshot = {'fields': FIELDS, 'records': records}
    validate_snapshot(meta, snapshot)
    return meta, snapshot


def check_regression(previous, candidate):
    if max(candidate['weeks']) < max(previous['weeks']):
        raise ValueError('New NFL snapshot ends before the current published snapshot')
    if not set(previous['weeks']).issubset(candidate['weeks']):
        raise ValueError('New NFL snapshot omits previously published weeks')
    if candidate['records'] < previous['records'] * 0.90 or candidate['players'] < previous['players'] * 0.90:
        raise ValueError('New NFL snapshot has substantially less coverage')


def prepare(output, refresh=False, loader=load_published, downloader=download, now=None):
    output = Path(output)
    if output.exists():
        raise FileExistsError('NFL output already exists')
    previous = loader()
    index, snapshots = previous if previous is not None else load_repo_data()
    validate_index(index)
    for meta in index:
        validate_snapshot(meta, snapshots[meta['season']])
    status = 'preserved published snapshots' if previous is not None else 'used repository snapshots for first deployment'
    if refresh:
        season = current_season(now or datetime.now(ZoneInfo('America/Chicago')))
        try:
            meta, snapshot = candidate_snapshot(season, downloader)
            existing = next((item for item in index if item['season'] == season), None)
            if existing:
                check_regression(existing, meta)
            index = [item for item in index if item['season'] != season] + [meta]
            snapshots[season] = snapshot
            status = f'refreshed {season} through week {max(meta["weeks"])}'
        except Exception as exc:
            # Do not substitute repository files for a previously published snapshot.
            status = f'refresh failed; baseline preserved: {type(exc).__name__}: {exc}'
            print('::warning::NFL refresh failed; the previously verified baseline will be retained.')
    output.mkdir(parents=True)
    for meta in index:
        season = meta['season']
        (output / f'{season}.json').write_text(json.dumps(snapshots[season], separators=(',', ':')), encoding='utf-8')
    (output / 'seasons.json').write_text(json.dumps(sorted(index, key=lambda x: x['season']), separators=(',', ':')), encoding='utf-8')
    return {'status': status, 'seasons': sorted(item['season'] for item in index)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    print(json.dumps(prepare(args.output, args.refresh), indent=2))
