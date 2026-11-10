# Customer Behavior & Sales Analytics

**Python · SQL (SQLite) · Pandas · Matplotlib · RFM**

An end-to-end analytics portfolio project that turns real retail transactions into reproducible sales reports and customer segments. It demonstrates data cleaning, SQL joins and aggregation, exploratory analysis, and visual reporting.

## Business questions

1. How do monthly gross sales, order counts, and customer counts change over time?
2. Which customers are high-value, loyal, or candidates for re-engagement?
3. Which countries and product codes contribute the most to gross sales?
4. How can observed monthly and weekly patterns inform operational planning?

## Data source and attribution

[UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online-retail), Chen, D. (2015), DOI: [10.24432/C5BW33](https://doi.org/10.24432/C5BW33), licensed under **CC BY 4.0**.

The dataset contains **541,909 transaction lines** from a UK-based online retailer, covering **1 December 2010 to 9 December 2011**. Prices are in **GBP**. These are real historical transactions, not synthetic data.

The pipeline downloads the original Excel file directly from UCI. `data/source_manifest.json` records the source URL and the reviewed file's SHA-256 checksum. A checksum mismatch stops subsequent runs. Internet access is required for the initial download; the raw dataset is excluded from Git.

## Quick start

Validated with **Python 3.12**. Open a terminal in the repository root.

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe src/pipeline.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

### macOS / Linux

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python src/pipeline.py
.venv/bin/python -m unittest discover -s tests -v
```

The first run downloads approximately 23 MB. Reading the Excel file may take a few minutes. Subsequent runs reuse the cached raw file and regenerate the outputs. Add `--offline` to the pipeline command to require a cached dataset without downloading it.

`requirements.txt` lists direct dependencies; `requirements-lock.txt` pins all package versions from the validated environment. SQLite is included with Python.

## Analysis workflow

`UCI XLSX → Pandas cleaning → SQLite sales + products → SQL reports → Pandas RFM → CSV + PNG + quality report`

- **Transaction grain:** Each row is an invoice line. Orders are counted with `COUNT(DISTINCT invoice_no)`.
- **Duplicates:** Exact duplicate rows are removed. Because the source has no unique invoice-line identifier, this is an explicit assumption that may also remove genuine repeated lines.
- **Exclusion waterfall:** Invalid required fields, cancellation codes, nonpositive quantities, and nonpositive prices are removed in sequence. `reports/quality_report.json` records mutually exclusive exclusion counts.
- **Missing customer IDs:** Valid positive sales without a customer ID remain in overall sales analysis but are excluded from RFM. A missing product description alone does not exclude a sale.
- **Currency precision:** Monetary amounts are aggregated as integers in units of 0.001 GBP to preserve source precision. Narrative summaries display two decimal places.
- **Sales definition:** Cancellation and negative transaction lines are excluded; returns are not matched to original invoices. **Reported amounts are cleaned gross positive sales, not net revenue or profit.** Shipping and other non-product codes are retained.
- **SQL joins:** The `products` table contains the latest observed non-null description for each stock code. A `LEFT JOIN` supports product reporting, with a check that the join does not multiply transaction rows. This is not a historical product dimension.
- **Reproducible snapshot:** RFM uses the day after the last retained transaction date rather than the current date.

## Customer segmentation: RFM

- **Recency:** Days between the snapshot date and the customer's most recent positive purchase.
- **Frequency:** Number of distinct positive invoices.
- **Monetary:** Total positive purchase amount.

All available purchase history is used. Each metric receives a score from 1 to 5 using average percentile ranks. Equal values receive equal scores; lower recency receives a higher score. Ties mean score groups may differ in size from exact quintiles.

The first matching rule determines the segment:

| Segment | Rule |
|---|---|
| Champions | R ≥ 4, F ≥ 4, M ≥ 4 |
| At risk high value | R ≤ 2 and (F ≥ 4 or M ≥ 4) |
| Recent low frequency | R ≥ 4, F ≤ 2 |
| Loyal | F ≥ 4 |
| Hibernating | R ≤ 2 |
| Developing | All remaining customers |

This is explainable, rule-based segmentation, not a trained machine learning model or a churn prediction system. Segment labels represent business hypotheses rather than evidence of campaign effectiveness.

## Results

The validated run produced:

| Metric | Result |
|---|---:|
| Retained positive sales lines | 524,878 |
| Distinct orders | 19,960 |
| Identified customers | 4,338 |
| Gross positive sales | £10,642,110.80 |
| Share of sales linked to identified customers | 83.51% |
| Highest-sales complete month | November 2011: £1,503,866.78 |
| Average / median order value | £533.17 / £303.30 |

The **Champions** segment contains **911 customers** and accounts for **63.87%** of gross positive sales among identified customers. The **At risk high value** segment contains **406 customers**, suggesting a group to investigate for re-engagement experiments. Its historical sales are not an estimate of future lost or recoverable revenue.

All analysis tables are available in `reports/tables/`. A [detailed findings report in Turkish](reports/findings_tr.md) accompanies the results.

![Monthly gross positive sales](reports/figures/monthly_sales.png)

![Gross positive sales by RFM segment](reports/figures/segments.png)

![Average sales by observed trading weekday](reports/figures/weekday_sales.png)

### Interpretation and limitations

December 2011 covers only **1–9 December**, so its month-over-month growth is not calculated. Approximately one annual cycle is insufficient to establish persistent seasonality. The weekday chart averages only dates with observed sales; unobserved dates are not assumed to have zero sales.

Missing customer IDs, wholesale buyers, and unusually large orders limit generalization. The project does not establish causality, predictive accuracy, or campaign-driven revenue uplift. Stock planning and customer outreach are proposed hypotheses that require further validation or controlled experiments.

## Validation

Every full run checks:

- The exclusion waterfall reconciles to the raw row count.
- Retained quantities and prices are positive.
- SQL and Pandas produce matching monthly sales totals.
- Customer-level recency, frequency, and monetary values agree between SQL and Pandas.
- The product join preserves transaction row counts.

Failed checks stop the run. Five unit tests cover cancellations, duplicates, anonymous customers, invalid dates, currency precision, fractional quantities, and deterministic RFM scoring with ties.

`reports/quality_report.json` records the latest full-data validation result, and `reports/test_results.txt` contains the recorded unit-test output. GitHub Actions runs the unit tests on pushes and pull requests. A manually triggered workflow also executes the full pipeline. Workflow repository permissions are limited to read access.

## Repository structure

| Path | Purpose |
|---|---|
| `src/pipeline.py` | Download, cleaning, analysis, and chart generation |
| `sql/` | Readable SQL queries for sales, customers, countries, and products |
| `tests/` | Edge-case and segmentation tests |
| `data/source_manifest.json` | Source attribution and file integrity metadata |
| `data/raw/` | Downloaded source file; excluded from Git |
| `data/processed/retail.sqlite` | Reproducible SQLite database; excluded from Git |
| `reports/` | Findings, quality checks, CSV tables, and PNG charts |
| `docs/cv_and_interview_tr.md` | CV statements in Turkish and English, plus interview notes in Turkish |
| `.github/workflows/validate.yml` | Automated validation workflow |

## License

Project code is provided under the **MIT License**. The source dataset is licensed under **CC BY 4.0**; derived tables and figures retain the dataset attribution. See [LICENSE](LICENSE) for details.
