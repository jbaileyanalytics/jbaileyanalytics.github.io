"""Fetch or backfill one explicit season and publish a validated local snapshot."""
import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from fetch_source import download
from pipeline import normalize_csv

ROOT = Path(__file__).parent

def publish(payload, metadata, output):
    frame, quality = normalize_csv(payload, expected_season=metadata['season'])
    normalized = frame.to_csv(index=False, lineterminator='\n').encode('utf-8')
    digest = hashlib.sha256(normalized).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    # Immutable-by-convention content-addressed snapshots; current pointer moves last.
    snapshot = output / 'snapshots' / f'season={metadata["season"]}' / digest
    snapshot.mkdir(parents=True, exist_ok=True)
    csv_path = snapshot / 'player_week.csv'
    if csv_path.exists():
        if hashlib.sha256(csv_path.read_bytes()).hexdigest() != digest:
            raise ValueError('Existing content-addressed snapshot is corrupt; refusing to overwrite')
    else:
        csv_path.write_bytes(normalized)
    for week, partition in frame.groupby('week'):
        target = snapshot / f'week={int(week):02d}'
        target.mkdir(exist_ok=True)
        if not (target / 'player_stats.parquet').exists():
            partition.to_parquet(target / 'player_stats.parquet', index=False)
    manifest = {**metadata, 'quality': quality, 'normalized_sha256': digest,
        'normalized_path': csv_path.relative_to(output).as_posix(),
        'published_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'REG only; QB/RB/WR/TE; selected columns; integer validation; sorted player-week keys',
        'attribution': 'nflverse contributors', 'license': 'CC-BY-4.0',
        'license_url': 'https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md'}
    (snapshot / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', dir=output, delete=False, encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2)
        pointer = stream.name
    os.replace(pointer, output / f'current_{metadata["season"]}.json')
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--raw-file', type=Path)
    args = parser.parse_args()
    if args.raw_file:
        payload = args.raw_file.read_bytes()
        metadata = json.loads(args.raw_file.with_suffix('.json').read_text(encoding='utf-8'))
        if metadata['season'] != args.season or metadata['sha256'] != hashlib.sha256(payload).hexdigest():
            raise ValueError('Raw file metadata does not match the requested season or checksum')
    else:
        payload, metadata = download(args.season)
        raw = ROOT / 'data/raw'
        raw.mkdir(parents=True, exist_ok=True)
        path = raw / f'player_week_{args.season}_{metadata["sha256"][:12]}.csv'
        path.write_bytes(payload)
        path.with_suffix('.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps(publish(payload, metadata, ROOT / 'data'), indent=2))
