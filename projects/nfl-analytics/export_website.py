"""Prepare local browser data from checksum-verified NFL snapshots."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
OUTPUT = ROOT / 'website' / 'data'
FIELDS = ['player_id', 'player_display_name', 'position', 'season', 'week', 'team',
          'opponent_team', 'attempts', 'completions', 'passing_yards', 'passing_tds', 'passing_interceptions',
          'carries', 'rushing_yards', 'rushing_tds', 'targets', 'receptions',
          'receiving_yards', 'receiving_tds']


def export():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    seasons = []
    for pointer in sorted(DATA.glob('current_*.json')):
        manifest = json.loads(pointer.read_text(encoding='utf-8'))
        source = (DATA / manifest['normalized_path']).resolve()
        if not source.is_relative_to(DATA.resolve()):
            raise ValueError('Snapshot path outside project data directory')
        payload = source.read_bytes()
        if hashlib.sha256(payload).hexdigest() != manifest['normalized_sha256']:
            raise ValueError('Snapshot checksum mismatch')
        rows = list(csv.DictReader(payload.decode('utf-8-sig').splitlines()))
        if not rows or any(key not in rows[0] for key in FIELDS):
            raise ValueError('Snapshot is empty or missing fields')
        if len(rows) != manifest['quality']['accepted_rows']:
            raise ValueError('Snapshot count does not match manifest')
        records = [[int(row[key]) if key in FIELDS[3:5] or key in FIELDS[7:] else row[key] for key in FIELDS] for row in rows]
        season = int(manifest['season'])
        if any(row[3] != season for row in records):
            raise ValueError('Unexpected season in snapshot')
        (OUTPUT / f'{season}.json').write_text(json.dumps({'fields': FIELDS, 'records': records}, separators=(',', ':')), encoding='utf-8')
        seasons.append({'season': season, 'weeks': manifest['quality']['weeks'], 'players': manifest['quality']['players'],
                        'records': len(records), 'retrieved_at_utc': manifest['retrieved_at_utc'],
                        'normalized_sha256': manifest['normalized_sha256'], 'source_url': manifest['source_url']})
    if not seasons:
        raise ValueError('No local season snapshots found')
    (OUTPUT / 'seasons.json').write_text(json.dumps(seasons, separators=(',', ':')), encoding='utf-8')
    print(json.dumps([{'season': s['season'], 'records': s['records']} for s in seasons]))


if __name__ == '__main__':
    export()
