"""Build an isolated stock-site preview from a supplied CSV snapshot.

This does not download data, publish, schedule a job, or preserve database IDs
between builds. Run in a new directory to inspect and validate a candidate build.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.is_dir():
        raise ValueError('The source snapshot directory does not exist')
    if output.exists():
        raise FileExistsError('Choose a new output directory; existing builds are never overwritten')
    if not list(source.glob('*.csv')):
        raise ValueError('No CSV files found directly in the source directory')
    output.mkdir(parents=True)
    database = output / 'market-data.sqlite'
    reporting = output / 'reporting'
    preview = output / 'site'
    commands = [
        ['build_local.py', '--source', str(source), '--output', str(database)],
        ['export_reporting.py', '--database', str(database), '--output', str(reporting)],
        ['export_market_overview.py', '--database', str(database), '--output', str(reporting / 'website' / 'market-overview.json')],
        ['prepare_static_site.py', '--source', str(reporting / 'website'), '--output', str(preview)],
    ]
    for script, *args in commands:
        subprocess.run([sys.executable, str(ROOT / 'pipelines' / script), *args], check=True)
    index = json.loads((preview / 'data/stocks.json').read_text(encoding='utf-8'))
    overview = json.loads((preview / 'data/market-overview.json').read_text(encoding='utf-8'))
    if not index or not overview.get('stocks'):
        raise ValueError('Candidate site has no stocks or market overview')
    return {'stocks': len(index), 'market_date': overview['date'], 'site': str(preview)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output), indent=2))
