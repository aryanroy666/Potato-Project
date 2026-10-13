# SQL Consecutive Streaks (Gaps & Islands)

**Tools:** SQL (PostgreSQL syntax; tested to run unchanged in DuckDB)

**File:** [`SQL Consecutive Streaks Gaps & Islands.sql`](./SQL%20Consecutive%20Streaks%20Gaps%20&%20Islands.sql)

## What I Learned

Many real questions are about **unbroken runs** of something: login streaks, consecutive days of sales, uninterrupted machine uptime. This family is called **gaps and islands**:

- **Island** = an unbroken run of consecutive values (a 5-day login streak)
- **Gap** = the hole between two islands (the days the user was missing)

It is exactly how apps calculate a "day streak", and how GitHub counts a commit streak. It is also a favourite SQL interview topic, because it looks impossible until you see the trick.

## The Core Trick: Date Minus Row Number

Imagine climbing a staircase. Dates go up by 1 each day, and the row number goes up by 1 each row. While a streak continues, **date minus row number stays the same**. The moment a day is skipped, the date jumps but the row number does not, so the value changes.

Worked example for User 1 (after removing duplicate logins):

| login_date | row_number | date - row_number (grp) | Streak |
|------------|------------|--------------------------|--------|
| Sep 1 | 1 | Aug 31 | A |
| Sep 2 | 2 | Aug 31 | A |
| Sep 3 | 3 | Aug 31 | A |
| Sep 4 | 4 | Aug 31 | A |
| Sep 5 | 5 | Aug 31 | A |
| Sep 8 | 6 | Sep 2 | B |
| Sep 9 | 7 | Sep 2 | B |
| Sep 12 | 8 | Sep 4 | C |
| Sep 13 | 9 | Sep 4 | C |
| Sep 14 | 10 | Sep 4 | C |

Group by user and this `grp` value, then take `MIN`, `MAX` and `COUNT` of the dates, and each streak is one row.

## Problems Solved

| # | Problem | Concept | Real-World Use |
|---|---------|---------|----------------|
| 1 | Find every login streak | Date minus `ROW_NUMBER` | Streak features, engagement analysis |
| 2 | Longest streak per user | Islands + `RANK` | Leaderboards, "best streak" badges |
| 3 | Users with 3+ days in a row | Islands + `HAVING` | Identifying highly engaged users |
| 4 | Find the gaps | `LAG` | Churn analysis: how long are users silent? |
| 5 | Current streak as of a date | Islands + "still alive?" check | Showing "5-day streak" in an app |
| 6 | Missing numbers in a sequence | `LEAD` | Data quality checks on IDs |
| 7 | Sessionization | `LAG` flag + running `SUM` | Web analytics sessions |

## Sample Output (from the setup data)

**Problem 1, streaks per user (selected rows):**

| user_id | streak_start | streak_end | streak_days |
|---------|--------------|------------|-------------|
| 1 | 2026-09-01 | 2026-09-05 | 5 |
| 1 | 2026-09-08 | 2026-09-09 | 2 |
| 1 | 2026-09-12 | 2026-09-14 | 3 |
| 2 | 2026-09-15 | 2026-09-18 | 4 |
| 4 | 2026-09-26 | 2026-09-30 | 5 |

**Problem 5, current streak as of 2026-09-30:**

| user_id | current_streak |
|---------|----------------|
| 1 | 0 (last login Sep 14, streak broken) |
| 2 | 1 |
| 3 | 0 |
| 4 | 5 |

**Problem 6, missing order ids:** 4 to 5, and 8 to 9 (2 missing each).

**Problem 7, sessions for user 1:** three sessions (10:00 to 10:25, 11:30 to 11:40, and a single event at 14:00).

## Key Concepts and Interview Points

**Always remove duplicates first.** If a user logs in twice on one day, that date gets two row numbers and the trick breaks. `SELECT DISTINCT user_id, login_date` first. In the data, User 1 has two logins on Sep 2 on purpose, so the bug is easy to see if you skip this step.

**Why the trick works.** Consecutive dates and consecutive row numbers move in lockstep, so their difference is constant within a streak. Say this in plain words in an interview, and walk through the table above on a whiteboard.

**Two ways to find islands.** The date-minus-row-number trick is short. The alternative is the **flag-and-running-sum** method used in Problem 7: use `LAG` to flag each row that starts a new group, then take a running `SUM` of the flags to number the groups. The second method is more general because it works for any condition (time gaps, status changes, price jumps), not just consecutive integers.

**Islands vs gaps.** They are two views of the same data. Islands answer "how long were they active?" Gaps answer "how long were they away?" For churn analysis, gaps are often more useful.

**Ties in "longest streak".** `RANK` returns every streak that ties for first place, which is why User 3 (whose streaks are all length 1) shows four rows in Problem 2. Use `ROW_NUMBER` with a tiebreaker (for example, the latest streak) when the business needs exactly one row per user.

**"Current" streaks need a reference date.** A streak is still alive if the last login was today or yesterday. Hard-code the date or pass it as a parameter so the answer is reproducible, rather than using the real current date, which changes the answer on every run.

**Gap boundaries.** A gap starts the day after the previous login (`prev_date + 1`) and ends the day before the current login (`login_date - 1`). Off-by-one errors here are the most common mistake, so check one example by hand.

**`LAG` and `LEAD`** look at the previous and next row (see Day 1). `LAG` is natural for "what happened before this?", and `LEAD` for "what comes next?".

**Dialect notes.**

| Task | PostgreSQL / DuckDB | MySQL | SQL Server |
|------|---------------------|-------|------------|
| Date minus number | `login_date - 3` | `DATE_SUB(login_date, INTERVAL 3 DAY)` | `DATEADD(day, -3, login_date)` |
| Days between | `date_b - date_a` | `DATEDIFF(date_b, date_a)` | `DATEDIFF(day, date_a, date_b)` |
| 30-minute check | `> INTERVAL '30 minutes'` | `TIMESTAMPDIFF(MINUTE, prev, cur) > 30` | `DATEDIFF(minute, prev, cur) > 30` |

**Connection to the Potato Project.** A GitHub contribution streak is a gaps-and-islands problem: each commit day is a row, an island is an unbroken run of days with commits, and a gap is a day with none. The same SQL would calculate it.

## How to Run

1. Open any SQL environment (PostgreSQL, DuckDB, or an online SQL sandbox).
2. Run the `SETUP` section first to create the three tables with sample data.
3. Run each problem one at a time, and before running it, work out the expected result by hand from the data.

## Next Steps

- Rewrite Problem 1 using the flag-and-running-sum method and compare it with the date-minus-row-number version
- Find the longest gap per user and the average gap length
- Calculate weekly streaks (consecutive weeks with at least one login)
- Reproduce the same logic in Pandas using `diff()` and `cumsum()`
