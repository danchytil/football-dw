from src.db import get_connection


def run():
    """Load Gold star schema tables from Silver layer."""
    print("Loading Gold star schema...")
    conn = get_connection()
    cur = conn.cursor()

    try:
        # ============================================================
        # DIMENSIONS (load first — facts reference them)
        # ============================================================

        # DIM_TEAM
        cur.execute("TRUNCATE gold.dim_team RESTART IDENTITY CASCADE;")
        cur.execute("""
            INSERT INTO gold.dim_team (team_id, display_name, canonical_name)
            SELECT team_id, display_name, canonical_name
            FROM silver.teams
            ORDER BY team_id;
        """)
        cur.execute("SELECT COUNT(*) FROM gold.dim_team;")
        print(f"  dim_team: {cur.fetchone()[0]} rows loaded.")

        # DIM_SEASON
        cur.execute("TRUNCATE gold.dim_season RESTART IDENTITY CASCADE;")
        cur.execute("""
            INSERT INTO gold.dim_season (season_id, start_year, end_year, season_label)
            SELECT 
                season_id,
                start_year,
                end_year,
                start_year || '/' || RIGHT(CAST(end_year AS VARCHAR), 2) AS season_label
            FROM silver.seasons
            ORDER BY season_id;
        """)
        cur.execute("SELECT COUNT(*) FROM gold.dim_season;")
        print(f"  dim_season: {cur.fetchone()[0]} rows loaded.")

        # DIM_DATE
        cur.execute("TRUNCATE gold.dim_date RESTART IDENTITY CASCADE;")
        cur.execute("""
            INSERT INTO gold.dim_date (date_key, year, month, day, month_name, day_name, day_of_week, is_weekend, week_number, quarter)
            SELECT 
                d::DATE                                      AS date_key,
                EXTRACT(YEAR FROM d)::INT                    AS year,
                EXTRACT(MONTH FROM d)::INT                   AS month,
                EXTRACT(DAY FROM d)::INT                     AS day,
                TRIM(TO_CHAR(d, 'Month'))                    AS month_name,
                TRIM(TO_CHAR(d, 'Day'))                      AS day_name,
                EXTRACT(DOW FROM d)::INT                     AS day_of_week,
                CASE WHEN EXTRACT(DOW FROM d) IN (0, 6) 
                     THEN TRUE ELSE FALSE END                AS is_weekend,
                EXTRACT(WEEK FROM d)::INT                    AS week_number,
                TO_CHAR(d, 'Q')::INT                         AS quarter
            FROM generate_series(
                (SELECT MIN(match_date)::DATE FROM silver.matches),
                (SELECT MAX(match_date)::DATE FROM silver.matches),
                '1 day'::INTERVAL
            ) AS d;
        """)
        cur.execute("SELECT COUNT(*) FROM gold.dim_date;")
        print(f"  dim_date: {cur.fetchone()[0]} rows loaded.")

        # DIM_STADIUM
        cur.execute("TRUNCATE gold.dim_stadium RESTART IDENTITY CASCADE;")
        cur.execute("""
            INSERT INTO gold.dim_stadium (team_name, stadium_name, capacity, opened_date, closed_date, is_current)
            SELECT 
                t.display_name,
                sh.stadium_name,
                sh.capacity,
                sh.opened_date,
                sh.closed_date,
                CASE WHEN sh.closed_date IS NULL THEN TRUE ELSE FALSE END AS is_current
            FROM silver.stadium_history sh
            JOIN silver.teams t ON t.team_id = sh.team_id
            ORDER BY t.display_name, sh.opened_date;
        """)
        cur.execute("SELECT COUNT(*) FROM gold.dim_stadium;")
        print(f"  dim_stadium: {cur.fetchone()[0]} rows loaded.")

        # ============================================================
        # FACTS
        # ============================================================

        # FCT_MATCH
        cur.execute("TRUNCATE gold.fct_match RESTART IDENTITY CASCADE;")
        cur.execute("""
            INSERT INTO gold.fct_match (
                match_id, season_key, date_key, home_team_key, away_team_key,
                stadium_key, home_goals, away_goals, total_goals, result,
                match_slug, home_points, away_points
            )
            SELECT 
                m.match_id,
                ds.season_key,
                m.match_date::DATE                           AS date_key,
                dh.team_key                                  AS home_team_key,
                da.team_key                                  AS away_team_key,
                dst.stadium_key,
                m.home_goals,
                m.away_goals,
                m.home_goals + m.away_goals                  AS total_goals,
                m.result,
                m.match_slug,
                CASE WHEN m.result = 'H' THEN 3 WHEN m.result = 'D' THEN 1 ELSE 0 END AS home_points,
                CASE WHEN m.result = 'A' THEN 3 WHEN m.result = 'D' THEN 1 ELSE 0 END AS away_points
            FROM silver.matches m
            JOIN gold.dim_season ds ON ds.season_id = m.season_id
            JOIN gold.dim_team dh ON dh.team_id = m.home_team_id
            JOIN gold.dim_team da ON da.team_id = m.away_team_id
            LEFT JOIN gold.dim_stadium dst 
                ON dst.team_name = dh.display_name
                AND CAST(m.season_id AS INT) >= COALESCE(dst.opened_date, 0)
                AND (dst.closed_date IS NULL OR CAST(m.season_id AS INT) < dst.closed_date)
            ORDER BY m.match_date;
        """)
        cur.execute("SELECT COUNT(*) FROM gold.fct_match;")
        print(f"  fct_match: {cur.fetchone()[0]} rows loaded.")

        # FCT_TEAM_SEASON
        cur.execute("TRUNCATE gold.fct_team_season RESTART IDENTITY CASCADE;")
        cur.execute("""
            WITH match_results AS (
                SELECT 
                    season_key, home_team_key AS team_key,
                    home_goals AS goals_for, away_goals AS goals_against,
                    CASE WHEN result = 'H' THEN 1 ELSE 0 END AS win,
                    CASE WHEN result = 'D' THEN 1 ELSE 0 END AS draw,
                    CASE WHEN result = 'A' THEN 1 ELSE 0 END AS loss,
                    CASE WHEN result = 'H' THEN 3 WHEN result = 'D' THEN 1 ELSE 0 END AS points
                FROM gold.fct_match
                UNION ALL
                SELECT 
                    season_key, away_team_key,
                    away_goals, home_goals,
                    CASE WHEN result = 'A' THEN 1 ELSE 0 END,
                    CASE WHEN result = 'D' THEN 1 ELSE 0 END,
                    CASE WHEN result = 'H' THEN 1 ELSE 0 END,
                    CASE WHEN result = 'A' THEN 3 WHEN result = 'D' THEN 1 ELSE 0 END
                FROM gold.fct_match
            )
            INSERT INTO gold.fct_team_season (
                team_key, season_key, matches_played, wins, draws, losses,
                goals_for, goals_against, goal_difference, total_points,
                league_position, market_value_eur, squad_size, avg_player_age
            )
            SELECT 
                mr.team_key,
                mr.season_key,
                COUNT(*)                                     AS matches_played,
                SUM(mr.win)                                  AS wins,
                SUM(mr.draw)                                 AS draws,
                SUM(mr.loss)                                 AS losses,
                SUM(mr.goals_for)                            AS goals_for,
                SUM(mr.goals_against)                        AS goals_against,
                SUM(mr.goals_for) - SUM(mr.goals_against)    AS goal_difference,
                SUM(mr.points)                               AS total_points,
                DENSE_RANK() OVER (
                    PARTITION BY mr.season_key 
                    ORDER BY SUM(mr.points) DESC, 
                             SUM(mr.goals_for) - SUM(mr.goals_against) DESC
                )                                            AS league_position,
                tmv.market_value_eur,
                tmv.squad_size,
                tmv.avg_player_age
            FROM match_results mr
            JOIN gold.dim_team dt ON dt.team_key = mr.team_key
            JOIN gold.dim_season ds ON ds.season_key = mr.season_key
            LEFT JOIN silver.team_market_values tmv 
                ON tmv.team_id = dt.team_id 
                AND tmv.season_id = ds.season_id
            GROUP BY mr.team_key, mr.season_key, 
                     tmv.market_value_eur, tmv.squad_size, tmv.avg_player_age;
        """)
        cur.execute("SELECT COUNT(*) FROM gold.fct_team_season;")
        print(f"  fct_team_season: {cur.fetchone()[0]} rows loaded.")

        conn.commit()
        print("Gold layer loading completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Gold loading error: {e}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run()