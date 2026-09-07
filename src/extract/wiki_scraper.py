import uuid
import requests
from bs4 import BeautifulSoup
from src.db import get_connection

def run():
    """Extract stadium history from Wikipedia into bronze layer."""
    print("3/3 Extracting stadiums and history from Wikipedia...")
    url = "https://en.wikipedia.org/wiki/List_of_Premier_League_stadiums"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    
    if resp.status_code != 200:
        print(f"  Error fetching Wikipedia page: HTTP {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", {"class": "wikitable"})
    
    if not table:
        print("  Stadium table not found on Wikipedia.")
        return

    run_id = str(uuid.uuid4())

    conn = get_connection()
    cur = conn.cursor()
    
    count = 0
    rows = table.find_all("tr")

    for row in rows[1:]:
        cols = row.find_all(["td", "th"])
        if len(cols) >= 7:
            stadium_name = cols[0].get_text(strip=True)
            club_raw = cols[2].get_text(strip=True)
            opened_str = cols[4].get_text(strip=True)
            closed_str = cols[5].get_text(strip=True)
            cap_str = cols[6].get_text(strip=True).replace(",", "").rstrip("†").split("[")[0]

            if not stadium_name or not club_raw:
                continue

            # Skip rows without a valid club (e.g. Wikipedia "N/a[nb 1]" entries)
            if "n/a" in club_raw.lower() or "[nb" in club_raw.lower():
                continue

            cur.execute(
                """INSERT INTO raw.wiki_stadiums 
                   (run_id, raw_wiki_club, raw_stadium_name, raw_capacity, raw_opened, raw_closed) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (run_id, club_raw, stadium_name, cap_str, opened_str, closed_str)
            )
            count += 1
                
    print(f"  {count} stadium records saved to raw.wiki_stadiums.")
    conn.commit()
    cur.close()
    conn.close()
    print(f"  Run ID: {run_id}")

if __name__ == "__main__":
    run()