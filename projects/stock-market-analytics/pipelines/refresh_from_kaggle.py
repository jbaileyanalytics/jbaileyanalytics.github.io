"""Download a Kaggle snapshot and rehearse a stock dashboard refresh locally.

This command does not deploy the generated site. Its output may contain data
and machine-specific paths and should stay outside version control.
"""
import argparse
import json
from pathlib import Path

from download_kaggle import download_and_manifest
from prepare_refresh import run as build_refresh


def refresh(downloader, output, minimum_files=400):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('Choose a new output directory')
    if minimum_files < 1:
        raise ValueError('minimum_files must be positive')
    source, _, count = download_and_manifest(downloader, output / 'audit')
    files = list(source.rglob('*.csv'))
    if count < minimum_files:
        raise ValueError(f'Snapshot has {count} CSV files; expected at least {minimum_files}')
    parents = {file.parent for file in files}
    if len(parents) != 1:
        raise ValueError('Expected all stock CSV files in one directory; inspect the dataset layout')
    result = build_refresh(parents.pop(), output / 'candidate')
    if result['stocks'] != count:
        raise ValueError('Number of exported symbols does not match source files')
    return {'source_files': count, 'stocks': result['stocks'], 'market_date': result['market_date']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--minimum-files', type=int, default=400)
    args = parser.parse_args()
    try:
        import kagglehub
    except ImportError as exc:
        raise SystemExit('Install kagglehub before downloading the dataset') from exc
    print(json.dumps(refresh(kagglehub.dataset_download, args.output, args.minimum_files), indent=2))
