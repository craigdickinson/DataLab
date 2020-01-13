"""Tests for the routines to calculate rainflow counting fatigue."""
__author__ = "Craig Dickinson"

import numpy as np
import pytest
import rainflow
from numpy.testing import assert_allclose

from core.rainflow_fatigue import (
    rainflow_cycles,
    number_of_bins,
    bin_cycles,
    histogram,
    calc_damage,
)


def test_rainflow_counting():
    y = [1, 5, 2, 1, 3, 1]
    ranges, num_cycles = rainflow_cycles(y)
    assert_allclose(ranges, [2, 4])
    assert_allclose(num_cycles, [1, 0.5])


def test_bin_cycles():
    ranges = [2, 4]
    cycles = [1, 0.5]

    bin_size = 1
    num_bins = number_of_bins(ranges[-1], bin_size)
    bin_edges, hist = bin_cycles(ranges, cycles, num_bins, bin_size)
    assert_allclose(bin_edges, [0, 1, 2, 3, 4, 5])
    assert_allclose(hist, [0, 0, 1, 0, 0.5])

    bin_size = 3
    num_bins = number_of_bins(ranges[-1], bin_size)
    bin_edges, hist = bin_cycles(ranges, cycles, num_bins, bin_size)
    assert_allclose(bin_edges, [0, 3, 6])
    assert_allclose(hist, [1, 0.5])

    bin_size = 4
    num_bins = number_of_bins(ranges[-1], bin_size)
    bin_edges, hist = bin_cycles(ranges, cycles, num_bins, bin_size)
    assert_allclose(bin_edges, [0, 4])
    assert_allclose(hist, [1.5])


def test_calc_damage():
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

    y = np.array([1, 5, 2, 1, 3, 1])
    ranges, num_cycles = rainflow_cycles(y)
    fd = calc_damage(ranges, num_cycles, SN)
    assert float(f"{fd:.6}") == 2.33039e-10

    #  Bin size = 1 for rainflow with left=True (include first point as a reversal)
    # assert float(f"{fd:.6}") == 4.40185e-10

    bin_size = 1
    bin_edges, hist = histogram(y, bin_size)
    lb = bin_edges[:-1]
    ub = bin_edges[1:]
    lfd = calc_damage(lb, hist, SN)
    ufd = calc_damage(ub, hist, SN)

    assert float(f"{lfd:.6}") == 2.33039e-10
    assert float(f"{ufd:.6}") == 6.36811e-10


if __name__ == "__main__":
    pytest.main()
