# SQL Joins & Set Operations

**Tools:** SQL (standard syntax; tested to run in PostgreSQL-style engines and SQLite)

**File To Refer:** [`SQL Joins & Set Operations.sql`](./SQL%20Joins%20&%20Set%20Operations.sql)

## What I Learned

Real data lives in several tables, so almost every analysis starts by connecting them. There are two families of tools:

- **Joins** add **columns** side by side, matching rows through a shared key (like matching names on two lists).
- **Set operations** stack **rows** from two queries on top of each other (like merging two guest lists).

## Join Types in One Picture (Guest List Analogy)

Imagine two lists at a party: **A = customers**, **B = orders**.

| Join | Keeps | Plain-English meaning |
|------|-------|-----------------------|
| `INNER JOIN` | Only matches | People on **both** lists |
| `LEFT JOIN` | All of A, matches from B (else `NULL`) | Everyone on list A, with a blank where list B has nothing |
| `RIGHT JOIN` | All of B, matches from A | Mirror image of left join |
| `FULL OUTER JOIN` | Everything from both | Everyone from either list, gaps marked `NULL` |
| `CROSS JOIN` | Every pairing | Every row of A with every row of B |
| `SELF JOIN` | A table joined to itself | Same phone book read twice (employee and manager) |

## Problems Solved

| # | Problem | Concept | Real-World Use |
|---|---------|---------|----------------|
| 1 | Orders with customer names | `INNER JOIN` | Basic reporting |
| 2 | Customers who never ordered | `LEFT JOIN` + anti-join | Finding inactive customers |
| 3 | Unassigned employees and empty departments | `FULL OUTER JOIN` | Data quality checks |
| 4 | Employee with manager name | `SELF JOIN` | Org structure reports |
| 5 | Every colour and size combination | `CROSS JOIN` | Product variants, calendars |
| 6 | Why revenue totals inflate | Fan-out trap | Avoiding a very common real-world bug |
| 7 | Filter in `ON` vs `WHERE` | `LEFT JOIN` trap | Keeping customers who have no matches |
| 8 | Combining email lists | `UNION`, `UNION ALL`, `INTERSECT`, `EXCEPT` | Marketing audience building |

## Sample Output (from the setup data)

**Problem 6, the fan-out trap.** Aman has 2 orders worth 10,000 in total and 3 support tickets.

| customer_name | Wrong query (joined first) | Correct query (aggregated first) |
|---------------|----------------------------|----------------------------------|
| Aman | **30000** | 10000 |
| Rahul | 9000 | 9000 |

The wrong query counted Aman's revenue three times, once per ticket. Rahul looks fine only because he has just one ticket, which is why this bug is easy to miss.

**Problem 7, filter in `WHERE` vs `ON`:**

| Approach | Customers returned |
|----------|--------------------|
| Filter in `WHERE` | 2 (Aman, Rahul), the others vanished |
| Filter in `ON` | All 5, with 0 for those without delivered orders |

**Problem 8, set operations on the two email lists:**

| Operation | Result |
|-----------|--------|
| `UNION` | 5 unique emails |
| `UNION ALL` | 8 rows, duplicates kept |
| `INTERSECT` | riya, rahul (on both lists) |
| `EXCEPT` | aman, priya (subscribers without the app) |

## Key Concepts and Interview Points

**Fan-out is the number one join bug.** Joining two "many" tables to the same parent multiplies rows (2 orders x 3 tickets = 6 rows), and any `SUM` is inflated. The fix is to aggregate each table separately first (CTEs from Day 4), then join the summaries. Always check a total against a simple `SUM` on the original table. Interviewers love: *"Your revenue number looks too high after a join. What do you check?"*

**`WHERE` vs `ON` in a `LEFT JOIN`.** A filter on the right table in `WHERE` runs after the join and removes the `NULL` rows, so the left join silently turns into an inner join. Put right-table filters in `ON` to keep every left row.

**Anti-join = `LEFT JOIN ... WHERE right_key IS NULL`.** The same question can be answered with `NOT EXISTS`, which is safer than `NOT IN` when `NULL`s are possible (Day 4).

**Match the join to the question.** "All customers" needs a `LEFT JOIN`. "Only customers who ordered" needs an `INNER JOIN`. Picking the wrong one drops rows without any error message, so always say why you chose it.

**`COUNT(*)` vs `COUNT(column)` after a left join.** `COUNT(*)` counts the `NULL` row too, so a customer with no orders shows 1. `COUNT(o.order_id)` counts only real matches, which is why Problem 2 shows 0 for Kabir.

**Self joins need aliases.** Both copies of the table have the same column names, so aliases (`e` and `m`) are required. Use a `LEFT JOIN` so the top boss, who has no manager, is not lost.

**`UNION` vs `UNION ALL`.** `UNION` removes duplicates, which takes extra work. `UNION ALL` is faster and keeps everything. Use `UNION ALL` when duplicates cannot occur or you want them counted.

**Set operation rules.** Both queries need the same number of columns with compatible types. `INTERSECT` and `EXCEPT` treat `NULL`s as equal, unlike normal comparisons.

**Cross join with care.** The result has (rows in A) x (rows in B) rows, so an accidental cross join on large tables can overwhelm a database.

**Dialect notes.**

| Feature | PostgreSQL | MySQL | SQL Server | Oracle |
|---------|------------|-------|------------|--------|
| `FULL OUTER JOIN` | Yes | No (use `LEFT JOIN UNION RIGHT JOIN`) | Yes | Yes |
| `EXCEPT` | `EXCEPT` | `EXCEPT` (8.0.31+) | `EXCEPT` | `MINUS` |

## How to Run

1. Open any SQL environment (PostgreSQL, SQLite 3.39+, or an online SQL sandbox).
2. Run the `SETUP` section first to create all tables with sample data.
3. Run each problem one at a time, and try to predict the output before you run it.

## Next Steps

- Rewrite Problem 6 with window functions instead of CTEs and compare
- Add a `RIGHT JOIN` version of Problem 3 and confirm it matches
- Practice the same joins in Pandas with `merge()` (see the Day 5 topic)
