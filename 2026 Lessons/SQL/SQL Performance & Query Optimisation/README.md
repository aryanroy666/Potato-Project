# SQL Performance and Query Optimisation

**Tools:** SQL (PostgreSQL syntax; dialect notes given per problem; tested for correctness in DuckDB)

**File:** [`SQL Performance & Query Optimisation.sql`](./SQL%20Performance%20&%20Query%20Optimisation.sql)

## What I Learned

Writing a query that returns the right answer is step one. Writing one that returns it **fast** is what separates a junior analyst from a senior one. A query that takes 3 seconds on a 500-row practice table can take 3 minutes on a 50-million-row production table, and the difference almost always comes down to a handful of recurring patterns, not exotic tuning.

This file covers those patterns against a small but realistic four-table schema (customers, products, orders, order_items), the kind an analyst meets on day one of a real job.

## Workflow

| Part | Topic | Key idea |
|------|-------|----------|
| 1 | Indexes | How the database finds rows without reading every one |
| 2 | Query patterns | Writing the same logic in a way the engine can execute efficiently |
| 3 | Data type and filter traps | Small mistakes that silently disable every optimisation above |

## Part 1: Indexes

**Analogy:** a book's index lets you jump straight to a page instead of reading cover to cover. A database index on `order_date` does the same for a `WHERE order_date >= ...` filter.

| Pattern | What it means |
|---------|----------------|
| Sequential scan vs index scan | Without an index, every row is read; with one, only matching pages are |
| Covering index (index-only scan) | If every column the query needs is inside the index, the table itself is never touched |
| Sargable predicates | A filter the database **can** use an index for; wrapping a column in a function (`EXTRACT(YEAR FROM ...)`) makes it non-sargable |

On this file's small sample data, PostgreSQL's planner may still choose a sequential scan even after adding an index, because scanning eight rows directly is already faster than loading an index. This is expected and worth saying out loud in an interview: *index behaviour only shows its real value at realistic scale, and a good analyst checks `EXPLAIN` rather than assuming.*

## Part 2: Query Patterns

| # | Pattern | The idea in one line |
|---|---------|------------------------|
| 2 | `EXISTS` vs `COUNT(*) > 0` | `EXISTS` stops at the first match; `COUNT(*)` counts everything first |
| 3 | Avoid `SELECT *` | Name only the columns needed; also keeps covering indexes effective |
| 4 | Aggregate before joining | Shrink a table to the right grain before it meets a join, avoiding the Day 7 fan-out trap |
| 5 | Window function vs self-join | One pass over the data instead of two |

**Verified, not just written:** I ran both the "slow" and "fast" version of Problems 2 and 4 and confirmed they return **identical results**: the same 8 customers for the `EXISTS` comparison, and matching customer totals for the pre-aggregation rewrite. A faster query that returns a different answer is not an optimisation, it is a bug, so checking this mattered more than checking the SQL merely ran without error.

## Part 3: Data Type and Filter Traps

| # | Trap | Why it matters |
|---|------|------------------|
| 6 | Implicit type cast | Comparing a text column to a number can force a cast on every row, disabling its index |
| 7 | `OR` across two columns | Can block the use of a composite index; `UNION ALL` lets each branch use its own index |
| 8 | `NULL` in aggregates and filters | `COUNT(*)` counts `NULL`s, `COUNT(column)` skips them; `= NULL` never matches, `IS NULL` does |

## Key Concepts and Interview Points

**"Did you use an index?" is really asking two things.** First, does an index exist on the filtered column? Second, is the query written so the planner can actually *use* it? A query can have a perfectly good index sitting right there and still ignore it, because the `WHERE` clause wraps the column in a function. Both halves matter, and interviewers often probe the second half specifically because it is the one people forget.

**Sargable is a word worth knowing and using.** It means "can this predicate use an index (Search ARGument ABLE)". `WHERE EXTRACT(YEAR FROM order_date) = 2026` is not sargable because the function must run on every row before comparison is even possible. `WHERE order_date BETWEEN '2026-01-01' AND '2026-12-31'` is sargable because the bare column sits on one side of the comparison. The fix is almost always to move the transformation off the column and onto the comparison value instead.

**`EXISTS` vs `COUNT(*) > 0` is a short-circuit, not a trick.** `EXISTS` can stop the instant it finds one matching row. `COUNT(*) > 0` must tally every matching row before the comparison can even run, like counting every apple in a barrel just to confirm there is at least one. On a customer with thousands of orders, this is not a minor difference.

**Aggregate before you join, not after.** This connects directly to Day 7's fan-out trap: joining raw, un-aggregated rows multiplies them, inflating any `SUM` taken afterward and wasting work the database never needed to do. Before writing a join, ask "what grain do I actually need the right-hand table at?" and aggregate to that grain first.

**A window function usually beats a correlated subquery or self-join for the same question.** Both can answer "how does this row compare to others in its group?", but a self-join or correlated subquery scans the table once per outer row, while a window function does it in a single pass. This is the performance argument behind the syntax choice first introduced in Day 1.

**`SELECT *` costs more than it looks like.** It pulls every column across the network even when only two are needed, defeats covering indexes (which can only answer a query without touching the table when every requested column is in the index), and silently breaks downstream code if a column is ever added, removed or reordered. Naming columns explicitly avoids all three problems at once.

**Type mismatches are invisible until you look for them.** A `VARCHAR` column compared against an integer literal can force a cast on every row in the column, not just the literal, which quietly disables an otherwise perfectly good index. Always match the literal's type to the column's declared type.

**`NULL` breaks intuition in three separate places.** `COUNT(*)` includes `NULL` rows, `COUNT(column)` does not; `SUM` and `AVG` silently skip `NULL`s (correct, but easy to forget when debugging a total that looks "too low"); and `column = NULL` always evaluates to unknown, never true, so `IS NULL` is the only way to actually test for it. All three are genuinely common sources of "why are my numbers wrong" bugs, not just textbook trivia.

**`EXPLAIN` is how you stop guessing.** Every performance claim here can be checked rather than assumed, by running `EXPLAIN` (or `EXPLAIN ANALYZE` to see real execution time) in front of a query and reading which scan type the planner chose. "I checked the query plan" is a stronger interview answer than "I heard indexes are faster."

**Dialect notes.**

| Feature | PostgreSQL | MySQL | SQL Server |
|---------|------------|-------|-------------|
| Auto-increment key | `SERIAL` | `AUTO_INCREMENT` | `IDENTITY(1,1)` |
| Query plan | `EXPLAIN` / `EXPLAIN ANALYZE` | `EXPLAIN` | `SET SHOWPLAN_ALL ON` |
| Covering index hint | automatic | `USE INDEX` (rarely needed) | `INCLUDE` columns in index |

## How to Run

1. Open a PostgreSQL environment (or an online sandbox that supports `EXPLAIN`).
2. Run the `SETUP` section to create all four tables with sample data and the two indexes.
3. Run the paired "BAD / GOOD" or "SLOWER / FASTER" queries in each problem, and where available, run `EXPLAIN` in front of each to compare the chosen plan.

Note: on this file's small sample data, the planner may pick a sequential scan over an index scan in some cases, since it correctly judges that to be faster at this size. The patterns are what to apply at realistic scale, not a guarantee of a different plan on 8 rows.

## Next Steps

- Load a few hundred thousand synthetic rows and re-run `EXPLAIN ANALYZE` to see these patterns actually change the chosen plan
- Compare a B-tree index with a partial index (`WHERE status = 'Delivered'`) for a filter that only ever targets one value
- Measure actual execution time, not just the plan, using `EXPLAIN (ANALYZE, BUFFERS)`
- Revisit Day 7's fan-out trap and Day 1's window functions through a performance lens now that the underlying mechanics are clearer
