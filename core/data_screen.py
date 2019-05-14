"""
Class to carry out screening checks on logger data.
"""
__author__ = 'Craig Dickinson'

import os.path

import numpy as np
import pandas as pd

from core.logger_properties import LoggerProperties
from core.read_files import read_pulse_acc_single_header_format


class DataScreen:
    """Screen data from a list of filenames and store stats."""

    def __init__(self):
        """Instantiate with empty logger."""

        self.logger = LoggerProperties()
        self.files = []

        # Dictionary of files with errors for specified logger
        self.dict_bad_files = {}

        # Number of points per file and channels across all files
        self.points_per_file = []
        self.cum_pts_per_channel = np.array([])

        # Minimum resolution
        # TODO: Output this in data screen report
        self.res = []

        # Data completeness
        self.data_completeness = np.array([])

        # Lists for sample start and end times
        self.stats_sample_start = []
        self.stats_sample_end = []
        self.spectral_sample_start = []
        self.spectral_sample_end = []

        # Interval to calculate stats over
        self.stats_sample_length = 0
        self.spectral_sample_length = 0

        # csv read properties
        self.header_row = 0
        self.skip_rows = []
        self.use_cols = []

    def set_logger(self, logger):
        """Set the logger filenames to be assessed and required read csv file properties."""

        self.logger = logger

        # Set full file path
        self.files = [os.path.join(self.logger.logger_path, f) for f in self.logger.files]

        # Set csv read properties
        self.header_row = self.logger.channel_header_row - 1
        self.skip_rows = [i for i in range(self.logger.num_headers) if i > self.header_row]

        # Set requested columns to process
        self.use_cols = [0] + [c - 1 for c in self.logger.requested_cols]

        # No header row specified
        if self.header_row < 0:
            self.header_row = None

    def read_logger_file(self, filename):
        """Read logger file into pandas data frame."""

        df = pd.DataFrame()

        # Read data into pandas data frame
        if self.logger.file_format == 'Fugro-csv' or self.logger.file_format == 'General-csv':
            df = pd.read_csv(filename,
                             sep=self.logger.file_delimiter,
                             header=self.header_row,
                             skiprows=self.skip_rows,
                             encoding='latin',
                             )
        elif self.logger.file_format == 'Pulse-acc':
            df = read_pulse_acc_single_header_format(filename)

        return df

    def munge_data(self, df):
        """Format the logger raw data so it is suitable for processing."""

        # Check all requested columns exist in file
        n = len(df.columns)
        missing_cols = [x for x in self.use_cols if x >= n]
        valid_cols = [x for x in self.use_cols if x < n]

        # Slice valid columns (copy to prevent SettingWithCopyWarning)
        df = df.iloc[:, valid_cols].copy()

        # Create dummy data for missing columns
        for i in missing_cols:
            df['Dummy' + str(i + 1)] = np.nan

        # Convert first column (should be timestamps string) to datetimes (not required for Pulse-acc format)
        if self.logger.file_format != 'Pulse-acc':
            df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0], format=self.logger.datetime_format, errors='coerce')

        # Convert any non-numeric data to NaN
        df.iloc[:, 1:] = df.iloc[:, 1:].apply(pd.to_numeric, errors='coerce')

        return df

    def screen_data(self, file_num, df):
        """Perform basic data screening operations on data frame."""

        # Number of rows in file
        pts = len(df)
        self.points_per_file.append(pts)

        # Number of points per channel - ignore timestamp column
        pts_per_channel = df.count().values[1:]

        # Cumulative total for all files
        if self.cum_pts_per_channel.size == 0:
            self.cum_pts_per_channel = pts_per_channel
        else:
            self.cum_pts_per_channel += pts_per_channel

        # Check number of points is valid
        if pts != self.logger.expected_data_points:
            filename = self.logger.files[file_num]
            self.dict_bad_files[filename] = 'Unexpected number of points'
        else:
            # Calculate resolution for each channel
            self.res.append(self.resolution(df))

    def resolution(self, df):
        """
        Return smallest difference between rows of a data frame for each
        column. Assumes column names are not multi-indexed.
        """

        # Array to hold resolutions
        res = []
        for col in df.columns:
            # Select column
            y = pd.DataFrame(df[col])

            # Sort and drop duplicates
            y = y.sort_values(col, ascending=True).drop_duplicates()

            # Calculate smallest difference between rows
            res.append(y.diff().min())

        return res

    def calc_data_completeness(self):
        """Calculate the proportion of good data coverage."""

        # Total data points in logger campaign
        # i = sum(self.points_per_file)

        # Total expected data points in logger campaign
        n = len(self.files) * self.logger.expected_data_points

        self.data_completeness = self.cum_pts_per_channel / n * 100

        return self.data_completeness

    def sample_data(self, sample_df, df, sample_length, type):
        """
        Extract data sample from file.
        Move the required rows from data to sample to make len(sample) = sample_length.
        :param sample_df: Current subset data frame of main logger file (initially empty)
        :param df: Current logger file data frame (sample data gets dropped)
        :return: Update sample data frame and logger file data frame with sample data dropped.
        """

        # TODO: Do units conversion here

        # Current number of points in sample
        ns = len(sample_df)

        # Number of points in data
        nd = len(df)

        # Number of points to append to sample - sample_length is the target number of sample points
        cutoff = min(sample_length - ns, nd)

        if ns < sample_length and nd > 0:
            # Append data to sample data frame and drop sample from main data frame
            sample_df = sample_df.append(df[:cutoff].copy(), ignore_index=True)
            df.drop(df.index[:cutoff], inplace=True)

            # TODO: Allowing short sample length (revisit)
            # Store start and end times of sample data if data frame contains target length
            # if len(sample_df) == sample_length:
            if len(sample_df) <= sample_length:
                if type == 'stats':
                    self.stats_sample_start.append(sample_df.iloc[0, 0])
                    self.stats_sample_end.append(sample_df.iloc[-1, 0])
                elif type == 'spectral':
                    self.spectral_sample_start.append(sample_df.iloc[0, 0])
                    self.spectral_sample_end.append(sample_df.iloc[-1, 0])

        return sample_df, df
