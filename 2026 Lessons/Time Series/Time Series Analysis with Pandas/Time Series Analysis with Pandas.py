"""
Potato Project Topic: Time Series
Time Series Analysis with Pandas

Business question:
    A retailer has daily sales for about 21 months. How are sales trending,
    what repeating patterns exist (weekly, yearly), were there unusual days,
    and can we forecast the next 4 weeks?

What this script covers:
    1. Datetime index and checking for missing days
    2. Resampling (daily -> weekly -> monthly)
    3. Rolling averages (smoothing noise to see the trend)
    4. Lags, month-over-month and year-over-year growth
    5. Seasonality: day-of-week and month patterns
    6. Decomposition: trend + seasonality + leftover noise
    7. Anomaly detection on the leftover noise
    8. Forecasting with simple baselines and honest evaluation

Run it with:  python "Time Series Analysis with Pandas.py"
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

# ---------------------------------------------------------------------
# STEP 0: Create a sample daily sales dataset
# ---------------------------------------------------------------------
# Built from known ingredients so we can check what the analysis finds:
#   trend (slow growth) + weekly pattern (weekends high) + yearly pattern
#   (festive peak in Oct-Nov) + random noise + 3 injected unusual days.
rng = np.random.default_rng(42)
dates = pd.date_range("2025-01-01", "2026-09-30", freq="D")
t = np.arange(len(dates))

trend = 2000 + 3.0 * t
weekly = np.array([0.90, 0.92, 0.95, 1.00, 1.10, 1.30, 1.25])[dates.dayofweek]  # Mon..Sun
yearly = 1 + 0.25 * np.exp(-((dates.dayofyear - 300) ** 2) / (2 * 25 ** 2))       # peak ~ end of Oct
sales = np.asarray(trend * weekly * yearly * rng.normal(1, 0.05, len(dates)))

anomaly_days = ["2025-06-18", "2025-12-25", "2026-04-09"]
sales[dates.get_indexer(pd.to_datetime(anomaly_days))] *= [2.2, 0.35, 2.0]

raw = pd.DataFrame({"date": dates, "sales": sales.round(0)})
raw = raw.drop(raw.sample(5, random_state=1).index)    # simulate 5 missing days
raw["date"] = raw["date"].dt.strftime("%Y-%m-%d")       # dates stored as TEXT, like a CSV

# ---------------------------------------------------------------------
# STEP 1: Datetime index and missing days
# ---------------------------------------------------------------------
# Rule 1 of time series: convert dates to real datetimes and make them the
# index. Rule 2: check for gaps, because rolling windows and lags assume
# one row per day.
df = raw.copy()
df["date"] = pd.to_datetime(df["date"])
df = df.set_index("date").sort_index()

print("=" * 60)
print("STEP 1: DATETIME INDEX AND GAPS")
print("=" * 60)
print("Rows:", len(df), "| From", df.index.min().date(), "to", df.index.max().date())
full_range = pd.date_range(df.index.min(), df.index.max(), freq="D")
missing = full_range.difference(df.index)
print("Missing days:", len(missing), [d.strftime("%Y-%m-%d") for d in missing])

# asfreq("D") inserts the missing days as NaN; interpolate fills them by
# drawing a straight line between neighbours. Fine for a few single-day gaps.
s = df["sales"].asfreq("D").interpolate(method="linear")
print("Missing after fix:", int(s.isna().sum()))

# ---------------------------------------------------------------------
# STEP 2: Resampling
# ---------------------------------------------------------------------
# Resampling is GROUP BY for time: group days into weeks or months.
# Use SUM for flows (sales, orders) and MEAN for levels (price, temperature).
weekly_sales = s.resample("W").sum()
monthly = s.resample("ME").sum()
print("\n" + "=" * 60)
print("STEP 2: RESAMPLING")
print("=" * 60)
print("Monthly sales (first 4 months):")
print(monthly.head(4).round(0))

# ---------------------------------------------------------------------
# STEP 3: Rolling averages
# ---------------------------------------------------------------------
# Daily data is noisy. A 7-day average removes the weekday pattern; a 30-day
# average shows the slow trend. Analogy: a blurry photo reveals the shape
# better than one with every pore visible.
roll7 = s.rolling(7).mean()
roll30 = s.rolling(30).mean()
print("\n" + "=" * 60)
print("STEP 3: ROLLING AVERAGES (last 3 days)")
print("=" * 60)
print(pd.DataFrame({"daily": s, "7-day avg": roll7, "30-day avg": roll30}).tail(3).round(0))

# ---------------------------------------------------------------------
# STEP 4: Lags and growth rates
# ---------------------------------------------------------------------
# shift(n) moves the series down by n rows so each row can see the past.
# This is the pandas version of SQL's LAG().
growth = monthly.to_frame("sales")
growth["mom_%"] = (growth["sales"].pct_change() * 100).round(1)
growth["yoy_%"] = (growth["sales"].pct_change(12) * 100).round(1)
print("\n" + "=" * 60)
print("STEP 4: MONTH-OVER-MONTH AND YEAR-OVER-YEAR GROWTH")
print("=" * 60)
print(growth.tail(6).round(0))
print("YoY needs 12 months of history, so it starts in the 13th month.")

# ---------------------------------------------------------------------
# STEP 5: Seasonality
# ---------------------------------------------------------------------
# Average by weekday and by month. A seasonal INDEX divides each group's
# average by the overall average: 1.20 means "20% above a typical day".
dow_index = (s.groupby(s.index.dayofweek).mean() / s.mean()).round(2)
dow_index.index = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
month_index = (s.groupby(s.index.month).mean() / s.mean()).round(2)
print("\n" + "=" * 60)
print("STEP 5: SEASONAL INDEX")
print("=" * 60)
print("By weekday:\n", dow_index)
print("\nBy month (note: this mixes in the growth trend, and Oct-Dec exist only for "
      "2025, so a proper yearly index needs more years of data):\n", month_index)

# ---------------------------------------------------------------------
# STEP 6: Decomposition (trend + seasonality + residual)
# ---------------------------------------------------------------------
# Split the series into parts, like separating a smoothie back into fruit:
#   trend    = centred 7-day average (removes the weekly cycle)
#   seasonal = how far each weekday sits from the trend, on average
#   residual = what is left over (noise and anomalies)
# Multiplicative form, because weekend peaks get bigger as sales grow.
trend_c = s.rolling(7, center=True).mean()
ratio = s / trend_c
weekday_factor = ratio.groupby(ratio.index.dayofweek).mean()
seasonal = pd.Series(weekday_factor.reindex(s.index.dayofweek).values, index=s.index)
residual = s / (trend_c * seasonal)
print("\n" + "=" * 60)
print("STEP 6: DECOMPOSITION")
print("=" * 60)
print("Weekday factors (Mon..Sun):", weekday_factor.round(2).tolist())
print(f"Residual mean = {residual.mean():.3f} (should be near 1.0), "
      f"std = {residual.std():.3f}")

# ---------------------------------------------------------------------
# STEP 7: Anomaly detection on the residual
# ---------------------------------------------------------------------
# After removing trend and weekly pattern, ordinary days sit near 1.0.
# Days more than 4 standard deviations away are suspicious.
z = (residual - residual.mean()) / residual.std()
anomalies = z[z.abs() > 4].dropna()
print("\n" + "=" * 60)
print("STEP 7: ANOMALIES (|z| > 4 on the residual)")
print("=" * 60)
for d, val in anomalies.items():
    print(f"{d.date()}  sales = {s[d]:,.0f}  z = {val:+.1f}")
print("Injected unusual days were:", anomaly_days)

# ---------------------------------------------------------------------
# STEP 8: Forecast the last 28 days with simple baselines
# ---------------------------------------------------------------------
# Time series rule: NEVER shuffle. Train on the past, test on the future.
HORIZON = 28
train, test = s.iloc[:-HORIZON], s.iloc[-HORIZON:]

naive = pd.Series(train.iloc[-1], index=test.index)                    # repeat last value
moving_avg = pd.Series(train.iloc[-28:].mean(), index=test.index)       # repeat 28-day average
last_week = train.iloc[-7:].values
seasonal_naive = pd.Series(np.tile(last_week, HORIZON // 7), index=test.index)  # same weekday last week

def score(name, forecast):
    mae = (test - forecast).abs().mean()
    mape = ((test - forecast).abs() / test).mean() * 100
    print(f"{name:<28} MAE = {mae:8.0f} | MAPE = {mape:5.1f}%")
    return mae

print("\n" + "=" * 60)
print(f"STEP 8: FORECAST THE LAST {HORIZON} DAYS")
print("=" * 60)
score("Naive (last value)", naive)
score("Moving average (28 days)", moving_avg)
score("Seasonal naive (last week)", seasonal_naive)

# ---------------------------------------------------------------------
# CHART: three panels summarising the analysis
# ---------------------------------------------------------------------
BLUE, ORANGE, GREY = "#2E86AB", "#E4572E", "#B8C4CE"
fig, axes = plt.subplots(3, 1, figsize=(11, 13))

ax = axes[0]
ax.plot(s.index, s, color=GREY, linewidth=0.8, label="Daily sales")
ax.plot(roll30.index, roll30, color=BLUE, linewidth=2.2, label="30-day average")
ax.scatter(anomalies.index, s[anomalies.index], color=ORANGE, s=45, zorder=5, label="Anomaly")
ax.set_title("Sales trend upward, with a festive peak and three unusual days",
             loc="left", fontweight="bold")
ax.legend(frameon=False, loc="upper left")

ax = axes[1]
colors = [ORANGE if v == dow_index.max() else GREY for v in dow_index.values]
ax.bar(dow_index.index, dow_index.values, color=colors)
ax.axhline(1, color="black", linewidth=1, linestyle="--")
ax.set_title(f"{dow_index.idxmax()} is the strongest day: {dow_index.max():.2f}x a typical day",
             loc="left", fontweight="bold")
ax.set_ylabel("Seasonal index (1.0 = average day)")

ax = axes[2]
ax.plot(train.index[-56:], train.iloc[-56:], color=GREY, label="Training data")
ax.plot(test.index, test, color="black", linewidth=2, label="Actual")
ax.plot(seasonal_naive.index, seasonal_naive, color=ORANGE, linestyle="--", linewidth=2,
        label="Seasonal naive forecast")
ax.plot(moving_avg.index, moving_avg, color=BLUE, linestyle=":", linewidth=2,
        label="Moving average forecast")
ax.set_title("Repeating last week's pattern beats a flat average forecast",
             loc="left", fontweight="bold")
ax.legend(frameon=False, loc="upper left")

for a in axes:
    a.spines[["top", "right"]].set_visible(False)
    a.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(OUT / "time_series_overview.png", dpi=120)
plt.close(fig)
print("\nSaved chart to:", OUT / "time_series_overview.png")
