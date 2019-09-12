"""
Methods to set up data read from a pulse-acc file.

Example pulse-acc file format is:

% Logger Serial Number - max 20 chars
%ID,MPOD001
% Logger start time in format: ss mm hh dd mm yyyy
%START,00 00 19 07 06 2018
% Logger download time in format: ss mm hh dd mm  yyyy
%DOWNLOAD,10 37 15 13 02 2019
% Bit mask of input channels used
%BITMASK, 63
% Sampling frequency in Hz
%FREQUENCY, 10.00
% Scanning mode (0=continuous logging, 1=intermittent logging)
%MODE, 0
% Scanning time in minutes (in intermittent mode)
%SCAN, 20
% Cycle time in minutes (in intermittent mode)
%CYCLE, 20
% Data structure: Timestamp CH1-CH6
%DATA,X Acceleration (m/s²):Y Acceleration (m/s²):Z Acceleration (m/s²):Temperature (V):Z-X Angular Rate (°/s):Z-Y Angular Rate (°/s)
% Time stamp maker (Page No. ss mm hh dd mm yyyy)
%0001 00 00 19 07 06 2018
0.000000E+00 7.055314E-02 1.389045E-02 0.000000E+00 0.000000E+00 -1.169407E-01 -2.415017E-01
"""

__author__ = "Craig Dickinson"

import os
from glob import glob


def set_pulse_acc_file_format(logger):
    """Return a LoggerProperties object populated with known Pulse-acc file format settings."""

    logger.file_format = "Pulse-acc"
    logger.file_timestamp_embedded = True
    logger.first_col_data = "Time Step"
    logger.file_ext = "acc"
    logger.file_delimiter = " "
    logger.num_headers = 20
    logger.channel_header_row = 18
    logger.units_header_row = 18

    # Timestamp format is not needed for Pulse-acc files
    logger.timestamp_format = "N/A"

    return logger


def detect_pulse_logger_properties(logger):
    """
    For Pulse logger file detect:
        sample frequency
        expected logging duration
        expected number of columns
    """

    # TODO: Need to check file is of expected filename first!
    raw_files = glob(logger.logger_path + "/*." + logger.file_ext)

    if len(raw_files) == 0:
        msg = f"No files with the extension {logger.file_ext} found in {logger.logger_path}"
        raise FileNotFoundError(msg)

    test_file = raw_files[0]
    test_filename = os.path.basename(test_file)

    # Read sample frequency and channel names and units from file header
    fs, duration, channels, units = read_pulse_header_info(test_file)

    # Store sample frequency
    if fs > 0:
        logger.freq = int(fs)
    else:
        msg = f"Could not read sample interval for logger {logger.logger_id}\nFile: {test_filename}"
        raise Exception(msg)

    # Store expected number of columns (+1 to include timestamp column)
    logger.num_columns = len(channels) + 1

    # Store expected logging duration
    logger.duration = duration

    return logger


def read_pulse_header_info(filename):
    """
    Retrieve the following information from the header of a Pulse-acc file:
    sample frequency
    logging duration
    channels names
    units
    """

    with open(filename, "r") as f:
        # Read sampling frequency
        [next(f) for _ in range(9)]
        fs = next(f).strip().split(" ")[1]

        # Read columns header
        [next(f) for _ in range(7)]
        cols = next(f).strip().split(":")

        [next(f) for _ in range(2)]
        data = f.readlines()

    # Manipulate and check info read
    # Check sample frequency is numeric
    if is_number(fs):
        fs = float(fs)

        # Calculate expected logging duration
        duration = len(data) / fs
    else:
        fs = 0
        duration = 0

    # Get lists of channel names and units
    # Drop "%Data," from the first column
    cols[0] = cols[0].split(",")[1]

    # Extract channel name and units from each column
    channels = []
    units = []
    for col in cols:
        c = col.split("(")
        channels.append(c[0].strip())
        units.append(c[1][:-1])

    return fs, duration, channels, units


def is_number(s):
    """Return True if a string represents a float, otherwise return False."""

    try:
        float(s)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    folder = r"C:\Users\dickinsc\PycharmProjects\_2. DataLab Analysis Files\21239\4. Dat2Acc\POD001"
    fname = "MPOD001_2018_06_07_16_20.ACC"
    f = os.path.join(folder, fname)

    read_pulse_header_info(f)
