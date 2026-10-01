# Day 1: SQL Window Functions & Aggregation

**Date:** October 1, 2026
**Dialect:** PostgreSQL
**File:** [`oct-01-sql-interview-problems.sql`](./oct-01-sql-interview-problems.sql)

## What I Learned

A normal `GROUP BY` squashes many rows into one. A **window function** does the calculation across a group of related rows but keeps every row visible. Think of a class result sheet: `GROUP BY` gives you only the class average, while a window function lets you show each student's marks *next to* the class average and their rank.

The pattern is always:

```sql
FUNCTION() OVER (PARTITION BY ... ORDER BY ...)
```

- `PARTITION BY` splits rows into separate groups (like separate leaderboards).
- `ORDER BY` sets the order inside each group (needed for running totals, ranking, and LAG).

## Problems Solved

| # | Problem | Key Function | Real-World Use |
|---|---------|--------------|----------------|
| 1 | Running total by department | `SUM() OVER` | Cumulative sales tracking on dashboards |
| 2 | Top 3 products per category | `DENSE_RANK()` | Best-seller reports |
| 3 | Month-over-month growth | `LAG()` | Executive KPI reporting |
| 4 | Top 10% customers by spend | `PERCENT_RANK()` | Customer segmentation |
| 5 | Longest gap between purchases | `LAG()` + date math | Churn risk detection |

## Key Concepts and Interview Points

**Ranking functions differ only in how they treat ties.** For scores 100, 90, 90, 80:

| Function | Result |
|----------|--------|
| `ROW_NUMBER` | 1, 2, 3, 4 (ties broken arbitrarily) |
| `RANK` | 1, 2, 2, 4 (skips a number after a tie) |
| `DENSE_RANK` | 1, 2, 2, 3 (no gaps) |

**Common trap: filtering on a window function.** `WHERE` runs before window functions are calculated, so `WHERE DENSE_RANK() OVER (...) <= 3` throws an error. Wrap the ranking in a subquery or CTE and filter outside. (I made this exact mistake in my first draft of Problem 2, which is a good story to tell in an interview.)

**`LAG` and `LEAD`** look at the previous or next row. The first row has no previous row, so `LAG` returns `NULL`. Always think about what happens with that `NULL`.

**Default frame matters.** When you add `ORDER BY` inside `OVER()`, the default frame is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`. Rows with the same date are treated together. Use `ROWS BETWEEN` for a strict row-by-row running total.

**Safe division.** Wrap denominators in `NULLIF(x, 0)` to avoid divide-by-zero errors in growth calculations.

**Top 10% of customers is not top 10% of revenue.** Problem 4 ranks customers by spend. Finding the customers who generate 10% of revenue is a different question that needs a cumulative revenue share.

## How to Run

1. Open any PostgreSQL environment (local install, pgAdmin, or an online sandbox).
2. Run the `SETUP` section at the top of the SQL file to create the `sales` table with sample data.
3. Run each problem one at a time and compare the output with what you expect.

## Next Steps

- Try `NTILE(4)` to split customers into quartiles.
- Add `LEAD()` to forecast-style comparisons (next month vs this month).
- Rewrite Problem 3 using a self-join and compare readability with the `LAG` version.
