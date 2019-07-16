"""
Collection of functions for processing custom date formats.
"""
import re

# Dict of strings that may appear in datetime formats
# Format assumes that mm is month, MM is minute
replacements = {
    "dd": "%d",
    "d": "%d",
    "DD": "%d",
    "D": "%d",
    "mm": "%m",
    "m": "%m",
    "mmm": "%b",
    "MMM": "%b",
    "yyyy": "%Y",
    "YYYY": "%Y",
    "yy": "%y",
    "YY": "%y",
    "hh": "%H",
    "HH": "%H",
    "MM": "%M",
    "ss": "%S",
    "SS": "%S",
    "f": "%f",
    "ff": "%f",
    "fff": "%f",
    "F": "%f",
    "FF": "%f",
    "FFF": "%f",
}


def get_date_code_span(letter, date_str):
    """
    Find span of a consecutive string of letters in another string
    e.g. if s='DD-MM-YYYY' then s[6:10] == 'YYYY'
    get_date_format_code('Y','DD-MM-YYYY') returns (6,10).
    """

    # Initialise start and end to the first char match found
    start = date_str.find(letter)
    end = start + 1

    # Use a regex to find consecutive letters
    pattern = letter + "+"
    match = re.search(pattern, date_str)

    # Return start and end positions if consecutive string is found
    if match:
        start = match.start()
        end = match.end()

    # Return span of regex
    return start, end


def make_time_str(h, m, s, f):
    """Create a string in the format h[:m[:s[.f]]]."""

    time_str = h
    if len(m) > 0:
        time_str += ":" + m

        if len(s) > 0:
            time_str += ":" + s

            if len(f) > 0:
                time_str += "." + f

    return time_str


def get_datetime_format(timestamp_format_str):
    """
    Convert a timestamp format string (as input by the user in the Fugro style) to datetime format string for parsing
    dates to datetime objects in pandas.
    Example 1: Timestamp format: dd-mmm-yyyy HH:MM:SS.FFF
               Datetime format:  %d-%b-%Y %H:%M:%S.%f
    Example 2: Timestamp format: dd/mm/yyyy HH:MM:SS.FFF
               Datetime format:  %d/%m/%Y %H:%M:%S.%f
    :param timestamp_format_str: Fugro-style timestamps format string
    :return: Datetime format string
    """

    # Get the datetime format string to parse dates to datetimes
    datetime_format_str = user_date_to_date_format(timestamp_format_str)
    return datetime_format_str


def user_date_to_date_format(timestamp_fmt_str, rep=replacements):
    """
    Replace timestamp format string with datetime specified in replacements dictionary.
    The dict_repl function is called for each dictionary key.
    """

    pattern = "|".join(r"\b" + k + r"\b" for k in rep)
    return re.sub(pattern, dict_repl, timestamp_fmt_str)


def dict_repl(match):
    """
    Return each replacements dictionary value to replace in format date string.
    match.group() is each dictionary key.
    :param match: Regular expression match object
    :return: Replacement string
    """

    return replacements[match.group()]
