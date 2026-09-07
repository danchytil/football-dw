import psycopg2
from src.db import get_connection
import os
from dotenv import load_dotenv

load_dotenv()
TARGET_SEASONS = os.getenv("TARGET_SEASONS", "2023,2024,2025").split(",")

def run():
    print("Starting transformation (RAW -> SILVER)...")
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Seasons
        for season in TARGET_SEASONS:
            start_year = int(season)
            cur.execute("""
                INSERT INTO silver.seasons (season_id, start_year, end_year)
                VALUES (%s, %s, %s)
                ON CONFLICT (season_id) DO NOTHING;
            """, (season, start_year, start_year + 1))
        print(f"Seasons {TARGET_SEASONS} updated.")


        # 2. Teams - source priority for display_name
        cur.execute("""
            INSERT INTO silver.teams (canonical_name, display_name)
            SELECT canonical, display FROM (
                SELECT 
                    silver.fn_normalize_team_name(team_name) AS canonical,
                    team_name AS display,
                    ROW_NUMBER() OVER (
                        PARTITION BY silver.fn_normalize_team_name(team_name) 
                        ORDER BY source_priority
                    ) AS rn
                FROM (
                    SELECT payload->'homeTeam'->>'name' AS team_name, 1 AS source_priority FROM raw.api_matches
                    UNION ALL SELECT payload->'awayTeam'->>'name', 1 FROM raw.api_matches
                    UNION ALL SELECT raw_team_name, 2 FROM raw.transfermarkt_values
                    UNION ALL SELECT raw_wiki_club, 3 FROM raw.wiki_stadiums
                ) all_teams
                WHERE team_name IS NOT NULL
            ) ranked
            WHERE rn = 1
            ON CONFLICT (canonical_name) DO NOTHING;
        """)
        print("Teams extracted, normalized and linked.")

        # Cross-reference table - audit trail for name matching
        cur.execute("""
            INSERT INTO silver.team_name_xref (source_name, source_system, canonical_name)
            SELECT DISTINCT team_name, source_system, silver.fn_normalize_team_name(team_name)
            FROM (
                SELECT payload->'homeTeam'->>'name' AS team_name, 'api' AS source_system FROM raw.api_matches
                UNION ALL SELECT payload->'awayTeam'->>'name', 'api' FROM raw.api_matches
                UNION ALL SELECT raw_team_name, 'transfermarkt' FROM raw.transfermarkt_values
                UNION ALL SELECT raw_wiki_club, 'wiki' FROM raw.wiki_stadiums
            ) all_names
            WHERE team_name IS NOT NULL
            ON CONFLICT (source_name, source_system) DO NOTHING;
        """)
        print("Team name cross-reference populated.")

        # Market values — deduplicated from raw + TRIM on parsing
        cur.execute("""
            INSERT INTO silver.team_market_values (team_id, season_id, market_value_eur, squad_size, avg_player_age)
            SELECT 
                t.team_id,
                r.season,
                (CAST(REGEXP_REPLACE(TRIM(r.market_value_str), '[€bnm]', '', 'gi') AS NUMERIC) * 
                 CASE 
                    WHEN TRIM(r.market_value_str) ILIKE '%bn' THEN 1000000000
                    WHEN TRIM(r.market_value_str) ILIKE '%m' THEN 1000000
                    ELSE 1
                 END)::BIGINT AS market_value_eur,
                CAST(NULLIF(r.squad_size_str, '') AS INT),
                CAST(NULLIF(r.avg_age_str, '') AS NUMERIC)
            FROM (
                SELECT DISTINCT ON (season, raw_team_name) *
                FROM raw.transfermarkt_values
                ORDER BY season, raw_team_name, ingested_at DESC
            ) r
            JOIN silver.teams t ON t.canonical_name = silver.fn_normalize_team_name(r.raw_team_name)
            WHERE r.market_value_str IS NOT NULL
            ON CONFLICT (team_id, season_id) 
            DO UPDATE SET 
                market_value_eur = EXCLUDED.market_value_eur,
                squad_size = EXCLUDED.squad_size,
                avg_player_age = EXCLUDED.avg_player_age;
        """)
        print("Market values (Transfermarkt) transformed and saved.")

        # Stadiums — upsert from deduplicated raw, no more TRUNCATE
        cur.execute("""
            INSERT INTO silver.stadium_history (team_id, stadium_name, capacity, opened_date, closed_date)
            SELECT 
                t.team_id,
                r.raw_stadium_name,
                CAST(NULLIF(REGEXP_REPLACE(r.raw_capacity, '[^0-9]', '', 'g'), '') AS INT) AS capacity,
                CAST(LEFT(NULLIF(REGEXP_REPLACE(r.raw_opened, '[^0-9]', '', 'g'), ''), 4) AS INT) AS opened_date,
                CAST(LEFT(NULLIF(REGEXP_REPLACE(r.raw_closed, '[^0-9]', '', 'g'), ''), 4) AS INT) AS closed_date
            FROM (
                SELECT DISTINCT ON (raw_wiki_club, raw_stadium_name) *
                FROM raw.wiki_stadiums
                ORDER BY raw_wiki_club, raw_stadium_name, ingested_at DESC
            ) r
            JOIN silver.teams t ON t.canonical_name = silver.fn_normalize_team_name(r.raw_wiki_club)
            ON CONFLICT (team_id, stadium_name) 
            DO UPDATE SET 
                capacity = EXCLUDED.capacity,
                opened_date = EXCLUDED.opened_date,
                closed_date = EXCLUDED.closed_date;
        """)
        print("Stadium history (Wiki) transformed.")


        # Auto-close older stadiums when a newer one exists
        cur.execute("""
            UPDATE silver.stadium_history sh
            SET closed_date = (
                SELECT MIN(newer.opened_date)
                FROM silver.stadium_history newer
                WHERE newer.team_id = sh.team_id
                  AND newer.opened_date > sh.opened_date
                  AND newer.stadium_history_id != sh.stadium_history_id
            )
            WHERE sh.closed_date IS NULL
              AND sh.opened_date IS NOT NULL
              AND EXISTS (
                  SELECT 1 FROM silver.stadium_history newer
                  WHERE newer.team_id = sh.team_id
                    AND newer.opened_date > sh.opened_date
                    AND newer.closed_date IS NULL
              );
        """)
        print("Older stadiums auto-closed based on newer openings.")

        # Matches — deduplicated from raw by latest ingested_at
        cur.execute("""
            INSERT INTO silver.matches (match_id, season_id, match_date, home_team_id, away_team_id, home_goals, away_goals, result)
            SELECT 
                CAST(r.payload->>'id' AS INT),
                r.season,
                CAST(r.payload->>'utcDate' AS TIMESTAMP WITH TIME ZONE),
                th.team_id,
                ta.team_id,
                CAST(r.payload->'score'->'fullTime'->>'home' AS INT),
                CAST(r.payload->'score'->'fullTime'->>'away' AS INT),
                CASE 
                    WHEN CAST(r.payload->'score'->'fullTime'->>'home' AS INT) > CAST(r.payload->'score'->'fullTime'->>'away' AS INT) THEN 'H'
                    WHEN CAST(r.payload->'score'->'fullTime'->>'home' AS INT) < CAST(r.payload->'score'->'fullTime'->>'away' AS INT) THEN 'A'
                    ELSE 'D'
                END
            FROM (
                SELECT DISTINCT ON ((payload->>'id')::INT) *
                FROM raw.api_matches
                ORDER BY (payload->>'id')::INT, ingested_at DESC
            ) r
            JOIN silver.teams th ON th.canonical_name = silver.fn_normalize_team_name(r.payload->'homeTeam'->>'name')
            JOIN silver.teams ta ON ta.canonical_name = silver.fn_normalize_team_name(r.payload->'awayTeam'->>'name')
            WHERE r.payload->'score'->'fullTime'->>'home' IS NOT NULL
            ON CONFLICT (match_id) DO UPDATE SET 
                home_goals = EXCLUDED.home_goals,
                away_goals = EXCLUDED.away_goals,
                result = EXCLUDED.result;
        """)
        print("Matches (API) loaded and linked.")

        conn.commit()
        print("Silver layer transformation completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Transformation error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run()