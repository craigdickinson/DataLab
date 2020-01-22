__author__ = "Craig Dickinson"

import os
from glob import glob
from dateutil.parser import parse
from datetime import datetime
from core.logger_properties import LoggerProperties


def set_custom_file_format(logger: LoggerProperties):
    """Return a LoggerProperties object populated with default file format properties of a Custom file."""

    logger.file_format = "Custom"
    logger.file_timestamp_embedded = True
    logger.first_col_data = "Timestamp"
    logger.file_ext = "csv"
    logger.file_delimiter = ","
    logger.num_headers = 2
    logger.channel_header_row = 1
    logger.units_header_row = 2

    return logger


def get_test_file(logger: LoggerProperties):
    """Return first file in source logger path to interrogate."""

    path = logger.logger_path
    ext = logger.file_ext

    # TODO: Add Azure support
    raw_files = glob(path + "/*." + ext)

    if len(raw_files) == 0:
        msg = f"No files with the extension {ext} found in {path}."
        raise FileNotFoundError(msg)

    return raw_files[0]


def read_test_file(file, num_headers):
    """Read test file - skipping header rows."""

    with open(file) as f:
        [next(f) for _ in range(num_headers)]
        data = f.readlines()

    return data


def get_sampling_freq(data, delim):
    """Attempt to determine sampling frequency from test file data."""

    # Attempt to determine sampling frequency from first two time rows
    try:
        t0_str = data[0].split(delim)[0]
        t1_str = data[1].split(delim)[0]

        # Test if column is timestamps
        try:
            t0 = parse(t0_str)
            t1 = parse(t1_str)
            d = (t1 - t0).total_seconds()
        # Assume time steps
        except ValueError:
            t0 = float(t0_str)
            t1 = float(t1_str)
            d = t1 - t0

        fs = 1 / d
    except ValueError:
        fs = 0

    return fs, t0_str


def detect_timestamp_format(timestamp):
    """Attempt to detect the datetime format of the first column timestamps."""

    # expected_dt = parse(timestamp)
    success = False

    # Test a variety of common datetime formats to try to find a match
    # 1. E.g. 02-Apr-2020 20:26:00.0"
    try:
        test_fmt = "%d-%b-%Y %H:%M:%S.%f"
        timestamp_code = "dd-mmm-yyyy HH:MM:SS.F"
        datetime.strptime(timestamp, test_fmt)
        success = True
    except ValueError:
        pass

    # 2. E.g. 02/14/20 20:26:00.0"
    if not success:
        try:
            test_fmt = "%d/%m/%y %H:%M:%S.%f"
            timestamp_code = "dd/mm/yy HH:MM:SS.F"
            datetime.strptime(timestamp, test_fmt)
            success = True
        except ValueError:
            success = False

    # 3. E.g. 02/14/2020 20:26:00.0"
    if not success:
        try:
            test_fmt = "%d/%m/%Y %H:%M:%S.%f"
            timestamp_code = "dd/mm/yyyy HH:MM:SS.F"
            datetime.strptime(timestamp, test_fmt)
            success = True
        except ValueError:
            success = False

    if success:
        return timestamp_code
    else:
        return "Not detected - must set manually (refer to tooltip)"
