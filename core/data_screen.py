"""
Created on 9 Aug 2016

@author: bowdenc
"""

import os.path

import numpy as np
import pandas as pd

from core.logger_properties import LoggerProperties


class DataScreen(object):
    """Screen data from a list of filenames and store stats."""

    def __init__(self):
        """Instantiate with empty logger."""

        self.logger = LoggerProperties('')
        self.files = []

        # Dictionary of files with errors for specified logger
        self.bad_files = {}

        # Number of points per file
        self.points_per_file = []

        # Minimum resolution
        # TODO: Output this in data screen report
        self.res = []

        self.header = []
        self.units = []

        # Lists for sample beginning and end times
        self.sample_start = []
        self.sample_end = []

        # Interval to calculate stats over
        self.sample_length = 0

        # csv read properties
        self.header_row = 0
        self.skip_rows = []
        self.use_cols = []

    def set_logger(self, logger):
        """Pass in the logger filenames and properties to be assessed."""

        self.logger = logger

        # Set full file path
        self.files = [os.path.join(self.logger.logger_path, f)
                      for f in self.logger.files]

        # Set csv read properties
        self.header_row = self.logger.channel_header_row - 1

        self.skip_rows = [i for i in range(self.logger.num_headers)
                          if i > self.header_row]

        self.use_cols = [0] + self.logger.stats_cols

        # No header row specified
        if self.header_row < 0:
            self.header_row = None

    def set_sample_length(self):
        """Convert sample length from seconds to number of data points."""

        self.sample_length = int(self.logger.stats_interval * self.logger.freq)

    def read_logger_file(self, f):
        """Process requested actions for all files."""

        # Read data in to Pandas data frame
        data = self.read_data(f,
                              self.logger.file_delimiter,
                              self.header_row,
                              self.skip_rows,
                              self.use_cols)

        # Column names
        columns = data.columns

        # Process first column - should be time
        data[columns[0]] = self.parse_timestamp(data[columns[0]],
                                                self.logger.datetime_format)

        # Convert any non numeric to NaN
        data[columns[1:]] = self.parse_numeric(data[columns[1:]])

        return data

    def read_data(self, fname, delim, header, skip_rows, use_cols):
        """Read logger file data into Pandas data frame."""

        df = pd.read_csv(fname,
                         sep=delim,
                         header=header,
                         skiprows=skip_rows,
                         engine='c',
                         encoding='utf-8')

        # Check stats columns exist in file
        n = len(df.columns)
        missing_cols = [x for x in use_cols if x >= n]
        valid_cols = [x for x in use_cols if x < n]

        # Slice valid columns
        df = df.iloc[:, valid_cols]

        # Create dummy data for missing columns
        for i in missing_cols:
            df['Dummy' + str(i + 1)] = np.nan

        # try:
        #     df2 = df[df.columns[use_cols]]
        # except ValueError as e:
        #     print(str(e))

        return df

        # df = pd.read_csv(fname,
        #                  sep=delim,
        #                  header=header,
        #                  usecols=use_cols,
        #                  skiprows=skip_rows,
        #                  engine='c',
        #                  encoding='utf-8')
        # return df
        # try:
        #     df = pd.read_csv(fname,
        #                      sep=delim,
        #                      header=header,
        #                      usecols=use_cols,
        #                      skiprows=skip_rows,
        #                      engine='c',
        #                      encoding='utf-8')
        #     return df
        # except ValueError as e:
        #     raise ValueError(str(e))

    def parse_timestamp(self, df, fmt):
        """Convert DataFrame column of text to datetime data must be a column of a data frame."""

        if fmt == 'DETECT':
            # This is very slow
            df = pd.to_datetime(df,
                                infer_datetime_format=True,
                                errors='coerce')
        else:
            # Much faster
            df = pd.to_datetime(df,
                                format=fmt,
                                errors='coerce')
        return df

    def parse_numeric(self, df):
        """Convert data from string to numeric."""

        df = df.apply(pd.to_numeric, errors='coerce')
        return df

    def screen_data(self, file_num, df):
        """Perform basic data screening operations on data frame."""

        # Number of points in file
        # pts = min(data.count())
        pts = len(df)
        self.points_per_file.append(pts)

        # Check number of points is valid
        if pts != self.logger.expected_data_points:
            filename = self.logger.files[file_num]
            self.bad_files[filename] = 'Unexpected number of points'
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

    def sample_dataframe(self, sample_df, df):
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
        cutoff = min(self.sample_length - ns, nd)

        if ns < self.sample_length and nd > 0:
            # Append data to sample data frame and drop sample from main data frame
            sample_df = sample_df.append(df[:cutoff].copy(), ignore_index=True)
            df.drop(df.index[:cutoff], inplace=True)

            # TODO: Allowing short sample length (revisit)
            # Store start and end times of sample data if data frame contains target length
            # if len(sample_df) == self.sample_length:
            if len(sample_df) <= self.sample_length:
                self.sample_start.append(sample_df.iloc[0, 0])
                self.sample_end.append(sample_df.iloc[-1, 0])

        return sample_df, df
