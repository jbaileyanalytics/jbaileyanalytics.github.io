"""Assemble a Pages artifact from tracked public assets and a stock candidate."""
import argparse
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
STOCK_PATH = Path('projects/stock-market-analytics/website')
PUBLIC_DIRS = ('assets/css/', 'assets/js/', 'assets/webfonts/', 'assets/resume/', 'images/',
               'case-studies/', 'scripts/', 'output/pdf/')
PUBLIC_FILES = {
    'projects/ecommerce-domain/lakehouse/README.md',
    'projects/ecommerce-domain/lakehouse/DATA_MODEL.md',
    'projects/healthcare-analytics/README.md',
    'projects/healthcare-analytics/databricks/README.md',
    'projects/weather-api-pipeline/sql/distribution_weather_outlook.sql',
    'projects/weather-api-pipeline/docs/weather-data-model.svg',
    'projects/nfl-analytics/website/index.html',
    'projects/nfl-analytics/website/styles.css',
    'projects/nfl-analytics/website/app.js',
    'projects/nfl-analytics/website/data/2025.json',
    'projects/nfl-analytics/website/data/2026.json',
    'projects/nfl-analytics/website/data/seasons.json',
}
PUBLIC_EXTENSIONS = {'.html', '.css', '.js', '.svg', '.png', '.jpg', '.jpeg',
                     '.webp', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.eot', '.pdf'}


def allowed(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or any(part.startswith('.') for part in path.parts):
        return False
    if name in PUBLIC_FILES:
        return True
    return path.suffix.lower() in PUBLIC_EXTENSIONS and (
        len(path.parts) == 1 and path.suffix.lower() == '.html'
        or any(name.startswith(prefix) for prefix in PUBLIC_DIRS))


def assemble(repository, candidate, output, nfl_data=None):
    repository, candidate, output = (Path(p).resolve() for p in (repository, candidate, output))
    if output.exists():
        raise FileExistsError('Choose a new artifact directory')
    if not (candidate / 'index.html').is_file() or not (candidate / 'data/market-overview.json').is_file():
        raise ValueError('Stock candidate is incomplete')
    tracked = subprocess.check_output(['git', '-C', str(repository), 'ls-files', '-z']).decode('utf-8').split('\0')
    output.mkdir(parents=True)
    count = 0
    for name in tracked:
        if not name or not allowed(name):
            continue
        if nfl_data and name.startswith('projects/nfl-analytics/website/data/'):
            continue
        source = repository / Path(name)
        if source.is_symlink() or not source.is_file():
            raise ValueError(f'Tracked public file is missing or is a symlink: {name}')
        destination = output / Path(name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        count += 1
    if not (output / 'index.html').is_file():
        raise ValueError('Tracked portfolio homepage is missing')
    homepage = (output / 'index.html').read_text(encoding='utf-8')
    if 'assets/resume/John-Bailey-II-Resume.pdf' in homepage and not (output / 'assets/resume/John-Bailey-II-Resume.pdf').is_file():
        raise ValueError('Homepage resume PDF is not tracked; review and add it before deploying')
    if 'projects/nfl-analytics/website/' in homepage:
        nfl_root = output / 'projects/nfl-analytics/website'
        if any(not (nfl_root / file).is_file() for file in ('index.html', 'styles.css', 'app.js')):
            raise ValueError('Homepage NFL dashboard files or approved season snapshots are not tracked')
        source = Path(nfl_data).resolve() if nfl_data else nfl_root / 'data'
        if not (source / 'seasons.json').is_file():
            raise ValueError('NFL season index is missing')
        index = json.loads((source / 'seasons.json').read_text(encoding='utf-8'))
        if not isinstance(index, list) or not index:
            raise ValueError('NFL season index is empty')
        season_ids = [item['season'] for item in index]
        if any(type(year) is not int or not 1999 <= year <= 2100 for year in season_ids) or len(set(season_ids)) != len(season_ids):
            raise ValueError('NFL season index contains an invalid or duplicate season')
        if any(not (source / f'{year}.json').is_file() for year in season_ids):
            raise ValueError('NFL season index refers to a missing snapshot')
        if nfl_data:
            # Only copy the explicit season index and files it names.
            destination = nfl_root / 'data'
            destination.mkdir(parents=True, exist_ok=True)
            for name in ['seasons.json', *(f'{year}.json' for year in season_ids)]:
                shutil.copy2(source / name, destination / name)
    stock_destination = output / STOCK_PATH
    stock_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(candidate, stock_destination)
    (output / '.nojekyll').touch()
    print(f'Assembled {count} tracked portfolio files and the stock dashboard.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, default=ROOT)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--nfl-data', type=Path, help='Validated NFL data to include in the Pages artifact')
    args = parser.parse_args()
    assemble(args.repository, args.candidate, args.output, args.nfl_data)
