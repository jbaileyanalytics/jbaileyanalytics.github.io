"""Prepare a local, self-contained GitHub Pages preview; do not publish it."""
import argparse
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results' / 'reporting-v1' / 'website'
DEFAULT = ROOT / 'results' / 'public-preview'
FILES = ('index.html', 'styles.css', 'app.js', 'market-overview.js')

def prepare(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('Output already exists; choose a new destination')
    index = json.loads((source/'stocks.json').read_text(encoding='utf-8'))
    overview = json.loads((source/'market-overview.json').read_text(encoding='utf-8'))
    if not index or not overview.get('stocks'):
        raise ValueError('Stock index or market overview is empty')
    data = output/'data'
    try:
        data.mkdir(parents=True, exist_ok=False)
        for filename in FILES:
            text = (ROOT/'website'/filename).read_text(encoding='utf-8')
            if filename in ('app.js','market-overview.js'):
                text = text.replace('../results/reporting-v1/website/', 'data/')
            if filename == 'index.html':
                text = text.replace('HISTORICAL DATA · LOCAL DEMONSTRATION',
                                    'HISTORICAL DATA · PORTFOLIO DEMONSTRATION')
            (output/filename).write_text(text,encoding='utf-8')
        shutil.copy2(source/'stocks.json', data/'stocks.json')
        shutil.copy2(source/'market-overview.json', data/'market-overview.json')
        (data/'stocks').mkdir()
        for item in index:
            relative = Path(item['data_file'])
            if relative.is_absolute() or len(relative.parts) != 2 or relative.parts[0] != 'stocks' or relative.suffix != '.json':
                raise ValueError('Unexpected stock data path')
            shutil.copy2(source/relative, data/relative)
        return {'stocks':len(index), 'files':len(list(data.rglob('*.json'))),
                'data_bytes':sum(p.stat().st_size for p in data.rglob('*.json')),
                'session_date':overview['date'], 'destination':str(output)}
    except BaseException:
        # Leave an incomplete output for inspection instead of deleting a user path.
        print('Preview build did not finish; the output directory may be incomplete.')
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, default=DEFAULT)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source,args.output),indent=2))
