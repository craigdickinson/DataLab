"""
Functions to auto-generate the file timestamp format string of logger file names.
"""
__author__ = "Craig Dickinson"

import os
import re


def detect_file_timestamp_format(filename):
    """
    Attempt to decipher the required file timestamp format to determine the datetime of a file.
    Example: For a filename BOP_2018_0607_1620
    File timestamp format = xxxxYYYYxmmDDxHHMM
    """

    # Drop extension
    filename = os.path.splitext(filename)[0]

    # Extract all numeric elements but only keep matches of even length
    # Don't expect any datetime elements to be of odd length
    pattern = re.compile(r"\d+")
    groups = [group for group in pattern.findall(filename) if len(group) % 2 == 0]
    matches = [
        match for match in pattern.finditer(filename) if len(match.group()) % 2 == 0
    ]

    # Initialise end index of last match for trimming superfluous characters of the format string
    end = 0

    # First replace non-numeric characters with x
    f = re.sub(pattern=r"\D", repl="x", string=filename)

    # Substitute timestamp components with appropriate timestamp code for various expected filename formats
    n = len(groups)

    # Fugro vessel file
    if n == 2:
        f, end = create_format_string_fugro_vessel(f, groups, matches)

    # Fugro logger file
    if n == 3:
        f, end = create_format_string_fugro_logger(f, groups, matches)

    # Fugro logger file with numeric in logger name (e.g. dd10_)
    if n == 4:
        f, end = create_format_string_fugro_logger_dd(f, groups, matches)

    # Pulse acc file
    if n == 5:
        f, end = create_format_string_pulse_acc(f, groups, matches)

    # 2HPS2 acc file
    if n == 7:
        f, end = create_format_string_2hps2_acc(f, groups, matches)

    # Pulse csv file
    if n == 12:
        f, end = create_format_string_pulse_csv(f, groups, matches)

    # Drop any characters after the last match as they're not required
    if end > 0:
        f = f[:end]

    # Finally replace any remaining digits with x
    file_timestamp_format = re.sub(pattern=r"\d", repl="x", string=f)

    return file_timestamp_format


def substitute_code(string, match, code):
    """Replace segment of filename with timestamp format code."""

    return "".join((string[: match.start()], code, string[match.end() :]))


def create_format_string_fugro_vessel(string, groups, matches):
    """Substitute filename with timestamp format codes expected of a Fugro vessel file."""

    if len(groups[0]) == 6:
        string = substitute_code(string, matches[0], code="YYmmDD")

    if len(groups[1]) == 4:
        string = substitute_code(string, matches[1], code="HHMM")

    return string, matches[1].end()


def create_format_string_fugro_logger(string, groups, matches):
    """Substitute filename with timestamp format codes expected of a Fugro logger file."""

    if len(groups[0]) == 4:
        string = substitute_code(string, matches[0], code="YYYY")

    if len(groups[1]) == 4:
        string = substitute_code(string, matches[1], code="mmDD")

    if len(groups[2]) == 4:
        string = substitute_code(string, matches[2], code="HHMM")

    return string, matches[2].end()


def create_format_string_fugro_logger_dd(string, groups, matches):
    """
    Substitute filename with timestamp format codes expected of a Fugro logger file
    containing a numeric id (e.g. dd10).
    """

    if len(groups[1]) == 4:
        string = substitute_code(string, matches[1], code="YYYY")

    if len(groups[2]) == 4:
        string = substitute_code(string, matches[2], code="mmDD")

    if len(groups[3]) == 4:
        string = substitute_code(string, matches[3], code="HHMM")

    return string, matches[3].end()


def create_format_string_pulse_acc(string, groups, matches):
    """Substitute filename with timestamp format codes expected of a Pulse acc file."""

    if len(groups[0]) == 4:
        string = substitute_code(string, matches[0], code="YYYY")

    if len(groups[1]) == 2:
        string = substitute_code(string, matches[1], code="mm")

    if len(groups[2]) == 2:
        string = substitute_code(string, matches[2], code="DD")

    if len(groups[3]) == 2:
        string = substitute_code(string, matches[3], code="HH")

    if len(groups[4]) == 2:
        string = substitute_code(string, matches[4], code="MM")

    return string, matches[4].end()


def create_format_string_pulse_csv(string, groups, matches):
    """Substitute filename with timestamp format codes expected of a Pulse csv file."""

    if len(groups[0]) == 4:
        string = substitute_code(string, matches[0], code="YYYY")

    if len(groups[1]) == 2:
        string = substitute_code(string, matches[1], code="mm")

    if len(groups[2]) == 2:
        string = substitute_code(string, matches[2], code="DD")

    if len(groups[3]) == 2:
        string = substitute_code(string, matches[3], code="HH")

    if len(groups[4]) == 2:
        string = substitute_code(string, matches[4], code="MM")

    if len(groups[5]) == 2:
        string = substitute_code(string, matches[5], code="SS")

    return string, matches[5].end()


def create_format_string_2hps2_acc(string, groups, matches):
    """Substitute filename with timestamp format codes expected of a 2HPS2 acc file."""

    if len(groups[2]) == 4:
        string = substitute_code(string, matches[2], code="YYYY")

    if len(groups[3]) == 2:
        string = substitute_code(string, matches[3], code="mm")

    if len(groups[4]) == 2:
        string = substitute_code(string, matches[4], code="DD")

    if len(groups[5]) == 2:
        string = substitute_code(string, matches[5], code="HH")

    if len(groups[6]) == 2:
        string = substitute_code(string, matches[6], code="MM")

    return string, matches[6].end()
