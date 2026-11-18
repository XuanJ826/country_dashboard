import unittest

import pandas as pd

from data_sources import annualized_quarterly_growth, real_exchange_rate_index, year_over_year_percent_change


class DashboardCalculationTests(unittest.TestCase):
    def test_yoy_inflation_is_percent_change_from_same_month(self):
        index = pd.date_range("2020-01-01", periods=13, freq="MS")
        cpi = pd.Series([100.0] * 12 + [110.0], index=index)
        result = year_over_year_percent_change(cpi)
        self.assertAlmostEqual(result.iloc[-1], 10.0)

    def test_missing_cpi_is_not_filled_into_an_inflation_estimate(self):
        index = pd.date_range("2020-01-01", periods=13, freq="MS")
        cpi = pd.Series([100.0] * 12 + [float("nan")], index=index)
        result = year_over_year_percent_change(cpi)
        self.assertTrue(pd.isna(result.iloc[-1]))

    def test_real_exchange_rate_uses_course_convention_and_2016_base(self):
        index = pd.date_range("2016-01-01", periods=13, freq="MS")
        fx = pd.Series([1.25] * 12 + [1.30], index=index)
        us_cpi = pd.Series([100.0] * 12 + [110.0], index=index)
        canada_cpi = pd.Series([100.0] * 12 + [105.0], index=index)
        result = real_exchange_rate_index(fx, us_cpi, canada_cpi)
        expected = 100 * (1.30 * 110 / 105) / 1.25
        self.assertAlmostEqual(result.loc["2016-01-01":"2016-12-01"].mean(), 100.0)
        self.assertAlmostEqual(result.iloc[-1], expected)
        self.assertGreater(result.iloc[-1], 100.0)

    def test_quarterly_growth_is_compounded_and_annualized(self):
        gdp = pd.Series([100.0, 102.0], index=pd.to_datetime(["2025-12-31", "2026-03-31"]))
        result = annualized_quarterly_growth(gdp)
        self.assertAlmostEqual(result.iloc[-1], ((1.02 ** 4) - 1) * 100)


if __name__ == "__main__":
    unittest.main()
