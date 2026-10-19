"""
Potato Project Topic: Customer Analytics
Market Basket Analysis (Association Rules)

Business question:
    "Customers who bought X also bought Y." How do we find rules like that
    from raw transaction data, and how do we tell a USEFUL pattern from a
    coincidence?

Market basket analysis looks at what items are bought TOGETHER in the same
transaction, and surfaces rules such as "Bread -> Butter" that can drive
product placement, bundle deals and recommendation engines (this is the
same family of idea behind "customers who bought this also bought...").

What this script covers:
    1. Build a sample grocery transactions dataset (one row per basket)
    2. One-hot encode transactions into a basket matrix
    3. The Apriori algorithm: finding frequent itemsets
    4. Generate association rules: support, confidence, lift
    5. Interpret the top rules in plain business language
    6. Why lift matters more than confidence alone (a worked trap)
    7. A simple product-placement recommendation from the rules

Run it with:  python "Market Basket Analysis.py"
Requires:     numpy, pandas, mlxtend, matplotlib
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder

OUT = Path(__file__).parent / "charts"
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 130)
pd.set_option("display.max_columns", 20)

# ---------------------------------------------------------------------
# STEP 0: Create a sample grocery transactions dataset
# ---------------------------------------------------------------------
# Built around a few HIDDEN real-world patterns so we can check whether the
# algorithm finds them:
#   Bread + Butter almost always together | Tea + Biscuits a strong pair
#   Diapers + Baby Wipes together | Milk is bought by almost everyone
#   (so Milk looks "linked" to everything by coincidence, not by real pull)
rng = np.random.default_rng(42)
catalog = ["Bread", "Butter", "Milk", "Eggs", "Tea", "Biscuits", "Coffee",
          "Diapers", "Baby Wipes", "Rice", "Lentils", "Soap", "Shampoo", "Chocolate"]

n_baskets = 2000
baskets = []
for _ in range(n_baskets):
    items = set()
    if rng.random() < 0.55:                       # Milk: bought by over half of everyone
        items.add("Milk")
    if rng.random() < 0.35:                        # Bread + Butter pattern
        items.add("Bread")
        if rng.random() < 0.80:
            items.add("Butter")
    if rng.random() < 0.25:                         # Tea + Biscuits pattern
        items.add("Tea")
        if rng.random() < 0.65:
            items.add("Biscuits")
    if rng.random() < 0.10:                          # Diapers + Wipes pattern
        items.add("Diapers")
        if rng.random() < 0.75:
            items.add("Baby Wipes")
    # background noise: everyone also grabs a few random unrelated items
    n_extra = rng.integers(0, 4)
    extra = rng.choice([c for c in catalog if c not in items], size=min(n_extra, len(catalog)),
                       replace=False)
    items.update(str(e) for e in extra)
    if items:
        baskets.append(sorted(items))

print("=" * 60)
print("STEP 0: TRANSACTIONS")
print("=" * 60)
print(f"{len(baskets):,} baskets | example baskets:")
for b in baskets[:3]:
    print(" ", b)

# ---------------------------------------------------------------------
# STEP 1: One-hot encode into a basket matrix
# ---------------------------------------------------------------------
# Each row = one transaction, each column = one product, True/False = bought
# or not. This "wide" shape is what the Apriori algorithm expects, similar
# to a pivot table (Day 5) with items as columns.
te = TransactionEncoder()
te_array = te.fit(baskets).transform(baskets)
basket_df = pd.DataFrame(te_array, columns=te.columns_)
print("\n" + "=" * 60)
print("STEP 1: BASKET MATRIX (first 5 rows, a few columns)")
print("=" * 60)
print(basket_df[["Bread", "Butter", "Milk", "Tea", "Biscuits"]].head())

# ---------------------------------------------------------------------
# STEP 2: Apriori, finding frequent itemsets
# ---------------------------------------------------------------------
# SUPPORT of an itemset = the share of ALL baskets that contain it.
# Analogy: of every basket that left the store, what fraction had this
# exact combination inside? Apriori's key shortcut: if an itemset is rare,
# every LARGER itemset built from it must be at least as rare (you cannot
# buy Bread+Butter+Jam more often than you buy Bread+Butter alone). This
# lets it skip checking huge numbers of impossible combinations.
min_support = 0.03
frequent = apriori(basket_df, min_support=min_support, use_colnames=True)
frequent["length"] = frequent["itemsets"].apply(len)
print("\n" + "=" * 60)
print(f"STEP 2: FREQUENT ITEMSETS (min support = {min_support:.0%})")
print("=" * 60)
print(f"Found {len(frequent)} itemsets. Top 10 by support:")
print(frequent.sort_values("support", ascending=False).head(10).to_string(index=False))

# ---------------------------------------------------------------------
# STEP 3: Generate association rules
# ---------------------------------------------------------------------
# A rule "A -> B" has three key numbers:
#   SUPPORT    : how often A and B appear together, out of ALL baskets
#   CONFIDENCE : of the baskets with A, what % also had B?
#                (like a conditional probability: P(B | A))
#   LIFT       : how much MORE likely B is when A is present, versus B's
#                normal rate on its own. Lift = 1 means no real connection;
#                above 1 means A genuinely pulls B in; below 1 means A
#                pushes B away.
all_rules = association_rules(frequent, metric="lift", min_threshold=1.0, num_itemsets=len(frequent))
all_rules = all_rules[all_rules["confidence"] >= 0.3].sort_values("lift", ascending=False)
all_rules["ant_len"] = all_rules["antecedents"].apply(len)
all_rules["con_len"] = all_rules["consequents"].apply(len)
all_rules["antecedents"] = all_rules["antecedents"].apply(lambda s: ", ".join(sorted(s)))
all_rules["consequents"] = all_rules["consequents"].apply(lambda s: ", ".join(sorted(s)))

# Simple 1-item -> 1-item rules are the easiest to explain to a business
# stakeholder ("if they buy X, put Y nearby"), so highlight those separately
# from multi-item combinations, which can show inflated lift purely because
# they are rare (small support makes lift noisier and less reliable).
rules = all_rules[(all_rules["ant_len"] == 1) & (all_rules["con_len"] == 1)].copy()

print("\n" + "=" * 60)
print("STEP 3: SIMPLE ONE-TO-ONE RULES (easiest to act on), BY LIFT")
print("=" * 60)
print(rules[["antecedents", "consequents", "support", "confidence", "lift"]]
      .head(10).round(3).to_string(index=False))

print("\nTop multi-item rules also exist (more specific, rarer, noisier):")
print(all_rules[(all_rules["ant_len"] + all_rules["con_len"]) > 2]
      [["antecedents", "consequents", "support", "confidence", "lift"]]
      .head(3).round(3).to_string(index=False))

# ---------------------------------------------------------------------
# STEP 4: Interpret the top rules
# ---------------------------------------------------------------------
top = rules.iloc[0]
print("\n" + "=" * 60)
print("STEP 4: PLAIN-LANGUAGE READING OF THE TOP RULE")
print("=" * 60)
print(f"Rule: {{{top['antecedents']}}} -> {{{top['consequents']}}}")
print(f"- Support {top['support']:.1%}: these items appear together in "
      f"{top['support']:.1%} of ALL baskets.")
print(f"- Confidence {top['confidence']:.1%}: of baskets containing "
      f"'{top['antecedents']}', {top['confidence']:.1%} also contained "
      f"'{top['consequents']}'.")
print(f"- Lift {top['lift']:.2f}: a basket with '{top['antecedents']}' is "
      f"{top['lift']:.1f}x as likely to also have '{top['consequents']}' "
      "compared with a random basket.")

# ---------------------------------------------------------------------
# STEP 5: The Milk trap, why lift matters more than confidence alone
# ---------------------------------------------------------------------
# Milk is bought by over half of all baskets, so almost ANY item will show
# high confidence toward Milk purely by coincidence, not because the two
# are genuinely linked. Lift corrects for this.
milk_support = basket_df["Milk"].mean()
print("\n" + "=" * 60)
print("STEP 5: THE 'POPULAR ITEM' TRAP")
print("=" * 60)
print(f"Milk appears in {milk_support:.1%} of ALL baskets, popular on its own.")
# Compute Bread -> Milk directly (it may not clear the confidence filter
# above, since its lift near 1.0 is exactly the point being made).
milk_itemset = frequent[frequent["itemsets"] == frozenset({"Milk"})]["support"].iloc[0]
both_itemset = frequent[frequent["itemsets"] == frozenset({"Bread", "Milk"})]
bread_itemset = frequent[frequent["itemsets"] == frozenset({"Bread"})]["support"].iloc[0]
if not both_itemset.empty:
    both_support = both_itemset["support"].iloc[0]
    bread_to_milk_conf = both_support / bread_itemset
    bread_to_milk_lift = bread_to_milk_conf / milk_itemset
    print(f"Rule {{Bread}} -> {{Milk}}: confidence {bread_to_milk_conf:.1%} looks strong "
          "on its own,")
    print(f"but lift is only {bread_to_milk_lift:.2f}, close to 1.0.")
    print("That near-1.0 lift means Bread does NOT genuinely pull Milk in: "
          "people buy Milk about that often anyway, with or without Bread. "
          "High confidence alone would have been a misleading signal here.")

bb = rules[(rules["antecedents"] == "Bread") & (rules["consequents"] == "Butter")]
if not bb.empty:
    r = bb.iloc[0]
    print(f"\nCompare with {{Bread}} -> {{Butter}}: confidence {r['confidence']:.1%} "
          f"AND lift {r['lift']:.2f}. This is a real pull, not a coincidence of popularity.")

# ---------------------------------------------------------------------
# STEP 6: A simple recommendation from the rules
# ---------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 6: PRODUCT PLACEMENT RECOMMENDATIONS")
print("=" * 60)
strong_rules = rules[(rules["lift"] > 1.5) & (rules["confidence"] > 0.4)]
for _, r in strong_rules.head(5).iterrows():
    print(f"- Place '{r['consequents']}' near '{r['antecedents']}', or bundle them: "
          f"{r['confidence']:.0%} of '{r['antecedents']}' buyers also buy "
          f"'{r['consequents']}' ({r['lift']:.1f}x more likely than chance).")

# ---------------------------------------------------------------------
# CHART: support vs confidence (bubble = lift) + top rules by lift
# ---------------------------------------------------------------------
BLUE, ORANGE, GREY = "#2E86AB", "#E4572E", "#B8C4CE"
fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))

ax = axes[0]
colors = [ORANGE if l > 1.5 else BLUE for l in rules["lift"]]
sizes = (rules["lift"].clip(upper=6) * 40)
ax.scatter(rules["support"], rules["confidence"], s=sizes, alpha=0.6,
           color=colors, edgecolor="white")
ax.set_xlabel("Support (how common the full combination is)")
ax.set_ylabel("Confidence (P(consequent | antecedent))")
ax.set_title("Bubble size = lift; orange = lift above 1.5 (a real pull)",
             loc="left", fontweight="bold", fontsize=11)

ax = axes[1]
top10 = rules.head(10).iloc[::-1]
labels = [f"{a} -> {c}" for a, c in zip(top10["antecedents"], top10["consequents"])]
bar_colors = [ORANGE if l > 1.5 else BLUE for l in top10["lift"]]
ax.barh(labels, top10["lift"], color=bar_colors)
ax.axvline(1, color="black", linewidth=1, linestyle="--")
ax.set_xlabel("Lift")
ax.set_title("Top rules by lift (1.0 = no real connection)",
             loc="left", fontweight="bold", fontsize=11)

for a in axes:
    a.spines[["top", "right"]].set_visible(False)
    a.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "market_basket_rules.png", dpi=120)
plt.close(fig)
print("\nSaved chart to:", OUT / "market_basket_rules.png")
