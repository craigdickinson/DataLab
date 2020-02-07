"""Tests for the routines to calculate frequency-dependent transfer functions."""
__author__ = "Craig Dickinson"

import pytest
import os

from core.calc_transfer_functions import TransferFunctions


def setup():
    tf = TransferFunctions()
    root_dir = "test_data"

    # Try to ensure correct path to test files is set (differs if script is run here or from project root)
    if os.path.basename(os.getcwd()) != "tests":
        root_dir = os.path.join(os.getcwd(), "tests", root_dir)

    tf.bm_dir = os.path.join(root_dir, "Hot_Spots_BM_Z")
    tf.disp_dir = os.path.join(root_dir, "Loggers_Disp_Y")
    tf.rot_dir = os.path.join(root_dir, "Loggers_Rot_Z")
    tf.get_files()
    tf.get_number_of_seastates()

    return tf


tf = setup()


def test_get_header_row():
    header_row = tf.get_header_row(tf.bm_files[0])
    assert header_row == 4


def test_read_loc_bm_time_traces_shape():
    df = tf.read_seastate_time_traces(tf.bm_files)
    assert df.shape[0] == 36002
    assert df.shape[1] == 24


def test_read_logger_disp_time_traces_shape():
    df = tf.read_seastate_time_traces(tf.disp_files)
    assert df.shape[0] == 36002
    assert df.shape[1] == 16


def test_read_logger_rot_time_traces_shape():
    df = tf.read_seastate_time_traces(tf.rot_files)
    assert df.shape[0] == 36002
    assert df.shape[1] == 16


def test_find_nearest_window():
    """Find nearest window given a (Hs, Tp) pair."""

    windows = [1, 2, 3, 4, 5, 6, 7, 8]
    hs = [0.875, 2.625, 1.125, 1.375, 2.625, 1.375, 1.125, 2.125]
    tp = [6.5, 7.5, 7.5, 8.5, 9.5, 9.5, 11.5, 14.5]
    perc_occ = [19.040, 10.134, 20.049, 17.022, 14.644, 10.374, 5.448, 3.289]

    hs_i = 2
    tp_i = 9.5
    win = tf.find_nearest_window(windows, hs, tp, hs_i, tp_i)
    assert win == 5


if __name__ == "__main__":
    pytest.main()
