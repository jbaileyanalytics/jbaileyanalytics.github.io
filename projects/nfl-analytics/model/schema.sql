CREATE TABLE dim_player (
    player_key INTEGER PRIMARY KEY, 
    player_id TEXT NOT NULL UNIQUE
    );

CREATE TABLE dim_player_profile (
    profile_key INTEGER PRIMARY KEY, 
    player_key INTEGER NOT NULL REFERENCES dim_player,
    player_display_name TEXT NOT NULL, 
    position TEXT NOT NULL CHECK(position IN ('QB','RB','WR','TE')), UNIQUE(player_key,player_display_name,position), UNIQUE(profile_key,player_key)
    );

CREATE TABLE dim_team (
    team_key INTEGER PRIMARY KEY, 
    team_code TEXT NOT NULL UNIQUE
    );

CREATE TABLE dim_season_week (
    week_key INTEGER PRIMARY KEY, 
    season INTEGER NOT NULL CHECK(season BETWEEN 1999 AND 2100),
    season_type TEXT NOT NULL CHECK(season_type='REG'), 
    week INTEGER NOT NULL CHECK(week BETWEEN 1 AND 18),
    UNIQUE(season,season_type,week)
    );

CREATE TABLE model_snapshot (
    snapshot_key INTEGER PRIMARY KEY, 
    canonical_sha256 TEXT NOT NULL UNIQUE,
    first_payload_sha256 TEXT NOT NULL, 
    accepted_rows INTEGER NOT NULL CHECK(accepted_rows>0), 
    loaded_at_utc TEXT NOT NULL
    );

CREATE TABLE fact_player_week (
    snapshot_key INTEGER NOT NULL REFERENCES model_snapshot,
    week_key INTEGER NOT NULL REFERENCES dim_season_week,
    player_key INTEGER NOT NULL REFERENCES dim_player, 
    profile_key INTEGER NOT NULL,
    team_key INTEGER NOT NULL REFERENCES dim_team, 
    opponent_team_key INTEGER NOT NULL REFERENCES dim_team,
    game_id TEXT NOT NULL,
    completions INTEGER NOT NULL CHECK(completions>=0), 
    attempts INTEGER NOT NULL CHECK(attempts>=0),
    passing_tds INTEGER NOT NULL CHECK(passing_tds>=0), 
    passing_interceptions INTEGER NOT NULL CHECK(passing_interceptions>=0),
    carries INTEGER NOT NULL CHECK(carries>=0), 
    rushing_tds INTEGER NOT NULL CHECK(rushing_tds>=0),
    targets INTEGER NOT NULL CHECK(targets>=0), 
    receptions INTEGER NOT NULL CHECK(receptions>=0),
    receiving_tds INTEGER NOT NULL CHECK(receiving_tds>=0),
    passing_yards INTEGER NOT NULL, 
    rushing_yards INTEGER NOT NULL, 
    receiving_yards INTEGER NOT NULL,
    PRIMARY KEY(snapshot_key,week_key,player_key),
    FOREIGN KEY(profile_key,player_key) REFERENCES dim_player_profile(profile_key,player_key),
    CHECK(completions<=attempts), CHECK(receptions<=targets)
    );

CREATE INDEX ix_player_week_team 
    ON fact_player_week(snapshot_key,team_key,week_key);

CREATE VIEW v_player_week AS
    SELECT  f.snapshot_key, 
            p.player_id, 
            profile.player_display_name, 
            profile.position,
            w.season, 
            w.week, 
            w.season_type, 
            f.game_id, 
            team.team_code AS team, 
            opponent.team_code AS opponent_team,
            f.completions, 
            f.attempts, 
            f.passing_tds, 
            f.passing_interceptions,
            f.carries, 
            f.rushing_tds, 
            f.targets, 
            f.receptions, 
            f.receiving_tds,
            f.passing_yards, 
            f.rushing_yards, 
            f.receiving_yards
    FROM fact_player_week f 
    JOIN dim_player p USING(player_key)
    JOIN dim_player_profile profile ON profile.profile_key=f.profile_key
    JOIN dim_season_week w USING(week_key)
    JOIN dim_team team ON team.team_key=f.team_key
    JOIN dim_team opponent ON opponent.team_key=f.opponent_team_key;

CREATE VIEW v_player_season_totals AS
    SELECT  snapshot_key, 
            season, 
            season_type, 
            player_id, 
            COUNT(*) AS observed_weeks,
            SUM(attempts) AS attempts, 
            SUM(passing_yards) AS passing_yards,
            SUM(carries) AS carries, 
            SUM(rushing_yards) AS rushing_yards,
            SUM(targets) AS targets, 
            SUM(receiving_yards) AS receiving_yards,
            1.0*SUM(passing_yards)/NULLIF(SUM(attempts),0) AS yards_per_attempt,
            1.0*SUM(rushing_yards)/NULLIF(SUM(carries),0) AS yards_per_carry,
            1.0*SUM(receiving_yards)/NULLIF(SUM(targets),0) AS yards_per_target,
            1.0*SUM(receptions)/NULLIF(SUM(targets),0) AS catch_rate
    FROM v_player_week 
    GROUP BY snapshot_key,season,season_type,player_id;
