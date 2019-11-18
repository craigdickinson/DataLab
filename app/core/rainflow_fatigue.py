"""Module to calculate fatigue damage using rainflow counting."""

__author__ = "Craig Dickinson"

import os
from datetime import timedelta

import numpy as np
import pandas as pd
import rainflow
from app.core.logger_properties import LoggerProperties
from app.core.read_files import read_2hps2_acc, read_pulse_acc


class RainflowHistograms(object):
    def __init__(self, logger=None):
        self.logger = LoggerProperties()
        self.files = []
        self.histograms = {}
        self.cols = []

        # File read properties
        self.file_format = "Custom"
        self.delim = ","
        self.header_row = 0
        self.skip_rows = []
        self.use_cols = []
        self.channel_names = []
        self.unit_conv_factors = []
        self.file_timestamp_embedded = True

        if logger:
            self.set_logger(logger)

    def set_logger(self, logger):
        """Set the logger filenames to be assessed and required read file properties."""

        self.logger = logger
        self.channel_names = logger.channel_names

        # Full file path
        self.files = [os.path.join(logger.logger_path, f) for f in logger.files]

        # File format (i.e. Custom/Fugro/Pulse/2HPS2")
        self.file_format = self.logger.file_format

        # Whether filenames contain timestamps
        self.file_timestamp_embedded = self.logger.file_timestamp_embedded

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
        self.use_cols = set([0] + [c - 1 for c in self.logger.rf_cols_to_process])

        # Unit conversion factors
        self.unit_conv_factors = logger.unit_conv_factors

    def read_logger_file(self, file):
        """Read logger file into data frame."""

        # Read data to data frame
        if self.file_format == "Custom":
            df = pd.read_csv(
                file,
                sep=self.delim,
                header=self.header_row,
                skiprows=self.skip_rows,
                skip_blank_lines=False,
            )
        elif self.file_format == "Fugro-csv":
            df = pd.read_csv(
                file,
                sep=self.delim,
                header=self.header_row,
                skiprows=self.skip_rows,
                encoding="latin1",
            )
        elif self.file_format == "Pulse-acc":
            df = read_pulse_acc(file, multi_header=False)
        elif self.file_format == "2HPS2-acc":
            df = read_2hps2_acc(file, multi_header=False)
        else:
            df = pd.DataFrame()

        return df

    def data_wrangle(self, df, file_idx=0):
        """Format the logger raw data so it is suitable for processing."""

        # Copy to prevent SettingWithCopyWarning
        df = df.copy()
        first_col = "Timestamp"

        if self.logger.file_format == "Custom":
            df = df.dropna(axis=1)

            # Time steps data
            if self.logger.first_col_data == "Time Step":
                # If filename contains timestamp info, replace time column with timestamp
                if self.logger.file_timestamp_embedded is True:
                    ts = df.iloc[:, 0].values
                    start_timestamp = self.logger.file_timestamps[file_idx]
                    timestamps = [start_timestamp + timedelta(seconds=t) for t in ts]
                    df.iloc[:, 0] = timestamps
                else:
                    first_col = "Time"
            #  Convert first column (should be timestamps string) to datetimes
            else:
                try:
                    df.iloc[:, 0] = pd.to_datetime(
                        df.iloc[:, 0], format=self.logger.datetime_format
                    )
                except ValueError as e:
                    if not isinstance(df.iloc[0, 0], pd.Timestamp):
                        raise ValueError(
                            f"Expected the first column of {self.logger.files[file_idx]} "
                            f"to contain dates.\n"
                            f"The time series appears to use a time step index but the "
                            f"'First column data' property is set to 'Timestamp'. Change this to 'Time Step'."
                        )
                    else:
                        raise ValueError(
                            f"Could not convert the first column of {self.logger.files[file_idx]} "
                            f"to datetime.\n"
                            f"Check the 'Data Timestamp' property has the correct format.\n\n<{e}>"
                        )

        #  Convert first column (should be timestamps string) to datetimes
        if self.logger.file_format == "Fugro-csv":
            df.iloc[:, 0] = pd.to_datetime(
                df.iloc[:, 0], format=self.logger.datetime_format, errors="coerce"
            )

        # Check all requested columns exist in file
        n = len(df.columns)
        missing_cols = [x for x in self.use_cols if x >= n]
        valid_cols = [x for x in self.use_cols if x < n]

        # Slice valid columns
        df = df.iloc[:, valid_cols]

        # Create dummy data for missing columns
        for i in missing_cols:
            df["Dummy " + str(i + 1)] = np.nan

        # Convert any non-numeric data to NaN
        df.iloc[:, 1:] = df.iloc[:, 1:].apply(pd.to_numeric, errors="coerce")

        # Apply any unit conversions
        # TODO: If no cols to process selected should default to all columns
        if len(self.unit_conv_factors) == len(df.columns) - 1:
            try:
                df.iloc[:, 1:] = np.multiply(df.iloc[:, 1:], self.unit_conv_factors)
            except TypeError as e:
                msg = (
                    f"Data screen error: Data frame contains no channel columns.\n {e}"
                )
                raise TypeError(msg)

        # Replace column names with setup channel names (should only be different if user names supplied)
        df.columns = [first_col] + self.channel_names

        return df


def get_column_series(df, col):
    return df[col].values.flatten()


def rainflow_count_data_frame(dict_df_col_hists, j, df, columns, bin_size=0.1):
    """Calculate rainflow counting histogram for each channel in data frame."""

    # Calculate rainflow counting histogram for each column
    for col in columns:
        # Get histogram for column i
        y = get_column_series(df, col)
        lb, ub, binned_cycles = get_hist(y, bin_size=0.01)

        # Convert to data frame
        df_temp = pd.DataFrame(binned_cycles, index=lb, columns=[f"File {j + 1}"])

        # Join to existing data frame
        df_hist = dict_df_col_hists[col]
        dict_df_col_hists[col] = df_hist.join(df_temp, how="outer")

    return dict_df_col_hists


def get_hist(y, bin_size):
    """Compute rainflow counting histogram of time series y."""

    ranges, num_cycles = rainflow_counting(y)

    # Use last range to get number of bins required - we add an epsilon to handle case of range equalling bin limit
    req_num_bins = np.ceil((ranges[-1] + 1e-9) / bin_size).astype(int)

    # Create lbound and ubound bins
    lb, ub = create_hist_bins(req_num_bins, bin_size)

    binned_cycles = bin_cycles(ranges, num_cycles, req_num_bins, bin_size)

    return lb, ub, binned_cycles


def rainflow_counting(y):
    """Use rainflow package to count number of cycles in an array."""

    cycles = rainflow.count_cycles(y, left=True, right=True)

    # Split tuple and convert to arrays
    ranges, num_cycles = zip(*cycles)
    ranges = np.asarray(ranges)
    num_cycles = np.asarray(num_cycles)

    return ranges, num_cycles


def create_hist_bins(num_bins, bin_size):
    lb = np.arange(0, num_bins) * bin_size
    ub = lb + bin_size

    return lb, ub


def bin_cycles(ranges, num_cycles, num_bins, bin_size):
    """Bin rainflow counting cycles based on number of bins and bin size input."""

    # Get bin index of each range
    bin_locs = np.floor(ranges / bin_size).astype(int)
    unique_bins = np.unique(bin_locs)

    # Bin cycles
    binned_cycles = [
        num_cycles[bin_locs == i].sum() if i in unique_bins else 0
        for i in range(num_bins)
    ]

    return np.array(binned_cycles)


def calc_damage(stress_ranges, stress_cycles, SN):
    """Calculate fatigue damage using Miner's rule."""

    stress_ranges = np.asarray(stress_ranges)
    stress_cycles = np.asarray(stress_cycles)
    sn_region = np.zeros(len(stress_ranges)).astype(int)

    for i in range(len(SN)):
        a = SN[i]["a"]
        n_trans = SN[i]["trans"]
        k = SN[i]["k"]
        trans_stress = calc_transition_stress(a, n_trans, k)
        sn_region[stress_ranges < trans_stress] = i

    # Get SN curve parameters belonging to region of each stress range
    a = np.array([SN[sn_region[i]]["a"] for i in range(len(stress_ranges))])
    k = np.array([SN[sn_region[i]]["k"] for i in range(len(stress_ranges))])
    SCF = np.array([SN[sn_region[i]]["SCF"] for i in range(len(stress_ranges))])
    n_fail = a * (SCF * stress_ranges) ** -k

    bin_damage = stress_cycles / n_fail
    damage = bin_damage.sum()

    return damage


def calc_transition_stress(a, n_trans, k):
    return (a / n_trans) ** (1 / k)


if __name__ == "__main__":
    # S-N curve parameters
    SN = [{}]
    SN[0]["a"] = 4.3072e11
    SN[0]["k"] = 3
    SN[0]["trans"] = 1e7
    SN[0]["SCF"] = 1.25

    SN.append({})
    SN[1]["a"] = 1.5086e12
    SN[1]["k"] = 4
    SN[1]["trans"] = 1e7
    SN[1]["SCF"] = 1.25

    # x = np.arange(10)
    # y = np.sin(x)
    y = [1, 5, 2, 1, 3, 1]
    peaks = reversals(y)
    print(peaks)
    cycles_array = extract_cycles(peaks)
    print(cycles_array)

    # Fatigue damage of actual stress ranges
    stress_ranges = cycles_array[:, 0]
    stress_cycles = cycles_array[:, 1]
    print(f"Stress ranges = {stress_ranges}")
    print(f"Stress cycles = {stress_cycles}")
    fd = calc_damage(stress_ranges, stress_cycles, SN)
    print(fd)

    # Fatigue damage of binned stress ranges
    stress_ranges, stress_cycles = bin_ranges(cycles_array, bin_size=4)
    # stress_ranges, stress_cycles = bin_ranges(cycles_array, bin_size=1)
    print(f"Stress ranges = {stress_ranges}")
    print(f"Stress cycles = {stress_cycles}")
    fd = calc_damage(stress_ranges, stress_cycles, SN)
    print(fd)
