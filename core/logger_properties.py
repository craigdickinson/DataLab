"""
Created on 5 Aug 2016

@author: bowdenc
"""
import os
from glob import glob

from dateutil.parser import parse

from core.custom_date import get_date_code_span, make_time_str


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class InputError(Error):
    """Exception raised for errors in the input.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class LoggerProperties(object):
    """Holds properties of a logger."""

    def __init__(self, logger_id):
        """
        Constructor - initialise properties.
        May wish to use a dictionary to hold these properties in future
        and then write this dictionary straight to JSON as part of the config
        file.
        """

        # Name and location
        self.logger_id = logger_id  # *LOGGER_ID
        self.logger_path = ''  # *PATH

        # File format variables
        self.file_type = ''  # *FILE_FORMAT
        self.file_timestamp_format = ''  # *FILE_TIMESTAMP
        self.timestamp_format = ''  # *TIMESTAMP
        self.file_ext = ''  # *EXTENSION
        self.file_delimiter = ''  # *DELIMITER

        # Number of rows/columns expected
        self.num_headers = 0  # *NUM_HEADERS
        # self.num_columns = 0  # *NUM_COLUMNS

        # Header row numbers. Note 1-indexed!
        self.channel_header_row = 0  # *CHANNEL_HEADER
        self.units_header_row = 0  # *UNITS_HEADER

        # Statistics processing parameters:
        # Channel columns to process
        self.stats_cols = []  # *STATS_COLUMNS

        # Channel unit conversion factors
        self.stats_unit_conv_factors = []  # *STATS_UNIT_CONV_FACTORS

        # Interval (in seconds) to process stats over
        self.stats_interval = 0  # *STATS_INTERVAL

        # Date range to process stats over
        self.stats_start = None  # *STATS_START
        self.stats_end = None  # *STATS_END

        # Channel names and units
        self.channel_names = []
        self.channel_units = []

        # Channel names and units
        self.user_channel_names = []  # *CHANNEL_NAMES
        self.user_channel_units = []  # *CHANNEL_UNITS

        # list of raw filenames
        self.raw_filenames = []

        # List of accepted files time stamps for each filename
        self.files = []
        self.file_timestamps = []
        self.dates = []

        # Dictionary of files with bad timestamps
        self.bad_filenames = {}

        # Recording properties
        self.freq = 0  # *LOGGING_FREQUENCY
        self.duration = 0  # *LOGGING_DURATION
        self.expected_data_points = 0

        # Processing start and end dates - these hold sampling dates and not the control file start/end dates
        self.start_date = None
        self.end_date = None

        # File timestamp component start and end indexes
        self.year_span = None
        self.month_span = None
        self.day_span = None
        self.hour_span = None
        self.min_span = None
        self.sec_span = None
        self.ms_span = None

    def process_filenames(self):
        """Read all file timestamps and check that they conform to the specified format."""

        self.get_filenames()
        self.get_timestamp_span()
        self.check_file_timestamps()

    def get_filenames(self):
        """Get all filenames with specified extension."""

        self.raw_filenames = [os.path.basename(f) for f in glob(self.logger_path + '/*.' + self.file_ext)]

        if not self.raw_filenames:
            raise InputError('No ' + self.logger_id + ' logger files found in ' + self.logger_path)

    def get_timestamp_span(self):
        """Extract timestamp code spans using filename format given in control file."""

        # File timestamp format
        f = self.file_timestamp_format

        # Get pos of Y, m, D, H, M and S strings
        self.year_span = get_date_code_span('Y', f)
        self.month_span = get_date_code_span('m', f)
        self.day_span = get_date_code_span('D', f)
        self.hour_span = get_date_code_span('H', f)
        self.min_span = get_date_code_span('M', f)
        self.sec_span = get_date_code_span('S', f)
        self.ms_span = get_date_code_span('f', f)

    def check_file_timestamps(self):
        """Check timestamps in all logger filenames are valid."""

        for f in self.raw_filenames:
            y = f[self.year_span[0]:self.year_span[1]]
            m = f[self.month_span[0]:self.month_span[1]]
            d = f[self.day_span[0]:self.day_span[1]]
            h = f[self.hour_span[0]:self.hour_span[1]]
            minute = f[self.min_span[0]:self.min_span[1]]
            sec = f[self.sec_span[0]:self.sec_span[1]]
            ms = f[self.ms_span[0]:self.ms_span[1]]

            # Date must contain y, m and d
            date_str = y + '-' + m + '-' + d

            # Construct time string
            time_str = make_time_str(h, minute, sec, ms)

            # Construct full datetime string
            date_time_str = (date_str + ' ' + time_str).strip()

            # Try to convert string to date
            try:
                date = parse(date_time_str, yearfirst=True)
            except ValueError:
                self.bad_filenames[f] = 'Unable to parse datetime from filename'
            else:
                # Append if date is successfully parsed
                self.files.append(f)
                self.file_timestamps.append(date)

    def set_range(self, start_date=None, end_date=None):
        """
        Filter out dates outside start_date, end_date range.
        :param start_date: dateutil object
        :param end_date: dateutil object
        :return: New list of file_timestamps and files within date range
        """

        # Set range of dates
        self.start_date = start_date
        self.end_date = end_date

        # Use first and last raw logger filenames if no start-end dates read from control file
        if self.start_date is None:
            self.start_date = min(self.file_timestamps)
        if self.end_date is None:
            self.end_date = max(self.file_timestamps)

        dates = [d for d in self.file_timestamps
                 if ((d >= self.start_date) and (d <= self.end_date))]

        files = [f for d, f in zip(self.file_timestamps, self.files)
                 if ((d >= self.start_date) and (d <= self.end_date))]

        # Make sure files are processed in correct order
        try:
            d, f = [list(t) for t in zip(*sorted(zip(dates, files)))]
            self.file_timestamps = d
            self.files = f
        # Empty lists
        except Exception:
            msg = 'No valid logger files found within date range input for ' + self.logger_id
            msg += '\n Check date range and file timestamp inputs'
            raise InputError(msg)
