# Module 2 — Analytics Pipeline

EDA and predictive modeling on the Titanic dataset. Two notebooks, run in order:

1. `01_eda.ipynb` — profiling, missing-value handling, outlier/skew analysis,
   bivariate and multivariate exploration, correlation analysis, standardization check.
2. `02_modeling.ipynb` — stratified split, preprocessing pipeline, three
   classifiers + full metrics, imbalance handling, `GridSearchCV`-tuned Random
   Forest with OOB score, a regression sub-task, final comparison table, and
   the saved end-to-end pipeline.

Both notebooks import from `cleaning.py`, the single source of truth for
loading and cleaning the data.

## Install / run

```bash
pip install pandas numpy seaborn matplotlib scikit-learn imbalanced-learn joblib nbclient nbformat --break-system-packages
cd analytics
jupyter nbconvert --to notebook --execute --inplace 01_eda.ipynb
jupyter nbconvert --to notebook --execute --inplace 02_modeling.ipynb
```

`01_eda.ipynb` must run first — it's the only cell in the whole module that
calls `seaborn.load_dataset("titanic")` (a network/cache fetch), and it
immediately writes the result to `titanic.csv`. Every other cell, in both
notebooks, reads `titanic.csv` through `cleaning.py` — the raw dataset is
never fetched a second time, and the modeling notebook never reloads
independently of the EDA notebook.

## Files

- `cleaning.py` — shared `load_raw()` / `missing_value_report()` / `clean()` / `load_and_clean()` functions, plus the missing-value threshold rule (see below).
- `titanic.csv` — the one committed offline fallback for the raw dataset (`df.to_csv("titanic.csv", index=False)`), loadable via `pd.read_csv("titanic.csv")`.
- `01_eda.ipynb`, `02_modeling.ipynb` — executed notebooks with real outputs.
- `charts/` — saved PNGs of every chart produced (distributions, correlation heatmaps, bivariate/multivariate plots, decision tree, ROC curves, residual plot).
- `model_comparison.csv` — the final comparison table (also below).
- `titanic_rf_pipeline.joblib` — the complete fitted pipeline (preprocessing + tuned Random Forest), saved via `joblib.dump`.

## Design decisions

### Missing-value strategy and threshold rule

Applied uniformly via `cleaning.py`, and to every affected column:

| Missing % | Strategy |
|---|---|
| `> 40%` | Drop the column |
| `> 0% and <= 5%` | Drop the affected rows |
| `> 5% and <= 40%` | Impute (median for numeric, mode for categorical) |

- `deck` — **77.2%** missing → dropped the column (over the 40% threshold).
- `age` — **19.9%** missing → imputed with the median (inside the 5–40% band).
- `embarked` / `embark_town` — **0.2%** missing → dropped the affected rows (at/under the 5% threshold).

### Outliers and skew

- `age`: 66 IQR outliers, roughly symmetric distribution.
- `fare`: 116 IQR outliers, strongly right-skewed — confirmed by **mean (32.20) > median (14.45) > mode (8.05)**.

### Correlation — two strongest pairs

1. `pclass` ↔ `fare`: r ≈ **-0.55** (lower `pclass` number = costlier ticket).
2. `sibsp` ↔ `parch`: r ≈ **0.41** (family-size components move together).

### Multivariate charts (4, each interpreted in the notebook)

1. Survival rate by `pclass` × `sex` (bar) — sex and class interact; the best/worst subgroup gap is wider than either feature alone predicts.
2. `fare` vs `age` colored by `survived` (scatter) — fare separates survival more visibly than age.
3. `age` distribution by `pclass`, split by `survived` (box) — age barely separates survival within a class; the visible effect is first class skewing older overall.
4. Correlation heatmap, 6 variables (heatmap) — confirms the two strongest pairs above.

### Standardization check

Before/after `StandardScaler` comparison shown for both `age` and `fare` in
`01_eda.ipynb` (exploratory only — the pipeline used for modeling fits its
own scaler on the training split in `02_modeling.ipynb`).

### Train/test split and preprocessing

Stratified 80/20 split on `survived` (imbalanced ~38%/62%), done **before**
any preprocessing. Each pipeline builds its own fresh `ColumnTransformer`
(via a `make_preprocessor()` factory) rather than sharing one mutable object
across models. All imputers/encoders/scalers are fit on the training split
only and applied transform-only to the test split — verified explicitly in
`02_modeling.ipynb` section 3.

### Imbalance handling

Baseline vs `class_weight='balanced'` vs SMOTE (SMOTE fit/applied on the
training fold only). Both rebalancing approaches trade precision for recall
versus the baseline; `class_weight='balanced'` is the simpler choice for a
similar gain to SMOTE here.

### Heteroscedasticity (regression)

Residual variance rises roughly 40–50x from the lowest to highest
predicted-fare tercile — a clear funnel/cone pattern, i.e. **heteroscedasticity**,
not homoscedasticity. A log-transform of `fare` would be the natural next step.

## Final model comparison

| Model | Task | Accuracy | Precision | Recall | F1 | ROC-AUC | MAE | RMSE | R² | Adj R² |
|---|---|---|---|---|---|---|---|---|---|---|
| Logistic Regression | Classification | 0.809 | 0.783 | 0.691 | 0.734 | 0.861 | – | – | – | – |
| Decision Tree | Classification | 0.809 | 0.815 | 0.647 | 0.721 | 0.856 | – | – | – | – |
| Random Forest (tuned, GridSearchCV) | Classification | 0.803 | 0.762 | 0.706 | 0.733 | 0.824 | – | – | – | – |
| Linear Regression (fare) | Regression | – | – | – | – | – | 21.14 | 41.75 | 0.347 | 0.324 |

*(Exact values regenerate in `model_comparison.csv` when the notebooks are re-run; classifier and regression metrics are kept in separate columns rather than merged onto one scale.)*

## Recommendation

For survival classification, the **tuned Random Forest** is recommended —
best F1 and closely-tracking OOB/test scores indicate the `GridSearchCV`
tuning generalizes rather than overfitting to the CV folds. The depth-4
**Decision Tree** is a reasonable, more interpretable fallback since it can
be visualized directly. For the regression sub-task, the Linear Regression
model only explains ~35% of fare variance and shows clear heteroscedasticity
— it should not be treated as production-ready without a log-transform of
`fare` and/or a non-linear regressor.

## Saved pipeline

`titanic_rf_pipeline.joblib` is the complete fitted pipeline (preprocessing
+ tuned Random Forest) saved via `joblib.dump(full_pipeline, ...)`. Reload
and use directly on raw, unprocessed passenger data:

```python
import joblib
import pandas as pd

pipeline = joblib.load("titanic_rf_pipeline.joblib")
sample = pd.DataFrame([{
    "pclass": 1, "sex": "female", "age": 25, "sibsp": 0,
    "parch": 0, "fare": 80, "embarked": "C",
}])
pipeline.predict(sample)
```
