import os
import json
import uuid
import requests
from dotenv import load_dotenv
from src.db import get_connection

load_dotenv()

def run(seasons=None):
    """Extract match data from football-data.org API into bronze layer."""
    if seasons is None:
        seasons = os.getenv("TARGET_SEASONS", "2023,2024,2025").split(",")

    print("1/3 Getting data from football-data.org API...")
    api_key = os.getenv("FOOTBALL_API_KEY")
    if not api_key:
        raise ValueError("Missing FOOTBALL_API_KEY in .env file")
        
    headers = {"X-Auth-Token": api_key}
    run_id = str(uuid.uuid4())
    
    conn = get_connection()
    cur = conn.cursor()
    
    for season in seasons:
        url = f"https://api.football-data.org/v4/competitions/PL/matches?season={season}&status=FINISHED"
        resp = requests.get(url, headers=headers)
        
        if resp.status_code == 200:
            matches = resp.json().get("matches", [])
            for match in matches:
                cur.execute(
                    "INSERT INTO raw.api_matches (run_id, season, payload) VALUES (%s, %s, %s)",
                    (run_id, season, json.dumps(match))
                )
            print(f"  Season {season}: {len(matches)} matches loaded to bronze.")
        else:
            print(f"  API error for season {season}: HTTP {resp.status_code}")
            
    conn.commit()
    cur.close()
    conn.close()
    print(f"  Run ID: {run_id}")

if __name__ == "__main__":
    run()