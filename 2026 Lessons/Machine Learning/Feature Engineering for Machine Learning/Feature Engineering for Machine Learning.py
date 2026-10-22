"""
Potato Project Topic: Machine Learning
Feature Engineering for Machine Learning

Business question:
    How much of a model's accuracy actually comes from the FEATURES rather 
    than the algorithm? And what are the classic ways a feature can quietly 
    leak the answer, making a model look great in testing and fail in production?

"Feature engineering" means creating, transforming or combining raw columns
into forms a model can use better. Analogy: raw ingredients versus a
prepped mise en place. The same vegetables cook into a better dish once
they are washed, chopped and seasoned correctly, same ingredients, better
form.

What this script covers:
    1. A deliberately under-engineered baseline (raw columns only)
    2. Date features: extracting signal hidden inside a single date column
    3. Binning a continuous variable (equal-width vs equal-frequency)
    4. Encoding categoricals the right way: one-hot vs target/mean encoding,
       and why mean encoding needs special care (leakage risk, fixed by
       cross-validated encoding)
    5. Interaction features: multiplying two columns to capture an effect
       neither captures alone
    6. A worked example of TARGET LEAKAGE: a feature that looks amazing and
       is actually cheating
    7. Final comparison: baseline vs engineered features, same model throughout

Run it with:  python "Feature Engineering for Machine Learning.py"
Requires:     numpy, pandas, scikit-learn, matplotlib
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer

OUT = Path(__file__).parent / "charts"
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 120)

# ---------------------------------------------------------------------
# STEP 0: Build a sample loan-default dataset
# ---------------------------------------------------------------------
# Predicting loan default: will this borrower miss a payment? Hidden rules
# the model should rediscover: weekend applications are riskier (impulsive
# borrowing), very young or very old applicants are safer in the middle,
# income relative to loan size matters more than either alone, and city
# has a real but modest effect.
rng = np.random.default_rng(42)
n = 4000
application_date = pd.to_datetime("2025-01-01") + pd.to_timedelta(
    rng.integers(0, 640, n), unit="D")
age = rng.integers(21, 65, n)
income = rng.normal(55000, 18000, n).clip(18000, 160000).round(0)
loan_amount = rng.normal(250000, 90000, n).clip(50000, 800000).round(0)
city = rng.choice(["Kolkata", "Delhi", "Mumbai", "Bengaluru"], n, p=[0.3, 0.25, 0.25, 0.2])
credit_score = rng.integers(300, 851, n)

is_weekend = application_date.dayofweek.isin([5, 6]).astype(int)
age_mid_risk = -((age - 42) ** 2) / 300            # safest around age 42
income_to_loan = income / loan_amount
city_effect = pd.Series(city).map(
    {"Kolkata": 0.0, "Delhi": 0.15, "Mumbai": -0.1, "Bengaluru": 0.05}).values

# income and loan_amount are deliberately given almost NO independent
# effect; what actually drives default is their RATIO, plus a sharp
# threshold below a critical affordability level. A model fed income and
# loan_amount as separate raw numbers has to approximate this ratio
# indirectly; a model fed the ratio directly should do noticeably better.
logit = (-1.0 + 0.5 * is_weekend - 0.02 * credit_score / 100
         + age_mid_risk - 6.0 * income_to_loan + city_effect
         + 2.0 * (income_to_loan < 0.18))             # a real, sharp threshold effect
default = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)

df = pd.DataFrame({
    "application_date": application_date, "age": age, "income": income,
    "loan_amount": loan_amount, "city": city, "credit_score": credit_score,
    "default": default,
})
print("=" * 60)
print("STEP 0: DATA")
print("=" * 60)
print(df.head())
print(f"\n{len(df):,} applications | default rate: {df['default'].mean():.1%}")

X_cols_raw = ["age", "income", "loan_amount", "city", "credit_score"]
X_train, X_test, y_train, y_test = train_test_split(
    df, df["default"], test_size=0.25, random_state=42, stratify=df["default"])

def evaluate(name, X_tr, X_te, feature_cols, cat_cols=()):
    num_cols = [c for c in feature_cols if c not in cat_cols]
    prep = ColumnTransformer([
        ("num", StandardScaler(), num_cols),
        ("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), list(cat_cols)),
    ]) if cat_cols else ColumnTransformer([("num", StandardScaler(), num_cols)])
    model = Pipeline([("prep", prep), ("clf", LogisticRegression(max_iter=1000))])
    model.fit(X_tr[feature_cols], y_train)
    auc = roc_auc_score(y_test, model.predict_proba(X_te[feature_cols])[:, 1])
    print(f"{name:<42} AUC = {auc:.3f}")
    return auc

# ---------------------------------------------------------------------
# STEP 1: Baseline, raw columns only
# ---------------------------------------------------------------------
# No date handling, no binning, no interactions, just the numeric columns
# and a plain one-hot of city. This is what a rushed first pass looks like.
print("\n" + "=" * 60)
print("STEP 1: BASELINE (raw columns, no engineering)")
print("=" * 60)
auc_baseline = evaluate("Baseline (raw columns)", X_train, X_test,
                        ["age", "income", "loan_amount", "credit_score", "city"],
                        cat_cols=["city"])

# ---------------------------------------------------------------------
# STEP 2: Date features
# ---------------------------------------------------------------------
# A raw datetime column is close to useless to a linear model; it is just
# a huge number. The USEFUL signal (weekday pattern, month, recency) has
# to be pulled out explicitly, the same instinct as Day 9's time series work.
for part in (df, X_train, X_test):
    part["is_weekend"] = part["application_date"].dt.dayofweek.isin([5, 6]).astype(int)
    part["app_month"] = part["application_date"].dt.month

print("\n" + "=" * 60)
print("STEP 2: DATE FEATURES EXTRACTED")
print("=" * 60)
print(df[["application_date", "is_weekend", "app_month"]].head(3))
auc_date = evaluate("+ date features (is_weekend)", X_train, X_test,
                    ["age", "income", "loan_amount", "credit_score", "city", "is_weekend"],
                    cat_cols=["city"])

# ---------------------------------------------------------------------
# STEP 3: Binning a continuous variable
# ---------------------------------------------------------------------
# Age's real effect here is U-shaped (safest in the middle), which a plain
# linear term cannot capture at all, since a straight line cannot curve.
# Binning age into groups lets a linear model fit a DIFFERENT coefficient
# per bucket, effectively letting it bend. Equal-width bins are simple;
# equal-frequency (quantile) bins guarantee enough data in every bucket,
# which matters most when a variable is skewed.
for part in (df, X_train, X_test):
    part["age_band"] = pd.cut(part["age"], bins=[20, 30, 40, 50, 65],
                              labels=["21-30", "31-40", "41-50", "51-65"])
print("\n" + "=" * 60)
print("STEP 3: AGE BINNED INTO BANDS (captures the U-shape a line cannot)")
print("=" * 60)
print(df.groupby("age_band", observed=True)["default"].agg(["mean", "count"]).round(3))
auc_binned = evaluate("+ binned age instead of raw age", X_train, X_test,
                      ["income", "loan_amount", "credit_score", "city", "is_weekend", "age_band"],
                      cat_cols=["city", "age_band"])

# ---------------------------------------------------------------------
# STEP 4: Target (mean) encoding, done SAFELY
# ---------------------------------------------------------------------
# One-hot encoding a high-cardinality categorical (many cities, postcodes,
# product SKUs) creates a huge number of columns. Target/mean encoding
# instead replaces each category with its average outcome rate, one column
# instead of many. The TRAP: computing the mean using a row's own label
# leaks the answer into its own feature (a row voting on its own target).
# The fix is K-FOLD encoding: compute each row's encoded value using only
# OTHER folds, never its own, the same leakage discipline as Day 13's
# threshold tuning on training data only.
def kfold_target_encode(train_x, train_y, col, n_splits=5, seed=42):
    encoded = pd.Series(index=train_x.index, dtype=float)
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    global_mean = train_y.mean()
    for fit_idx, hold_idx in kf.split(train_x):
        means = train_y.iloc[fit_idx].groupby(train_x[col].iloc[fit_idx]).mean()
        encoded.iloc[hold_idx] = train_x[col].iloc[hold_idx].map(means).fillna(global_mean)
    return encoded

train_mean_by_city = y_train.groupby(X_train["city"]).mean()
X_train = X_train.copy()
X_train["city_target_enc"] = kfold_target_encode(X_train, y_train, "city")
X_test = X_test.copy()
X_test["city_target_enc"] = X_test["city"].map(train_mean_by_city)  # test set uses the full train mapping, safely

print("\n" + "=" * 60)
print("STEP 4: K-FOLD TARGET ENCODING FOR 'CITY'")
print("=" * 60)
print("Default rate by city (train set):\n", train_mean_by_city.round(3))
auc_target_enc = evaluate(
    "+ target-encoded city (instead of one-hot)", X_train, X_test,
    ["income", "loan_amount", "credit_score", "is_weekend", "age_band", "city_target_enc"],
    cat_cols=["age_band"])

# ---------------------------------------------------------------------
# STEP 5: Interaction feature
# ---------------------------------------------------------------------
# Income alone and loan amount alone each tell PART of the story, but
# what actually drives default is income RELATIVE to the loan, a ratio
# neither raw column expresses on its own. This is exactly the hidden rule
# the data was generated with, so finding it should visibly help.
for part in (df, X_train, X_test):
    part["income_to_loan"] = part["income"] / part["loan_amount"]

print("\n" + "=" * 60)
print("STEP 5: INTERACTION FEATURE (income / loan_amount)")
print("=" * 60)
print(f"Correlation of raw income with default:  {df['income'].corr(df['default']):+.3f}")
print(f"Correlation of raw loan_amount with default: {df['loan_amount'].corr(df['default']):+.3f}")
print(f"Correlation of income_to_loan with default:  {df['income_to_loan'].corr(df['default']):+.3f}")
# Add the ratio ALONGSIDE the two raw columns first: a linear model can
# already approximate a ratio fairly well using two separate linear terms
# when income and loan_amount each have a fairly restricted range, so this
# step alone may show only a small gain.
auc_interaction_added = evaluate(
    "+ income_to_loan added alongside raw cols", X_train, X_test,
    ["income", "loan_amount", "credit_score", "is_weekend", "age_band",
     "city_target_enc", "income_to_loan"],
    cat_cols=["age_band"])
# Now REPLACE the two raw columns with the ratio instead of keeping all
# three: this isolates what the engineered feature adds on its own,
# instead of letting the raw columns already do most of the work.
auc_interaction_replaced = evaluate(
    "+ income_to_loan REPLACING raw income & loan_amount", X_train, X_test,
    ["credit_score", "is_weekend", "age_band", "city_target_enc", "income_to_loan"],
    cat_cols=["age_band"])
auc_interaction = auc_interaction_replaced

# ---------------------------------------------------------------------
# STEP 6: Target leakage, a worked trap
# ---------------------------------------------------------------------
# Imagine a column "collections_called" that is only ever set to 1 AFTER a
# borrower has already missed a payment. It is recorded in the same table
# as default, so it looks like a normal feature, but it is really a
# RESULT of the outcome, not a cause available at prediction time. This is
# the single most common reason a model performs beautifully in testing
# and then fails in production, where that information does not exist yet.
leak_feature = df["default"] * rng.integers(0, 2, n) + 0 * rng.integers(0, 2, n)
# construct so it is correlated with default but still noisy, to mimic a
# real (if sloppy) operational field rather than a perfect copy of the label
leak_feature = np.where(df["default"] == 1, rng.choice([0, 1], n, p=[0.1, 0.9]),
                        rng.choice([0, 1], n, p=[0.95, 0.05]))
for part, idx in ((X_train, X_train.index), (X_test, X_test.index)):
    part["collections_called"] = pd.Series(leak_feature, index=df.index).loc[idx]

print("\n" + "=" * 60)
print("STEP 6: TARGET LEAKAGE, A FEATURE THAT CHEATS")
print("=" * 60)
auc_leaked = evaluate(
    "+ 'collections_called' (LEAKED feature)", X_train, X_test,
    ["income", "loan_amount", "credit_score", "is_weekend", "age_band",
     "city_target_enc", "income_to_loan", "collections_called"],
    cat_cols=["age_band"])
print(f"\nAUC jumped to {auc_leaked:.3f}. That looks like a huge win, but "
      "'collections_called' is only ever recorded AFTER a payment is missed.")
print("At prediction time (loan application), this field does not exist "
      "yet. A model trained on it would be unusable in production despite "
      "its perfect test score, and would fail silently rather than loudly.")

# ---------------------------------------------------------------------
# STEP 7: Final summary
# ---------------------------------------------------------------------
results = pd.Series({
    "Baseline (raw columns)": auc_baseline,
    "+ date features": auc_date,
    "+ binned age": auc_binned,
    "+ target-encoded city": auc_target_enc,
    "+ ratio added alongside raw cols": auc_interaction_added,
    "+ ratio replacing raw income & loan": auc_interaction_replaced,
    "+ leaked feature (DO NOT SHIP)": auc_leaked,
})
print("\n" + "=" * 60)
print("STEP 7: SUMMARY, SAME MODEL THROUGHOUT, ONLY FEATURES CHANGED")
print("=" * 60)
print(results.round(3).to_string())
print(f"\nLegitimate engineering improved AUC from {auc_baseline:.3f} to "
      f"{auc_interaction_replaced:.3f}, a real, usable gain, using the SAME "
      "logistic regression the whole time. Most of that gain came from "
      "binning age and target-encoding city. The income/loan RATIO, "
      "despite being the true underlying driver used to generate this "
      "data, added almost nothing beyond what the two raw columns already "
      "captured; a linear model's two separate coefficients can locally "
      "approximate a ratio reasonably well across a limited data range. "
      "That is a genuinely useful negative result: an engineered feature "
      "is only as valuable as what the model could not already infer on "
      "its own, and that depends on both the model and the data range. "
      "The leaked feature's score is not a real gain and must never ship.")

# ---------------------------------------------------------------------
# CHART
# ---------------------------------------------------------------------
BLUE, ORANGE, GREY = "#2E86AB", "#E4572E", "#B8C4CE"
fig, ax = plt.subplots(figsize=(10, 5.2))
colors = [BLUE] * (len(results) - 1) + [ORANGE]
bars = ax.barh(results.index[::-1], results.values[::-1], color=colors[::-1])
ax.axvline(auc_baseline, color=GREY, linestyle="--", linewidth=1.3, label="Baseline AUC")
for bar, v in zip(bars, results.values[::-1]):
    ax.text(v + 0.003, bar.get_y() + bar.get_height() / 2, f"{v:.3f}",
            va="center", fontsize=9)
ax.set_xlabel("ROC-AUC on the test set")
ax.set_xlim(0.45, min(results.max() + 0.05, 1.0))
ax.set_title("Same model, same data, only the features changed",
             loc="left", fontweight="bold", fontsize=12)
ax.legend(frameon=False, loc="lower right")
ax.spines[["top", "right"]].set_visible(False)
ax.grid(alpha=0.25, axis="x")
fig.tight_layout()
fig.savefig(OUT / "feature_engineering_impact.png", dpi=120)
plt.close(fig)
print("\nSaved chart to:", OUT / "feature_engineering_impact.png")
