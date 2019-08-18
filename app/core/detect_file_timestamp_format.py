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
    match = None

    # First replace non-numeric characters with x
    f = re.sub(pattern=r"\D", repl="x", string=filename)

    # Substitute timestamp ID flags for various expected file naming formats
    # Fugro vessel file
    if len(groups) == 2:
        if len(groups[0]) == 6:
            # Assume date format is YYmmDD
            fmt = "YYmmDD"
            match = matches[0]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[1]) == 4:
            fmt = "HHMM"
            match = matches[1]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

    # Fugro logger file
    if len(groups) == 3:
        if len(groups[0]) == 4:
            fmt = "YYYY"
            match = matches[0]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[1]) == 4:
            fmt = "mmDD"
            match = matches[1]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[2]) == 4:
            fmt = "HHMM"
            match = matches[2]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

    # Fugro logger file with numeric in logger name (e.g. dd10_)
    if len(groups) == 4:
        if len(groups[1]) == 4:
            fmt = "YYYY"
            match = matches[1]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[2]) == 4:
            fmt = "mmDD"
            match = matches[2]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[3]) == 4:
            fmt = "HHMM"
            match = matches[3]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

    # Pulse acc file
    if len(groups) == 5:
        if len(groups[0]) == 4:
            fmt = "YYYY"
            match = matches[0]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[1]) == 2:
            fmt = "mm"
            match = matches[1]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[2]) == 2:
            fmt = "DD"
            match = matches[2]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[3]) == 2:
            fmt = "HH"
            match = matches[3]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[4]) == 2:
            fmt = "MM"
            match = matches[4]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

    # Pulse csv file
    if len(groups) == 12:
        if len(groups[0]) == 4:
            fmt = "YYYY"
            match = matches[0]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[1]) == 2:
            fmt = "mm"
            match = matches[1]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[2]) == 2:
            fmt = "DD"
            match = matches[2]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[3]) == 2:
            fmt = "HH"
            match = matches[3]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[4]) == 2:
            fmt = "MM"
            match = matches[4]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

        if len(groups[5]) == 2:
            fmt = "SS"
            match = matches[5]
            f = f.replace(f[match.start() : match.end()], fmt, 1)

    # Drop any characters after the last match as they're not required
    if match:
        f = f[: match.end()]

    # Finally replace any remaining digits with x
    file_timestamp_format = re.sub(pattern=r"\d", repl="x", string=f)

    return file_timestamp_format
