"""
clean_and_load.py — Module 1: Data Pipeline

Reads raw_books.csv (output of scrape.py), cleans/types every field,
converts price to INR using the fixed project baseline rate, and loads
everything into a normalized two-table SQLite database (books.db).

Fixed conversion rate (project-defined constant, not a live/historical
market rate — no lookup or date reference needed):
    1 GBP = 105.50 INR

Row-handling policy for unparseable fields: DROP the row, and log why.
Justification: books.toscrape.com's markup is a clean, purpose-built
scraping-practice site — every field is machine-generated and follows a
fixed format (star-rating class is always one of One..Five, price is
always "£<number>", availability text always contains "In stock" or "Out
of stock"). A row that fails to parse here indicates a genuinely
malformed/unexpected record, not a "hole" in an otherwise clean field
where imputing a median tells us anything meaningful about that book — so
dropping (with a clear log line) is more honest than inventing a rating
or availability status for a specific named book. Median imputation is
reserved for numeric fields with missing-but-plausible values, which
doesn't apply to any field in this dataset.
"""
import re
import sqlite3

import pandas as pd

GBP_TO_INR = 105.50  # fixed project-defined baseline rate — see README

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def clean(df: pd.DataFrame) -> pd.DataFrame:
    dropped = []

    def parse_price(v):
        m = re.search(r"[\d.]+", str(v))
        return float(m.group()) if m else None

    def parse_rating(v):
        return RATING_WORDS.get(str(v).strip())

    def parse_stock(v):
        text = str(v).lower()
        if "out of stock" in text:
            return False
        if "in stock" in text:
            return True
        return None

    df = df.copy()
    df["price_gbp"] = df["price"].apply(parse_price)
    df["rating"] = df["star_rating"].apply(parse_rating)
    df["in_stock"] = df["availability"].apply(parse_stock)

    before = len(df)
    bad_mask = df["price_gbp"].isna() | df["rating"].isna() | df["in_stock"].isna()
    if bad_mask.any():
        dropped = df.loc[bad_mask, "title"].tolist()
        print(f"Dropping {bad_mask.sum()} unparseable row(s): {dropped}")
    df = df.loc[~bad_mask].copy()
    after = len(df)
    print(f"Cleaned {before} -> {after} rows ({before - after} dropped)")

    df["price_inr"] = (df["price_gbp"] * GBP_TO_INR).round(2)
    df["rating"] = df["rating"].astype(int)
    df["in_stock"] = df["in_stock"].astype(bool)

    return df[["title", "price_gbp", "price_inr", "rating", "in_stock", "category"]]


def load_to_sqlite(df: pd.DataFrame, db_path: str = "books.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript(
        """
        DROP TABLE IF EXISTS books;
        DROP TABLE IF EXISTS categories;

        CREATE TABLE categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE books (
            book_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price_gbp REAL NOT NULL,
            price_inr REAL NOT NULL,
            rating INTEGER NOT NULL,
            in_stock INTEGER NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(category_id)
        );
        """
    )

    categories = sorted(df["category"].unique())
    cur.executemany(
        "INSERT INTO categories (category_name) VALUES (?)",
        [(c,) for c in categories],
    )
    conn.commit()

    cat_id_map = dict(
        cur.execute("SELECT category_name, category_id FROM categories").fetchall()
    )

    rows = [
        (
            r.title,
            r.price_gbp,
            r.price_inr,
            r.rating,
            int(r.in_stock),
            cat_id_map[r.category],
        )
        for r in df.itertuples()
    ]
    cur.executemany(
        """INSERT INTO books (title, price_gbp, price_inr, rating, in_stock, category_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()

    n_books = cur.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    n_cats = cur.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    print(f"Loaded {n_books} books across {n_cats} categories into {db_path}")

    conn.close()


def main():
    raw = pd.read_csv("raw_books.csv")
    cleaned = clean(raw)
    cleaned.to_csv("cleaned_books.csv", index=False)
    print(f"Wrote cleaned_books.csv ({len(cleaned)} rows)")
    load_to_sqlite(cleaned, "books.db")


if __name__ == "__main__":
    main()
