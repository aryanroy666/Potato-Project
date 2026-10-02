"""
Potato Project: Day 2
Pandas Data Cleaning & Exploratory Data Analysis (EDA)
Date: Oct 2, 2026

What this script does:
    1. Builds a small, deliberately MESSY retail dataset (so no download is needed)
    2. Inspects the problems
    3. Cleans the data step by step
    4. Runs a quick EDA to answer business questions

Run it with:  python Pandas-Data-Cleaning-EDA.py
Requires:     pandas, numpy
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------
# STEP 0: Create a messy dataset
# ---------------------------------------------------------------------
# Real data is rarely clean. This dataset has the usual problems:
# duplicates, missing values, inconsistent text, wrong data types, outliers.
rng = np.random.default_rng(42)
n = 60

categories = rng.choice(["Electronics", "Furniture", "Clothing"], n)
base_price = pd.Series(categories).map(
    {"Electronics": 15000, "Furniture": 5000, "Clothing": 1500}
).to_numpy()

raw = pd.DataFrame({
    "order_id": np.arange(1001, 1001 + n),
    "order_date": pd.date_range("2026-01-01", periods=n, freq="4D").strftime("%d-%m-%Y"),
    "customer_name": rng.choice(
        ["Aman Das", "  riya sen", "RAHUL ROY", "Sneha Paul", "aman das", "Priya Nath"], n),
    "city": rng.choice(["Kolkata", "kolkata ", "Delhi", "DELHI", "Mumbai", "Mumbai "], n),
    "category": categories,
    "quantity": rng.integers(1, 6, n).astype(float),
    "unit_price": (base_price * rng.uniform(0.8, 1.2, n)).round(0),
})

# Inject problems on purpose
raw.loc[[5, 17, 33], "quantity"] = np.nan            # missing quantity
raw.loc[[8, 41], "unit_price"] = np.nan              # missing price
raw.loc[12, "unit_price"] = 9000000.0                # extreme outlier (typo)
raw.loc[[20, 21], "city"] = np.nan                   # missing city
raw["unit_price"] = raw["unit_price"].astype("object")
raw.loc[3, "unit_price"] = "Rs. 1500"                # text inside a number column
raw = pd.concat([raw, raw.iloc[[2, 9]]], ignore_index=True)  # exact duplicate rows

# ---------------------------------------------------------------------
# STEP 1: Inspect the data (always look before you clean)
# ---------------------------------------------------------------------
# Analogy: a doctor examines the patient before prescribing medicine.
print("=" * 60)
print("STEP 1: INSPECTION")
print("=" * 60)
print("Shape (rows, columns):", raw.shape)
print("\nData types:\n", raw.dtypes)
print("\nMissing values per column:\n", raw.isna().sum())
print("\nDuplicate rows:", raw.duplicated().sum())

# ---------------------------------------------------------------------
# STEP 2: Clean the data
# ---------------------------------------------------------------------
df = raw.copy()  # never edit the raw data; keep it as a backup

# 2a. Remove exact duplicate rows
df = df.drop_duplicates()

# 2b. Fix text: strip spaces and use consistent capitalisation
#     "kolkata " and "Kolkata" would otherwise be counted as two cities.
df["customer_name"] = df["customer_name"].str.strip().str.title()
df["city"] = df["city"].str.strip().str.title()

# 2c. Fix data types
#     Dates stored as text can't be sorted or grouped by month properly.
df["order_date"] = pd.to_datetime(df["order_date"], format="%d-%m-%Y")

#     Strip "Rs." from price text, then convert to numbers.
#     errors="coerce" turns anything unconvertible into NaN instead of crashing.
df["unit_price"] = (
    df["unit_price"].astype(str).str.replace("Rs.", "", regex=False).str.strip()
)
df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")

# 2d. Handle outliers with the IQR rule, calculated PER CATEGORY
#     Analogy: if most people in a room earn Rs. 50k and one earns Rs. 9 crore,
#     the average becomes meaningless. IQR flags values far from the "middle 50%".
#     We do it per category because a Rs. 15,000 laptop is normal, but a
#     Rs. 15,000 T-shirt is not. "Outlier" always depends on the context.
grouped = df.groupby("category")["unit_price"]
q1 = grouped.transform(lambda x: x.quantile(0.25))
q3 = grouped.transform(lambda x: x.quantile(0.75))
upper_limit = q3 + 1.5 * (q3 - q1)
is_outlier = df["unit_price"] > upper_limit
print("\nOutlier rows flagged:")
print(df.loc[is_outlier, ["order_id", "category", "unit_price"]])
# Treat the flagged value as missing (it is a typo) rather than deleting the row.
df.loc[is_outlier, "unit_price"] = np.nan

# 2e. Handle missing values
#     Median is safer than mean because it is not pulled by extreme values.
#     Fill price using the median of the SAME category (more accurate than global).
df["unit_price"] = df["unit_price"].fillna(
    df.groupby("category")["unit_price"].transform("median")
)
df["quantity"] = df["quantity"].fillna(df["quantity"].median()).astype(int)
df["city"] = df["city"].fillna("Unknown")  # unknown is more honest than guessing

# 2f. Create a new column for analysis
df["revenue"] = df["quantity"] * df["unit_price"]
df["month"] = df["order_date"].dt.to_period("M")

print("\n" + "=" * 60)
print("STEP 2: AFTER CLEANING")
print("=" * 60)
print("Shape:", df.shape)
print("Missing values:\n", df.isna().sum())
print("Duplicates:", df.duplicated().sum())

# ---------------------------------------------------------------------
# STEP 3: Exploratory Data Analysis (EDA)
# ---------------------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 3: EDA")
print("=" * 60)

# 3a. Summary statistics
print("\nSummary statistics:\n", df[["quantity", "unit_price", "revenue"]].describe().round(2))

# 3b. Revenue by category
print("\nRevenue by category:")
print(df.groupby("category")["revenue"].agg(["sum", "mean", "count"]).round(2)
      .sort_values("sum", ascending=False))

# 3c. Revenue by city
print("\nRevenue by city:")
print(df.groupby("city")["revenue"].sum().sort_values(ascending=False).round(2))

# 3d. Monthly revenue trend with month-over-month growth
monthly = df.groupby("month")["revenue"].sum().to_frame("revenue")
monthly["mom_growth_%"] = (monthly["revenue"].pct_change() * 100).round(2)
print("\nMonthly revenue trend:\n", monthly)

# 3e. Top customers
print("\nTop 3 customers by revenue:")
print(df.groupby("customer_name")["revenue"].sum().nlargest(3).round(2))

# 3f. Correlation: does buying more units relate to higher revenue?
print("\nCorrelation matrix:\n", df[["quantity", "unit_price", "revenue"]].corr().round(2))

# ---------------------------------------------------------------------
# STEP 4: Save the cleaned data
# ---------------------------------------------------------------------
df.to_csv("cleaned_retail_orders.csv", index=False)
print("\nSaved cleaned data to cleaned_retail_orders.csv")
