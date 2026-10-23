"""
Potato Project Topic: Time Series

Seasonal Decomposition and Forecast Backtesting
===============================================

Two questions answered:
  1. WHAT is in my time series?  (trend + seasonality + leftover noise)
  2. WHICH simple forecast method predicts it best?  (tested honestly on held-out months)

Analogy: monthly ice-cream sales = a slowly growing business (trend) + hot
summers and cold winters (seasonality) + random bad-weather days (noise).
Decomposition pulls those three layers apart, like separating the layers of a
cake. Backtesting then asks: "if I had used method X in the past, how wrong
would I have been?"

Methods compared (all written from scratch, no statsmodels needed):
  - Naive                : next month = last month
  - Seasonal naive       : next month = same month last year
  - Moving average (12)  : next month = average of the last 12 months
  - Simple exp. smoothing: weighted average, recent months count more
  - Seasonal naive + drift: seasonal naive shifted by the yearly growth

Run:  python seasonal_decomposition_forecasting.py
"""

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SEED = 7
NOISE_SD = 4.0  # std dev of the random noise used to build the data
PERIOD = 12  # monthly data, yearly seasonality

# The TRUE seasonal pattern used to build the data (sums to zero).
# Decomposition should recover something close to this.
TRUE_SEASONAL = np.array([-18, -22, -8, 2, 10, 20, 26, 22, 6, -2, 8, 24], dtype=float)
TRUE_SEASONAL = TRUE_SEASONAL - TRUE_SEASONAL.mean()


# ----------------------------------------------------------------------------
# 1. DATA
# ----------------------------------------------------------------------------
def generate_series(n_years: int = 6, seed: int = SEED) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2019-01-01", periods=n_years * PERIOD, freq="MS")
    t = np.arange(len(idx))
    trend = 200 + 1.5 * t                      # +1.5 units per month
    seasonal = np.tile(TRUE_SEASONAL, n_years)
    noise = rng.normal(0, NOISE_SD, len(idx))
    return pd.Series(trend + seasonal + noise, index=idx, name="sales").round(2)


# ----------------------------------------------------------------------------
# 2. CLASSICAL ADDITIVE DECOMPOSITION
# ----------------------------------------------------------------------------
def centered_moving_average(s: pd.Series, period: int = PERIOD) -> pd.Series:
    """For an even period (12) a plain rolling mean sits between two months.
    The 2 x 12 centred MA fixes that: average two adjacent 12-month means."""
    two_step = s.rolling(period).mean().rolling(2).mean()   # covers 13 months, ends weighted 0.5
    return two_step.shift(-(period // 2))                    # re-centre on the middle month


def decompose(s: pd.Series, period: int = PERIOD) -> pd.DataFrame:
    trend = centered_moving_average(s, period)
    detrended = s - trend
    month_pos = np.arange(len(s)) % period
    raw_seasonal = detrended.groupby(month_pos).mean()          # average per calendar slot
    seasonal_idx = raw_seasonal - raw_seasonal.mean()           # force to sum to zero
    seasonal = pd.Series(seasonal_idx.values[month_pos], index=s.index)
    resid = s - trend - seasonal
    return pd.DataFrame({"observed": s, "trend": trend, "seasonal": seasonal, "resid": resid})


# ----------------------------------------------------------------------------
# 3. FORECASTING METHODS (each returns h future values)
# ----------------------------------------------------------------------------
def f_naive(train: pd.Series, h: int) -> np.ndarray:
    return np.repeat(train.iloc[-1], h)


def f_seasonal_naive(train: pd.Series, h: int, period: int = PERIOD) -> np.ndarray:
    last_season = train.iloc[-period:].values
    return np.array([last_season[i % period] for i in range(h)])


def f_moving_average(train: pd.Series, h: int, window: int = 12) -> np.ndarray:
    return np.repeat(train.iloc[-window:].mean(), h)


def f_ses(train: pd.Series, h: int, alpha: float = 0.3) -> np.ndarray:
    level = train.iloc[0]
    for y in train.iloc[1:]:
        level = alpha * y + (1 - alpha) * level
    return np.repeat(level, h)


def f_seasonal_naive_drift(train: pd.Series, h: int, period: int = PERIOD) -> np.ndarray:
    base = f_seasonal_naive(train, h, period)
    yearly_growth = train.iloc[-1] - train.iloc[-1 - period]   # change over the last 12 months
    years_ahead = np.ceil(np.arange(1, h + 1) / period)        # 1 for months 1-12, 2 for 13-24 ...
    return base + yearly_growth * years_ahead


METHODS = {
    "Naive": f_naive,
    "Seasonal naive": f_seasonal_naive,
    "Moving average (12)": f_moving_average,
    "Simple exp. smoothing": f_ses,
    "Seasonal naive + drift": f_seasonal_naive_drift,
}


# ----------------------------------------------------------------------------
# 4. ERROR METRICS
# ----------------------------------------------------------------------------
def mae(a, f):
    return float(np.mean(np.abs(a - f)))


def rmse(a, f):
    return float(np.sqrt(np.mean((a - f) ** 2)))


def mape(a, f):
    return float(np.mean(np.abs((a - f) / a)) * 100)


def backtest(s: pd.Series, horizon: int = 12) -> pd.DataFrame:
    """Hold out the final `horizon` months, forecast them from earlier data only."""
    train, test = s.iloc[:-horizon], s.iloc[-horizon:]
    rows = []
    for name, fn in METHODS.items():
        fc = fn(train, horizon)
        rows.append((name, mae(test.values, fc), rmse(test.values, fc), mape(test.values, fc)))
    res = pd.DataFrame(rows, columns=["method", "MAE", "RMSE", "MAPE_%"]).set_index("method")
    return res.sort_values("MAE").round(2)


def rolling_origin_backtest(s: pd.Series, horizon: int = 3, min_train: int = 36) -> pd.DataFrame:
    """Many forecast origins: train on [0:t], predict next `horizon`, slide forward.
    Gives a far more reliable score than a single train/test split."""
    errs = {name: [] for name in METHODS}
    origins = range(min_train, len(s) - horizon + 1)
    for t in origins:
        train, actual = s.iloc[:t], s.iloc[t:t + horizon].values
        for name, fn in METHODS.items():
            errs[name].append(np.abs(actual - fn(train, horizon)).mean())
    out = pd.DataFrame({"MAE": {k: np.mean(v) for k, v in errs.items()}})
    out["n_origins"] = len(origins)
    return out.sort_values("MAE").round(2)


# ----------------------------------------------------------------------------
# 5. VERIFICATION
# ----------------------------------------------------------------------------
def verify(s: pd.Series, dec: pd.DataFrame, bt: pd.DataFrame) -> None:
    # A: observed = trend + seasonal + resid, wherever the trend exists
    ok = dec.dropna()
    recon = ok["trend"] + ok["seasonal"] + ok["resid"]
    assert np.allclose(recon, ok["observed"]), "Components do not add back to the series"

    # B: seasonal indices sum to zero over one full cycle
    one_cycle = dec["seasonal"].iloc[:PERIOD].sum()
    assert abs(one_cycle) < 1e-9, "Seasonal indices must sum to zero"

    # C: centred MA at one point recomputed by hand (2 x 12 weights: 0.5, 1 x10, 0.5, over 12)
    i = 20
    w = np.r_[0.5, np.ones(PERIOD - 1), 0.5] / PERIOD
    hand = float(np.dot(s.iloc[i - PERIOD // 2: i + PERIOD // 2 + 1].values, w))
    assert abs(hand - dec["trend"].iloc[i]) < 1e-9, "Centred MA differs from hand calculation"

    # D: the first and last 6 trend values are NaN (not enough neighbours), nothing else
    assert dec["trend"].isna().sum() == PERIOD, "Expected exactly 12 NaN trend values"

    # E: recovered seasonal pattern matches the TRUE one used to build the data.
    #    Each month's index averages ~5 noisy yearly values, so its standard error is
    #    about NOISE_SD / sqrt(5). Allow 3 standard errors, and require near-perfect correlation.
    recovered = dec["seasonal"].iloc[:PERIOD].values
    max_gap = np.abs(recovered - TRUE_SEASONAL).max()
    tol = 3 * NOISE_SD / np.sqrt(5)
    corr = np.corrcoef(recovered, TRUE_SEASONAL)[0, 1]
    assert max_gap < tol, f"Recovered seasonality too far from truth (max gap {max_gap:.2f} > {tol:.2f})"
    assert corr > 0.99, f"Recovered seasonality shape differs from truth (corr {corr:.3f})"

    # F: one backtest metric recomputed by hand
    train, test = s.iloc[:-12], s.iloc[-12:]
    sn = train.iloc[-12:].values
    hand_mae = np.abs(test.values - sn).mean()
    assert abs(round(hand_mae, 2) - bt.loc["Seasonal naive", "MAE"]) < 1e-9, "MAE mismatch"

    # G: naive forecast really is a flat line at the last observed value
    assert np.all(f_naive(train, 12) == train.iloc[-1])

    print(f"All 7 verification checks passed (max gap to true seasonality = {max_gap:.2f}, "
          f"tolerance {tol:.2f}, correlation {corr:.4f}).")


# ----------------------------------------------------------------------------
# 6. CHARTS
# ----------------------------------------------------------------------------
def save_charts(dec: pd.DataFrame, s: pd.Series, horizon: int = 12) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
    for ax, col, color in zip(axes, ["observed", "trend", "seasonal", "resid"],
                              ["#1f77b4", "#d62728", "#2ca02c", "#7f7f7f"]):
        ax.plot(dec.index, dec[col], color=color)
        ax.set_ylabel(col)
        ax.grid(alpha=0.3)
    axes[0].set_title("Additive Decomposition: Observed = Trend + Seasonal + Residual")
    fig.tight_layout()
    fig.savefig("decomposition.png", dpi=150)
    plt.close(fig)

    train, test = s.iloc[:-horizon], s.iloc[-horizon:]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(train.index[-36:], train.iloc[-36:], color="black", label="Train (last 36 mo)")
    ax.plot(test.index, test, color="black", linestyle="--", label="Actual (held out)")
    for name in ["Naive", "Seasonal naive", "Seasonal naive + drift"]:
        ax.plot(test.index, METHODS[name](train, horizon), marker="o", markersize=3, label=name)
    ax.set_title("Backtest: Forecasts vs Held-Out Actuals")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("forecast_backtest.png", dpi=150)
    plt.close(fig)


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
def main() -> None:
    pd.set_option("display.width", 200)
    s = generate_series()
    print(f"Series: {len(s)} monthly points | {s.index[0].date()} to {s.index[-1].date()} | "
          f"mean {s.mean():.2f} | min {s.min():.2f} | max {s.max():.2f}\n")

    dec = decompose(s)
    slope = np.polyfit(np.arange(dec["trend"].dropna().size), dec["trend"].dropna().values, 1)[0]
    print(f"Estimated trend slope: {slope:.3f} per month (true value used to build data: 1.500)")
    resid_sd = dec["resid"].std()
    print(f"Residual std dev: {resid_sd:.2f} (noise std dev used to build data: 4.00)\n")

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    comp = pd.DataFrame({"estimated": dec["seasonal"].iloc[:PERIOD].values.round(2),
                         "true": TRUE_SEASONAL.round(2)}, index=months)
    comp["gap"] = (comp["estimated"] - comp["true"]).round(2)
    print("Seasonal index per month (estimated vs true):")
    print(comp.to_string(), "\n")

    bt = backtest(s, horizon=12)
    print("Single hold-out backtest (last 12 months):")
    print(bt.to_string(), "\n")

    ro = rolling_origin_backtest(s, horizon=3, min_train=36)
    print("Rolling-origin backtest (3-month horizon, many origins):")
    print(ro.to_string(), "\n")

    verify(s, dec, bt)
    save_charts(dec, s)
    print("Saved: decomposition.png, forecast_backtest.png")


if __name__ == "__main__":
    main()
