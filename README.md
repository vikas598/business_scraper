# Business Listings Dashboard

A full-stack project that scrapes business listing data, stores it in MySQL, exposes it via a FastAPI backend, and visualizes it on a React dashboard.

> **Status:** In progress. This README currently documents Phase 1 (Web Scraping), Phase 2 (Database), and Phase 3 (Backend API). The Frontend (React) section will be added once that phase is complete.

---

## Tech Stack

- **Frontend:** React.js (with a charting library — Recharts/Chart.js, TBD)
- **Backend:** FastAPI (Python)
- **Database:** MySQL
- **Scraping:** Python (`requests`, `BeautifulSoup4`)

---

## Project Structure

```
business_scraper/
  .env                  # DB credentials (not committed — see .gitignore)
  .gitignore
  schema.sql             # Full MySQL schema
  venv/
  app/
    db.py                 # MySQL connection + reusable query/insert functions
    insert_data.py        # CLI script to bulk-load a scraped JSON file into MySQL
    main.py                # FastAPI app: bulk-insert + aggregation endpoints
    scraper/
      fetch.py             # Page fetching: retries, timeout, redirect/end-of-pagination handling
      parse.py              # HTML -> raw field extraction
      clean.py               # Validation, normalization, city/pincode extraction
      dedupe.py               # Duplicate removal across the full scraped batch
      run_scraper.py           # Orchestrates fetch -> parse -> clean -> dedupe -> save
      listings_test500.json     # Latest full scrape output
```

---

## Phase 1: Web Scraping

### Data Source

**Source chosen:** [Sulekha](https://www.sulekha.com) — "Packers and Movers" category listings, scraped across multiple cities to reach the required volume (`https://www.sulekha.com/packers-and-movers/mumbai`, plus additional city/category searches), using page-based pagination (`/page-2`, `/page-3`, ...).

**Why Sulekha over Google Maps / Justdial:**
The assignment listed Google Maps, Justdial, Sulekha, or any other business directory as acceptable, but also explicitly instructed to avoid scraping in violation of a site's Terms of Service. Google Maps and Justdial both explicitly prohibit scraping in their ToS and run aggressive anti-bot/CAPTCHA systems that make reliable large-scale collection risky within a short assignment timeline. Sulekha was chosen as a lower-risk, India-relevant alternative that still provided all required fields at sufficient volume.

### Source Investigation Process

Before writing any scraper code, the site was manually investigated using browser DevTools:

1. **View Page Source** showed listing data present in the initial server-rendered HTML.
2. The "View More" button had `onclick="event.preventDefault()"` and triggered a `listingsV3` XHR call (visible in the Network tab) — suggesting a JS-driven load.
3. However, the same button also carried a real `href` pointing to `.../page-2`. Visiting that URL directly confirmed these are **fully server-rendered pages**, each returning ~10 additional listings.
4. Pagination was tested to its limit: page 99 returns valid content; page 100 redirects back to page 1 — used as one signal of "end of pagination."
5. **An additional quirk was discovered during testing:** pages 10–19 (for the Mumbai/packers-and-movers search) consistently redirected to page 1, while pages 20 and beyond returned genuine, distinct listings again — confirmed by manually comparing business names across pages, and reproduced on a different category search as well. This was treated as a real, reproducible gap in Sulekha's pagination rather than a rate-limiting artifact (it was consistent across separate manual tests, not just rapid automated requests) and the scraper was made resilient to it (see Reliability Measures below).

**Conclusion:** despite the site's UI using dynamic (JS-triggered) loading for convenience, the underlying paginated URLs are static and fully scrapeable with simple HTTP requests. A browser automation tool (Playwright/Selenium) was therefore **not required** for this data source.

### Tool Choice: Requests + BeautifulSoup

| Tool | Considered | Decision |
|---|---|---|
| Requests + BeautifulSoup | ✅ | **Used** — sufficient since pages are server-rendered |
| Playwright | Considered | Not needed for this source; would be the correct choice for a target lacking static paginated URLs |
| Selenium | Considered | Skipped in favor of Playwright's more modern API, had a browser tool been necessary |

### Fields Captured

| Field | Extraction approach |
|---|---|
| `business_name` | From each card's `<h3>` tag |
| `category` | Preferentially from the card's service tag (`span.bg-gray-100`); falls back to the search page's category context (derived from the URL) when a card has no service tags — see Data Quality Notes |
| `city` | Parsed from the card's `<address>` text (format: `[Locality,] City, Pincode`), extracted as the segment immediately before the pincode |
| `address` | Full raw text of the `<address>` tag, stored as-is |
| `pincode` | Parsed from the same `<address>` text — the final comma-separated segment, only accepted if it is purely numeric and 5–6 digits long (guards against misclassifying a locality-only address as a pincode) |
| `phone` | From `a[href^='tel:']` when present; stored as `NULL` when absent |
| `source` | Constant value `"Sulekha"`, set by the scraper |

### Scraper Architecture

```
scraper/
  fetch.py        -> Fetches raw HTML for a given page number (network layer only)
  parse.py        -> Extracts raw field values from HTML into dicts (no validation)
  clean.py         -> Validates, normalizes, and derives fields (city, pincode); pure data logic
  dedupe.py        -> Removes duplicate listings from the full collected batch
  run_scraper.py   -> Orchestrates fetch -> parse -> clean -> dedupe -> save, with a max_records parameter
```

Each module has a single responsibility and can be tested independently — e.g. `clean.py` is tested with plain Python dicts, with no network or HTML involved. This made it straightforward to isolate and fix issues (such as the category-extraction bug below) without touching unrelated modules.

### Handling Missing Values

- `phone` is optional by design — observed present on roughly 7–8% of listings. Missing values are stored as `NULL`, never as empty strings or placeholders.
- `business_name`, `category`, and `city` are required; records missing any of these are dropped during cleaning.
- Length sanity checks (e.g., `business_name` under 200 characters) guard against parsing bugs that might capture an oversized, wrong chunk of HTML.

### Data Quality Notes / Known Limitations

- **No full street address available.** Sulekha's listing/search pages show only `Locality, City, Pincode`, not a complete street address. Retrieving a full address would require an additional request per listing to each business's profile page — not feasible at 500+ record scale within the timeline. The available string is stored in `address` as the closest available approximation, with `city` and `pincode` additionally parsed out into their own columns.
- **Category fallback.** Initial testing at 100 records showed ~43% of records being dropped due to `category` coming back empty — traced to many listing cards (likely non-premium listings) not rendering individual service tags at all. Fixed by falling back to the category implied by the search page's URL/context when a card-level tag isn't present. This is documented in code and reflects a deliberate, verified design decision rather than an oversight.
- **Category simplification.** Where a card lists multiple services, only the first is used as the primary `category`, since the schema stores one category per business.
- **Duplicate handling.** Deduplication (within a single scrape run) uses a composite key of normalized `business_name` + `city`. Duplicate handling **across** separate scrape runs/insert operations is additionally enforced at the database level (see Phase 2).

### Reliability Measures

- **Retry logic:** each page fetch retries up to 3 times with exponential backoff (2s, 4s, 8s) on network errors, failed HTTP statuses, or redirects, before giving up on that specific page.
- **Timeouts:** every request has a 10-second timeout.
- **Rate limiting:** a short, slightly randomized delay is added between requests.
- **Tolerance for non-monotonic pagination gaps:** rather than treating the first redirected/failed page as the definitive end of data, the scraper's page loop tolerates up to `max_consecutive_failures` (set to 15) consecutive failed pages before concluding pagination has genuinely ended — resetting this counter on every successful page. This was specifically required to correctly scrape past the pages 10–19 gap described above, while still reliably stopping once the real end of pagination (around page 100) is reached.

### Incremental Testing Strategy

The scraper's orchestration function accepts a `max_records` parameter:

1. **20 records** — verify field extraction correctness.
2. **100 records** — exercises pagination across multiple pages; surfaced both the category-fallback bug and the pagination-gap behavior described above.
3. **500+ records** — full run. An initial single-category/city run yielded 470 clean, deduplicated records; an additional city/category was scraped using the same pipeline to comfortably clear the 500-record requirement.

---

## Phase 2: Database (MySQL)

### Schema

```sql
CREATE DATABASE IF NOT EXISTS business_dashboard;
USE business_dashboard;

CREATE TABLE listing_master (
    id INT AUTO_INCREMENT PRIMARY KEY,
    business_name VARCHAR(255) NOT NULL,
    category VARCHAR(150) NOT NULL,
    city VARCHAR(100) NOT NULL,
    address VARCHAR(500),
    pincode VARCHAR(10),
    phone VARCHAR(20),
    source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_listing (business_name, city, source)
);
```

**Design decisions:**
- `NOT NULL` on `business_name`, `category`, `city`, `source` mirrors the validation already enforced in `clean.py` — defense in depth, so a bug in the Python layer can't silently insert incomplete data.
- `pincode` is stored as `VARCHAR(10)`, not `INT` — it's an identifier, not a quantity (no aggregation like `AVG()` or `SUM()` would ever make sense on it), and `VARCHAR` avoids any risk of leading zeros or non-numeric formats being silently mishandled.
- `created_at` is auto-populated by MySQL (`DEFAULT CURRENT_TIMESTAMP`) — never set manually from application code.
- `UNIQUE KEY (business_name, city, source)` prevents duplicate rows if the same scrape data is inserted more than once (e.g., during testing, or if the scraper is re-run later) — this is a different, complementary protection to the in-memory deduplication done in `dedupe.py`, which only catches duplicates *within* a single scrape batch.

### Connection & Insert Layer (`db.py`)

- Credentials are read from a `.env` file (via `python-dotenv`) and never hardcoded — `.env` is excluded from version control via `.gitignore`.
- `insert_listings()` performs a bulk insert using `ON DUPLICATE KEY UPDATE`, meaning re-running an insert with overlapping data safely updates existing rows (address/pincode/phone) rather than erroring or creating duplicate rows.
- Insert failures are handled per-record (one bad record doesn't abort the whole batch), and a single commit is issued after the full batch for performance.

### Current Row Count

470+ records inserted successfully as of the last full pipeline run (topped up with an additional scrape batch to clear the 500+ requirement — see Phase 1).

---

## Phase 3: Backend API (FastAPI)

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/listings/bulk-insert` | Accepts a JSON list of listings and bulk-inserts them into `listing_master` |
| `GET` | `/stats/city-wise` | Returns listing counts grouped by city |
| `GET` | `/stats/category-wise` | Returns listing counts grouped by category |
| `GET` | `/stats/source-wise` | Returns listing counts grouped by source |

Interactive documentation (Swagger UI) is auto-generated by FastAPI and available at `/docs` when the server is running.

### Design Notes

- **Request validation via Pydantic models** — the bulk-insert endpoint defines a `Listing` model matching the database schema (required vs optional fields mirrored exactly), so malformed requests are rejected automatically with a clear error, before any application code runs.
- **Shared query logic** — all three aggregation endpoints call one underlying `get_counts_by(column)` function in `db.py`, parameterized by column name, rather than duplicating near-identical SQL three times.
- **Aggregation queries use a fixed, code-controlled set of column names** (`city`, `category`, `source`) — never derived from user input — to avoid any SQL injection risk from the dynamic column name in the query string.
- Rows are returned as dictionaries (`cursor(dictionary=True)`) rather than raw tuples, so API responses are directly usable JSON (`{"label": ..., "count": ...}`) without manual field-mapping — this shape also maps cleanly onto chart libraries on the frontend.

### Running the Backend

```bash
cd app
uvicorn main:app --reload
```
Server runs at `http://127.0.0.1:8000`; interactive docs at `http://127.0.0.1:8000/docs`.

---

## Current Status

- [x] Scraper built and verified at 20 / 100 / 500+ records
- [x] MySQL schema created (`listing_master`, with `pincode` as an added column beyond the original spec)
- [x] Bulk data load from scraped JSON into MySQL (`insert_data.py`)
- [x] FastAPI bulk-insert endpoint
- [x] FastAPI aggregation endpoints (city-wise, category-wise, source-wise)
- [ ] Manual API edge-case testing (empty table, invalid payloads)
- [ ] React dashboard
- [ ] Final README sections (Setup Instructions, Challenges Faced, Demo Video)
- [ ] SQL dump for submission

---

*(Further sections — Frontend Setup, full Setup Instructions, Challenges Faced, and Demo Video link — will be appended as subsequent phases are completed.)*
