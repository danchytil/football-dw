-- 03: GOLD LAYER — STAR SCHEMA (Tables with surrogate keys)

-- ============================================================
-- DIMENSIONS
-- ============================================================

-- DIM_TEAM
CREATE TABLE IF NOT EXISTS gold.dim_team (
    team_key     BIGSERIAL PRIMARY KEY,
    team_id      INT NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    canonical_name VARCHAR(100) NOT NULL
);

-- DIM_SEASON
CREATE TABLE IF NOT EXISTS gold.dim_season (
    season_key   BIGSERIAL PRIMARY KEY,
    season_id    VARCHAR(10) NOT NULL UNIQUE,
    start_year   INT NOT NULL,
    end_year     INT NOT NULL,
    season_label VARCHAR(10) NOT NULL              -- e.g. "2023/24"
);

-- DIM_DATE
CREATE TABLE IF NOT EXISTS gold.dim_date (
    date_key     DATE PRIMARY KEY,
    year         INT NOT NULL,
    month        INT NOT NULL,
    day          INT NOT NULL,
    month_name   VARCHAR(20) NOT NULL,
    day_name     VARCHAR(20) NOT NULL,
    day_of_week  INT NOT NULL,
    is_weekend   BOOLEAN NOT NULL,
    week_number  INT NOT NULL,
    quarter      INT NOT NULL
);

-- DIM_STADIUM
CREATE TABLE IF NOT EXISTS gold.dim_stadium (
    stadium_key  BIGSERIAL PRIMARY KEY,
    team_name    VARCHAR(100) NOT NULL,
    stadium_name VARCHAR(150) NOT NULL,
    capacity     INT,
    opened_date  INT,
    closed_date  INT,
    is_current   BOOLEAN NOT NULL DEFAULT FALSE
);

-- ============================================================
-- FACTS
-- ============================================================

-- FCT_MATCH — one row per match
CREATE TABLE IF NOT EXISTS gold.fct_match (
    match_key       BIGSERIAL PRIMARY KEY,
    match_id        INT NOT NULL UNIQUE,
    season_key      BIGINT NOT NULL REFERENCES gold.dim_season(season_key),
    date_key        DATE NOT NULL REFERENCES gold.dim_date(date_key),
    home_team_key   BIGINT NOT NULL REFERENCES gold.dim_team(team_key),
    away_team_key   BIGINT NOT NULL REFERENCES gold.dim_team(team_key),
    stadium_key     BIGINT REFERENCES gold.dim_stadium(stadium_key),
    home_goals      INT NOT NULL,
    away_goals      INT NOT NULL,
    total_goals     INT NOT NULL,
    result          CHAR(1) NOT NULL CHECK (result IN ('H', 'D', 'A')),
    match_slug      VARCHAR(20),
    home_points     INT NOT NULL,
    away_points     INT NOT NULL,
    CONSTRAINT chk_fct_different_teams CHECK (home_team_key <> away_team_key)
);

-- FCT_TEAM_SEASON — league table per season (denormalized with market values)
CREATE TABLE IF NOT EXISTS gold.fct_team_season (
    team_season_key  BIGSERIAL PRIMARY KEY,
    team_key         BIGINT NOT NULL REFERENCES gold.dim_team(team_key),
    season_key       BIGINT NOT NULL REFERENCES gold.dim_season(season_key),
    matches_played   INT NOT NULL,
    wins             INT NOT NULL,
    draws            INT NOT NULL,
    losses           INT NOT NULL,
    goals_for        INT NOT NULL,
    goals_against    INT NOT NULL,
    goal_difference  INT NOT NULL,
    total_points     INT NOT NULL,
    league_position  INT NOT NULL,
    market_value_eur BIGINT,
    squad_size       INT,
    avg_player_age   NUMERIC(4, 1),
    CONSTRAINT uq_fct_team_season UNIQUE (team_key, season_key)
);

-- ============================================================
-- ROLE-PLAYING DIMENSIONS (for Power BI - two FK to same dim)
-- ============================================================

CREATE OR REPLACE VIEW gold.dim_home_team AS
SELECT team_key AS home_team_key, team_id, display_name, canonical_name
FROM gold.dim_team;

CREATE OR REPLACE VIEW gold.dim_away_team AS
SELECT team_key AS away_team_key, team_id, display_name, canonical_name
FROM gold.dim_team;

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_fct_match_season ON gold.fct_match(season_key);
CREATE INDEX IF NOT EXISTS idx_fct_match_date ON gold.fct_match(date_key);
CREATE INDEX IF NOT EXISTS idx_fct_match_home ON gold.fct_match(home_team_key);
CREATE INDEX IF NOT EXISTS idx_fct_match_away ON gold.fct_match(away_team_key);
CREATE INDEX IF NOT EXISTS idx_fct_team_season_team ON gold.fct_team_season(team_key);
CREATE INDEX IF NOT EXISTS idx_fct_team_season_season ON gold.fct_team_season(season_key);