"""Fetch and validate a single forecast; print a small, non-persistent summary."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'src'))
from forecast import fetch, normalize

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--location', default='CHI')
parser.add_argument('--locations', type=Path, default=PROJECT / 'config/locations.example.json')
args = parser.parse_args()
locations = json.loads(args.locations.read_text(encoding='utf-8'))
matches = [item for item in locations if item['location_code'] == args.location]
if len(matches) != 1:
    parser.error('location must identify exactly one configured location')
payload, retrieved_at = fetch(matches[0])
snapshot = normalize(matches[0], payload, retrieved_at)
print(json.dumps({'location': snapshot['location']['name'], 'retrieved_at_utc': snapshot['retrieved_at_utc'],
                  'returned_coordinates': [snapshot['returned_latitude'], snapshot['returned_longitude']],
                  'units': snapshot['units'], 'hours': len(snapshot['hours']),
                  'first_hour': snapshot['hours'][0], 'last_hour': snapshot['hours'][-1]}, indent=2))
