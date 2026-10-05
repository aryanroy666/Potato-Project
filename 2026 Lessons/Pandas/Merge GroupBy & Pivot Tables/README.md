# Pandas Merge, GroupBy and Pivot Tables

**Tools:** Python, Pandas
**File:** [`Pandas Merge GroupBy and Pivot Tables.py`](./Pandas%20Merge%20GroupBy%20and%20Pivot%20Tables.py)

## What I Learned

Almost every analyst report is built from three moves: **combine** tables, **summarize** them, and **reshape** the result so a human can read it. Pandas has one tool for each.

| Move | Pandas tool | SQL / Excel equivalent | Analogy |
|------|-------------|------------------------|---------|
| Combine tables | `merge()` | `JOIN` | Matching a guest list with a ticket list |
| Summarize by group | `groupby()` | `GROUP BY` | Sorting students by class, then averaging each class |
| Reshape for reading | `pivot_table()`, `crosstab()` | Excel pivot table | Turning a long list into a neat grid |

The script builds three small related tables (customers, products, orders), joins them, summarizes them, and ends with a mini report.

## What the Script Covers

### Part 1: Merge

| Technique | Code | Purpose |
|-----------|------|---------|
| Inner merge | `how="inner"` | Keep only rows that match in both tables |
| Safety check | `validate="many_to_one"` | Error out if keys are duplicated unexpectedly |
| Anti-join | `how="left"` + `indicator=True` | Find customers who never ordered |
| Different key names | `left_on=` / `right_on=` | Join when column names do not match |

### Part 2: GroupBy

| Technique | Code | Purpose |
|-----------|------|---------|
| Named aggregation | `.agg(total=("revenue", "sum"))` | Several metrics at once, with clean column names |
| Group value on every row | `.transform("sum")` | Each order's share of its city's revenue |
| Rank within a group | `.rank(method="dense")` | Top customer per city |
| Filter whole groups | `.filter(lambda g: ...)` | Like SQL `HAVING` |
| Running total | `.cumsum()` | Cumulative monthly revenue |

### Part 3: Pivot Tables

| Technique | Code | Purpose |
|-----------|------|---------|
| Pivot table | `pivot_table(..., margins=True)` | Revenue by city and category, with totals |
| Cross-tab | `pd.crosstab()` | Count of orders by city and category |
| Monthly trend by category | `pivot_table(index="month", ...)` | Ready for a line chart |
| Melt | `.melt()` | Back to long format, needed by most chart tools |

## Sample Output (from the setup data)

**Revenue by city and category:**

| city | Electronics | Furniture | Total |
|------|-------------|-----------|-------|
| Delhi | 28000 | 18000 | 46000 |
| Kolkata | 75000 | 12000 | 87000 |
| Mumbai | 110000 | 36000 | 146000 |
| **Total** | 213000 | 66000 | 279000 |

**Top customer per city:** Priya (Delhi), Aman (Kolkata), Rahul (Mumbai)

## Key Concepts and Interview Points

**Know your join types.** Inner keeps matches only. Left keeps everything from the left table and fills `NaN` where there is no match. Outer keeps everything from both. Choosing wrongly changes your totals without any error, so always say *why* you picked one.

**Row explosion is the silent killer.** If the key is duplicated in the table you are joining to, every match multiplies rows and your revenue gets double-counted. Two defences are used in the script: compare row counts before and after the merge, and pass `validate="many_to_one"` so pandas raises an error instead of quietly inflating the data. This is a favourite interview question: *"How do you make sure a join didn't create duplicates?"*

**`indicator=True` makes joins debuggable.** It adds a `_merge` column saying `both`, `left_only` or `right_only`. Filtering for `left_only` is the pandas version of the SQL `LEFT JOIN ... WHERE right.id IS NULL` anti-join pattern.

**`agg` vs `transform` vs `filter`.** This trips up many candidates:

| Method | Returns | Use when |
|--------|---------|----------|
| `agg` | One row per group | You want a summary table |
| `transform` | Same number of rows as the original | You want a group number next to every row (share of total, z-scores) |
| `filter` | Only the rows from groups that pass a test | You want to keep or drop whole groups |

**`transform` is the pandas version of a SQL window function.** `groupby().transform("sum")` is `SUM(...) OVER (PARTITION BY ...)`, which connects directly to Day 1.

**`pivot_table` vs `groupby`.** A pivot table is a `groupby` whose result is reshaped into a grid. Use `pivot_table` for presentation and `groupby` for further calculation. `fill_value=0` avoids gaps, and `margins=True` adds totals.

**Why melt?** Pivoted (wide) data is easy for people to read, but plotting libraries and databases usually want long format, with one row per observation. Knowing when to go wide and when to go long is a sign of real experience.

**Be careful with averages of averages.** The average of group averages is not the overall average unless the groups are the same size. Calculate from the raw rows instead.

## How to Run

```bash
pip install pandas
python "Pandas Merge GroupBy and Pivot Tables.py"
```

The data is built inside the script, so no download is needed and the output is identical every time.

## Next Steps

- Plot the monthly revenue by category with Matplotlib
- Rebuild the same report in SQL using `JOIN`, `GROUP BY` and window functions, then compare results
- Try `merge_asof` for matching on the nearest date
