"""Module to calculate fatigue damage using rainflow counting."""

__author__ = "Craig Dickinson"

import os

import numpy as np
import pandas as pd
import rainflow

from core.control import Control
from core.data_screen import DataScreen


class CycleHistograms(object):
    def __init__(self, control=Control()):
        self.logger_id = ""
        self.output_dir = control.hist_output_path
        self.dict_df_col_hists = {}
        self.channels = []
        self.units = []
        self.channel_bin_sizes = []
        self.channel_num_bins = []

        # If writing stats HDF5 file, stats for all loggers are written to the same file
        # Set write mode to write new file for first logger then append for all others
        self.h5_write_mode = "w"
        self.h5_output_file_suffix = ""

        # Dictionary of True/False flags of histogram output file formats to create
        self.dict_hist_export_formats = dict(
            csv=control.hist_to_csv, xlsx=control.hist_to_xlsx, h5=control.hist_to_h5,
        )

    def init_dataset(self, data_screen: DataScreen):
        self.logger_id = data_screen.logger_id
        self.channels = data_screen.logger.channel_names
        self.units = data_screen.logger.channel_units
        self.channel_bin_sizes = data_screen.logger.channel_bin_sizes
        self.channel_num_bins = data_screen.logger.channel_num_bins
        self.dict_df_col_hists = {channel: pd.DataFrame() for channel in self.channels}

        self._review_histogram_settings()

    def _review_histogram_settings(self):
        """Review bins size and number of bins inputs."""

        nc = len(self.channels)
        ns = len(self.channel_bin_sizes)
        nb = len(self.channel_num_bins)

        if ns != nc:
            if ns == 1:
                self.channel_bin_sizes = [self.channel_bin_sizes[0]] * nc

        if nb != nc:
            if nb == 1:
                self.channel_num_bins = [self.channel_num_bins[0]] * nc

    def calc_histograms_on_dataframe(
        self, df_file: pd.DataFrame, filename, data_screen: DataScreen
    ):
        """Calculate rainflow counting histograms of each channel in the (file) dataframe."""

        filename = os.path.splitext(filename)[0]

        for i, col in enumerate(self.channels):
            # Retrieve bin size and num bins
            try:
                bin_size = self.channel_bin_sizes[i]
            except IndexError:
                bin_size = None

            # Check for user supplied number of bins
            try:
                num_bins = self.channel_num_bins[i]
            except IndexError:
                num_bins = None

            # Get histogram for column i
            y = df_file[col].values.flatten()
            bin_edges, hist = histogram(y, bin_size, num_bins)

            # Add histogram to dataframe
            if hist.size > 0:
                # Convert to dataframe - index with lower bound bins
                df_temp = pd.DataFrame(hist, index=bin_edges[:-1], columns=[filename])
                df_temp.index.name = f"Bins ({self.units[i]})"

                # Join to existing dataframe
                df_hist = self.dict_df_col_hists[col]
                self.dict_df_col_hists[col] = df_hist.join(df_temp, how="outer")

        data_screen.histograms_processed = True

        return self.dict_df_col_hists

    def calc_aggregate_histograms(self):
        """Add aggregate histograms row to each channel dataframe."""

        for col, df_hist in self.dict_df_col_hists.items():
            df_hist.fillna(0, inplace=True)
            df_hist.insert(0, "Aggregate", df_hist.sum(axis=1))
            self.dict_df_col_hists[col] = df_hist

        return self.dict_df_col_hists

    def export_histograms(self):
        """Export histograms to selected output formats."""

        output_files = []

        if self.dict_hist_export_formats["csv"] is True:
            output_files_csv = export_histograms_to_csv(
                self.dict_df_col_hists, self.output_dir, self.logger_id
            )
            output_files.extend(output_files_csv)

        if self.dict_hist_export_formats["xlsx"] is True:
            output_file_xlsx = export_histograms_to_excel(
                self.dict_df_col_hists, self.output_dir, self.logger_id
            )
            output_files.append(output_file_xlsx)

        if self.dict_hist_export_formats["h5"] is True:
            output_file_h5 = export_histograms_to_hdf5(
                self.dict_df_col_hists, self.output_dir, self.logger_id, self.h5_write_mode
            )
            output_files.append(output_file_h5)
            self.h5_write_mode = "a"

        return output_files


def histogram(y, bin_size=1, num_bins=None):
    """
    Compute rainflow counting histogram of time series y.
    Three stages:
    1. Do rainflow counting on series
    2. Get required number of bins
    3. Bin rainflow cycles
    """

    ranges, cycles = rainflow_cycles(y)
    max_range = ranges[-1]
    max_bins = 500

    if bin_size is None and num_bins is None:
        return np.array([]), np.array([])

    if bin_size is None:
        bin_size = calc_bin_size(max_range, num_bins)

    if num_bins is None:
        num_bins = calc_number_of_bins(max_range, bin_size)

    if num_bins > max_bins:
        print(
            f"\nNumber of bins = {num_bins}. Too many! Number of bins set to 500. Suggest to use a larger bin size."
        )
        num_bins = max_bins
    else:
        print(f"\nNumber of bins = {num_bins}.")

    bin_edges, hist = bin_cycles(ranges, cycles, num_bins, bin_size)

    return bin_edges, hist


def rainflow_cycles(y):
    """Use rainflow package to count number of cycles in an array."""

    # Settings mimic output of OrcaFlex OrcFxAPI.RainflowHalfCycles function
    cycles = rainflow.count_cycles(y, left=False, right=True)

    # Split tuple and convert to arrays
    cycle_range, num_cycles = zip(*cycles)
    cycle_range = np.asarray(cycle_range)
    num_cycles = np.asarray(num_cycles)

    return cycle_range, num_cycles


def calc_bin_size(max_range, num_bins=10):
    """Use max range and number of bins to calculate bins size to use in histogram."""

    #  Round up to 3dp
    bin_size = round_up(max_range / num_bins, decimals=3)

    return bin_size


def calc_number_of_bins(max_range, bin_size=1):
    """Use max range and bin size to calculate number of bins required in histogram."""

    if max_range == bin_size:
        num_bins = np.ceil(max_range / bin_size).astype(int)
    else:
        # We add a delta to ensure integers are rounded up to give the last bin
        num_bins = np.ceil((max_range + 1e-9) / bin_size).astype(int)

    return num_bins


def bin_cycles(ranges, cycles, num_bins=10, bin_size=1):
    """Bin rainflow counting cycles based on number of bins and bin size input."""

    bin_edges = calc_bin_intervals(num_bins, bin_size)
    ranges = np.asarray(ranges)
    cycles = np.asarray(cycles)

    # Get bin index of each range
    bin_locs = np.floor(ranges / bin_size).astype(int)
    unique_bins = np.unique(bin_locs)

    # Bin cycles
    # If bin size equals the last cycle range then we only want one bin, which all cycles fall into
    if num_bins == 1:
        hist = np.array(
            [cycles[bin_locs == i].sum() if i in unique_bins else 0 for i in range(num_bins + 1)]
        )
        hist = np.array([hist.sum()])
    else:
        hist = np.array(
            [cycles[bin_locs == i].sum() if i in unique_bins else 0 for i in range(num_bins)]
        )

    return bin_edges, hist


def calc_bin_intervals(num_bins=10, bin_size=1):
    """Return bins edges. """

    return np.arange(num_bins + 1) * bin_size


def export_histograms_to_csv(dict_df_col_hists, dir_path, logger_id):
    """Export dataset histograms to csv."""

    output_files = []
    folder = os.path.basename(dir_path)
    filestem = f"Histograms {logger_id}"

    for channel, df in dict_df_col_hists.items():
        filename = f"{filestem} {channel}.csv"
        filepath = os.path.join(dir_path, filename)
        df.to_csv(filepath)

        # Add to output files list - to write to progress window
        rel_filepath = folder + "/" + filename
        output_files.append(rel_filepath)

    return output_files


def export_histograms_to_excel(dict_df_col_hists, dir_path, logger_id):
    """Export dataset histograms to Excel."""

    folder = os.path.basename(dir_path)
    filename = f"Histograms {logger_id}.xlsx"
    filepath = os.path.join(dir_path, filename)
    writer = pd.ExcelWriter(filepath)

    for channel, df in dict_df_col_hists.items():
        df.to_excel(writer, sheet_name=channel)

    writer.save()

    # Output file relative path - to write to progress window
    rel_filepath = folder + "/" + filename

    return rel_filepath


def export_histograms_to_hdf5(dict_df_col_hists, dir_path, logger_id, mode="w"):
    """Export dataset histograms to HDF5 file."""

    folder = os.path.basename(dir_path)
    filename = "Histograms.h5"

    for channel, df in dict_df_col_hists.items():
        filepath = os.path.join(dir_path, filename)
        key = f"{logger_id}_{channel}".replace(" ", "_")
        df.to_hdf(filepath, key, mode=mode)

    # Output file relative path - to write to progress window
    rel_filepath = folder + "/" + filename

    return rel_filepath


def calc_damage(stress_ranges, stress_cycles, SN):
    """Calculate fatigue damage using Miner's rule."""

    stress_ranges = np.asarray(stress_ranges)
    stress_cycles = np.asarray(stress_cycles)

    # Drop zero cycles
    nonzero_idx = np.where(stress_cycles > 0)
    stress_ranges = stress_ranges[nonzero_idx]
    stress_cycles = stress_cycles[nonzero_idx]

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


def round_up(n, decimals=0):
    multiplier = 10 ** decimals
    return np.ceil(n * multiplier) / multiplier


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
    ranges, num_cycles = rainflow_cycles(y)

    # Fatigue damage of actual stress ranges
    print(f"Stress ranges = {ranges}")
    print(f"Stress cycles = {num_cycles}")
    fd = calc_damage(ranges, num_cycles, SN)
    print(fd)

    # Fatigue damage of binned stress ranges
    bin_size = 1
    bin_edges, hist = histogram(y, bin_size)
    lb = bin_edges[:-1]
    ub = bin_edges[1:]
    print(f"Lower bins = {lb}")
    print(f"Upper bins = {ub}")
    print(f"Hist cycles = {hist}")
    lfd = calc_damage(lb, hist, SN)
    ufd = calc_damage(ub, hist, SN)
    print(lfd)
    print(ufd)
