"""
Tests for logger properties routines.
"""
__author__ = "Craig Dickinson"

import unittest

import pytest
from dateutil.parser import parse
from testfixtures import TempDirectory

from app.core.logger_properties import LoggerProperties


class TestLogger(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TempDirectory()
        self.test_dir = self.temp_dir.makedir("dd09")
        self.test_filenames = [
            "dd09_2016_0317_0000.csv",
            "dd09_2016_0317_0100.csv",
            "dd09_2016_0317_0200.csv",
        ]
        self.test_dates = ["2016-03-17 00:00", "2016-03-17 01:00", "2016-03-17 02:00"]
        self.test_format = "xxxxxYYYYxmmDDxHHMM"

        # Write some empty files with desired date format
        for f in self.test_filenames:
            self.temp_dir.write("/".join([self.test_dir, f]), b"")

    def tearDown(self):
        self.temp_dir.cleanup_all()

    def test_get_filenames(self):
        """Check filenames are read in correctly."""

        logger = LoggerProperties("test_logger")
        logger.logger_path = self.test_dir
        logger.file_ext = "csv"
        logger.get_filenames_on_local()
        self.assertEqual(logger.raw_filenames, self.test_filenames)

    def test_check_file_timestamps(self):
        """Check file timestamps are correctly read as dates."""

        logger = LoggerProperties("test_logger")
        logger.logger_path = self.test_dir
        logger.file_timestamp_format = self.test_format
        logger.file_ext = "csv"
        logger.get_filenames_on_local()
        logger.get_timestamp_span()
        logger.check_file_timestamps()
        self.assertEqual(logger.files, self.test_filenames)

        dates = [parse(date, yearfirst=True) for date in self.test_dates]
        self.assertEqual(logger.file_timestamps, dates)


if __name__ == "__main__":
    pytest.main()
