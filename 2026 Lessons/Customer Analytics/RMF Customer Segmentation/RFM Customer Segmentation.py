"""
Potato Project Topic: Cusstomer Analytics
RFM Customer Segmentation

Business question:
    Marketing cannot treat 1,500 customers the same way. Who are our best
    customers, who is about to leave, and what should we do about each group?

RFM scores every customer on three simple questions:
    R = Recency   : how recently did they buy?         (lower days = better)
    F = Frequency : how often do they buy?             (more orders = better)
    M = Monetary  : how much money do they spend?      (more = better)

What this script covers:
    1. Build a sample transactions table
    2. Calculate R, F and M per customer
    3. Score each from 1 to 5 using quintiles
    4. Map score combinations to named segments
    5. Summarise each segment (size, revenue share, behaviour)
    6. Check the 80/20 rule and recommend actions

Run it with:  python "RFM Customer Segmentation.py"
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
pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 20)

# ---------------------------------------------------------------------
# STEP 0: Create a sample transactions table (one row per order)
# ---------------------------------------------------------------------
# Customers are generated from six hidden behaviour types. The analysis
# does NOT see these types; it has to rediscover them from the orders alone.
rng = np.random.default_rng(42)
START, SNAPSHOT = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-10-01")
# type: (share of customers, avg orders, min/max days since last order, avg order value)
types = {
    "champion":   (0.12, 14, 1, 20,   2500),
    "loyal":      (0.18,  8, 10, 60,  1500),
    "new":        (0.15,  1.2, 1, 30, 1000),
    "slipping":   (0.15,  7, 120, 250, 1800),
    "occasional": (0.15,  3, 60, 150,  900),
    "dormant":    (0.25,  2, 200, 360, 700),
}
n_customers = 1500
names = list(types)
assigned = rng.choice(names, n_customers, p=[types[k][0] for k in names])

rows = []
for cid, kind in enumerate(assigned, start=1001):
    _, lam, lo, hi, aov = types[kind]
    n_orders = max(1, rng.poisson(lam))
    last_gap = int(rng.integers(lo, hi + 1))
    last_date = SNAPSHOT - pd.Timedelta(days=last_gap)
    span = max((last_date - START).days, 1)
    days = np.append(rng.integers(0, span, n_orders - 1), span)  # last order sits on last_date
    for d in days:
        rows.append((cid, START + pd.Timedelta(days=int(d)),
                     round(float(aov * rng.lognormal(0, 0.35)), 0)))
orders = pd.DataFrame(rows, columns=["customer_id", "order_date", "amount"])

print("=" * 60)
print("STEP 0: TRANSACTIONS")
print("=" * 60)
print(orders.head())
print(f"\n{len(orders):,} orders from {orders['customer_id'].nunique():,} customers "
      f"between {orders['order_date'].min().date()} and {orders['order_date'].max().date()}")

# ---------------------------------------------------------------------
# STEP 1: Calculate R, F and M per customer
# ---------------------------------------------------------------------
# Snapshot date = "today" for the analysis. Always fix it explicitly instead
# of using the real today, otherwise results change every time you re-run.
rfm = orders.groupby("customer_id").agg(
    recency=("order_date", lambda d: (SNAPSHOT - d.max()).days),
    frequency=("order_date", "count"),
    monetary=("amount", "sum"),
)
print("\n" + "=" * 60)
print("STEP 1: RAW RFM VALUES")
print("=" * 60)
print(rfm.describe().round(1))

# ---------------------------------------------------------------------
# STEP 2: Score each dimension from 1 (worst) to 5 (best)
# ---------------------------------------------------------------------
# qcut splits customers into 5 equal-sized groups (quintiles).
# Analogy: ranking a class and giving the top 20% a 5, the next 20% a 4...
# Recency is REVERSED: fewer days since last order is better, so it gets a
# higher score. rank(method="first") breaks ties so qcut never fails when many
# customers share the same value (very common for frequency).
rfm["R"] = pd.qcut(rfm["recency"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
rfm["F"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["M"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["RFM_score"] = rfm["R"].astype(str) + rfm["F"].astype(str) + rfm["M"].astype(str)

print("\n" + "=" * 60)
print("STEP 2: RFM SCORES (first 5 customers)")
print("=" * 60)
print(rfm.head())

# ---------------------------------------------------------------------
# STEP 3: Map score combinations to named segments
# ---------------------------------------------------------------------
# 125 possible scores (5x5x5) are too many to act on, so we group them.
# Segments use R (is the customer still active?) and F (are they habitual?).
# Order matters: the first rule that matches wins.
def segment(row):
    r, f = row["R"], row["F"]
    if r >= 4 and f >= 4:
        return "Champions"
    if r >= 3 and f >= 3:
        return "Loyal Customers"
    if r >= 4 and f <= 2:
        return "New / Promising"
    if r <= 2 and f >= 3:
        return "At Risk"
    if r <= 2 and f <= 2:
        return "Hibernating"
    return "Need Attention"

rfm["segment"] = rfm.apply(segment, axis=1)

# ---------------------------------------------------------------------
# STEP 4: Summarise each segment
# ---------------------------------------------------------------------
summary = rfm.groupby("segment").agg(
    customers=("segment", "size"),
    avg_recency_days=("recency", "mean"),
    avg_orders=("frequency", "mean"),
    avg_spend=("monetary", "mean"),
    total_revenue=("monetary", "sum"),
)
summary["pct_customers"] = summary["customers"] / summary["customers"].sum() * 100
summary["pct_revenue"] = summary["total_revenue"] / summary["total_revenue"].sum() * 100
summary = summary.sort_values("total_revenue", ascending=False)

print("\n" + "=" * 60)
print("STEP 4: SEGMENT SUMMARY")
print("=" * 60)
print(summary.round(1))

# ---------------------------------------------------------------------
# STEP 5: The 80/20 (Pareto) check
# ---------------------------------------------------------------------
# Rule of thumb: a small share of customers often brings most of the revenue.
# Check it instead of assuming it.
sorted_rev = rfm["monetary"].sort_values(ascending=False)
top20_share = sorted_rev.head(int(len(sorted_rev) * 0.2)).sum() / sorted_rev.sum() * 100
print("\n" + "=" * 60)
print("STEP 5: 80/20 CHECK")
print("=" * 60)
print(f"Top 20% of customers bring {top20_share:.0f}% of revenue")

# Revenue at stake: customers who used to buy often but have gone quiet
at_risk_rev = summary.loc["At Risk", "total_revenue"] if "At Risk" in summary.index else 0
print(f"Historical revenue from the 'At Risk' group: Rs. {at_risk_rev:,.0f} "
      f"({summary.loc['At Risk', 'pct_revenue']:.1f}% of total)")

# ---------------------------------------------------------------------
# STEP 6: Recommended action per segment
# ---------------------------------------------------------------------
actions = {
    "Champions": "Reward them: early access, loyalty perks, ask for reviews and referrals",
    "Loyal Customers": "Upsell and cross-sell; nudge them toward Champion behaviour",
    "New / Promising": "Welcome series and a second-purchase offer to build the habit",
    "At Risk": "Urgent win-back: personal outreach, 'we miss you' offer before they churn",
    "Need Attention": "Reminder campaigns and targeted offers based on past purchases",
    "Hibernating": "Low-cost reactivation test; stop spending heavily if no response",
}
print("\n" + "=" * 60)
print("STEP 6: RECOMMENDED ACTIONS")
print("=" * 60)
for seg in summary.index:
    print(f"{seg:<17} -> {actions[seg]}")

# ---------------------------------------------------------------------
# CHART: who they are and how much they matter
# ---------------------------------------------------------------------
BLUE, ORANGE, GREY = "#2E86AB", "#E4572E", "#B8C4CE"
order = summary.sort_values("pct_revenue").index.tolist()
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

ax = axes[0]
y = np.arange(len(order))
ax.barh(y + 0.2, summary.loc[order, "pct_customers"], height=0.38, color=GREY, label="% of customers")
ax.barh(y - 0.2, summary.loc[order, "pct_revenue"], height=0.38, color=BLUE, label="% of revenue")
ax.set_yticks(y)
ax.set_yticklabels(order)
ax.set_xlabel("Percent")
top = summary["pct_revenue"].idxmax()
ax.set_title(f"{top} are {summary.loc[top, 'pct_customers']:.0f}% of customers "
             f"but {summary.loc[top, 'pct_revenue']:.0f}% of revenue", loc="left", fontweight="bold", fontsize=11)
ax.legend(frameon=False, loc="lower right")

ax = axes[1]
palette = {"Champions": ORANGE, "Loyal Customers": BLUE, "New / Promising": "#7FB069",
           "At Risk": "#F2A541", "Need Attention": "#9B8FB5", "Hibernating": GREY}
for seg, g in rfm.groupby("segment"):
    ax.scatter(g["recency"], g["frequency"], s=14, alpha=0.6, color=palette[seg], label=seg)
ax.set_xlabel("Recency (days since last order)")
ax.set_ylabel("Frequency (number of orders)")
ax.set_title("Active, frequent buyers sit top-left; lapsed ones sit to the right",
             loc="left", fontweight="bold", fontsize=11)
ax.legend(frameon=False, markerscale=2, fontsize=8)
for a in axes:
    a.spines[["top", "right"]].set_visible(False)
    a.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "rfm_segments.png", dpi=120)
plt.close(fig)
print("\nSaved chart to:", OUT / "rfm_segments.png")
