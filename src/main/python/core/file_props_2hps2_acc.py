__author__ = "Craig Dickinson"

"""
Methods to set up data read from a pulse-acc file.

Example 2HPS2-acc file format is:

% 2HPS2 Version: 2.44: 27th Nov 2007
%
% *Pod Name: SMA0096
% *Logger Type: MKII
% *Calibration Data: (S, V0, T, Tcal)
%   (Sensitivity, Zero Voltage, Temperature Coefficient, Calibration Temperature)
%   *Accelerometer: (X)  1.050 1.252  0.00000 20.0
%                   (Y)  1.049 1.237  0.00000 20.0
%                   (Z)  1.037 1.222  0.00000 20.0
%   *Temperature:   (-)  0.000 0.000
%   *Angular Rate: (YZ)  3.728 1.303
%                  (XZ)  -3.734 1.323
%   *Temperature Data is NOT used
%
% *Column Header Information
% Time, Accel X, Accel Y, Accel Z, Ang Rate YZ, Ang Rate XZ, Temperature
% (s) , (m/s2) , (m/s2) , (m/s2) , (deg/s)     , (deg/s)   , (C)
%
% *Logger ID: SMA0096
% *Logging start time (s,m,h,d,m,y): 02 00 18 08 06 2019
% *Logging download time (s,m,h,d,m,y): 40 00 17 18 07 2019
% *Frequency in DAT file is: 10.0
% *MODE 1
% *SCAN 10
% *CYCLE 60
% *Logger Time Stamp Marker 0001 02 00 18 08 06 2019 6.664 0.606 0.541
%
  0.0000 3.32475 -9.25886 -0.21519  0.08725 -0.17365 0.00000
"""

__author__ = "Craig Dickinson"

import os
from glob import glob


def set_2hps2_acc_file_format(logger):
    """
    Return a LoggerProperties object populated with file format properties of a Pulse-acc file generated from 2HPS2.
    """

    logger.file_format = "2HPS2-acc"
    logger.file_timestamp_embedded = True
    logger.first_col_data = "Time Step"
    logger.file_ext = "acc"
    logger.file_delimiter = " "
    logger.num_headers = 27
    logger.channel_header_row = 16
    logger.units_header_row = 17

    # Timestamp format is not needed for Pulse-acc files
    logger.timestamp_format = "N/A"

    return logger


def detect_2hps2_logger_properties(logger):
    """
    For Pulse logger file generated from 2HPS2 detect:
        sample frequency
        expected logging duration
        expected number of columns
    """

    # TODO: Add Azure support
    raw_files = glob(logger.logger_path + "/*." + logger.file_ext)

    if len(raw_files) == 0:
        msg = f"No files with the extension {logger.file_ext} found in {logger.logger_path}."
        raise FileNotFoundError(msg)

    test_file = raw_files[0]
    test_filename = os.path.basename(test_file)

    # Read sample frequency and channel names and units from file header
    fs, duration, channels, units = read_2hps2_header_info(test_file)

    # Store sample frequency
    if fs > 0:
        logger.freq = fs
    else:
        msg = (
            f"Could not read sample frequency for logger {logger.logger_id}\nFile: {test_filename}"
        )
        raise Exception(msg)

    # Store expected number of columns (+1 to include timestamp column)
    logger.num_columns = len(channels) + 1

    # Store expected logging duration
    logger.duration = duration

    return logger


def read_2hps2_header_info(file):
    """
    Retrieve the following information from the header of a Pulse-acc file generated from 2HPS2:
    sample frequency
    logging duration
    channel names
    channel units
    """

    with open(file, "r") as f:
        # Read channels header
        [next(f) for _ in range(15)]
        channel_line = f.readline().strip().split(",")

        # Read units header
        units_line = f.readline().strip().split(",")

        # Read sampling frequency
        [next(f) for _ in range(4)]
        fs = f.readline().strip().split(" ")[-1]

        # Skip remaining header and read body
        [next(f) for _ in range(5)]
        data = f.readlines()

    # Check sample frequency is numeric and calculate expected logging duration
    try:
        fs = float(fs)
        duration = len(data) / fs
    except ValueError:
        fs = 0
        duration = 0

    # Get lists of channel names and units
    # Drop "Time" item and trim
    channels = [c.strip() for c in channel_line[1:]]
    units = [i.strip().split("(")[1][:-1] for i in units_line[1:]]

    return fs, duration, channels, units


if __name__ == "__main__":
    folder = r"C:/Users/dickinsc/PycharmProjects/DataLab/demo_data/1. Raw Data/Perth 2HPS2-acc"
    fname = "SMA0096_0000_2019_06_08_18_00.Acc"
    f = os.path.join(folder, fname)
    read_2hps2_header_info(f)
