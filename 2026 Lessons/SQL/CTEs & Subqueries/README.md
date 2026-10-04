# SQL CTEs and Subqueries

**Tools:** SQL (standard syntax; tested to run in PostgreSQL-style engines, MySQL 8+ and SQLite)

**File:** [`SQL CTEs & Subqueries.sql`](./SQL%20CTEs%20&%20Subqueries.sql)

## What I Learned

Most real analytics questions cannot be answered in a single step. You first need an intermediate result (an average, a total, a ranking) and then use it to answer the real question. **Subqueries** and **CTEs** are the two tools for building those steps.

- A **subquery** is a query tucked inside another query, like a calculation done in the margin of an exam paper.
- A **CTE** (Common Table Expression, written with `WITH`) gives that intermediate result a name, like labelled steps in a recipe. The query then reads top to bottom instead of inside out.

## Problems Solved

| # | Problem | Concept | Real-World Use |
|---|---------|---------|----------------|
| 1 | Employees earning above the company average | Scalar subquery | Benchmarking against an overall figure |
| 2 | Employees earning above their own department's average | Correlated subquery vs CTE | Fair comparisons within a group |
| 3 | Customers who ordered vs never ordered | `EXISTS` / `NOT EXISTS` | Finding inactive or churned customers |
| 4 | Customer segmentation by total spend | Chained CTEs, `LEFT JOIN`, `CASE` | Marketing segments (High / Medium / Low) |
| 5 | Highest-paid employee per department | CTE + window function | Top performer reports |
| 6 | Company hierarchy | Recursive CTE | Org charts, category trees |

## Subquery Types at a Glance

| Type | Returns | Example use |
|------|---------|-------------|
| Scalar | One value | `WHERE salary > (SELECT AVG(salary) ...)` |
| Row / list | A list of values | `WHERE id IN (SELECT ...)` |
| Table (in `FROM`) | A full result set | `FROM (SELECT ...) AS t` |
| Correlated | Depends on the outer row, re-runs per row | `WHERE salary > (SELECT AVG(...) WHERE dept = e.dept)` |

## Sample Output (from the setup data)

**Problem 3, customers who never ordered:**

| customer_name | city |
|---------------|------|
| Kabir | Mumbai |

**Problem 4, customer segments:**

| customer_name | total_spent | order_count | segment |
|---------------|-------------|-------------|---------|
| Rahul | 21500 | 3 | High |
| Aman | 10500 | 2 | High |
| Priya | 5500 | 2 | Medium |
| Riya | 1200 | 1 | Low |
| Sneha | 800 | 1 | Low |
| Kabir | 0 | 0 | Low |

**Problem 6, hierarchy (first rows):**

| level | emp_name | reporting_path |
|-------|----------|----------------|
| 1 | Asha | Asha |
| 2 | Bikram | Asha > Bikram |
| 3 | Chitra | Asha > Bikram > Chitra |
| 4 | Gita | Asha > Esha > Farhan > Gita |

## Key Concepts and Interview Points

**CTE vs subquery.** They often give the same result. A CTE wins on readability, can be referenced several times in the same query, and is the only way to write recursion. A subquery is fine for a quick, one-off filter. In an interview, say that you choose based on readability and reuse, and that performance is usually similar in modern databases (always check the query plan on large data).

**Correlated subqueries run once per outer row.** Like a teacher checking each student against their own class average, they are easy to read but can be slow on big tables. The CTE-and-join version in Problem 2 computes each average once. Knowing both and explaining the trade-off is a strong answer.

**`NOT EXISTS` is safer than `NOT IN`.** If the subquery behind `NOT IN` returns even one `NULL`, the whole condition returns no rows, because comparing anything with `NULL` is "unknown", not true. `NOT EXISTS` has no such trap. This is one of the most common SQL interview questions.

**`EXISTS` stops early.** It only checks whether a match exists, so it can stop at the first one. `SELECT 1` inside it is just a convention, since the selected value is ignored.

**Keep the zero-activity rows.** In Problem 4, an `INNER JOIN` would silently drop Kabir, who has no orders. `LEFT JOIN` keeps him, and `COALESCE(SUM(...), 0)` turns his `NULL` total into 0. Losing "zero" rows is a classic reporting bug.

**Why a CTE for window-function filters.** `WHERE` runs before window functions are calculated, so you cannot filter on a rank directly. Calculate the rank in a CTE, then filter in the outer query.

**Recursive CTE structure.** Two parts joined by `UNION ALL`: the **anchor** (the starting row, here the boss with no manager) and the **recursive member** (finds the next level by joining back to the CTE). It stops when the recursive step returns no new rows. In a real database with messy data, a loop in the hierarchy could run forever, so a depth limit is a sensible safeguard.

**Do not nest deeply.** Three or four nested subqueries are hard to read and debug. If you find yourself nesting, convert each layer into a named CTE.

## How to Run

1. Open any SQL environment (PostgreSQL, MySQL 8+, SQLite, or an online SQL sandbox).
2. Run the `SETUP` section first to create the three tables with sample data.
3. Run each problem one at a time and compare the output with your own answer first.

Note: in SQL Server, write `WITH` without the word `RECURSIVE`, and use `+` instead of `||` for joining text.

## Next Steps

- Rewrite Problem 4 using a subquery in `FROM` instead of CTEs and compare readability
- Add a depth limit to the recursive CTE
- Combine CTEs with window functions to find each customer's second-largest order
