import unittest
import generate_spatial_comparisons as g

class DateTest(unittest.TestCase):
	def test_days_in_month(self):
		self.assertEqual(g.get_days_in_month_by_band_and_year(4, 2015), 28)  # Feb 2015 has 28 days
		self.assertEqual(g.get_days_in_month_by_band_and_year(4, 2016), 29)  # Feb 2016 has 29 days
		self.assertEqual(g.get_days_in_month_by_band_and_year(11, 2016), 30)  # Sept 2016
		self.assertEqual(g.get_days_in_month_by_band_and_year(10, 2016), 31)  # Aug 2016

if __name__ == "__main__":
	unittest.main()