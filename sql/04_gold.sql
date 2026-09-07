-- 04: GOLD LAYER — STAR SCHEMA

-- DIM_TEAM - one row per team with current stadium
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.dim_team AS
SELECT 
    t.team_id,
    t.display_name,
    st.stadium_name AS current_stadium,
    st.capacity AS current_capacity
FROM silver.teams t
LEFT JOIN silver.stadium_history st 
    ON t.team_id = st.team_id 
    AND st.closed_date IS NULL;
 

--DIM_SEASON - season lookup with display label

CREATE MATERIALIZED VIEW IF NOT EXISTS gold.dim_season AS
SELECT 
    season_id,
    start_year,
    end_year,
    start_year || '/' || RIGHT(CAST(end_year AS VARCHAR), 2) AS season_label
FROM silver.seasons;


-- DIM_DATE - calendar table for time intelligence

CREATE MATERIALIZED VIEW IF NOT EXISTS gold.dim_date AS
SELECT 
    d::DATE AS date_key,
    EXTRACT(YEAR FROM d)::INT AS year,
    EXTRACT(MONTH FROM d)::INT AS month,
    EXTRACT(DAY FROM d)::INT AS day,
    TO_CHAR(d, 'Month') AS month_name,
    TO_CHAR(d, 'Day') AS day_name,
    EXTRACT(DOW FROM d)::INT AS day_of_week,
    CASE WHEN EXTRACT(DOW FROM d) IN (0, 6) 
         THEN TRUE ELSE FALSE END AS is_weekend,
    EXTRACT(WEEK FROM d)::INT AS week_number,
    TO_CHAR(d, 'Q')::INT AS quarter
FROM generate_series(
    (SELECT MIN(match_date)::DATE FROM silver.matches),
    (SELECT MAX(match_date)::DATE FROM silver.matches),
    '1 day'::INTERVAL
) AS d;

 

-- FCT_MATCH
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.fct_match AS
SELECT 
    m.match_id,
    m.season_id,
    m.match_date::DATE AS date_key,
    m.home_team_id,
    m.away_team_id,
    m.home_goals,
    m.away_goals,
    m.result,
    CASE WHEN m.result = 'H' THEN 3 WHEN m.result = 'D' THEN 1 ELSE 0 END AS home_points,
    CASE WHEN m.result = 'A' THEN 3 WHEN m.result = 'D' THEN 1 ELSE 0 END AS away_points
FROM silver.matches m;

-- FCT_TEAM_SEASON

CREATE MATERIALIZED VIEW IF NOT EXISTS gold.fct_team_season AS
WITH match_results AS (
    SELECT 
        season_id, home_team_id AS team_id,
        home_goals AS goals_for, away_goals AS goals_against,
        CASE WHEN result = 'H' THEN 1 ELSE 0 END AS win,
        CASE WHEN result = 'D' THEN 1 ELSE 0 END AS draw,
        CASE WHEN result = 'A' THEN 1 ELSE 0 END AS loss,
        CASE WHEN result = 'H' THEN 3 WHEN result = 'D' THEN 1 ELSE 0 END AS points
    FROM silver.matches
    UNION ALL
    SELECT 
        season_id, away_team_id,
        away_goals, home_goals,
        CASE WHEN result = 'A' THEN 1 ELSE 0 END,
        CASE WHEN result = 'D' THEN 1 ELSE 0 END,
        CASE WHEN result = 'H' THEN 1 ELSE 0 END,
        CASE WHEN result = 'A' THEN 3 WHEN result = 'D' THEN 1 ELSE 0 END
    FROM silver.matches
)
SELECT 
    mr.season_id,
    mr.team_id,
    COUNT(*)    AS matches_played,
    SUM(mr.win)   AS wins,
    SUM(mr.draw)  AS draws,
    SUM(mr.loss)    AS losses,
    SUM(mr.goals_for)     AS goals_for,
    SUM(mr.goals_against)AS goals_against,
    SUM(mr.goals_for) - SUM(mr.goals_against)AS goal_difference,
    SUM(mr.points)   AS total_points,
    DENSE_RANK() OVER (
        PARTITION BY mr.season_id 
        ORDER BY SUM(mr.points) DESC, 
                 SUM(mr.goals_for) - SUM(mr.goals_against) DESC
    )                                           AS league_position
FROM match_results mr
GROUP BY mr.season_id, mr.team_id;

-- ML features table
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.ml_features AS
WITH team_performances AS (
    SELECT 
        match_id, match_date,
        home_team_id AS team_id, 'home' AS venue,
        CASE WHEN result = 'H' THEN 3 WHEN result = 'D' THEN 1 ELSE 0 END AS points
    FROM silver.matches
    UNION ALL
    SELECT 
        match_id, match_date,
        away_team_id AS team_id, 'away' AS venue,
        CASE WHEN result = 'A' THEN 3 WHEN result = 'D' THEN 1 ELSE 0 END AS points
    FROM silver.matches
),
rolling_form AS (
    SELECT 
        match_id, team_id, venue,
        SUM(points) OVER w AS form_points
    FROM team_performances
    WINDOW w AS (
        PARTITION BY team_id 
        ORDER BY match_date, match_id 
        ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
    )
)
SELECT 
    m.match_id,
    m.match_date,
    m.season_id,
    hf.form_points AS home_form,
    af.form_points AS away_form,
    m.result
FROM silver.matches m
JOIN rolling_form hf ON m.match_id = hf.match_id AND hf.venue = 'home'
JOIN rolling_form af ON m.match_id = af.match_id AND af.venue = 'away';