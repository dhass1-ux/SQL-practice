-- =============================================================
-- solutions.sql
-- One possible answer for each question in exercises/questions.md.
-- Try each question yourself first. There is usually more than one
-- correct way to write a query; if your numbers match, you got it.
-- The dataset's "today" is 2026-11-01.
-- =============================================================

USE dealer_practice;

-- -------------------------------------------------------------
-- Level 1: SELECT, WHERE, ORDER BY
-- -------------------------------------------------------------

-- Q1. Rooftops in the Rochester market
SELECT rooftop_id, name, brand
FROM rooftops
WHERE market = 'Rochester';

-- Q2. Used vehicles in stock at Genesee Ford (rooftop 5), oldest first
SELECT vin, model_year, make, model, stock_date
FROM vehicles
WHERE rooftop_id = 5
  AND new_used = 'Used'
  AND status = 'in_stock'
ORDER BY stock_date;

-- Q3. In-stock vehicles listed over $60,000, most expensive first
SELECT vin, make, model, list_price
FROM vehicles
WHERE status = 'in_stock'
  AND list_price > 60000
ORDER BY list_price DESC;

-- Q4. Customers with no email on file
SELECT COUNT(*) AS customers_without_email
FROM customers
WHERE email IS NULL;

-- -------------------------------------------------------------
-- Level 2: COUNT, SUM, AVG, GROUP BY, HAVING
-- -------------------------------------------------------------

-- Q5. Units in stock by rooftop and new/used
SELECT rooftop_id, new_used, COUNT(*) AS units_in_stock
FROM vehicles
WHERE status = 'in_stock'
GROUP BY rooftop_id, new_used
ORDER BY rooftop_id, new_used;

-- Q6. Deal count and average front and back gross by deal type
SELECT deal_type,
       COUNT(*)                   AS deals,
       ROUND(AVG(front_gross), 0) AS avg_front_gross,
       ROUND(AVG(back_gross), 0)  AS avg_back_gross
FROM deals
GROUP BY deal_type;

-- Q7. Units sold per month in 2026
SELECT DATE_FORMAT(sold_date, '%Y-%m') AS sold_month,
       COUNT(*) AS units_sold
FROM deals
WHERE sold_date >= '2026-01-01' AND sold_date < '2027-01-01'
GROUP BY sold_month
ORDER BY sold_month;

-- Q8. Salespeople with 25 or more units in 2025
SELECT rooftop_id, salesperson, COUNT(*) AS units
FROM deals
WHERE YEAR(sold_date) = 2025
GROUP BY rooftop_id, salesperson
HAVING COUNT(*) >= 25
ORDER BY units DESC;

-- -------------------------------------------------------------
-- Level 3: JOINs
-- -------------------------------------------------------------

-- Q9. Units sold and total front gross by rooftop name, 2026
SELECT r.name,
       COUNT(*)            AS units_sold,
       SUM(d.front_gross)  AS total_front_gross
FROM deals d
JOIN rooftops r ON r.rooftop_id = d.rooftop_id
WHERE d.sold_date >= '2026-01-01'
GROUP BY r.name
ORDER BY total_front_gross DESC;

-- Q10. Aged used inventory: in stock more than 60 days
SELECT r.name AS rooftop,
       v.vin, v.model_year, v.make, v.model,
       DATEDIFF('2026-11-01', v.stock_date) AS days_in_stock
FROM vehicles v
JOIN rooftops r ON r.rooftop_id = v.rooftop_id
WHERE v.status = 'in_stock'
  AND v.new_used = 'Used'
  AND DATEDIFF('2026-11-01', v.stock_date) > 60
ORDER BY days_in_stock DESC;

-- Q11. October 2026 deals with customer, vehicle and rooftop
SELECT d.deal_id, d.sold_date,
       CONCAT(c.first_name, ' ', c.last_name) AS customer,
       CONCAT(v.model_year, ' ', v.make, ' ', v.model) AS vehicle,
       r.name AS rooftop,
       d.sale_price
FROM deals d
JOIN customers c ON c.customer_id = d.customer_id
JOIN vehicles  v ON v.vin         = d.vin
JOIN rooftops  r ON r.rooftop_id  = d.rooftop_id
WHERE d.sold_date >= '2026-10-01' AND d.sold_date < '2026-11-01'
ORDER BY d.sold_date, d.deal_id;

-- Q12. Customers who have never bought a vehicle
SELECT c.customer_id, c.first_name, c.last_name, c.created_date
FROM customers c
LEFT JOIN deals d ON d.customer_id = c.customer_id
WHERE d.deal_id IS NULL
ORDER BY c.created_date;

-- -------------------------------------------------------------
-- Level 4: business questions (subqueries and CTEs)
-- -------------------------------------------------------------

-- Q13. Service defection: bought before 2025-11-01, no RO since then
WITH buyers AS (
    SELECT DISTINCT customer_id
    FROM deals
    WHERE sold_date < '2025-11-01'
),
recent_service AS (
    SELECT DISTINCT customer_id
    FROM service_ros
    WHERE ro_date >= '2025-11-01'
)
SELECT c.customer_id, c.first_name, c.last_name, c.phone, c.email
FROM buyers b
JOIN customers c ON c.customer_id = b.customer_id
LEFT JOIN recent_service s ON s.customer_id = b.customer_id
WHERE s.customer_id IS NULL
ORDER BY c.last_name, c.first_name;

-- Q14. 2026 customer-pay service revenue by rooftop and share of the group total
SELECT r.name,
       SUM(s.labor_total + s.parts_total) AS cp_revenue,
       ROUND(100 * SUM(s.labor_total + s.parts_total)
             / SUM(SUM(s.labor_total + s.parts_total)) OVER (), 1) AS pct_of_group
FROM service_ros s
JOIN rooftops r ON r.rooftop_id = s.rooftop_id
WHERE s.pay_type = 'Customer'
  AND s.ro_date >= '2026-01-01'
GROUP BY r.name
ORDER BY cp_revenue DESC;

-- Q15. Repeat buyers: customers with 2 or more deals
SELECT c.customer_id, c.first_name, c.last_name, COUNT(*) AS vehicles_bought
FROM deals d
JOIN customers c ON c.customer_id = d.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name
HAVING COUNT(*) >= 2
ORDER BY vehicles_bought DESC, c.customer_id;

-- Q16. Days supply by rooftop (in-stock units / average daily sales, last 30 days)
WITH stock AS (
    SELECT rooftop_id, COUNT(*) AS in_stock
    FROM vehicles
    WHERE status = 'in_stock'
    GROUP BY rooftop_id
),
pace AS (
    SELECT rooftop_id, COUNT(*) / 30 AS sold_per_day
    FROM deals
    WHERE sold_date >= '2026-10-02' AND sold_date < '2026-11-01'
    GROUP BY rooftop_id
)
SELECT r.name, st.in_stock, ROUND(p.sold_per_day * 30) AS sold_last_30,
       ROUND(st.in_stock / p.sold_per_day, 0) AS days_supply
FROM rooftops r
JOIN stock st ON st.rooftop_id = r.rooftop_id
JOIN pace  p  ON p.rooftop_id  = r.rooftop_id
ORDER BY days_supply DESC;

-- -------------------------------------------------------------
-- Level 5: window functions and data cleanup
-- -------------------------------------------------------------

-- Q17. Rank rooftops by 2026 total gross (front + back) within each market
SELECT r.market, r.name,
       SUM(d.front_gross + d.back_gross) AS total_gross,
       RANK() OVER (PARTITION BY r.market
                    ORDER BY SUM(d.front_gross + d.back_gross) DESC) AS market_rank
FROM deals d
JOIN rooftops r ON r.rooftop_id = d.rooftop_id
WHERE d.sold_date >= '2026-01-01'
GROUP BY r.market, r.name
ORDER BY r.market, market_rank;

-- Q18. Days between each purchase and the same customer's previous purchase
SELECT customer_id, deal_id, sold_date, previous_purchase,
       DATEDIFF(sold_date, previous_purchase) AS days_since_last
FROM (
    SELECT customer_id, deal_id, sold_date,
           LAG(sold_date) OVER (PARTITION BY customer_id ORDER BY sold_date) AS previous_purchase
    FROM deals
) t
WHERE previous_purchase IS NOT NULL
ORDER BY days_since_last;

-- Q19. Duplicate customers: same email, ignoring upper/lower case
SELECT LOWER(email) AS email_clean,
       COUNT(*) AS records,
       GROUP_CONCAT(customer_id ORDER BY customer_id) AS customer_ids
FROM customers
WHERE email IS NOT NULL
GROUP BY LOWER(email)
HAVING COUNT(*) > 1
ORDER BY email_clean;

-- Q20. Duplicate customers: same phone once formatting is stripped
WITH clean AS (
    SELECT customer_id, first_name, last_name, phone,
           REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(phone,
               '(', ''), ')', ''), '-', ''), ' ', ''), '.', '') AS phone_digits
    FROM customers
    WHERE phone IS NOT NULL
)
SELECT a.customer_id AS id_1, a.first_name AS first_1, a.phone AS phone_1,
       b.customer_id AS id_2, b.first_name AS first_2, b.phone AS phone_2,
       a.last_name
FROM clean a
JOIN clean b
  ON a.phone_digits = b.phone_digits
 AND a.customer_id < b.customer_id     -- each pair once, never a row with itself
ORDER BY a.customer_id;
