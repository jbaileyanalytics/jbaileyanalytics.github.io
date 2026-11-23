-- Bind :snapshot_key. Do not mix revisions of the same player-week.
SELECT season,player_id,observed_weeks,targets,receiving_yards,yards_per_target,catch_rate
FROM v_player_season_totals WHERE snapshot_key=:snapshot_key AND targets>=30
ORDER BY receiving_yards DESC,player_id;

-- Team production is scoped to QB/RB/WR/TE source observations, not a full team box score.
SELECT season,week,team,SUM(targets) AS targets,SUM(receiving_yards) AS receiving_yards,
 1.0*SUM(receiving_yards)/NULLIF(SUM(targets),0) AS yards_per_target
FROM v_player_week WHERE snapshot_key=:snapshot_key
GROUP BY season,week,team ORDER BY season,week,team;

-- Joining dimensions must preserve source row counts and additive statistics.
SELECT COUNT(*) AS joined_rows, SUM(attempts) AS attempts, SUM(passing_yards) AS passing_yards,
 SUM(carries) AS carries, SUM(rushing_yards) AS rushing_yards,
 SUM(targets) AS targets,SUM(receiving_yards) AS receiving_yards
FROM v_player_week WHERE snapshot_key=:snapshot_key;
