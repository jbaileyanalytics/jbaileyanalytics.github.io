"""Fetch one forecast or replay a saved validated capture into PostgreSQL."""
import argparse
import json
from pathlib import Path
import sys
import uuid

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT/'src'))
from forecast import fetch, normalize
from storage import save_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--location', default='CHI')
    parser.add_argument('--snapshot', type=Path, help='Replay a previously captured file, e.g. /app/results/captures/....json')
    args = parser.parse_args()
    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit('Install project requirements or use the Docker pipeline container.') from exc
    if args.snapshot:
        envelope = json.loads(args.snapshot.read_text(encoding='utf-8'))
        token = uuid.UUID(envelope['capture_token'])
        snapshot = normalize(envelope['location'], envelope['payload'],
                             __import__('datetime').datetime.fromisoformat(envelope['retrieved_at_utc']))
    else:
        locations = json.loads((PROJECT/'config/locations.example.json').read_text(encoding='utf-8'))
        selected = [v for v in locations if v['location_code'] == args.location]
        if len(selected) != 1: parser.error('location must identify exactly one configured location')
        payload, retrieved = fetch(selected[0])
        snapshot = normalize(selected[0], payload, retrieved)
        token = uuid.uuid4()
        captures = PROJECT/'results/captures'
        captures.mkdir(parents=True, exist_ok=True)
        path = captures/(str(token)+'.json')
        with path.open('x', encoding='utf-8') as stream:
            json.dump({'capture_token':str(token), 'location':selected[0], 'retrieved_at_utc':retrieved.isoformat(),
                       'payload':payload}, stream, indent=2)
            stream.write('\n')
        print(f'Capture retained at {path}', flush=True)
    # libpq receives credentials through PG* environment variables; never print them.
    with psycopg.connect() as connection:
        result = save_snapshot(connection, snapshot, token)
    print(json.dumps({'capture_token':str(token), 'location_code':snapshot['location']['location_code'], **result}))


if __name__ == '__main__':
    main()
