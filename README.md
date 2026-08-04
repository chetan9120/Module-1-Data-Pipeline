# Project Repository

This repository holds all assignment modules. Each module lives in its own
top-level folder with its own code, data/database artifacts, and a
module-level `README.md` covering install/run steps and design decisions.

## Modules

| Module | Path | Description |
|---|---|---|
| 1 — Data Pipeline | [`/data_pipeline`](./data_pipeline/README.md) | Scrapes books.toscrape.com, cleans and converts currency, loads into a normalized SQLite database, and runs SQL + pandas queries. |
| 2 — Analytics Pipeline | [`/analytics`](./analytics/README.md) | EDA and predictive modeling on the Titanic dataset — cleaning, outlier/correlation analysis, three classifiers with full metrics, imbalance handling, a tuned Random Forest, a regression sub-task, and a saved end-to-end pipeline. |

Git workflow note: this repo's commits show a feature branch created,
committed to multiple times, and merged back into `main` — that check
applies once across the whole repository (not per module).
