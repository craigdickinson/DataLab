"""
Module to calculate fatigue damage using rainflow counting.
"""
__author__ = "Craig Dickinson"

import numpy as np


def condense_peaks(y):
    """Return time series peaks."""

    y = np.asarray(y)
    dy = np.sign(np.diff(y))
    dy[1:] = [dy[i - 1] if dy[i] == 0 else dy[i] for i in range(1, len(dy))]

    d2y = np.abs(np.sign(np.diff(dy)))
    d2y = np.insert(d2y, 0, 1)
    d2y = np.insert(d2y, -1, 1)

    peaks = y[d2y == 1]
    indexes = np.nonzero(d2y == 1)
    num_peaks = len(peaks)

    return peaks, num_peaks


def count_cycles(peaks, num_peaks):
    """Rainflow counting algorithm from ASTM E 1049-85."""

    cycles_range = np.zeros((num_peaks, 3))
    cycl_count = -1
    points = []

    for x in peaks:
        points.append(x)

        while len(points) >= 3:
            X = abs(points[-1] - points[-2])
            Y = abs(points[-2] - points[-3])

            if X < Y:
                break

            mean_stress = np.mean(points[-3:-1])

            if len(points) == 3:
                points.pop(0)

                # if Y >= 0:
                cycl_count += 1
                cycles_range[cycl_count, 0] = Y
                cycles_range[cycl_count, 1] = 0.5
                cycles_range[cycl_count, 2] = mean_stress
                break
            else:
                points[-3] = points[-1]
                points.pop()
                points.pop()

                # if Y >= 0:
                cycl_count += 1
                cycles_range[cycl_count, 0] = Y
                cycles_range[cycl_count, 1] = 1
                cycles_range[cycl_count, 2] = mean_stress

    while len(points) > 1:
        Y = abs(points[1] - points[0])
        mean_stress = np.mean(points[:2])
        points.pop(0)

        # if Y >= 0:
        cycl_count += 1
        cycles_range[cycl_count, 0] = Y
        cycles_range[cycl_count, 1] = 0.5
        cycles_range[cycl_count, 2] = mean_stress

    cycles_range = np.delete(cycles_range, np.s_[cycl_count + 1 :], axis=0)

    return cycles_range


def bin_ranges(cycles, bin_size=1):
    """Group stress ranges into bins of size input."""

    bin_locs = np.ceil(cycles[:, 0] / bin_size).astype(int)
    unique_bins = np.unique(bin_locs)
    stress_ranges = unique_bins * bin_size
    stress_cycles = [
        cycles[bin_locs == unique_bin, 1].sum() for unique_bin in unique_bins
    ]

    return stress_ranges, stress_cycles


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
    SN = []
    SN.append({})
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
    peaks, n = condense_peaks(y)
    print(peaks)
    cycles_range = count_cycles(peaks, n)
    print(cycles_range)
    stress_ranges, stress_cycles = bin_ranges(cycles_range)
    print(stress_ranges)
    print(stress_cycles)
    fd = calc_damage(stress_ranges, stress_cycles, SN)
    print(fd)
