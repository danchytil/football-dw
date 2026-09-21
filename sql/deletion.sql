-- DELETION: Drop all tables and functions (reverse order of dependencies)

-- Drop Gold tables (facts first, then dimensions)
DROP TABLE IF EXISTS gold.fct_team_season CASCADE;
DROP TABLE IF EXISTS gold.fct_match CASCADE;
DROP TABLE IF EXISTS gold.dim_stadium CASCADE;
DROP TABLE IF EXISTS gold.dim_date CASCADE;
DROP TABLE IF EXISTS gold.dim_season CASCADE;
DROP TABLE IF EXISTS gold.dim_team CASCADE;

-- Drop Silver tables
DROP TABLE IF EXISTS silver.matches CASCADE;
DROP TABLE IF EXISTS silver.team_market_values CASCADE;
DROP TABLE IF EXISTS silver.stadium_history CASCADE;
DROP TABLE IF EXISTS silver.team_name_xref CASCADE;
DROP TABLE IF EXISTS silver.seasons CASCADE;
DROP TABLE IF EXISTS silver.teams CASCADE;

-- Drop Bronze tables
DROP TABLE IF EXISTS raw.api_matches CASCADE;
DROP TABLE IF EXISTS raw.wiki_stadiums CASCADE;
DROP TABLE IF EXISTS raw.transfermarkt_values CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS silver.fn_normalize_team_name(VARCHAR);