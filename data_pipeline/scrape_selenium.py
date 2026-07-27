"""
scrape_selenium.py — Module 1: Data Pipeline (Selenium variant)

Same output as scrape.py (raw_books.csv with title, price, star_rating,
availability, category) but drives a real, VISIBLE Chrome window instead of
using requests/BeautifulSoup. Useful if you want to watch the scrape happen,
or if the assignment/course wants Selenium specifically demonstrated.

Like scrape.py, this visits each book's own detail page (in addition to the
category listing page) to capture the stock-count text, e.g.
"In stock (22 available)" — that count is not shown on the listing page.

Requirements:
    pip install selenium
    A Chrome/Chromium install on your machine (Selenium Manager, bundled
    with selenium>=4.6, downloads a matching chromedriver automatically —
    no manual driver setup needed).

Usage:
    python3 scrape_selenium.py
    python3 scrape_selenium.py --base-url http://localhost:8000   # local test
    python3 scrape_selenium.py --headless                         # optional, off by default
"""
import argparse
import csv
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CATEGORIES = {
    "travel_2": "Travel",
    "mystery_3": "Mystery",
    "classics_6": "Classics",
    "fantasy_19": "Fantasy",
    "fiction_10": "Fiction",
}


def make_driver(headless: bool):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,1000")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(options=options)


def fetch_stock_count(driver, detail_url, delay=0.3):
    """Visits a book's detail page in the same browser and returns its raw
    availability string, e.g. 'In stock (22 available)' or 'Out of stock'."""
    driver.get(detail_url)
    el = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "p.instock.availability"))
    )
    text = el.text.strip()
    time.sleep(delay)
    return text


def scrape_category(driver, base_url, slug, name, delay=0.6):
    """Follows pagination via the 'next' button for one category."""
    rows = []
    url = f"{base_url}/catalogue/category/books/{slug}/index.html"

    while url:
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article.product_pod"))
        )

        # Collect per-book detail-page URLs up front, since navigating away
        # (to fetch stock counts) invalidates the pod elements on this page.
        pods = driver.find_elements(By.CSS_SELECTOR, "article.product_pod")
        pod_data = []
        for pod in pods:
            title = pod.find_element(By.CSS_SELECTOR, "h3 a").get_attribute("title")
            price_text = pod.find_element(By.CSS_SELECTOR, "p.price_color").text
            rating_classes = pod.find_element(
                By.CSS_SELECTOR, "p.star-rating"
            ).get_attribute("class")
            star_word = next(
                (c for c in rating_classes.split() if c != "star-rating"), None
            )
            detail_url = pod.find_element(By.CSS_SELECTOR, "h3 a").get_attribute("href")
            pod_data.append((title, price_text, star_word, detail_url))

        next_links = driver.find_elements(By.CSS_SELECTOR, "li.next a")
        next_url = next_links[0].get_attribute("href") if next_links else None

        for title, price_text, star_word, detail_url in pod_data:
            availability_text = fetch_stock_count(driver, detail_url)
            rows.append(
                {
                    "title": title,
                    "price": price_text,
                    "star_rating": star_word,
                    "availability": availability_text,
                    "category": name,
                }
            )

        if next_url:
            url = next_url
            time.sleep(delay)
        else:
            url = None

    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://books.toscrape.com")
    parser.add_argument("--out", default="raw_books.csv")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run with no visible window (off by default — window is shown)",
    )
    args = parser.parse_args()

    driver = make_driver(headless=args.headless)
    all_rows = []

    try:
        for slug, name in CATEGORIES.items():
            print(f"Scraping category: {name} ({slug}) ...")
            rows = scrape_category(driver, args.base_url, slug, name)
            print(f"  -> {len(rows)} books")
            all_rows.extend(rows)
    finally:
        driver.quit()

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
