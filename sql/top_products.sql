-- Join transaction facts to a unique, latest-observed product description.
SELECT s.stock_code, p.description, SUM(s.quantity) AS units,
       SUM(s.line_millipounds) / 1000.0 AS gross_sales_gbp
FROM sales AS s LEFT JOIN products AS p ON s.stock_code = p.stock_code
GROUP BY s.stock_code, p.description
ORDER BY gross_sales_gbp DESC LIMIT 20;
