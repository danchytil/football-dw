from src.db import get_connection


# CHECK REGISTRY
# Each check returns (passed: bool, detail: str)

BRONZE_CHECKS = []
SILVER_CHECKS = []
GOLD_CHECKS = []

def bronze_check(name):
    def decorator(fn):
        BRONZE_CHECKS.append((name, fn))
        return fn
    return decorator

def silver_check(name):
    def decorator(fn):
        SILVER_CHECKS.append((name, fn))
        return fn
    return decorator

def gold_check(name):
    def decorator(fn):
        GOLD_CHECKS.append((name, fn))
        return fn
    return decorator


# BRONZE CHECKS: run after extractors

@bronze_check("api_matches is not empty")
def _(cur):
    cur.execute("SELECT COUNT(*) FROM raw.api_matches;")
    count = cur.fetchone()[0]
    return count > 0, f"{count} rows"

@bronze_check("transfermarkt_values is not empty")
def _(cur):
    cur.execute("SELECT COUNT(*) FROM raw.transfermarkt_values;")
    count = cur.fetchone()[0]
    return count > 0, f"{count} rows"

@bronze_check("wiki_stadiums is not empty")
def _(cur):
    cur.execute("SELECT COUNT(*) FROM raw.wiki_stadiums;")
    count = cur.fetchone()[0]
    return count > 0, f"{count} rows"

@bronze_check("no NULL payloads in api_matches")
def _(cur):
    cur.execute("SELECT COUNT(*) FROM raw.api_matches WHERE payload IS NULL;")
    count = cur.fetchone()[0]
    return count == 0, f"{count} NULL payloads"

@bronze_check("no NULL team names in transfermarkt")
def _(cur):
    cur.execute("SELECT COUNT(*) FROM raw.transfermarkt_values WHERE raw_team_name IS NULL;")
    count = cur.fetchone()[0]
    return count == 0, f"{count} NULL names"

@bronze_check("no invalid wiki entries (N/a)")
def _(cur):
    cur.execute("SELECT COUNT(*) FROM raw.wiki_stadiums WHERE raw_wiki_club ILIKE '%n/a%';")
    count = cur.fetchone()[0]
    return count == 0, f"{count} invalid entries"

# SILVER CHECKS: run after to_silver.py

@silver_check("teams table is not empty")
def _(cur):
    cur.execute("SELECT COUNT(*) FROM silver.teams;")
    count = cur.fetchone()[0]
    return count > 0, f"{count} teams"

@silver_check("no duplicate match_id")
def _(cur):
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT match_id FROM silver.matches 
            GROUP BY match_id HAVING COUNT(*) > 1
        ) dupes;
    """)
    count = cur.fetchone()[0]
    return count == 0, f"{count} duplicates"

@silver_check("every match team exists in teams table")
def _(cur):
    cur.execute("""
        SELECT COUNT(*) FROM silver.matches m
        WHERE NOT EXISTS (SELECT 1 FROM silver.teams t WHERE t.team_id = m.home_team_id)
           OR NOT EXISTS (SELECT 1 FROM silver.teams t WHERE t.team_id = m.away_team_id);
    """)
    count = cur.fetchone()[0]
    return count == 0, f"{count} orphan matches"

@silver_check("no team plays against itself")
def _(cur):
    cur.execute("SELECT COUNT(*) FROM silver.matches WHERE home_team_id = away_team_id;")
    count = cur.fetchone()[0]
    return count == 0, f"{count} self-matches"

@silver_check("380 matches per season (20 teams)")
def _(cur):
    cur.execute("""
        SELECT season_id, COUNT(*) AS cnt
        FROM silver.matches 
        GROUP BY season_id 
        HAVING COUNT(*) != 380;
    """)
    bad = cur.fetchall()
    if bad:
        detail = ", ".join([f"{s}: {c}" for s, c in bad])
        return False, detail
    return True, "all seasons correct"

@silver_check("no team has multiple active stadiums")
def _(cur):
    cur.execute("""
        SELECT t.display_name, COUNT(*) 
        FROM silver.stadium_history sh
        JOIN silver.teams t ON t.team_id = sh.team_id
        WHERE sh.closed_date IS NULL 
        GROUP BY t.display_name HAVING COUNT(*) > 1;
    """)
    multi = cur.fetchall()
    if multi:
        detail = ", ".join([f"{name}: {cnt}" for name, cnt in multi])
        return False, detail
    return True, "all teams have 0 or 1 active stadium"

@silver_check("market values are positive and reasonable")
def _(cur):
    cur.execute("""
        SELECT COUNT(*) FROM silver.team_market_values 
        WHERE market_value_eur <= 0 OR market_value_eur > 5000000000;
    """)
    count = cur.fetchone()[0]
    return count == 0, f"{count} invalid values"

@silver_check("every season has market values")
def _(cur):
    cur.execute("""
        SELECT s.season_id FROM silver.seasons s
        WHERE NOT EXISTS (
            SELECT 1 FROM silver.team_market_values tmv 
            WHERE tmv.season_id = s.season_id
        );
    """)
    missing = cur.fetchall()
    if missing:
        return False, f"missing: {[s[0] for s in missing]}"
    return True, "all seasons have valuations"

@silver_check("all raw names matched via xref")
def _(cur):
    cur.execute("""
        SELECT x.source_name, x.source_system 
        FROM silver.team_name_xref x
        WHERE NOT EXISTS (
            SELECT 1 FROM silver.teams t 
            WHERE t.canonical_name = x.canonical_name
        );
    """)
    unmatched = cur.fetchall()
    if unmatched:
        detail = ", ".join([f"{name} ({sys})" for name, sys in unmatched[:5]])
        return False, f"{len(unmatched)} unmatched: {detail}"
    return True, "all names matched"

@silver_check("no negative goals in matches")
def _(cur):
    cur.execute("""
        SELECT COUNT(*) FROM silver.matches 
        WHERE home_goals < 0 OR away_goals < 0;
    """)
    count = cur.fetchone()[0]
    return count == 0, f"{count} negative goals"

@silver_check("match results are consistent with goals")
def _(cur):
    cur.execute("""
        SELECT COUNT(*) FROM silver.matches
        WHERE (home_goals > away_goals AND result != 'H')
           OR (home_goals < away_goals AND result != 'A')
           OR (home_goals = away_goals AND result != 'D');
    """)
    count = cur.fetchone()[0]
    return count == 0, f"{count} inconsistent results"


# GOLD CHECKS: run after to_gold.py

@gold_check("fct_team_season has 20 teams per season")
def _(cur):
    cur.execute("""
        SELECT season_id, COUNT(*) AS cnt
        FROM gold.fct_team_season 
        GROUP BY season_id 
        HAVING COUNT(*) != 20;
    """)
    bad = cur.fetchall()
    if bad:
        detail = ", ".join([f"{s}: {c}" for s, c in bad])
        return False, detail
    return True, "all seasons have 20 teams"

@gold_check("each team played 38 matches per season")
def _(cur):
    cur.execute("""
        SELECT season_id, team_id, matches_played 
        FROM gold.fct_team_season 
        WHERE matches_played != 38;
    """)
    bad = cur.fetchall()
    return len(bad) == 0, f"{len(bad)} teams with wrong match count"

@gold_check("no duplicate matches in fct_match")
def _(cur):
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT match_id FROM gold.fct_match 
            GROUP BY match_id HAVING COUNT(*) > 1
        ) dupes;
    """)
    count = cur.fetchone()[0]
    return count == 0, f"{count} duplicates"

@gold_check("league positions are 1-20 per season")
def _(cur):
    cur.execute("""
        SELECT season_id, MIN(league_position), MAX(league_position)
        FROM gold.fct_team_season
        GROUP BY season_id
        HAVING MIN(league_position) != 1 OR MAX(league_position) > 20;
    """)
    bad = cur.fetchall()
    return len(bad) == 0, f"{bad if bad else 'all correct'}"

@gold_check("dim_team has no duplicate teams")
def _(cur):
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT team_id FROM gold.dim_team 
            GROUP BY team_id HAVING COUNT(*) > 1
        ) dupes;
    """)
    count = cur.fetchone()[0]
    return count == 0, f"{count} duplicates"

@gold_check("ml_features has no duplicate matches")
def _(cur):
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT match_id FROM gold.ml_features 
            GROUP BY match_id HAVING COUNT(*) > 1
        ) dupes;
    """)
    count = cur.fetchone()[0]
    return count == 0, f"{count} duplicates"


# RUNNER

def _run_checks(checks, layer_name):
    """Execute a list of checks and report results."""
    conn = get_connection()
    cur = conn.cursor()

    passed = 0
    failed = 0

    print(f"\n  [{layer_name.upper()}]")
    for name, fn in checks:
        try:
            ok, detail = fn(cur)
            status = "PASS" if ok else "FAIL"
            if ok:
                passed += 1
            else:
                failed += 1
            print(f" {status}: {name} ({detail})")
        except Exception as e:
            failed += 1
            print(f"ERROR: {name} ({e})")

    cur.close()
    conn.close()
    return passed, failed


def run_bronze():
    """Quality gate after extractors."""
    print("Running Bronze quality checks...")
    passed, failed = _run_checks(BRONZE_CHECKS, "bronze")
    print(f"\n  Bronze: {passed} passed, {failed} failed")
    if failed > 0:
        raise SystemExit(f"Bronze quality gate failed: {failed} check(s)")


def run_silver():
    """Quality gate after to_silver.py."""
    print("Running Silver quality checks...")
    passed, failed = _run_checks(SILVER_CHECKS, "silver")
    print(f"\n  Silver: {passed} passed, {failed} failed")
    if failed > 0:
        raise SystemExit(f"Silver quality gate failed: {failed} check(s)")


def run_gold():
    """Quality gate after to_gold.py."""
    print("Running Gold quality checks...")
    passed, failed = _run_checks(GOLD_CHECKS, "gold")
    print(f"\n  Gold: {passed} passed, {failed} failed")
    if failed > 0:
        raise SystemExit(f"Gold quality gate failed: {failed} check(s)")


def run():
    """Run all quality checks across all layers."""
    print("Running all data quality checks...")
    
    total_passed = 0
    total_failed = 0
    
    for layer, checks in [("bronze", BRONZE_CHECKS), ("silver", SILVER_CHECKS), ("gold", GOLD_CHECKS)]:
        p, f = _run_checks(checks, layer)
        total_passed += p
        total_failed += f

    total = total_passed + total_failed
    print(f"\n Total: {total_passed}/{total} passed, {total_failed} failed")
    if total_failed > 0:
        raise SystemExit(f"Quality gate failed: {total_failed} check(s)")


if __name__ == "__main__":
    run()