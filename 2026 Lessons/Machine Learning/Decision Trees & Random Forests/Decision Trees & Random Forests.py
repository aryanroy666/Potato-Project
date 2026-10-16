"""
Potato Project Topic: Machine Learning
Decision Trees and Random Forests

Business question:
    Same churn problem as Logistic Regression. Can a tree-based
    model do better? And what do we gain or lose by switching?

A DECISION TREE asks a series of yes/no questions, like a flowchart or the
game "20 Questions": "Is tenure < 6 months? If yes, is monthly charge >
Rs. 80? ..." A RANDOM FOREST builds many different trees on random slices
of the data and lets them vote, which usually works better than any single
tree.

What this script covers:
    1. Reuse the Day 13 churn dataset (same data = a fair comparison)
    2. Fit a single decision tree and visualise its logic
    3. Show overfitting: a deep tree memorises, a shallow tree generalises
    4. Find the best depth with cross-validation
    5. Fit a random forest and compare metrics with the tree and Day 13
    6. Feature importance: which signals matter, and how it differs from
       logistic regression's odds ratios
    7. Score the same new customer as Day 13 and compare

Run it with:  python "Decision Trees and Random Forests.py"
Requires:     numpy, pandas, scikit-learn, matplotlib
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree

OUT = Path(__file__).parent / "charts"
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 120)

# ---------------------------------------------------------------------
# STEP 1: Same churn dataset as Day 13 (same seed = identical data)
# ---------------------------------------------------------------------
# Using the exact same generation code as Day 13 keeps the comparison fair:
# both models are judged on the same customers.
rng = np.random.default_rng(42)
n = 3000
tenure = rng.integers(1, 73, n)
monthly_charges = rng.normal(70, 25, n).clip(20, 150).round(1)
support_calls = rng.poisson(1.5, n)
contract = rng.choice(["Month-to-month", "One year", "Two year"], n, p=[0.55, 0.25, 0.20])
autopay = rng.choice([0, 1], n, p=[0.55, 0.45])

logit = (-0.8 - 0.035 * tenure + 0.018 * (monthly_charges - 70) + 0.35 * support_calls
         + np.select([contract == "Month-to-month", contract == "One year"], [0.9, -0.2], -1.0)
         - 0.6 * autopay)
churn = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)

df = pd.DataFrame({"tenure": tenure, "monthly_charges": monthly_charges,
                   "support_calls": support_calls, "contract": contract,
                   "autopay": autopay, "churn": churn})
print("=" * 60)
print("STEP 1: DATA (identical generation to Day 13)")
print("=" * 60)
print(f"Customers: {len(df):,} | Churn rate: {df['churn'].mean():.1%}")

numeric, categorical, passthrough = ["tenure", "monthly_charges", "support_calls"], ["contract"], ["autopay"]
prep = ColumnTransformer([
    ("num", StandardScaler(), numeric),
    ("cat", OneHotEncoder(drop="first"), categorical),
    ("pass", "passthrough", passthrough),
])
X, y = df.drop(columns="churn"), df["churn"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
feature_names = numeric + [f"contract_{c}" for c in ["One year", "Two year"]] + passthrough

def metrics(name, y_true, y_pred, y_score):
    row = (f"{name:<28} acc {accuracy_score(y_true, y_pred):.3f} | "
           f"precision {precision_score(y_true, y_pred, zero_division=0):.3f} | "
           f"recall {recall_score(y_true, y_pred):.3f} | F1 {f1_score(y_true, y_pred):.3f} | "
           f"AUC {roc_auc_score(y_true, y_score):.3f}")
    print(row)

# ---------------------------------------------------------------------
# STEP 2: A single decision tree, and what it actually looks like
# ---------------------------------------------------------------------
# A shallow tree (max_depth=3) is small enough to read like a flowchart.
# Trees handle mixed numeric/categorical data and need NO scaling, unlike
# logistic regression, because they only ever ask "is this value > X?".
tree_prep = ColumnTransformer([
    ("num", "passthrough", numeric),
    ("cat", OneHotEncoder(drop="first"), categorical),
    ("pass", "passthrough", passthrough),
])
small_tree = Pipeline([("prep", tree_prep),
                       ("clf", DecisionTreeClassifier(max_depth=3, random_state=42))])
small_tree.fit(X_train, y_train)

print("\n" + "=" * 60)
print("STEP 2: A SHALLOW TREE, READ AS A FLOWCHART")
print("=" * 60)
print(export_text(small_tree.named_steps["clf"], feature_names=feature_names))

fig, ax = plt.subplots(figsize=(14, 7))
plot_tree(small_tree.named_steps["clf"], feature_names=feature_names,
          class_names=["Stays", "Churns"], filled=True, rounded=True,
          fontsize=9, proportion=False, ax=ax)
ax.set_title("The model's logic, three questions deep", loc="left", fontweight="bold", fontsize=13)
fig.tight_layout()
fig.savefig(OUT / "decision_tree_diagram.png", dpi=120)
plt.close(fig)
print("\nSaved tree diagram to:", OUT / "decision_tree_diagram.png")

# ---------------------------------------------------------------------
# STEP 3: Overfitting, shallow vs deep
# ---------------------------------------------------------------------
# Analogy: a student who memorises every practice question verbatim aces
# the practice set but fails the real exam, because they learned the
# QUESTIONS, not the SUBJECT. An unlimited-depth tree can carve out one
# leaf per training example: perfect training accuracy, poor generalisation.
print("\n" + "=" * 60)
print("STEP 3: OVERFITTING, TRAIN VS TEST ACCURACY BY DEPTH")
print("=" * 60)
depths = [1, 2, 3, 5, 8, 12, 20, None]
depth_rows = []
for d in depths:
    m = Pipeline([("prep", tree_prep), ("clf", DecisionTreeClassifier(max_depth=d, random_state=42))])
    m.fit(X_train, y_train)
    tr_acc = accuracy_score(y_train, m.predict(X_train))
    te_acc = accuracy_score(y_test, m.predict(X_test))
    depth_rows.append((d if d else "None (unlimited)", tr_acc, te_acc))
    print(f"max_depth = {str(d):<16} train acc = {tr_acc:.3f} | test acc = {te_acc:.3f} | "
          f"gap = {tr_acc - te_acc:+.3f}")

# ---------------------------------------------------------------------
# STEP 4: Find the best depth with cross-validation
# ---------------------------------------------------------------------
# Instead of eyeballing the table above, GridSearchCV tries each depth with
# 5-fold cross-validation and picks the one with the best AVERAGE score,
# which is a more honest choice than picking from a single train/test split.
grid = GridSearchCV(
    Pipeline([("prep", tree_prep), ("clf", DecisionTreeClassifier(random_state=42))]),
    param_grid={"clf__max_depth": [2, 3, 4, 5, 6, 8, 10, 15]},
    scoring="roc_auc", cv=5,
)
grid.fit(X_train, y_train)
best_depth = grid.best_params_["clf__max_depth"]
print("\n" + "=" * 60)
print("STEP 4: BEST DEPTH BY 5-FOLD CROSS-VALIDATION (scoring = ROC-AUC)")
print("=" * 60)
print(f"Best max_depth: {best_depth} | CV AUC: {grid.best_score_:.3f}")

tree_final = Pipeline([("prep", tree_prep),
                       ("clf", DecisionTreeClassifier(max_depth=best_depth, random_state=42))])
tree_final.fit(X_train, y_train)
tree_proba = tree_final.predict_proba(X_test)[:, 1]
tree_pred = (tree_proba >= 0.5).astype(int)

# ---------------------------------------------------------------------
# STEP 5: Random forest, and compare all three models
# ---------------------------------------------------------------------
# A forest trains many trees, each on a random bootstrap sample of rows and
# a random subset of features at each split, then averages their votes.
# Analogy: asking 300 doctors for a second opinion and going with the
# majority, instead of trusting just one doctor's judgement.
forest = Pipeline([("prep", tree_prep),
                   ("clf", RandomForestClassifier(n_estimators=300, max_depth=8,
                                                   min_samples_leaf=5, random_state=42, n_jobs=-1))])
forest.fit(X_train, y_train)
forest_proba = forest.predict_proba(X_test)[:, 1]
forest_pred = (forest_proba >= 0.5).astype(int)

# Re-fit Day 13's logistic regression here so every number in this script
# comes from one run, on the exact same split.
logreg = Pipeline([("prep", prep), ("clf", LogisticRegression(max_iter=1000))])
logreg.fit(X_train, y_train)
logreg_proba = logreg.predict_proba(X_test)[:, 1]
logreg_pred = (logreg_proba >= 0.5).astype(int)

print("\n" + "=" * 60)
print("STEP 5: ALL THREE MODELS, THRESHOLD 0.50, SAME TEST SET")
print("=" * 60)
metrics("Logistic regression", y_test, logreg_pred, logreg_proba)
metrics(f"Decision tree (depth {best_depth})", y_test, tree_pred, tree_proba)
metrics("Random forest (300 trees)", y_test, forest_pred, forest_proba)

# ---------------------------------------------------------------------
# STEP 6: Feature importance vs odds ratios
# ---------------------------------------------------------------------
# A tree/forest's importance = how much each feature reduces impurity
# (roughly, "how useful was this feature for splitting the data?"),
# averaged over all trees for a forest. It has NO sign and NO units, unlike
# logistic regression's odds ratios, which say "raises" or "lowers" risk by
# how much. Importance says WHICH features matter; odds ratios say HOW.
importance = pd.Series(
    forest.named_steps["clf"].feature_importances_, index=feature_names
).sort_values(ascending=False)
print("\n" + "=" * 60)
print("STEP 6: RANDOM FOREST FEATURE IMPORTANCE")
print("=" * 60)
print(importance.round(3).to_string())

# ---------------------------------------------------------------------
# STEP 7: Score the same new customer as Day 13
# ---------------------------------------------------------------------
new_customer = pd.DataFrame({"tenure": [4], "monthly_charges": [95.0], "support_calls": [4],
                             "contract": ["Month-to-month"], "autopay": [0]})
print("\n" + "=" * 60)
print("STEP 7: SAME NEW CUSTOMER AS DAY 13")
print("=" * 60)
print(new_customer.to_string(index=False))
print(f"\nLogistic regression: {logreg.predict_proba(new_customer)[0, 1]:.1%} churn probability")
print(f"Decision tree:       {tree_final.predict_proba(new_customer)[0, 1]:.1%} churn probability")
print(f"Random forest:       {forest.predict_proba(new_customer)[0, 1]:.1%} churn probability")

# ---------------------------------------------------------------------
# CHART: overfitting curve, feature importance, model comparison
# ---------------------------------------------------------------------
BLUE, ORANGE, GREY, GREEN = "#2E86AB", "#E4572E", "#B8C4CE", "#7FB069"
fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))

ax = axes[0]
x_labels = [str(d) for d, _, _ in depth_rows]
train_accs = [r[1] for r in depth_rows]
test_accs = [r[2] for r in depth_rows]
ax.plot(x_labels, train_accs, marker="o", color=ORANGE, linewidth=2, label="Train accuracy")
ax.plot(x_labels, test_accs, marker="o", color=BLUE, linewidth=2, label="Test accuracy")
ax.axvline(x_labels.index(str(best_depth)), color=GREEN, linestyle="--", linewidth=1.5,
           label=f"Chosen depth ({best_depth})")
ax.set_xlabel("max_depth")
ax.set_ylabel("Accuracy")
ax.set_title("Train accuracy keeps climbing; test accuracy does not", loc="left",
             fontweight="bold", fontsize=10.5)
ax.legend(frameon=False, fontsize=8.5)
ax.tick_params(axis="x", rotation=45)

ax = axes[1]
ax.barh(importance.index[::-1], importance.values[::-1], color=BLUE)
ax.set_xlabel("Importance (impurity reduction)")
ax.set_title(f"{importance.index[0]} drives the most splits", loc="left",
             fontweight="bold", fontsize=10.5)

ax = axes[2]
model_names = ["Logistic\nRegression", f"Decision\nTree (d={best_depth})", "Random\nForest"]
aucs = [roc_auc_score(y_test, logreg_proba), roc_auc_score(y_test, tree_proba),
        roc_auc_score(y_test, forest_proba)]
recalls = [recall_score(y_test, logreg_pred), recall_score(y_test, tree_pred), recall_score(y_test, forest_pred)]
xpos = np.arange(3)
ax.bar(xpos - 0.17, aucs, width=0.34, color=BLUE, label="ROC-AUC")
ax.bar(xpos + 0.17, recalls, width=0.34, color=ORANGE, label="Recall @ 0.50")
ax.set_xticks(xpos)
ax.set_xticklabels(model_names, fontsize=9)
ax.set_ylim(0, 1)
best_auc_i = int(np.argmax(aucs))
ax.set_title(f"{model_names[best_auc_i].replace(chr(10), ' ')} has the highest AUC",
             loc="left", fontweight="bold", fontsize=10.5)
ax.legend(frameon=False, fontsize=8.5)

for a in axes:
    a.spines[["top", "right"]].set_visible(False)
    a.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "tree_forest_comparison.png", dpi=120)
plt.close(fig)
print("\nSaved chart to:", OUT / "tree_forest_comparison.png")
