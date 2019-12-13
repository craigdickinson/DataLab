"""Module to calculate fatigue damage using rainflow counting."""

__author__ = "Craig Dickinson"

import numpy as np
import pandas as pd
import rainflow


def rainflow_count_data_frame(dict_df_col_hists, j, df, columns, bin_size=0.1):
    """Calculate rainflow counting histogram for each channel in data frame."""

    # Calculate rainflow counting histogram for each column
    for col in columns:
        # Get histogram for column i
        y = get_column_series(df, col)
        lb, ub, binned_cycles = calc_hist(y, bin_size)

        # Convert to data frame
        df_temp = pd.DataFrame(binned_cycles, index=lb, columns=[f"File {j + 1}"])

        # Join to existing data frame
        df_hist = dict_df_col_hists[col]
        dict_df_col_hists[col] = df_hist.join(df_temp, how="outer")

    return dict_df_col_hists


def get_column_series(df, col):
    return df[col].values.flatten()


def calc_hist(y, bin_size):
    """Compute rainflow counting histogram of time series y."""

    ranges, num_cycles = rainflow_counting(y)

    # Use last range to get number of bins required
    # (add a delta to handle case of range equalling bin limit)
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
    ranges, num_cycles = rainflow_counting(y)

    # Fatigue damage of actual stress ranges
    print(f"Stress ranges = {ranges}")
    print(f"Stress cycles = {num_cycles}")
    fd = calc_damage(ranges, num_cycles, SN)
    print(fd)

    # Fatigue damage of binned stress ranges
    bin_size = 1
    req_num_bins = np.ceil((ranges[-1] + 1e-9) / bin_size).astype(int)
    lb, ub = create_hist_bins(req_num_bins, bin_size)
    binned_cycles = bin_cycles(ranges, num_cycles, req_num_bins, bin_size)
    print(f"Stress ranges = {ub}")
    print(f"Stress cycles = {binned_cycles}")
    fd = calc_damage(ub, binned_cycles, SN)
    print(fd)
