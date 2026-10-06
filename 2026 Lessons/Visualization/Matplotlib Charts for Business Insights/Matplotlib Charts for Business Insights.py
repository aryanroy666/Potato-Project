"""
Potato Project Topic: Visualization
Matplotlib Charts for Business Insights

A chart should answer a business question, not just display numbers.
This script builds four charts, each matched to a question:

    1. Line chart      -> "How is revenue changing over time?"
    2. Bar chart       -> "Which category earns the most?"
    3. Histogram       -> "What does a typical order look like?"
    4. Scatter plot    -> "Does discounting actually drive more sales?"

Every chart title states the INSIGHT (calculated from the data), not just the
topic. Charts are saved into a "charts" folder next to this script.

Run it with:  python "Matplotlib Charts for Business Insights.py"
Requires:     numpy, pandas, matplotlib
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to files only, so it also runs on servers
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "charts"
OUT.mkdir(exist_ok=True)

# A small, consistent style: light grid, no top/right borders, readable fonts.
plt.rcParams.update({
    "figure.dpi": 120,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.labelsize": 10,
})
HIGHLIGHT = "#E4572E"   # one strong colour for what matters
MUTED = "#B8C4CE"       # grey-blue for everything else
BASE = "#2E86AB"        # neutral main colour

# ---------------------------------------------------------------------
# STEP 0: Create a sample retail dataset (12 months of orders)
# ---------------------------------------------------------------------
rng = np.random.default_rng(42)
n = 600
orders = pd.DataFrame({
    "order_date": pd.to_datetime("2025-10-01")
                  + pd.to_timedelta(rng.integers(0, 365, n), unit="D"),
    "category": rng.choice(["Electronics", "Furniture", "Clothing", "Books"],
                           n, p=[0.30, 0.20, 0.35, 0.15]),
    "discount_pct": rng.choice([0, 5, 10, 15, 20, 25, 30], n),
})
base_value = orders["category"].map(
    {"Electronics": 9000, "Furniture": 6000, "Clothing": 1800, "Books": 600})
# Real-world pattern: discounts slightly lift the units bought
orders["quantity"] = np.clip(
    rng.poisson(1.2 + orders["discount_pct"] / 25), 1, None)
orders["revenue"] = (base_value * rng.lognormal(0, 0.25, n)
                     * (1 - orders["discount_pct"] / 100)
                     * orders["quantity"]).round(0)
orders["month"] = orders["order_date"].dt.to_period("M")

# ---------------------------------------------------------------------
# CHART 1: Line chart for a trend over time
# ---------------------------------------------------------------------
# Use a line when the x-axis is ORDERED (time). The line tells the viewer
# "these points are connected in sequence".
monthly = orders.groupby("month")["revenue"].sum()
best_month = monthly.idxmax()
labels = [m.strftime("%b %y") for m in monthly.index]

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(labels, monthly.values / 1000, color=BASE, marker="o", linewidth=2.2)
peak_x = list(monthly.index).index(best_month)
ax.scatter(peak_x, monthly.max() / 1000, color=HIGHLIGHT, s=90, zorder=5)
ax.annotate(f"Peak: {best_month.strftime('%b %Y')}\nRs. {monthly.max() / 1000:,.0f}k",
            xy=(peak_x, monthly.max() / 1000), xytext=(10, 12),
            textcoords="offset points", color=HIGHLIGHT, fontweight="bold")
ax.set_title(f"Revenue peaked in {best_month.strftime('%B %Y')}")
ax.set_ylabel("Revenue (Rs. thousands)")
ax.tick_params(axis="x", rotation=45)
fig.tight_layout()
fig.savefig(OUT / "1_monthly_revenue_trend.png")
plt.close(fig)

# ---------------------------------------------------------------------
# CHART 2: Horizontal bar chart for comparing categories
# ---------------------------------------------------------------------
# Use bars to compare categories. Sort them so the ranking is obvious, and
# highlight only the winner so the eye goes there first.
cat_rev = orders.groupby("category")["revenue"].sum().sort_values()
share = cat_rev / cat_rev.sum() * 100
top_cat = cat_rev.idxmax()
colors = [HIGHLIGHT if c == top_cat else MUTED for c in cat_rev.index]

fig, ax = plt.subplots(figsize=(9, 4))
bars = ax.barh(cat_rev.index, cat_rev.values / 1e5, color=colors)
for bar, pct in zip(bars, share[cat_rev.index]):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
            f"{bar.get_width():.1f}L  ({pct:.0f}%)", va="center", fontsize=9)
ax.set_title(f"{top_cat} brings in {share[top_cat]:.0f}% of total revenue")
ax.set_xlabel("Revenue (Rs. lakhs)")
ax.grid(axis="y", visible=False)
ax.set_xlim(0, cat_rev.max() / 1e5 * 1.25)
fig.tight_layout()
fig.savefig(OUT / "2_revenue_by_category.png")
plt.close(fig)

# ---------------------------------------------------------------------
# CHART 3: Histogram for a distribution
# ---------------------------------------------------------------------
# Use a histogram to see the SHAPE of a single numeric column. Order values
# are usually right-skewed (many small orders, a few huge ones), so the
# median is a better "typical" value than the mean.
mean_v, median_v = orders["revenue"].mean(), orders["revenue"].median()

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.hist(orders["revenue"].clip(upper=orders["revenue"].quantile(0.99)),
        bins=35, color=BASE, edgecolor="white")
ax.axvline(median_v, color=HIGHLIGHT, linewidth=2, label=f"Median: Rs. {median_v:,.0f}")
ax.axvline(mean_v, color="black", linestyle="--", linewidth=1.5,
           label=f"Mean: Rs. {mean_v:,.0f}")
ax.legend(frameon=False)
ax.set_title("A few large orders pull the average above the typical order")
ax.set_xlabel("Order value (Rs., top 1% capped for readability)")
ax.set_ylabel("Number of orders")
fig.tight_layout()
fig.savefig(OUT / "3_order_value_distribution.png")
plt.close(fig)

# ---------------------------------------------------------------------
# CHART 4: Scatter plot for a relationship between two numbers
# ---------------------------------------------------------------------
# Use a scatter plot to check if two numeric variables move together.
# We add a trend line and report the correlation, but remember:
# correlation shows a relationship, NOT that one causes the other.
disc = orders.groupby("discount_pct").agg(
    avg_units=("quantity", "mean"), orders=("quantity", "size")).reset_index()
corr = orders["discount_pct"].corr(orders["quantity"])
slope, intercept = np.polyfit(disc["discount_pct"], disc["avg_units"], 1)

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.scatter(disc["discount_pct"], disc["avg_units"],
           s=disc["orders"] * 2.2, color=BASE, alpha=0.8, edgecolor="white")
xs = np.array([0, 30])
ax.plot(xs, slope * xs + intercept, color=HIGHLIGHT, linewidth=2, linestyle="--")
ax.set_title("Bigger discounts go with more units per order")
ax.set_xlabel("Discount (%)")
ax.set_ylabel("Average units per order")
ax.text(0.02, 0.95, f"Correlation (all orders): {corr:.2f}\nBubble size = number of orders",
        transform=ax.transAxes, va="top", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "4_discount_vs_units.png")
plt.close(fig)

# ---------------------------------------------------------------------
# BONUS: all four as one dashboard-style image
# ---------------------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(14, 8))
axes[0, 0].plot(labels, monthly.values / 1000, color=BASE, marker="o")
axes[0, 0].set_title("Monthly revenue (Rs. thousands)")
axes[0, 0].tick_params(axis="x", rotation=45)
axes[0, 1].barh(cat_rev.index, cat_rev.values / 1e5, color=colors)
axes[0, 1].set_title("Revenue by category (Rs. lakhs)")
axes[0, 1].grid(axis="y", visible=False)
axes[1, 0].hist(orders["revenue"].clip(upper=orders["revenue"].quantile(0.99)),
                bins=35, color=BASE, edgecolor="white")
axes[1, 0].axvline(median_v, color=HIGHLIGHT, linewidth=2)
axes[1, 0].set_title("Order value distribution")
axes[1, 1].scatter(disc["discount_pct"], disc["avg_units"],
                   s=disc["orders"] * 2.2, color=BASE, alpha=0.8, edgecolor="white")
axes[1, 1].plot(xs, slope * xs + intercept, color=HIGHLIGHT, linestyle="--")
axes[1, 1].set_title("Discount vs units per order")
fig.suptitle("Retail Sales Overview", fontsize=16, fontweight="bold", x=0.02, ha="left")
fig.tight_layout()
fig.savefig(OUT / "5_dashboard_overview.png")
plt.close(fig)

print("Saved charts to:", OUT)
for f in sorted(OUT.glob("*.png")):
    print(" -", f.name)
print(f"\nKey numbers: peak month = {best_month}, top category = {top_cat} "
      f"({share[top_cat]:.0f}%), median order = Rs. {median_v:,.0f}, "
      f"mean order = Rs. {mean_v:,.0f}, correlation = {corr:.2f}")
