-- =====================================================================
-- Potato Project Topic: SQL CTEs and Subqueries
-- Syntax: standard SQL (works in PostgreSQL; also runs in MySQL 8+ and SQLite)
-- Tables: employees, customers, orders
-- =====================================================================


-- ---------------------------------------------------------------------
-- SETUP: Sample data so every query below can be run and tested
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS employees;

CREATE TABLE employees (
    emp_id      INT PRIMARY KEY,
    emp_name    VARCHAR(50),
    department  VARCHAR(30),
    salary      INT,
    manager_id  INT              -- NULL for the top boss
);

CREATE TABLE customers (
    customer_id    INT PRIMARY KEY,
    customer_name  VARCHAR(50),
    city           VARCHAR(30)
);

CREATE TABLE orders (
    order_id     INT PRIMARY KEY,
    customer_id  INT,
    order_date   DATE,
    amount       INT
);

INSERT INTO employees (emp_id, emp_name, department, salary, manager_id) VALUES
(1, 'Asha',   'Management', 150000, NULL),
(2, 'Bikram', 'Sales',       90000, 1),
(3, 'Chitra', 'Sales',       70000, 2),
(4, 'Dev',    'Sales',       70000, 2),
(5, 'Esha',   'Tech',       120000, 1),
(6, 'Farhan', 'Tech',        95000, 5),
(7, 'Gita',   'Tech',        85000, 6),
(8, 'Harsh',  'Tech',        60000, 6),
(9, 'Ira',    'HR',          65000, 1),
(10,'Jay',    'HR',          50000, 9);

INSERT INTO customers (customer_id, customer_name, city) VALUES
(101, 'Aman',  'Kolkata'),
(102, 'Riya',  'Delhi'),
(103, 'Rahul', 'Mumbai'),
(104, 'Sneha', 'Kolkata'),
(105, 'Priya', 'Delhi'),
(106, 'Kabir', 'Mumbai');

INSERT INTO orders (order_id, customer_id, order_date, amount) VALUES
(1, 101, '2026-01-10', 4000),
(2, 101, '2026-02-15', 6500),
(3, 102, '2026-01-22', 1200),
(4, 103, '2026-03-05', 9000),
(5, 103, '2026-03-28', 7000),
(6, 103, '2026-04-12', 5500),
(7, 104, '2026-02-02', 800),
(8, 105, '2026-04-20', 3000),
(9, 105, '2026-05-01', 2500);
-- Note: customer 106 (Kabir) has never placed an order. This is on purpose.


-- ---------------------------------------------------------------------
-- Problem 1: Employees earning more than the company average
-- Concept: Scalar subquery (a subquery that returns ONE value)
-- ---------------------------------------------------------------------
-- Idea: Like asking "who scored above the class average?". First you
-- need the average, then you compare everyone against it. The inner
-- query runs once and hands a single number to the outer query.
--
-- Interview note: A scalar subquery must return exactly one row and one
-- column, or the database throws an error.
-- ---------------------------------------------------------------------
SELECT emp_name, department, salary
FROM employees
WHERE salary > (SELECT AVG(salary) FROM employees)
ORDER BY salary DESC;


-- ---------------------------------------------------------------------
-- Problem 2: Employees earning more than their own department's average
-- Concept: Correlated subquery vs CTE (two ways to solve the same thing)
-- ---------------------------------------------------------------------
-- Idea: Now the benchmark changes per person: a Tech employee is compared
-- with Tech, a Sales employee with Sales. A correlated subquery re-runs
-- for every row, like a teacher checking each student against THEIR OWN
-- class average.
--
-- Interview note: Correlated subqueries are easy to read but can be slow
-- on big tables because they run once per outer row. The CTE version
-- calculates each department average once and joins to it, which is
-- usually faster and easier to debug. Know both and explain the trade-off.
-- ---------------------------------------------------------------------

-- Version A: correlated subquery
SELECT e.emp_name, e.department, e.salary
FROM employees e
WHERE e.salary > (
    SELECT AVG(salary)
    FROM employees
    WHERE department = e.department      -- this line "correlates" the two queries
)
ORDER BY e.department, e.salary DESC;

-- Version B: CTE + join (same result)
WITH dept_avg AS (
    SELECT department, AVG(salary) AS avg_salary
    FROM employees
    GROUP BY department
)
SELECT e.emp_name, e.department, e.salary, ROUND(d.avg_salary, 0) AS dept_avg_salary
FROM employees e
JOIN dept_avg d ON e.department = d.department
WHERE e.salary > d.avg_salary
ORDER BY e.department, e.salary DESC;


-- ---------------------------------------------------------------------
-- Problem 3: Customers who ordered vs customers who never ordered
-- Concept: EXISTS / NOT EXISTS
-- ---------------------------------------------------------------------
-- Idea: EXISTS asks "is there at least one matching row?" and stops
-- looking as soon as it finds one, like checking whether anyone is home
-- by ringing the bell once rather than counting everybody inside.
--
-- Interview note: Prefer NOT EXISTS over NOT IN. If the subquery returns
-- even one NULL, NOT IN returns no rows at all (because of how NULL
-- comparisons work). NOT EXISTS has no such trap. This is a classic
-- interview question.
-- ---------------------------------------------------------------------

-- Customers who placed at least one order
SELECT c.customer_name, c.city
FROM customers c
WHERE EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id
);

-- Customers who NEVER placed an order (the inactive ones)
SELECT c.customer_name, c.city
FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id
);


-- ---------------------------------------------------------------------
-- Problem 4: Segment customers by total spend (chained CTEs)
-- Concept: Multiple CTEs, each building on the previous one
-- ---------------------------------------------------------------------
-- Idea: Think of an assembly line. Station 1 totals each customer's
-- spend. Station 2 labels them High, Medium or Low. Each station does
-- one job, so the query reads top to bottom like a recipe.
--
-- Interview note: Chained CTEs replace deeply nested subqueries, which
-- are hard to read and debug. A LEFT JOIN keeps customers with zero
-- orders, and COALESCE turns their NULL total into 0.
-- ---------------------------------------------------------------------
WITH customer_spend AS (
    SELECT
        c.customer_id,
        c.customer_name,
        COALESCE(SUM(o.amount), 0) AS total_spent,
        COUNT(o.order_id)          AS order_count
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.customer_name
),
segmented AS (
    SELECT
        customer_name,
        total_spent,
        order_count,
        CASE
            WHEN total_spent >= 10000 THEN 'High'
            WHEN total_spent >= 3000  THEN 'Medium'
            ELSE 'Low'
        END AS segment
    FROM customer_spend
)
SELECT customer_name, total_spent, order_count, segment
FROM segmented
ORDER BY total_spent DESC;


-- ---------------------------------------------------------------------
-- Problem 5: Highest-paid employee in each department
-- Concept: CTE + window function (connects to Day 1)
-- ---------------------------------------------------------------------
-- Idea: Rank employees inside each department, then keep only rank 1.
-- You cannot filter on a window function in the same query's WHERE, so
-- the CTE does the ranking and the outer query does the filtering.
--
-- Interview note: RANK keeps ties (if two Sales employees both earned the
-- top salary, both would be returned), while ROW_NUMBER forces exactly
-- one winner per group. Pick the one that matches what the business asked.
-- ---------------------------------------------------------------------
WITH ranked AS (
    SELECT
        emp_name,
        department,
        salary,
        RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS salary_rank
    FROM employees
)
SELECT department, emp_name, salary
FROM ranked
WHERE salary_rank = 1
ORDER BY department;


-- ---------------------------------------------------------------------
-- Problem 6: Company hierarchy (who reports to whom)
-- Concept: Recursive CTE
-- ---------------------------------------------------------------------
-- Idea: A recursive CTE is like climbing a family tree. Start with the
-- top person (the anchor), then repeatedly find everyone who reports to
-- the people you already have (the recursive step), until nobody is left.
--
-- Interview note: Every recursive CTE has two parts joined by UNION ALL:
-- the anchor (starting row) and the recursive member (which refers back
-- to the CTE itself). It needs a stopping condition, and here it stops
-- naturally when no one reports to the last level. Typical uses:
-- org charts, category trees, bill of materials.
-- ---------------------------------------------------------------------
WITH RECURSIVE org_chart AS (
    -- Anchor: the top boss has no manager
    SELECT emp_id, emp_name, manager_id, 1 AS level, emp_name AS reporting_path
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive step: find people who report to someone already found
    SELECT e.emp_id, e.emp_name, e.manager_id, oc.level + 1,
           oc.reporting_path || ' > ' || e.emp_name
    FROM employees e
    JOIN org_chart oc ON e.manager_id = oc.emp_id
)
SELECT level, emp_name, reporting_path
FROM org_chart
ORDER BY level, emp_name;
