"""
Class to calculate and hold logger statistics.
"""
__author__ = "Craig Dickinson"

import numpy as np


class LoggerStats(object):
    """Screen data from a list of filenames and store stats."""

    def __init__(self):
        """Lists for stats of each channel."""

        self.min = []
        self.max = []
        self.std = []
        self.mean = []

    def calc_stats(self, df_sample):
        """
        Calculate basic stats.
        Assumes at least two columns and first column is time.
        """

        data = df_sample[df_sample.columns[1:]]

        # Calculate min, max, mean and std for each channel
        mn = data.min()
        mx = data.max()
        ave = data.mean()
        std = data.std()

        # Append to internal list
        self.min.append(mn.values)
        self.max.append(mx.values)
        self.mean.append(ave.values)
        self.std.append(std.values)

        # TODO: McDermott project hack - don't keep this!
        # Hack for McDermott project to report slope between E and N time series instead of st. dev.
        # x = data.iloc[:, 1].values
        # y = data.iloc[:, 2].values
        # m = calc_slope(x, y)
        # self.std.append(np.array([m, m, m]))


def calc_slope(x, y):
    """Calculate the slope between two time series."""

    m, b = np.polyfit(x, y, 1)

    return m
