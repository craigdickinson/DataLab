"""Routines to create dataset of time series files to plot in Inspect Raw Data dashboard."""

__author__ = "Craig Dickinson"

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from logger_properties import LoggerProperties
from read_files import read_2hps2_acc, read_fugro_csv, read_pulse_acc


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

    def read_file(self, file):
        """Read time series file into data frame using logger file format settings."""

        # Read data to data frame
        if self.file_format == "Custom":
            df = pd.read_csv(
                file,
                sep=self.delim,
                header=self.header_rows,
                skiprows=self.skip_rows,
                skip_blank_lines=False,
            )
            # Ensure column names are strings and remove any nan columns (can arise from superfluous delimiters)
            df.columns = df.columns.astype(str)
            df = df.dropna(axis=1)

            # TODO: Need to process if column 1 is timestamps
        elif self.file_format == "Fugro-csv":
            df = read_fugro_csv(file)
        elif self.file_format == "Pulse-acc":
            df = read_pulse_acc(file, multi_header=True)
        elif self.file_format == "2HPS2-acc":
            df = read_2hps2_acc(file, multi_header=True)
        else:
            df = pd.DataFrame()

        return df


class RawDataPlotProperties(object):
    """Contains general plot properties for the raw data dashboard."""

    def __init__(self):
        # Create 4 potential axis 1 and axis 2 plot series
        self.max_num_series = 4
        self.axis1_series_list = [SeriesPlotData() for _ in range(self.max_num_series)]
        self.axis2_series_list = [SeriesPlotData() for _ in range(self.max_num_series)]

        # Assign axis and series numbers (more for developer reference to help identify a series)
        for i, srs in enumerate(self.axis1_series_list):
            srs.axis = 1
            srs.series = i + 1

        for i, srs in enumerate(self.axis2_series_list):
            srs.axis = 2
            srs.series = i + 1

        # Plot style
        plt.style.use("seaborn")

        # Assign plot colours for each series
        # Use paired colour palette, selecting the even/odd item of each pairing
        # colors1 = [c for i, c in enumerate(sns.color_palette("Paired").as_hex()) if i % 2 == 0]
        # colors1_filt = [c for i, c in enumerate(sns.color_palette("Paired").as_hex()) if i % 2 == 1]
        # colors2 = [c for i, c in enumerate(sns.color_palette("Paired").as_hex()) if i % 2 == 0]
        # colors_filt = [c for i, c in enumerate(sns.color_palette("Paired").as_hex()) if i % 2 == 1]

        colors1_idx = [0, 1, 2, 3]
        colors1 = [sns.color_palette("muted").as_hex()[i] for i in colors1_idx]
        colors1_filt = [sns.color_palette("dark").as_hex()[i] for i in colors1_idx]

        colors2_idx = [8, 9, 4, 7]
        colors2 = [sns.color_palette("colorblind").as_hex()[i] for i in colors2_idx]
        colors2_filt = [sns.color_palette("dark").as_hex()[i] for i in colors2_idx]

        # print(plt.rcParams['axes.prop_cycle'].by_key()['color'])

        for i, srs in enumerate(self.axis1_series_list):
            srs.color = colors1[i]
            srs.color_filt = colors1_filt[i]

        for i, srs in enumerate(self.axis2_series_list):
            srs.color = colors2[i]
            srs.color_filt = colors2_filt[i]

        self.project_name = "Project Title"
        self.df_file = pd.DataFrame()

        self.axis1_is_plotted = False
        self.axis2_is_plotted = False
        self.plot_period = False
        self.log_scale = False
        self.psd_params_type = "default"
        self.set_init_axis_limits = True

        # PSD parameters
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
        self.def_low_cutoff = None
        self.def_high_cutoff = None
        self.plot_filt_only = False

        # Legend options
        self.filename_in_legend = True
        self.dataset_in_legend = True
        self.column_in_legend = True

    def reset(self):
        self.__init__()


class SeriesPlotData(object):
    """Contains plot data and setting pertaining to a single plot series of the raw data dashboard."""

    def __init__(self):
        self.axis = 1
        self.series = 1
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

        # Plot data
        self.x = []
        self.y = []
        self.y_filt = []
        self.freq = []
        self.pxx = []
        self.pxx_filt = []
        self.label = ""

        # Line plot handles
        self.ts_line = None
        self.ts_line_filt = None
        self.psd_line = None
        self.psd_line_filt = None

        # Filters
        self.low_cutoff = None
        self.high_cutoff = None

        # Axes limits
        # Initial axis limits upon loading a file
        self.init_xlim = (0.0, 1.0)

        # Current axis limits
        self.ts_xlim = (0.0, 1.0)
        self.psd_xlim = (0.0, 1.0)

        # Plot parameters
        self.color = "b"
        self.color_filt = "r"
        self.linewidth = None

    def reset_series(self):
        """Reset series properties pertaining to plot selection and data."""

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
        self.freq = []
        self.pxx = []
        self.pxx_filt = []
        self.label = ""
        self.ts_line = None
        self.ts_line_filt = None
        self.psd_line = None
        self.psd_line_filt = None
        self.low_cutoff = None
        self.high_cutoff = None

    def set_series_data(self, df):
        """Store plot series data."""

        self.x = df.index.values
        self.y = df[self.column].values.ravel()
        self.units = self.channel_units[self.column_i]
        self.timestamps = df.iloc[:, 0].values
