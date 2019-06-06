"""
Collection of functions for processing custom date formats.
"""
import re

# Dict of strings that may appear in datetime formats
# Format assumes that mm is month, MM is minute
replacements = {
    r"dd": "%d",
    r"d": "%d",
    r"mm": "%m",
    r"m": "%m",
    r"mmm": "%b",
    r"MMM": "%b",
    r"yyyy": "%Y",
    r"YYYY": "%Y",
    r"yy": "%y",
    r"YY": "%y",
    r"hh": "%H",
    r"HH": "%H",
    r"MM": "%M",
    r"ss": "%S",
    r"SS": "%S",
    r"f": "%f",
    r"ff": "%f",
    r"fff": "%f",
    r"F": "%f",
    r"FF": "%f",
    r"FFF": "%f",
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
    regex = letter + "+"
    pos = re.search(regex, date_str)

    # Return start and end positions if consecutive string is found
    if pos:
        start = pos.span()[0]
        end = pos.span()[1]

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
    :param timestamp_format_str: Fugro-style timestamps form at string
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

    pattern = "|".join(r"\b" + re.escape(k) + r"\b" for k in rep)
    return re.sub(pattern, dict_repl, timestamp_fmt_str)


def dict_repl(match):
    """
    Return each replacements dictionary value to replace in format date string.
    match.group() is each dictionary key.
    :param match: Regular expression match object
    :return: Replacement string
    """

    return replacements[match.group()]
