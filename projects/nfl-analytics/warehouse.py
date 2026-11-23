"""Local player-week dimensional model; no network calls or automatic disk storage."""
import argparse
import hashlib
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from pipeline import FIELDS, COUNTS, YARDS, DataError, normalize_csv

ROOT = Path(__file__).parent

def connect_model(path=':memory:'):
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        version=conn.execute('PRAGMA user_version').fetchone()[0]
        if version==0:
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table'").fetchone():
                raise DataError('Refusing to initialize a database containing existing tables')
            conn.executescript('BEGIN;\n'+(ROOT/'model/schema.sql').read_text()+'\nPRAGMA user_version=1; COMMIT;')
        elif version!=1:
            raise DataError('Unsupported NFL model version')
        return conn
    except Exception:
        conn.close()
        raise

def load_snapshot(conn,payload,expected_season=None):
    if conn.in_transaction or not conn.execute('PRAGMA foreign_keys').fetchone()[0]:
        raise DataError('Load requires foreign keys enabled and no active transaction')
    frame,quality=normalize_csv(payload,expected_season)
    canonical=frame.to_csv(index=False,lineterminator='\n').encode('utf-8')
    digest=hashlib.sha256(canonical).hexdigest()
    previous=conn.execute('SELECT snapshot_key FROM model_snapshot WHERE canonical_sha256=?',(digest,)).fetchone()
    if previous:
        return previous[0],quality
    with conn:
        snapshot=conn.execute('''INSERT INTO model_snapshot(canonical_sha256,first_payload_sha256,accepted_rows,loaded_at_utc)
            VALUES (?,?,?,?)''',(digest,hashlib.sha256(payload).hexdigest(),len(frame),datetime.now(timezone.utc).isoformat())).lastrowid
        for pid in sorted(frame.player_id.unique()):
            conn.execute('INSERT OR IGNORE INTO dim_player(player_id) VALUES (?)',(pid,))
        players={r['player_id']:r['player_key'] for r in conn.execute('SELECT * FROM dim_player')}
        for row in frame[['player_id','player_display_name','position']].drop_duplicates().itertuples(index=False):
            conn.execute('INSERT OR IGNORE INTO dim_player_profile(player_key,player_display_name,position) VALUES (?,?,?)',
                         (players[row.player_id],row.player_display_name,row.position))
        profiles={(r['player_key'],r['player_display_name'],r['position']):r['profile_key'] for r in conn.execute('SELECT * FROM dim_player_profile')}
        for team in sorted(set(frame.team)|set(frame.opponent_team)):
            conn.execute('INSERT OR IGNORE INTO dim_team(team_code) VALUES (?)',(team,))
        teams={r['team_code']:r['team_key'] for r in conn.execute('SELECT * FROM dim_team')}
        for row in frame[['season','season_type','week']].drop_duplicates().itertuples(index=False):
            conn.execute('INSERT OR IGNORE INTO dim_season_week(season,season_type,week) VALUES (?,?,?)',tuple(row))
        weeks={(r['season'],r['season_type'],r['week']):r['week_key'] for r in conn.execute('SELECT * FROM dim_season_week')}
        for row in frame.to_dict('records'):
            values=[snapshot,weeks[row['season'],row['season_type'],row['week']],players[row['player_id']],
                profiles[players[row['player_id']],row['player_display_name'],row['position']],
                teams[row['team']],teams[row['opponent_team']],row['game_id'],*[row[c] for c in COUNTS+YARDS]]
            conn.execute('INSERT INTO fact_player_week VALUES ('+','.join('?' for _ in values)+')',values)
        actual=read_snapshot(conn,snapshot)
        if len(actual)!=len(frame) or any(int(actual[c].sum())!=int(frame[c].sum()) for c in COUNTS+YARDS):
            raise DataError('Dimension joins changed source row counts or measures')
        if conn.execute('PRAGMA foreign_key_check').fetchall():
            raise DataError('Model contains orphan relationships')
    return snapshot,quality

def read_snapshot(conn,snapshot,season=None,teams=None,positions=None,week_start=None,week_end=None):
    if not conn.execute('SELECT 1 FROM model_snapshot WHERE snapshot_key=?',(snapshot,)).fetchone():
        raise DataError('Snapshot does not exist')
    clauses,params=['snapshot_key=?'],[snapshot]
    for field,values in [('team',teams),('position',positions)]:
        if values is not None:
            clauses.append(field+' IN ('+','.join('?' for _ in values)+')' if values else '0=1')
            params.extend(values)
    for field,op,value in [('season','=',season),('week','>=',week_start),('week','<=',week_end)]:
        if value is not None:
            clauses.append(field+op+'?')
            params.append(value)
    frame=pd.read_sql_query('SELECT '+','.join(FIELDS)+' FROM v_player_week WHERE '+' AND '.join(clauses)+
        ' ORDER BY season,week,player_id',conn,params=params)
    # Preserve the normalized schema even when a filter returns no rows.
    for col in ['season','week']+COUNTS+YARDS:
        frame[col]=frame[col].astype('int64')
    return frame

def analyze_snapshot(payload,expected_season=None):
    with closing(connect_model()) as conn:
        snapshot,quality=load_snapshot(conn,payload,expected_season)
        return read_snapshot(conn,snapshot),quality

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--season',type=int)
    parser.add_argument('--database',type=Path,required=True)
    args=parser.parse_args()
    args.database.parent.mkdir(parents=True,exist_ok=True)
    with closing(connect_model(args.database)) as conn:
        snapshot,quality=load_snapshot(conn,args.input.read_bytes(),args.season)
        print({'snapshot_key':snapshot,**quality})
