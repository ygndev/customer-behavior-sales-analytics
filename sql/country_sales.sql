SELECT country, SUM(line_millipounds) / 1000.0 AS gross_sales_gbp,
       COUNT(DISTINCT invoice_no) AS orders
FROM sales GROUP BY country ORDER BY gross_sales_gbp DESC;
