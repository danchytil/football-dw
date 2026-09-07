-- DELETION: Drop all tables and functions (reverse order of dependencies)

-- Drop Gold views first
DROP MATERIALIZED VIEW IF EXISTS gold.fct_match;
DROP MATERIALIZED VIEW IF EXISTS gold.fct_team_season;
DROP MATERIALIZED VIEW IF EXISTS gold.dim_team;
DROP MATERIALIZED VIEW IF EXISTS gold.dim_season;
DROP MATERIALIZED VIEW IF EXISTS gold.dim_date;

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