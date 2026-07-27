"""
pandas_verify.py — Module 1: Data Pipeline

- Reads at least two of the SQL query results into pandas via pd.read_sql.
- Reproduces the JOIN query's result using pd.merge on in-memory DataFrames
  (no SQL), and shows both approaches produce equivalent output.
"""
import sqlite3

import pandas as pd

conn = sqlite3.connect("books.db")

# --- 1. Read two query results back via pd.read_sql --------------------

print("=" * 70)
print("pd.read_sql — Q2: top 10 most expensive books (INR)")
print("=" * 70)
df_top10 = pd.read_sql(
    "SELECT title, price_inr FROM books ORDER BY price_inr DESC LIMIT 10", conn
)
print(df_top10.to_string(index=False))

print("\n" + "=" * 70)
print("pd.read_sql — Q3: distinct ratings present")
print("=" * 70)
df_distinct_ratings = pd.read_sql(
    "SELECT DISTINCT rating FROM books ORDER BY rating", conn
)
print(df_distinct_ratings.to_string(index=False))

# --- 2. SQL JOIN result, via pd.read_sql --------------------------------

sql_join = """
    SELECT c.category_name, b.title, b.rating, b.price_inr
    FROM books b
    JOIN categories c ON b.category_id = c.category_id
    ORDER BY c.category_name, b.title;
"""
df_join_sql = pd.read_sql(sql_join, conn)

# --- 3. Same join, reproduced purely with pd.merge on in-memory frames -

books_df = pd.read_sql("SELECT * FROM books", conn)
categories_df = pd.read_sql("SELECT * FROM categories", conn)

df_join_merge = (
    books_df.merge(categories_df, on="category_id", how="inner")
    [["category_name", "title", "rating", "price_inr"]]
    .sort_values(["category_name", "title"])
    .reset_index(drop=True)
)

df_join_sql_sorted = df_join_sql.sort_values(["category_name", "title"]).reset_index(
    drop=True
)

print("\n" + "=" * 70)
print("JOIN via SQL (pd.read_sql) — first 10 rows")
print("=" * 70)
print(df_join_sql_sorted.head(10).to_string(index=False))

print("\n" + "=" * 70)
print("JOIN via pd.merge (no SQL) — first 10 rows")
print("=" * 70)
print(df_join_merge.head(10).to_string(index=False))

match = df_join_sql_sorted.equals(df_join_merge)
print("\n" + "=" * 70)
print(f"pd.read_sql JOIN and pd.merge JOIN produce identical output: {match}")
print("=" * 70)

if not match:
    diff = pd.concat([df_join_sql_sorted, df_join_merge]).drop_duplicates(keep=False)
    print("Differences found:")
    print(diff)

conn.close()
