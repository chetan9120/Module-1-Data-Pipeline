"""
scrape.py — Module 1: Data Pipeline
Scrapes books.toscrape.com by category, parses each product_pod block, and
writes the raw scraped rows to raw_books.csv.

Usage:
    python3 scrape.py
    python3 scrape.py --base-url http://localhost:8000   # for local testing

Design choice: rather than the "5 pages of All products" scope, this script
scrapes 5 named categories (Travel, Mystery, Classics, Fantasy, Fiction),
each with pagination followed to the end. This satisfies "at least 3
categories" and lets us read category directly off each category page's
breadcrumb/heading, with no need to hit book detail pages.
"""
import argparse
import csv
import time

import requests
from bs4 import BeautifulSoup

CATEGORIES = {
    "travel_2": "Travel",
    "mystery_3": "Mystery",
    "classics_6": "Classics",
    "fantasy_19": "Fantasy",
    "fiction_10": "Fiction",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (data-pipeline-assignment scraper)"}


def scrape_category(base_url, slug, name, session, delay=0.5):
    """Follows pagination for one category, returns list of raw row dicts."""
    rows = []
    page = 1
    url = f"{base_url}/catalogue/category/books/{slug}/index.html"

    while url:
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"  # site serves UTF-8; be explicit to avoid mojibake
        soup = BeautifulSoup(resp.text, "html.parser")

        for pod in soup.select("article.product_pod"):
            title = pod.h3.a["title"]
            price_text = pod.select_one("p.price_color").get_text(strip=True)
            rating_classes = pod.select_one("p.star-rating")["class"]
            # class list is like ["star-rating", "Three"] — rating word is the non-"star-rating" token
            star_word = next((c for c in rating_classes if c != "star-rating"), None)
            availability_text = pod.select_one("p.instock.availability").get_text(strip=True)

            rows.append(
                {
                    "title": title,
                    "price": price_text,
                    "star_rating": star_word,
                    "availability": availability_text,
                    "category": name,
                }
            )

        next_link = soup.select_one("li.next a")
        if next_link:
            page += 1
            # pagination pages live alongside index.html in the same category dir
            base_dir = url.rsplit("/", 1)[0]
            url = f"{base_dir}/{next_link['href']}"
            time.sleep(delay)
        else:
            url = None

    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="https://books.toscrape.com",
        help="Site root (override for local testing against a fixture server)",
    )
    parser.add_argument("--out", default="raw_books.csv")
    args = parser.parse_args()

    session = requests.Session()
    all_rows = []

    for slug, name in CATEGORIES.items():
        print(f"Scraping category: {name} ({slug}) ...")
        rows = scrape_category(args.base_url, slug, name, session)
        print(f"  -> {len(rows)} books")
        all_rows.extend(rows)

    print(f"Total scraped: {len(all_rows)} books across {len(CATEGORIES)} categories")

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["title", "price", "star_rating", "availability", "category"]
        )
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Wrote raw data to {args.out}")


if __name__ == "__main__":
    main()
