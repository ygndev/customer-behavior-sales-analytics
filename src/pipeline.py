"""Reproducible UCI Online Retail analysis. Run from any working directory."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import sqlite3
import urllib.request
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://archive.ics.uci.edu/static/public/352/online+retail.zip'
COLS = ['InvoiceNo', 'StockCode', 'Description', 'Quantity', 'InvoiceDate',
        'UnitPrice', 'CustomerID', 'Country']


def download(path):
    if not path.exists():
        request = urllib.request.Request(URL, headers={'User-Agent': 'RetailPortfolio/1.0'})
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            content = archive.read('Online Retail.xlsx')
        temp = path.with_suffix('.tmp')
        temp.write_bytes(content)
        temp.replace(path)


def clean(raw):
    """Exclusive exclusion waterfall; anonymous sales remain in sales analytics."""
    if list(raw.columns) != COLS:
        raise ValueError('Unexpected dataset schema')
    df = raw.copy()
    audit = {'raw_rows': len(df)}

    def exclude(mask, name):
        nonlocal df
        audit[name] = int(mask.sum())
        df = df.loc[~mask].copy()

    exclude(df.duplicated(), 'exact_duplicates_removed')
    df['InvoiceDate'] = pd.to_datetime(df.InvoiceDate, errors='coerce')
    for col in ['Quantity', 'UnitPrice']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    exclude(df[['InvoiceDate', 'Quantity', 'UnitPrice', 'InvoiceNo', 'StockCode', 'Country']].isna().any(axis=1), 'invalid_required_removed')
    df['InvoiceNo'] = df.InvoiceNo.astype(str).str.strip()
    df['StockCode'] = df.StockCode.astype(str).str.strip()
    exclude(~np.isfinite(df.Quantity) | ~np.isfinite(df.UnitPrice), 'nonfinite_removed')
    exclude(df.InvoiceNo.str.upper().str.startswith('C'), 'cancellation_lines_removed')
    exclude(df.Quantity <= 0, 'nonpositive_quantity_removed')
    exclude(df.UnitPrice <= 0, 'nonpositive_price_removed')
    if not (df.Quantity == np.rint(df.Quantity)).all():
        raise ValueError('Fractional quantities require an explicit unit policy')
    # Millipounds give exact integer monetary aggregation for the retained sales.
    scaled = df.UnitPrice * 1000
    if not np.allclose(scaled, np.rint(scaled), atol=1e-6, rtol=0):
        raise ValueError('Prices contain precision beyond 0.001 GBP; revise currency policy')
    df['line_millipounds'] = np.rint(scaled).astype('int64') * df.Quantity.astype('int64')
    df['CustomerID'] = df.CustomerID.astype('Int64').astype('string')
    df = df.rename(columns={'InvoiceNo': 'invoice_no', 'StockCode': 'stock_code',
        'Description': 'description', 'Quantity': 'quantity', 'InvoiceDate': 'invoice_date',
        'UnitPrice': 'unit_price', 'CustomerID': 'customer_id', 'Country': 'country'})
    audit['retained_sales_rows'] = len(df)
    audit['anonymous_sales_rows'] = int(df.customer_id.isna().sum())
    return df, audit


def segment(rfm):
    """Tie-preserving empirical percentile scores; deterministic rule segments."""
    result = rfm.copy()
    for col, short in [('recency', 'r'), ('frequency', 'f'), ('monetary', 'm')]:
        # Same values receive the same score; quintile sizes may differ.
        pct = result[col].rank(method='average', pct=True, ascending=col != 'recency')
        result[short + '_score'] = np.ceil(pct * 5).clip(1, 5).astype(int)
    r, f, m = (result[c + '_score'] for c in 'rfm')
    result['segment'] = np.select(
        [(r >= 4) & (f >= 4) & (m >= 4), (r <= 2) & ((f >= 4) | (m >= 4)),
         (r >= 4) & (f <= 2), f >= 4, r <= 2],
        ['Champions', 'At risk high value', 'Recent low frequency', 'Loyal', 'Hibernating'],
        default='Developing')
    return result


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true', help='Require cached raw XLSX')
    args = parser.parse_args()
    for folder in ['data/raw', 'data/processed', 'reports/figures', 'reports/tables']:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    path = ROOT / 'data/raw/Online Retail.xlsx'
    if args.offline and not path.exists():
        raise FileNotFoundError('Run once online to download the dataset')
    download(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path = ROOT / 'data/source_manifest.json'
    if manifest_path.exists():
        expected = json.loads(manifest_path.read_text())['xlsx_sha256']
        if digest != expected:
            raise ValueError('Raw file checksum differs from the reviewed dataset')
    raw = pd.read_excel(path, engine='openpyxl')
    sales, audit = clean(raw)
    assert len(raw) == 541909, 'Unexpected source row count'
    assert sum(v for k, v in audit.items() if k.endswith('_removed')) + len(sales) == len(raw)
    assert sales.quantity.gt(0).all() and sales.unit_price.gt(0).all()
    snapshot = (sales.invoice_date.max().normalize() + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    db = ROOT / 'data/processed/retail.sqlite'
    with sqlite3.connect(db) as conn:
        sales.to_sql('sales', conn, if_exists='replace', index=False)
        products = (sales.sort_values('invoice_date', kind='stable')
                    .dropna(subset=['description']).drop_duplicates('stock_code', keep='last')
                    [['stock_code', 'description']])
        products.to_sql('products', conn, if_exists='replace', index=False)
        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_product ON products(stock_code)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_customer ON sales(customer_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_invoice ON sales(invoice_no)')
        def query(name, params=None):
            return pd.read_sql_query((ROOT / f'sql/{name}.sql').read_text(), conn, params=params)
        monthly = query('monthly_sales')
        rfm = segment(query('customer_rfm', {'snapshot': snapshot}))
        countries = query('country_sales')
        top_products = query('top_products')
        joined_count = conn.execute('SELECT COUNT(*) FROM sales s LEFT JOIN products p ON s.stock_code=p.stock_code').fetchone()[0]
        assert joined_count == len(sales), 'Join multiplied sales rows'
        known_total = conn.execute('SELECT SUM(line_millipounds) FROM sales WHERE customer_id IS NOT NULL').fetchone()[0]
    # Independent Pandas reconciliation against SQL.
    reference = sales.groupby(sales.invoice_date.dt.strftime('%Y-%m')).line_millipounds.sum() / 1000
    np.testing.assert_allclose(monthly.gross_sales_gbp, reference.to_numpy(), rtol=0, atol=1e-7)
    assert round(rfm.monetary.sum() * 1000) == known_total
    assert rfm.customer_id.nunique() == sales.customer_id.nunique()
    assert rfm.frequency.sum() == sales.dropna(subset=['customer_id']).groupby('customer_id').invoice_no.nunique().sum()
    known = sales.dropna(subset=['customer_id']).groupby('customer_id')
    expected_rfm = pd.DataFrame({
        'recency': (pd.Timestamp(snapshot) - known.invoice_date.max().dt.normalize()).dt.days,
        'frequency': known.invoice_no.nunique(),
        'monetary': known.line_millipounds.sum() / 1000,
    }).sort_index()
    actual_rfm = rfm.set_index('customer_id').sort_index()
    for column in ['recency', 'frequency', 'monetary']:
        np.testing.assert_allclose(actual_rfm[column], expected_rfm[column], rtol=0, atol=1e-7)
    monthly['complete_month'] = monthly.month != '2011-12'
    monthly['mom_pct'] = monthly.gross_sales_gbp.pct_change() * 100
    monthly.loc[~monthly.complete_month, 'mom_pct'] = np.nan
    summary = rfm.groupby('segment').agg(customers=('customer_id', 'size'),
        gross_sales_gbp=('monetary', 'sum'), median_recency=('recency', 'median'),
        median_frequency=('frequency', 'median')).reset_index()
    summary['sales_share_pct'] = summary.gross_sales_gbp / summary.gross_sales_gbp.sum() * 100
    order_values = sales.groupby('invoice_no').line_millipounds.sum() / 1000
    descriptive = order_values.describe(percentiles=[.25, .5, .75, .95, .99]).rename('order_value_gbp').to_frame()
    for name, frame in [('monthly_sales', monthly), ('customer_rfm', rfm), ('segments', summary),
                         ('top_products', top_products),
                         ('country_sales', countries), ('order_statistics', descriptive)]:
        frame.to_csv(ROOT / f'reports/tables/{name}.csv', index=name == 'order_statistics')
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(11, 5))
    colors = ['#235b83' if v else '#c88b47' for v in monthly.complete_month]
    ax.bar(monthly.month, monthly.gross_sales_gbp / 1000, color=colors)
    ax.set(title='Monthly gross positive sales | Dec 2011 is partial (1–9)', ylabel='GBP thousands')
    ax.tick_params(axis='x', rotation=45)
    fig.tight_layout(); fig.savefig(ROOT / 'reports/figures/monthly_sales.png', dpi=160); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 5))
    ordered = summary.sort_values('gross_sales_gbp')
    ax.barh(ordered.segment, ordered.gross_sales_gbp / 1000, color='#297f78')
    ax.set(title='RFM segments | identified customers only', xlabel='Gross positive sales (GBP thousands)')
    fig.tight_layout(); fig.savefig(ROOT / 'reports/figures/segments.png', dpi=160); plt.close(fig)
    daily = sales.groupby(sales.invoice_date.dt.normalize()).line_millipounds.sum() / 1000
    weekday = daily.groupby(daily.index.dayofweek).agg(['mean', 'count']).reindex(range(7))
    weekday.index = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    weekday.to_csv(ROOT / 'reports/tables/weekday_sales.csv', index_label='weekday')
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(weekday.index, weekday['mean'], color='#235b83')
    ax.set(title='Average sales per observed trading day | missing days excluded', ylabel='GBP')
    for day in weekday.index[weekday['count'].isna()]:
        ax.text(day, 100, 'No observations', ha='center', va='bottom', rotation=90, fontsize=8)
    fig.tight_layout(); fig.savefig(ROOT / 'reports/figures/weekday_sales.png', dpi=160); plt.close(fig)
    audit.update({'snapshot_date': snapshot, 'gross_sales_gbp': int(sales.line_millipounds.sum()) / 1000,
        'source_start': str(sales.invoice_date.min()), 'source_end': str(sales.invoice_date.max()),
        'currency_unit': 'GBP; aggregation uses integer 0.001 GBP units',
        'orders': sales.invoice_no.nunique(), 'known_customers': sales.customer_id.nunique(),
        'identified_sales_share_pct': known_total / int(sales.line_millipounds.sum()) * 100,
        'validation': 'PASS: waterfall, positivity, join cardinality, SQL/Pandas monthly totals and per-customer RFM'})
    (ROOT / 'reports/quality_report.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    manifest_path.write_text(json.dumps({'source_url': URL, 'doi': '10.24432/C5BW33',
        'license': 'CC BY 4.0', 'xlsx_sha256': digest, 'raw_rows': len(raw)}, indent=2), encoding='utf-8')
    peak = monthly[monthly.complete_month].sort_values('gross_sales_gbp').iloc[-1]
    text = f'''# Bulgular\n\n- Temiz pozitif satış: £{audit['gross_sales_gbp']:,.2f}; {audit['orders']:,} fatura.\n- Kimliği bilinen {audit['known_customers']:,} müşteri, satış tutarının %{audit['identified_sales_share_pct']:.2f}'sini kapsar.\n- Tam aylar arasında en yüksek satış {peak['month']}: £{peak['gross_sales_gbp']:,.2f}.\n- Ortalama sipariş £{order_values.mean():,.2f}; medyan £{order_values.median():,.2f}. Uç değerler ortalamayı etkiler.\n\n## Yorum ve aksiyon hipotezleri\n\nYüksek hacimli aylar öncesinde stok ve kapasite planlaması incelenebilir. Champions için sadakat, At risk high value için yeniden etkileşim kampanyaları test edilebilir. Bunlar ölçülmüş kampanya etkisi değildir; kontrollü deney gerektirir.\n\nTek bir yıllık döngü kalıcı mevsimselliği kanıtlamaz. Aralık 2011 yalnızca 1–9 günlerini kapsar ve aylık büyüme karşılaştırmasından çıkarılmıştır. Gelir, iptal/iade ve sıfır/negatif tutarlar dışlandıktan sonraki brüt pozitif satıştır; net gelir veya kâr değildir. Ürün dışı ücret kodları korunur; toplam ürün geliri olarak yorumlanmamalıdır.\n'''
    champions = summary.loc[summary.segment == 'Champions'].iloc[0]
    risk = summary.loc[summary.segment == 'At risk high value'].iloc[0]
    text += (f"\n## Segment bulguları\n\nChampions grubundaki {int(champions.customers):,} müşteri, "
             f"kimliği bilinen müşterilerin satış tutarının %{champions.sales_share_pct:.2f}'sini oluşturur. "
             f"At risk high value grubunda {int(risk.customers):,} müşteri vardır; "
             f"gözlem dönemindeki pozitif satış tutarları £{risk.gross_sales_gbp:,.2f}'dir. "
             "Bu tutar gelecekte kaybedilecek gelir veya geri kazanılabilir gelir tahmini değildir.\n")
    (ROOT / 'reports/findings_tr.md').write_text(text, encoding='utf-8')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    run()
