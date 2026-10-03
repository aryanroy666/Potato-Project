"""
Potato Project Topic: Statistics
A/B Testing and Hypothesis Testing

Scenario:
    An e-commerce site tests a new "Buy Now" button (Variant B) against the
    current one (Control A). Did the new button really improve the conversion
    rate, or is the difference just luck?

What this script covers:
    1. Setting up the hypotheses
    2. Two-proportion z-test (conversion rate)   -> done by hand AND with scipy
    3. Confidence interval for the difference
    4. Welch's t-test (a continuous metric: revenue per user)
    5. Sample size planning (power analysis)
    6. Why "peeking" at results early is dangerous (simulation)

Run it with:  python "AB Testing and Hypothesis Testing.py"
Requires:     numpy, scipy
"""

import numpy as np
from scipy import stats

rng = np.random.default_rng(42)
ALPHA = 0.05  # significance level: we accept a 5% risk of a false alarm

# ---------------------------------------------------------------------
# STEP 0: Simulate the experiment data
# ---------------------------------------------------------------------
# In real life this data comes from your tracking tool. We simulate it so the
# script is self-contained. True conversion: A = 10%, B = 12%.
n_a, n_b = 5000, 5000
conv_a = rng.binomial(1, 0.10, n_a)   # 1 = user bought, 0 = did not
conv_b = rng.binomial(1, 0.12, n_b)

# ---------------------------------------------------------------------
# STEP 1: State the hypotheses BEFORE looking at results
# ---------------------------------------------------------------------
# Analogy: a court trial. The null hypothesis is "innocent until proven guilty".
#   H0 (null):        the new button has NO effect  (p_B = p_A)
#   H1 (alternative): the new button changes conversion (p_B != p_A)
print("=" * 60)
print("STEP 1: HYPOTHESES")
print("=" * 60)
print("H0: conversion rate of B equals conversion rate of A")
print("H1: conversion rate of B differs from A")
print(f"Significance level (alpha): {ALPHA}")

# ---------------------------------------------------------------------
# STEP 2: Two-proportion z-test
# ---------------------------------------------------------------------
x_a, x_b = conv_a.sum(), conv_b.sum()
p_a, p_b = x_a / n_a, x_b / n_b

print("\n" + "=" * 60)
print("STEP 2: TWO-PROPORTION Z-TEST")
print("=" * 60)
print(f"Control A: {x_a} / {n_a} = {p_a:.4f}")
print(f"Variant B: {x_b} / {n_b} = {p_b:.4f}")
print(f"Observed lift: {(p_b - p_a):.4f} ({(p_b - p_a) / p_a * 100:.1f}% relative)")

# Pooled proportion: if H0 is true, both groups share ONE true rate, so we
# combine them to estimate it.
p_pool = (x_a + x_b) / (n_a + n_b)
se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))

# z-score = how many standard errors the observed difference is from zero.
z = (p_b - p_a) / se_pool

# p-value = probability of seeing a difference at least this extreme IF H0 were
# true. Two-sided, so we look at both tails.
p_value = 2 * (1 - stats.norm.cdf(abs(z)))

print(f"\nz-score: {z:.3f}")
print(f"p-value: {p_value:.5f}")
if p_value < ALPHA:
    print("Decision: REJECT H0. The difference is statistically significant.")
else:
    print("Decision: FAIL TO REJECT H0. Not enough evidence of a real difference.")

# Cross-check with the chi-square test (equivalent for a 2x2 table).
table = np.array([[x_a, n_a - x_a], [x_b, n_b - x_b]])
chi2, p_chi, _, _ = stats.chi2_contingency(table, correction=False)
print(f"\nCross-check with chi-square test: p-value = {p_chi:.5f} (should match)")

# ---------------------------------------------------------------------
# STEP 3: Confidence interval for the difference
# ---------------------------------------------------------------------
# A p-value says IF there is an effect; a confidence interval says HOW BIG it
# could be. Stakeholders care far more about the second.
# Here we use the unpooled standard error (no assumption that H0 is true).
se_diff = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
z_crit = stats.norm.ppf(1 - ALPHA / 2)
diff = p_b - p_a
ci_low, ci_high = diff - z_crit * se_diff, diff + z_crit * se_diff

print("\n" + "=" * 60)
print("STEP 3: 95% CONFIDENCE INTERVAL FOR THE DIFFERENCE")
print("=" * 60)
print(f"Difference in conversion rate: {diff:.4f}")
print(f"95% CI: [{ci_low:.4f}, {ci_high:.4f}]")
print("If this interval does not contain 0, it agrees with a significant result.")

# ---------------------------------------------------------------------
# STEP 4: Welch's t-test for a continuous metric (revenue per user)
# ---------------------------------------------------------------------
# Use a t-test when the metric is a number (revenue, time on site), and a
# z-test / chi-square when the metric is a yes/no (converted or not).
# Welch's version does NOT assume both groups have equal variance, which is
# the safer default in practice.
rev_a = rng.normal(loc=50, scale=20, size=2000)
rev_b = rng.normal(loc=53, scale=25, size=2000)
t_stat, p_t = stats.ttest_ind(rev_b, rev_a, equal_var=False)

print("\n" + "=" * 60)
print("STEP 4: WELCH'S T-TEST (REVENUE PER USER)")
print("=" * 60)
print(f"Mean revenue A: {rev_a.mean():.2f}")
print(f"Mean revenue B: {rev_b.mean():.2f}")
print(f"t-statistic: {t_stat:.3f}, p-value: {p_t:.5f}")

# Effect size (Cohen's d): how big is the difference in standard-deviation units?
# Significance says "is it real"; effect size says "does it matter".
pooled_sd = np.sqrt((rev_a.var(ddof=1) + rev_b.var(ddof=1)) / 2)
cohens_d = (rev_b.mean() - rev_a.mean()) / pooled_sd
print(f"Cohen's d (effect size): {cohens_d:.3f}  (0.2 small, 0.5 medium, 0.8 large)")

# ---------------------------------------------------------------------
# STEP 5: Sample size planning (BEFORE running the test)
# ---------------------------------------------------------------------
# Analogy: you can't judge a coin's fairness from 10 flips. The smaller the
# improvement you want to detect, the more users you need.
def sample_size_per_group(p_baseline, min_lift, alpha=0.05, power=0.80):
    """Users needed in EACH group to detect an absolute lift of `min_lift`."""
    p_new = p_baseline + min_lift
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    variance = p_baseline * (1 - p_baseline) + p_new * (1 - p_new)
    return int(np.ceil(((z_alpha + z_power) ** 2 * variance) / (min_lift ** 2)))

print("\n" + "=" * 60)
print("STEP 5: SAMPLE SIZE PLANNING (baseline 10%, power 80%)")
print("=" * 60)
for lift in [0.04, 0.02, 0.01]:
    print(f"To detect +{lift * 100:.0f} percentage points: "
          f"{sample_size_per_group(0.10, lift):,} users per group")

# ---------------------------------------------------------------------
# STEP 6: The peeking problem (simulation)
# ---------------------------------------------------------------------
# Run 1,000 A/A tests where BOTH groups are identical (no real difference).
# A correct test should give a false alarm only 5% of the time.
# But if you check the p-value every day and stop at the first p < 0.05,
# the false alarm rate explodes. Like re-rolling a die until you get a six.
def false_positive_rate(peek, n_sims=1000, n_total=2000, n_looks=10):
    false_alarms = 0
    sim_rng = np.random.default_rng(7)
    checkpoints = np.linspace(n_total // n_looks, n_total, n_looks, dtype=int)
    for _ in range(n_sims):
        a = sim_rng.binomial(1, 0.10, n_total)
        b = sim_rng.binomial(1, 0.10, n_total)  # same true rate: no real effect
        looks = checkpoints if peek else [n_total]
        for n in looks:
            xa, xb = a[:n].sum(), b[:n].sum()
            pp = (xa + xb) / (2 * n)
            se = np.sqrt(pp * (1 - pp) * 2 / n)
            if se > 0 and 2 * (1 - stats.norm.cdf(abs((xb - xa) / n / se))) < ALPHA:
                false_alarms += 1
                break
    return false_alarms / n_sims

print("\n" + "=" * 60)
print("STEP 6: THE PEEKING PROBLEM (A/A tests, no real difference)")
print("=" * 60)
print(f"False alarm rate, test once at the end: {false_positive_rate(False):.1%}")
print(f"False alarm rate, peek 10 times:        {false_positive_rate(True):.1%}")
print("Lesson: decide the sample size in advance and do not stop early.")

# ---------------------------------------------------------------------
# STEP 7: Final business summary
# ---------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 7: BUSINESS SUMMARY")
print("=" * 60)
print(f"Variant B lifted conversion from {p_a:.2%} to {p_b:.2%} "
      f"(p = {p_value:.4f}). The plausible true lift is between "
      f"{ci_low * 100:.2f} and {ci_high * 100:.2f} percentage points.")
print("Recommendation: roll out B if the lower end of the interval is still "
      "worth the cost of the change.")
