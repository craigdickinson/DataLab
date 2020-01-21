__author__ = "Craig Dickinson"

import os
from glob import glob
from dateutil.parser import parse


def set_custom_file_format(logger):
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


def detect_custom_logger_properties(logger):
    """
    For custom logger file detect:
        sample frequency
        expected number of columns
        expected logging duration
    """

    path = logger.logger_path
    ext = logger.file_ext
    delim = logger.file_delimiter
    num_headers = logger.num_headers

    # TODO: Add Azure support
    raw_files = glob(path + "/*." + ext)

    if len(raw_files) == 0:
        msg = f"No files with the extension {ext} found in {path}"
        raise FileNotFoundError(msg)

    test_file = raw_files[0]
    test_filename = os.path.basename(test_file)

    with open(test_file) as f:
        # Skip header rows
        [next(f) for _ in range(num_headers)]

        # Read body
        data = f.readlines()

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
    except Exception:
        msg = (
            f"Could not read sample frequency for logger {logger.logger_id}\nFile: {test_filename}"
        )
        raise Exception(msg)

    # Store sample frequency
    if fs > 0:
        logger.freq = fs

    logger.num_columns = len(data[0].strip().split(delim))
    n = len(data)
    logger.duration = n / logger.freq

    return logger
