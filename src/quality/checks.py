from pathlib import Path
from src.db import get_connection

SQL_DIR = Path(__file__).resolve().parent / "sql_quality"


def _run_sql_file(layer_name: str, file_name: str):
    """Executes a single SQL script for the layer. Any returned rows indicate failures."""
    sql_path = SQL_DIR / file_name

    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found at: {sql_path}")

    query = sql_path.read_text(encoding="utf-8")

    conn = get_connection()
    cur = conn.cursor()

    print(f"Running {layer_name.upper()} quality checks...")
    try:
        cur.execute(query)
        errors = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    if errors:
        error_details = "\n  - ".join([str(row[0]) for row in errors[:5]])
        raise SystemExit(
            f"{layer_name.upper()} quality gate failed ({len(errors)} issue(s)):\n  - {error_details}"
        )

    print(f"{layer_name.upper()} quality checks passed!")


def run_bronze():
    _run_sql_file("bronze", "01_bronze_check.sql")


def run_silver():
    _run_sql_file("silver", "02_silver_check.sql")


def run_gold():
    _run_sql_file("gold", "03_gold_check.sql")