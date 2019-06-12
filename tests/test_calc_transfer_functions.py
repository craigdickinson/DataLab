"""Tests for the routines to calculate frequency-dependent transfer functions."""
__author__ = "Craig Dickinson"

import pytest
import os

from app.core.calc_transfer_functions import TransferFunctions, get_header_row, read_windows_time_traces, \
    find_nearest_window


def setup():
    tf = TransferFunctions()
    root = os.path.join(os.path.dirname(os.getcwd()), "demo_data", "3. Transfer Functions")
    tf.bm_dir = os.path.join(root, "Hot Spots BM Z")
    tf.disp_dir = os.path.join(root, "Loggers Disp Y")
    tf.rot_dir = os.path.join(root, "Loggers Rot Z")
    tf.get_files()

    return tf


tf = setup()


def test_get_header_row():
    header_row = get_header_row(tf.bm_files[0])
    assert header_row == 4


def test_read_loc_bm_time_traces_shape():
    df = read_windows_time_traces(tf.bm_files)
    assert df.shape[0] == 36002
    assert df.shape[1] == 24


def test_read_logger_disp_time_traces_shape():
    df = read_windows_time_traces(tf.disp_files)
    assert df.shape[0] == 36002
    assert df.shape[1] == 16


def test_read_logger_rot_time_traces_shape():
    df = read_windows_time_traces(tf.rot_files)
    assert df.shape[0] == 36002
    assert df.shape[1] == 16


def test_find_nearest_window():
    """Find nearest window given a (Hs, Tp) pair."""

    windows = [1, 2, 3, 4, 5, 6, 7, 8]
    hs = [
        0.875,
        2.625,
        1.125,
        1.375,
        2.625,
        1.375,
        1.125,
        2.125,
    ]
    tp = [
        6.5,
        7.5,
        7.5,
        8.5,
        9.5,
        9.5,
        11.5,
        14.5,
    ]
    perc_occ = [
        19.040,
        10.134,
        20.049,
        17.022,
        14.644,
        10.374,
        5.448,
        3.289,
    ]

    hs_i = 2
    tp_i = 9.5
    win = find_nearest_window(windows, hs, tp, hs_i, tp_i)
    assert win == 5


if __name__ == "__main__":
    pytest.main()
