"""
cleaning.py — Module 2: Analytics Pipeline

Single source of truth for loading and cleaning the Titanic dataset.
Both 01_eda.ipynb and 02_modeling.ipynb import from this module so the
raw dataset is fetched from network/cache exactly once (in 01_eda.ipynb,
which writes titanic.csv), and every later stage — including the modeling
notebook — reads the same committed titanic.csv rather than calling
seaborn's loader again. This guarantees Part A (EDA) and Part B (modeling)
operate on identically-cleaned data.

Missing-value threshold rule (as specified by the assignment):
  - missing % < 5%          -> DROP the affected rows
  - 5% <= missing % <= 30%  -> IMPUTE (median for numeric, mode for categorical)
  - missing % > 30%         -> too high to impute reliably; NOT covered by an
                               automatic rule. Each such column gets an
                               explicit, justified, per-column decision
                               (drop the column, or encode "Missing" as its
                               own category) recorded in HIGH_MISSING_DECISIONS
                               below, with the reasoning next to it.
"""
import os
import pandas as pd

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(THIS_DIR, "titanic.csv")

# Thresholds (see module docstring)
DROP_ROWS_THRESHOLD = 5.0      # < 5%          -> drop rows
IMPUTE_UPPER_THRESHOLD = 30.0  # 5% - 30%      -> impute
# > 30% is a judgment call, made explicitly per column below.

# Explicit, justified per-column decisions for columns whose missing rate
# exceeds IMPUTE_UPPER_THRESHOLD (i.e. imputation would be unreliable).
# Each entry is (action, justification). action is one of:
#   "drop_column"       -> remove the column entirely
#   "missing_category"  -> fill with the literal string "Missing" so the
#                          gap itself becomes a modeled category
HIGH_MISSING_DECISIONS = {
    "deck": (
        "drop_column",
        "~77% missing. At that rate there isn't enough real signal left to "
        "impute meaningfully, and encoding 'Missing' would effectively just "
        "recreate a near-constant flag (since nearly everyone would fall "
        "into that one bucket) rather than a genuinely informative category. "
        "Dropping the column is the more defensible choice here.",
    ),
}


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

    - deck (~77% missing): > 30% band -> explicit justified decision,
      see HIGH_MISSING_DECISIONS: drop the column.
    - embarked / embark_town (~0.22% missing): < 5% band -> drop the
      affected rows.
    - age (~19.87% missing): 5%-30% band -> impute with the median.
    """
    df = df.copy()
    report = missing_value_report(df)

    # > 30% band: explicit justified per-column decisions
    high_missing_cols = report[report["missing_pct"] > IMPUTE_UPPER_THRESHOLD].index.tolist()
    for col in high_missing_cols:
        if col not in HIGH_MISSING_DECISIONS:
            raise ValueError(
                f"Column '{col}' is missing {report.loc[col, 'missing_pct']:.1f}% "
                "of its values (> 30%), which needs an explicit justified "
                "decision in HIGH_MISSING_DECISIONS before it can be cleaned."
            )
        action, _justification = HIGH_MISSING_DECISIONS[col]
        if action == "drop_column":
            df = df.drop(columns=[col])
        elif action == "missing_category":
            df[col] = df[col].fillna("Missing")
        else:
            raise ValueError(f"Unknown action '{action}' for column '{col}'")

    # < 5% band: drop the affected rows
    report2 = missing_value_report(df)
    drop_row_cols = report2[report2["missing_pct"] < DROP_ROWS_THRESHOLD].index.tolist()
    if drop_row_cols:
        df = df.dropna(subset=drop_row_cols)

    # 5%-30% band: impute (median for numeric, mode for categorical)
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
