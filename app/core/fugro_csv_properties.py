"""
Methods to set up data read from a fugro-csv file.

Example fugro-csv file format is:

#Sample Interval: 0.100000 (seconds)
Timestamp,AccelX,AccelY,RateX,RateY
dd-mmm-yyyy HH:MM:SS.FFF,mm/s2,mm/s2,rad/s,rad/s
17-Mar-2016 02:00:00.000,-48.085023,-1.237695e+002,-7.414453e-004,2.252544e-003
"""
import os
from glob import glob


def set_fugro_csv_file_format(logger):
    """Return a LoggerProperties object populated with known Fugro-csv file format settings."""

    logger.file_format = "Fugro-csv"
    logger.file_ext = "csv"
    logger.file_delimiter = ","
    logger.num_headers = 3
    logger.channel_header_row = 2
    logger.units_header_row = 3

    return logger


def set_general_csv_file_format(logger):
    """Return a LoggerProperties object populated with default settings for a General-csv file format."""

    logger.file_format = "General-csv"
    logger.file_ext = "csv"
    logger.file_delimiter = ","
    logger.num_headers = 2
    logger.channel_header_row = 1
    logger.units_header_row = 2

    return logger


def detect_fugro_logger_properties(logger):
    """
    For Fugro logger file detect:
        sample frequency
        timestamp format (user style format string)
        datetime format (datetime/pandas format string)
        expected number of columns
        expected logging duration
    """

    # TODO: Need to check file is of expected filename first!
    raw_files = glob(logger.logger_path + "/*." + logger.file_ext)

    if len(raw_files) == 0:
        msg = f"No files with the extension {logger.file_ext} found in {logger.logger_path}"
        raise FileNotFoundError(msg)

    test_file = raw_files[0]
    test_filename = os.path.basename(test_file)

    # Read sample interval
    sample_interval = read_fugro_sample_interval(test_file)

    # Convert to sample frequency
    if sample_interval > 0:
        logger.freq = float(1 / sample_interval)
    else:
        msg = f"Could not read sample interval for logger {logger.logger_id}\nFile: {test_filename}"
        raise Exception(msg)

    # Read headers
    header, units = read_fugro_headers(test_file)

    # Retrieve timestamp format from first column of units header
    logger.timestamp_format = units[0]

    # Get expected number of columns
    logger.num_columns = len(header)

    # Get expected logging duration
    # Read number of data points
    with open(test_file) as f:
        data = f.readlines()

    # Less number of header rows
    n = len(data) - 3
    logger.duration = n / logger.freq

    return logger


def read_fugro_sample_interval(filename):
    """
    Read the first line of filename which should be of the format:
    #Sample Interval: 0.100000 (seconds)
    If successful return the sample interval, otherwise return 0.
    """

    # Read the first line
    with open(filename) as f:
        line = f.readline()

    # Select the sample interval assuming header is as expected
    words = line.split(" ")
    samp_str = ""
    if len(words) == 4:
        samp_str = words[2]

    if is_number(samp_str):
        return float(samp_str)
    else:
        return 0


def read_fugro_headers(filename):
    """Return the second and third headers in filename as lists."""

    # Skip the first two lines
    with open(filename) as f:
        next(f)
        header = f.readline().strip().split(",")
        units = f.readline().strip().split(",")

    return header, units


def is_number(s):
    """Return True if a string represents a float, otherwise return False."""

    try:
        float(s)
        return True
    except ValueError:
        return False
