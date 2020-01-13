"""Module to calculate fatigue damage using rainflow counting."""

__author__ = "Craig Dickinson"

import numpy as np
import pandas as pd
import rainflow


def file_histograms_processing(dict_df_col_hists, df_file, data_screen, file_num):
    """Calculate histograms on a file."""

    bin_size = data_screen.logger.bin_size
    dict_df_col_hists = dataframe_histogram(dict_df_col_hists, file_num, df_file, bin_size)

    data_screen.histograms_processed = True

    return dict_df_col_hists


def dataframe_histogram(dict_df_col_hists, j, df, bin_size=1):
    """Calculate rainflow counting histogram for each channel in data frame."""

    # Calculate (binned) histogram for each column using rainflow counting
    for col in df.columns:
        # Get histogram for column i
        y = df[col].values.flatten()
        bin_edges, hist = histogram(y, bin_size)

        # Convert to data frame - index with lower bound bins
        df_temp = pd.DataFrame(hist, index=bin_edges[:-1], columns=[f"File {j}"])

        # Join to existing data frame
        df_hist = dict_df_col_hists[col]
        dict_df_col_hists[col] = df_hist.join(df_temp, how="outer")

    return dict_df_col_hists


def histogram(y, bin_size=1):
    """
    Compute rainflow counting histogram of time series y.
    Three stages:
    1. Do rainflow counting on series
    2. Get required number of bins
    3. Bin rainflow cycles
    """

    ranges, cycles = rainflow_cycles(y)
    num_bins = number_of_bins(ranges[-1], bin_size)
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


def number_of_bins(last_range, bin_size=1):
    """Use last range and bin size to get number of bins required in histogram."""

    if last_range == bin_size:
        num_bins = np.ceil(last_range / bin_size).astype(int)
    else:
        # We add a delta to ensure integers are rounded up to give the last bin
        num_bins = np.ceil((last_range + 1e-9) / bin_size).astype(int)

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
        hist = np.asarray(hist.sum())
    else:
        hist = np.array(
            [cycles[bin_locs == i].sum() if i in unique_bins else 0 for i in range(num_bins)]
        )

    return bin_edges, hist


def calc_bin_intervals(num_bins=10, bin_size=1):
    """Return bins edges. """

    return np.arange(num_bins + 1) * bin_size


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
