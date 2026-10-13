-- =====================================================================
-- Potato Project Topic: SQL Consecutive Streaks (Gaps & Islands)
-- Syntax: PostgreSQL (also runs unchanged in DuckDB; notes for other dialects)
-- Tables: logins, orders, events
-- =====================================================================
-- The "gaps and islands" family of problems asks:
--   ISLANDS = unbroken runs of consecutive values (a 7-day login streak)
--   GAPS    = the holes between those runs (the days someone was missing)
-- It is a favourite SQL interview topic, and it is exactly how apps
-- calculate a "day streak", or how GitHub counts a commit streak.


-- ---------------------------------------------------------------------
-- SETUP: Sample data so every query below can be run and tested
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS logins;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS events;

CREATE TABLE logins (user_id INT, login_date DATE);
CREATE TABLE orders (order_id INT);
CREATE TABLE events (user_id INT, event_time TIMESTAMP);

INSERT INTO logins VALUES
-- User 1: three streaks (5 days, 2 days, 3 days). Sep 2 appears twice on purpose.
(1, '2026-09-01'), (1, '2026-09-02'), (1, '2026-09-02'), (1, '2026-09-03'),
(1, '2026-09-04'), (1, '2026-09-05'),
(1, '2026-09-08'), (1, '2026-09-09'),
(1, '2026-09-12'), (1, '2026-09-13'), (1, '2026-09-14'),
-- User 2: streaks of 2 and 4 days, then a single login on the last day
(2, '2026-09-10'), (2, '2026-09-11'),
(2, '2026-09-15'), (2, '2026-09-16'), (2, '2026-09-17'), (2, '2026-09-18'),
(2, '2026-09-30'),
-- User 3: logs in every other day, so no streak is longer than 1
(3, '2026-09-01'), (3, '2026-09-03'), (3, '2026-09-05'), (3, '2026-09-07'),
-- User 4: a 5-day streak that is still running on Sep 30
(4, '2026-09-26'), (4, '2026-09-27'), (4, '2026-09-28'),
(4, '2026-09-29'), (4, '2026-09-30');

-- Order ids with holes (4, 5, 8 and 9 are missing)
INSERT INTO orders VALUES (1), (2), (3), (6), (7), (10);

-- Clickstream for user 1: a pause longer than 30 minutes starts a new session
INSERT INTO events VALUES
(1, '2026-09-30 10:00:00'), (1, '2026-09-30 10:10:00'), (1, '2026-09-30 10:25:00'),
(1, '2026-09-30 11:30:00'), (1, '2026-09-30 11:40:00'),
(1, '2026-09-30 14:00:00'),
(2, '2026-09-30 09:00:00'), (2, '2026-09-30 09:20:00');


-- ---------------------------------------------------------------------
-- Problem 1: Find every login streak (the "islands")
-- Concept: date minus ROW_NUMBER trick
-- ---------------------------------------------------------------------
-- Idea: Walk along a staircase. Dates go up by 1 each day and the row
-- number goes up by 1 each row, so while a streak continues, (date - row
-- number) stays the SAME value. The moment a day is skipped, the date
-- jumps but the row number does not, so the value changes. Rows sharing
-- the same value belong to the same streak.
--
-- Interview note: Remove duplicates FIRST (SELECT DISTINCT). Two logins
-- on the same day would give two row numbers for one date and break the
-- trick. Step through the middle CTE and look at the grp column to see it.
-- ---------------------------------------------------------------------
WITH daily AS (
    SELECT DISTINCT user_id, login_date
    FROM logins
),
numbered AS (
    SELECT
        user_id,
        login_date,
        login_date - CAST(ROW_NUMBER() OVER (
            PARTITION BY user_id ORDER BY login_date
        ) AS INT) AS grp                      -- same grp = same streak
    FROM daily
)
SELECT
    user_id,
    MIN(login_date) AS streak_start,
    MAX(login_date) AS streak_end,
    COUNT(*)        AS streak_days
FROM numbered
GROUP BY user_id, grp
ORDER BY user_id, streak_start;


-- ---------------------------------------------------------------------
-- Problem 2: Longest streak per user
-- Concept: islands + RANK
-- ---------------------------------------------------------------------
-- Idea: Reuse Problem 1 as a CTE, then rank each user's streaks by length
-- and keep rank 1. Chaining CTEs keeps each step simple (Day 4).
--
-- Interview note: RANK keeps ties (two equally long streaks both show up).
-- Use ROW_NUMBER if the business wants exactly one row per user.
-- ---------------------------------------------------------------------
WITH daily AS (
    SELECT DISTINCT user_id, login_date FROM logins
),
numbered AS (
    SELECT user_id, login_date,
           login_date - CAST(ROW_NUMBER() OVER (
               PARTITION BY user_id ORDER BY login_date) AS INT) AS grp
    FROM daily
),
streaks AS (
    SELECT user_id, MIN(login_date) AS streak_start,
           MAX(login_date) AS streak_end, COUNT(*) AS streak_days
    FROM numbered
    GROUP BY user_id, grp
),
ranked AS (
    SELECT *, RANK() OVER (PARTITION BY user_id ORDER BY streak_days DESC) AS rnk
    FROM streaks
)
SELECT user_id, streak_start, streak_end, streak_days AS longest_streak
FROM ranked
WHERE rnk = 1
ORDER BY user_id;


-- ---------------------------------------------------------------------
-- Problem 3: Users who logged in 3 or more days in a row at least once
-- Concept: filter islands with HAVING
-- ---------------------------------------------------------------------
-- Idea: Count the days in each island and keep only the long ones, like
-- finding students who attended class 3 days running.
--
-- Interview note: This is the standard answer to "find users with N
-- consecutive days of activity". Change the 3 to any number.
-- ---------------------------------------------------------------------
WITH daily AS (
    SELECT DISTINCT user_id, login_date FROM logins
),
numbered AS (
    SELECT user_id, login_date,
           login_date - CAST(ROW_NUMBER() OVER (
               PARTITION BY user_id ORDER BY login_date) AS INT) AS grp
    FROM daily
)
SELECT DISTINCT user_id
FROM (
    SELECT user_id, grp
    FROM numbered
    GROUP BY user_id, grp
    HAVING COUNT(*) >= 3
) AS long_streaks
ORDER BY user_id;


-- ---------------------------------------------------------------------
-- Problem 4: Find the gaps (days a user was missing)
-- Concept: LAG to compare each login with the previous one
-- ---------------------------------------------------------------------
-- Idea: If the previous login was more than 1 day ago, the days in
-- between are a gap. The gap starts the day after the previous login
-- and ends the day before the current one.
--
-- Interview note: Islands and gaps are two views of the same data. Gaps
-- are useful for churn analysis: "how long are users silent before they
-- come back?"
-- ---------------------------------------------------------------------
WITH daily AS (
    SELECT DISTINCT user_id, login_date FROM logins
),
with_prev AS (
    SELECT user_id, login_date,
           LAG(login_date) OVER (PARTITION BY user_id ORDER BY login_date) AS prev_date
    FROM daily
)
SELECT
    user_id,
    prev_date + 1               AS gap_start,
    login_date - 1              AS gap_end,
    login_date - prev_date - 1  AS missing_days
FROM with_prev
WHERE login_date - prev_date > 1
ORDER BY user_id, gap_start;


-- ---------------------------------------------------------------------
-- Problem 5: Current streak as of a given date
-- Concept: islands filtered by "is it still alive?"
-- ---------------------------------------------------------------------
-- Idea: A streak is still active if the last login was today or
-- yesterday (the user still has today to extend it). Anything older is
-- already broken, so the current streak is 0.
--
-- Interview note: Hard-code the "as of" date in the query (or pass it as
-- a parameter) so results are reproducible. Using the real current date
-- makes the answer change every time you run it.
-- ---------------------------------------------------------------------
WITH daily AS (
    SELECT DISTINCT user_id, login_date FROM logins
),
numbered AS (
    SELECT user_id, login_date,
           login_date - CAST(ROW_NUMBER() OVER (
               PARTITION BY user_id ORDER BY login_date) AS INT) AS grp
    FROM daily
),
streaks AS (
    SELECT user_id, MAX(login_date) AS streak_end, COUNT(*) AS streak_days
    FROM numbered
    GROUP BY user_id, grp
)
SELECT u.user_id,
       COALESCE(MAX(CASE WHEN s.streak_end >= DATE '2026-09-30' - 1
                         THEN s.streak_days END), 0) AS current_streak
FROM (SELECT DISTINCT user_id FROM logins) u
LEFT JOIN streaks s ON u.user_id = s.user_id
GROUP BY u.user_id
ORDER BY u.user_id;


-- ---------------------------------------------------------------------
-- Problem 6: Missing numbers in a sequence (gaps in IDs)
-- Concept: LEAD to peek at the next value
-- ---------------------------------------------------------------------
-- Idea: Order ids are supposed to run 1, 2, 3, 4... If the next id is
-- more than 1 higher than the current one, the numbers in between are
-- missing, like noticing page numbers jump from 3 to 6 in a book.
--
-- Interview note: Missing ids can mean deleted rows, failed inserts or a
-- data pipeline losing records. Finding them is a basic data quality check.
-- ---------------------------------------------------------------------
SELECT
    order_id + 1           AS missing_from,
    next_id - 1            AS missing_to,
    next_id - order_id - 1 AS how_many_missing
FROM (
    SELECT order_id,
           LEAD(order_id) OVER (ORDER BY order_id) AS next_id
    FROM orders
) AS t
WHERE next_id - order_id > 1
ORDER BY missing_from;


-- ---------------------------------------------------------------------
-- Problem 7: Sessionization (group events into sessions)
-- Concept: LAG flag + running SUM
-- ---------------------------------------------------------------------
-- Idea: A new session begins whenever the user was inactive for more
-- than 30 minutes. Step 1 flags those "new session" rows with 1. Step 2
-- adds up the flags as a running total, which numbers the sessions, like
-- turning a page every time there is a long pause.
--
-- Interview note: "Flag the start of a group, then running-SUM the flags"
-- is a general recipe for any grouping defined by a condition, not just
-- time. In MySQL, use TIMESTAMPDIFF(MINUTE, prev, current) > 30 instead
-- of INTERVAL arithmetic.
-- ---------------------------------------------------------------------
WITH flagged AS (
    SELECT
        user_id,
        event_time,
        CASE
            WHEN event_time - LAG(event_time) OVER (
                     PARTITION BY user_id ORDER BY event_time
                 ) > INTERVAL '30 minutes'
            THEN 1 ELSE 0
        END AS new_session
    FROM events
),
numbered AS (
    SELECT
        user_id,
        event_time,
        SUM(new_session) OVER (
            PARTITION BY user_id ORDER BY event_time
        ) + 1 AS session_id
    FROM flagged
)
SELECT
    user_id,
    session_id,
    MIN(event_time)                 AS session_start,
    MAX(event_time)                 AS session_end,
    COUNT(*)                        AS events_in_session,
    MAX(event_time) - MIN(event_time) AS session_length
FROM numbered
GROUP BY user_id, session_id
ORDER BY user_id, session_id;
