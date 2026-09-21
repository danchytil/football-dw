SELECT 'silver.teams table is empty' AS error_msg
WHERE (SELECT COUNT(*) FROM silver.teams) = 0

UNION ALL

SELECT CONCAT('match_id duplicate: ', match_id, ' (', COUNT(*), 'x)')
FROM silver.matches
GROUP BY match_id
HAVING COUNT(*) > 1

UNION ALL

SELECT CONCAT('Orphan match (match_id: ', m.match_id, ')')
FROM silver.matches m
WHERE NOT EXISTS (SELECT 1 FROM silver.teams t WHERE t.team_id = m.home_team_id)
   OR NOT EXISTS (SELECT 1 FROM silver.teams t WHERE t.team_id = m.away_team_id)

UNION ALL

SELECT CONCAT('Team plays against itself in match_id: ', match_id)
FROM silver.matches
WHERE home_team_id = away_team_id

UNION ALL

-- Check 380 matches for finished seasons and flexible for current season
SELECT CONCAT('Invalid match count in season ', s.season_id, ': ', COUNT(m.match_id))
FROM silver.seasons s
LEFT JOIN silver.matches m ON m.season_id = s.season_id
CROSS JOIN (SELECT MAX(start_year) AS max_yr FROM silver.seasons) cur_s
GROUP BY s.season_id, s.start_year, cur_s.max_yr
HAVING (s.start_year < cur_s.max_yr AND COUNT(m.match_id) != 380)
    OR (s.start_year = cur_s.max_yr AND (COUNT(m.match_id) = 0 OR COUNT(m.match_id) > 380))

UNION ALL

SELECT CONCAT('Multiple active stadiums: ', t.display_name)
FROM silver.stadium_history sh
JOIN silver.teams t ON t.team_id = sh.team_id
WHERE sh.closed_date IS NULL
GROUP BY t.display_name
HAVING COUNT(*) > 1

UNION ALL

SELECT CONCAT('Invalid market values count: ', COUNT(*))
FROM silver.team_market_values
WHERE market_value_eur <= 0 OR market_value_eur > 5000000000
HAVING COUNT(*) > 0

UNION ALL

SELECT CONCAT('Missing valuations for season: ', s.season_id)
FROM silver.seasons s
WHERE NOT EXISTS (
    SELECT 1 FROM silver.team_market_values tmv 
    WHERE tmv.season_id = s.season_id
)

UNION ALL

SELECT CONCAT('Unmatched xref name: ', x.source_name)
FROM silver.team_name_xref x
WHERE NOT EXISTS (
    SELECT 1 FROM silver.teams t 
    WHERE t.canonical_name = x.canonical_name
)

UNION ALL

SELECT CONCAT('Negative goals found: ', COUNT(*))
FROM silver.matches
WHERE home_goals < 0 OR away_goals < 0
HAVING COUNT(*) > 0

UNION ALL

SELECT CONCAT('Inconsistent results vs goals: ', COUNT(*))
FROM silver.matches
WHERE (home_goals > away_goals AND result != 'H')
   OR (home_goals < away_goals AND result != 'A')
   OR (home_goals = away_goals AND result != 'D')
HAVING COUNT(*) > 0;