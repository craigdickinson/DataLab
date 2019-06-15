"""
Class to setup project control.
"""
import os.path

from dateutil.parser import parse

from app.core.custom_date import get_datetime_format
from app.core.fugro_csv_properties import (
    read_fugro_headers,
    read_fugro_sample_interval,
    set_fugro_csv_file_format,
)
from app.core.logger_properties import LoggerProperties

# Used in get_delimiter() method
delimiters = dict(comma=",", space=" ")


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


class Control(object):
    """Contain and process input settings."""

    def __init__(self):
        """Initialise control file properties."""

        # Control filename to read from
        self.control_file = ""
        self.config_file = ""

        # List to hold text lines from control file
        self.data = []

        # Project and campaign details
        self.project_num = ""
        self.project_name = ""
        self.campaign_name = ""
        self.project_path = ""

        # Output settings
        self.output_folder = ""

        # Selected stats output file formats
        self.stats_to_h5 = True
        self.stats_to_csv = False
        self.stats_to_xlsx = False

        # Selected spectral output file formats
        self.spect_to_h5 = True
        self.spect_to_csv = False
        self.spect_to_xlsx = False

        # List to store lines with *LOGGER_ID
        self.logger_id_lines = []

        # List of logger ids
        self.logger_ids = []
        self.logger_ids_upper = []

        # List of logger objects from LoggerProperties class
        # Each logger object will contain the majority of input parameters
        self.loggers = []

    def set_filename(self, filename):
        """Set control file to read from """

        self.control_file = filename

    def analyse(self):
        """Read all data from control file"""

        self.read_data_from_control_file()
        self.get_project_name()
        self.get_campaign_name()
        self.get_output_folder()
        self.ensure_dir_exists(self.output_folder)
        self.process_logger_names()
        self.add_loggers()

    def read_data_from_control_file(self):
        """Read all lines from control file into internal list."""

        with open(self.control_file, "r") as filestream:
            self.data = self.read_data_from_filestream(filestream)

    def read_data_from_filestream(self, filestream):
        """Return all lines from filestream."""

        return filestream.readlines()

    def get_project_name(self):
        """Extract project name from control data."""

        key = "*PROJECT_NAME"
        _, self.project_name = self.get_key_data(key, self.data)
        if self.project_name == "":
            raise InputError("No project name found in control file")

    def get_campaign_name(self):
        """Extract campaign name from control data."""

        key = "*CAMPAIGN_NAME"
        _, self.campaign_name = self.get_key_data(key, self.data)
        if self.campaign_name == "":
            raise InputError("No campaign name found in control file")

    def get_output_folder(self):
        """Extract output name from control data."""

        key = "*OUTPUT_FOLDER"
        _, self.output_folder = self.get_key_data(key, self.data)
        if self.output_folder == "":
            raise InputError("No output folder name found in control file")

    def ensure_dir_exists(self, directory):
        """Create directory (and intermediate directories) if do not exist."""

        if directory != "" and os.path.exists(directory) is False:
            os.makedirs(directory)

    def process_logger_names(self):
        """Extract all logger names from control file and check for uniqueness."""

        # Find lines in control file with *LOGGER_ID
        self.get_logger_ids()

        # Check all ids are unique
        self.check_logger_ids(self.logger_ids)

    def get_logger_ids(self):
        """Get *LOGGER_ID line numbers from control data."""

        i = 0
        j = 0
        while (j < len(self.data) - 1) and (i != -1):
            i, logger_id = self.get_key_data(key="*LOGGER_ID", data=self.data[j:])

            # Append logger if new
            if i > -1:
                j += i
                self.logger_id_lines.append(j)
                self.logger_ids.append(logger_id)
                j += 1

        # Check at least one logger id was found
        if len(self.logger_id_lines) == 0:
            msg = "No logger id found in control file"
            raise InputError(msg)

        # List of upper case logger IDs
        self.logger_ids_upper = [log_id.upper() for log_id in self.logger_ids]

    def check_logger_ids(self, id_list):
        """Check for duplicate logger names."""

        if len(id_list) != len(set(id_list)):
            msg = "Duplicate logger ids detected"
            raise InputError(msg)

    def add_loggers(self):
        """Read control file and set logger properties."""

        # Create containers for file format/logger properties
        for name in self.logger_ids:
            self.loggers.append(LoggerProperties(name))

        # Control file text lines
        data = self.data

        # Read in required properties for each logger
        logger_id_lines = self.logger_id_lines
        self.set_logger_file_paths(logger_id_lines, data)

        # Get file format of each logger
        for i, logger in enumerate(self.loggers):
            print(f"Analysing logger {i + 1} of {len(self.loggers)}")

            # Get portion of control file referring to logger
            logger_data = self.slice_data(i, logger_id_lines, data)

            # Check file format
            key1 = "*FILE_FORMAT"
            _, file_format = self.get_key_data(key1, logger_data)

            key2 = "*COPY_FILE_FORMAT"
            _, copy_file_format = self.get_key_data(key2, logger_data)

            if (file_format == "") and (copy_file_format == ""):
                msg = key1 + " or " + key2 + " not specified for logger "
                msg += logger.logger_id
                raise InputError(msg)
            # Check only one format option specified
            elif (file_format != "") and (copy_file_format != ""):
                msg = key1 + " or " + key2 + " cannot both be specified for logger "
                msg += logger.logger_id
                raise InputError(msg)

            # Get file timestamp - *FILE_TIMESTAMP - if not copying file format settings of a previous logger
            if copy_file_format == "":
                file_timestamp_format = self.get_file_timestamp(logger_data)

                # Key not found
                if file_timestamp_format == "":
                    msg = f"File timestamp format for {logger.logger_id} not found"
                    raise InputError(msg)
                logger.file_timestamp_format = file_timestamp_format

            # Assign file format-specific logger properties
            # General file format
            if file_format.lower() == "general-csv":
                self.set_general_file_format(logger, logger_data)
            # Fugro csv format - need to detect some properties from the file
            # However we want to check all data in control file is valid first
            # So just extract the information from the control file for now
            elif file_format.lower() == "fugro-csv":
                self.set_fugro_file_format(logger, logger_data)
            # Copy logger file format of logger properties provided
            elif copy_file_format != "":
                self.copy_file_format(logger, logger_data)
            # Unknown format
            else:
                raise InputError("File format option not recognised.")

            # Get logging duration and header info if not copying file format settings of a previous logger
            if copy_file_format == "":
                # Get logging duration
                self.get_logging_duration(logger, logger_data)

                # Check for user defined headers and units
                self.get_user_headers(logger, logger_data)

                # Check at least one header specification has been made
                logger.check_header_specification()

            # Get stats format
            self.read_or_copy_stats_format(logger, logger_data)

            # Get filenames and check timestamps
            logger.process_filenames()

            # Select only files within specified datetime range
            logger.select_files_in_datetime_range(logger.process_start, logger.process_end)

            # Select first logger file to detect additional properties and checks on
            test_file = logger.files[0]

            # Now detect any properties we need to from known file formats
            if logger.file_format.lower() == "fugro-csv":
                # Detect sample rate and timestamp format from first Fugro file
                self.detect_fugro_file_properties(logger, test_file)

            # Detect number of columns and read headers from the first file
            logger.detect_requested_channels_and_units(test_file)

            # Set expected number of points
            logger.expected_data_points = logger.freq * logger.duration

            # Make any user defined units and channels override any detected
            logger.check_for_user_headers()

            # Check header lengths match number of columns
            logger.check_headers()

            # Check if spectrograms are to be generated
            # self.get_spectrograms(logger_data)

    def set_logger_file_paths(self, logger_id_lines, data):
        """
        Retrieve the file path of each logger and assign to its logger object.
        :param logger_id_lines: list of lines that each logger's commands start
        :param data: control file data
        :return:
        """

        for i in range(len(logger_id_lines)):
            # Extract only control file lines pertaining to current logger
            logger_data = self.slice_data(i, logger_id_lines, data)

            # Logger pointer - will still update self.loggers[i] attributes
            logger = self.loggers[i]
            logger_id = logger.logger_id
            logger.logger_path = self.get_logger_path(logger_id, logger_data)

    def slice_data(self, index, slice_array, data):
        """Return elements of data between slice_array[index] and slice_array[index + 1]."""

        i = slice_array[index]
        if index < len(slice_array) - 1:
            return data[i : slice_array[index + 1]]
        else:
            return data[i:]

    def set_general_file_format(self, logger, data):
        """
        Set:
            file_format
            file_timestamp
            file_ext
            file_delimiter
            num_headers
            num_columns
            timestamp_format
            freq
            duration
            expected_data_points
            channel_header_row
            units_header_row
        """

        logger_id = logger.logger_id
        logger.file_format = "general-csv"

        # Get file extension - *EXTENSION
        logger.file_ext = self.get_extension(data)

        # Key not found
        if logger.file_ext == "":
            msg = f"Extension for {logger_id} data not found"
            raise InputError(msg)

        # Get file delimiter - *DELIMITER
        logger.file_delimiter = self.get_delimiter(data)

        # Key not found
        if logger.file_delimiter == "":
            msg = f"Delimiter for {logger_id} data not found"
            raise InputError(msg)

        # Get number of header lines
        key = "*NUM_HEADERS"
        i, num_rows_str = self.get_key_data(key, data)
        if i < 0:
            msg = f"{key} data not found for {logger_id}"
            raise InputError(msg)
        logger.num_headers = self.get_integer_key_data(key, num_rows_str)

        # Get total number of columns
        # TODO remove
        # key = '*NUM_COLUMNS'
        # i, num_col_str = self.get_key_data(key, data)
        # if i < 0:
        #     msg = key + ' data not found for ' + logger_id
        #     raise InputError(msg)
        # num_columns = self.get_integer_key_data(key, num_col_str)
        # logger.num_columns = num_columns

        # Get timestamp format
        self.get_timestamp(logger, data)

        # Get logging frequency
        key = "*LOGGING_FREQUENCY"
        i, freq_str = self.get_key_data(key, data)
        if i < 0:
            msg = f"{key} data not found for {logger_id}"
            raise InputError(msg)
        freq = self.get_float_key_data(key, freq_str)
        logger.freq = freq

        # Optional keywords
        # Get channel and unit names header numbers
        self.get_header_rows(logger, data)

    def set_fugro_file_format(self, logger, data):
        """
        Set the following logger properies to Fugro standard file format:
            file_format
            file_ext
            file_delimiter
            num_headers
            channel_header_row
            units_header_row
        """

        logger_id = logger.logger_id
        logger = set_fugro_csv_file_format(logger)

        # TODO CD note: num_columns is never used in code! Question if required?
        # Also get total number of columns
        # key = '*NUM_COLUMNS'
        # j, num_col_str = self.get_key_data(key, data)
        # if j < 0:
        #     msg = key + ' data not found for ' + logger.logger_id
        #     raise InputError(msg)
        # num_columns = self.get_integer_key_data(key, num_col_str)
        # logger.num_columns = num_columns

    def copy_file_format(self, logger, data):
        """Copy file format of another logger."""

        key = "*COPY_FILE_FORMAT"
        _, logger1_name = self.get_key_data(key, data)

        # Find existing logger
        logger1_upper = logger1_name.upper()
        if logger1_upper in self.logger_ids_upper:
            logger1_idx = self.logger_ids_upper.index(logger1_upper)
        else:
            msg = "Logger id " + logger1_upper + " in " + key + " not found"
            raise InputError(msg)

        # Check current logger appears after logger being copied
        if logger1_idx >= self.logger_ids.index(logger.logger_id):
            msg = "Logger id in " + key + " not found"
            raise InputError(msg)

        # Attributes to copy
        names = [
            "file_format",
            "file_timestamp_format",
            "timestamp_format",
            "file_ext",
            "file_delimiter",
            "num_headers",
            # 'num_columns',
            "freq",
            "duration",
            "expected_data_points",
            "channel_header_row",
            "units_header_row",
            "channel_names",
            "channel_units",
            "user_channel_names",
            "user_channel_units",
        ]

        # Copy attributes from reference logger
        ref_logger = self.loggers[logger1_idx]
        self.copy_logger_attributes(ref_logger, logger, names)

    def get_user_headers(self, logger, data):
        """Extract user defined header and unit names."""

        # Get user defined channel names
        key = "*CHANNEL_NAMES"
        i, chan_names_str = self.get_key_data(key, data)
        if i > -1:
            logger.user_channel_names = chan_names_str.split()

        # Get user defined units
        key = "*CHANNEL_UNITS"
        i, units_str = self.get_key_data(key, data)
        if i > -1:
            logger.user_channel_units = units_str.split()

    def read_or_copy_stats_format(self, logger, data):
        """Read file format from control file or copy from another logger."""

        key = "*COPY_STATS_FORMAT"
        i, ref_logger_name = self.get_key_data(key, data)

        # Read stats format inputs
        if i == -1:
            self.get_stats_format(logger, data)
        # Copy stats format inputs from an existing logger
        else:
            self.copy_stats_format(key, ref_logger_name, logger)

    def detect_fugro_file_properties(self, logger, file):
        """
        For Fugro logger file detect:
            sampling frequency
            timestamp format
        """

        # Use first file
        test_path = os.path.join(logger.logger_path, file)

        # Read sample interval
        sample_interval = read_fugro_sample_interval(test_path)

        # Convert to sample frequency
        if sample_interval > 0:
            logger.freq = int(1 / sample_interval)
        else:
            msg = "Could not read sample interval for logger "
            msg = msg + logger.logger_id + "\n"
            msg = msg + "File: " + file
            raise InputError(msg)

        # Read headers
        header, units = read_fugro_headers(test_path)

        # Check header lengths make sense
        if len(header) != len(units) or len(units) == 0:
            msg = "Headers in first file for logger " + logger.logger_id
            msg += "do not match Fugro-csv format"
            msg += "\n File: " + file
            raise InputError(msg)

        # TODO: Sort this out for topside data where not all columns are present
        #  Check stats columns make sense
        m = max(logger.cols_to_process)
        if m > len(header):
            msg = "Error in *STATS_COLUMNS for logger " + logger.logger_id
            msg += "\n Number of columns detected is less than " + str(m)
            msg += "\n File: " + file
            raise InputError(msg)

        # Determine timestamp format from first units header
        timestamp_format = units[0]
        logger.datetime_format = get_datetime_format(timestamp_format)

    def get_logging_duration(self, logger, data):
        """Get expected logging duration from control file."""

        logger_id = logger.logger_id

        # Get logging duration
        key = "*LOGGING_DURATION"
        i, dur_str = self.get_key_data(key, data)
        if i < 0:
            msg = key + " data not found for " + logger_id
            raise InputError(msg)
        duration = self.get_float_key_data(key, dur_str)
        logger.duration = duration

    def get_spectrograms(self, data):
        """Set flag to create spectrograms."""

        key = "*SPECTROGRAMS"
        i, _ = self.get_key_data(key, data)

        if i > -1:
            self.create_spectrograms.append(True)
        else:
            self.create_spectrograms.append(False)

    def get_file_timestamp(self, data):
        """Extract logger file timestamp from control file data."""

        key = "*FILE_TIMESTAMP"
        _, file_timestamp = self.get_key_data(key, data)

        return file_timestamp

    def get_extension(self, data):
        """Extract logger data file extension from control file data."""

        key = "*EXTENSION"
        _, extension = self.get_key_data(key, data)

        return extension

    def get_delimiter(self, data):
        """Extract logger data file delimiter from control file data."""

        key = "*DELIMITER"
        _, delim = self.get_key_data(key, data)

        # Assign delimiters associated with names
        if delim.lower() in delimiters:
            return delimiters[delim.lower()]
        else:
            return delim

    def get_timestamp(self, logger, data):
        """Get format for timestamp on time axis."""

        logger_id = logger.logger_id

        # Get timestamp axis processing option
        key = "*TIMESTAMP"
        i, timestamp_str = self.get_key_data(key, data)
        if i == -1:
            msg = key + " option not found for " + logger_id
            raise InputError(msg)

        logger.timestamp_format = timestamp_str

        # TODO: Set datetime_format to be the same for now. Intention will be that e.g.
        # timestamp_format = dd-mmm-yyyy HH:MM:SS.FFF
        # datetime_format = %d-%b-%Y %H:%M:%S.%f
        logger.datetime_format = timestamp_str

    def get_logger_path(self, logger_id, data):
        """Extract path to logger data from control file data."""

        key = "*PATH"
        i, logger_path = self.get_key_data(key, data)

        # key not found
        if i == -1:
            msg = "Path to " + logger_id + " must follow *LOGGER_ID"
            raise InputError(msg)

        # Check path exists
        if not os.path.exists(logger_path):
            msg = logger_path + " not found"
            raise InputError(msg)

        # Return logger path
        return logger_path

    def copy_logger_attributes(self, objfrom, objto, attribute_names):
        """Function to copy attributes from one object to another."""

        for n in attribute_names:
            try:
                param = getattr(objfrom, n)
                setattr(objto, n, param)
            except AttributeError:
                pass

    def get_header_rows(self, logger, data):
        """Extract header rows to read columns names and units from."""

        # Get channel header number
        key = "*CHANNEL_HEADER"
        i, row_num_str = self.get_key_data(key, data)
        if i > -1:
            logger.channel_header_row = self.get_integer_key_data(key, row_num_str)

        # Get units header number
        key = "*UNITS_HEADER"
        i, row_num_str = self.get_key_data(key, data)
        if i > -1:
            logger.units_header_row = self.get_integer_key_data(key, row_num_str)

    def get_stats_format(self, logger, data):
        """
        Get stats parameters to process from control file data.
        Store all parameters in the logger object.
        Extracts data from the following commands:
            *STATS_COLUMNS
            *STATS_UNIT_CONV_FACTORS
            *STATS_INTERVAL
            *STATS_START
            *STATS_END
        """

        # Get columns to process
        key = "*STATS_COLUMNS"
        i, stats_col_str = self.get_key_data(key, data)
        if i == -1:
            msg = key + " data not found for " + logger.logger_id
            raise InputError(msg)

        logger.cols_to_process = list(map(int, stats_col_str.split()))

        # Get unit conversion factors (optional)
        key = "*STATS_UNIT_CONV_FACTORS"
        i, unit_conv_factors_str = self.get_key_data(key, data)
        if i != -1:
            try:
                # Extract and store unit conversion factors
                unit_conv_factors = list(map(float, unit_conv_factors_str.split()))
                logger.unit_conv_factors = unit_conv_factors
            except ValueError:
                msg = key + " each unit conversion factor must be a number"
                raise InputError(msg)

        # Get interval to process stats over
        key = "*STATS_INTERVAL"
        i, stats_int_str = self.get_key_data(key, data)
        if i == -1:
            msg = key + " data not found for " + logger.logger_id
            raise InputError(msg)

        logger.stats_interval = self.get_float_key_data(key, stats_int_str)

        # Get start date if specified
        # TODO: Once have start and end dates should create list of expected filenames sequence to check missing files
        key = "*STATS_START"
        i, process_start_str = self.get_key_data(key, data)
        if i != -1:
            try:
                logger.process_start = parse(process_start_str, yearfirst=True)
            except ValueError:
                msg = key + " format not recognised for " + logger.logger_id
                raise InputError(msg)

        # Get end date if specified
        key = "*STATS_END"
        i, process_end_str = self.get_key_data(key, data)
        if i != -1:
            try:
                logger.process_end = parse(process_end_str, yearfirst=True)
            except ValueError:
                msg = key + " format not recognised for " + logger.logger_id
                raise InputError(msg)

    def copy_stats_format(self, key, ref_logger_name, logger):
        """
        Copy parameters data for the following stats commands from ref logger to new logger:
            *STATS_COLUMNS
            *STATS_UNIT_CONV_FACTORS
            *STATS_INTERVAL
            *STATS_START
            *STATS_END
        """

        # Get list index of logger to copy
        ref_logger_idx = self.logger_index(ref_logger_name, self.logger_ids_upper)

        # Check reference logger appears before logger being copied
        if ref_logger_idx >= self.logger_ids.index(logger.logger_id):
            msg = "Logger id in " + key + " not found"
            raise InputError(msg)

        # Attributes to copy
        names = [
            "cols_to_process",
            "unit_conv_factors",
            "stats_interval",
            "process_start",
            "process_end",
        ]

        # Copy attributes from reference logger
        ref_logger = self.loggers[ref_logger_idx]
        self.copy_logger_attributes(ref_logger, logger, names)

    def logger_index(self, logger_name, logger_ids_upper):
        """
        Get index of logger from its name.
        Return logger index.
        """

        name_upper = logger_name.upper()
        if name_upper in logger_ids_upper:
            index = logger_ids_upper.index(name_upper)
        else:
            index = -1

        return index

    def get_key_data(self, key, data):
        """Extract data specified by keywords in control file."""

        # Loop through list and find key
        for line, text in enumerate(data):
            # Case insensitive
            text_upper = text.upper().strip()
            if text_upper.startswith(key.upper()):
                # Return the rest of the line and row number if found
                key_data = text[len(key) :].strip()
                return line, key_data

        # Return empty string and negative row number if not found
        return -1, ""

    def get_integer_key_data(self, key, num_str):
        """Extract positive integer from control file data."""

        msg = key + " data must be a positive integer"

        # Check for numeric input
        num_str = num_str.strip()
        try:
            i = int(num_str)
        except ValueError:
            raise InputError(msg)
        if i <= 0:
            raise InputError(msg)

        return i

    def get_float_key_data(self, key, num_str):
        """Extract positive float from control file data."""

        msg = key + " data must be a positive number"

        # Check for numeric input
        num_str = num_str.strip()
        try:
            f = float(num_str)
        except ValueError:
            raise InputError(msg)
        if f <= 0:
            raise InputError(msg)

        return f

    def set_data(self, data):
        """Set internal data structure. Used in unit tests."""

        self.data = data
