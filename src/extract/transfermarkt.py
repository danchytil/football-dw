import os
import time
import uuid
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from src.db import get_connection

load_dotenv()

def parse_market_value(val_str: str) -> str:
    """Clean raw text value from the table."""
    if not val_str or val_str.strip() in ["-", ""]:
        return None
    return val_str.strip()

def run(seasons=None):
    """Extract team financial data from Transfermarkt into bronze layer."""
    if seasons is None:
        seasons = os.getenv("TARGET_SEASONS", "2023,2024,2025").split(",")

    print("2/3 Extracting financial data from Transfermarkt...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    run_id = str(uuid.uuid4())
    
    conn = get_connection()
    cur = conn.cursor()
    
    total_inserted = 0
    
    for season in seasons:
        url = f"https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1/plus/?saison_id={season}"
        resp = requests.get(url, headers=headers)
        
        if resp.status_code != 200:
            print(f"  Error downloading season {season}: HTTP {resp.status_code}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        
        table = soup.find("table", class_="items")
        if not table or not table.find("tbody"):
            print(f"  Table not found for season {season}.")
            continue

        rows = table.find("tbody").find_all("tr", recursive=False)
        season_count = 0
        
        for tr in rows:
            tds = tr.find_all("td")
            
            if len(tds) >= 7:
                club_cell = tr.find("td", class_="hauptlink")
                if not club_cell:
                    continue
                    
                team_name = club_cell.get_text(strip=True)
                
                squad_size = tds[-5].get_text(strip=True)
                avg_age = tds[-4].get_text(strip=True)
                market_val = parse_market_value(tds[-1].get_text(strip=True))
                
                cur.execute(
                    """INSERT INTO raw.transfermarkt_values 
                       (run_id, season, raw_team_name, market_value_str, squad_size_str, avg_age_str) 
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (run_id, season, team_name, market_val, squad_size, avg_age)
                )
                season_count += 1
                
        print(f"  Season {season}: {season_count} clubs saved.")
        total_inserted += season_count
        
        time.sleep(3)
        
    conn.commit()
    cur.close()
    conn.close()
    print(f"  Total: {total_inserted} records inserted.")
    print(f"  Run ID: {run_id}")

if __name__ == "__main__":
    run()