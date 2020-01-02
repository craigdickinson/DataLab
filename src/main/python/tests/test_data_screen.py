"""
Tests for data screen routines.
"""
__author__ = "Craig Dickinson"

import datetime as dt
import io
import unittest

import numpy as np
import pandas as pd
import pandas.util.testing as pdt
import pytest

from core.data_screen import DataScreen


def example_data_file():
    """Create an example data file in memory."""

    header1 = "#Sample Interval: 0.100000 (seconds)"
    header2 = "Timestamp,AccelX,AccelY,RateX,RateY"
    header3 = "dd-mmm-yyyy HH:MM:SS.FFF,mm/s2,mm/s2,rad/s,rad/s"

    start_date = dt.datetime(2016, 3, 17, 1, 0, 0)

    # Add one tenth of a second
    time_delta = dt.timedelta(0, 0, 0, 100)

    # Sample frequency in Hz
    sample_freq = 10

    # 20 in event duration in seconds
    Ts = 60 * 20

    # Number of points
    N = Ts * sample_freq

    # Array of times
    time = [start_date + i * time_delta for i in range(N)]
    time_str = [t.strftime("%Y-%m-%d %H:%M:%S.%f") for t in time]

    ax, ay, Rx, Ry = example_data(sample_freq, Ts)

    data = [
        ",".join([time_str[i], str(ax[i]), str(ay[i]), str(Rx[i]), str(Ry[i])])
        for i in range(N)
    ]

    data.insert(0, header3)
    data.insert(0, header2)
    data.insert(0, header1)

    return "\n".join(data)


def example_data(fs, Ts):
    """
    Create 4 test signals
    :param fs: Sampling frequency (Hz)
    :param Ts: Ts: sample length (seconds)
    :return: Lists of dummy X, Y accelerations/rotations
    """

    # Number of points
    N = Ts * fs

    # random signals
    phi = np.pi / 2
    ax = [np.sin(2 * np.pi * 2 * (i / fs)) for i in range(N)]
    ay = [np.sin(2 * np.pi * 2 * (i / fs) + phi) for i in range(N)]
    Rx = [a * 0.01 + 0.5 for a in ax]
    Ry = [a * 0.01 + 0.3 for a in ay]

    # Make some noise!
    noise1 = np.random.normal(0, 0.1, N)
    noise2 = np.random.normal(0, 0.1, N)
    noise3 = np.random.normal(0, 0.1, N)
    noise4 = np.random.normal(0, 0.1, N)

    ax = ax + noise1
    ay = ay + noise2
    Rx = Rx + noise3
    Ry = Ry + noise4

    return ax, ay, Rx, Ry


class Test(unittest.TestCase):
    def setUp(self):
        """Start with an empty logger_stats object and test the associated functions."""

        self.logger_stats = DataScreen()

    def test_read_all_from_fstream(self):
        """Test function to read lines from file into an array."""

        # Create some test data
        test_stream = io.StringIO()
        eg_file = example_data_file()
        test_stream.write(eg_file)
        test_stream.seek(0)

        # Set up file read properties
        delim = ","
        header_row = 1
        skip_rows = [2]
        use_cols = [0, 1, 2, 3, 4]

        # Store properties in DataScreen object
        self.logger_stats.delim = delim
        self.logger_stats.header_row = header_row
        self.logger_stats.skip_rows = skip_rows
        self.logger_stats.use_cols = use_cols

        # Read the data using data_screen routine
        data = self.logger_stats.read_logger_file(test_stream)

        # Compare the data
        test_stream.seek(0)
        data1 = pd.read_csv(
            test_stream,
            sep=delim,
            header=header_row,
            usecols=use_cols,
            skiprows=skip_rows,
            encoding="latin1",
        )

        pdt.assert_frame_equal(data1, data)

    def test_process_data(self):
        """Test function to convert data from string to numbers."""
        pass


if __name__ == "__main__":
    pytest.main()
