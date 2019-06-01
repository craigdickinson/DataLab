"""
Created on 8 Aug 2016

@author: bowdenc
"""
import unittest
from core import custom_date


class TestCustomDate(unittest.TestCase):
    def setUp(self):
        self.test_dates = ["2016-03-17 00:00", "2016-03-17 01:00", "2016-03-17 02:00"]
        self.test_format = "xxxxxYYYYxmmDDxHHMM"

    def test_get_date_format_code(self):
        """Check date codes are found correctly."""

        test_format = self.test_format
        start, end = custom_date.get_date_code_span("Y", test_format)
        self.assertEqual(start, 5)
        self.assertEqual(end, 9)

        start, end = start, end = custom_date.get_date_code_span("H", test_format)
        self.assertEqual(start, 15)
        self.assertEqual(end, 17)

    def test_make_time_str(self):
        """Check custom time string format routine gives correct string."""

        s = custom_date.make_time_str("23", "15", "01", "100")
        self.assertEqual(s, "23:15:01.100")


if __name__ == "__main__":
    unittest.main()
