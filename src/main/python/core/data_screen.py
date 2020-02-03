"""
Class to carry out screening checks on logger data.
"""
__author__ = "Craig Dickinson"

import os.path
from datetime import timedelta

import numpy as np
import pandas as pd

from core.logger_properties import LoggerProperties
from core.read_files import read_2hps2_acc, read_pulse_acc
from core.signal_processing import (
    add_signal_mean,
    apply_butterworth_filter,
    apply_rectangular_filter,
    create_butterworth_filter,
)


class DataScreen(object):
    """Screen data from a list of filenames and store stats."""

    def __init__(self, logger=None):
        """Instantiate with empty logger."""

        self.logger = LoggerProperties()
        self.logger_id = ""
        self.files = []
        self.stats_file_nums = []
        self.spect_file_nums = []

        # Dictionary of files with errors for specified logger
        self.dict_bad_files = {}

        # Number of points per file and channels across all files
        self.points_per_file = []
        self.cum_pts_per_channel = np.array([])

        # Number of data points processed per sample
        self.stats_sample_length = 0
        self.spect_sample_length = 0

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

        # File read properties
        self.file_format = "Custom"
        self.delim = ","
        self.header_row = 0
        self.skip_rows = []
        self.use_cols = []
        self.channel_names = []
        self.unit_conv_factors = []
        self.file_timestamp_embedded = True
        self.first_col = "Timestamp"

        # Filter parameters
        self.apply_filters = True
        self.filter_type = "butterworth"
        self.low_cutoff = None
        self.high_cutoff = None
        self.sos_filter = None
        self.butterworth_order = 6

        # Screening requested flags
        self.stats_requested = False
        self.spect_requested = False
        self.histograms_requested = False
        self.integration_requested = False

        # Screening processed flags
        self.stats_processed = False
        self.spect_processed = False
        self.histograms_processed = False
        self.integration_processed = False

        if logger:
            self.set_logger(logger)

    def set_logger(self, logger: LoggerProperties):
        """Set the logger filenames to be assessed and required read file properties."""

        self.logger = logger
        self.logger_id = logger.logger_id
        self.channel_names = logger.channel_names

        # Full file path
        self.files = [os.path.join(logger.logger_path, f) for f in logger.files]

        # File format (i.e. Custom/Fugro/Pulse/2HPS2")
        self.file_format = self.logger.file_format

        # Flag whether filenames contain timestamps
        self.file_timestamp_embedded = self.logger.file_timestamp_embedded

        # Set file read properties
        self.delim = self.logger.file_delimiter
        self.header_row = self.logger.channel_header_row - 1

        # Additional header rows to skip - only using the first header row for dataframe column names
        self.skip_rows = [i for i in range(self.logger.num_headers) if i > self.header_row]

        # No header row specified
        if self.header_row < 0:
            self.header_row = None

        # Set requested columns to process
        self.use_cols = set([0] + [c - 1 for c in self.logger.cols_to_process])

        # Unit conversion factors
        self.unit_conv_factors = logger.unit_conv_factors

        # Interval to process on
        self.stats_sample_length = int(self.logger.stats_interval * self.logger.freq)
        self.spect_sample_length = int(self.logger.spect_interval * self.logger.freq)

        # Flags to set whether bandpass filtering is to be applied
        self.low_cutoff = self.logger.low_cutoff_freq
        self.high_cutoff = self.logger.high_cutoff_freq

        if self.low_cutoff is None and self.high_cutoff is None:
            self.apply_filters = False
        elif self.filter_type == "butterworth":
            self.sos_filter = create_butterworth_filter(
                self.logger.freq, self.low_cutoff, self.high_cutoff, order=self.butterworth_order
            )

    def read_logger_file(self, file):
        """Read logger file into dataframe."""

        # Read data to dataframe
        if self.file_format == "Custom" or self.file_format == "Fugro-csv":
            if self.file_format == "Fugro-csv":
                encoding = "latin1"
            else:
                encoding = None

            try:
                df = pd.read_csv(
                    file,
                    sep=self.delim,
                    header=self.header_row,
                    skiprows=self.skip_rows,
                    skip_blank_lines=False,
                    encoding=encoding,
                )
            # Attempt to handle non-utf-8 encoded files
            except UnicodeDecodeError:
                df = pd.read_csv(
                    file,
                    sep=self.delim,
                    header=self.header_rows,
                    skiprows=self.skip_rows,
                    skip_blank_lines=False,
                    encoding="latin1",
                )
        elif self.file_format == "Pulse-acc":
            df = read_pulse_acc(file, multi_header=False)
        elif self.file_format == "2HPS2-acc":
            df = read_2hps2_acc(file, multi_header=False)
        else:
            df = pd.DataFrame()

        return df

    def wrangle_data(self, df, file_idx=0):
        """Format the logger raw data so it is suitable for processing."""

        # Copy to prevent SettingWithCopyWarning
        df = df.copy()
        self.first_col = "Timestamp"

        if self.logger.file_format == "Custom":
            # Drop columns that are all nan (can happen with poorly delimited csv files, e.g. trailing commas)
            df = df.dropna(axis=1, how="all")

            # If no header rows set, the columns index will be Int64Index - instead set custom column names
            if self.header_row is None:
                df.columns = [f"Column {i + 1}" for i in range(len(df.columns))]

            # Time steps data
            if self.logger.first_col_data == "Time Step":
                # If filename contains timestamp info, replace time column with timestamp
                if self.logger.file_timestamp_embedded is True:
                    ts = df.iloc[:, 0].values
                    start_timestamp = self.logger.file_timestamps[file_idx]
                    timestamps = [start_timestamp + timedelta(seconds=t) for t in ts]
                    df.iloc[:, 0] = timestamps
                else:
                    self.first_col = "Time"
            #  Convert first column (should be timestamps string) to datetimes
            else:
                try:
                    df.iloc[:, 0] = pd.to_datetime(
                        df.iloc[:, 0], format=self.logger.datetime_format
                    )
                # TODO: isinstance error doesn't seem to work - get rid of error
                # except ValueError as e:
                #     try:
                #         # Try without code but could be a lot slower
                #         # TODO: Warn code is bad and slow
                #         df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
                except ValueError as e:
                    msg = (
                        f"Could not convert the first column of {self.logger.files[file_idx]} to datetime.\n\n"
                        f"If the first column is expected to be a time step index, ensure the 'First column data' "
                        f"property is set to 'Time Step'. Otherwise, check the 'Data Timestamp' property is the "
                        f"correct format.\n\n<{e}>"
                    )
                    raise ValueError(msg)

        # Convert first column (should be timestamps string) to datetimes
        if self.logger.file_format == "Fugro-csv":
            df.iloc[:, 0] = pd.to_datetime(
                df.iloc[:, 0], format=self.logger.datetime_format, errors="coerce"
            )

        # Trim column names
        df.columns = [c.strip() for c in df.columns]

        # Convert any non-numeric data to NaN
        df.iloc[:, 1:] = df.iloc[:, 1:].apply(pd.to_numeric, errors="coerce")

        return df

    def select_columns_to_process(self, df):
        """Select columns to screen on."""

        # Check all requested columns exist in file
        n = len(df.columns)
        missing_cols = [x for x in self.use_cols if x >= n]
        valid_cols = [x for x in self.use_cols if x < n]

        # Slice valid columns
        df = df.iloc[:, valid_cols]

        # Create dummy data for missing columns
        for i in missing_cols:
            df["Dummy " + str(i + 1)] = np.nan

        return df

    def set_column_names(self, df):
        """Replace column names with logger setup channel names - only different if user names supplied."""

        df.columns = [self.first_col] + self.channel_names
        return df

    def apply_unit_conversions(self, df):
        """Apply any unit conversions."""

        if len(self.unit_conv_factors) == len(df.columns) - 1:
            try:
                df.iloc[:, 1:] = np.multiply(df.iloc[:, 1:], self.unit_conv_factors)
            except TypeError as e:
                msg = f"Data screen error: Dataframe contains no channel columns.\n {e}"
                raise TypeError(msg)

        return df

    def screen_data(self, file_num, df):
        """Perform basic data screening operations on dataframe."""

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
        Return smallest difference between rows of a dataframe for each
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
        :param df_sample: Current subset dataframe of main logger file (initially empty)
        :param df: Current logger file dataframe (sample data gets dropped)
        :param sample_length: Number of expected data points sample is to have
        :param type: stats or spectral string
        :return: Updated sample dataframe and logger file dataframe with sample data dropped
        """

        # if type == "stats":
        #     sample_length = self.stats_sample_length
        # elif type == "spectral":
        #     sample_length = self.spect_sample_length

        # Current number of points in sample
        ns = len(df_sample)

        # Number of points in data
        nd = len(df)

        # Number of points to append to sample - sample_length is the target number of sample points
        cutoff = min(sample_length - ns, nd)

        if ns < sample_length and nd > 0:
            # Append data to sample dataframe and drop sample from main dataframe
            df_sample = df_sample.append(df[:cutoff].copy(), ignore_index=True)
            df.drop(df.index[:cutoff], inplace=True)

            # TODO: Allowing short sample length (revisit)
            # Store start and end times of sample data if dataframe contains target length
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

        # Timestamps/time column
        t = df.iloc[:, 0]

        # Need index to be time - calculate time delta from t0 and convert to seconds (float) then set as index
        if self.file_timestamp_embedded is True:
            df.index = (df.iloc[:, 0] - df.iloc[0, 0]).dt.total_seconds().values.round(3)
            df.drop(df.columns[0], axis=1, inplace=True)
        else:
            df.set_index(df.columns[0], inplace=True)

        # Apply filter on all dataframe time series
        if self.filter_type == "butterworth":
            df_filtered = apply_butterworth_filter(df, self.sos_filter)

            # Reapply mean
            if self.low_cutoff is not None:
                df_filtered = add_signal_mean(df, df_filtered)
        else:
            df_filtered = apply_rectangular_filter(df, self.low_cutoff, self.high_cutoff)

        if not df_filtered.empty:
            # Insert timestamps/time column and reset index to return a dataframe in same format as unfiltered one
            df_filtered.reset_index(drop=True, inplace=True)
            df_filtered.insert(loc=0, column=t.name, value=t)

        return df_filtered
