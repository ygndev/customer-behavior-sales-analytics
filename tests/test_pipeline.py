import sys
import unittest
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pipeline import clean, segment, COLS


class CleaningTests(unittest.TestCase):
    def test_waterfall_and_anonymous_sales(self):
        base = ['100', 'A', 'Product', 2, pd.Timestamp('2011-01-01'), 1.25, 12345, 'UK']
        rows = [base.copy() for _ in range(7)]
        rows[2][0] = 'C101'
        rows[3][0], rows[3][3] = '102', -2
        rows[4][0], rows[4][5] = '103', 0
        rows[5][0], rows[5][6] = '104', None
        rows[6][0], rows[6][4] = '105', None
        sales, audit = clean(pd.DataFrame(rows, columns=COLS))
        self.assertEqual(len(sales), 2)
        self.assertEqual(sales.line_millipounds.sum(), 5000)
        self.assertEqual(audit['anonymous_sales_rows'], 1)
        self.assertEqual(audit['exact_duplicates_removed'], 1)
        self.assertEqual(sum(v for k, v in audit.items() if k.endswith('_removed')), 5)

    def test_excess_precision_rejected(self):
        row = ['100', 'A', 'P', 1, pd.Timestamp('2011-01-01'), 1.2345, 12345, 'UK']
        with self.assertRaises(ValueError):
            clean(pd.DataFrame([row], columns=COLS))

    def test_millipound_precision_preserved(self):
        row = ['100', 'A', 'P', 3, pd.Timestamp('2011-01-01'), .001, 12345, 'UK']
        sales, _ = clean(pd.DataFrame([row], columns=COLS))
        self.assertEqual(sales.line_millipounds.sum(), 3)

    def test_fractional_quantity_rejected(self):
        row = ['100', 'A', 'P', 1.5, pd.Timestamp('2011-01-01'), 1, 12345, 'UK']
        with self.assertRaises(ValueError):
            clean(pd.DataFrame([row], columns=COLS))

    def test_rfm_direction_ties_and_order_independence(self):
        frame = pd.DataFrame({'customer_id': list('abcdef'), 'recency': [1, 1, 5, 30, 60, 90],
                              'frequency': [20, 20, 4, 3, 2, 1], 'monetary': [1000, 1000, 400, 300, 200, 100]})
        result = segment(frame).set_index('customer_id')
        shuffled = segment(frame.sample(frac=1, random_state=7)).set_index('customer_id')
        pd.testing.assert_frame_equal(result.sort_index(), shuffled.sort_index())
        self.assertEqual(result.loc['a', 'r_score'], result.loc['b', 'r_score'])
        self.assertGreater(result.loc['a', 'r_score'], result.loc['f', 'r_score'])
        self.assertEqual(result.loc['a', 'segment'], 'Champions')


if __name__ == '__main__':
    unittest.main()
