--02: BRONZE (RAW) LAYER

-- Raw match data from football-data.org (JSON format)
CREATE TABLE IF NOT EXISTS raw.api_matches (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    season VARCHAR(10) NOT NULL,
    payload JSONB NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

--Raw stadium data from Wikipedia (including opened/closed dates)
CREATE TABLE IF NOT EXISTS raw.wiki_stadiums (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    raw_wiki_club VARCHAR(255) NOT NULL,
    raw_stadium_name VARCHAR(255),
    raw_capacity VARCHAR(100),
    raw_opened VARCHAR(50),
    raw_closed VARCHAR(50),
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

--Raw financial data from Transfermarkt
CREATE TABLE IF NOT EXISTS raw.transfermarkt_values (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    season VARCHAR(10) NOT NULL,
    raw_team_name VARCHAR(255) NOT NULL,
    market_value_str VARCHAR(100),
    squad_size_str VARCHAR(50),
    avg_age_str VARCHAR(50),
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for faster filtering
CREATE INDEX IF NOT EXISTS idx_raw_matches_season ON raw.api_matches(season);
CREATE INDEX IF NOT EXISTS idx_raw_matches_run ON raw.api_matches(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_transfermarkt_run ON raw.transfermarkt_values(run_id);
CREATE INDEX IF NOT EXISTS idx_raw_wiki_run ON raw.wiki_stadiums(run_id);