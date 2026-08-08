## Setup

Only `/support_assistant` has a dedicated `requirements.txt` file — the
other two modules list their (smaller) dependency lists directly in their
own README as a `pip install` command. Install per-module as needed:

```bash
# Module 1 — Data Pipeline
pip install requests beautifulsoup4 pandas

# Module 2 — Analytics Pipeline
pip install pandas numpy seaborn matplotlib scikit-learn imbalanced-learn joblib nbclient nbformat

# Module 3 — Support Assistant
cd support_assistant && pip install -r requirements.txt
```

## Modules

| Module | Path | Description |
|---|---|---|
| 1 — Data Pipeline | [`/data_pipeline`](/data_pipeline) | Scrapes books.toscrape.com, cleans and converts currency, loads into a normalized SQLite database, and runs SQL + pandas queries. |
| 2 — Analytics Pipeline | [`/analytics`](/analytics) | EDA and predictive modeling on the Titanic dataset — cleaning, outlier/correlation analysis, three classifiers with full metrics, imbalance handling, a tuned Random Forest, a regression sub-task, and a saved end-to-end pipeline. |
| 3 — Support Assistant | [`/support_assistant`](/support_assistant) | RAG-based Zepto customer-support assistant — LangGraph intent routing, ChromaDB + sentence-transformers retrieval, Pydantic-validated structured output, FastAPI + Docker. Fully offline mock-gradable (`MOCK_LLM=1` default), with an optional real-LLM (Groq free tier) extension. |

### How to run each module

**Module 1 — Data Pipeline**
```bash
cd data_pipeline
python3 scrape.py                 # -> raw_books.csv
python3 clean_and_load.py         # -> cleaned_books.csv, books.db
python3 run_queries.py            # -> prints + query_results.txt
python3 pandas_verify.py          # -> prints pd.read_sql / pd.merge comparison
```
See [`data_pipeline/README.md`](/data_pipeline/README.md) for the schema and design notes.

**Module 2 — Analytics Pipeline**
```bash
cd analytics
jupyter nbconvert --to notebook --execute --inplace 01_eda.ipynb
jupyter nbconvert --to notebook --execute --inplace 02_modeling.ipynb
```
`01_eda.ipynb` must run first — it's the only cell that fetches the raw
Titanic dataset and writes it to `titanic.csv`; every other cell reads that
file. See [`analytics/README.md`](/analytics/README.md) for the full
threshold rule, model comparison, and interpretation write-up.

**Module 3 — Support Assistant**
```bash
cd support_assistant
pip install -r requirements.txt
uvicorn main:app          # MOCK_LLM defaults to 1 (mock/graded baseline)
```
Then `POST /ask` with `{"query": "..."}`. See [`support_assistant/README.md`](/support_assistant/README.md)
for the full RAG architecture (ingestion → embedding → retrieval → generation),
example call transcripts, and the Docker build/run steps.

### Design decisions summary

- **Data Pipeline**: normalized `categories` out of `books` into its own
  table (FK relationship) so the JOIN query and the `pandas_verify.py`
  `pd.merge` reproduction operate on integer keys; used a fixed baseline
  GBP→INR rate (105.50) per the assignment spec; chose to drop unparseable
  rows rather than impute, since the source site's fields follow a fixed,
  predictable format. See module README for full rationale.
- **Analytics Pipeline**: used an explicit boolean-masking approach (`&`/`|`)
  for bivariate analysis per the assignment spec, applied a documented
  missing-value rule (<5% drop rows, 5–30% impute, >30% explicit
  per-column justification — e.g. `deck` at 77% missing was dropped
  entirely), and compared three classifiers before tuning a Random Forest
  (best F1) as the final recommended model.
- **Support Assistant**: kept the graded path fully offline and
  deterministic (keyword-based intent routing, canned templated answers,
  local embeddings via `sentence-transformers`) so the module needs no API
  key or network call to any LLM provider to earn full marks; the real-LLM
  path (Groq free tier) and Hugging Face Spaces deployment are both
  optional, ungraded extensions layered on top, gated behind a single
  `MOCK_LLM` environment variable.

## Git workflow

This repo's commit history includes feature branches (`feature/analytics-pipeline`,
`feature/assignment-alignment-fixes`) created, committed to multiple times,
and merged back into `main` — visible via `git log --graph --all`. This
applies once across the whole repository per the assignment's submission
guidelines.
