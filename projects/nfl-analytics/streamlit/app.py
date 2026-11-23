"""Real nflverse weekly statistics, reproducible offline snapshot, no app-time scraping."""
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import altair as alt
import pandas as pd
import streamlit as st

from pipeline import DataError, FOCUS, POSITIONS, aggregate_players, weekly_metrics
from warehouse import analyze_snapshot

ROOT = Path(__file__).resolve().parent
DATA = PROJECT_ROOT / 'data'
st.set_page_config(page_title='NFL Analytics | Player Performance', layout='wide')
st.markdown(f'<style>{(ROOT / "styles.css").read_text()}</style>', unsafe_allow_html=True)

def show_chart(value, height=220):
    value = value.properties(height=height, background='#1c2637').configure_view(stroke=None).configure_axis(
        labelColor='#a9bed5', titleColor='#a9bed5', gridColor='#304057', domain=False,
        tickColor='#304057', labelFontSize=11, labelPadding=8
    ).configure_legend(labelColor='#b9cde4', titleColor='#b9cde4', labelFontSize=11)
    st.altair_chart(value, width='stretch', theme=None)

with st.sidebar:
    st.markdown('<div class="brand"><span>4Q</span><div>NFL ANALYTICS<small>PLAYER PERFORMANCE LAB</small></div></div>', unsafe_allow_html=True)
    source = st.selectbox('Data source', ['nflverse snapshot', 'Upload player-week CSV'])
    focus = st.selectbox('Analysis focus', list(FOCUS), key='focus')
    config = FOCUS[focus]

st.markdown('<div class="eyebrow">SPORTS DATA ENGINEERING / OFFENSIVE PLAYER ANALYTICS</div><div class="hero"><h1>Volume. Efficiency. Production.</h1><p>Explore player usage, compare performance, and trace every result to a validated weekly snapshot.</p></div>', unsafe_allow_html=True)

manifest = None
if source == 'Upload player-week CSV':
    uploaded = st.file_uploader('nflverse-format player-week CSV · UTF-8 · up to 15 MB', type=['csv'])
    if uploaded is None:
        st.info('Upload a player-week CSV or select the included nflverse snapshot.')
        st.stop()
    if uploaded.size > 15 * 1024 * 1024:
        st.error('Input rejected. Maximum CSV size is 15 MB.')
        st.stop()
    payload = uploaded.getvalue()
else:
    manifests = sorted(DATA.glob('current_*.json'), reverse=True)
    if not manifests:
        st.info('No local snapshot found. Run ingest.py --season 2025 to create one.')
        st.stop()
    with st.sidebar:
        season_file = st.selectbox('Season', manifests, format_func=lambda p: p.stem.replace('current_', ''), key='snapshot')
    try:
        manifest = json.loads(season_file.read_text(encoding='utf-8'))
        csv_path = (DATA / manifest['normalized_path']).resolve()
        if not csv_path.is_relative_to(DATA.resolve()):
            raise DataError('Snapshot path is outside the data directory')
        payload = csv_path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != manifest['normalized_sha256']:
            raise DataError('Snapshot checksum mismatch; rerun ingestion before analysis')
    except (OSError, KeyError, ValueError) as exc:
        st.error(f'Snapshot could not be verified: {exc}')
        st.stop()

try:
    frame, quality = analyze_snapshot(payload, expected_season=manifest['season'] if manifest else None)
except DataError as exc:
    st.error(f'Data validation failed: {exc}')
    st.stop()

with st.sidebar:
    season = int(manifest['season']) if manifest else st.selectbox('Season', sorted(frame['season'].unique(), reverse=True), key='season')
    frame = frame[frame['season'] == season]
    lo, hi = int(frame['week'].min()), int(frame['week'].max())
    if lo == hi:
        weeks = (lo, hi)
        st.caption(f'Available week: {lo}')
    else:
        weeks = st.slider('Week range', lo, hi, (lo, hi), key=f'weeks_{season}')
    teams = st.multiselect('Teams', sorted(frame['team'].unique()), default=[], help='Leave empty to include every team.')
    defaults = ['QB'] if focus == 'Passing' else ['RB', 'QB', 'WR', 'TE'] if focus == 'Rushing' else ['WR', 'TE', 'RB']
    positions = st.multiselect('Positions', POSITIONS, default=defaults, key=f'positions_{focus}')
    minimum = st.number_input(f'Minimum {config["label"].lower()}', min_value=1, max_value=1000, value=30, step=5, key=f'minimum_{focus}')
    st.caption('Minimum applies across the selected weeks and teams. It defines the player cohort used by all overview charts and KPIs.')

scoped = frame[frame['week'].between(*weeks) & frame['position'].isin(positions)]
if teams:
    scoped = scoped[scoped['team'].isin(teams)]
players = aggregate_players(scoped, focus, minimum)
if players.empty:
    st.info('No players qualify. Lower the minimum or expand the weeks, teams, and positions.')
    st.stop()
cohort = scoped[scoped['player_id'].isin(players['player_id'])].copy()
volume = int(players['opportunities'].sum())
yards = int(players['yards'].sum())
weighted_efficiency = yards / volume
context = f'nflverse public snapshot · season {season}' if manifest else f'Uploaded dataset · season {season}'
today_utc = datetime.now(timezone.utc).date()
current_season = date(season, 7, 1) <= today_utc < date(season + 1, 3, 1)
season_note = 'IN-PROGRESS SEASON · SNAPSHOT MAY BE INCOMPLETE' if current_season else 'HISTORICAL SNAPSHOT'
st.markdown(f'<div class="context">{escape(context)} &nbsp; / &nbsp; {season_note} &nbsp; / &nbsp; REGULAR SEASON &nbsp; / &nbsp; WEEKS {weeks[0]}–{weeks[1]} &nbsp; / &nbsp; {focus.upper()} COHORT</div>', unsafe_allow_html=True)
cols = st.columns(4, gap='small')
for col, key, label, value, caption in [
    (cols[0], 'players', 'Qualifying players', f'{len(players):,}', f'At least {minimum} {config["label"].lower()}'),
    (cols[1], 'volume', config['label'], f'{volume:,}', 'Selected cohort · selected weeks'),
    (cols[2], 'yards', f'{focus} yards', f'{yards:,}', 'Selected discipline only'),
    (cols[3], 'efficiency', config['efficiency'], f'{weighted_efficiency:.2f}', 'Total yards / total opportunities')]:
    with col, st.container(key=f'kpi_{key}', border=True):
        st.metric(label, value)
        st.caption(caption)

overview, compare, leaders, provenance = st.tabs(['Performance overview', 'Player comparison', 'Leaderboard', 'Data & methodology'])
with overview:
    trend_col, ranking_col = st.columns([1.4, 1], gap='medium')
    with trend_col, st.container(border=True):
        st.subheader('Weekly efficiency')
        st.caption(f'{config["efficiency"]} · fixed qualifying cohort across the selected weeks')
        weekly = weekly_metrics(cohort, focus)
        line = alt.Chart(weekly).mark_line(color='#66d9c2', strokeWidth=2.5, point=True).encode(
            x=alt.X('week:O', title='NFL week', axis=alt.Axis(labelAngle=0)),
            y=alt.Y('yards_per_opportunity:Q', title=config['efficiency'], scale=alt.Scale(zero=True)),
            tooltip=['week:O', 'opportunities:Q', 'yards:Q', alt.Tooltip('yards_per_opportunity:Q', format='.2f')])
        show_chart(line)
    with ranking_col, st.container(border=True):
        st.subheader(f'{focus} yardage leaders')
        st.caption('Top ten qualifying players · selected scope')
        top = players.head(10).copy()
        top['Player'] = top['player_display_name'] + ' · ' + top['team']
        bars = alt.Chart(top).mark_bar(color='#a89af7', cornerRadiusEnd=3, size=13).encode(
            x=alt.X('yards:Q', title='Yards'), y=alt.Y('Player:N', sort='-x', title=None, axis=alt.Axis(labelLimit=175)),
            tooltip=['player_display_name:N', 'teams_in_scope:N', 'opportunities:Q', 'yards:Q'])
        show_chart(bars)
    scatter_col, team_col = st.columns([1.4, 1], gap='medium')
    with scatter_col, st.container(border=True):
        st.subheader('Opportunity vs. efficiency')
        st.caption(f'Each point is a player · dashed line: selected cohort average ({weighted_efficiency:.2f} {config["efficiency"].lower()})')
        scatter = alt.Chart(players).mark_circle(opacity=.75).encode(
            x=alt.X('opportunities:Q', title=config['label']),
            y=alt.Y('yards_per_opportunity:Q', title=config['efficiency']),
            size=alt.Size('observed_weeks:Q', scale=alt.Scale(range=[35, 200]), legend=None),
            color=alt.Color('position:N', scale=alt.Scale(range=['#66d9c2', '#a89af7', '#e9bc75', '#6ebce9']), legend=alt.Legend(title=None, orient='bottom')),
            tooltip=['player_display_name:N', 'position:N', 'teams_in_scope:N', 'opportunities:Q', 'yards:Q', alt.Tooltip('yards_per_opportunity:Q', format='.2f')])
        # Use the ratio of cohort totals, not an unweighted average of player rates.
        benchmark = alt.Chart(pd.DataFrame({'benchmark': [weighted_efficiency]})).mark_rule(
            color='#d7e1ef', strokeDash=[5, 5], strokeWidth=1.5, opacity=.8
        ).encode(y=alt.Y('benchmark:Q'))
        show_chart(scatter + benchmark)
        st.caption('Point size reflects observed player-weeks. The benchmark changes with the filters and minimum workload.')
    with team_col, st.container(border=True):
        st.subheader('Cohort opportunity by team')
        st.caption('Contributions from qualifying players · not full team totals')
        team = cohort.groupby('team')[config['opportunities']].sum().reset_index(name='Opportunities').sort_values('Opportunities', ascending=False).head(10)
        bars = alt.Chart(team).mark_bar(color='#6ebce9', size=13, cornerRadiusEnd=3).encode(
            x=alt.X('Opportunities:Q', title=config['label']), y=alt.Y('team:N', sort='-x', title=None), tooltip=['team:N', 'Opportunities:Q'])
        show_chart(bars)

with compare:
    st.subheader('Player comparison')
    name_map = players.set_index('player_id')['player_display_name'].to_dict()
    selected = st.multiselect('Select up to four players', players['player_id'].tolist(),
        default=players['player_id'].head(2).tolist(), max_selections=4,
        format_func=lambda pid: f'{name_map[pid]} · {pid}', key=f'compare_{focus}')
    if selected:
        comparison = players[players['player_id'].isin(selected)]
        weekly_players = cohort[cohort['player_id'].isin(selected)].copy()
        weekly_players['Player'] = weekly_players['player_display_name'] + ' · ' + weekly_players['player_id']
        # Missing weeks remain gaps, not fabricated zero-production observations.
        weeks_index = pd.MultiIndex.from_product([selected, range(weeks[0], weeks[1]+1)], names=['player_id', 'week'])
        weekly_players = weekly_players.set_index(['player_id', 'week']).reindex(weeks_index).reset_index()
        weekly_players['Player'] = weekly_players['player_id'].map(lambda pid: f'{name_map[pid]} · {pid}')
        line = alt.Chart(weekly_players).mark_line(strokeWidth=2.5, point=True, invalid='break-paths-show-domains').encode(
            x=alt.X('week:O', title='NFL week', axis=alt.Axis(labelAngle=0)),
            y=alt.Y(f'{config["yards"]}:Q', title=f'{focus} yards'),
            color=alt.Color('Player:N', scale=alt.Scale(range=['#66d9c2', '#a89af7', '#e9bc75', '#6ebce9']), legend=alt.Legend(title=None, orient='bottom')),
            tooltip=['Player:N', 'week:O', alt.Tooltip(f'{config["yards"]}:Q', title='Yards'), alt.Tooltip(f'{config["opportunities"]}:Q', title=config['label'])])
        show_chart(line, 260)
        st.caption('Gaps indicate no included source observation; they do not distinguish byes, injury, inactivity, or missing data.')
        st.dataframe(comparison[['player_display_name', 'position', 'teams_in_scope', 'observed_weeks', 'opportunities', 'yards', 'touchdowns', 'yards_per_opportunity']],
            hide_index=True, width='stretch')
    else:
        st.info('Select one or more players to compare.')

with leaders:
    st.subheader('Player leaderboard')
    search = st.text_input('Find a player', placeholder='Player name or team abbreviation')
    leaderboard = players.copy()
    if search:
        leaderboard = leaderboard[leaderboard[['player_display_name', 'teams_in_scope']].apply(lambda c: c.str.contains(search, case=False, regex=False)).any(axis=1)]
    columns = ['player_display_name', 'player_id', 'position', 'teams_in_scope', 'observed_weeks', 'opportunities', 'yards', 'touchdowns', 'yards_per_opportunity']
    if focus == 'Receiving':
        columns += ['receptions', 'catch_rate']
    if focus == 'Passing':
        columns += ['completions', 'completion_rate', 'passing_interceptions']
    st.dataframe(leaderboard[columns], hide_index=True, width='stretch')
    st.download_button('Export leaderboard CSV', leaderboard[columns].to_csv(index=False), file_name=f'nfl_{focus.lower()}_{season}.csv', mime='text/csv')

with provenance:
    st.subheader('Source, validation & metric definitions')
    st.write('Source: nflverse contributors, weekly player statistics. Regular season only; QB, RB, WR, and TE. This version uses box-score data, not player-tracking Next Gen Stats, and is not a live feed.')
    if manifest:
        st.caption(f"Retrieved (UTC): {manifest['retrieved_at_utc']} | Source Last-Modified: {manifest.get('source_last_modified', 'Not supplied')}")
        st.json({'season': manifest['season'], 'source_rows': manifest['quality']['source_rows'],
            'included_player_weeks': manifest['quality']['accepted_rows'], 'excluded_scope_rows': manifest['quality']['excluded_scope_rows'],
            'raw_sha256': manifest['sha256'], 'curated_sha256': manifest['normalized_sha256']})
        st.link_button('nflverse source release', manifest['source_url'])
    st.write('Efficiency is total yards divided by total opportunities: attempts for passing, carries for rushing, targets for receiving. Catch rate is receptions / targets; completion rate is completions / attempts. Rates are recomputed from summed numerators and denominators. Zero denominators produce missing rates.')
    st.write('Observed weeks count source player-week rows, not verified games played. A traded player is grouped by player ID; team history is retained. Team filters include only contributions recorded for the selected teams. Cohort charts exclude players below the selected minimum.')
    st.write('Passing yards and receiving yards are separate disciplines and are never added into a league total. Missing player-weeks are not filled with zeroes. Source validation detects duplicate player-week keys, missing identifiers, non-integer stats, negative counts, and impossible completions or receptions.')
    st.write('Limitations: no opponent adjustment, route participation, snap share, injury attribution, forecasts, fantasy scoring, or automated cloud schedule. Historical source corrections require a new explicit ingestion run; previous local content-addressed snapshots are retained.')
    st.download_button('Export selected player-week data', cohort.to_csv(index=False), file_name=f'nfl_player_week_{season}.csv', mime='text/csv')
st.markdown('<div class="footer">NFL ANALYTICS / Data: <a href="https://github.com/nflverse/nflverse-data">nflverse contributors</a> · <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a> · Filtered and transformed for this project. Independent portfolio project; no NFL affiliation.</div>', unsafe_allow_html=True)
