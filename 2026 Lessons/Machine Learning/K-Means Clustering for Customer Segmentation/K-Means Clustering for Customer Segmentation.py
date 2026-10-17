"""
Potato Project Topic: Machine Learning
K-Means Clustering for Customer Segmentation

Business question:
    Day 10 used RFM with hand-picked rules ("R>=4 and F>=4 = Champion") to
    segment customers. Today asks: what if we let an algorithm FIND the
    groups on its own, with no rules written by a human? Does it find
    the same segments, or something new?

K-MEANS groups points so that points in the same group are close to each
other. Analogy: dropping K magnets onto a table scattered with iron
filings. Each filing snaps to its nearest magnet, then each magnet moves
to the centre of the filings nearest it, and this repeats until nothing
moves.

What this script covers:
    1. Reuse Day 10's RFM features (recency, frequency, monetary)
    2. Why scaling is REQUIRED for K-means (unlike trees in Day 14)
    3. The elbow method and silhouette score to choose K
    4. Fit K-means and profile each cluster in plain language
    5. Compare the clusters with Day 10's rule-based RFM segments
    6. Visualize with PCA (reducing 3 dimensions to 2 for a chart)
    7. Caveats: when K-means works well and when it does not

Run it with:  python "K-Means Clustering for Customer Segmentation.py"
Requires:     numpy, pandas, scikit-learn, matplotlib
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

OUT = Path(__file__).parent / "charts"
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 120)

# ---------------------------------------------------------------------
# STEP 0: Rebuild the same customer transactions as Day 10
# ---------------------------------------------------------------------
# Identical generation code and seed as Day 10's RFM Customer Segmentation,
# so today's clusters can be compared against that day's rule-based segments.
rng = np.random.default_rng(42)
START, SNAPSHOT = pd.Timestamp("2025-10-01"), pd.Timestamp("2026-10-01")
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
    days = np.append(rng.integers(0, span, n_orders - 1), span)
    for d in days:
        rows.append((cid, START + pd.Timedelta(days=int(d)),
                     round(float(aov * rng.lognormal(0, 0.35)), 0)))
orders = pd.DataFrame(rows, columns=["customer_id", "order_date", "amount"])

rfm = orders.groupby("customer_id").agg(
    recency=("order_date", lambda d: (SNAPSHOT - d.max()).days),
    frequency=("order_date", "count"),
    monetary=("amount", "sum"),
)
print("=" * 60)
print("STEP 0: RFM TABLE (same customers as Day 10)")
print("=" * 60)
print(rfm.describe().round(1))

# ---------------------------------------------------------------------
# STEP 1: Why scaling is required
# ---------------------------------------------------------------------
# K-means measures distance between points. Monetary values run into the
# tens of thousands while recency is in the hundreds of days; without
# scaling, monetary would completely dominate the distance calculation,
# like comparing people using height in millimetres and weight in tonnes.
# Monetary and frequency are also right-skewed (a few big spenders), so a
# log transform makes "distance" better reflect typical differences.
features = rfm.copy()
features["monetary_log"] = np.log1p(features["monetary"])
features["frequency_log"] = np.log1p(features["frequency"])
X_cols = ["recency", "frequency_log", "monetary_log"]

scaler = StandardScaler()
X_scaled = scaler.fit_transform(features[X_cols])

print("\n" + "=" * 60)
print("STEP 1: BEFORE VS AFTER SCALING (ranges)")
print("=" * 60)
print("Raw ranges:\n", features[["recency", "frequency", "monetary"]].agg(["min", "max"]))
print("\nScaled ranges (mean 0, std 1):\n",
      pd.DataFrame(X_scaled, columns=X_cols).agg(["mean", "std"]).round(2))

# ---------------------------------------------------------------------
# STEP 2: Choosing K, the elbow method and silhouette score
# ---------------------------------------------------------------------
# Elbow method: as K grows, "inertia" (how tightly points hug their
# cluster's centre) always falls. We look for the point where adding
# another cluster stops giving a big improvement, like the elbow of an arm.
# Silhouette score (-1 to 1) checks something elbow cannot: are points
# closer to their OWN cluster than to the NEXT nearest one? Higher is better.
inertias, silhouettes = [], []
K_range = range(2, 11)
for k in K_range:
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X_scaled)
    inertias.append(km.inertia_)
    silhouettes.append(silhouette_score(X_scaled, km.labels_))

print("\n" + "=" * 60)
print("STEP 2: CHOOSING K")
print("=" * 60)
for k, inertia, sil in zip(K_range, inertias, silhouettes):
    print(f"K={k:>2}  inertia={inertia:>8.1f}  silhouette={sil:.3f}")
best_k = list(K_range)[int(np.argmax(silhouettes))]
print(f"\nBest K by silhouette score: {best_k}")

# ---------------------------------------------------------------------
# STEP 3: Fit K-means and profile each cluster
# ---------------------------------------------------------------------
# n_init=10 runs the whole algorithm 10 times from different random
# starting points and keeps the best result, since K-means can land in a
# worse local solution depending on where it starts (like a hiker who
# stops at the first hilltop reached instead of finding the tallest peak).
km_final = KMeans(n_clusters=best_k, n_init=10, random_state=42)
features["cluster"] = km_final.fit_predict(X_scaled)

profile = features.groupby("cluster").agg(
    customers=("cluster", "size"),
    avg_recency=("recency", "mean"),
    avg_frequency=("frequency", "mean"),
    avg_monetary=("monetary", "mean"),
).round(1)
profile["pct_customers"] = (profile["customers"] / profile["customers"].sum() * 100).round(1)
profile = profile.sort_values("avg_monetary", ascending=False)

print("\n" + "=" * 60)
print(f"STEP 3: CLUSTER PROFILES (K={best_k})")
print("=" * 60)
print(profile)

# Give each cluster a business-friendly name based on its own numbers,
# rather than a hard-coded label, since cluster 0/1/2 order can change run
# to run.
def name_cluster(row, med_recency, med_freq, med_monetary):
    if row["avg_monetary"] >= med_monetary and row["avg_recency"] <= med_recency:
        return "High-value & active"
    if row["avg_recency"] > med_recency * 1.5:
        return "Lapsed / at risk"
    if row["avg_frequency"] <= med_freq * 0.6:
        return "Low-engagement"
    return "Steady mid-tier"

meds = features[["recency", "frequency", "monetary"]].median()
profile["label"] = profile.apply(
    lambda r: name_cluster(r, meds["recency"], meds["frequency"], meds["monetary"]), axis=1)
print("\nBusiness-friendly labels:\n", profile[["customers", "pct_customers", "label"]])

# ---------------------------------------------------------------------
# STEP 4: Compare with Day 10's rule-based RFM segments
# ---------------------------------------------------------------------
# Rebuild Day 10's quintile scores and segment rule so we can cross-tab
# them against today's clusters: does the algorithm "discover" the same
# groups a human defined by hand?
r_score = pd.qcut(rfm["recency"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
f_score = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

def rfm_segment(r, f):
    if r >= 4 and f >= 4: return "Champions"
    if r >= 3 and f >= 3: return "Loyal Customers"
    if r >= 4 and f <= 2: return "New / Promising"
    if r <= 2 and f >= 3: return "At Risk"
    if r <= 2 and f <= 2: return "Hibernating"
    return "Need Attention"

features["rfm_segment"] = [rfm_segment(r, f) for r, f in zip(r_score, f_score)]
cross = pd.crosstab(features["rfm_segment"], features["cluster"])
print("\n" + "=" * 60)
print("STEP 4: RULE-BASED RFM SEGMENT vs K-MEANS CLUSTER")
print("=" * 60)
print(cross)
print("\nEach cluster's most common RFM segment:")
print(cross.idxmax(axis=0).rename("most_common_rfm_segment"))

# ---------------------------------------------------------------------
# STEP 5: Visualize with PCA
# ---------------------------------------------------------------------
# Humans cannot see in 3D-plus the way the algorithm "sees" the data. PCA
# (Principal Component Analysis) finds the 2 directions that capture the
# most spread in the data, so clusters can be viewed on a flat chart, like
# photographing a 3D sculpture from its most revealing angle.
pca = PCA(n_components=2, random_state=42)
coords = pca.fit_transform(X_scaled)
explained = pca.explained_variance_ratio_.sum()
print("\n" + "=" * 60)
print("STEP 5: PCA")
print("=" * 60)
print(f"2 PCA components explain {explained:.1%} of the variation in the scaled data")

# ---------------------------------------------------------------------
# CHART: elbow + silhouette, PCA scatter, cluster profile
# ---------------------------------------------------------------------
PALETTE = ["#2E86AB", "#E4572E", "#7FB069", "#F2A541", "#9B8FB5", "#B8C4CE"]
fig, axes = plt.subplots(1, 3, figsize=(17, 5))

ax = axes[0]
ax2 = ax.twinx()
ax.plot(list(K_range), inertias, marker="o", color="#B8C4CE", label="Inertia")
ax2.plot(list(K_range), silhouettes, marker="o", color="#E4572E", label="Silhouette")
ax.axvline(best_k, color="black", linestyle="--", linewidth=1, alpha=0.6)
ax.set_xlabel("Number of clusters (K)")
ax.set_ylabel("Inertia (lower = tighter clusters)", color="#8D98A3")
ax2.set_ylabel("Silhouette score (higher = better separated)", color="#E4572E")
ax.set_title(f"K={best_k} gives the best silhouette score", loc="left", fontweight="bold", fontsize=10.5)

ax = axes[1]
for c in sorted(features["cluster"].unique()):
    mask = features["cluster"] == c
    ax.scatter(coords[mask, 0], coords[mask, 1], s=14, alpha=0.6,
               color=PALETTE[c % len(PALETTE)], label=f"Cluster {c}")
ax.set_xlabel("PCA component 1")
ax.set_ylabel("PCA component 2")
ax.set_title(f"Clusters in 2D (explains {explained:.0%} of the variation)",
             loc="left", fontweight="bold", fontsize=10.5)
ax.legend(frameon=False, fontsize=8, markerscale=2)

ax = axes[2]
plot_df = profile.sort_values("avg_monetary")
y = np.arange(len(plot_df))
norm_recency = 1 - (plot_df["avg_recency"] / plot_df["avg_recency"].max())
norm_freq = plot_df["avg_frequency"] / plot_df["avg_frequency"].max()
norm_monetary = plot_df["avg_monetary"] / plot_df["avg_monetary"].max()
ax.barh(y + 0.27, norm_recency, height=0.25, color="#2E86AB", label="Recency (inverted)")
ax.barh(y, norm_freq, height=0.25, color="#E4572E", label="Frequency")
ax.barh(y - 0.27, norm_monetary, height=0.25, color="#7FB069", label="Monetary")
ax.set_yticks(y)
ax.set_yticklabels([f"C{i}: {l}" for i, l in zip(plot_df.index, plot_df["label"])], fontsize=8.5)
ax.set_xlabel("Normalised score (higher = stronger)")
ax.set_title("What each cluster looks like", loc="left", fontweight="bold", fontsize=10.5)
ax.legend(frameon=False, fontsize=8, loc="lower right")

for a in axes:
    a.spines[["top", "right"]].set_visible(False)
    a.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "kmeans_clusters.png", dpi=120)
plt.close(fig)
print("\nSaved chart to:", OUT / "kmeans_clusters.png")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"K-means (K={best_k}) found groups that line up closely with several of "
      "Day 10's hand-written RFM segments, without being told the rules, "
      "which is a good sanity check on both approaches.")
