import json
from fetch import fetch_page
from parse import parse_listings
from clean import clean_records
from dedupe import dedupe_records

SOURCE_NAME = "Sulekha"
CATEGORY_NAME = "Packers and Movers"


def scrape_city(city, max_records, max_consecutive_failures=15):
    """
    Scrapes a single city until max_records raw listings are collected
    or pagination genuinely ends. Returns a list of raw listing dicts.
    """
    city_raw = []
    page = 1
    consecutive_failures = 0

    while len(city_raw) < max_records:
        print(f"Fetching {city} page {page}...")
        html = fetch_page(city, page)

        if html is None:
            consecutive_failures += 1
            print(f"  {city} page {page} failed ({consecutive_failures} consecutive failures)")
            if consecutive_failures >= max_consecutive_failures:
                print(f"  Too many consecutive failures for {city} — stopping this city.")
                break
            page += 1
            continue

        consecutive_failures = 0

        page_listings = parse_listings(html, source=SOURCE_NAME, default_category=CATEGORY_NAME)
        if not page_listings:
            print(f"  No listings found on {city} page {page} — stopping this city.")
            break

        city_raw.extend(page_listings)
        print(f"  -> {len(page_listings)} listings found, {city} total: {len(city_raw)}")
        page += 1

    print(f"Finished {city}: {len(city_raw)} raw records collected\n")
    return city_raw


def run_scraper(cities, max_records_per_city=100, output_file="listings.json"):
    all_raw = []

    for city in cities:
        print(f"=== Scraping city: {city} ===")
        city_raw = scrape_city(city, max_records_per_city)
        all_raw.extend(city_raw)

    print(f"Finished all cities. Total raw records: {len(all_raw)}")

    cleaned = clean_records(all_raw)
    final = dedupe_records(cleaned)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(final)} final records to {output_file}")
    return final


if __name__ == "__main__":
    CITIES = ["mumbai", "delhi", "chennai", "bangalore", "pune", "kolkata"]
    run_scraper(cities=CITIES, max_records_per_city=100, output_file="listings_multicity.json")