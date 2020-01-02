"""Tests for the detecting the file timestamp format of timestamps embedded in logger files."""
__author__ = "Craig Dickinson"

import pytest

from core.detect_file_timestamp_format import detect_file_timestamp_format


def test_detect_file_timestamp_format_1():
    filename = "dd10_2017_0310_0000.csv"
    timestamp_fmt = detect_file_timestamp_format(filename)
    assert timestamp_fmt == "xxxxxYYYYxmmDDxHHMM"


def test_detect_file_timestamp_format_2():
    filename = "BOP_2018_0607_1620.csv"
    timestamp_fmt = detect_file_timestamp_format(filename)
    assert timestamp_fmt == "xxxxYYYYxmmDDxHHMM"


def test_detect_file_timestamp_format_3():
    filename = "wp_180506_1400.csv"
    timestamp_fmt = detect_file_timestamp_format(filename)
    assert timestamp_fmt == "xxxYYmmDDxHHMM"


def test_detect_file_timestamp_format_4():
    filename = "MPOD001_2018_06_07_16_20.ACC"
    timestamp_fmt = detect_file_timestamp_format(filename)
    assert timestamp_fmt == "xxxxxxxxYYYYxmmxDDxHHxMM"


def test_detect_file_timestamp_format_5():
    filename = "MRU Blue_CalibratedData_start2018_09_26_00_24_36_end2018_09_26_00_54_36_312.csv"
    timestamp_fmt = detect_file_timestamp_format(filename)
    assert timestamp_fmt == "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxYYYYxmmxDDxHHxMMxSS"


def test_detect_file_timestamp_format_6():
    filename = "case0000_2019_0101_0000.txt"
    timestamp_fmt = detect_file_timestamp_format(filename)
    assert timestamp_fmt == "xxxxxxxxxYYYYxmmDDxHHMM"


def test_detect_file_timestamp_format_7():
    filename = "FLJ_2019_0827_0000.csv"
    timestamp_fmt = detect_file_timestamp_format(filename)
    assert timestamp_fmt == "xxxxYYYYxmmDDxHHMM"


def test_detect_file_timestamp_format_8():
    filename = "SMA0096_0000_2019_06_08_18_00.acc"
    timestamp_fmt = detect_file_timestamp_format(filename)
    assert timestamp_fmt == "xxxxxxxxxxxxxYYYYxmmxDDxHHxMM"


if __name__ == "__main__":
    pytest.main()
