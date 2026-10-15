"""
Potato Project Topic: Machine Learning
Logistic Regression for Churn Prediction

Business question:
    A telecom company loses customers every month ("churn"). Which customers
    are most likely to leave, so the retention team can contact them first?

Day 8 predicted a NUMBER (sales). Today we predict a CATEGORY (churn: yes/no).
That is a classification problem, and it needs different metrics.

What this script covers:
    1. Build a sample customer dataset (about 20% churn)
    2. Prepare features: one-hot encoding and scaling inside a Pipeline
    3. Baseline: "nobody churns" (the accuracy paradox)
    4. Fit logistic regression, read the confusion matrix
    5. Precision, recall, F1 and ROC-AUC
    6. Pick the decision threshold using business costs
    7. Interpret the model with odds ratios
    8. Score a new customer

Run it with:  python "Logistic Regression for Churn Prediction.py"
Requires:     numpy, pandas, scikit-learn, matplotlib
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

OUT = Path(__file__).parent / "charts"
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 120)

# ---------------------------------------------------------------------
# STEP 1: Create a sample customer dataset
# ---------------------------------------------------------------------
# Hidden rules used to generate churn (the model must rediscover them):
#   longer tenure -> less churn | higher bill -> more churn
#   more support calls -> more churn | month-to-month contract -> more churn
#   autopay -> less churn
rng = np.random.default_rng(42)
n = 3000
tenure = rng.integers(1, 73, n)                                   # months as a customer
monthly_charges = rng.normal(70, 25, n).clip(20, 150).round(1)    # Rs. hundreds / month
support_calls = rng.poisson(1.5, n)                               # calls in last 3 months
contract = rng.choice(["Month-to-month", "One year", "Two year"], n, p=[0.55, 0.25, 0.20])
autopay = rng.choice([0, 1], n, p=[0.55, 0.45])

logit = (-0.8
         - 0.035 * tenure
         + 0.018 * (monthly_charges - 70)
         + 0.35 * support_calls
         + np.select([contract == "Month-to-month", contract == "One year"], [0.9, -0.2], -1.0)
         - 0.6 * autopay)
churn = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)

df = pd.DataFrame({"tenure": tenure, "monthly_charges": monthly_charges,
                   "support_calls": support_calls, "contract": contract,
                   "autopay": autopay, "churn": churn})

print("=" * 60)
print("STEP 1: DATA")
print("=" * 60)
print(df.head())
print(f"\nCustomers: {len(df):,} | Churn rate: {df['churn'].mean():.1%}")

# ---------------------------------------------------------------------
# STEP 2: Prepare features and split
# ---------------------------------------------------------------------
# Models need numbers. OneHotEncoder turns "contract" into 0/1 columns, and
# StandardScaler puts numeric features on the same scale so their
# coefficients can be compared. Both live INSIDE a Pipeline so the same steps
# are applied to training and test data, and nothing leaks from test to train.
numeric = ["tenure", "monthly_charges", "support_calls"]
categorical = ["contract"]
passthrough = ["autopay"]

prep = ColumnTransformer([
    ("num", StandardScaler(), numeric),
    ("cat", OneHotEncoder(drop="first"), categorical),
    ("pass", "passthrough", passthrough),
])
X, y = df.drop(columns="churn"), df["churn"]

# stratify=y keeps the churn share the same in train and test; essential when
# one class is rare.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y)
print(f"\nTrain: {len(X_train)} rows | Test: {len(X_test)} rows | "
      f"Churn in test: {y_test.mean():.1%}")

# ---------------------------------------------------------------------
# STEP 3: Baseline, "nobody ever churns"
# ---------------------------------------------------------------------
# With 80% non-churners, always predicting "stays" is right 80% of the time
# while catching ZERO churners. This is the accuracy paradox: accuracy alone
# is misleading when classes are imbalanced.
baseline_pred = np.zeros(len(y_test), dtype=int)
print("\n" + "=" * 60)
print("STEP 3: BASELINE (predict 'stays' for everyone)")
print("=" * 60)
print(f"Accuracy: {accuracy_score(y_test, baseline_pred):.1%} | "
      f"Recall (churners caught): {recall_score(y_test, baseline_pred):.1%}")

# ---------------------------------------------------------------------
# STEP 4: Fit logistic regression
# ---------------------------------------------------------------------
# Logistic regression predicts a PROBABILITY between 0 and 1. By default,
# probability >= 0.5 becomes "will churn". Despite the name, it is a
# classification model.
model = Pipeline([("prep", prep), ("clf", LogisticRegression(max_iter=1000))])
model.fit(X_train, y_train)
proba = model.predict_proba(X_test)[:, 1]
pred_50 = (proba >= 0.5).astype(int)

def metrics(name, y_true, y_pred, y_score=None):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    row = (f"{name:<26} acc {accuracy_score(y_true, y_pred):.3f} | "
           f"precision {precision_score(y_true, y_pred, zero_division=0):.3f} | "
           f"recall {recall_score(y_true, y_pred):.3f} | F1 {f1_score(y_true, y_pred):.3f}")
    if y_score is not None:
        row += f" | AUC {roc_auc_score(y_true, y_score):.3f}"
    print(row)
    return tn, fp, fn, tp

print("\n" + "=" * 60)
print("STEP 4-5: METRICS ON THE TEST SET")
print("=" * 60)
tn, fp, fn, tp = metrics("Logistic regression (0.5)", y_test, pred_50, proba)
print(f"\nConfusion matrix at threshold 0.50:")
print(f"  Correctly kept (TN): {tn:>4}   Wrongly flagged (FP): {fp:>4}")
print(f"  Missed churners (FN): {fn:>3}   Caught churners (TP): {tp:>4}")

# ---------------------------------------------------------------------
# STEP 6: Choose the threshold using business costs
# ---------------------------------------------------------------------
# 0.5 is just a default. The right cut-off depends on what mistakes cost:
#   Missing a churner (FN) loses the customer:        Rs. 5,000
#   Offering a discount to someone who stays (FP):    Rs. 500
# Missing a churner is 10x worse, so we should flag MORE customers.
COST_FN, COST_FP = 5000, 500
# Simplification: we assume every flagged churner is saved by the offer. In
# real life offers only work part of the time, which pushes the best
# threshold higher. A quick rule of thumb for a well-calibrated model:
# break-even threshold = cost_FP / (cost_FP + cost_FN).
BREAK_EVEN = COST_FP / (COST_FP + COST_FN)

# Choose the threshold on the TRAINING data only (using cross-validated
# predictions), then apply it to the test set. Tuning on the test set would
# make the final score look better than it really is.
train_proba = cross_val_predict(model, X_train, y_train, cv=5, method="predict_proba")[:, 1]
thresholds = np.arange(0.05, 0.96, 0.01)

def total_cost(y_true, p, t):
    pred = (p >= t).astype(int)
    fp_ = ((pred == 1) & (y_true == 0)).sum()
    fn_ = ((pred == 0) & (y_true == 1)).sum()
    return fp_ * COST_FP + fn_ * COST_FN

costs = [total_cost(y_train.values, train_proba, t) for t in thresholds]
best_t = float(thresholds[int(np.argmin(costs))])
pred_best = (proba >= best_t).astype(int)

print("\n" + "=" * 60)
print("STEP 6: THRESHOLD CHOSEN BY BUSINESS COST")
print("=" * 60)
print(f"Cost of a missed churner: Rs. {COST_FN:,} | cost of a wasted offer: Rs. {COST_FP:,}")
print(f"Best threshold (from training data): {best_t:.2f} "
      f"(theory says about {BREAK_EVEN:.2f}, so they agree closely)")
tn2, fp2, fn2, tp2 = metrics(f"Logistic regression ({best_t:.2f})", y_test, pred_best, proba)
cost_default = fp * COST_FP + fn * COST_FN
cost_tuned = fp2 * COST_FP + fn2 * COST_FN
cost_nothing = int(y_test.sum()) * COST_FN
print(f"\nTotal cost on the test set:")
print(f"  Do nothing (no model):      Rs. {cost_nothing:,}")
print(f"  Threshold 0.50:             Rs. {cost_default:,}")
print(f"  Threshold {best_t:.2f} (tuned):     Rs. {cost_tuned:,}")

# ---------------------------------------------------------------------
# STEP 7: Interpret with odds ratios
# ---------------------------------------------------------------------
# A coefficient is the change in LOG-ODDS. Exponentiating gives an ODDS RATIO:
# 1.50 means "50% higher odds of churn for each +1 standard deviation".
# Below 1.0 means protective. Because features are scaled, ratios are comparable.
names = numeric + [f"contract: {c}" for c in
                   model.named_steps["prep"].named_transformers_["cat"].categories_[0][1:]] + passthrough
odds = pd.Series(np.exp(model.named_steps["clf"].coef_[0]), index=names).sort_values()
print("\n" + "=" * 60)
print("STEP 7: ODDS RATIOS (per +1 SD for numbers; vs reference for categories)")
print("=" * 60)
print(odds.round(2).to_string())
print("(Reference contract is 'Month-to-month'.)")

# ---------------------------------------------------------------------
# STEP 8: Score a new customer
# ---------------------------------------------------------------------
new_customer = pd.DataFrame({"tenure": [4], "monthly_charges": [95.0], "support_calls": [4],
                             "contract": ["Month-to-month"], "autopay": [0]})
p_new = model.predict_proba(new_customer)[0, 1]
print("\n" + "=" * 60)
print("STEP 8: NEW CUSTOMER")
print("=" * 60)
print(new_customer.to_string(index=False))
print(f"\nChurn probability: {p_new:.1%} -> "
      f"{'FLAG for retention team' if p_new >= best_t else 'no action'}")

# ---------------------------------------------------------------------
# CHART: ROC curve, confusion matrix, odds ratios
# ---------------------------------------------------------------------
BLUE, ORANGE, GREY = "#2E86AB", "#E4572E", "#B8C4CE"
fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))

fpr, tpr, _ = roc_curve(y_test, proba)
ax = axes[0]
ax.plot(fpr, tpr, color=BLUE, linewidth=2.4, label=f"Model (AUC = {roc_auc_score(y_test, proba):.2f})")
ax.plot([0, 1], [0, 1], color=GREY, linestyle="--", label="Random guessing (AUC = 0.50)")
ax.set_xlabel("False positive rate")
ax.set_ylabel("True positive rate (recall)")
ax.set_title("The model separates churners from loyal customers", loc="left",
             fontweight="bold", fontsize=11)
ax.legend(frameon=False, loc="lower right")

ax = axes[1]
cm = np.array([[tn2, fp2], [fn2, tp2]])
ax.imshow(cm, cmap="Blues")
for i in range(2):
    for j in range(2):
        ax.text(j, i, f"{cm[i, j]}", ha="center", va="center", fontsize=18,
                color="white" if cm[i, j] > cm.max() / 2 else "black")
ax.set_xticks([0, 1]); ax.set_xticklabels(["Predicted: stays", "Predicted: churns"])
ax.set_yticks([0, 1]); ax.set_yticklabels(["Actually stayed", "Actually churned"])
ax.set_title(f"Confusion matrix at threshold {best_t:.2f}", loc="left",
             fontweight="bold", fontsize=11)
ax.grid(False)

ax = axes[2]
colors = [ORANGE if v > 1 else BLUE for v in odds.values]
ax.barh(odds.index, odds.values, color=colors)
ax.axvline(1, color="black", linewidth=1)
ax.set_xlabel("Odds ratio (above 1 = raises churn odds)")
ax.set_title("What drives churn", loc="left", fontweight="bold", fontsize=11)

for a in (axes[0], axes[2]):
    a.spines[["top", "right"]].set_visible(False)
    a.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "churn_model_results.png", dpi=120)
plt.close(fig)
print("\nSaved chart to:", OUT / "churn_model_results.png")
