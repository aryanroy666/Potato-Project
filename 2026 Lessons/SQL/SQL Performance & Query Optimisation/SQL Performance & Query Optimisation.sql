-- =====================================================================
-- Potato Project Topic: SQL Performance and Query Optimisation
-- Syntax: PostgreSQL (concepts apply to MySQL, SQL Server and BigQuery;
--         dialect notes given per problem)
-- =====================================================================
-- Writing a query that returns the right answer is step one. Writing one
-- that returns it FAST is what separates a junior analyst from a senior
-- one. This file covers the practical patterns that matter most in an
-- analyst role, tested against a realistic schema.


-- ---------------------------------------------------------------------
-- SETUP: A schema large enough to make performance choices visible
-- ---------------------------------------------------------------------
-- The numbers in comments show approximately how many rows each table
-- would hold in a small real-world deployment. Indexes are added
-- deliberately so the examples can show when they help and when they do
-- not, matching what the interview question "did you use an index?"
-- actually means.
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;

CREATE TABLE customers (
    customer_id   SERIAL PRIMARY KEY,
    email         VARCHAR(100) UNIQUE,
    city          VARCHAR(30),
    joined_date   DATE,
    tier          VARCHAR(10)           -- 'Gold', 'Silver', 'Bronze'
);

CREATE TABLE products (
    product_id    SERIAL PRIMARY KEY,
    product_name  VARCHAR(80),
    category      VARCHAR(30),
    unit_price    NUMERIC(10,2)
);

CREATE TABLE orders (
    order_id      SERIAL PRIMARY KEY,
    customer_id   INT REFERENCES customers,
    order_date    DATE,
    status        VARCHAR(15)           -- 'Delivered', 'Cancelled', 'Pending'
);

CREATE TABLE order_items (
    item_id       SERIAL PRIMARY KEY,
    order_id      INT REFERENCES orders,
    product_id    INT REFERENCES products,
    quantity      INT,
    line_total    NUMERIC(10,2)
);

-- Sample data (small, but the patterns apply identically at any scale)
INSERT INTO customers (email, city, joined_date, tier) VALUES
('aman@mail.com',   'Kolkata', '2024-01-15', 'Gold'),
('riya@mail.com',   'Delhi',   '2024-03-20', 'Silver'),
('rahul@mail.com',  'Mumbai',  '2024-02-10', 'Gold'),
('sneha@mail.com',  'Kolkata', '2024-06-05', 'Bronze'),
('priya@mail.com',  'Delhi',   '2025-01-12', 'Silver'),
('kabir@mail.com',  'Mumbai',  '2025-03-08', 'Bronze'),
('esha@mail.com',   'Kolkata', '2025-05-20', 'Gold'),
('farhan@mail.com', 'Delhi',   '2025-07-14', 'Silver');

INSERT INTO products (product_name, category, unit_price) VALUES
('Laptop',      'Electronics', 60000.00),
('Headphones',  'Electronics',  3000.00),
('Desk',        'Furniture',   12000.00),
('Office Chair','Furniture',    6000.00),
('Notebook',    'Stationery',    200.00),
('Pen Set',     'Stationery',    150.00),
('Tablet',      'Electronics', 25000.00),
('Monitor',     'Electronics', 18000.00);

INSERT INTO orders (customer_id, order_date, status) VALUES
(1, '2026-01-10', 'Delivered'), (1, '2026-03-15', 'Delivered'),
(1, '2026-07-20', 'Cancelled'), (2, '2026-02-05', 'Delivered'),
(2, '2026-06-18', 'Pending'),   (3, '2026-01-22', 'Delivered'),
(3, '2026-04-30', 'Delivered'), (4, '2026-03-11', 'Delivered'),
(5, '2026-05-09', 'Delivered'), (6, '2026-06-25', 'Delivered'),
(7, '2026-02-14', 'Delivered'), (7, '2026-08-01', 'Pending'),
(8, '2026-04-19', 'Cancelled'), (8, '2026-07-07', 'Delivered');

INSERT INTO order_items (order_id, product_id, quantity, line_total) VALUES
(1,1,1,60000),(1,2,2,6000),(2,3,1,12000),(3,4,1,6000),(4,7,1,25000),
(5,8,1,18000),(6,1,1,60000),(7,3,1,12000),(7,5,3,600),(8,6,5,750),
(9,2,1,3000),(10,4,2,12000),(11,8,1,18000),(12,7,1,25000),
(13,1,1,60000),(14,2,3,9000),(14,5,2,400);


-- =====================================================================
-- PART 1: INDEXES
-- =====================================================================

-- ---------------------------------------------------------------------
-- Problem 1a: Why a date filter without an index hurts on big tables
-- Concept: Sequential scan vs index scan
-- ---------------------------------------------------------------------
-- Without an index, the database reads EVERY row to check the date
-- condition, like flipping through every page of a book to find one name
-- instead of using the index at the back. EXPLAIN shows which plan the
-- planner picks.
--
-- Interview note: On a small sample table the planner may STILL choose a
-- sequential scan (it is faster than loading an index for tiny tables).
-- The patterns below are what matter when orders contains millions of rows.

EXPLAIN
SELECT order_id, order_date
FROM orders
WHERE order_date >= '2026-06-01';

-- Now create an index on the column being filtered
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);

-- The planner may now use an index scan, which reads only the matching
-- pages instead of the whole table
EXPLAIN
SELECT order_id, order_date
FROM orders
WHERE order_date >= '2026-06-01';


-- ---------------------------------------------------------------------
-- Problem 1b: A covering index skips the table entirely
-- Concept: Index-only scan
-- ---------------------------------------------------------------------
-- If every column the query NEEDS is stored in the index itself, the
-- database never even looks at the table. Like finding a flight number
-- on the departure board without walking to the gate.
CREATE INDEX IF NOT EXISTS idx_orders_date_status
    ON orders(order_date, status);

EXPLAIN
SELECT order_date, status
FROM orders
WHERE order_date >= '2026-06-01';
-- Planner can answer this without touching the orders table rows at all.


-- ---------------------------------------------------------------------
-- Problem 1c: Function on a column breaks the index
-- Concept: Non-sargable predicates
-- ---------------------------------------------------------------------
-- Wrapping a column in a function forces the database to evaluate the
-- function for every row, making the index useless. The fix is to
-- rewrite the filter so the COLUMN is compared directly.
--
-- Interview note: "Is that predicate sargable?" means "can it use an
-- index?" Wrapping the column in YEAR(), LOWER(), CAST() or arithmetic
-- makes it non-sargable. Rearranging the expression to keep the bare
-- column on the left of the comparison restores sargability.

-- BAD: index on order_date is useless here
EXPLAIN
SELECT order_id
FROM orders
WHERE EXTRACT(YEAR FROM order_date) = 2026;

-- GOOD: the column is bare, the index can be used
EXPLAIN
SELECT order_id
FROM orders
WHERE order_date BETWEEN '2026-01-01' AND '2026-12-31';


-- =====================================================================
-- PART 2: QUERY PATTERNS
-- =====================================================================

-- ---------------------------------------------------------------------
-- Problem 2: EXISTS vs COUNT(*) > 0
-- Concept: Short-circuit evaluation
-- ---------------------------------------------------------------------
-- "Does this customer have at least one order?" should stop looking as
-- soon as it finds ONE match. COUNT(*) has to count ALL matches first
-- before comparing the total, like counting every apple in a barrel
-- just to confirm there is at least one.
--
-- Interview note: EXISTS returns as soon as the first matching row is
-- found. On a customer with 1,000 orders this can be 1,000x faster.

-- SLOW on large tables: reads ALL orders, counts, then compares
SELECT customer_id
FROM customers c
WHERE (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) > 0;

-- FAST: stops at the first match
SELECT customer_id
FROM customers c
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id);


-- ---------------------------------------------------------------------
-- Problem 3: Avoid SELECT *, always name your columns
-- Concept: Projection pushdown and maintenance safety
-- ---------------------------------------------------------------------
-- SELECT * transfers every column across the network and through the
-- query plan, even ones the query does not need. On a table with a dozen
-- wide text or JSON columns this adds up. It also silently breaks if
-- someone adds or reorders a column.
--
-- Interview note: In a covering index scenario, SELECT * forces a trip
-- back to the table even when the index covers the needed columns.

-- BAD
SELECT * FROM customers WHERE city = 'Kolkata';

-- GOOD
SELECT customer_id, email, tier
FROM customers
WHERE city = 'Kolkata';


-- ---------------------------------------------------------------------
-- Problem 4: Aggregating BEFORE joining (pre-aggregation)
-- Concept: Reduce row count before the join, not after
-- ---------------------------------------------------------------------
-- Joining the raw order_items table (potentially millions of rows) to
-- customers and then aggregating is the most common "makes a slow report
-- fast" fix. Push the grouping into a subquery or CTE first, shrinking
-- the set that participates in the join. Connects to the fan-out trap
-- from Day 7 (Joins and Set Operations).
--
-- Interview note: Ask "how many rows does each side of the join have?"
-- before writing a join. If one side is already the grain you want, join
-- the aggregation of the other side, not its raw rows.

-- SLOWER: join first, aggregate after (fan-out risk too)
SELECT c.customer_id, c.email, SUM(oi.line_total) AS total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.email
ORDER BY total_spent DESC;

-- FASTER: aggregate order_items to order grain first, then join once
WITH order_totals AS (
    SELECT order_id, SUM(line_total) AS order_value
    FROM order_items
    GROUP BY order_id
),
customer_totals AS (
    SELECT o.customer_id, SUM(ot.order_value) AS total_spent
    FROM orders o
    JOIN order_totals ot ON o.order_id = ot.order_id
    GROUP BY o.customer_id
)
SELECT c.customer_id, c.email, ct.total_spent
FROM customers c
JOIN customer_totals ct ON c.customer_id = ct.customer_id
ORDER BY ct.total_spent DESC;


-- ---------------------------------------------------------------------
-- Problem 5: Window function vs self-join
-- Concept: Let the engine do one pass, not two
-- ---------------------------------------------------------------------
-- Comparing each order to the customer's own average requires either a
-- self-join (scan the table twice) or a window function (one pass). The
-- window version is almost always faster and cleaner, connecting back
-- to Day 1 (Window Functions and Aggregation).

-- SLOWER: self-join scans orders twice
SELECT o.order_id, o.customer_id, o.order_date,
       (SELECT AVG(o2.order_id) FROM orders o2
        WHERE o2.customer_id = o.customer_id) AS avg_order_count
FROM orders o;

-- FASTER and cleaner: one pass with a window function
SELECT o.order_id, o.customer_id, o.order_date,
       COUNT(*) OVER (PARTITION BY o.customer_id) AS customer_order_count,
       AVG(oi.line_total) OVER (PARTITION BY o.customer_id) AS customer_avg_item
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id;


-- =====================================================================
-- PART 3: DATA TYPE AND FILTER TRAPS
-- =====================================================================

-- ---------------------------------------------------------------------
-- Problem 6: Implicit type cast breaks an index
-- Concept: Type coercion in WHERE clauses
-- ---------------------------------------------------------------------
-- If the column is VARCHAR but you compare it to an INTEGER, some engines
-- silently cast every row in the column to the comparison type, making
-- the index useless.

-- BAD: if customer_id in another table is stored as VARCHAR, this
-- forces a cast on every row (shown as a pattern, not runnable here
-- because our IDs are already INT)
-- WHERE customer_id = '1'      -- '1' is a string; INT column gets cast

-- GOOD: match the literal type to the column type
-- WHERE customer_id = 1        -- exact match, index is usable


-- ---------------------------------------------------------------------
-- Problem 7: OR conditions and composite indexes
-- Concept: When OR prevents index use
-- ---------------------------------------------------------------------
-- An OR that spans two different columns cannot use one composite index
-- on both; the planner may fall back to a sequential scan. UNION ALL
-- turns one scan per branch into two targeted index scans, then combines.
--
-- Interview note: UNION ALL is faster than UNION here because deduplication
-- is not needed (city and email are different columns, so there are no
-- duplicates to remove). Each branch can use a separate index.

-- May cause a full scan depending on selectivity and planner:
SELECT customer_id, email FROM customers
WHERE city = 'Kolkata' OR email = 'priya@mail.com';

-- Two index scans joined with UNION ALL (each branch is sargable):
SELECT customer_id, email FROM customers WHERE city = 'Kolkata'
UNION ALL
SELECT customer_id, email FROM customers WHERE email = 'priya@mail.com';


-- ---------------------------------------------------------------------
-- Problem 8: NULL handling in aggregations and comparisons
-- Concept: NULLs disappear from COUNT, SUM and comparison
-- ---------------------------------------------------------------------
-- COUNT(*) counts every row including NULLs. COUNT(column) silently
-- skips NULLs. Comparing a column to NULL with = never returns true;
-- you must use IS NULL. Knowing this prevents "where did my rows go?"
-- bugs, which are surprisingly common.

-- How many orders per status, including a NULL status if it existed
SELECT status, COUNT(*) AS orders, COUNT(status) AS non_null_status
FROM orders
GROUP BY status;

-- Finding customers with no tier set
SELECT customer_id FROM customers WHERE tier IS NULL;
-- (none in our data, but the pattern matters)


-- ---------------------------------------------------------------------
-- SUMMARY: the five questions to ask before submitting any query
-- ---------------------------------------------------------------------
-- 1. Have I avoided SELECT * and named only the columns I need?
-- 2. Does every WHERE column have an index, and is it kept bare
--    (no functions wrapping it)?
-- 3. If I join to a large table, have I aggregated it first?
-- 4. Could EXISTS or a window function replace a subquery or self-join?
-- 5. Have I checked data types to avoid silent implicit casts?
