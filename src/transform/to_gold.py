from src.db import get_connection

def run():
    """Refresh all Gold materialized views (Kimball star schema)."""
    print("Refreshing Gold materialized views...")
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Dimensions first (facts may depend on them in Power BI)
        cur.execute("REFRESH MATERIALIZED VIEW gold.dim_team;")
        print("dim_team refreshed.")

        cur.execute("REFRESH MATERIALIZED VIEW gold.dim_season;")
        print("dim_season refreshed.")

        cur.execute("REFRESH MATERIALIZED VIEW gold.dim_date;")
        print("dim_date refreshed.")

        # Facts
        cur.execute("REFRESH MATERIALIZED VIEW gold.fct_match;")
        print("fct_match refreshed.")

        cur.execute("REFRESH MATERIALIZED VIEW gold.fct_team_season;")
        print("fct_team_season refreshed.")

        conn.commit()
        print("Gold layer refresh completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Gold refresh error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run()