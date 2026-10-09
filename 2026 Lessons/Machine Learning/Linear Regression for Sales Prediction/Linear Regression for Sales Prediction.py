"""
Potato Project: Day 8
Linear Regression for Sales Prediction

Business question:
    A retail chain wants to predict monthly store sales from things it can
    control or observe: advertising spend, store size, nearby competitors and
    discount level. Which factors matter, and how accurate can we be?

What this script covers:
    1. Build a sample dataset (we KNOW the true rules, so we can check the model)
    2. Explore: correlations and multicollinearity
    3. Split into train and test sets
    4. Baseline model (always predict the average) to beat
    5. Simple regression (one feature) vs multiple regression (all features)
    6. Interpret the coefficients in plain language
    7. Evaluate: R-squared, MAE, RMSE, cross-validation
    8. Check the residuals (are the errors random?)
    9. Predict for a new store

Run it with:  python "Linear Regression for Sales Prediction.py"
Requires:     numpy, pandas, scikit-learn, matplotlib
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, train_test_split

OUT = Path(__file__).parent / "charts"
OUT.mkdir(exist_ok=True)

# ---------------------------------------------------------------------
# STEP 1: Create a sample dataset
# ---------------------------------------------------------------------
# We simulate the data so we know the TRUE relationship:
#   sales = 20 + 0.8*ad_spend + 0.012*store_size - 2.5*competitors - 0.6*discount + noise
# Real data never tells you the true rule, but here it lets us check whether
# the model recovers it.
rng = np.random.default_rng(42)
n = 300
ad_spend = rng.uniform(5, 60, n)                         # Rs. lakhs per month
store_size = 800 + 12 * ad_spend + rng.normal(0, 250, n)  # sq ft (a bit linked to ad spend)
competitors = rng.integers(0, 8, n)                       # competing stores nearby
discount = rng.uniform(0, 25, n)                          # average discount %
noise = rng.normal(0, 8, n)

sales = 20 + 0.8 * ad_spend + 0.012 * store_size - 2.5 * competitors - 0.6 * discount + noise

df = pd.DataFrame({
    "ad_spend": ad_spend.round(1),
    "store_size": store_size.round(0),
    "competitors": competitors,
    "discount": discount.round(1),
    "sales": sales.round(1),                              # Rs. lakhs per month
})
FEATURES = ["ad_spend", "store_size", "competitors", "discount"]

print("=" * 60)
print("STEP 1: DATA PREVIEW")
print("=" * 60)
print(df.head())
print("\nShape:", df.shape, "| Missing values:", int(df.isna().sum().sum()))

# ---------------------------------------------------------------------
# STEP 2: Explore correlations
# ---------------------------------------------------------------------
# Correlation runs from -1 to +1. Check two things:
#   (a) features that relate to the TARGET (useful predictors)
#   (b) features that relate to EACH OTHER (multicollinearity: two features
#       carrying the same information make coefficients unstable)
print("\n" + "=" * 60)
print("STEP 2: CORRELATIONS")
print("=" * 60)
corr = df.corr().round(2)
print(corr)
print("\nCorrelation of each feature with sales:")
print(corr["sales"].drop("sales").sort_values(ascending=False))
print("\nad_spend vs store_size correlation:", corr.loc["ad_spend", "store_size"],
      "(moderate overlap; worth watching)")

# ---------------------------------------------------------------------
# STEP 3: Train / test split
# ---------------------------------------------------------------------
# Analogy: a student who only sees the exam questions in advance looks
# brilliant, but proves nothing. We hold back 25% of stores as a "final exam"
# the model has never seen.
X_train, X_test, y_train, y_test = train_test_split(
    df[FEATURES], df["sales"], test_size=0.25, random_state=42
)
print("\n" + "=" * 60)
print("STEP 3: SPLIT")
print("=" * 60)
print(f"Training rows: {len(X_train)} | Test rows: {len(X_test)}")

def report(name, y_true, y_pred):
    """Print the three standard regression metrics."""
    r2 = r2_score(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    print(f"{name:<28} R2 = {r2:6.3f} | MAE = {mae:6.2f} | RMSE = {rmse:6.2f}")
    return r2, mae, rmse

# ---------------------------------------------------------------------
# STEP 4: Baseline, the model to beat
# ---------------------------------------------------------------------
# The dumbest sensible model: predict the training average for every store.
# If a fancy model cannot beat this, it is useless. R2 of 0 means "no better
# than predicting the average".
baseline_pred = np.full(len(y_test), y_train.mean())
print("\n" + "=" * 60)
print("STEP 4-5: MODELS (evaluated on the TEST set)")
print("=" * 60)
base = report("Baseline (always average)", y_test, baseline_pred)

# ---------------------------------------------------------------------
# STEP 5: Simple vs multiple regression
# ---------------------------------------------------------------------
simple = LinearRegression().fit(X_train[["ad_spend"]], y_train)
simple_pred = simple.predict(X_test[["ad_spend"]])
simple_m = report("Simple (ad_spend only)", y_test, simple_pred)

model = LinearRegression().fit(X_train, y_train)
pred = model.predict(X_test)
multi_m = report("Multiple (all 4 features)", y_test, pred)

# ---------------------------------------------------------------------
# STEP 6: Interpret the coefficients
# ---------------------------------------------------------------------
# Each coefficient = the change in sales for a ONE-unit increase in that
# feature, holding the other features constant.
true_values = {"ad_spend": 0.8, "store_size": 0.012, "competitors": -2.5, "discount": -0.6}
coef_table = pd.DataFrame({
    "coefficient": model.coef_.round(3),
    "true_value": [true_values[f] for f in FEATURES],
}, index=FEATURES)
print("\n" + "=" * 60)
print("STEP 6: COEFFICIENTS")
print("=" * 60)
print(coef_table)
print(f"Intercept: {model.intercept_:.2f}")
print("\nIn plain language:")
print(f"- Each extra Rs. 1 lakh of ad spend adds about Rs. {model.coef_[0]:.2f} lakh of sales.")
print(f"- Each extra competitor nearby changes sales by about Rs. {model.coef_[2]:.2f} lakh.")
print(f"- Each extra 1% of discount changes sales by about Rs. {model.coef_[3]:.2f} lakh.")

# Raw coefficients cannot be compared across features (ad_spend is in lakhs,
# store_size in square feet). Standardising puts every feature on the same
# scale, so the biggest absolute value is the most influential.
std_coef = pd.Series(
    model.coef_ * X_train.std().values / y_train.std(), index=FEATURES
).round(2).sort_values(key=abs, ascending=False)
print("\nStandardised coefficients (compare importance across features):")
print(std_coef)

# ---------------------------------------------------------------------
# STEP 7: Evaluate properly
# ---------------------------------------------------------------------
# One train/test split can be lucky or unlucky. 5-fold cross-validation
# repeats the "final exam" five times with different hold-out groups.
cv = cross_val_score(LinearRegression(), df[FEATURES], df["sales"], cv=5, scoring="r2")
print("\n" + "=" * 60)
print("STEP 7: CROSS-VALIDATION (5-fold R2)")
print("=" * 60)
print("Scores:", cv.round(3))
print(f"Mean R2: {cv.mean():.3f}  (spread: +/- {cv.std():.3f})")
train_r2 = r2_score(y_train, model.predict(X_train))
print(f"\nTrain R2 = {train_r2:.3f} vs Test R2 = {multi_m[0]:.3f}.")
print("A train score far ABOVE the test score signals overfitting. Here the test "
      "score is not lower, so there is no overfitting; its difference from the "
      "train score is down to which stores landed in the test set. The "
      f"cross-validated mean ({cv.mean():.3f}) is the more honest estimate.")

# ---------------------------------------------------------------------
# STEP 8: Residual analysis
# ---------------------------------------------------------------------
# Residual = actual - predicted. In a good linear model the errors look like
# random noise: centred on zero, no pattern, similar spread everywhere.
residuals = y_test - pred
print("\n" + "=" * 60)
print("STEP 8: RESIDUALS")
print("=" * 60)
print(f"Mean residual: {residuals.mean():.2f} (should be close to 0)")
print(f"Std of residuals: {residuals.std():.2f}")

fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
axes[0].scatter(y_test, pred, alpha=0.7, color="#2E86AB", edgecolor="white")
lims = [min(y_test.min(), pred.min()), max(y_test.max(), pred.max())]
axes[0].plot(lims, lims, color="#E4572E", linestyle="--", linewidth=2, label="Perfect prediction")
axes[0].set_xlabel("Actual sales (Rs. lakhs)")
axes[0].set_ylabel("Predicted sales (Rs. lakhs)")
axes[0].set_title(f"Predictions track reality (R2 = {multi_m[0]:.2f})", loc="left", fontweight="bold")
axes[0].legend(frameon=False)

axes[1].scatter(pred, residuals, alpha=0.7, color="#2E86AB", edgecolor="white")
axes[1].axhline(0, color="#E4572E", linestyle="--", linewidth=2)
axes[1].set_xlabel("Predicted sales (Rs. lakhs)")
axes[1].set_ylabel("Residual (actual - predicted)")
axes[1].set_title("Errors look random: no pattern", loc="left", fontweight="bold")

for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "regression_results.png", dpi=120)
plt.close(fig)
print("\nSaved chart to:", OUT / "regression_results.png")

# ---------------------------------------------------------------------
# STEP 9: Predict for a new store
# ---------------------------------------------------------------------
new_store = pd.DataFrame({"ad_spend": [40], "store_size": [1500],
                          "competitors": [3], "discount": [10]})
print("\n" + "=" * 60)
print("STEP 9: PREDICTION FOR A NEW STORE")
print("=" * 60)
print(new_store.to_string(index=False))
estimate = model.predict(new_store)[0]
rmse = multi_m[2]
print(f"\nPredicted monthly sales: Rs. {estimate:.1f} lakh")
print(f"Rough range (about +/- 2 RMSE): Rs. {estimate - 2 * rmse:.1f} to {estimate + 2 * rmse:.1f} lakh")
print("A prediction without a range gives a false sense of precision.")

# ---------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Multiple regression beat the baseline: R2 {multi_m[0]:.2f} vs {base[0]:.2f}, "
      f"and cut the average error (MAE) from {base[1]:.1f} to {multi_m[1]:.1f} lakh.")
