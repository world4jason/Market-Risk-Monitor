import unittest

from pipeline.cbc_rates import parse_cbc_rate_html


class CbcRateHtmlTests(unittest.TestCase):
    def test_parse_official_table_shape(self):
        html = """
        <table>
          <thead><tr><th>EFFECTIVE DATE OF CHANGE</th><th>DISCOUNT</th><th>ACCOMMODATIONS WITH COLLATERAL</th><th>ACCOMMODATIONS WITHOUT COLLATERAL</th></tr></thead>
          <tbody>
            <tr><td>2024/3/22</td><td>2</td><td>2.375</td><td>4.25</td></tr>
            <tr><td>2023/3/24</td><td>1.875</td><td>2.25</td><td>4.125</td></tr>
          </tbody>
        </table>
        """
        rows = parse_cbc_rate_html(
            html,
            "https://www.cbc.gov.tw/en/lp-695-2.html",
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["date"], "2024-03-22")
        self.assertEqual(rows[0]["discount_rate"], 2.0)
        self.assertEqual(rows[1]["collateral_rate"], 2.25)


if __name__ == "__main__":
    unittest.main()
