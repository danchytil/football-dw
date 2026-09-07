-- 03: SILVER LAYER

-- 1.Normalization function for automatic team name matching
--Handles: lowercase, dots, ampersands, FC/AFC prefixes and suffixes
CREATE OR REPLACE FUNCTION silver.fn_normalize_team_name(raw_name VARCHAR) 
RETURNS VARCHAR AS $$
BEGIN
    RETURN TRIM(
        REGEXP_REPLACE(
            REGEXP_REPLACE(
                REPLACE(
                    REPLACE(
                        LOWER(raw_name),
                        '.', ''
                    ),
                    '&', 'and'
                ),
                '(^afc | afc$| fc$)', '', 'g'
            ),
            '\s+', ' ', 'g'
        )
    );
END;
$$ LANGUAGE plpgsql;

-- 2.Teams (unified via canonical name)
CREATE TABLE IF NOT EXISTS silver.teams (
    team_id SERIAL PRIMARY KEY,
    canonical_name VARCHAR(100) UNIQUE NOT NULL, 
    display_name VARCHAR(100) NOT NULL           
);

-- 3. Team Name Cross-Reference (audit trail for name matching)
CREATE TABLE IF NOT EXISTS silver.team_name_xref (
    xref_id SERIAL PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL,
    source_system VARCHAR(50) NOT NULL,
    canonical_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_xref UNIQUE (source_name, source_system)
);

-- 4. Stadium History (handles stadium relocations and history over time)
CREATE TABLE IF NOT EXISTS silver.stadium_history (
    stadium_history_id SERIAL PRIMARY KEY,
    team_id INT NOT NULL REFERENCES silver.teams(team_id) ON DELETE CASCADE,
    stadium_name VARCHAR(150) NOT NULL,
    capacity INT CHECK (capacity > 0),
    opened_date INT,
    closed_date INT,
    CONSTRAINT uq_stadium_team UNIQUE (team_id, stadium_name)
);

-- 5. Seasons
CREATE TABLE IF NOT EXISTS silver.seasons (
    season_id VARCHAR(10) PRIMARY KEY,
    start_year INT NOT NULL,
    end_year INT NOT NULL
);

-- 6. Matches
CREATE TABLE IF NOT EXISTS silver.matches (
    match_id INT PRIMARY KEY,
    season_id VARCHAR(10) NOT NULL REFERENCES silver.seasons(season_id),
    match_date TIMESTAMP WITH TIME ZONE NOT NULL,
    home_team_id INT NOT NULL REFERENCES silver.teams(team_id),
    away_team_id INT NOT NULL REFERENCES silver.teams(team_id),
    home_goals INT NOT NULL CHECK (home_goals >= 0),
    away_goals INT NOT NULL CHECK (away_goals >= 0),
    result CHAR(1) NOT NULL CHECK (result IN ('H', 'D', 'A')),
    CONSTRAINT chk_different_teams CHECK (home_team_id <> away_team_id)
);

--7.Team Market Values
CREATE TABLE IF NOT EXISTS silver.team_market_values (
    valuation_id SERIAL PRIMARY KEY,
    team_id INT NOT NULL REFERENCES silver.teams(team_id),
    season_id VARCHAR(10) NOT NULL REFERENCES silver.seasons(season_id),
    market_value_eur BIGINT NOT NULL CHECK (market_value_eur > 0),
    squad_size INT CHECK (squad_size > 0),
    avg_player_age NUMERIC(4, 1),
    CONSTRAINT uq_team_season_val UNIQUE (team_id, season_id)
);

--Indexes for fast JOINs
CREATE INDEX IF NOT EXISTS idx_silver_matches_date ON silver.matches(match_date);
CREATE INDEX IF NOT EXISTS idx_silver_matches_home ON silver.matches(home_team_id);
CREATE INDEX IF NOT EXISTS idx_silver_matches_away ON silver.matches(away_team_id);