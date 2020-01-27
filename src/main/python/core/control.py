"""Class to set up project control."""

__author__ = "Craig Dickinson"

import os.path


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

        # Config json filename
        self.config_file = ""

        # Project and campaign details
        self.project_num = ""
        self.project_name = ""
        self.campaign_name = ""
        self.project_path = ""

        # Global screening flags
        self.global_process_stats = True
        self.global_process_spect = True
        self.global_process_histograms = True

        # Azure account settings
        self.azure_account_name = ""
        self.azure_account_key = ""

        # Output folders
        self.report_output_folder = "Screening Report"
        self.stats_output_folder = "Statistics"
        self.spect_output_folder = "Spectrograms"
        self.hist_output_folder = "Histograms"
        self.integration_output_folder = "Displacements and Angles"

        # Output paths
        self.report_output_path = ""
        self.stats_output_path = ""
        self.spect_output_path = ""
        self.hist_output_path = ""
        self.integration_output_path = ""

        # Selected stats output file formats
        self.stats_to_csv = True
        self.stats_to_xlsx = False
        self.stats_to_h5 = False

        # Selected spectral output file formats
        self.spect_to_csv = True
        self.spect_to_xlsx = False
        self.spect_to_h5 = False

        # Selected histogram output file formats
        self.hist_to_csv = True
        self.hist_to_xlsx = False
        self.hist_to_h5 = False

        # List to store lines with *LOGGER_ID
        self.logger_id_lines = []

        # List of logger ids
        self.logger_ids = []
        self.logger_ids_upper = []

        # List of logger objects from LoggerProperties class
        # Each logger object will contain the majority of the setup information
        self.loggers = []

        # Flag to indicate type of processing worker to run
        self.processing_mode = "screening"

    def set_output_paths(self):
        """Construct file paths for output folders and create folders if required."""

        path = self.project_path
        self.report_output_path = os.path.join(path, self.report_output_folder)
        self.stats_output_path = os.path.join(path, self.stats_output_folder)
        self.spect_output_path = os.path.join(path, self.spect_output_folder)
        self.hist_output_path = os.path.join(path, self.hist_output_folder)
        self.integration_output_path = os.path.join(path, self.integration_output_folder)

    def check_logger_ids(self):
        """Check for duplicate logger names."""

        if len(self.logger_ids) != len(set(self.logger_ids)):
            msg = "Duplicate logger ids detected."
            raise InputError(msg)

    def copy_logger_properties(self, ref_logger_id, dest_logger):
        """Copy another logger's file format properties."""

        # Attributes to copy
        names = [
            "file_format",
            "file_timestamp_embedded",
            "first_col_data",
            "file_ext",
            "file_delimiter",
            "num_headers",
            "channel_header_row",
            "units_header_row",
            "timestamp_format",
            "num_columns",
            "freq",
            "duration",
        ]

        # Get reference logger to copy
        logger_idx = self.logger_ids.index(ref_logger_id)
        ref_logger = self.loggers[logger_idx]

        # Copy attributes from reference logger
        self.copy_attributes(obj_from=ref_logger, obj_to=dest_logger, attribute_names=names)

    def copy_logger_screening_settings(self, ref_logger_id, dest_logger):
        """Copy anotehr logger's screening settings."""

        # Attributes to copy
        names = [
            "cols_to_process",
            "unit_conv_factors",
            "user_channel_names",
            "user_channel_units",
            "process_start",
            "process_end",
            "low_cutoff_freq",
            "high_cutoff_freq",
            "stats_interval",
            "spectInterval",
            "psd_nperseg",
            "psd_window",
            "psd_overlap",
        ]

        # Get reference logger to copy
        logger_idx = self.logger_ids.index(ref_logger_id)
        ref_logger = self.loggers[logger_idx]

        # Copy attributes from reference logger
        self.copy_attributes(ref_logger, dest_logger, names)

    def copy_logger_integration_settings(self, ref_logger_id, dest_logger):
        """Copy another logger's time series integration settings (acc to disp and angular rate to angle)."""

        # Attributes to copy
        names = [
            "acc_x_col",
            "acc_y_col",
            "acc_z_col",
            "ang_rate_x_col",
            "ang_rate_y_col",
            "ang_rate_z_col",
            "apply_gcorr",
        ]

        # Get reference logger to copy
        logger_idx = self.logger_ids.index(ref_logger_id)
        ref_logger = self.loggers[logger_idx]

        # Copy attributes from reference logger
        self.copy_attributes(ref_logger, dest_logger, names)

    @staticmethod
    def copy_attributes(obj_from, obj_to, attribute_names):
        """Function to copy attributes from one object to another."""

        for n in attribute_names:
            try:
                param = getattr(obj_from, n)
                setattr(obj_to, n, param)
            except AttributeError:
                pass
