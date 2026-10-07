-- =====================================================================
-- Potato Project Topic: SQL Joins and Set Operations
-- Syntax: standard SQL (PostgreSQL-friendly; notes below for MySQL/SQL Server)
-- Tables: departments, employees, customers, orders, support_tickets,
--         colors, sizes, newsletter_subscribers, app_users
-- =====================================================================


-- ---------------------------------------------------------------------
-- SETUP: Sample data so every query below can be run and tested
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS departments;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS support_tickets;
DROP TABLE IF EXISTS colors;
DROP TABLE IF EXISTS sizes;
DROP TABLE IF EXISTS newsletter_subscribers;
DROP TABLE IF EXISTS app_users;

CREATE TABLE departments (dept_id INT PRIMARY KEY, dept_name VARCHAR(30));
CREATE TABLE employees (
    emp_id INT PRIMARY KEY, emp_name VARCHAR(30),
    dept_id INT,          -- NULL = not assigned to a department yet
    manager_id INT        -- NULL = top boss
);
CREATE TABLE customers (customer_id INT PRIMARY KEY, customer_name VARCHAR(30), city VARCHAR(30));
CREATE TABLE orders (
    order_id INT PRIMARY KEY, customer_id INT,
    order_date DATE, amount INT, status VARCHAR(15)
);
CREATE TABLE support_tickets (ticket_id INT PRIMARY KEY, customer_id INT, issue VARCHAR(30));
CREATE TABLE colors (color VARCHAR(15));
CREATE TABLE sizes  (size  VARCHAR(5));
CREATE TABLE newsletter_subscribers (email VARCHAR(40));
CREATE TABLE app_users (email VARCHAR(40));

INSERT INTO departments VALUES (1, 'Sales'), (2, 'Tech'), (3, 'HR'), (4, 'Legal');
-- Note: Legal (4) has no employees on purpose.

INSERT INTO employees VALUES
(1, 'Asha',   1, NULL),
(2, 'Bikram', 1, 1),
(3, 'Esha',   2, 1),
(4, 'Farhan', 2, 3),
(5, 'Gita',   3, 1),
(6, 'Harsh',  NULL, 3);
-- Note: Harsh has no department on purpose.

INSERT INTO customers VALUES
(101, 'Aman',  'Kolkata'),
(102, 'Riya',  'Delhi'),
(103, 'Rahul', 'Mumbai'),
(104, 'Sneha', 'Kolkata'),
(105, 'Kabir', 'Mumbai');
-- Note: Kabir (105) has never ordered on purpose.

INSERT INTO orders VALUES
(1, 101, '2026-01-10', 4000, 'Delivered'),
(2, 101, '2026-02-15', 6000, 'Delivered'),
(3, 102, '2026-01-22', 1500, 'Cancelled'),
(4, 103, '2026-03-05', 9000, 'Delivered'),
(5, 104, '2026-03-18',  800, 'Cancelled');

INSERT INTO support_tickets VALUES
(1, 101, 'Late delivery'),
(2, 101, 'Wrong item'),
(3, 101, 'Refund query'),
(4, 103, 'Late delivery');

INSERT INTO colors VALUES ('Black'), ('White'), ('Blue');
INSERT INTO sizes  VALUES ('S'), ('M'), ('L');

INSERT INTO newsletter_subscribers VALUES
('aman@mail.com'), ('riya@mail.com'), ('rahul@mail.com'), ('priya@mail.com');
INSERT INTO app_users VALUES
('riya@mail.com'), ('rahul@mail.com'), ('sneha@mail.com'), ('rahul@mail.com');
-- Note: rahul@mail.com appears twice in app_users on purpose.


-- ---------------------------------------------------------------------
-- Problem 1: Orders with customer names
-- Concept: INNER JOIN
-- ---------------------------------------------------------------------
-- Idea: Think of two guest lists at a party. An INNER JOIN keeps only the
-- people who appear on BOTH lists. Customers with no orders disappear.
--
-- Interview note: Always join on the key that links the tables
-- (customer_id), and qualify column names with table aliases (c., o.) so
-- the query stays readable and avoids "ambiguous column" errors.
-- ---------------------------------------------------------------------
SELECT o.order_id, c.customer_name, c.city, o.amount, o.status
FROM orders o
INNER JOIN customers c ON o.customer_id = c.customer_id
ORDER BY o.order_id;


-- ---------------------------------------------------------------------
-- Problem 2: All customers, including those who never ordered
-- Concept: LEFT JOIN and the anti-join pattern
-- ---------------------------------------------------------------------
-- Idea: LEFT JOIN keeps EVERYONE from the left list and fills the right
-- side with NULL when there is no match, like a class register with a
-- blank next to students who skipped the exam.
--
-- Interview note: "Find rows with no match" is a very common question.
-- LEFT JOIN plus WHERE right_key IS NULL is the anti-join. NOT EXISTS
-- (Day 4) gives the same answer.
-- ---------------------------------------------------------------------

-- All customers with their order count (zero included)
SELECT c.customer_name, COUNT(o.order_id) AS order_count
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_name
ORDER BY order_count DESC, c.customer_name;

-- Anti-join: customers who have NEVER ordered
SELECT c.customer_name, c.city
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_id IS NULL;


-- ---------------------------------------------------------------------
-- Problem 3: Employees without a department AND departments without employees
-- Concept: FULL OUTER JOIN
-- ---------------------------------------------------------------------
-- Idea: Keep everything from both sides and mark the gaps. It is a data
-- quality check: "who is unassigned, and which departments are empty?"
--
-- Interview note: FULL OUTER JOIN is not available in MySQL. There, write
-- a LEFT JOIN, UNION it with a RIGHT JOIN, and you get the same result.
-- ---------------------------------------------------------------------
SELECT e.emp_name, d.dept_name
FROM employees e
FULL OUTER JOIN departments d ON e.dept_id = d.dept_id
WHERE e.emp_id IS NULL OR d.dept_id IS NULL;


-- ---------------------------------------------------------------------
-- Problem 4: Each employee with their manager's name
-- Concept: SELF JOIN
-- ---------------------------------------------------------------------
-- Idea: The employees table contains both workers and bosses. Join the
-- table to ITSELF using two different aliases, one playing "employee"
-- and the other playing "manager", like reading the same phone book
-- twice to match each person with their emergency contact.
--
-- Interview note: Use LEFT JOIN here, otherwise the top boss (who has no
-- manager) disappears from the result. COALESCE gives that row a label.
-- ---------------------------------------------------------------------
SELECT e.emp_name AS employee,
       COALESCE(m.emp_name, 'No manager (top boss)') AS manager
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.emp_id
ORDER BY e.emp_id;


-- ---------------------------------------------------------------------
-- Problem 5: Every colour and size combination
-- Concept: CROSS JOIN
-- ---------------------------------------------------------------------
-- Idea: A CROSS JOIN pairs every row of one table with every row of the
-- other, like a restaurant combo menu: 3 colours x 3 sizes = 9 options.
--
-- Interview note: There is no ON condition, and the row count is
-- (rows in A) x (rows in B). It is useful for building calendars, product
-- variants and test grids, but an accidental cross join on big tables
-- can freeze a database.
-- ---------------------------------------------------------------------
SELECT c.color, s.size
FROM colors c
CROSS JOIN sizes s
ORDER BY c.color, s.size;


-- ---------------------------------------------------------------------
-- Problem 6: The join trap, why totals can silently inflate
-- Concept: Fan-out (row multiplication) when joining two "many" tables
-- ---------------------------------------------------------------------
-- Idea: Customer 101 has 2 orders and 3 tickets. Joining all three
-- tables pairs every order with every ticket: 2 x 3 = 6 rows, so the
-- order amounts get counted three times. Like taking attendance in a
-- room where each person is counted once per friend they came with.
--
-- Interview note: This is one of the most common real-world SQL bugs.
-- The fix is to AGGREGATE each "many" table separately first (in CTEs),
-- then join the summaries. Always sanity-check a total against a simple
-- SUM on the original table.
-- ---------------------------------------------------------------------

-- WRONG: revenue is inflated for customers with several tickets
SELECT c.customer_name, SUM(o.amount) AS inflated_revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN support_tickets t ON c.customer_id = t.customer_id
GROUP BY c.customer_name
ORDER BY c.customer_name;

-- RIGHT: aggregate first, then join
WITH revenue AS (
    SELECT customer_id, SUM(amount) AS total_revenue
    FROM orders
    GROUP BY customer_id
),
tickets AS (
    SELECT customer_id, COUNT(*) AS ticket_count
    FROM support_tickets
    GROUP BY customer_id
)
SELECT c.customer_name,
       COALESCE(r.total_revenue, 0) AS total_revenue,
       COALESCE(t.ticket_count, 0)  AS ticket_count
FROM customers c
LEFT JOIN revenue r ON c.customer_id = r.customer_id
LEFT JOIN tickets t ON c.customer_id = t.customer_id
ORDER BY c.customer_name;


-- ---------------------------------------------------------------------
-- Problem 7: Condition in ON vs condition in WHERE (LEFT JOIN trap)
-- Concept: Where you put a filter changes the result
-- ---------------------------------------------------------------------
-- Idea: Show every customer with their DELIVERED revenue only.
--
-- Interview note: Putting the filter in WHERE runs AFTER the join and
-- throws away the NULL rows, so the LEFT JOIN quietly behaves like an
-- INNER JOIN and customers vanish. Putting the filter in ON limits which
-- orders are matched, while still keeping every customer.
-- ---------------------------------------------------------------------

-- WRONG: customers with no delivered orders disappear
SELECT c.customer_name, SUM(o.amount) AS delivered_revenue
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'Delivered'
GROUP BY c.customer_name
ORDER BY c.customer_name;

-- RIGHT: filter inside the ON clause
SELECT c.customer_name, COALESCE(SUM(o.amount), 0) AS delivered_revenue
FROM customers c
LEFT JOIN orders o
       ON c.customer_id = o.customer_id AND o.status = 'Delivered'
GROUP BY c.customer_name
ORDER BY c.customer_name;


-- ---------------------------------------------------------------------
-- Problem 8: Combining lists with set operations
-- Concept: UNION, UNION ALL, INTERSECT, EXCEPT
-- ---------------------------------------------------------------------
-- Idea: Joins add COLUMNS side by side. Set operations stack ROWS from
-- two queries on top of each other, like combining two guest lists.
--   UNION      -> everyone on either list, duplicates removed
--   UNION ALL  -> everyone on either list, duplicates kept (faster)
--   INTERSECT  -> people on BOTH lists
--   EXCEPT     -> people on the first list but NOT the second
--
-- Interview note: Both queries must return the same number of columns
-- with compatible types. UNION has to remove duplicates, so it is slower
-- than UNION ALL; use UNION ALL when duplicates are impossible or wanted.
-- Oracle uses MINUS instead of EXCEPT.
-- ---------------------------------------------------------------------

-- Everyone we can reach (duplicates removed)
SELECT email FROM newsletter_subscribers
UNION
SELECT email FROM app_users
ORDER BY email;

-- Same, but duplicates kept (note rahul appears extra times)
SELECT email FROM newsletter_subscribers
UNION ALL
SELECT email FROM app_users
ORDER BY email;

-- On BOTH lists (most engaged users)
SELECT email FROM newsletter_subscribers
INTERSECT
SELECT email FROM app_users
ORDER BY email;

-- Subscribers who have NOT installed the app (targets for an app campaign)
SELECT email FROM newsletter_subscribers
EXCEPT
SELECT email FROM app_users
ORDER BY email;
