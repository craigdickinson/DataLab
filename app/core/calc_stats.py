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
