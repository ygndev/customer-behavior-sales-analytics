-- Frequency is unique invoices, not transaction lines.
SELECT customer_id,
       CAST(julianday(:snapshot) - julianday(date(MAX(invoice_date))) AS INTEGER) AS recency,
       COUNT(DISTINCT invoice_no) AS frequency,
       SUM(line_millipounds) / 1000.0 AS monetary
FROM sales WHERE customer_id IS NOT NULL
GROUP BY customer_id;
