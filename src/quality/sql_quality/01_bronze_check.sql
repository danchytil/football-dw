SELECT 'raw.api_matches is empty' AS error_msg
WHERE (SELECT COUNT(*) FROM raw.api_matches) = 0

UNION ALL

SELECT 'raw.kaggle_values is empty'
WHERE (SELECT COUNT(*) FROM raw.kaggle_values) = 0

UNION ALL

SELECT 'raw.wiki_stadiums is empty'
WHERE (SELECT COUNT(*) FROM raw.wiki_stadiums) = 0

UNION ALL

SELECT CONCAT('Found ', COUNT(*), ' NULL payloads in raw.api_matches')
FROM raw.api_matches 
WHERE payload IS NULL
HAVING COUNT(*) > 0

UNION ALL

SELECT CONCAT('Found ', COUNT(*), ' NULL team names in raw.kaggle_values')
FROM raw.kaggle_values 
WHERE raw_team_name IS NULL
HAVING COUNT(*) > 0

UNION ALL

SELECT CONCAT('Found ', COUNT(*), ' invalid n/a entries in raw.wiki_stadiums')
FROM raw.wiki_stadiums 
WHERE raw_wiki_club ILIKE '%n/a%'
HAVING COUNT(*) > 0;