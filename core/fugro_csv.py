"""
Created on 15 Sep 2016

@author: bowdenc

Methods to setup data read from a fugro-csv file

Example fugro-csv file format is:

#Sample Interval: 0.100000 (seconds)
Timestamp,AccelX,AccelY,RateX,RateY
dd-mmm-yyyy HH:MM:SS.FFF,mm/s2,mm/s2,rad/s,rad/s
17-Mar-2016 02:00:00.000,-48.085023,-1.237695e+002,-7.414453e-004,2.252544e-003
"""
from core.custom_date import user_date_to_date_format
from core.logger_properties import LoggerProperties


def fugro_file_format(logger):
    # def fugro_file_format(logger_id):
    """Return a LoggerProperties object populated with fugro_csv file format settings."""

    # logger = LoggerProperties(logger_id)
    logger.file_format = 'Fugro-csv'
    logger.file_ext = 'csv'
    logger.file_delimiter = ','
    logger.num_headers = 3
    logger.channel_header_row = 2
    logger.units_header_row = 3

    return logger


def read_fugro_sample_header(fname):
    """
    Read the first line of fname which should be of the format:
    #Sample Interval: 0.100000 (seconds)
    If successful return the sample interval, otherwise return 0.
    """

    # Read the first line
    with open(fname) as f:
        line = f.readline()

    # Split by a space
    words = line.split(' ')

    # Select the sample interval assuming header is as expected
    samp_str = ''
    if len(words) == 4:
        samp_str = words[2]

    if is_number(samp_str):
        return float(samp_str)
    else:
        return 0


def read_headers(fname):
    """Return the second and third headers in fname as lists."""

    # Skip the first two lines
    with open(fname) as f:
        next(f)
        header = f.readline().split(',')
        units = f.readline().split(',')

    # Split the header and get the timestamp format
    return header, units


def read_fugro_timestamp_format(fmt_str):
    """
    Read the third header specifying the timestamp format.
    If successful return a string for parsing dates in dateutil
    e.g. %d-%b-%Y %H:%M:%S.%f
    """

    # Get the timestamp format
    date_format = user_date_to_date_format(fmt_str)
    return date_format


def is_number(s):
    """Return True if a string represents a float, otherwise return False."""

    try:
        float(s)
        return True
    except ValueError:
        return False
