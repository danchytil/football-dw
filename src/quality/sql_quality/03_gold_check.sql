-- Gold layer quality checks (table-based schema with surrogate keys)

-- Dimension integrity
SELECT 'dim_team is empty' AS error_msg
WHERE (SELECT COUNT(*) FROM gold.dim_team) = 0

UNION ALL

SELECT 'dim_season is empty'
WHERE (SELECT COUNT(*) FROM gold.dim_season) = 0

UNION ALL

SELECT 'dim_date is empty'
WHERE (SELECT COUNT(*) FROM gold.dim_date) = 0

UNION ALL

SELECT CONCAT('Duplicate team_id in dim_team: ', team_id)
FROM gold.dim_team
GROUP BY team_id
HAVING COUNT(*) > 1

UNION ALL

SELECT CONCAT('Duplicate season_id in dim_season: ', season_id)
FROM gold.dim_season
GROUP BY season_id
HAVING COUNT(*) > 1

UNION ALL

-- Fact integrity
SELECT CONCAT('Duplicate match_id in fct_match: ', match_id)
FROM gold.fct_match
GROUP BY match_id
HAVING COUNT(*) > 1

UNION ALL

SELECT CONCAT('Season ', ds.season_label, ' does not have 20 teams (count: ', COUNT(*), ')')
FROM gold.fct_team_season fts
JOIN gold.dim_season ds ON ds.season_key = fts.season_key
GROUP BY ds.season_label, ds.season_key
HAVING COUNT(*) != 20

UNION ALL

-- Match count validation
SELECT CONCAT('Team ', dt.display_name, ' (', ds.season_label, ') played ', fts.matches_played, ' matches')
FROM gold.fct_team_season fts
JOIN gold.dim_team dt ON dt.team_key = fts.team_key
JOIN gold.dim_season ds ON ds.season_key = fts.season_key
WHERE ds.start_year < (SELECT MAX(start_year) FROM gold.dim_season)
  AND fts.matches_played != 38

UNION ALL

-- League position validation
SELECT CONCAT('Invalid positions in season ', ds.season_label)
FROM gold.fct_team_season fts
JOIN gold.dim_season ds ON ds.season_key = fts.season_key
GROUP BY ds.season_label, ds.season_key
HAVING MIN(fts.league_position) != 1 OR MAX(fts.league_position) > 20

UNION ALL

-- Referential integrity: fact → dimension
SELECT CONCAT('Orphan fct_match (match_id: ', fm.match_id, ') - missing home_team_key')
FROM gold.fct_match fm
WHERE NOT EXISTS (SELECT 1 FROM gold.dim_team dt WHERE dt.team_key = fm.home_team_key)

UNION ALL

SELECT CONCAT('Orphan fct_match (match_id: ', fm.match_id, ') - missing away_team_key')
FROM gold.fct_match fm
WHERE NOT EXISTS (SELECT 1 FROM gold.dim_team dt WHERE dt.team_key = fm.away_team_key)

UNION ALL

SELECT CONCAT('Orphan fct_match (match_id: ', fm.match_id, ') - missing season_key')
FROM gold.fct_match fm
WHERE NOT EXISTS (SELECT 1 FROM gold.dim_season ds WHERE ds.season_key = fm.season_key)

UNION ALL

SELECT CONCAT('Orphan fct_match (match_id: ', fm.match_id, ') - missing date_key')
FROM gold.fct_match fm
WHERE NOT EXISTS (SELECT 1 FROM gold.dim_date dd WHERE dd.date_key = fm.date_key)

UNION ALL

-- dim_stadium: no team with multiple current stadiums
SELECT CONCAT('Multiple current stadiums: ', dst.team_name)
FROM gold.dim_stadium dst
WHERE dst.is_current = TRUE
GROUP BY dst.team_name
HAVING COUNT(*) > 1;