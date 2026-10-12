"""
Potato Project Topic: Customer Analytics 
Cohort Retention Analysis

Business question:
    Of the customers who joined in a given month, how many are still active
    1, 2, 3... months later? And are newer customers sticking around better
    than older ones?

A COHORT is a group of customers who share a starting point (here: the month
they signed up). Comparing cohorts is fairer than looking at one overall
number, because a blended average hides whether things are getting better.

What this script covers:
    1. Build users and activity tables
    2. Assign each user to a signup-month cohort
    3. Calculate "months since signup" for every activity
    4. Build the cohort retention matrix
    5. Plot it as a heatmap
    6. Average retention curve and early-vs-late cohort comparison

Run it with:  python "Cohort Retention Analysis.py"
Requires:     numpy, pandas, matplotlib
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "charts"
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 130)
pd.set_option("display.max_columns", 20)

# ---------------------------------------------------------------------
# STEP 0: Create sample data
# ---------------------------------------------------------------------
# 9 signup months (Jan to Sep 2026). Hidden rule used to generate activity:
# users who signed up from July onward went through an improved onboarding,
# so more of them come back in month 1. The analysis must discover this.
rng = np.random.default_rng(42)
DATA_END = pd.Timestamp("2026-09-30")

users, activity = [], []
uid = 1
for month in pd.period_range("2026-01", "2026-09", freq="M"):
    n_users = int(rng.integers(260, 340))
    month1_rate = 0.55 if month >= pd.Period("2026-07", "M") else 0.40
    for _ in range(n_users):
        day = int(rng.integers(0, month.days_in_month))
        signup = month.start_time + pd.Timedelta(days=day)
        users.append((uid, signup))
        activity.append((uid, signup))                   # the signup order itself
        k = 1
        while (month + k).end_time <= DATA_END + pd.Timedelta(days=1):
            p = month1_rate * (0.88 ** (k - 1))          # chance of being active in month k
            if rng.random() < p:
                d = int(rng.integers(0, (month + k).days_in_month))
                activity.append((uid, (month + k).start_time + pd.Timedelta(days=d)))
            k += 1
        uid += 1

users = pd.DataFrame(users, columns=["user_id", "signup_date"])
activity = pd.DataFrame(activity, columns=["user_id", "activity_date"])

print("=" * 60)
print("STEP 0: DATA")
print("=" * 60)
print(f"{len(users):,} users | {len(activity):,} activity rows")
print(activity.head(3))

# ---------------------------------------------------------------------
# STEP 1: Assign each user to a cohort
# ---------------------------------------------------------------------
users["cohort"] = users["signup_date"].dt.to_period("M")

# ---------------------------------------------------------------------
# STEP 2: Join activity to cohort and calculate months since signup
# ---------------------------------------------------------------------
df = activity.merge(users[["user_id", "cohort"]], on="user_id", how="left", validate="many_to_one")
df["activity_month"] = df["activity_date"].dt.to_period("M")

# Subtracting two monthly periods gives a month offset. 0 = signup month,
# 1 = the month after, and so on.
df["months_since"] = (df["activity_month"] - df["cohort"]).apply(lambda x: x.n)

# ---------------------------------------------------------------------
# STEP 3: Count unique active users per cohort per month offset
# ---------------------------------------------------------------------
# nunique, not count: a user with 5 orders in one month is still ONE active user.
active = (df.groupby(["cohort", "months_since"])["user_id"]
            .nunique()
            .unstack(fill_value=0))

cohort_size = active[0]                         # everyone is active in month 0
retention = active.divide(cohort_size, axis=0)  # share of the cohort still active

# Mask cells that lie in the future (no data yet), so they show as blank, not 0%.
last_month = pd.Period(DATA_END, "M")
for c in retention.index:
    max_k = (last_month - c).n
    retention.loc[c, retention.columns > max_k] = np.nan

print("\n" + "=" * 60)
print("STEP 3: COHORT SIZES")
print("=" * 60)
print(cohort_size.to_string())

print("\n" + "=" * 60)
print("STEP 4: RETENTION MATRIX (% of cohort active)")
print("=" * 60)
print((retention * 100).round(0).fillna(-1).astype(int).replace(-1, "").to_string())

# ---------------------------------------------------------------------
# STEP 5: Average retention curve (weighted by cohort size)
# ---------------------------------------------------------------------
# A plain average of percentages would give a 260-user cohort the same weight
# as a 340-user cohort. Weighting by size is the correct way.
weighted = {}
for k in retention.columns:
    valid = retention[k].dropna().index
    weighted[k] = active.loc[valid, k].sum() / cohort_size.loc[valid].sum()
avg_curve = pd.Series(weighted)
print("\n" + "=" * 60)
print("STEP 5: AVERAGE RETENTION CURVE")
print("=" * 60)
print((avg_curve * 100).round(1).to_string())

# ---------------------------------------------------------------------
# STEP 6: Did the July onboarding change help?
# ---------------------------------------------------------------------
# Compare month-1 retention before and after July. Only cohorts that already
# HAVE a month-1 value can be compared (September cohort cannot yet).
m1 = retention[1].dropna()
before = m1[m1.index < pd.Period("2026-07", "M")]
after = m1[m1.index >= pd.Period("2026-07", "M")]
w = lambda idx: active.loc[idx, 1].sum() / cohort_size.loc[idx].sum()
print("\n" + "=" * 60)
print("STEP 6: MONTH-1 RETENTION, BEFORE VS AFTER JULY SIGNUPS")
print("=" * 60)
print(f"Jan-Jun cohorts: {w(before.index):.1%}  ({len(before)} cohorts)")
print(f"Jul-Aug cohorts: {w(after.index):.1%}  ({len(after)} cohorts)")
print("Caution: only two 'after' cohorts exist. Treat this as a strong hint,\n"
      "not proof; confirm with more months or a proper A/B test.")

# ---------------------------------------------------------------------
# CHART: heatmap + average curve
# ---------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), gridspec_kw={"width_ratios": [1.6, 1]})

ax = axes[0]
data = retention.values * 100
im = ax.imshow(data, cmap="Blues", vmin=0, vmax=100, aspect="auto")
ax.set_xticks(range(retention.shape[1]))
ax.set_xticklabels([f"M{k}" for k in retention.columns])
ax.set_yticks(range(retention.shape[0]))
ax.set_yticklabels([str(c) for c in retention.index])
for i in range(data.shape[0]):
    for j in range(data.shape[1]):
        if not np.isnan(data[i, j]):
            ax.text(j, i, f"{data[i, j]:.0f}", ha="center", va="center",
                    color="white" if data[i, j] > 55 else "black", fontsize=8)
ax.set_xlabel("Months since signup")
ax.set_ylabel("Signup cohort")
ax.set_title("Newer cohorts (from Jul) hold on to more customers in month 1",
             loc="left", fontweight="bold", fontsize=11)
ax.grid(False)
fig.colorbar(im, ax=ax, label="% of cohort active", shrink=0.8)

ax = axes[1]
ax.plot([f"M{k}" for k in avg_curve.index], avg_curve.values * 100,
        color="#2E86AB", marker="o", linewidth=2.2)
ax.axhline(0, color="black", linewidth=0.8)
ax.set_ylim(0, 105)
ax.set_xlabel("Months since signup")
ax.set_ylabel("% of cohort active")
ax.set_title(f"Biggest drop is right after month 0 ({avg_curve[1] * 100:.0f}% return)",
             loc="left", fontweight="bold", fontsize=11)
for a in axes:
    a.spines[["top", "right"]].set_visible(False)
axes[1].grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "cohort_retention_heatmap.png", dpi=120)
plt.close(fig)
print("\nSaved chart to:", OUT / "cohort_retention_heatmap.png")
