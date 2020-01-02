"""Tests for the routines to calculate rainflow counting fatigue."""
__author__ = "Craig Dickinson"

import numpy as np
import pytest
import rainflow
from numpy.testing import assert_allclose

from core.rainflow_fatigue import bin_ranges, calc_damage, extract_cycles, reversals


def test_condense_peaks():
    y = [1, 5, 2, 1, 3, 1]
    p = reversals(y)

    res = [1, 5, 1, 3, 1]
    assert_allclose(p, res)


def test_count_cycles():
    y = [1, 5, 2, 1, 3, 1]
    p = reversals(y)
    cycles = extract_cycles(p)

    # range; cycles; mean stress
    res = [[4, 0.5, 3], [2, 1, 2], [4, 0.5, 3]]
    assert_allclose(cycles, res)


def test_bin_ranges_1():
    y = [1, 5, 2, 1, 3, 1]
    p = reversals(y)
    cycles = extract_cycles(p)

    stress_ranges, stress_cycles = bin_ranges(cycles, bin_size=3)
    assert_allclose(stress_ranges, [3, 6])
    assert_allclose(stress_cycles, [1, 1])

    stress_ranges, stress_cycles = bin_ranges(cycles, bin_size=4)
    assert_allclose(stress_ranges, [4])
    assert_allclose(stress_cycles, [2])


def test_bin_ranges_2():
    """Test against rainflow package."""

    y = [1, 5, 2, 1, 3, 1]
    p = reversals(y)
    cycles = extract_cycles(p)
    stress_ranges, stress_cycles = bin_ranges(cycles)

    # Using rainflow package
    cycles = rainflow.count_cycles(y, left=True, right=True)
    rf_stress_ranges = [i[0] for i in cycles]
    rf_stress_cycles = [i[1] for i in cycles]

    assert_allclose(stress_ranges, rf_stress_ranges)
    assert_allclose(stress_cycles, rf_stress_cycles)


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
    p = reversals(y)
    cycles = extract_cycles(p)
    stress_ranges, stress_cycles = bin_ranges(cycles, bin_size=1)
    fd = calc_damage(stress_ranges, stress_cycles, SN)
    assert float(f"{fd:.6}") == 4.40185e-10


if __name__ == "__main__":
    pytest.main()
