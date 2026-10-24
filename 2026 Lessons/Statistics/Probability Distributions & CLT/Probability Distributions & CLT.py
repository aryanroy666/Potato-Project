"""
Potato Project Topic: Statistics
Probability Distributions & the Central Limit Theorem
======================================================

Three questions answered:
  1. What shape does my data follow? (fitting distributions)
  2. What is the probability of a specific outcome? (PDF, CDF, PPF)
  3. Why does the normal distribution appear EVERYWHERE? (CLT demonstration)

Analogy:
  A distribution is a rulebook that tells you how likely each possible value is.
  The CLT says: even if the original rulebook is weird and lopsided, the rulebook
  for the *average of many samples* always turns into a bell curve. This is why
  banks, doctors, and data analysts can use the same normal-distribution tools on
  almost any dataset once they have enough data.

Distributions covered:
  - Normal (Gaussian)   : symmetric bell curve, most common in nature
  - Binomial            : count of successes in N coin-flip-style trials
  - Poisson             : count of rare events in a fixed window (emails per hour)
  - Exponential         : time between Poisson events (minutes until next email)
  - Uniform             : every value in a range equally likely

Business contexts used throughout:
  - Call centre: calls per hour (Poisson), handle time (Exponential/Normal)
  - Quality control: defect rate (Binomial), measurement error (Normal)
  - E-commerce: conversion rate (Binomial), session duration (Exponential)

Run:  python probability_distributions_clt.py
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

SEED = 42
rng = np.random.default_rng(SEED)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — DISTRIBUTION OVERVIEW: PDF, CDF, KEY STATS
# ─────────────────────────────────────────────────────────────────────────────

def section1_distribution_overview():
    print("=" * 65)
    print("SECTION 1 — Distribution Key Stats")
    print("=" * 65)

    distributions = {
        "Normal(μ=170, σ=10)": stats.norm(loc=170, scale=10),
        "Binomial(n=20, p=0.3)": stats.binom(n=20, p=0.3),
        "Poisson(λ=5)": stats.poisson(mu=5),
        "Exponential(λ=0.2)": stats.expon(scale=1/0.2),   # scale = 1/rate
        "Uniform(a=0, b=60)": stats.uniform(loc=0, scale=60),
    }

    rows = []
    for name, dist in distributions.items():
        mean, var, skew, kurt = dist.stats(moments="mvsk")
        rows.append({
            "Distribution": name,
            "Mean": round(float(mean), 3),
            "Std Dev": round(float(var**0.5), 3),
            "Skewness": round(float(skew), 3),
            "Kurtosis": round(float(kurt), 3),
        })

    df = pd.DataFrame(rows).set_index("Distribution")
    print(df.to_string())
    print()
    return distributions


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — PRACTICAL PROBABILITY QUESTIONS
# ─────────────────────────────────────────────────────────────────────────────

def section2_probability_questions():
    print("=" * 65)
    print("SECTION 2 — Practical Probability Questions")
    print("=" * 65)

    # 2a. Normal: employee height
    dist = stats.norm(loc=170, scale=10)
    p_above_185 = 1 - dist.cdf(185)
    p_between = dist.cdf(180) - dist.cdf(160)
    p90_cutoff = dist.ppf(0.90)
    print("Normal(μ=170 cm, σ=10 cm) — employee heights")
    print(f"  P(height > 185 cm)        = {p_above_185:.4f}  ({p_above_185*100:.2f}%)")
    print(f"  P(160 < height < 180)     = {p_between:.4f}  ({p_between*100:.2f}%)")
    print(f"  90th percentile height    = {p90_cutoff:.2f} cm")
    print()

    # 2b. Binomial: quality control
    n, p = 20, 0.05          # 20 units, 5% defect rate
    dist_b = stats.binom(n=n, p=p)
    p_zero_defects = dist_b.pmf(0)
    p_at_most_2    = dist_b.cdf(2)
    p_at_least_3   = 1 - dist_b.cdf(2)
    print(f"Binomial(n={n}, p={p}) — defects in a batch of 20")
    print(f"  P(0 defects)              = {p_zero_defects:.4f}  ({p_zero_defects*100:.2f}%)")
    print(f"  P(≤ 2 defects)            = {p_at_most_2:.4f}  ({p_at_most_2*100:.2f}%)")
    print(f"  P(≥ 3 defects) [reject]   = {p_at_least_3:.4f}  ({p_at_least_3*100:.2f}%)")
    print()

    # 2c. Poisson: call centre
    lam = 12          # average calls per hour
    dist_p = stats.poisson(mu=lam)
    p_more_than_15 = 1 - dist_p.cdf(15)
    p_exactly_12   = dist_p.pmf(12)
    p_quiet        = dist_p.cdf(8)          # ≤ 8 calls
    print(f"Poisson(λ={lam}) — calls per hour at a call centre")
    print(f"  P(exactly 12 calls)       = {p_exactly_12:.4f}  ({p_exactly_12*100:.2f}%)")
    print(f"  P(> 15 calls) [overload]  = {p_more_than_15:.4f}  ({p_more_than_15*100:.2f}%)")
    print(f"  P(≤ 8 calls) [quiet hour] = {p_quiet:.4f}  ({p_quiet*100:.2f}%)")
    print()

    # 2d. Exponential: time between arrivals
    rate = 0.2        # 0.2 customers per minute → mean wait = 5 min
    dist_e = stats.expon(scale=1/rate)
    p_under_3_min = dist_e.cdf(3)
    p_over_10_min = 1 - dist_e.cdf(10)
    median_wait   = dist_e.ppf(0.5)
    print(f"Exponential(rate={rate}/min) — time between customer arrivals")
    print(f"  Mean wait time            = {1/rate:.1f} min")
    print(f"  P(next customer < 3 min)  = {p_under_3_min:.4f}  ({p_under_3_min*100:.2f}%)")
    print(f"  P(wait > 10 min)          = {p_over_10_min:.4f}  ({p_over_10_min*100:.2f}%)")
    print(f"  Median wait time          = {median_wait:.2f} min")
    print()

    return {
        "p_above_185": p_above_185,
        "p90_cutoff": p90_cutoff,
        "p_zero_defects": p_zero_defects,
        "p_at_least_3": p_at_least_3,
        "p_more_than_15": p_more_than_15,
        "p_under_3_min": p_under_3_min,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — CENTRAL LIMIT THEOREM DEMONSTRATION
# ─────────────────────────────────────────────────────────────────────────────

def section3_clt():
    print("=" * 65)
    print("SECTION 3 — Central Limit Theorem Demonstration")
    print("=" * 65)

    # Population: heavily RIGHT-SKEWED (exponential, λ=0.5)
    # True population mean = 1/0.5 = 2.0; std dev = 2.0
    pop_rate = 0.5
    pop_mean_true = 1 / pop_rate
    pop_std_true  = 1 / pop_rate

    population = rng.exponential(scale=1/pop_rate, size=100_000)
    pop_skew = float(stats.skew(population))

    print(f"Population: Exponential(rate={pop_rate})  [highly right-skewed]")
    print(f"  True mean          = {pop_mean_true:.4f}")
    print(f"  True std dev       = {pop_std_true:.4f}")
    print(f"  Observed mean      = {population.mean():.4f}")
    print(f"  Observed std dev   = {population.std():.4f}")
    print(f"  Observed skewness  = {pop_skew:.4f}  (0 = perfectly symmetric)")
    print()

    sample_sizes = [1, 5, 10, 30, 50, 100]
    n_simulations = 5_000

    rows = []
    sample_means_by_n = {}
    for n in sample_sizes:
        # Draw 5,000 samples of size n and compute each sample mean
        samples = rng.exponential(scale=1/pop_rate, size=(n_simulations, n))
        means = samples.mean(axis=1)
        sample_means_by_n[n] = means

        # CLT predictions
        predicted_std = pop_std_true / np.sqrt(n)
        observed_std  = means.std()
        observed_skew = float(stats.skew(means))
        sw_stat, sw_p = stats.shapiro(means[:500])   # Shapiro-Wilk on first 500

        rows.append({
            "n": n,
            "Predicted SE": round(predicted_std, 4),
            "Observed SE": round(observed_std, 4),
            "Skewness": round(observed_skew, 4),
            "Shapiro-Wilk p": f"{sw_p:.4f}",
            "Normal?": "YES ✓" if sw_p > 0.05 else "NO  ✗",
        })

    clt_df = pd.DataFrame(rows).set_index("n")
    print("Sample means of n draws from the skewed population (5,000 simulations each):")
    print(clt_df.to_string())
    print()
    print("Rule of thumb: sample means look normal once n ≥ 30.")
    print()

    return sample_means_by_n, population


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — DISTRIBUTION FITTING ON SYNTHETIC BUSINESS DATA
# ─────────────────────────────────────────────────────────────────────────────

def section4_fitting():
    print("=" * 65)
    print("SECTION 4 — Distribution Fitting (Goodness-of-Fit)")
    print("=" * 65)

    # Simulate call-handle times: real call centres see roughly log-normal shape
    handle_times = rng.lognormal(mean=np.log(5), sigma=0.6, size=1_000)

    # Try fitting three candidate distributions
    candidates = {
        "Normal":      stats.norm,
        "Exponential": stats.expon,
        "Log-normal":  stats.lognorm,
    }

    rows = []
    for name, dist_class in candidates.items():
        params = dist_class.fit(handle_times)
        ks_stat, ks_p = stats.kstest(handle_times, dist_class.cdf, args=params)
        fitted_dist = dist_class(*params)
        rows.append({
            "Distribution": name,
            "KS Statistic": round(ks_stat, 4),
            "KS p-value": f"{ks_p:.4f}",
            "Good fit?": "YES ✓" if ks_p > 0.05 else "NO  ✗",
        })

    fit_df = pd.DataFrame(rows).set_index("Distribution")
    print("Call-handle time data (synthetically log-normal, n=1,000):")
    print(f"  Mean  = {handle_times.mean():.2f} min | Median = {np.median(handle_times):.2f} min")
    print(f"  Skew  = {float(stats.skew(handle_times)):.3f} | Max = {handle_times.max():.2f} min")
    print()
    print("Kolmogorov-Smirnov goodness-of-fit test (p > 0.05 → good fit):")
    print(fit_df.to_string())
    print()
    print("Log-normal wins. The positive skew (long tail of long calls) is the tell.")
    print()

    return handle_times


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def verify(prob_results, sample_means_by_n):
    print("=" * 65)
    print("VERIFICATION")
    print("=" * 65)

    # V1: P(Z > 1.5) from first principles using the error function
    z = (185 - 170) / 10    # = 1.5
    import math
    hand = 0.5 * (1 - math.erf(z / math.sqrt(2)))
    assert abs(hand - prob_results["p_above_185"]) < 1e-9, "Normal CDF mismatch"

    # V2: 90th percentile is above the mean for a symmetric distribution
    assert prob_results["p90_cutoff"] > 170, "90th pct must exceed the mean"

    # V3: P(0 defects) = (1-p)^n
    hand_binom = (1 - 0.05) ** 20
    assert abs(hand_binom - prob_results["p_zero_defects"]) < 1e-9, "Binomial PMF mismatch"

    # V4: P(reject) = 1 - CDF(2) — complementary
    assert abs(prob_results["p_at_least_3"] - (1 - stats.binom(n=20, p=0.05).cdf(2))) < 1e-9

    # V5: CLT — SE of sample means converges to sigma/sqrt(n)
    pop_std = 1 / 0.5
    for n, means in sample_means_by_n.items():
        predicted = pop_std / np.sqrt(n)
        observed  = means.std()
        rel_err   = abs(predicted - observed) / predicted
        assert rel_err < 0.05, f"CLT SE error too large at n={n}: {rel_err:.3f}"

    # V6: Exponential memoryless property
    # P(X > 10) should equal P(X > 3) * P(X > 7)   [independence of increments]
    dist_e = stats.expon(scale=5)
    lhs = 1 - dist_e.cdf(10)
    rhs = (1 - dist_e.cdf(3)) * (1 - dist_e.cdf(7))
    assert abs(lhs - rhs) < 1e-9, "Exponential memoryless property failed"

    # V7: P(under 3 min) via 1 - e^(-rate*t)
    rate = 0.2
    hand_exp = 1 - np.exp(-rate * 3)
    assert abs(hand_exp - prob_results["p_under_3_min"]) < 1e-9, "Exponential CDF mismatch"

    print("All 7 verification checks passed.")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def save_charts(sample_means_by_n, population, handle_times):
    CHARTS = "charts"

    # Chart 1: Five distributions side by side
    fig, axes = plt.subplots(1, 5, figsize=(16, 4))
    configs = [
        ("Normal\n(μ=170, σ=10)", stats.norm(170, 10), np.linspace(135, 205, 300), False, "#1f77b4"),
        ("Binomial\n(n=20, p=0.3)", stats.binom(20, 0.3), np.arange(0, 21), True, "#ff7f0e"),
        ("Poisson\n(λ=5)", stats.poisson(5), np.arange(0, 16), True, "#2ca02c"),
        ("Exponential\n(rate=0.2)", stats.expon(scale=5), np.linspace(0, 30, 300), False, "#d62728"),
        ("Uniform\n(0–60)", stats.uniform(0, 60), np.linspace(-5, 65, 300), False, "#9467bd"),
    ]
    for ax, (title, dist, x, discrete, color) in zip(axes, configs):
        if discrete:
            ax.bar(x, dist.pmf(x), color=color, alpha=0.8, width=0.7)
            ax.set_ylabel("P(X = x)")
        else:
            ax.fill_between(x, dist.pdf(x), alpha=0.5, color=color)
            ax.plot(x, dist.pdf(x), color=color)
            ax.set_ylabel("Density")
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("x")
        ax.grid(alpha=0.3)
    fig.suptitle("Probability Distributions: PDF / PMF", fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(f"{CHARTS}/distributions_overview.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Chart 2: CLT — histograms of sample means for increasing n
    sizes_to_plot = [1, 5, 30, 100]
    fig, axes = plt.subplots(1, 4, figsize=(14, 4))
    for ax, n in zip(axes, sizes_to_plot):
        means = sample_means_by_n[n]
        ax.hist(means, bins=50, density=True, color="#1f77b4", alpha=0.7, edgecolor="white", linewidth=0.3)
        # overlay fitted normal
        m, s = means.mean(), means.std()
        x = np.linspace(m - 4*s, m + 4*s, 300)
        ax.plot(x, stats.norm(m, s).pdf(x), "r-", linewidth=1.5, label="Normal fit")
        ax.set_title(f"n = {n}", fontsize=10)
        ax.set_xlabel("Sample mean")
        ax.set_ylabel("Density")
        ax.grid(alpha=0.3)
        sk = float(stats.skew(means))
        ax.text(0.05, 0.92, f"skew={sk:.2f}", transform=ax.transAxes, fontsize=8, color="darkred")
    fig.suptitle("CLT: Sample Means from Exponential Population (5,000 simulations each)",
                 fontsize=11, y=1.02)
    fig.tight_layout()
    fig.savefig(f"{CHARTS}/clt_demonstration.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Chart 3: CDF comparison — Normal, height example
    dist_h = stats.norm(170, 10)
    x = np.linspace(135, 205, 400)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax1.plot(x, dist_h.pdf(x), "#1f77b4", linewidth=2)
    ax1.fill_between(x, dist_h.pdf(x), where=(x > 185), alpha=0.4, color="red", label="P(X > 185)")
    ax1.fill_between(x, dist_h.pdf(x), where=((x >= 160) & (x <= 180)), alpha=0.4, color="green", label="P(160<X<180)")
    ax1.axvline(185, color="red", linestyle="--", linewidth=1)
    ax1.set_xlabel("Height (cm)")
    ax1.set_ylabel("Density")
    ax1.set_title("Normal PDF: Shaded Probability Regions")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)
    ax2.plot(x, dist_h.cdf(x), "#d62728", linewidth=2)
    ax2.axhline(0.90, color="purple", linestyle="--", linewidth=1, label="90th percentile")
    ax2.axvline(dist_h.ppf(0.90), color="purple", linestyle="--", linewidth=1)
    ax2.set_xlabel("Height (cm)")
    ax2.set_ylabel("Cumulative Probability")
    ax2.set_title("Normal CDF: Cumulative Probability")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{CHARTS}/normal_pdf_cdf.png", dpi=150)
    plt.close(fig)

    # Chart 4: Distribution fitting — handle times
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(handle_times, bins=60, density=True, color="#aec7e8", edgecolor="white",
            linewidth=0.3, label="Observed data", zorder=2)
    x = np.linspace(0, handle_times.max(), 400)
    for dist_class, label, color in [
        (stats.norm, "Normal fit", "#d62728"),
        (stats.expon, "Exponential fit", "#ff7f0e"),
        (stats.lognorm, "Log-normal fit", "#2ca02c"),
    ]:
        params = dist_class.fit(handle_times)
        ax.plot(x, dist_class(*params).pdf(x), linewidth=2, label=label, color=color)
    ax.set_xlabel("Handle time (minutes)")
    ax.set_ylabel("Density")
    ax.set_title("Distribution Fitting: Call Handle Times")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{CHARTS}/distribution_fitting.png", dpi=150)
    plt.close(fig)

    print(f"Saved 4 charts to {CHARTS}/")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    pd.set_option("display.width", 200)

    section1_distribution_overview()
    prob_results = section2_probability_questions()
    sample_means_by_n, population = section3_clt()
    handle_times = section4_fitting()
    verify(prob_results, sample_means_by_n)
    save_charts(sample_means_by_n, population, handle_times)


if __name__ == "__main__":
    main()
