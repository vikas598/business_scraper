import json
from fetch import fetch_page
from parse import parse_listings
from clean import clean_records
from dedupe import dedupe_records

SOURCE_NAME = "Sulekha"
CATEGORY_NAME = "Packers and Movers" 


def run_scraper(max_records=20, start_page=1, output_file="listings.json", max_consecutive_failures=15):
    all_raw = []
    page = start_page
    consecutive_failures = 0

    while len(all_raw) < max_records:
        print(f"Fetching page {page}...")
        html = fetch_page(page)

        if html is None:
            consecutive_failures += 1
            print(f"Page {page} failed ({consecutive_failures} consecutive failures)")
            if consecutive_failures >= max_consecutive_failures:
                print("Too many consecutive failures — assuming end of pagination.")
                break
            page += 1
            continue  # skip this page, try the next one
        
        consecutive_failures = 0  # reset on success

        page_listings = parse_listings(html, source=SOURCE_NAME, default_category=CATEGORY_NAME)
        if not page_listings:
            print(f"No listings found on page {page} — skipping.")
            page += 1
            continue

        all_raw.extend(page_listings)
        print(f"  -> {len(page_listings)} listings found, total raw so far: {len(all_raw)}")
        page += 1

    print(f"\nFinished fetching. Total raw records: {len(all_raw)}")
    
    # Clean and validate
    cleaned = clean_records(all_raw)

    # Deduplicate
    final = dedupe_records(cleaned)

    # Trim to exactly max_records if we overshot (buffer is fine, but let's cap cleanly)
    final = final[:max_records] if len(final) > max_records else final

    # Save to JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(final)} final records to {output_file}")
    return final


if __name__ == "__main__":
    run_scraper(max_records=500, output_file="listings_test500.json")