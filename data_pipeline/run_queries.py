"""
run_queries.py — Module 1: Data Pipeline

Executes the required SQL queries against books.db and prints their output.
Also writes the same output to query_results.txt for the submission record.

Coverage:
  Q1 SELECT / WHERE
  Q2 ORDER BY / LIMIT
  Q3 DISTINCT
  Q4 WHERE ... BETWEEN
  Q5 WHERE ... IN
  Q6 JOIN (books x categories) — top 10 highest-rated books per category (illustrated for one category + overall top rated join)

Each query is logged with its header and full result set to query_results.txt
so the SQL output is reviewable without re-running the script.
"""
import sqlite3

QUERIES = [
    (
        "Q1: SELECT/WHERE — in-stock books priced under 2000 INR",
        """
        SELECT title, price_inr, rating
        FROM books
        WHERE in_stock = 1 AND price_inr < 2000
        ORDER BY price_inr ASC;
        """,
    ),
    (
        "Q2: ORDER BY/LIMIT — 10 most expensive books (INR)",
        """
        SELECT title, price_inr
        FROM books
        ORDER BY price_inr DESC
        LIMIT 10;
        """,
    ),
    (
        "Q3: DISTINCT — distinct rating values present in the dataset",
        """
        SELECT DISTINCT rating
        FROM books
        ORDER BY rating;
        """,
    ),
    (
        "Q4: BETWEEN — books priced between 1500 and 3000 INR",
        """
        SELECT title, price_inr
        FROM books
        WHERE price_inr BETWEEN 1500 AND 3000
        ORDER BY price_inr;
        """,
    ),
    (
        "Q5: IN — books in a chosen subset of categories",
        """
        SELECT title, category_id
        FROM books
        WHERE category_id IN (
            SELECT category_id FROM categories WHERE category_name IN ('Travel', 'Fantasy')
        )
        ORDER BY category_id;
        """,
    ),
    (
        "Q6: JOIN — top 3 highest-rated books per category (books x categories)",
        """
        SELECT c.category_name, b.title, b.rating, b.price_inr
        FROM books b
        JOIN categories c ON b.category_id = c.category_id
        WHERE b.rating >= (
            SELECT MIN(rating) FROM (
                SELECT rating FROM books b2
                WHERE b2.category_id = b.category_id
                ORDER BY rating DESC LIMIT 3
            )
        )
        ORDER BY c.category_name, b.rating DESC;
        """,
    ),
    (
        "Q7: stock_count — low-stock in-stock books (fewer than 5 available)",
        """
        SELECT title, stock_count, price_inr
        FROM books
        WHERE in_stock = 1 AND stock_count < 5
        ORDER BY stock_count ASC;
        """,
    ),
]


def main():
    conn = sqlite3.connect("books.db")
    cur = conn.cursor()

    log_lines = []
    for title, sql in QUERIES:
        header = f"\n{'='*70}\n{title}\n{'='*70}"
        print(header)
        log_lines.append(header)

        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()

        col_line = " | ".join(cols)
        print(col_line)
        log_lines.append(col_line)

        for row in rows:
            line = " | ".join(str(v) for v in row)
            print(line)
            log_lines.append(line)

        summary = f"({len(rows)} rows)"
        print(summary)
        log_lines.append(summary)

    conn.close()

    with open("query_results.txt", "w") as f:
        f.write("\n".join(log_lines) + "\n")
    print("\nWrote full query output to query_results.txt")


if __name__ == "__main__":
    main()
