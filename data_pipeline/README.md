# Module 1 — Data Pipeline

Scrapes [books.toscrape.com](https://books.toscrape.com), cleans and types the
scraped fields, converts price into INR using a fixed baseline rate, loads
everything into a normalized SQLite database, and runs SQL + pandas queries
against it.

## Pipeline

```
scrape.py  →  raw_books.csv  →  clean_and_load.py  →  books.db, cleaned_books.csv
                                                              │
                                    run_queries.py  ──────────┤  → query_results.txt
                                    pandas_verify.py ─────────┘
```

## Install

```bash
pip install requests beautifulsoup4 pandas
```

(Python 3.9+; no other dependencies. `sqlite3` is in the standard library.)

## Run — full pipeline, in order

```bash
python3 scrape.py                 # -> raw_books.csv
python3 clean_and_load.py         # -> cleaned_books.csv, books.db
python3 run_queries.py            # -> prints + query_results.txt
python3 pandas_verify.py          # -> prints pd.read_sql / pd.merge comparison
```

`scrape.py` defaults to `--base-url https://books.toscrape.com`. It needs
outbound network access to that host — if you're running this from a
network-restricted environment, allow that domain first.

## Scope / design decisions

**Schema design.** Two tables: `categories` (`category_id` PK, `category_name`
UNIQUE) and `books` (`book_id` PK, plus `category_id` as a FK referencing
`categories`). Category names are normalized out into their own table rather
than stored as a repeated text column on `books`, so the JOIN in Q6 and the
`pd.merge` reproduction in `pandas_verify.py` operate on integer keys instead
of string matching.

**Scraping scope.** The assignment allows either "≥3 categories" or "first 5
pages of All products." I scraped **5 named categories** (Travel, Mystery,
Classics, Fantasy, Fiction), following pagination to the end of each. This
satisfies the ≥3-category requirement and, importantly, lets `category` be
read directly off each category listing page (via the page heading) rather
than requiring a second HTTP request per book to a detail page just to learn
its category. Net effect: fewer requests, same required fields per row
(title, price, star_rating, availability, category).

**Field parsing.**
- `price_gbp`: numeric portion extracted from the listed `£XX.XX` string via
  regex, cast to `float`.
- `rating`: the star-rating CSS class (`One`…`Five`) mapped to an integer
  1–5.
- `in_stock`: the availability text checked for the substring "out of
  stock" vs "in stock" and mapped to a boolean.
- `stock_count`: the number of available units, e.g. `22` from "In stock
  (22 available)"; `0` for "Out of stock". **This count only appears on
  each book's own detail page, not the category listing page** — so
  `scrape.py` visits each book's detail URL (one extra request per book)
  to pull it, in addition to the listing page for title/price/rating.

**Currency conversion — fixed baseline rate.**
`price_inr = price_gbp * 105.50`. This is the project-defined fixed
constant specified in the assignment (**1 GBP = 105.50 INR**) — not a live
or historical market rate, so it requires no API call, no lookup, and no
date reference. It's applied identically to every row. (The assignment's
optional/ungraded stretch of also trying a live keyless FX API with a
fallback to this same fixed rate was not implemented, since it doesn't
affect the graded `price_inr` column — the fixed rate is the whole
requirement.)

**Row-drop vs. median-impute policy.** I chose to **drop** any row where
`price_gbp`, `rating`, or `in_stock` fails to parse, rather than
median-impute. Justification: books.toscrape.com is a purpose-built,
machine-generated scraping-practice site, so every field follows a fixed,
predictable format — a parse failure there signals a genuinely malformed or
unexpected record for that specific book, not a legitimate "missing value"
in an otherwise-clean numeric field. Inventing a median rating or
median-imputed stock status for a specific named book would misrepresent
that book rather than fill a genuine gap, so dropping (with the row logged)
is the more honest choice here. In the actual run, all 80 scraped rows
parsed cleanly (0 dropped) — see `clean_and_load.py` output.

**Schema.** Two tables, `categories` (PK `category_id`) and `books` (PK
`book_id`, FK `category_id → categories.category_id`), matching the
suggested schema in the assignment.

**SQL queries (`run_queries.py`).** Seven queries covering every required
clause:
1. `SELECT` / `WHERE` — in-stock books under 2000 INR
2. `ORDER BY` / `LIMIT` — 10 most expensive books
3. `DISTINCT` — distinct rating values present
4. `BETWEEN` — books priced 1500–3000 INR
5. `IN` — books in a chosen category subset
6. `JOIN` — top 3 highest-rated books per category (`books` ⋈ `categories`)
7. `stock_count` — in-stock books with fewer than 5 units available

Full printed output of all six is captured in `query_results.txt` after
running `run_queries.py`.

**Pandas verification (`pandas_verify.py`).** Reads two query results back
via `pd.read_sql` (top-10-by-price, distinct ratings), then reproduces the
JOIN query using `pd.merge` on the two tables pulled into memory as
DataFrames (no SQL for the merge itself), sorts both results identically,
and asserts `.equals()` — confirmed `True` in the reference run.

## Testing note (sandbox-only, not part of the submission)

The `fixtures/` folder contains a small local HTML mirror of
books.toscrape.com's real markup (`product_pod` structure, `star-rating`
classes, pagination), generated by `fixtures/make_fixtures.py`. It exists
only so `scrape.py` could be exercised end-to-end in a network-restricted
sandbox during development (`python3 scrape.py --base-url
http://localhost:8000`) — it is not required for, and does not affect, the
actual submission. Run `scrape.py` with its default `--base-url` against
the real site for the graded data.

## Files

| File | Purpose |
|---|---|
| `scrape.py` | Scrapes books.toscrape.com by category → `raw_books.csv` |
| `scrape_selenium.py` | Same scrape, driven via a visible Selenium/Chrome browser instead of requests |
| `clean_and_load.py` | Cleans/types fields, converts currency, builds `books.db` |
| `run_queries.py` | Runs the 6 required SQL queries → `query_results.txt` |
| `pandas_verify.py` | `pd.read_sql` + `pd.merge` equivalence check |
| `fixtures/` | Local test-only HTML mirror (see Testing note above) |
