-- Gross positive sales, not net accounting revenue. Includes anonymous buyers.
SELECT substr(invoice_date, 1, 7) AS month,
       SUM(line_millipounds) / 1000.0 AS gross_sales_gbp,
       COUNT(DISTINCT invoice_no) AS orders,
       SUM(quantity) AS units,
       COUNT(DISTINCT customer_id) AS known_customers
FROM sales
GROUP BY month ORDER BY month;
