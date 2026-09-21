import os
import uuid
import pandas as pd
from dotenv import load_dotenv
from src.db import get_connection

load_dotenv()


def run(seasons=None):
    """Load team financial data from Kaggle CSV files into bronze layer.

    Expects three CSV files in data/kaggle/:
        - players.csv          (player_id, name, current_club_id, date_of_birth, ...)
        - player_valuations.csv (player_id, date, market_value_in_eur, current_club_id, ...)
        - clubs.csv            (club_id, name, domestic_competition_id, ...)
    """
    if seasons is None:
        seasons = os.getenv("TARGET_SEASONS", "2023,2024,2025").split(",")

    print("2/3 Loading financial data from Kaggle dataset...")

    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "kaggle")

    # --- Load CSVs -----------------------------------------------------------
    try:
        players = pd.read_csv(os.path.join(data_dir, "players.csv"))
        valuations = pd.read_csv(os.path.join(data_dir, "player_valuations.csv"))
        clubs = pd.read_csv(os.path.join(data_dir, "clubs.csv"))
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Kaggle CSV files not found in {data_dir}. "
            "Download from https://www.kaggle.com/datasets/davidcariboo/player-scores "
            "and place players.csv, player_valuations.csv, and clubs.csv there."
        ) from e

    # --- Filter Premier League clubs -----------------------------------------
    pl_club_ids = clubs.loc[
        clubs["domestic_competition_id"] == "GB1", "club_id"
    ].tolist()

    valuations["date"] = pd.to_datetime(valuations["date"])
    players["date_of_birth"] = pd.to_datetime(players["date_of_birth"], errors="coerce")

    run_id = str(uuid.uuid4())
    conn = get_connection()
    cur = conn.cursor()
    total_inserted = 0

    for season in seasons:
        season_year = int(season)

        # Season window: Aug – Jun
        season_start = pd.Timestamp(f"{season_year}-08-01")
        season_end = pd.Timestamp(f"{season_year + 1}-06-30")

        # Valuations for PL clubs within season window
        mask = (
            (valuations["current_club_id"].isin(pl_club_ids))
            & (valuations["date"] >= season_start)
            & (valuations["date"] <= season_end)
        )
        season_vals = valuations.loc[mask].copy()

        if season_vals.empty:
            print(f"  Season {season}: no valuation data found, skipping.")
            continue

        # Keep latest valuation per player in the season
        season_vals = (
            season_vals.sort_values("date")
            .drop_duplicates(subset=["player_id"], keep="last")
        )

        # Merge player age
        season_vals = season_vals.merge(
            players[["player_id", "date_of_birth"]], on="player_id", how="left"
        )
        season_vals["age"] = season_vals["date_of_birth"].apply(
            lambda dob: season_year - dob.year if pd.notna(dob) else None
        )

        # Merge club name
        season_vals = season_vals.merge(
            clubs[["club_id", "name"]],
            left_on="current_club_id",
            right_on="club_id",
            how="left",
        )

        # Aggregate per club
        team_stats = (
            season_vals.groupby("name")
            .agg(
                market_value_eur=("market_value_in_eur", "sum"),
                squad_size=("player_id", "count"),
                avg_age=("age", "mean"),
            )
            .reset_index()
        )

        season_count = 0
        for _, row in team_stats.iterrows():
            cur.execute(
                """INSERT INTO raw.kaggle_values
                   (run_id, season, raw_team_name, market_value_eur, squad_size, avg_age)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    run_id,
                    str(season_year),
                    row["name"],
                    int(row["market_value_eur"]) if pd.notna(row["market_value_eur"]) else None,
                    int(row["squad_size"]),
                    round(float(row["avg_age"]), 1) if pd.notna(row["avg_age"]) else None,
                ),
            )
            season_count += 1

        print(f"  Season {season}: {season_count} clubs loaded to bronze.")
        total_inserted += season_count

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Total: {total_inserted} records inserted.")
    print(f"  Run ID: {run_id}")


if __name__ == "__main__":
    run()