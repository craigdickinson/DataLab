"""
Class to carry out screening checks on logger data.
"""
__author__ = "Craig Dickinson"

import os.path
from datetime import timedelta

import numpy as np
import pandas as pd

from app.core.logger_properties import LoggerProperties
from app.core.read_files import read_pulse_acc
from app.core.signal_processing import filter_signal


class DataScreen(object):
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

        # Lists for sample start and end datetimes
        self.stats_sample_start = []
        self.stats_sample_end = []
        self.spect_sample_start = []
        self.spect_sample_end = []

        # Interval to calculate stats over
        self.stats_sample_length = 0
        self.spect_sample_length = 0

        # File read properties
        self.file_format = "General-csv"
        self.delim = ","
        self.header_row = 0
        self.skip_rows = []
        self.use_cols = []
        self.channel_names = []
        self.unit_conv_factors = []

        # Apply bandpass signal filtering flag
        self.apply_filters = True

    def set_logger(self, logger):
        """Set the logger filenames to be assessed and required read file properties."""

        self.logger = logger
        self.channel_names = logger.channel_names

        # Set full file path
        self.files = [
            os.path.join(self.logger.logger_path, f) for f in self.logger.files
        ]

        # Set file format (i.e. Fugro/Pulse/General)
        self.file_format = self.logger.file_format

        # Set file read properties
        self.delim = self.logger.file_delimiter
        self.header_row = self.logger.channel_header_row - 1

        # Additional header rows to skip - only using the first header row for data frame column names
        self.skip_rows = [
            i for i in range(self.logger.num_headers) if i > self.header_row
        ]

        # No header row specified
        if self.header_row < 0:
            self.header_row = None

        # Set requested columns to process
        self.use_cols = set([0] + [c - 1 for c in self.logger.cols_to_process])

        # Unit conversion factors
        self.unit_conv_factors = logger.unit_conv_factors

        # Flags to set whether bandpass filtering is to be applied
        low_cutoff = self.logger.low_cutoff_freq
        high_cutoff = self.logger.high_cutoff_freq

        if low_cutoff is None and high_cutoff is None:
            self.apply_filters = False

    def read_logger_file(self, filename):
        """Read logger file into pandas data frame."""

        df = pd.DataFrame()

        # Read data into pandas data frame
        if self.file_format == "Fugro-csv" or self.file_format == "General-csv":
            df = pd.read_csv(
                filename,
                sep=self.delim,
                header=self.header_row,
                skiprows=self.skip_rows,
                encoding="latin",
            )
        elif self.file_format == "Pulse-acc":
            df = read_pulse_acc(filename, multi_header=False)

        return df

    def munge_data(self, df, timestamp=""):
        """Format the logger raw data so it is suitable for processing."""

        # Copy to prevent SettingWithCopyWarning
        df = df.copy()

        if self.logger.file_format == "General-csv":
            df = df.dropna(axis=1)

            # Replace time column with timestamp
            ts = df.iloc[:, 0].values
            timestamps = [timestamp + timedelta(seconds=t) for t in ts]
            df.iloc[:, 0] = timestamps

        # Check all requested columns exist in file
        n = len(df.columns)
        missing_cols = [x for x in self.use_cols if x >= n]
        valid_cols = [x for x in self.use_cols if x < n]

        # Slice valid columns
        df = df.iloc[:, valid_cols]

        # Create dummy data for missing columns
        for i in missing_cols:
            df["Dummy " + str(i + 1)] = np.nan

        # Replace column names with setup channel names (should only be different if user names supplied)
        df.columns = ["Timestamp"] + self.channel_names

        # Convert first column (should be timestamps string) to datetimes (not required for Pulse-acc format)
        if self.logger.file_format != "Pulse-acc":
            df.iloc[:, 0] = pd.to_datetime(
                df.iloc[:, 0], format=self.logger.datetime_format, errors="coerce"
            )

        # Convert any non-numeric data to NaN
        df.iloc[:, 1:] = df.iloc[:, 1:].apply(pd.to_numeric, errors="coerce")

        # Apply any unit conversions
        if len(self.unit_conv_factors) == len(df.columns) - 1:
            df.iloc[:, 1:] = np.multiply(df.iloc[:, 1:], self.unit_conv_factors)

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
            self.dict_bad_files[filename] = "Unexpected number of points"
        else:
            # Calculate resolution for each channel
            self.res.append(self._resolution(df))

    @staticmethod
    def _resolution(df):
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

    def sample_data(self, df_sample, df, sample_length, type):
        """
        Extract data sample from file.
        Move the required rows from data to sample to make len(sample) = sample_length.
        :param df_sample: Current subset data frame of main logger file (initially empty)
        :param df: Current logger file data frame (sample data gets dropped)
        :param sample_length: Number of expected data points sample to have
        :param type: stats or spectral string
        :return: Updated sample data frame and logger file data frame with sample data dropped
        """

        # Current number of points in sample
        ns = len(df_sample)

        # Number of points in data
        nd = len(df)

        # Number of points to append to sample - sample_length is the target number of sample points
        cutoff = min(sample_length - ns, nd)

        if ns < sample_length and nd > 0:
            # Append data to sample data frame and drop sample from main data frame
            df_sample = df_sample.append(df[:cutoff].copy(), ignore_index=True)
            df.drop(df.index[:cutoff], inplace=True)

            # TODO: Allowing short sample length (revisit)
            # Store start and end times of sample data if data frame contains target length
            # if len(df_sample) == sample_length:
            if len(df_sample) <= sample_length:
                if type == "stats":
                    self.stats_sample_start.append(df_sample.iloc[0, 0])
                    self.stats_sample_end.append(df_sample.iloc[-1, 0])
                elif type == "spectral":
                    self.spect_sample_start.append(df_sample.iloc[0, 0])
                    self.spect_sample_end.append(df_sample.iloc[-1, 0])

        return df_sample, df

    def filter_data(self, df_sample):
        """Filter out low frequencies (drift) and high frequencies (noise)."""

        df = df_sample.copy()

        # Timestamps column
        ts = df.iloc[:, 0]

        # Need index to be time - calculate time delta from t0 and convert to seconds (float) then set as index
        t = (df.iloc[:, 0] - df.iloc[0, 0]).dt.total_seconds().values.round(3)
        df.index = t

        # Remove timestamps column
        df = df.select_dtypes("number")

        # Apply bandpass filter
        df_filtered = filter_signal(
            df, self.logger.low_cutoff_freq, self.logger.high_cutoff_freq
        )

        if not df_filtered.empty:
            # Insert timestamps column and reset index to return a data frame in the same format as the unfiltered one
            df_filtered.reset_index(drop=True, inplace=True)
            df_filtered.insert(loc=0, column=ts.name, value=ts)

        return df_filtered
