"""Download an explicit nflverse season snapshot; does not run during app startup."""
import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent

def download(season):
    if not 1999 <= season <= datetime.now(timezone.utc).year:
        raise ValueError('Season must be between 1999 and the current UTC year')
    url = f'https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{season}.csv'
    request = urllib.request.Request(url, headers={'User-Agent': 'JohnBailey-NFLPortfolio/1.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read(30 * 1024 * 1024 + 1)
                if len(payload) > 30 * 1024 * 1024:
                    raise ValueError('Source exceeds the 30 MB download limit')
                return payload, {'season': season, 'source_url': url,
                    'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                    'source_last_modified': response.headers.get('Last-Modified'),
                    'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)}
        except urllib.error.HTTPError as exc:
            if exc.code < 500 or attempt == 2:
                raise
        except urllib.error.URLError:
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--season', required=True, type=int)
    args = parser.parse_args()
    payload, metadata = download(args.season)
    raw = ROOT / 'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    target = raw / f'player_week_{args.season}_{metadata["sha256"][:12]}.csv'
    target.write_bytes(payload)
    target.with_suffix('.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(json.dumps({'file': str(target), **metadata}, indent=2))
