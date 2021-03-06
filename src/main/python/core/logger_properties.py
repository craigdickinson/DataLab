"""Class to hold logger properties."""

__author__ = "Craig Dickinson"

import os
from glob import glob

from PyQt5.QtCore import QObject, pyqtSignal
from dateutil.parser import parse
from natsort import natsorted

from core.azure_cloud_storage import (
    connect_to_azure_account,
    extract_container_name_and_folders_path,
    get_blobs,
    stream_blob,
)
from core.custom_date import get_date_code_span, make_time_str


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


class LoggerWarning(Error):
    """Exception raised for errors in the logger properties that wish to report as warnings.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class LoggerProperties(QObject):
    """Holds properties of a logger."""

    logger_warning_signal = pyqtSignal(str)

    def __init__(self, logger_id=""):
        super().__init__()

        # =================
        # LOGGER PROPERTIES
        # =================
        # Name and location
        self.logger_id = logger_id
        self.enabled = True
        self.data_on_azure = False
        self.logger_path = ""

        # Azure account access settings, container name and blobs list
        self.azure_account_name = ""
        self.azure_account_key = ""
        self.container_name = ""
        self.blobs = []

        # File format variables
        self.file_format = "Custom"
        self.file_timestamp_embedded = True
        self.file_timestamp_format = ""
        self.first_col_data = "Timestamp"
        self.file_ext = ""
        self.file_delimiter = ","

        # Number of rows/columns expected
        self.num_headers = 0
        self.num_columns = 0

        # Header row numbers. Note 1-indexed!
        self.channel_header_row = 0
        self.units_header_row = 0

        # Logging data properties
        self.timestamp_format = ""

        # Datetime format string to convert timestamp strings to datetimes, e.g. %d-%b-%Y %H:%M:%S.%f
        self.datetime_format = ""
        self.freq = 0
        self.duration = 0
        self.num_files = 0
        self.expected_data_points = 0

        # Store index column name of raw files (to report in the channels list widget on the config dashboard)
        self.index_col_name = "Timestamp"

        # Channel names and units lists
        self.all_channel_names = []
        self.all_channel_units = []

        # List of raw filenames
        self.raw_filenames = []

        # Lists of accepted filenames to process, their file timestamps (if applicable)
        # and file index (out of the raw filenames list)
        self.files = []
        self.file_timestamps = []
        self.file_indices = []

        # Dictionary of files with bad timestamps
        self.dict_bad_filenames = {}

        # File timestamp component start and end indexes
        self.year_span = None
        self.month_span = None
        self.day_span = None
        self.hour_span = None
        self.min_span = None
        self.sec_span = None
        self.ms_span = None

        # Flag to force maximum interval length (i.e. file length) if file format is Custom format
        # with raw files containing a time steps index;
        # this is to ensure results files contain a unique file number index
        self.enforce_max_duration = False

        # ==========================
        # GENERAL SCREENING SETTINGS
        # ==========================
        # Channel columns to process
        self.cols_to_process = []

        # Channel unit conversion factors
        self.unit_conv_factors = []

        # Requested channel names and units
        self.channel_names = []
        self.channel_units = []

        # Custom channel names and units
        self.user_channel_names = []
        self.user_channel_units = []

        # Datetime or file index range to process over
        self.process_start = None
        self.process_end = None
        self.num_selected_files = 0

        # Data type to screen on (unfiltered only, filtered only, both unfiltered and filtered)
        self.process_type = "Both unfiltered and filtered"

        # Cut-off frequencies for filtered screening analysis
        self.low_cutoff_freq = 0.05
        self.high_cutoff_freq = 0.5

        # ========================
        # STATS SCREENING SETTINGS
        # ========================
        self.process_stats = True
        self.stats_interval = 0

        # ===========================
        # SPECTRAL SCREENING SETTINGS
        # ===========================
        self.process_spect = True
        self.spect_interval = 0

        # PSD parameters
        self.psd_nperseg = 1000
        self.psd_window = "Hann"
        self.psd_overlap = 50

        # ========================
        # CYCLE HISTOGRAM SETTINGS
        # ========================
        self.process_hists = True
        self.channel_bin_sizes = [1]
        self.channel_num_bins = [50]

        # ==================================
        # TIME SERIES INTEGRATION PROPERTIES
        # ==================================
        self.process_integration = True

        # Apply gravity correction
        self.apply_gcorr = True

        # Create an RMS summary csv file of displacements and/or angles for all files
        self.output_rms_summary = True

        # Column names to convert
        self.acc_x_col = "Not used"
        self.acc_y_col = "Not used"
        self.acc_z_col = "Not used"
        self.ang_rate_x_col = "Not used"
        self.ang_rate_y_col = "Not used"

        # Units conversions
        self.acc_x_units_conv = "-"
        self.acc_y_units_conv = "-"
        self.acc_z_units_conv = "-"
        self.ang_rate_x_units_conv = "-"
        self.ang_rate_y_units_conv = "-"

        # Low cut-off frequencies
        self.acc_x_low_cutoff = 0.25
        self.acc_y_low_cutoff = 0.25
        self.acc_z_low_cutoff = 0.25
        self.ang_rate_x_low_cutoff = 0.25
        self.ang_rate_y_low_cutoff = 0.25

        # High cut-off frequencies
        self.acc_x_high_cutoff = 2.0
        self.acc_y_high_cutoff = 2.0
        self.acc_z_high_cutoff = 2.0
        self.ang_rate_x_high_cutoff = 2.0
        self.ang_rate_y_high_cutoff = 2.0

    def get_filenames(self):
        """Read all file timestamps and check that they conform to the specified format."""

        self.raw_filenames = []

        if not self.logger_path:
            return

        if self.data_on_azure:
            filenames = self.get_filenames_on_azure()
        else:
            filenames = self.get_filenames_on_local()

        self.raw_filenames = filenames
        self.num_files = len(filenames)

        return filenames

    def get_filenames_on_local(self):
        """Get all filenames with specified extension in logger path."""

        # Get filenames and use natsort to ensure files are sorted correctly
        # (i.e. not lexicographically e.g. 0, 1, 10, 2)
        filenames = [os.path.basename(f) for f in glob(self.logger_path + "/*." + self.file_ext)]
        filenames = natsorted(filenames)

        if not filenames:
            msg = f"No {self.logger_id} files with the extension {self.file_ext} found in:\n{self.logger_path}."
            raise FileNotFoundError(msg)

        return filenames

    def get_filenames_on_azure(self):
        """Get all filenames with specified extension stored on Azure Cloud Storage container."""

        self.container_name = ""
        self.blobs = []

        try:
            bloc_blob_service = connect_to_azure_account(
                self.azure_account_name, self.azure_account_key
            )
        except Exception as e:
            raise LoggerError(e)

        try:
            container_name, virtual_folders_path = extract_container_name_and_folders_path(
                self.logger_path
            )
            blobs = get_blobs(bloc_blob_service, container_name, virtual_folders_path)
            blobs = natsorted(blobs)

            # Store container name and blobs list
            self.container_name = container_name
            self.blobs = blobs
        except Exception:
            msg = f"Could not connect to {container_name} container on Azure Cloud Storage account."
            raise LoggerError(msg)

        ext = "." + self.file_ext.lower()
        filenames = [os.path.basename(f) for f in blobs if os.path.splitext(f)[1].lower() == ext]

        if not filenames:
            msg = (
                f"No {self.logger_id} files with the extension {self.file_ext} found in:\n{self.logger_path} "
                f"on Azure Cloud Storage account."
            )
            raise FileNotFoundError(msg)

        return filenames

    def get_timestamp_span(self):
        """Extract timestamp code spans using filename format given in control file."""

        # File timestamp format
        f = self.file_timestamp_format

        # Get position of Y, m, D, H, M, S and ms strings
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
        self.file_indices = []

        for i, f in enumerate(self.raw_filenames):
            date = self.get_file_timestamp(f)

            if date is None:
                self.dict_bad_filenames[f] = "Unable to parse datetime from filename"
            else:
                # Append if date is successfully parsed
                self.files.append(f)
                self.file_timestamps.append(date)
                self.file_indices.append(i)

        # Check at least one valid file was found
        # if not self.files:
        #     msg = (
        #         f"No file names with a valid embedded timestamp found for {self.logger_id}.\n\n"
        #         f"Check the file timestamp format input and the files in\n{self.logger_path}."
        #     )
        #     raise LoggerError(msg)

    def get_file_timestamp(self, f):
        """
        Attempt to extract timestamp embedded in logger filename.
        :param f: logger filename
        :return: filename datetime as string
        """

        y = f[self.year_span[0] : self.year_span[1]]
        m = f[self.month_span[0] : self.month_span[1]]
        d = f[self.day_span[0] : self.day_span[1]]
        h = f[self.hour_span[0] : self.hour_span[1]]
        minute = f[self.min_span[0] : self.min_span[1]]
        sec = f[self.sec_span[0] : self.sec_span[1]]
        ms = f[self.ms_span[0] : self.ms_span[1]]

        # Date must contain y, m and d
        date_str = y + "-" + m + "-" + d

        # Construct time string
        time_str = make_time_str(h, minute, sec, ms)

        # Construct full datetime string
        datetime_str = (date_str + " " + time_str).strip()

        # Try to convert string to date
        try:
            return parse(datetime_str, yearfirst=True)
        except ValueError:
            return None

    def set_files_to_process(self):
        """Set selected files to process."""

        if self.file_timestamp_embedded is True:
            self.get_timestamp_span()
            self.check_file_timestamps()

            # Select only files in date range to process on
            self.select_files_in_date_range(self.process_start, self.process_end)
        else:
            self.select_files_in_index_range(self.process_start, self.process_end)

        self.num_selected_files = len(self.files)

    def select_files_in_date_range(self, start_date=None, end_date=None):
        """
        Select files for processing within start_date, end_date range range.
        :param start_date: datetime
        :param end_date: datetime
        :return: New list of file_timestamps and files within date range
        """

        if not self.files:
            return

        # Use first and last raw logger filenames if no start/end dates read from control file
        if start_date is None:
            start_date = min(self.file_timestamps)
        if end_date is None:
            end_date = max(self.file_timestamps)

        dates_files = [
            (i, d, f)
            for i, d, f in zip(self.file_indices, self.file_timestamps, self.files)
            if start_date <= d <= end_date
        ]

        # Make sure files are processed in correct order (and make sure they are lists not tuples)
        try:
            i, d, f = list(zip(*dates_files))
            self.file_indices = list(i)
            self.file_timestamps = list(d)
            self.files = list(f)
        # Empty lists
        except ValueError:
            msg = (
                f"No valid logger files found within date range input for {self.logger_id}.\n"
                f"Check date range and file timestamp inputs."
            )
            raise LoggerError(msg)

    def select_files_in_index_range(self, start_idx, end_idx):
        """Select files for processing within start_idx, end_idx range."""

        # Use first file if no start index read from control file
        if start_idx is None:
            start_idx = 1

        # Use last file if no end index read from control file
        if end_idx is None:
            end_idx = len(self.files)

        # Slice files to process
        self.files = self.raw_filenames[start_idx - 1 : end_idx]

        # Slice file indices to process
        self.file_indices = list(range(start_idx - 1, end_idx))

    def get_all_columns(self):
        """Store all channel and units names extracted from the header of a test file."""

        # Initialise lists
        self.all_channel_names = []
        self.all_channel_units = []

        if not self.raw_filenames:
            return

        # Set test file to read and file format read properties
        # Create a file stream of blob from Azure
        if self.data_on_azure:
            test_blob = self.blobs[0]
            bloc_blob_service = connect_to_azure_account(
                self.azure_account_name, self.azure_account_key
            )
            test_file = stream_blob(bloc_blob_service, self.container_name, test_blob)
        # Read local file
        else:
            test_file = os.path.join(self.logger_path, self.raw_filenames[0])

        file_format = self.file_format
        delim = self.file_delimiter
        c = self.channel_header_row
        u = self.units_header_row

        # Get column names and units, if exist
        if file_format == "Custom":
            channels, units = self.read_column_names(test_file, delim, c, u, decoding="utf-8")
        elif file_format == "Fugro-csv":
            channels, units = self.read_column_names(test_file, delim, c, u, decoding="latin1")
        elif file_format == "Pulse-acc":
            channels, units = self.read_columns_pulse(test_file, c)
        elif file_format == "2HPS2-acc":
            channels, units = self.read_column_names_2hps2(test_file, delim, c)

        # Assign channels and units list to logger - encode and decode to handle ascii characters
        try:
            self.all_channel_names = [c.strip().encode("latin1").decode() for c in channels]
        except UnicodeDecodeError:
            self.all_channel_names = [c.strip() for c in channels]

        try:
            self.all_channel_units = [u.strip().encode("latin1").decode() for u in units]
        except UnicodeDecodeError:
            self.all_channel_units = [u.strip() for u in units]

        return channels, units

    def read_column_names(self, test_file, delim, c, u, decoding):
        """Retrieve channel and unit names from a general or Fugro-csv file."""

        # Read channel and unit name rows, if exist - from Azure file stream or local file
        if self.data_on_azure:
            header_lines = [
                test_file.readline().decode(decoding).strip().split(delim)
                for _ in range(self.num_headers)
            ]
        else:
            with open(test_file) as f:
                header_lines = [f.readline().strip().split(delim) for _ in range(self.num_headers)]

        # Extract list of channel names and units (drop the first item - expected to be timestamp)
        if c > 0:
            self.index_col_name = header_lines[c - 1][0]
            channels = header_lines[c - 1][1:]
        # If no channels header exists
        else:
            # Set index column name
            if self.first_col_data == "Timestamp":
                self.index_col_name = "Timestamp"
            else:
                self.index_col_name = "Time (s)"

            # Create a dummy channel list
            channels = [f"Column {i}" for i in range(2, self.num_columns + 1)]

        if u > 0:
            units = header_lines[u - 1][1:]
        # If no units header exists, create a dummy list
        else:
            units = ["-"] * (self.num_columns - 1)

        return channels, units

    def read_columns_pulse(self, test_file, c):
        """Retrieve channel and unit names from a Pulse-acc file."""

        # Read columns header - from Azure file stream or local file
        if self.data_on_azure:
            [test_file.readline() for _ in range(c - 1)]
            header = test_file.readline().decode("latin1").strip().split(":")
        else:
            with open(test_file, "r") as f:
                [next(f) for _ in range(c - 1)]
                header = f.readline().strip().split(":")

        # Drop "%Data," from the first column
        header[0] = header[0].split(",")[1]

        # Extract lists of channel names and units
        self.index_col_name = "Time (s)"
        channels = [i.split("(")[0].strip() for i in header]
        units = [i.split("(")[1][:-1] for i in header]

        return channels, units

    def read_column_names_2hps2(self, test_file, delim, c):
        """Retrieve channel and unit names from a 2HPS2-acc file."""

        # Read channel and unit name rows - from Azure file stream or local file
        if self.data_on_azure:
            [test_file.readline() for _ in range(c - 1)]
            channels = test_file.readline().decode().strip().split(delim)
            units = test_file.readline().decode().strip().split(delim)
        else:
            with open(test_file, "r") as f:
                [next(f) for _ in range(c - 1)]
                channels = f.readline().strip().split(delim)
                units = f.readline().strip().split(delim)

        # Extract lists of channel names and units
        # Convert column names list so that split by "," not " ", drop "Time" item and trim
        self.index_col_name = "Time (s)"
        channels = " ".join(channels).split(",")[1:]
        channels = [c.strip() for c in channels]
        units = " ".join(units).split(",")[1:]
        units = [i.strip().split("(")[1][:-1] for i in units]

        return channels, units

    def set_selected_column_and_units_names(self):
        """
        Assign user-defined channel names and units to logger if supplied.
        Otherwise use header info from a test file and create dummy header columns for any columns
        to process not found in test file.
        """

        # Check columns to process have been set
        if self.cols_to_process:
            last_col = max(self.cols_to_process)
        else:
            # Select all columns using the expected number of columns property
            if self.num_columns > 0:
                self.cols_to_process = list(range(2, self.num_columns + 1))
                last_col = max(self.cols_to_process)
            else:
                msg = f"Need to input number of expected columns for {self.logger_id}."
                raise LoggerError(msg)

        # Read first data row from a test file
        test_file, first_row = self._get_data_first_row()

        # Check we have at least one full row of data
        n = len(first_row)
        if last_col > n:
            msg = (
                f"Number of columns in test file for {self.logger_id} ({n}) is less than {last_col}, "
                f"which is the highest column number to be processed."
                f"\n\nTest file: {test_file}."
            )
            self.logger_warning_signal.emit(msg)

        # Now set channel names and units for columns to process
        all_channels = self.all_channel_names
        all_units = self.all_channel_units
        warn_flag = False

        # Use user-defined channel names
        if self.user_channel_names:
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
        if self.user_channel_units:
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

        # If missing cols found, inform user
        # Note emitting a message not raise an error so that screening is not halted
        if warn_flag is True:
            msg = (
                f"Number of columns in test file for {self.logger_id} is less than {last_col}.\n"
                f"{len(dummy_cols)} dummy column names will be created for missing columns.\n"
                f"Alternatively, input custom channel and unit names."
                f"\n\nTest file: {test_file}."
            )
            self.logger_warning_signal.emit(msg)

        return self.channel_names, self.channel_units

    def _get_data_first_row(self, file_idx=0):
        """
        Read first data row to validate on.
        :return: name of test file, first data row list
        """

        # Stream test file (blob) on Azure Cloud Storage
        if self.data_on_azure:
            test_blob = self.blobs[file_idx]
            test_file = os.path.basename(test_blob)
            bloc_blob_service = connect_to_azure_account(
                self.azure_account_name, self.azure_account_key
            )
            fs = stream_blob(bloc_blob_service, self.container_name, test_blob)
            [fs.readline() for _ in range(self.num_headers)]
            first_row = fs.readline().decode().strip().split(self.file_delimiter)
        # Read test file on local drive
        else:
            try:
                test_file = self.files[file_idx]
            except IndexError:
                test_file = ""
                first_row = []
            else:
                test_path = os.path.join(self.logger_path, test_file)
                with open(test_path) as f:
                    [f.readline() for _ in range(self.num_headers)]
                    first_row = f.readline().strip().split(self.file_delimiter)

        # Remove blanks (can happen with space-delimited files)
        first_row = [x for x in first_row if x != ""]

        return test_file, first_row

    def check_if_units_in_channel_name(self):
        """Check for columns with no units set and check if units are in channel name; if so extract to units list."""

        channels = self.channel_names
        units = self.channel_units
        p = -1

        for i, u in enumerate(units):
            if u == "-":
                channel = channels[i]

                # Attempt to find possible embedded units in the channel name of the form "(units)" or "[units]"
                if "(" in channel:
                    p = channel.index("(")
                if "[" in channel:
                    p = channel.index("[")

                # Expected units found - remove units from channel name and add to units list
                if p > -1:
                    new_channel = channel[:p].strip()
                    new_units = channel[p + 1 :]
                    if new_units.endswith(")") or new_units.endswith("]"):
                        new_units = new_units[:-1]

                    channels[i] = new_channel
                    units[i] = new_units

        self.channel_names = channels
        self.channel_units = units

        return self.channel_names, self.channel_units

    def check_headers(self):
        """Check that there is a channel name and channel units per requested column to process."""

        # Check length of channels header
        n = len(self.channel_names)
        m = len(self.cols_to_process)
        if n != m:
            msg = (
                f"Number of channel names specified ({n}) does not equal number of "
                f"channels to process ({m}) for {self.logger_id}."
            )
            raise LoggerError(msg)

        # Check length of units header
        n = len(self.channel_units)
        if n != m:
            msg = (
                f"Number of units specified ({n}) does not equal number of "
                f"channels to process ({m}) for {self.logger_id}."
            )
            raise LoggerError(msg)
