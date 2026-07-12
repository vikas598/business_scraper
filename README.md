# Business Listings Dashboard

A full-stack application that scrapes business listing data, stores it in MySQL, exposes it via a FastAPI backend, and visualizes it on a React dashboard.

> **Status:** Core functionality complete — scraping, database, backend API, and frontend dashboard are all built and working end-to-end. Remaining: repo restructure to match submission spec, API edge-case testing, and demo video.

---

## Tech Stack

- **Frontend:** React.js (Vite) + Recharts
- **Backend:** FastAPI (Python)
- **Database:** MySQL
- **Scraping:** Python (`requests`, `BeautifulSoup4`)

---

## Setup Instructions (Full Stack)

1. **Database:**
   ```bash
   mysql -u root -p < database/dump.sql
   ```
   (or run `schema.sql` for structure only, then use `insert_data.py` to load a fresh scrape)

2. **Backend:**
   ```bash
   cd app
   pip install -r requirements.txt   # fastapi, uvicorn, mysql-connector-python, python-dotenv
   ```
   Create a `.env` file in `app/` with:
   ```
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=yourpassword
   DB_NAME=business_dashboard
   ```
   ```bash
   uvicorn main:app --reload
   ```

3. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. Open `http://localhost:5173` — the dashboard should load charts, stats, and the listings table from the running backend.

---

## Challenges Faced

**1. Category field was empty for ~43% of listings.**
An early 100-record test batch showed a much higher drop rate than expected during cleaning. Debugging by printing the actual dropped raw records (rather than just the count) showed every dropped record had `category: None` — traced to many listing cards not rendering per-listing service tags at all (likely non-premium listings). Fixed by falling back to the category implied by the search page's URL/context whenever a card-level tag was missing, rather than dropping the record. This also turned out to be a more reliable signal than the per-card tags, since it applies to every listing on a category-specific search page unconditionally.

**2. Non-monotonic pagination gap.**
While testing pagination limits, pages 10–19 were found to consistently redirect back to page 1, while page 20 onward returned genuine new listings again — reproduced manually and on a separate category search, ruling out simple rate-limiting. The scraper's page loop initially treated any single redirect as the definitive end of data, which would have caused it to stop at page 10 and miss all remaining listings. Fixed by adding a tolerance for a run of consecutive failed pages (reset on any success) before concluding pagination had genuinely ended, rather than stopping at the first failure.

**3. Address format inconsistency when extracting city.**
Initial city-extraction logic assumed a fixed `"City, Pincode"` format and took the first comma-separated segment. Real addresses varied — some included a locality prefix (`"Andheri East, Mumbai, 400072"`), which the naive logic misread as the city. Fixed by anchoring extraction on the pincode's position (the last segment) rather than assuming a fixed number of parts, so the city is reliably the segment immediately before it regardless of whether a locality prefix is present.

**4. Phone numbers included STD/country-code prefixes inconsistently.**
Raw phone numbers came through as 11-digit strings (with a leading `0`) rather than clean 10-digit Indian mobile numbers, which wasn't caught by the initial "strip non-digits" normalization alone. Fixed by explicitly detecting and stripping a leading `91` country code (12-digit case) or a leading `0` STD prefix (11-digit case) before validating the final 10-digit length.

**5. React + Recharts crash on initial setup (`Invalid hook call`).**
Adding chart components initially crashed the whole page with a deep, unclear stack trace pointing into React's internals. Initial diagnosis suspected a duplicate React installation (a known cause of this exact error), but `npm ls react` showed only one resolved React version. Further investigation showed the actual cause was much simpler: the `recharts` package had never actually been installed (an earlier `npm install recharts` had failed silently), so the import was resolving to nothing, which produced a misleading low-level error rather than an obvious "module not found." Resolved by reinstalling and explicitly verifying with `npm ls recharts` before continuing — a reminder that unclear library errors are worth checking for a missing/failed install before assuming something more complex is wrong.

**6. CORS blocking frontend-backend communication.**
The React dev server (`localhost:5173`) and FastAPI backend (`127.0.0.1:8000`) are different origins from the browser's perspective, so the first fetch attempt was blocked by the browser's default cross-origin policy. Resolved by explicitly adding FastAPI's `CORSMiddleware`, scoped to the frontend's specific origin rather than left open to all origins, as a deliberately safer default.

**7. Reaching 500+ records from a single city/category.**
An initial full scrape of one city/category (Mumbai, packers-and-movers) yielded 470 clean records after validation and deduplication — short of the 500+ requirement. Rather than loosening validation to inflate the count, the scraper was extended to loop over multiple cities (Mumbai, Delhi, Chennai, Bangalore, Pune, Kolkata), reusing the existing fetch/clean/dedupe pipeline unchanged, which both cleared the requirement with margin and better demonstrated the scraper's generalizability.

**8. Learning React while building the frontend.**
React was new to me going into this assignment. Rather than treating it as a black box, I focused on understanding the core patterns as I built each piece — component state (`useState`), data fetching (`useEffect`), and extracting repeated logic into a reusable custom hook (`useFetchData`) once the same fetch pattern appeared across three data sources. I prioritized being able to explain and extend each piece over simply getting something on screen.
---

## Project Structure

```
business_scraper/
  .env                    # DB credentials (not committed — see .gitignore)
  .gitignore
  schema.sql               # MySQL schema only
  database/
    dump.sql                # Full MySQL dump (schema + data)
  app/                       # FastAPI backend (to be renamed backend/ per submission spec)
    db.py                     # MySQL connection, insert logic, aggregation queries
    insert_data.py             # CLI script to bulk-load a scraped JSON file into MySQL
    main.py                     # FastAPI app: all endpoints
    scraper/
      fetch.py                   # Page fetching: retries, timeout, redirect/gap handling
      parse.py                    # HTML -> raw field extraction
      clean.py                     # Validation, normalization, city/pincode/phone extraction
      dedupe.py                     # Duplicate removal across the full scraped batch
      run_scraper.py                 # Orchestrates multi-city scraping end-to-end
      listings_multicity.json         # Latest full scrape output (500+ records)
  frontend/                            # React dashboard
    src/
      App.jsx
      App.css
```

---

## Phase 1: Web Scraping

### Data Source

**Source:** [Sulekha](https://www.sulekha.com) — "Packers and Movers" category, scraped across **multiple cities** (Mumbai, Delhi, Chennai, Bangalore, Pune, Kolkata) to reach and comfortably exceed the 500-record requirement, using page-based pagination (`/page-2`, `/page-3`, ...).

**Why Sulekha over Google Maps / Justdial:** the assignment permitted either, but also explicitly required avoiding scraping that violates a site's Terms of Service. Google Maps and Justdial both prohibit scraping in their ToS and run aggressive anti-bot systems, which posed real risk to a short, fixed timeline. Sulekha was chosen as a lower-risk, India-relevant alternative that still supplied every required field.

### Source Investigation Process

Before writing scraper code, the site was manually investigated using browser DevTools:

1. **View Page Source** showed listing data present in the initial server-rendered HTML.
2. The "View More" button used `onclick="event.preventDefault()"` and triggered a `listingsV3` XHR call (visible in the Network tab) — suggesting JS-driven loading.
3. The same button also carried a real `href` pointing to `.../page-2`. Visiting that URL directly confirmed these are **fully server-rendered pages**.
4. Pagination was tested to its limit: page 99 returns valid content; page 100 redirects to page 1.
5. **A pagination gap was discovered during testing:** pages 10–19 (for the Mumbai search) consistently redirected to page 1, while page 20 onward returned genuine, distinct listings — confirmed by manually comparing business names across pages and reproduced on a different category search. Treated as a real, reproducible site quirk (not rate-limiting, since it reproduced on slow manual requests) and the scraper was made resilient to it.

**Conclusion:** despite the site's UI using dynamic loading for convenience, the underlying paginated URLs are static and fully scrapeable with simple HTTP requests — no browser automation tool (Playwright/Selenium) was required.

### Tool Choice: Requests + BeautifulSoup

| Tool | Considered | Decision |
|---|---|---|
| Requests + BeautifulSoup | ✅ | **Used** — sufficient since pages are server-rendered |
| Playwright | Considered | Not needed for this source; correct choice for a target lacking static paginated URLs |
| Selenium | Considered | Skipped in favor of Playwright's more modern API, had a browser tool been necessary |

### Fields Captured

| Field | Extraction approach |
|---|---|
| `business_name` | From each card's `<h3>` tag |
| `category` | From the card's service tag when present; falls back to the search page's category context (derived from the URL) otherwise |
| `city` | Parsed from the card's `<address>` text (format: `[Locality,] City, Pincode`) |
| `address` | Full raw text of the `<address>` tag |
| `pincode` | Parsed from the same `<address>` text; only accepted if the final comma-separated segment is purely numeric and 5–6 digits, to avoid misreading a locality-only address as a pincode |
| `phone` | From `a[href^='tel:']`; normalized to a clean 10-digit string (leading `0` STD prefix and `91` country code both stripped); stored as `NULL` if absent or if it doesn't resolve to a 10-digit number after cleanup |
| `source` | Constant value `"Sulekha"` |

### Scraper Architecture

```
scraper/
  fetch.py        -> Fetches raw HTML for a given (city, page) pair (network layer only)
  parse.py        -> Extracts raw field values from HTML into dicts
  clean.py         -> Validates, normalizes, derives fields (city, pincode, phone); pure data logic
  dedupe.py        -> Removes duplicate listings from the full collected batch
  run_scraper.py   -> Orchestrates: for each city, scrape pages -> combine -> clean -> dedupe -> save
```

`run_scraper.py` loops over a list of target cities, calling a per-city `scrape_city()` helper (itself the original single-city fetch/paginate loop) for each. Cleaning and deduplication run once, on the full multi-city batch, at the end — not per city — so a business appearing under more than one city search is still caught by deduplication. Each module remains independently testable, which made isolating real issues (see below) fast.

### Handling Missing Values

- `phone` is optional — observed present on roughly 7–8% of listings before normalization; after normalization, any number that doesn't resolve to a clean 10-digit format is also treated as missing.
- `business_name`, `category`, and `city` are required; records missing any of these are dropped during cleaning.
- Length sanity checks guard against parsing bugs capturing an oversized, wrong chunk of HTML.

### Data Quality Notes / Known Limitations

- **No full street address available** — Sulekha's listing pages show only `Locality, City, Pincode`. Retrieving a full street address would require an extra request per listing to each business's profile page — not feasible at 500+ scale within the timeline. `address` stores the available string as-is; `city` and `pincode` are additionally parsed into their own columns.
- **Category fallback** — ~43% of an early 100-record test batch was dropped due to empty `category`, traced to many listing cards (likely non-premium listings) not rendering service tags at all. Fixed by falling back to the category implied by the search page's URL/context.
- **Category simplification** — where a card lists multiple services, only the first is used as the primary category.
- **Phone number normalization is intentionally strict** — numbers are normalized to a clean 10-digit format (stripping a leading `0` STD prefix or a `91` country code). Numbers that don't resolve to exactly 10 digits after this (e.g., landlines with area codes in a different format) are stored as `NULL` rather than kept in an inconsistent format. This was a deliberate tradeoff favoring consistency over completeness for this field.
- **Duplicate handling** — deduplication within a scrape run uses a composite key of normalized `business_name` + `city`. Duplicate protection **across** separate scrape/insert runs is additionally enforced at the database level via a unique constraint (see Phase 2).

### Reliability Measures

- **Retry logic:** each page fetch retries up to 3 times with exponential backoff (2s, 4s, 8s) on network errors, failed HTTP statuses, or redirects.
- **Timeouts:** every request has a 10-second timeout.
- **Rate limiting:** a short, randomized delay between requests.
- **Tolerance for non-monotonic pagination gaps:** the per-city page loop tolerates up to 15 consecutive failed pages before concluding that city's pagination has genuinely ended, resetting the counter on every success — required to correctly scrape past the pages 10–19 gap while still stopping reliably at the real end of pagination (~page 100).
- **Per-city isolation:** each city's fetch loop has its own independent failure counter and page counter, so one city's pagination quirks don't affect any other city's run.

### Incremental Testing Strategy

1. **20 records** — verified field extraction correctness.
2. **100 records** — exercised multi-page pagination; surfaced the category-fallback bug and the pagination-gap behavior.
3. **500+ records, multi-city** — an initial single-city (Mumbai) run yielded 470 records; the scraper was extended to loop over six cities (Mumbai, Delhi, Chennai, Bangalore, Pune, Kolkata), comfortably clearing the 500-record requirement after cleaning and deduplication.

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
- `NOT NULL` on `business_name`, `category`, `city`, `source` mirrors the validation already enforced in `clean.py` — defense in depth against a Python-layer bug ever inserting incomplete data.
- `pincode` is `VARCHAR(10)`, not `INT` — it's an identifier, not a quantity; storing it as text avoids leading-zero loss and prevents nonsensical aggregation (e.g. `AVG(pincode)`).
- `created_at` is auto-populated by MySQL (`DEFAULT CURRENT_TIMESTAMP`), never set from application code.
- `UNIQUE KEY (business_name, city, source)` prevents duplicate rows across separate insert operations (e.g., re-running the scraper/insert later) — a different, complementary protection to the in-memory deduplication in `dedupe.py`.

### Connection & Insert Layer (`db.py`)

- Credentials are read from a `.env` file (via `python-dotenv`) and never hardcoded; `.env` is excluded from version control.
- `insert_listings()` performs a bulk insert using `ON DUPLICATE KEY UPDATE`, so re-running an insert with overlapping data safely updates existing rows rather than erroring or duplicating.
- Insert failures are handled per-record; a single commit is issued after the full batch for performance.

### Current Row Count

500+ records, spanning six cities, inserted successfully with zero insert failures.

### Database Dump

A full dump (schema + data) is provided at `database/dump.sql`, generated via:
```bash
mysqldump -u root -p --databases business_dashboard > database/dump.sql
```
Using `--databases` includes a `CREATE DATABASE IF NOT EXISTS` statement, so the dump can be restored against a completely empty MySQL server with no manual setup:
```bash
mysql -u root -p < database/dump.sql
```

---

## Phase 3: Backend API (FastAPI)

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/listings/bulk-insert` | Accepts a JSON list of listings and bulk-inserts them into `listing_master` |
| `GET` | `/listings` | Returns all listings currently stored (used to power the frontend's data table + CSV export) |
| `GET` | `/stats/city-wise` | Returns listing counts grouped by city |
| `GET` | `/stats/category-wise` | Returns listing counts grouped by category |
| `GET` | `/stats/source-wise` | Returns listing counts grouped by source |

Interactive documentation (Swagger UI) is auto-generated by FastAPI at `/docs`.

### Design Notes

- **Request validation via Pydantic models** — the bulk-insert endpoint defines a `Listing` model matching the database schema exactly (required vs optional fields mirrored), so malformed requests are rejected automatically with a clear error before any application code runs.
- **Shared query logic** — all three aggregation endpoints call one underlying `get_counts_by(column)` function, parameterized by column name, rather than duplicating near-identical SQL three times.
- **Aggregation queries use a fixed, code-controlled set of column names** (`city`, `category`, `source`) — never derived from user input — to avoid SQL injection risk from a dynamic column name.
- **CORS is explicitly scoped** to the frontend's dev origin (`http://localhost:5173`) rather than left open to all origins (`*`), a deliberate safer default.
- Rows are returned as dictionaries rather than raw tuples, so API responses are directly usable JSON without manual field-mapping.

### Running the Backend

```bash
cd app
uvicorn main:app --reload
```
Server runs at `http://127.0.0.1:8000`; interactive docs at `http://127.0.0.1:8000/docs`.

---

## Phase 4: Frontend Dashboard (React)

### Stack

- **Vite** for the build tool/dev server (modern standard, faster than `create-react-app`).
- **Recharts** for charting — chosen since it's built specifically for React (components rather than a wrapped non-React library) and consumes the API's `{label, count}` response shape with no transformation needed.

### Features

- **Summary stat row** — total listings, city count, category count, source count, computed client-side from already-fetched aggregation data (no extra API calls needed).
- **City-wise bar chart** and **source-wise bar chart**, each fetched from their respective aggregation endpoint.
- **Category-wise donut chart** with a custom side-by-side legend (chart + scrollable color-coded list with counts) — built instead of Recharts' built-in slice labels, which became visually cluttered with a larger number of categories.
- **Full listings table** — fetches all rows via `GET /listings`, rendered in a scrollable table with a sticky header.
- **CSV export** — a client-side "Download CSV" button that converts the fetched listings array into a CSV file and triggers a browser download, with proper quote-escaping for fields containing commas.

### Architecture Notes

- A custom hook, `useFetchData(url)`, wraps the repeated "fetch a URL, store the result in state" pattern used by every data source on the page (city/category/source stats, and the full listings list) — extracted after noticing the same `useState` + `useEffect` pairing being duplicated for each data source.
- Chart colors are drawn from the same fixed palette used throughout the design (`--accent`, `--accent-2`, `--accent-3`, ...), so charts feel like one coherent design rather than a library's default color scheme dropped in unchanged.

### Running the Frontend

```bash
cd frontend
npm install
npm run dev
```
Runs at `http://localhost:5173`. Requires the backend to be running for data to load.

---


## Assumptions Made

- Sulekha was treated as an acceptable substitute for Google Maps/Justdial under the assignment's "any other business directory website" allowance, given the explicit instruction to avoid ToS-violating scraping.
- Where a listing card offered multiple services, the first-listed service was treated as the business's primary category.
- Missing street-level address detail was accepted as a source limitation rather than pursued via per-listing profile page requests, given the 500+ record volume target and timeline.
- Phone numbers were normalized to a strict 10-digit Indian mobile format; numbers not resolving cleanly to this format (e.g., unusual landline formats) were stored as `NULL` rather than kept in a non-uniform format.

---

## Current Status

- [x] Multi-city scraper built and verified (500+ records across 6 cities)
- [x] MySQL schema created and populated (`listing_master`, with an added `pincode` column beyond the original spec)
- [x] Bulk data load from scraped JSON into MySQL
- [x] FastAPI: bulk-insert, all-listings, and three aggregation endpoints
- [x] React dashboard: stat cards, bar charts, custom donut + legend, full data table, CSV export
- [x] Full MySQL dump generated (schema + data)
- [ ] Repo restructure to match submission spec (`app/` → `backend/`, confirm `database/` placement)
- [ ] Manual API edge-case testing (empty table, invalid payloads)
- [ ] Demo video (3–5 minutes)

---

*(Final section — Demo Video link — will be added once recorded.)*
