"""
Potato Project Topic: Pandas
Pandas Merge, GroupBy and Pivot Tables

The three tools behind almost every analyst report:
    1. MERGE  : combine tables (the pandas version of SQL JOIN)
    2. GROUPBY: split the data into groups, calculate, combine (SQL GROUP BY)
    3. PIVOT  : reshape results into a readable cross-table (Excel pivot table)

Run it with:  python "Pandas Merge GroupBy and Pivot Tables.py"
Requires:     pandas
"""

import pandas as pd

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 20)

# ---------------------------------------------------------------------
# STEP 0: Build three small related tables
# ---------------------------------------------------------------------
customers = pd.DataFrame({
    "customer_id": [1, 2, 3, 4, 5, 6],
    "customer_name": ["Aman", "Riya", "Rahul", "Sneha", "Priya", "Kabir"],
    "city": ["Kolkata", "Delhi", "Mumbai", "Kolkata", "Delhi", "Mumbai"],
})

products = pd.DataFrame({
    "product_id": [10, 11, 12, 13, 14],
    "product_name": ["Laptop", "Headphones", "Desk", "Chair", "Tablet"],
    "category": ["Electronics", "Electronics", "Furniture", "Furniture", "Electronics"],
    "unit_price": [60000, 3000, 12000, 6000, 25000],
})

orders = pd.DataFrame({
    "order_id": range(1, 13),
    "customer_id": [1, 1, 2, 3, 3, 3, 4, 5, 5, 1, 2, 3],
    "product_id": [10, 11, 13, 10, 12, 14, 11, 14, 13, 12, 11, 13],
    "quantity": [1, 2, 1, 1, 1, 2, 3, 1, 2, 1, 1, 4],
    "order_date": pd.to_datetime([
        "2026-01-10", "2026-01-25", "2026-02-03", "2026-02-14", "2026-02-20", "2026-03-05",
        "2026-03-18", "2026-03-29", "2026-04-11", "2026-04-21", "2026-05-02", "2026-05-15"]),
})
# Note: customer 6 (Kabir) has never ordered. This is on purpose.

# ---------------------------------------------------------------------
# PART 1: MERGE (joining tables)
# ---------------------------------------------------------------------
print("=" * 60)
print("PART 1: MERGE")
print("=" * 60)

# 1a. Inner merge: keep only rows that match in BOTH tables.
# Analogy: a guest list and a ticket list. Inner = people on both lists.
orders_full = (
    orders
    .merge(customers, on="customer_id", how="inner", validate="many_to_one")
    .merge(products, on="product_id", how="inner", validate="many_to_one")
)
orders_full["revenue"] = orders_full["quantity"] * orders_full["unit_price"]
print("\nOrders joined with customers and products:")
print(orders_full[["order_id", "customer_name", "city", "product_name",
                   "category", "quantity", "revenue"]].head())

# validate="many_to_one" tells pandas: "each order has ONE customer, but a
# customer can have MANY orders". If that is false (duplicate keys in the
# customers table), pandas raises an error instead of silently inflating rows.
print("\nRow count check: orders =", len(orders),
      "| after merges =", len(orders_full), "(must be equal)")

# 1b. Left merge + indicator: find customers who NEVER ordered (an "anti-join").
check = customers.merge(
    orders[["customer_id"]].drop_duplicates(),
    on="customer_id", how="left", indicator=True
)
never_ordered = check[check["_merge"] == "left_only"]
print("\nCustomers who never ordered:")
print(never_ordered[["customer_name", "city"]])

# 1c. A merge on columns with different names
renamed = customers.rename(columns={"customer_id": "cust_id"})
demo = orders.merge(renamed, left_on="customer_id", right_on="cust_id", how="left")
print("\nMerge with different key names works with left_on / right_on:")
print(demo[["order_id", "customer_id", "cust_id", "customer_name"]].head(3))

# ---------------------------------------------------------------------
# PART 2: GROUPBY (split, calculate, combine)
# ---------------------------------------------------------------------
print("\n" + "=" * 60)
print("PART 2: GROUPBY")
print("=" * 60)

# 2a. Named aggregation: several metrics at once with clear column names.
category_summary = (
    orders_full.groupby("category")
    .agg(total_revenue=("revenue", "sum"),
         avg_order_value=("revenue", "mean"),
         orders=("order_id", "count"),
         unique_customers=("customer_id", "nunique"))
    .round(0)
    .sort_values("total_revenue", ascending=False)
)
print("\nSummary by category:")
print(category_summary)

# 2b. transform(): add a group-level number BACK onto every row.
# Analogy: writing the class average next to every student's marks.
orders_full["city_revenue"] = orders_full.groupby("city")["revenue"].transform("sum")
orders_full["pct_of_city_revenue"] = (
    orders_full["revenue"] / orders_full["city_revenue"] * 100
).round(1)
print("\nEach order's share of its city's revenue (first 5 rows):")
print(orders_full[["order_id", "city", "revenue", "city_revenue",
                   "pct_of_city_revenue"]].head())

# 2c. Top customer per city using rank inside each group
customer_totals = (
    orders_full.groupby(["city", "customer_name"], as_index=False)["revenue"].sum()
)
customer_totals["rank_in_city"] = (
    customer_totals.groupby("city")["revenue"].rank(method="dense", ascending=False)
)
print("\nTop customer in each city:")
print(customer_totals[customer_totals["rank_in_city"] == 1]
      .sort_values("city")[["city", "customer_name", "revenue"]])

# 2d. Filter whole groups with a condition (like SQL HAVING)
big_customers = orders_full.groupby("customer_name").filter(
    lambda g: g["revenue"].sum() > 100000
)
print("\nCustomers with total revenue above 100,000:",
      sorted(big_customers["customer_name"].unique()))

# 2e. Monthly revenue with running total
orders_full["month"] = orders_full["order_date"].dt.to_period("M")
monthly = orders_full.groupby("month")["revenue"].sum().to_frame("revenue")
monthly["running_total"] = monthly["revenue"].cumsum()
print("\nMonthly revenue and running total:")
print(monthly)

# ---------------------------------------------------------------------
# PART 3: PIVOT TABLES (reshape for reading)
# ---------------------------------------------------------------------
print("\n" + "=" * 60)
print("PART 3: PIVOT TABLES")
print("=" * 60)

# 3a. pivot_table: rows = city, columns = category, values = revenue.
# This is exactly an Excel pivot table, written in code so it is repeatable.
pivot = orders_full.pivot_table(
    index="city", columns="category", values="revenue",
    aggfunc="sum", fill_value=0, margins=True, margins_name="Total"
)
print("\nRevenue by city and category:")
print(pivot)

# 3b. crosstab: a pivot table that simply counts occurrences.
counts = pd.crosstab(orders_full["city"], orders_full["category"])
print("\nNumber of orders by city and category:")
print(counts)

# 3c. Monthly revenue per category, one column per category
trend = orders_full.pivot_table(
    index="month", columns="category", values="revenue", aggfunc="sum", fill_value=0
)
print("\nMonthly revenue by category:")
print(trend)

# 3d. melt: the reverse of a pivot (wide -> long), needed for many chart tools.
long_format = trend.reset_index().melt(
    id_vars="month", var_name="category", value_name="revenue"
)
print("\nMelted back to long format (first 4 rows):")
print(long_format.head(4))

# ---------------------------------------------------------------------
# PART 4: Mini report that combines everything
# ---------------------------------------------------------------------
print("\n" + "=" * 60)
print("PART 4: MINI REPORT")
print("=" * 60)
total = orders_full["revenue"].sum()
best_city = orders_full.groupby("city")["revenue"].sum().idxmax()
best_product = orders_full.groupby("product_name")["revenue"].sum().idxmax()
print(f"Total revenue: {total:,}")
print(f"Best city: {best_city}")
print(f"Best product: {best_product}")
print(f"Customers who never ordered: {len(never_ordered)}")
