from src.extract import football_api, transfermarkt, wiki_scraper
from src.transform import to_silver, to_gold
from src.quality.checks import run_bronze, run_silver, run_gold

def main():
    # 1. Extract to bronze
    print("\n=== EXTRACTION (Bronze) ===")
    football_api.run()
    transfermarkt.run()
    wiki_scraper.run()

    # 2. Quality gate: bronze
    print("\n=== QUALITY CHECK (Bronze) ===")
    run_bronze()

    # 3. Transform to silver
    print("\n=== TRANSFORMATION (Silver) ===")
    to_silver.run()

    # 4. Quality gate: silver
    print("\n=== QUALITY CHECK (Silver) ===")
    run_silver()

    # 5. Refresh gold
    print("\n=== REFRESH (Gold) ===")
    to_gold.run()

    # 6. Quality gate: gold
    print("\n=== QUALITY CHECK (Gold) ===")
    run_gold()

if __name__ == "__main__":
    main()