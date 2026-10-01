-- =====================================================================
-- Potato Project: Day 1
-- SQL Interview Problems - Window Functions & Aggregation
-- Date: Oct 1, 2026
-- Syntax: PostgreSQL
-- Table: sales(employee_id, customer_id, department, category,
--              product_name, sale_date, sale_amount)
-- =====================================================================


-- ---------------------------------------------------------------------
-- SETUP: Sample data so every query below can be run and tested
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS sales;

CREATE TABLE sales (
    sale_id       SERIAL PRIMARY KEY,
    employee_id   INT,
    customer_id   INT,
    department    VARCHAR(30),
    category      VARCHAR(30),
    product_name  VARCHAR(50),
    sale_date     DATE,
    sale_amount   NUMERIC(10, 2)
);

INSERT INTO sales (employee_id, customer_id, department, category, product_name, sale_date, sale_amount) VALUES
(1, 101, 'Retail',    'Electronics', 'Laptop',       '2026-01-05', 900.00),
(1, 102, 'Retail',    'Electronics', 'Headphones',   '2026-01-18', 150.00),
(2, 103, 'Retail',    'Furniture',   'Office Chair', '2026-02-03', 220.00),
(2, 101, 'Retail',    'Electronics', 'Laptop',       '2026-02-20', 950.00),
(3, 104, 'Online',    'Electronics', 'Smartphone',   '2026-02-11', 700.00),
(3, 105, 'Online',    'Electronics', 'Tablet',       '2026-03-02', 450.00),
(4, 102, 'Online',    'Furniture',   'Desk',         '2026-03-15', 380.00),
(4, 106, 'Online',    'Furniture',   'Bookshelf',    '2026-03-28', 190.00),
(1, 107, 'Retail',    'Electronics', 'Smartwatch',   '2026-04-09', 300.00),
(2, 103, 'Retail',    'Furniture',   'Office Chair', '2026-04-22', 220.00),
(3, 104, 'Online',    'Electronics', 'Smartphone',   '2026-05-06', 720.00),
(4, 108, 'Online',    'Furniture',   'Desk',         '2026-05-19', 400.00),
(1, 101, 'Retail',    'Electronics', 'Headphones',   '2026-06-14', 160.00),
(2, 109, 'Retail',    'Furniture',   'Sofa',         '2026-06-25', 1200.00),
(3, 105, 'Online',    'Electronics', 'Laptop',       '2026-07-08', 880.00),
(4, 110, 'Online',    'Furniture',   'Bookshelf',    '2026-07-21', 210.00),
(1, 102, 'Retail',    'Electronics', 'Tablet',       '2026-08-12', 470.00),
(2, 111, 'Retail',    'Furniture',   'Desk',         '2026-08-30', 390.00),
(3, 112, 'Online',    'Electronics', 'Smartwatch',   '2026-09-10', 310.00),
(4, 101, 'Online',    'Furniture',   'Sofa',         '2026-09-24', 1150.00);


-- ---------------------------------------------------------------------
-- Problem 1: Running Total by Department
-- ---------------------------------------------------------------------
-- Question: Show the cumulative sales within each department over time.
--
-- Idea: Think of a running total like your bank balance after every
-- transaction. PARTITION BY gives each department its own "account",
-- and ORDER BY sale_date makes the total build up day by day.
--
-- Interview note: With ORDER BY inside OVER(), the default frame is
-- RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW. Rows sharing the
-- same date are treated as one group. Use ROWS BETWEEN ... if you need
-- a strict row-by-row running total.
-- ---------------------------------------------------------------------
SELECT
    employee_id,
    department,
    sale_date,
    sale_amount,
    SUM(sale_amount) OVER (
        PARTITION BY department
        ORDER BY sale_date
    ) AS cumulative_sales
FROM sales
ORDER BY department, sale_date;


-- ---------------------------------------------------------------------
-- Problem 2: Top 3 Products per Category (with ties)
-- ---------------------------------------------------------------------
-- Question: Rank products by total sales inside each category and
-- return only the top 3 ranks.
--
-- Idea: Like a leaderboard in each sport. Each category is its own
-- league, and products compete only inside their league.
--
-- Interview note: You cannot filter on a window function in WHERE,
-- because WHERE runs before window functions are calculated. Wrap the
-- ranking in a subquery (or CTE) and filter in the outer query.
-- DENSE_RANK keeps ties without skipping numbers (1,2,2,3), while
-- RANK would skip (1,2,2,4) and ROW_NUMBER would break ties randomly.
-- ---------------------------------------------------------------------
SELECT category, product_name, total_sales, rank_in_category
FROM (
    SELECT
        category,
        product_name,
        SUM(sale_amount) AS total_sales,
        DENSE_RANK() OVER (
            PARTITION BY category
            ORDER BY SUM(sale_amount) DESC
        ) AS rank_in_category
    FROM sales
    GROUP BY category, product_name
) AS ranked
WHERE rank_in_category <= 3
ORDER BY category, rank_in_category;


-- ---------------------------------------------------------------------
-- Problem 3: Month-over-Month Revenue Growth
-- ---------------------------------------------------------------------
-- Question: Calculate the % change in revenue versus the previous month.
--
-- Idea: LAG lets each row "look back" at the row before it, like
-- comparing this month's report card with last month's.
--
-- Interview note: The first month has no previous month, so LAG returns
-- NULL and growth is NULL. NULLIF protects against divide-by-zero.
-- A CTE keeps the query readable instead of repeating LAG three times.
-- ---------------------------------------------------------------------
WITH monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', sale_date)::DATE AS month,
        SUM(sale_amount) AS revenue
    FROM sales
    GROUP BY DATE_TRUNC('month', sale_date)
)
SELECT
    month,
    revenue,
    LAG(revenue) OVER (ORDER BY month) AS prev_month_revenue,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY month))
        / NULLIF(LAG(revenue) OVER (ORDER BY month), 0) * 100,
        2
    ) AS growth_percentage
FROM monthly_revenue
ORDER BY month;


-- ---------------------------------------------------------------------
-- Problem 4: Identify Power Customers (top 10% by spend)
-- ---------------------------------------------------------------------
-- Question: Find the customers who fall in the top 10% when ranked by
-- total amount spent.
--
-- Idea: PERCENT_RANK tells you where someone stands compared to everyone
-- else, like a test score percentile. 0.9 means "better than 90% of
-- customers".
--
-- Interview note: This finds the top 10% of CUSTOMERS by spend, which is
-- different from the customers who make up 10% of total REVENUE (that
-- needs a cumulative revenue share). NTILE(10) is an alternative that
-- splits customers into 10 equal buckets.
-- ---------------------------------------------------------------------
WITH customer_revenue AS (
    SELECT
        customer_id,
        SUM(sale_amount) AS total_spent,
        PERCENT_RANK() OVER (ORDER BY SUM(sale_amount)) AS percentile
    FROM sales
    GROUP BY customer_id
)
SELECT
    customer_id,
    total_spent,
    ROUND((percentile * 100)::NUMERIC, 2) AS percentile_rank
FROM customer_revenue
WHERE percentile >= 0.9
ORDER BY total_spent DESC;


-- ---------------------------------------------------------------------
-- Problem 5: Longest Gap Between Purchases per Customer
-- ---------------------------------------------------------------------
-- Question: For each customer, find the longest number of days between
-- two consecutive purchases.
--
-- Idea: Line up each customer's purchases in date order, then for every
-- purchase peek at the previous one using LAG and subtract the dates.
-- A long gap can signal a customer who is drifting away (churn risk).
--
-- Interview note: In PostgreSQL, date - date returns an integer number
-- of days. Customers with only one purchase have no gap, so they are
-- excluded by the days_gap IS NOT NULL filter.
-- ---------------------------------------------------------------------
SELECT
    customer_id,
    MAX(days_gap) AS longest_gap_days
FROM (
    SELECT
        customer_id,
        sale_date,
        sale_date - LAG(sale_date) OVER (
            PARTITION BY customer_id
            ORDER BY sale_date
        ) AS days_gap
    FROM sales
) AS gaps
WHERE days_gap IS NOT NULL
GROUP BY customer_id
ORDER BY longest_gap_days DESC;
