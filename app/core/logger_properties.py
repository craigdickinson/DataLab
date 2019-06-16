"""
Class to hold logger properties.
"""
__author__ = "Craig Dickinson"

import os
from glob import glob

from dateutil.parser import parse
from PyQt5.QtCore import QObject, pyqtSignal

from app.core.custom_date import get_date_code_span, make_time_str


class Error(Exception):
    """Base class for exceptions in this module."""

    pass


class LoggerError(Error):
    """Exception raised for errors in the logger properties.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class LoggerProperties(QObject):
    """Holds properties of a logger."""

    signal_warning = pyqtSignal(str)

    def __init__(self, logger_id=""):
        """
        Constructor - initialise properties.
        May wish to use a dictionary to hold these properties in future
        and then write this dictionary straight to JSON as part of the config file.
        """
        super().__init__()

        # Name and location
        self.logger_id = logger_id  # *LOGGER_ID
        self.logger_path = ""  # *PATH

        # File format variables
        self.file_format = ""  # *FILE_FORMAT
        self.file_timestamp_format = ""  # *FILE_TIMESTAMP
        self.timestamp_format = ""  # *TIMESTAMP

        # Datetime format string to convert timestamp strings to datetimes, e.g. %d-%b-%Y %H:%M:%S.%f
        self.datetime_format = ""

        self.file_ext = ""  # *EXTENSION
        self.file_delimiter = ""  # *DELIMITER

        # Number of rows/columns expected
        self.num_headers = 0  # *NUM_HEADERS
        self.num_columns = 0  # *NUM_COLUMNS

        # Header row numbers. Note 1-indexed!
        self.channel_header_row = 0  # *CHANNEL_HEADER
        self.units_header_row = 0  # *UNITS_HEADER

        # Channel names and units lists
        self.all_channel_names = []
        self.all_channel_units = []

        # Channel columns to process
        self.cols_to_process = []

        # Channel unit conversion factors
        self.unit_conv_factors = []

        # Requested channel names and units
        self.channel_names = []
        self.channel_units = []

        # Custom channel names and units
        self.user_channel_names = []  # *CHANNEL_NAMES
        self.user_channel_units = []  # *CHANNEL_UNITS

        # Datetime range to process over
        self.process_start = None  # *STATS_START
        self.process_end = None  # *STATS_END

        # Cut-off frequencies for filtered screening analysis
        self.low_cutoff_freq = 0.05
        self.high_cutoff_freq = 0.5

        # Data type to screen on (unfiltered only, filtered only, both unfiltered and filtered)
        self.process_type = "Both unfiltered and filtered"

        # STATISTICS ANALYSIS PARAMETERS
        # Include in processing flag
        self.process_stats = True

        # Interval (in seconds) to process stats over
        self.stats_interval = 0  # *STATS_INTERVAL

        # SPECTRAL ANALYSIS PARAMETERS
        # Include in processing flag
        self.process_spectral = True

        # Interval (in seconds) to process stats over
        self.spect_interval = 0

        # List of raw filenames and of accepted file timestamps for each filename
        self.raw_filenames = []
        self.files = []
        self.file_timestamps = []
        self.dates = []

        # Dictionary of files with bad timestamps
        self.dict_bad_filenames = {}

        # Recording properties
        self.freq = 0  # *LOGGING_FREQUENCY
        self.duration = 0  # *LOGGING_DURATION
        self.expected_data_points = 0

        # Processing start and end dates
        # These hold sampling dates and not the control file stats start/end dates (which may not be provided)
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
        """Get all filenames with specified extension in logger path."""

        self.raw_filenames = [
            os.path.basename(f) for f in glob(self.logger_path + "/*." + self.file_ext)
        ]

        if not self.raw_filenames:
            raise LoggerError(
                f"No {self.logger_id} logger files found in {self.logger_path}"
            )

    def get_timestamp_span(self):
        """Extract timestamp code spans using filename format given in control file."""

        # File timestamp format
        f = self.file_timestamp_format

        # Get pos of Y, m, D, H, M and S strings
        self.year_span = get_date_code_span("Y", f)
        self.month_span = get_date_code_span("m", f)
        self.day_span = get_date_code_span("D", f)
        self.hour_span = get_date_code_span("H", f)
        self.min_span = get_date_code_span("M", f)
        self.sec_span = get_date_code_span("S", f)
        self.ms_span = get_date_code_span("f", f)

    def check_file_timestamps(self):
        """Check timestamps in all logger filenames are valid."""

        self.files = []
        self.file_timestamps = []

        for f in self.raw_filenames:
            y = f[self.year_span[0]: self.year_span[1]]
            m = f[self.month_span[0]: self.month_span[1]]
            d = f[self.day_span[0]: self.day_span[1]]
            h = f[self.hour_span[0]: self.hour_span[1]]
            minute = f[self.min_span[0]: self.min_span[1]]
            sec = f[self.sec_span[0]: self.sec_span[1]]
            ms = f[self.ms_span[0]: self.ms_span[1]]

            # Date must contain y, m and d
            date_str = y + "-" + m + "-" + d

            # Construct time string
            time_str = make_time_str(h, minute, sec, ms)

            # Construct full datetime string
            datetime_str = (date_str + " " + time_str).strip()

            # Try to convert string to date
            try:
                date = parse(datetime_str, yearfirst=True)
            except ValueError:
                self.dict_bad_filenames[f] = "Unable to parse datetime from filename"
            else:
                # Append if date is successfully parsed
                self.files.append(f)
                self.file_timestamps.append(date)

    def select_files_in_datetime_range(self, start_date=None, end_date=None):
        """
        Filter out dates outside start_date, end_date range.
        :param start_date: datetime
        :param end_date: datetime
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

        dates_files = [
            (d, f)
            for d, f in zip(self.file_timestamps, self.files)
            if self.start_date <= d <= self.end_date
        ]

        # Make sure files are processed in correct order (and make sure they are lists not tuples)
        try:
            d, f = list(zip(*sorted(dates_files)))
            self.file_timestamps = list(d)
            self.files = list(f)
        # Empty lists
        except ValueError:
            msg = (
                f"No valid logger files found within date range input for {self.logger_id}.\n"
                f"Check date range and file timestamp inputs."
            )
            raise LoggerError(msg)

    def get_all_channel_and_unit_names(self):
        """Store in logger object lists of all channel and units header in test file."""

        if self.logger_path == "":
            return

        # TODO: Need to check file is of expected filename first!
        raw_files = glob(self.logger_path + "/*." + self.file_ext)

        if len(raw_files) == 0:
            msg = f"No files with the extension {self.file_ext} found in {self.logger_path}"
            raise FileNotFoundError(msg)

        test_file = raw_files[0]
        file_format = self.file_format
        delim = self.file_delimiter
        c = self.channel_header_row
        u = self.units_header_row
        channels = []
        units = []

        # Get headers and first line of data
        if file_format == "Fugro-csv" or file_format == "General-csv":
            with open(test_file) as f:
                header_lines = [
                    f.readline().strip().split(delim) for _ in range(self.num_headers)
                ]

            # Extract list of channel names and units (drop the first item - expected to be timestamp)
            if c > 0:
                channels = header_lines[c - 1][1:]
            # If no channels header exists, create a dummy channels list
            else:
                channels = [f"Column {i + 2}" for i in range(len(header_lines[c - 1][1:]))]

            if u > 0:
                units = header_lines[u - 1][1:]
            # If no units header exists, create a dummy list
            else:
                units = ["-"] * len(header_lines[u - 1][1:])
        elif file_format == "Pulse-acc":
            with open(test_file, "r") as f:
                # Read columns header
                [next(f) for _ in range(c - 1)]
                header = next(f).strip().split(":")

            # Drop "%Data," from the first column
            header[0] = header[0].split(",")[1]

            # Extract lists of channel names and units
            channels = [col.split("(")[0].strip() for col in header]
            units = [col.split("(")[1][:-1] for col in header]

        # Assign channels and units list to logger
        self.all_channel_names = channels
        self.all_channel_units = units

    def set_columns_to_process_headers(self):
        """
        Assign user-defined channel names and units to logger if supplied.
        Otherwise use header info from a test file and create dummy header columns for any columns
        to process not found in test file.
        """

        # First check columns detected in test make sense with requested columns to process
        if len(self.cols_to_process) > 0:
            last_col = max(self.cols_to_process)
        else:
            msg = f"Need to input columns to process for logger {self.logger_id} or disable processing."
            raise LoggerError(msg)

        test_file = self.files[0]
        file_path = os.path.join(self.logger_path, test_file)

        # Read first data row
        with open(file_path) as f:
            [next(f) for _ in range(self.num_headers)]
            first_row = f.readline().strip().split(self.file_delimiter)

        # Check we have at least one full row of data
        if last_col > len(first_row):
            msg = (
                f"Number of columns in test file for logger {self.logger_id} is less than {last_col}."
                f"\nTest file: {test_file}."
            )
            raise LoggerError(msg)

        # Now set channel names and units for columns to process
        all_channels = self.all_channel_names
        all_units = self.all_channel_units
        warn_flag = False

        # Use user-defined channel names
        if len(self.user_channel_names) > 0:
            self.channel_names = self.user_channel_names
        # Use channel names detected from test file
        else:
            # Check number of columns in header row is sufficient
            # Construct lists of columns present and missing in test file
            num_cols = len(all_channels) + 1
            present_cols = [c for c in self.cols_to_process if c - num_cols <= 0]
            missing_cols = [c for c in self.cols_to_process if c - num_cols > 0]

            # Construct list of dummy channel names for column numbers not in test file
            dummy_cols = [f"Column {i}" for i in missing_cols]

            # Keep headers requested (append dummy channel names if exist)
            self.channel_names = [all_channels[i - 2] for i in present_cols] + dummy_cols

            if missing_cols:
                warn_flag = True

        # Use user-defined channel units
        if len(self.user_channel_units) > 0:
            self.channel_units = self.user_channel_units
        # Use channel units detected from test file
        else:
            # Check number of columns in units row is sufficient
            # Construct lists of columns present and missing in test file
            num_cols = len(all_units) + 1
            present_cols = [c for c in self.cols_to_process if c - num_cols <= 0]
            missing_cols = [c for c in self.cols_to_process if c - num_cols > 0]

            # Construct list of dummy channel names for column numbers not in test file
            dummy_cols = ["-"] * len(missing_cols)

            # Keep headers requested (append dummy channel units if exist)
            self.channel_units = [all_units[i - 2] for i in present_cols] + dummy_cols

            if missing_cols:
                warn_flag = True

        # If missing cols found, warn user
        if warn_flag is True:
            msg = (
                f"Number of columns in test file for logger {self.logger_id} is less than {last_col}.\n\n"
                f"Dummy column names will be created for missing columns.\n\n"
                f"Alternatively, input custom channel and unit names."
                f"\nTest file: {test_file}."
            )
            self.signal_warning.emit(msg)

    def check_headers(self):
        """Check that there is a channel name and channel units per requested column to process."""

        # Check number of analysis headers is correct
        if self.process_stats is True or self.process_spectral is True:
            # Check length of channel header
            if len(self.channel_names) != len(self.cols_to_process):
                msg = f"Number of channel names specified does not equal number of " \
                    f"channels to process for logger {self.logger_id}."
                raise LoggerError(msg)

            # Check length of units header
            if len(self.channel_units) != len(self.cols_to_process):
                msg = f"Number of units specified does not equal number of " \
                    f"channels to process for logger {self.logger_id}."
                raise LoggerError(msg)

    def check_header_specification(self):
        """
        TO DELETE - DAT ROUTINE:
        Check that user has provided either the channel/units header row or user channel and unit names.
        """

        # Check something has been entered for channel names
        if self.channel_header_row == 0 and len(self.user_channel_names) == 0:
            msg = f"Either the channel header row or user-defined channel names" \
                f"must be specified for logger {self.logger_id}."
            raise LoggerError(msg)

        # Check something has been entered for units
        # if self.units_header_row == 0 and len(self.user_channel_units) == 0:
        #     msg = f"Either the units header row or user-defined channel units" \
        #         f"must be specified for logger {self.logger_id}."
        #     raise LoggerError(msg)

    def detect_requested_channels_and_units(self, test_file):
        """
        TO DELETE - DAT ROUTINE:
        Detect number of columns and channel names/units from headers of logger file.
        """

        file_path = os.path.join(self.logger_path, test_file)
        delim = self.file_delimiter

        # Get headers and first line of data
        with open(file_path) as f:
            header_lines = [
                f.readline().strip().split(delim) for _ in range(self.num_headers)
            ]
            first_row = f.readline().strip().split(delim)

        # Rows/cols to process
        last_stats_col = max(self.cols_to_process)
        c = self.channel_header_row
        u = self.units_header_row

        # Check requested columns make sense
        # Error message to raise if *STATS_COLUMNS doesn't make sense
        msg = "Error in *STATS_COLUMNS for logger " + self.logger_id
        msg += "\n Number of columns in first file is less than " + str(last_stats_col)
        msg += "\n File: " + test_file

        # TODO: Sort this out for topside data where not all columns are present
        # Check we have at least one full row of data
        if last_stats_col > len(first_row):
            raise LoggerError(msg)

        # Get headers for the columns to be processed
        if c > 0:
            header = header_lines[c - 1]

            # TODO: Sort this out for topside data where not all columns are present
            # Check number of columns in header row is sufficient
            if last_stats_col > len(header):
                raise LoggerError(msg)

            # TODO: Issue here if first file doesn't have all columns
            # Keep headers requested
            self.channel_names = [header[i - 1] for i in self.cols_to_process]

        # Get units for the columns to be processed
        if u > 0:
            units = header_lines[u - 1]

            # TODO: Sort this out for topside data where not all columns are present
            # Check number of columns in units row is sufficient
            if last_stats_col > len(units):
                raise LoggerError(msg)

            # TODO: Issue here if first file doesn't have all columns
            # Keep headers requested
            self.channel_units = [units[i - 1] for i in self.cols_to_process]

    def check_for_user_headers(self):
        """
        TO DELETE - DAT ROUTINE:
        Assign user-defined channel names and units to logger if supplied.
        """

        if len(self.user_channel_names) > 0:
            self.channel_names = self.user_channel_names
        if len(self.user_channel_units) > 0:
            self.channel_units = self.user_channel_units
