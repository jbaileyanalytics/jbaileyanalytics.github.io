"""Download a Kaggle snapshot on demand and record a local file manifest."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid

HANDLE = 'svaningelgem/nasdaq-daily-stock-prices'
PROJECT = Path(__file__).resolve().parents[1]


def download_and_manifest(downloader, audit_dir):
    """Use a downloader returning a cached dataset directory; never alter it."""
    source = Path(downloader(HANDLE))
    if not source.is_dir():
        raise ValueError(f'Kaggle download did not return a directory: {source}')
    files = sorted(source.rglob('*.csv'))
    if not files:
        raise ValueError(f'No CSV files found in the downloaded dataset: {source}')
    manifest = []
    for file in files:
        digest = hashlib.sha256()
        with file.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        manifest.append({'path': file.relative_to(source).as_posix(),
                         'bytes': file.stat().st_size, 'sha256': digest.hexdigest()})
    now = datetime.now(timezone.utc)
    record = {'dataset': HANDLE, 'observed_at_utc': now.isoformat(),
              'local_directory': str(source.resolve()), 'file_count': len(files), 'files': manifest,
              'note': 'Content inventory only; upstream version and data quality not verified.'}
    audit_dir.mkdir(parents=True, exist_ok=True)
    path = audit_dir / f"{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex}.json"
    with path.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    return source, path, len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-dir', type=Path, default=PROJECT / 'results' / 'acquisitions')
    args = parser.parse_args()
    try:
        import kagglehub
    except ImportError as exc:
        raise SystemExit('Install kagglehub in your Python environment: python -m pip install kagglehub') from exc
    source, manifest, count = download_and_manifest(kagglehub.dataset_download, args.audit_dir)
    print(f'Downloaded snapshot directory: {source}\nCSV files: {count}\nManifest: {manifest}')


if __name__ == '__main__':
    main()
