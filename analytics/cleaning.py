"""
cleaning.py — Module 2: Analytics Pipeline

Single source of truth for loading and cleaning the Titanic dataset.
Both 01_eda.ipynb and 02_modeling.ipynb import from this module so the
raw dataset is fetched from network/cache exactly once (in 01_eda.ipynb,
which writes titanic.csv), and every later stage — including the modeling
notebook — reads the same committed titanic.csv rather than calling
seaborn's loader again. This guarantees Part A (EDA) and Part B (modeling)
operate on identically-cleaned data.

Missing-value threshold rule (cited wherever a strategy is applied):
  - missing % > 40%   -> DROP the column (too sparse to impute reliably)
  - 0% < missing % <= 5%  -> DROP the affected rows (small, safe to lose)
  - 5% < missing % <= 40% -> IMPUTE (median for numeric, mode for categorical)
"""
import os
import pandas as pd

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(THIS_DIR, "titanic.csv")

# Thresholds (see module docstring)
DROP_COLUMN_THRESHOLD = 40.0
DROP_ROWS_THRESHOLD = 5.0


def load_raw():
    """Load the raw (uncleaned) Titanic dataset from the committed offline
    fallback CSV. This is the ONLY place the module reads titanic.csv, and
    titanic.csv is the only place the raw seaborn dataset was ever fetched
    from network/cache (done once, in 01_eda.ipynb)."""
    return pd.read_csv(CSV_PATH)


def missing_value_report(df):
    """Return missing counts and percentages for every affected column,
    sorted descending by percentage."""
    counts = df.isnull().sum()
    pct = (counts / len(df)) * 100
    report = pd.DataFrame({"missing_count": counts, "missing_pct": pct})
    report = report[report["missing_count"] > 0].sort_values(
        "missing_pct", ascending=False
    )
    return report


def clean(df):
    """Apply the missing-value strategy per the threshold rule above.

    - deck: ~77% missing -> DROP COLUMN (> 40% threshold)
    - embarked / embark_town: ~0.22% missing -> DROP ROWS (<= 5% threshold)
    - age: ~19.87% missing -> IMPUTE with median (5%-40% band)
    """
    df = df.copy()

    report = missing_value_report(df)

    # Columns over the drop-column threshold
    drop_cols = report[report["missing_pct"] > DROP_COLUMN_THRESHOLD].index.tolist()
    df = df.drop(columns=drop_cols)

    # Recompute report after column drops, for row-level decisions
    report2 = missing_value_report(df)

    # Columns at/under the drop-rows threshold -> drop affected rows
    drop_row_cols = report2[
        report2["missing_pct"] <= DROP_ROWS_THRESHOLD
    ].index.tolist()
    if drop_row_cols:
        df = df.dropna(subset=drop_row_cols)

    # Remaining missing columns (5%-40% band) -> impute
    report3 = missing_value_report(df)
    for col in report3.index:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].fillna(df[col].median())
        else:
            df[col] = df[col].fillna(df[col].mode()[0])

    return df


def load_and_clean():
    """Convenience wrapper: load raw CSV, apply the cleaning strategy."""
    return clean(load_raw())
