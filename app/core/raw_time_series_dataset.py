"""Routines to create dataset of time series files to plot in Inspect Raw Data dashboard."""

__author__ = "Craig Dickinson"

import pandas as pd

from logger_properties import LoggerProperties
from read_files import read_fugro_csv, read_pulse_acc, read_2hps2_acc


class RawDataRead(object):
    def __init__(self, logger=LoggerProperties()):
        """
        Set the logger filenames to be assessed and required read file properties.
        :param logger: LoggerProperties instance
        """

        self.logger_id = ""
        self.path_to_files = ""
        self.filenames = []

        # File read properties
        self.file_format = ""
        self.delim = ""
        self.header_rows = 0
        self.skip_rows = []
        self.channel_names = []
        self.channel_units = []

        # Initialise with current logger settings
        self.set_logger(logger)

    def set_logger(self, logger):
        """Set the logger filenames and required read file properties."""

        self.logger_id = logger.logger_id
        self.path_to_files = logger.logger_path
        self.filenames = logger.raw_filenames
        self.channel_names = logger.all_channel_names
        self.channel_units = logger.all_channel_units

        # Set file read properties
        self.file_format = logger.file_format
        self.delim = logger.file_delimiter
        header_row = logger.channel_header_row - 1
        units_row = logger.units_header_row - 1

        # Additional header rows to skip - only using the first header row for data frame column names
        self.skip_rows = [
            i for i in range(logger.num_headers) if i > header_row and i != units_row
        ]

        # No header row specified
        if header_row < 0:
            self.header_rows = None
        elif units_row < 0:
            self.header_rows = header_row
        else:
            self.header_rows = [header_row, units_row]

    def read_file(self, filepath):
        """Read time series file into data frame using logger file format settings."""

        df = pd.DataFrame()

        # Read data to data frame
        if self.file_format == "General-csv":
            df = pd.read_csv(
                filepath,
                sep=self.delim,
                header=self.header_rows,
                skiprows=self.skip_rows,
            )
            df = df.dropna(axis=1)
        elif self.file_format == "Fugro-csv":
            df = read_fugro_csv(filepath)
            # df = pd.read_csv(
            #     filename,
            #     sep=self.delim,
            #     header=self.header_rows,
            #     skiprows=self.skip_rows,
            #     encoding="latin1",
            # )
        elif self.file_format == "Pulse-acc":
            df = read_pulse_acc(filepath, multi_header=True)
        elif self.file_format == "2HPS2-acc":
            df = read_2hps2_acc(filepath, multi_header=True)

        return df


class RawDataPlotSettings(object):
    def __init__(self):
        # Create 4 potential axis 1 and axis 2 plot series
        self.max_num_series = 4
        self.axis1_series_list = [SeriesPlotData() for _ in range(self.max_num_series)]
        self.axis2_series_list = [SeriesPlotData() for _ in range(self.max_num_series)]

        self.project = "Project Title"
        self.logger_id = ""
        self.df_file = pd.DataFrame()

        self.axis1_is_plotted = False
        self.axis2_is_plotted = False
        self.plot_period = False
        self.log_scale = False
        self.psd_params_type = "default"
        self.set_init_axis_limits = True

        # Default PSD parameters
        self.def_num_ensembles = 1
        self.def_window = "None"
        self.def_overlap = 0
        self.def_nperseg = 256

        # Default Welch PSD parameters
        self.welch_num_ensembles = 46.875
        self.welch_window = "Hann"
        self.welch_overlap = 50
        self.welch_nperseg = 256

        # Custom Welch PSD parameters
        self.cust_num_ensembles = 1
        self.cust_window = "None"
        self.cust_overlap = 0
        self.cust_nperseg = 256

        # Initialise with default PSD parameters (i.e. basic PSD)
        self.num_ensembles = self.def_num_ensembles
        self.window = self.def_window
        self.overlap = self.def_overlap
        self.fs = 10

        # Initial axis limits upon loading a file
        self.init_xlim = (0.0, 1.0)

        # Current axis limits
        self.ts_xlim = (0.0, 1.0)
        self.ts_ylim = (0.0, 1.0)
        self.psd_xlim = (0.0, 1.0)
        self.psd_ylim = (0.0, 1.0)

        # Low and high frequency cut-offs
        self.apply_low_cutoff = False
        self.apply_high_cutoff = False
        self.low_cutoff = 0.05
        self.high_cutoff = 0.5

        # To hold file data
        self.df = pd.DataFrame()
        self.df_filtered = pd.DataFrame()
        self.df_plot = pd.DataFrame()
        self.plot_units = []

    def reset_series_lists(self):
        self.axis1_series_list = [SeriesPlotData() for _ in range(self.max_num_series)]
        self.axis2_series_list = [SeriesPlotData() for _ in range(self.max_num_series)]


class SeriesPlotData(object):
    def __init__(self):
        self.dataset_i = 0
        self.dataset = "None"
        self.path_to_files = ""
        self.file_i = 0
        self.file = "-"
        self.column_i = 0
        self.column = "-"
        self.units = ""
        self.filenames = []
        self.channel_names = []
        self.channel_units = []
        self.timestamps = []
        self.x = []
        self.y = []
        self.y_filt = []

    def reset_series(self):
        self.dataset_i = 0
        self.dataset = "None"
        self.path_to_files = ""
        self.file_i = 0
        self.file = "-"
        self.column_i = 0
        self.column = "-"
        self.units = ""
        self.filenames = []
        self.channel_names = []
        self.channel_units = []
        self.timestamps = []
        self.x = []
        self.y = []
        self.y_filt = []

    def set_series_data(self, df):
        """Store plot series data."""

        self.x = df.index.values
        self.y = df[self.column].values.ravel()
        self.units = self.channel_units[self.column_i]
        self.timestamps = df.iloc[:, 0].values
