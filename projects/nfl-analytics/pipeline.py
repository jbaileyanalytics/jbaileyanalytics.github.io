"""Validate weekly offensive box scores and calculate denominator-weighted metrics."""
import io
import pandas as pd

IDENTIFIERS = ['player_id', 'player_display_name', 'position', 'season', 'week', 'season_type', 'game_id', 'team', 'opponent_team']
COUNTS = ['completions', 'attempts', 'passing_tds', 'passing_interceptions', 'carries', 'rushing_tds', 'targets', 'receptions', 'receiving_tds']
YARDS = ['passing_yards', 'rushing_yards', 'receiving_yards']
FIELDS = IDENTIFIERS + COUNTS + YARDS
POSITIONS = ['QB', 'RB', 'WR', 'TE']
FOCUS = {
    'Receiving': {'opportunities': 'targets', 'yards': 'receiving_yards', 'tds': 'receiving_tds', 'label': 'Targets', 'efficiency': 'Yards / target'},
    'Rushing': {'opportunities': 'carries', 'yards': 'rushing_yards', 'tds': 'rushing_tds', 'label': 'Carries', 'efficiency': 'Yards / carry'},
    'Passing': {'opportunities': 'attempts', 'yards': 'passing_yards', 'tds': 'passing_tds', 'label': 'Pass attempts', 'efficiency': 'Yards / attempt'},
}

class DataError(ValueError):
    pass

def normalize_csv(payload, expected_season=None):
    try:
        frame = pd.read_csv(io.BytesIO(payload), dtype=str, keep_default_na=False, encoding='utf-8-sig')
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise DataError('Input must be a valid UTF-8 CSV') from exc
    missing = sorted(set(FIELDS) - set(frame.columns))
    if missing:
        raise DataError('Missing required columns: ' + ', '.join(missing))
    frame = frame[FIELDS].copy()
    for col in IDENTIFIERS:
        frame[col] = frame[col].str.strip()
    raw_count = len(frame)
    # Filtering is intentional scope selection, not silent rejection of bad offensive rows.
    frame = frame[(frame['season_type'] == 'REG') & frame['position'].isin(POSITIONS)].copy()
    if frame.empty:
        raise DataError('No regular-season QB/RB/WR/TE player-week rows found')
    if frame[IDENTIFIERS].eq('').any().any():
        raise DataError('Required identifiers must not be blank')
    for col in ['season', 'week'] + COUNTS + YARDS:
        values = pd.to_numeric(frame[col], errors='coerce')
        if values.isna().any() or not values.between(-100000, 100000).all() or (values % 1 != 0).any():
            raise DataError(f'{col} must contain finite integer values')
        frame[col] = values.astype('int64')
    if not frame['week'].between(1, 18).all():
        raise DataError('Regular-season weeks must be between 1 and 18')
    if not frame['season'].between(1999, 2100).all():
        raise DataError('Season is outside supported bounds')
    if expected_season is not None and not frame['season'].eq(expected_season).all():
        raise DataError('Input contains an unexpected season')
    if (frame[COUNTS] < 0).any().any():
        raise DataError('Counts must be nonnegative; yardage may be negative')
    if (frame['completions'] > frame['attempts']).any():
        raise DataError('Completions cannot exceed attempts')
    if (frame['receptions'] > frame['targets']).any():
        raise DataError('Receptions cannot exceed targets')
    if frame.duplicated(['season', 'season_type', 'week', 'player_id']).any():
        raise DataError('Duplicate season/type/week/player key')
    frame = frame.sort_values(['season', 'week', 'player_id']).reset_index(drop=True)
    return frame, {'source_rows': raw_count, 'accepted_rows': len(frame), 'excluded_scope_rows': raw_count - len(frame),
        'players': int(frame['player_id'].nunique()), 'weeks': sorted(map(int, frame['week'].unique())),
        'positions': POSITIONS, 'season_type': 'REG'}

def aggregate_players(frame, focus, minimum=0):
    config = FOCUS[focus]
    if frame.empty:
        return pd.DataFrame()
    totals = frame.groupby('player_id', sort=False)[COUNTS + YARDS].sum()
    # Team reflects the latest selected observation; history preserves traded-player context.
    latest = frame.sort_values(['season', 'week']).groupby('player_id', sort=False).tail(1).set_index('player_id')
    totals = totals.join(latest[['player_display_name', 'position', 'team']])
    totals['teams_in_scope'] = frame.groupby('player_id')['team'].agg(lambda x: ', '.join(sorted(set(x))))
    totals['observed_weeks'] = frame.groupby('player_id').size()
    totals['opportunities'] = totals[config['opportunities']]
    totals['yards'] = totals[config['yards']]
    totals['touchdowns'] = totals[config['tds']]
    totals['yards_per_opportunity'] = totals['yards'].div(totals['opportunities'].where(totals['opportunities'] != 0))
    totals['yards_per_observed_week'] = totals['yards'] / totals['observed_weeks']
    totals['catch_rate'] = totals['receptions'].div(totals['targets'].where(totals['targets'] != 0))
    totals['completion_rate'] = totals['completions'].div(totals['attempts'].where(totals['attempts'] != 0))
    return totals[(totals['opportunities'] >= minimum) & (totals['opportunities'] > 0)].reset_index().sort_values(
        ['yards', 'player_id'], ascending=[False, True]).reset_index(drop=True)

def weekly_metrics(frame, focus):
    config = FOCUS[focus]
    grouped = frame.groupby(['season', 'week'])[[config['opportunities'], config['yards']]].sum().reset_index()
    grouped = grouped.rename(columns={config['opportunities']: 'opportunities', config['yards']: 'yards'})
    grouped['yards_per_opportunity'] = grouped['yards'].div(grouped['opportunities'].where(grouped['opportunities'] != 0))
    return grouped
