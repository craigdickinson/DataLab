"""Tests for the routines to calculate frequency-dependent transfer functions."""
__author__ = "Craig Dickinson"

import pytest
import os

from app.core.calc_transfer_functions import TransferFunctions, get_header_row, read_all_windows


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
    df = read_all_windows(tf.bm_files)
    assert df.shape[0] == 36002
    assert df.shape[1] == 24


def test_read_logger_disp_time_traces_shape():
    df = read_all_windows(tf.disp_files)
    assert df.shape[0] == 36002
    assert df.shape[1] == 16


def test_read_logger_rot_time_traces_shape():
    df = read_all_windows(tf.rot_files)
    assert df.shape[0] == 36002
    assert df.shape[1] == 16


if __name__ == "__main__":
    pytest.main()
