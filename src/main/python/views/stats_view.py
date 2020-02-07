"""Statistics screening dashboard gui view."""

__author__ = "Craig Dickinson"

import sys
import logging

import PIL
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoLocator, AutoMinorLocator, MultipleLocator, MaxNLocator

import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

# To resolve a pandas warning in using timestamps with matplotlib - to investigate
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()

# from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap
# from matplotlib.patches import Rectangle
# from matplotlib.font_manager import findfont, FontProperties
# import colormap as cmaps

stat_ylabels = ["Acceleration ($\mathregular{m/s^2}$)", "Angular Rate ($\mathregular{deg/s}$)"]

variance_channels_combo = ["Acceleration X", "Acceleration Y", "Angular Rate X", "Angular Rate Y"]

motion_types = ["Surge/Sway/Heave", "Roll/Pitch/Yaw"]
vessel_trans = ["Surge", "Sway", "Heave"]
vessel_rots = ["Roll", "Pitch", "Yaw"]
# vessel_trans = ["AccSurge", "AccSway", "AccHeave"]
# vessel_rots = ["AccRoll", "AccPitch", "AccYaw"]

# Dictionary of stats combo items and stats file column name pairs
dict_stats = {
    "Minimum": "min",
    "Maximum": "max",
    "Mean": "mean",
    "Std. Dev.": "std",
    "Combined": "combined",
}

dict_stats_abbrev = {"Minimum": "Min", "Maximum": "Max", "Std. Dev.": "Std. Dev."}

dict_labels = {"SigWaveHeight": "Sig. Wave Height", "SigWavePeriod": "Sig. Wave Period"}

dict_ylabels = {"SigWaveHeight": "Hs", "SigWavePeriod": "Tp"}

# 2H blue colour font
color_2H = np.array([0, 49, 80]) / 255

# Title style args
title_args = dict(size=14, fontname="tahoma", color=color_2H, weight="bold")


# plt.style.use('seaborn')


# plt.style.use('default')


class StatsDataset:
    """Class to hold stats datasets and associated properties."""

    def __init__(self, logger_id="", df=pd.DataFrame()):
        try:
            # Get unique channels list and filter out blanks
            self.channels = [c for c in df.columns.unique(level="channels") if c != ""]
        except:
            self.channels = ["N/A"]

        # If timestamp index exists create a time steps column, otherwise set flag that file number index is used
        if isinstance(df.index[0], pd.Timestamp):
            df = self._add_time_steps_column(df)
            self.index_type = "Timestamp"
        else:
            self.index_type = "File Number"

        self.logger_id = logger_id
        self.df = df

    @staticmethod
    def _add_time_steps_column(df):
        """Calculate time delta from t0 and convert to seconds (float)."""

        t = (df.index - df.index[0]).total_seconds().values.round(3)
        df.insert(loc=0, column="Time (s)", value=t)

        return df


class AxesPlotData:
    def __init__(self):
        """
        Class to hold plot data for primary and secondary axes of a subplot
        and to plot to a given axes.
        """

        # Primary axes combo selections
        self.logger_1 = "-"
        self.channel_1 = "-"
        self.stat_1 = "Std. Dev."

        # Primary axes plot data
        self.ax1 = None
        self.handles_1 = []
        self.df_1 = pd.DataFrame()
        self.time_index_1 = np.array([])
        self.label_1 = ""
        self.units_1 = ""
        self.color_1 = "dodgerblue"

        # Secondary axes combo selections
        self.logger_2 = "-"
        self.channel_2 = "-"
        self.stat_2 = "Std. Dev."

        # Secondary axes plot data
        self.ax2 = None
        self.handles_2 = []
        self.df_2 = pd.DataFrame()
        self.time_index_2 = np.array([])
        self.label_2 = ""
        self.units_2 = ""
        self.color_2 = "orange"

        # Flags to identify if axes are plotted
        self.ax1_in_use = False
        self.ax2_in_use = False

    def set_axes_plot_data(self, axis, datasets, logger_i, channel_name, stat):
        """"""

        # Initialise plot data
        df = pd.DataFrame()
        t = np.array([])
        label = ""
        units = ""

        # Logger index and default id
        i = logger_i - 1
        logger_id = "-"

        if i > -1 and channel_name != "-":
            # Retrieve logger id and set as proper case
            logger_id = datasets[i].logger_id

            # Format logger name for legend label
            # logger_label = self._get_preferred_logger_label(logger_id)
            logger_label = logger_id

            # Retrieve logger stats data
            df = datasets[i].df

            # Column name in stats dataset
            # TODO: Handle KeyError (McDermott: Std -> Slope)
            stat_col = dict_stats[stat]

            # Check for preferred stat label for legend
            if stat in dict_stats_abbrev:
                stat_label = dict_stats_abbrev[stat]
            else:
                stat_label = stat

            # Store time steps column as potential plot x-axis index - convert from seconds to days
            if "Time (s)" in df.columns:
                t = df["Time (s)"].values / 86400

            # Slice dataframe for the selected statistic and then on channel
            if stat == "Combined":
                df = df[channel_name]
                units = df.columns[0][1]
                label = " ".join((logger_label, channel_name))
            else:
                df = df.xs(key=channel_name, axis=1, level=0)
                df = df[stat_col]
                units = df.columns[0]
                label = " ".join((stat_label, logger_label, channel_name))

        # Store plot data and combo selections
        if axis == 0:
            self.df_1 = df
            self.time_index_1 = t
            self.label_1 = label
            self.units_1 = units
            self.logger_1 = logger_id
            self.channel_1 = channel_name
            self.stat_1 = stat
        else:
            self.df_2 = df
            self.time_index_2 = t
            self.label_2 = label
            self.units_2 = units
            self.logger_2 = logger_id
            self.channel_2 = channel_name
            self.stat_2 = stat

    def plot_data(self, stat, axis, num_plots, index_type):
        """Plot channel statistic(s) on selected subplot axes (i.e. primary or secondary)."""

        if axis == 0:
            ax = self.ax1
            df = self.df_1
            t = self.time_index_1
            channel = self.channel_1
            label = self.label_1
            units = self.units_1
            color = self.color_1
            color2 = "red"
        else:
            ax = self.ax2
            df = self.df_2
            t = self.time_index_2
            channel = self.channel_2
            label = self.label_2
            units = self.units_2
            color = self.color_2
            color2 = "green"

        # Determine x-axis values to use: time steps or dataframe index (timestamps or file numbers)
        if index_type != "Time Step":
            t = df.index.values

        if index_type == "File Number":
            linestyle = "None"
            marker = "o"
        else:
            linestyle = "-"
            marker = ""

        # Construct y-axis label
        ylabel, ylabel_size = self._create_ylabel(channel, units, num_plots)
        ax.cla()
        handles = []
        ax_in_use = False

        if not df.empty:
            # Plot all stats on selected axes
            if stat == "Combined":
                mn = df["min"].values.flatten()
                mx = df["max"].values.flatten()
                ave = df["mean"].values.flatten()
                std = df["std"].values.flatten()

                label_1 = f"Mean {label}"
                label_2 = f"Range {label}"
                label_3 = f"Std. Dev. {label}"

                # Plot mean, range and SD range
                line1 = ax.plot(
                    t, ave, label=label_1, color=color, ls=linestyle, lw=1, marker=marker
                )
                line2 = ax.fill_between(t, mn, mx, label=label_2, facecolor=color, alpha=0.2)
                line3 = ax.fill_between(
                    t, ave - std, ave + std, label=label_3, facecolor=color2, alpha=0.2
                )

                # Select first list item for line1 because line plots are returned as a list
                handles = [line1[0], line2, line3]
            # Plot a single channel stat on selected axes
            else:
                y = df.values.flatten()
                line = ax.plot(t, y, label=label, color=color, ls=linestyle, lw=1, marker=marker)
                handles.append(line[0])

            ax.set_ylabel(ylabel, size=ylabel_size)
            ax.margins(0)
            ax_in_use = True

            if axis == 0:
                ax.legend(loc="upper left")
            else:
                ax.legend(loc="upper right")

        # Store handles and plot status flag
        if axis == 0:
            self.ax1_in_use = ax_in_use
            self.handles_1 = handles
        else:
            self.ax2_in_use = ax_in_use
            self.handles_2 = handles

    @staticmethod
    def _create_ylabel(channel, units, num_plots):
        # Check for a preferred channel name to use
        if channel in dict_ylabels:
            channel = dict_ylabels[channel]

        # Set y-axis font size depending on number of plots
        if num_plots > 2:
            ylabel = f"{channel}\n($\mathregular{{{units}}}$)"
            ylabel_size = 10
        else:
            ylabel = f"{channel} ($\mathregular{{{units}}}$)"
            ylabel_size = 11

        return ylabel, ylabel_size

    @staticmethod
    def _get_preferred_logger_label(logger_id):
        """Return logger label in proper case unless meets the given exceptions."""

        if logger_id == "BOP" or logger_id == "LMRP" or logger_id[:2].lower() == "dd":
            return logger_id
        else:
            return logger_id.title()


class StatsWidget(QtWidgets.QWidget):
    """Summary stats plot widget class."""

    # List of plot colours for each subplot (limited to 4 plots)
    ax1_colors = ["dodgerblue", "red", "blue", "green"]
    ax2_colors = ["deepskyblue", "orange", "yellow", "purple"]

    def __init__(self, parent=None):
        super(StatsWidget, self).__init__(parent)

        # So can access parent class
        self.parent = parent

        self.plot_capacity = 4
        self.num_plots = 1

        # Combo box selection indexes
        self.plot_i = 0
        self.axis_i = 0
        self.logger_i = 0
        self.channel_i = 0

        # Combo box selection text
        self.logger_id = ""
        self.channel_name = ""
        self.stat = ""

        # Container to hold plot data for each subplot
        self.subplots = [AxesPlotData()]

        # Container for StatsDataset objects
        self.datasets = []
        self.ylabel = stat_ylabels[0]

        # Flags to prevent unwanted plotting during combo boxes updates
        self.skip_plotting = False
        self.removing_channel_items = False
        self.resetting_dashboard = False
        self.presets_set = False
        self.skip_on_xaxis_type_changed = False

        # X-axis datetime interval settings
        self.date_locator = "days"
        self.date_fmt = "%Y-%b-%d"
        self.day_interval = 7
        self.hour_interval = 12

        # X-axis values type
        self.xaxis_type = "Timestamp"

        # Stats dataframe index type of current plot "session" (either Timestamp of File Number)
        # Purpose is to prevent mix and match of plotted indexes - which wouldn't make sense
        self.df_index_type = ""

        # Shared axes flags
        self.equal_pri_sec_yaxis = False
        self.share_subplot_yaxes1 = False
        self.share_subplot_yaxes2 = False

        # Set layout and initialise combo boxes and create plot figure
        self._init_ui()
        self._init_combos()
        self._connect_signals()
        self._create_subplots()
        self.fig.tight_layout()
        self.canvas.draw()

    def _init_ui(self):
        # WIDGETS
        # Buttons and datasets and channels lists
        self.openStatsButton = QtWidgets.QPushButton("Open Statistics...")
        self.openStatsButton.setToolTip("Open logger stats (*.h5;*.csv;*.xlsx) (F3)")
        self.clearDatasetsButton = QtWidgets.QPushButton("Clear Datasets")
        self.datasetList = QtWidgets.QListWidget()
        self.channelsLabel = QtWidgets.QLabel("Available Channels")
        self.channelList = QtWidgets.QListWidget()
        self.settingsButton = QtWidgets.QPushButton("Plot Settings...")

        # Number of plots
        self.numPlotsCombo = QtWidgets.QComboBox()
        self.numPlotsCombo.setFixedWidth(40)

        # Plot selection
        self.plotNumCombo = QtWidgets.QComboBox()
        self.plotNumCombo.setFixedWidth(40)
        self.axisCombo = QtWidgets.QComboBox()
        self.axisCombo.setFixedWidth(80)
        self.loggerCombo = QtWidgets.QComboBox()
        self.channelCombo = QtWidgets.QComboBox()
        self.statCombo = QtWidgets.QComboBox()
        self.statCombo.setFixedWidth(80)

        # X axis datetime interval options
        self.xaxisIntervalsCombo = QtWidgets.QComboBox()
        self.xaxisTypeCombo = QtWidgets.QComboBox()

        # Check box to set whether pri and sec y-axis limits should be equal or not
        self.equalPriSecYAxisChkBox = QtWidgets.QCheckBox("Equal pri-sec y-axis limits")
        self.equalPriSecYAxisChkBox.setChecked(False)

        # Check boxes to set whether pri/sec y-axes are shared both across subplots
        self.shareSubplotYAxes1ChkBox = QtWidgets.QCheckBox("Shared subplot pri y-axis")
        self.shareSubplotYAxes1ChkBox.setChecked(False)
        self.shareSubplotYAxes2ChkBox = QtWidgets.QCheckBox("Shared subplot sec y-axis")
        self.shareSubplotYAxes2ChkBox.setChecked(False)

        # Plot figure, canvas and navbar
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # CONTAINERS
        # Number of plots
        self.numPlotsForm = QtWidgets.QFormLayout()
        self.numPlotsForm.addRow(QtWidgets.QLabel("Number of plots:"), self.numPlotsCombo)

        # Plot selection group
        self.plotGroup = QtWidgets.QGroupBox("Select Plot Data")
        self.form = QtWidgets.QFormLayout(self.plotGroup)
        self.form.addRow(QtWidgets.QLabel("Plot:"), self.plotNumCombo)
        self.form.addRow(QtWidgets.QLabel("Axis:"), self.axisCombo)
        self.form.addRow(QtWidgets.QLabel("Logger:"), self.loggerCombo)
        self.form.addRow(QtWidgets.QLabel("Channel:"), self.channelCombo)
        self.form.addRow(QtWidgets.QLabel("Stat:"), self.statCombo)

        # Plot settings group
        self.plotSettingsGroup = QtWidgets.QGroupBox("Plot Settings")
        self.form2 = QtWidgets.QFormLayout()
        self.form2.addRow(QtWidgets.QLabel("X-axis type:"), self.xaxisTypeCombo)
        self.form2.addRow(QtWidgets.QLabel("X-axis interval:"), self.xaxisIntervalsCombo)
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.equalPriSecYAxisChkBox)
        self.vbox.addWidget(self.shareSubplotYAxes1ChkBox)
        self.vbox.addWidget(self.shareSubplotYAxes2ChkBox)
        # self.vbox.addWidget(self.settingsButton)
        self.vboxSettings = QtWidgets.QVBoxLayout(self.plotSettingsGroup)
        self.vboxSettings.addLayout(self.form2)
        self.vboxSettings.addLayout(self.vbox)

        # Selection container
        self.selectionContainer = QtWidgets.QWidget()
        self.selectionContainer.setMinimumWidth(200)
        # self.selectionContainer.resize(200, 847)
        self.vboxSel = QtWidgets.QVBoxLayout(self.selectionContainer)
        self.vboxSel.addWidget(self.openStatsButton)
        self.vboxSel.addWidget(self.clearDatasetsButton)
        self.vboxSel.addWidget(QtWidgets.QLabel("Loaded Datasets"))
        self.vboxSel.addWidget(self.datasetList)
        self.vboxSel.addWidget(self.channelsLabel)
        self.vboxSel.addWidget(self.channelList)
        self.vboxSel.addLayout(self.numPlotsForm)
        self.vboxSel.addWidget(self.plotGroup)
        self.vboxSel.addWidget(self.plotSettingsGroup)

        # Plot figure
        self.plotWidget = QtWidgets.QWidget()
        self.plotLayout = QtWidgets.QVBoxLayout(self.plotWidget)
        self.plotLayout.addWidget(navbar)
        self.plotLayout.addWidget(self.canvas)

        # Splitter to allow resizing of widget containers
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.selectionContainer)
        splitter.addWidget(self.plotWidget)
        splitter.setSizes([200, 10000])

        # LAYOUT
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(splitter)

    def _init_combos(self):
        """Populate combo boxes and store initial selections."""

        plot_capacity = self._get_plot_numbers_list(self.plot_capacity)
        self.numPlotsCombo.addItems(plot_capacity)
        plot_nums = self._get_plot_numbers_list(self.num_plots)
        self.plotNumCombo.addItems(plot_nums)
        self.axisCombo.addItems(["Primary", "Secondary"])
        self.statCombo.addItems(dict_stats.keys())
        self.statCombo.setCurrentIndex(3)
        self.stat = self.statCombo.currentText()
        self.loggerCombo.addItem("-")
        self.channelCombo.addItem("-")
        self.xaxisTypeCombo.addItems(["Timestamp", "Time Step"])
        date_intervals = ["14 days", "7 days", "1 day", "12 hours"]
        self.xaxisIntervalsCombo.addItems(date_intervals)
        self.xaxisIntervalsCombo.setCurrentIndex(1)

    def _connect_signals(self):
        self.clearDatasetsButton.clicked.connect(self.on_clear_datasets_clicked)
        self.datasetList.currentItemChanged.connect(self.on_dataset_list_item_changed)
        self.numPlotsCombo.currentIndexChanged.connect(self.on_num_plots_combo_changed)
        self.plotNumCombo.currentIndexChanged.connect(self.on_plot_num_combo_changed)
        self.axisCombo.currentIndexChanged.connect(self.on_axis_combo_changed)
        self.loggerCombo.currentIndexChanged.connect(self.on_logger_combo_changed)
        self.channelCombo.currentIndexChanged.connect(self.on_channel_combo_changed)
        self.statCombo.currentIndexChanged.connect(self.on_stat_combo_changed)
        self.xaxisTypeCombo.currentIndexChanged.connect(self.on_xaxis_type_changed)
        self.xaxisIntervalsCombo.currentIndexChanged.connect(self.on_xaxis_interval_changed)
        self.equalPriSecYAxisChkBox.toggled.connect(self.on_equal_pri_sec_yaxis_toggled)
        self.shareSubplotYAxes1ChkBox.toggled.connect(self.on_share_subplot_yaxes1_toggled)
        self.shareSubplotYAxes2ChkBox.toggled.connect(self.on_share_subplot_yaxes2_toggled)

    @staticmethod
    def _get_plot_numbers_list(n):
        return [str(i) for i in range(1, n + 1)]

    def on_clear_datasets_clicked(self):
        self.clear_dashboard()

    def on_dataset_list_item_changed(self):
        self._update_channels_list()

    def on_num_plots_combo_changed(self):
        """Actions to perform when changing number of subplots."""

        # Get current plot number index to reapply later if relevant
        curr_plot_i = self.plot_i
        self.num_plots = self.numPlotsCombo.currentIndex() + 1
        self._set_subplot_containers()
        self._update_plot_num_combo()

        # Attempt to retain previously selected plot number, otherwise select plot 1
        if curr_plot_i < self.plotNumCombo.count():
            self.plot_i = curr_plot_i
            self.plotNumCombo.setCurrentIndex(self.plot_i)
        else:
            self.plotNumCombo.setCurrentIndex(0)

        try:
            # Create new number of subplots and replot all current plot data
            self._create_subplots()
            self._plot_all_stored_data()
        except Exception as e:
            msg = "Unexpected error plotting stats"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def on_plot_num_combo_changed(self):
        self.plot_i = self.plotNumCombo.currentIndex()
        if self.plot_i == -1:
            return

        self.skip_plotting = True
        self._set_plot_selections()
        self.skip_plotting = False

    def on_axis_combo_changed(self):
        self.axis_i = self.axisCombo.currentIndex()

        self.skip_plotting = True
        self._set_plot_selections()
        self.skip_plotting = False

    def on_logger_combo_changed(self):
        self.logger_i = self.loggerCombo.currentIndex()
        self.logger_id = self.loggerCombo.currentText()

        if self.resetting_dashboard is True:
            return

        try:
            self._update_channel_combo()

            # Clear plot axes if no channel selected
            if self.channel_name == "-":
                self.update_plot()
        except Exception as e:
            msg = "Unexpected error plotting stats"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def on_channel_combo_changed(self):
        self.channel_i = self.channelCombo.currentIndex()
        self.channel_name = self.channelCombo.currentText()

        if self.resetting_dashboard is True:
            return

        try:
            self.update_plot()
        except Exception as e:
            msg = "Unexpected error plotting stats"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def on_stat_combo_changed(self):
        """Update primary axis plots for selected statistic if datasets have been loaded"""

        # Set stat selection details
        self.stat = self.statCombo.currentText()

        if self.datasets:
            try:
                self.update_plot()
            except Exception as e:
                msg = "Unexpected error plotting stats"
                self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
                logging.exception(e)

    def on_xaxis_type_changed(self):
        """Set x-axis type: timestamps or time steps."""

        if self.skip_on_xaxis_type_changed is True:
            return

        self.xaxis_type = self.xaxisTypeCombo.currentText()

        # Disable the x-axis interval combo box if x-axis type is not set to Timestamps
        if self.xaxis_type == "Timestamp":
            self.xaxisIntervalsCombo.setEnabled(True)
        else:
            self.xaxisIntervalsCombo.setEnabled(False)

        # Update subplots stored data and replot
        for subplot in self.subplots:
            # Check data exists
            if subplot.ax1_in_use is True:
                subplot.plot_data(
                    stat=subplot.stat_1,
                    axis=0,
                    num_plots=self.num_plots,
                    index_type=self.xaxis_type,
                )

            if subplot.ax2_in_use is True:
                subplot.plot_data(
                    stat=subplot.stat_2,
                    axis=1,
                    num_plots=self.num_plots,
                    index_type=self.xaxis_type,
                )

            self._set_yaxes_and_gridlines(subplot)
            # self._add_subplot_legend(subplot, num_plots=self.num_plots)

        # Format plot
        self._set_xaxis()
        self._set_title()
        self._adjust_fig_layout()
        self.canvas.draw()

    def on_xaxis_interval_changed(self):
        """Set x-axis datetime interval."""

        date_interval = self.xaxisIntervalsCombo.currentText()

        if date_interval == "14 days":
            self.date_locator = "days"
            self.date_fmt = "%Y-%b-%d"
            self.day_interval = 14
        elif date_interval == "7 days":
            self.date_locator = "days"
            self.date_fmt = "%Y-%b-%d"
            self.day_interval = 7
        elif date_interval == "1 day":
            self.date_locator = "days"
            self.date_fmt = "%Y-%b-%d"
            self.day_interval = 1
        elif date_interval == "12 hours":
            self.date_locator = "hours"
            self.date_fmt = "%Y-%b-%d %H:%M"
            self.hour_interval = 12

        self._set_xaxis()
        self.canvas.draw()

    def on_equal_pri_sec_yaxis_toggled(self):
        if self.equalPriSecYAxisChkBox.isChecked():
            self.equal_pri_sec_yaxis = True
            self._set_equal_pri_sec_yaxes_limits()
            self.canvas.draw()
        else:
            self.equal_pri_sec_yaxis = False
            self._set_max_data_yaxes_limits()
            self.canvas.draw()

    def on_share_subplot_yaxes1_toggled(self):
        """Redraw subplots with shared or unshared primary axes and replot current data."""

        if self.shareSubplotYAxes1ChkBox.isChecked():
            self.share_subplot_yaxes1 = True
        else:
            self.share_subplot_yaxes1 = False

        try:
            # Create new number of subplots and replot all current plot data
            self._create_subplots()
            self._plot_all_stored_data()
        except Exception as e:
            msg = "Unexpected error plotting stats"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def on_share_subplot_yaxes2_toggled(self):
        """Redraw subplots with shared or unshared secondary axes and replot current data."""

        if self.shareSubplotYAxes2ChkBox.isChecked():
            self.share_subplot_yaxes2 = True
        else:
            self.share_subplot_yaxes2 = False

        try:
            # Create new number of subplots and replot all current plot data
            self._create_subplots()
            self._plot_all_stored_data()
        except Exception as e:
            msg = "Unexpected error plotting stats"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def set_xaxis_type_combo(self):
        """Set x-axis type drop-down options depending on stats dataset type."""

        self.skip_on_xaxis_type_changed = True
        i = self.xaxisTypeCombo.currentIndex()
        self.xaxisTypeCombo.clear()

        if self.df_index_type == "File Number":
            self.xaxisTypeCombo.addItem("File Number")
            self.xaxisTypeCombo.setEnabled(False)
        else:
            self.xaxisTypeCombo.addItems(["Timestamp", "Time Step"])
            self.xaxisTypeCombo.setCurrentIndex(i)
            self.xaxisTypeCombo.setEnabled(True)

        self.xaxis_type = self.xaxisTypeCombo.currentText()
        self.skip_on_xaxis_type_changed = False

    def _create_subplots(self):
        """Create figure with required number of subplots."""

        self.fig.clf()

        # Create first subplot
        ax1 = self.fig.add_subplot(self.num_plots, 1, 1)

        # Set whether primary y-axis is to be shared across subplots
        if self.share_subplot_yaxes1 is True:
            sharey_ax = ax1
        else:
            sharey_ax = None

        # Create remaining subplots list with a shared x-axis to ax1 then prepend ax1 to axes list
        pri_axes = [
            self.fig.add_subplot(self.num_plots, 1, i + 1, sharex=ax1, sharey=sharey_ax)
            for i in range(1, self.num_plots)
        ]
        pri_axes.insert(0, ax1)

        # Create secondary axes list and set properties
        sec_axes = [ax.twinx() for ax in pri_axes]
        ax0 = sec_axes[0]

        for ax in sec_axes:
            # Share secondary axes with first subplot
            if self.share_subplot_yaxes2 is True:
                if ax != ax0:
                    ax0.get_shared_x_axes().join(ax0, ax)
                    ax0.get_shared_y_axes().join(ax0, ax)

            # Initially hide secondary y-axis and gridlines
            ax.yaxis.set_visible(False)
            ax.grid(False)

        # Assign axes to subplots objects
        for i, subplot in enumerate(self.subplots):
            subplot.ax1 = pri_axes[i]
            subplot.ax2 = sec_axes[i]

            # Set plot axes colours
            # subplot.color_1 = self.ax1_colors[i]
            # subplot.color_2 = self.ax2_colors[i]

    def clear_dashboard(self):
        """Clear all stored datasets and reset layout."""

        self.resetting_dashboard = True
        self.datasets = []
        self.datasetList.clear()
        self.channelList.clear()
        self.channelsLabel.setText("Available Channels")
        self.df_index_type = ""
        self.set_xaxis_type_combo()

        # Remove all but the first item in each combo box
        [self.loggerCombo.removeItem(i) for i in range(self.loggerCombo.count(), 0, -1)]
        [self.channelCombo.removeItem(i) for i in range(self.channelCombo.count(), 0, -1)]

        self.logger_i = 0
        self.channel_i = 0
        self.subplots = [AxesPlotData() for _ in range(self.num_plots)]
        self._create_subplots()
        self.fig.tight_layout()
        self.canvas.draw()
        self.resetting_dashboard = False

    def set_preset_logger_and_channel(self):
        """When no datasets previously loaded, set drop-downs to presets to create an initial plot."""

        self.presets_set = True

        if self.loggerCombo.count() > 1:
            self.loggerCombo.setCurrentIndex(1)
        if self.channelCombo.count() > 1:
            self.channelCombo.setCurrentIndex(1)

        self.presets_set = False

    def _set_plot_selections(self):
        """Set plot drop-down selections."""

        i = self.plot_i

        if self.axis_i == 0:
            logger = self.subplots[i].logger_1
            channel = self.subplots[i].channel_1
            stat = self.subplots[i].stat_1
        else:
            logger = self.subplots[i].logger_2
            channel = self.subplots[i].channel_2
            stat = self.subplots[i].stat_2

        # Assign settings to combo boxes
        self.loggerCombo.setCurrentText(logger)
        self.channelCombo.setCurrentText(channel)
        self.statCombo.setCurrentText(stat)

    def _set_subplot_containers(self):
        """Add or remove PlotData objects from plot data list to equal number of subplots."""

        # Number of subplots
        n = self.num_plots

        # Number of current subplot data containers
        m = len(self.subplots)

        # Create required additional subplot objects
        if n > m:
            for i in range(n - m):
                self.subplots.append(AxesPlotData())
        # Delete excess subplot objects
        elif n < m:
            for i in range(m - n):
                del self.subplots[-1]

    def update_datasets_list(self, dataset_ids):
        """Populate loaded datasets list."""

        # Create dataset list and select first item (this will trigger an update of update_channels_list)
        self.datasetList.addItems(dataset_ids)
        self.datasetList.setCurrentRow(0)
        self._update_logger_combo(dataset_ids)

    def _update_channels_list(self):
        """Update channels list to match selected dataset."""

        i = self.datasetList.currentRow()
        if i == -1:
            return

        # Update channel list label
        logger_id = self.datasetList.currentItem().text()
        self.channelsLabel.setText(f"Available {logger_id} Channels")

        # Add channels to list and make non-selectable since they are just an echo for reference
        self.channelList.clear()
        for channel in self.datasets[i].channels:
            item = QtWidgets.QListWidgetItem(channel)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
            self.channelList.addItem(item)

    def _update_plot_num_combo(self):
        """Update plot number drop-down."""

        self.plotNumCombo.clear()
        plot_nums = self._get_plot_numbers_list(self.num_plots)
        self.plotNumCombo.addItems(plot_nums)

    def _update_logger_combo(self, logger_ids):
        """Add logger ids to logger combo box."""

        self.loggerCombo.addItems(logger_ids)

    def _update_channel_combo(self):
        """Repopulate channel combo box with channels that pertain to selected logger."""

        # Remove all but first item
        self.removing_channel_items = True
        [self.channelCombo.removeItem(i) for i in range(self.channelCombo.count(), 0, -1)]
        self.removing_channel_items = False

        # Don't add any channels if no logger selected;
        # otherwise retrieve channel names for selected logger and add to combo box
        i = self.logger_i - 1
        if i > -1:
            channels = self.datasets[i].channels
            self.channelCombo.addItems(channels)

    def update_plot(self):
        """Update selected subplot for selected axes (primary or secondary)."""

        if self.skip_plotting is True:
            # print('skipping')
            return
        if self.presets_set is True:
            # print('presets')
            return
        if self.removing_channel_items is True:
            # print('removing channels')
            return

        # print("Updating plot")
        i = self.plot_i
        subplot = self.subplots[i]

        # Plot on the primary axes
        if self.axis_i == 0:
            # Set plot data for selected subplot primary axes
            subplot.set_axes_plot_data(
                axis=0,
                datasets=self.datasets,
                logger_i=self.logger_i,
                channel_name=self.channel_name,
                stat=self.stat,
            )

            # Plot the data
            subplot.plot_data(
                stat=self.stat, axis=0, num_plots=self.num_plots, index_type=self.xaxis_type
            )

            # Check if no data was plotted on primary axes but the secondary axes is in use.
            # If so then need to replot the secondary axes data due to ax2 being twinned to ax1 but ax1 was cleared,
            # screwing up ax2
            if subplot.ax1_in_use is False and subplot.ax2_in_use is True:
                subplot.plot_data(
                    stat=subplot.stat_2,
                    axis=1,
                    num_plots=self.num_plots,
                    index_type=self.xaxis_type,
                )
        # Plot on the secondary axes
        else:
            # Set plot data for selected subplot secondary axes
            subplot.set_axes_plot_data(
                axis=1,
                datasets=self.datasets,
                logger_i=self.logger_i,
                channel_name=self.channel_name,
                stat=self.stat,
            )

            # Create combined stats plot
            subplot.plot_data(
                stat=self.stat, axis=1, num_plots=self.num_plots, index_type=self.xaxis_type
            )

        # Format plot
        self._set_xaxis()
        self._set_title()
        self._set_yaxes_and_gridlines(subplot)
        if self.equal_pri_sec_yaxis is True:
            self._set_equal_pri_sec_yaxes_limits()
        # self._add_subplot_legend(subplot, num_plots=self.num_plots)
        self._adjust_fig_layout()
        self.canvas.draw()

    def _plot_all_stored_data(self):
        """Plot all axes that have stored plot data."""

        data_plotted = False

        for subplot in self.subplots:
            # Check data exists
            if subplot.ax1_in_use is True:
                subplot.plot_data(
                    stat=subplot.stat_1,
                    axis=0,
                    num_plots=self.num_plots,
                    index_type=self.xaxis_type,
                )
                data_plotted = True
            if subplot.ax2_in_use is True:
                subplot.plot_data(
                    stat=subplot.stat_2,
                    axis=1,
                    num_plots=self.num_plots,
                    index_type=self.xaxis_type,
                )
                data_plotted = True

        if data_plotted is True:
            self._set_xaxis()
            self._set_title()

            for subplot in self.subplots:
                self._set_yaxes_and_gridlines(subplot)
                # self._add_subplot_legend(subplot, num_plots=self.num_plots)

            if self.equal_pri_sec_yaxis is True:
                self._set_equal_pri_sec_yaxes_limits()
            self._adjust_fig_layout()
        else:
            self.fig.tight_layout()

        self.canvas.draw()

    def _set_equal_pri_sec_yaxes_limits(self):
        """Set primary and secondary axis y-axis limits to be equal for each subplot."""
        # TODO: Some more refinement required when subplot sharing is active

        for subplot in self.subplots:
            df1 = subplot.df_1
            df2 = subplot.df_2

            # Process only if both axes contain data
            if df1.empty or df2.empty:
                continue

            # Get data limits, get global min and max and apply to both axes
            ymin1 = np.nanmin(df1.values)
            ymax1 = np.nanmax(df1.values)
            ymin2 = np.nanmin(df2.values)
            ymax2 = np.nanmax(df2.values)

            # Subplot overall min/max
            ymin = min(ymin1, ymin2)
            ymax = max(ymax1, ymax2)

            subplot.ax1.set_ylim(ymin, ymax)
            subplot.ax2.set_ylim(ymin, ymax)

    def _set_max_data_yaxes_limits(self):
        """Remove equal primary and secondary y-axis limits."""
        # TODO: Some more refinement required when subplot sharing is active

        # Check if any subplot axes is set
        if self.share_subplot_yaxes1 is True or self.share_subplot_yaxes2 is True:
            apply_global_limits = True
        else:
            apply_global_limits = False

        glob_ymin1 = np.inf
        glob_ymax1 = -np.inf
        glob_ymin2 = np.inf
        glob_ymax2 = -np.inf
        for subplot in self.subplots:
            df1 = subplot.df_1
            df2 = subplot.df_2

            if not df1.empty:
                ymin = np.nanmin(df1.values)
                ymax = np.nanmax(df1.values)

                if apply_global_limits is False:
                    subplot.ax1.set_ylim(ymin, ymax)
                else:
                    glob_ymin1 = min(glob_ymin1, ymin)
                    glob_ymax1 = max(glob_ymax1, ymax)

            if not df2.empty:
                ymin = np.nanmin(df2.values)
                ymax = np.nanmax(df2.values)

                if apply_global_limits is False:
                    subplot.ax2.set_ylim(ymin, ymax)
                else:
                    glob_ymin2 = min(glob_ymin2, ymin)
                    glob_ymax2 = max(glob_ymax2, ymax)

        # Apply global subplots min/max
        if apply_global_limits is True:
            for subplot in self.subplots:
                try:
                    subplot.ax1.set_ylim(glob_ymin1, glob_ymax1)
                    subplot.ax2.set_ylim(glob_ymin2, glob_ymax2)
                except ValueError:
                    # If glob limits happen to be +/- inf
                    pass

    def _set_title(self):
        """Set main plot title."""

        # Attempt to retrieve title from project setup dashboard
        project_name = self.parent.inputDataModule.control.project_name
        campaign_name = self.parent.inputDataModule.control.campaign_name

        if project_name == "":
            project_name = "Project Title"
        if campaign_name == "":
            campaign_name = "Campaign Title"

        title = f"{project_name} - {campaign_name}"
        self.fig.suptitle(title, **title_args)

    def _set_yaxes_and_gridlines(self, subplot):
        """Modify y-axes and gridlines shown."""

        ax1 = subplot.ax1
        ax2 = subplot.ax2

        if subplot.ax1_in_use is False and subplot.ax2_in_use is True:
            ax1.yaxis.set_visible(False)
            ax2.yaxis.set_visible(True)
            ax1.grid(False, axis="y")
            ax2.grid(True)
        elif subplot.ax1_in_use is True and subplot.ax2_in_use is True:
            ax1.yaxis.set_visible(True)
            ax2.yaxis.set_visible(True)
            ax1.grid(True)
            ax2.grid(False)
        else:
            ax1.yaxis.set_visible(True)
            ax2.yaxis.set_visible(False)
            ax1.grid(True)
            ax2.grid(False)

    def _set_xaxis(self):
        """Set x-axis format."""

        # Select bottom axes
        ax = self.subplots[-1].ax1
        # plt.rcParams['xtick.major.size'] = 3.5
        # plt.rcParams['xtick.minor.size'] = 2.0
        # ax.tick_params(which='major', length=3.5)
        # ax.tick_params(which='minor', length=2.0)
        # ax.xaxis.set_minor_locator(AutoMinorLocator())

        if self.num_plots > 2:
            xlabel_size = 10
        else:
            xlabel_size = 11

        if self.xaxis_type == "Timestamp":
            ax.set_xlabel("", size=xlabel_size)

            if self.date_locator == "days":
                interval = mdates.DayLocator(interval=self.day_interval)
            elif self.date_locator == "hours":
                interval = mdates.HourLocator(interval=self.hour_interval)

            fmt = mdates.DateFormatter(self.date_fmt)
            ax.xaxis.set_major_locator(interval)
            ax.xaxis.set_major_formatter(fmt)
            self.fig.autofmt_xdate()
        elif self.xaxis_type == "Time Step":
            ax.set_xlabel("Time (days)", size=xlabel_size)
            # x0, x1 = ax.get_xlim()
            # dt = 5
            # ax.xaxis.set_ticks(np.arange(x0, x1 + dt, dt))

            # Hide x-axis tick labels from all but the bottom (last) subplot
            for subplot in self.subplots[:-1]:
                plt.setp(subplot.ax1.get_xticklabels(), visible=False)
                plt.setp(subplot.ax2.get_xticklabels(), visible=False)
        elif self.xaxis_type == "File Number":
            ax.set_xlabel("File Number (Load Case)", size=xlabel_size)
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))

            # Hide x-axis tick labels from all but the bottom (last) subplot
            for subplot in self.subplots[:-1]:
                plt.setp(subplot.ax1.get_xticklabels(), visible=False)
                plt.setp(subplot.ax2.get_xticklabels(), visible=False)

    def _plot_unlatched_period(self):
        # TODO: Finish this properly!
        # Unlatched period
        # d1 = mdates.date2num(datetime(2018, 7, 13, 19, 40))
        # d2 = mdates.date2num(datetime(2018, 7, 14, 15, 40))
        # ymin, ymax = self.ax.get_ylim()
        # w = d2 - d1
        # h = 1.1 * (ymax - ymin)
        # rect = Rectangle(xy=(d1, ymin), width=w, height=h, edgecolor=None, facecolor='yellow', alpha=0.2)
        # self.ax.add_patch(rect)

        pass

    def _add_subplot_legend(self, subplot, num_plots=1):
        """
        Add legend to subplot.
        Creates list of line objects contained in both axes, then gets label for each line and creates legend.
        """

        if num_plots > 2:
            fontsize = 10
        else:
            fontsize = 11

        ncol = 4
        lines = subplot.handles_1 + subplot.handles_2
        labels = [l.get_label() for l in lines]

        if len(lines) == 6:
            lines = [lines[0], lines[3], lines[1], lines[4], lines[2], lines[5]]
            labels = [labels[0], labels[3], labels[1], labels[4], labels[2], labels[5]]
            ncol = 3

        subplot.ax1.legend(lines, labels, loc="upper right", ncol=ncol, fontsize=fontsize)

    def _add_fig_legend(self):
        """Add legend to bottom of figure."""

        if self.fig.legends:
            self.fig.legends = []

        self.fig.legend(loc="lower center", ncol=4, fontsize=10)

    def _adjust_fig_layout(self):
        """Size plots so that it doesn't overlap suptitle and legend."""

        self.fig.tight_layout(rect=[0, 0, 1, 0.92])  # (rect=[left, bottom, right, top])
        self.fig.subplots_adjust(hspace=0.05)


class VesselStatsWidget(QtWidgets.QWidget):
    """Summary stats plot widget class."""

    def __init__(self, parent=None):
        super(VesselStatsWidget, self).__init__(parent)

        # So can access parent class
        self.parent = parent

        # Skip routine flags; used to prevent unnecessary multiple calls to update plot routines
        self.skip_logger_combo_change = False
        self.skip_set_radios = False
        self.skip_radio_changed = False
        self.skip_update_plot = False

        # Plot data and settings
        self.plot_data = {}
        self.motions = ""

        # Container for StatsDataset objects
        self.datasets = []
        self.ylabel = stat_ylabels[0]

        # Set up layout
        self.init_ui()
        self.connect_signals()
        self.draw_axes()
        self.canvas.draw()

        # Populate fixed combo boxes - don't do this in init_ui to restrict its purpose to layout design
        self.vesselMotionsCombo.addItems(motion_types)
        self.vesselMotionsCombo.setCurrentIndex(0)
        self.stats1Combo.addItems(dict_stats.keys())
        self.stats1Combo.setCurrentIndex(3)
        self.stats2Combo.addItems(dict_stats.keys())
        self.stats2Combo.setCurrentIndex(3)

        self.skip_plot = True
        self.init_logger_channel_combos()
        self.skip_plot = False

    def init_ui(self):
        # WIDGETS
        # Selection controls
        self.openStatsButton = QtWidgets.QPushButton("Open Statistics...")
        self.clearDatasetsButton = QtWidgets.QPushButton("Clear Datasets")
        self.lbl1 = QtWidgets.QLabel("Loaded Datasets")
        self.lbl2 = QtWidgets.QLabel("Channels (echo)")
        self.datasetsList = QtWidgets.QListWidget()
        self.channelsList = QtWidgets.QListWidget()
        self.vesselMotionsCombo = QtWidgets.QComboBox()
        self.stats1Combo = QtWidgets.QComboBox()
        self.stats2Combo = QtWidgets.QComboBox()
        # self.plotSettings = QtWidgets.QPushButton("Plot Settings...")
        self.replotButton = QtWidgets.QPushButton("Replot")

        # Plot drop-downs
        self.axis2Logger = QtWidgets.QComboBox()
        self.axis2Channel = QtWidgets.QComboBox()

        # Create plot figure, canvas widget to display figure and navbar
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # CONTAINERS
        # Primary axis controls
        self.statsWidget = QtWidgets.QGroupBox("Primary Axis")
        self.vbox1 = QtWidgets.QVBoxLayout(self.statsWidget)
        self.vbox1.addWidget(QtWidgets.QLabel("Motions:"))
        self.vbox1.addWidget(self.vesselMotionsCombo)
        self.vbox1.addWidget(QtWidgets.QLabel("Statistic:"))
        self.vbox1.addWidget(self.stats1Combo)

        # Secondary axis controls
        self.axis2Group = QtWidgets.QGroupBox("Secondary Axis")
        self.vbox2 = QtWidgets.QVBoxLayout(self.axis2Group)
        self.vbox2.addWidget(QtWidgets.QLabel("Logger:"))
        self.vbox2.addWidget(self.axis2Logger)
        self.vbox2.addWidget(QtWidgets.QLabel("Channel:"))
        self.vbox2.addWidget(self.axis2Channel)
        self.vbox2.addWidget(QtWidgets.QLabel("Statistic:"))
        self.vbox2.addWidget(self.stats2Combo)

        # Selection layout
        self.selectionContainer = QtWidgets.QWidget()
        self.selectionContainer.setMinimumWidth(200)
        self.vbox = QtWidgets.QVBoxLayout(self.selectionContainer)
        self.vbox.addWidget(self.openStatsButton)
        self.vbox.addWidget(self.clearDatasetsButton)
        self.vbox.addWidget(self.lbl1)
        self.vbox.addWidget(self.datasetsList)
        self.vbox.addWidget(self.lbl2)
        self.vbox.addWidget(self.channelsList)
        self.vbox.addWidget(self.statsWidget)
        self.vbox.addWidget(self.axis2Group)
        # self.vbox.addWidget(self.plotSettings)
        self.vbox.addWidget(self.replotButton)

        # Plot layout
        self.plotWidget = QtWidgets.QWidget()
        self.plotLayout = QtWidgets.QVBoxLayout(self.plotWidget)
        self.plotLayout.addWidget(navbar)
        self.plotLayout.addWidget(self.canvas)

        # LAYOUT
        # Splitter to allow resizing of widget containers
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.selectionContainer)
        splitter.addWidget(self.plotWidget)
        splitter.setSizes([200, 10000])

        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(splitter)

    def connect_signals(self):
        self.clearDatasetsButton.clicked.connect(self.on_clear_datasets_clicked)
        self.datasetsList.currentItemChanged.connect(self.on_dataset_list_changed)
        self.vesselMotionsCombo.currentIndexChanged.connect(self.on_motions_combo_changed)
        self.stats1Combo.currentIndexChanged.connect(self.on_stats1_combo_changed)
        self.axis2Logger.currentIndexChanged.connect(self.on_axis2_logger_combo_changed)
        self.stats2Combo.currentIndexChanged.connect(self.on_stats2_combo_changed)
        self.replotButton.clicked.connect(self.on_replot_clicked)

    def draw_axes(self):
        """(Re)construct a blank figure workspace."""

        self.fig.clf()
        self.ax1 = self.fig.add_subplot(311)
        self.ax2 = self.fig.add_subplot(312, sharex=self.ax1)
        self.ax3 = self.fig.add_subplot(313, sharex=self.ax1)
        self.ax1b = self.ax1.twinx()
        self.ax2b = self.ax2.twinx()
        self.ax3b = self.ax3.twinx()
        self.ax1b.yaxis.set_visible(False)
        self.ax2b.yaxis.set_visible(False)
        self.ax3b.yaxis.set_visible(False)
        self.ax1b.grid(False)
        self.ax2b.grid(False)
        self.ax3b.grid(False)

    def init_logger_channel_combos(self):
        """Reset logger and channel drop-downs."""

        self.axis2Logger.clear()
        self.axis2Logger.addItem("None")
        self.axis2Channel.clear()
        self.axis2Channel.addItem("None")

    def on_clear_datasets_clicked(self):
        self.clear_dashboard()

    def on_dataset_list_changed(self):
        self.update_channels_list()

    def on_axis2_logger_combo_changed(self):
        if self.skip_plot is False:
            self.update_channels_combo()

    def on_motions_combo_changed(self):
        """Update plots for selected vessel motions."""

        if self.datasets:
            self.set_plot_data()
            self.update_plots()

    def on_stats1_combo_changed(self):
        """Update vessel motion plots for selected statistic."""

        if self.datasets:
            self.set_plot_data()
            self.update_plots()

    def on_stats2_combo_changed(self):
        """Update secondary axis plots for selected statistic."""

        if self.datasets:
            self.set_plot_data()
            self.update_plots()

    def on_replot_clicked(self):
        """Replot stats."""

        if self.datasets:
            self.set_plot_data()
            self.update_plots()

    def clear_dashboard(self):
        """Clear all stored stats datasets and reset layout."""

        # Set flag to prevent channel combo boxes repopulating when clear the dataset combo boxes
        self.skip_logger_combo_change = True
        self.datasets = []
        self.datasetsList.clear()
        self.channelsList.clear()
        self.init_logger_channel_combos()
        self.skip_logger_combo_change = False

    def update_stats_datasets_list(self, dataset_ids):
        """Populate loaded datasets list."""

        # Create dataset list and select first item (this will trigger an update of update_channels_list)
        self.datasetsList.addItems(dataset_ids)

        # Add dataset ids to logger combo box
        self.axis2Logger.addItems(dataset_ids)
        self.datasetsList.setCurrentRow(0)

    def update_channels_list(self):
        """Update channels list to match selected dataset."""

        i = self.datasetsList.currentRow()
        if i == -1:
            return

        # Add channels to list and make non-selectable since they are just an echo for reference
        self.channelsList.clear()
        for channel in self.datasets[i].channels:
            item = QtWidgets.QListWidgetItem(channel)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
            self.channelsList.addItem(item)

    def update_channels_combo(self):
        """Update the channel drop-down to reflect the respective logger drop-down selection."""

        if self.skip_logger_combo_change is True:
            return

        dataset_id = self.axis2Logger.currentText()

        # If no dataset is selected, re-initialise the channel drop-down
        if dataset_id == "None":
            self.axis2Channel.clear()
            self.axis2Channel.addItem("None")
        else:
            # Retrieve channel names for selected dataset_id
            i = self.axis2Logger.currentIndex() - 1
            channels = self.datasets[i].channels

            # Add channels to respective channel combo
            self.axis2Channel.clear()
            self.axis2Channel.addItems(channels)

    def set_plot_data(self, init=False):
        """Assign plot data for each axis based on respective selected logger and channel drop-downs."""

        # If flag is set it means no datasets were previously loaded; therefore set drop-downs to presets
        # to create an initial plot
        if init is True:
            self.axis2Logger.setCurrentIndex(1)

            # If vessel dataset loaded, look for SigWaveHeight column and select that if exists since it makes sense to
            # plot this by default and st statistic combo to plot the mean
            if "SigWaveHeight" in self.datasets[0].channels:
                self.axis2Channel.setCurrentText("SigWaveHeight")
                self.stats2Combo.setCurrentText("Mean")

        # Selected motions and statistic to get data for
        self.motions = self.vesselMotionsCombo.currentText()

        if self.motions == "Surge/Sway/Heave":
            motion_cols = vessel_trans
        else:
            motion_cols = vessel_rots

        self.stat1 = self.stats1Combo.currentText()
        self.stat2 = self.stats2Combo.currentText()
        stat1_col = dict_stats[self.stat1]
        stat2_col = dict_stats[self.stat2]

        # Dictionary to hold plot vessel motions dataframe and axis 2 channel dataframe, label and units
        plot_data = {}

        # Get axis 1 plot data
        # Get vessel motions data from vessel dataframe
        # It is required that the vessel dataset is called "VESSEL"
        # and the columns are named "Surge", "Sway", "Heave", "Roll", "Pitch", "Yaw"
        for i in range(len(self.datasets)):
            if self.datasets[i].logger_id.upper() == "VESSEL":
                df_vessel = self.datasets[i].df
                df_vessel = df_vessel.xs(key=stat1_col, axis=1, level=1)

                try:
                    # TODO: Should make work for more generalised column names
                    df_vessel = df_vessel[motion_cols]
                    plot_data["vessel_data"] = df_vessel
                except:
                    pass
                break

        # Selected logger info
        logger_i = self.axis2Logger.currentIndex() - 1
        channel = self.axis2Channel.currentText()

        if channel == "":
            channel = "None"

        # Get axis 2 plot data
        if logger_i > -1 and channel != "None":
            # Retrieve dataframe from dataset objects list
            df_axis2 = self.datasets[logger_i].df
            logger_id = self.datasets[logger_i].logger_id

            # Slice dataframe for the selected statistic and then select channel
            df_axis2 = df_axis2.xs(key=stat2_col, axis=1, level=1)
            df_axis2 = df_axis2[channel]
            units = df_axis2.columns[0]

            # Create legend label and y-axis label
            label = self.create_legend_label(self.stat2, logger_id, channel)
            ylabel = self.create_ylabel(channel, units)

            # Store vessel data from and channel data and info to dictionary
            plot_data["axis2_data"] = df_axis2
            plot_data["channel"] = channel
            plot_data["label"] = label
            plot_data["ylabel"] = ylabel
            plot_data["units"] = units

        self.plot_data = plot_data

    def create_legend_label(self, stat, logger_id, channel):
        """Construct legend label based on plotted stat, logger id and channel."""

        # Check for a preferred channel name to use
        if channel in dict_labels:
            channel = dict_labels[channel]

        # # Construct label - prepend logger name unless channel source is the vessel (which would be superfluous)
        if logger_id.upper() != "VESSEL":
            label = " ".join((stat, logger_id, channel))
        else:
            label = " ".join((stat, channel))

        return label

    def create_ylabel(self, channel, units):
        """Construct y axis label based on plotted channel and units."""

        # Check for a preferred channel name to use
        if channel in dict_ylabels:
            channel = dict_ylabels[channel]

        # Construct label
        ylabel = f"{channel} ($\mathregular{{{units}}}$)"

        return ylabel

    def update_plots(self):
        """Update stats plots."""

        self.draw_axes()

        # Flags to check which axes are plotted to modify gridlines shown
        plot = False
        linewidth = 1
        df_vessel: pd.DataFrame
        df: pd.DataFrame
        self._set_title()

        # Plot vessel motions
        if "vessel_data" in self.plot_data:
            df_vessel = self.plot_data["vessel_data"]
            index_test_value = df_vessel.index[0]

            col = df_vessel.columns[0]
            motion = col[0]
            units = col[1]
            self.ax1.plot(df_vessel[col], "r", lw=linewidth, label=motion + " Acceleration")
            label = f"{motion} ($\mathregular{{{units}}}$)"
            self.ax1.set_ylabel(label)

            col = df_vessel.columns[1]
            motion = col[0]
            units = col[1]
            self.ax2.plot(df_vessel[col], "g", lw=linewidth, label=motion + " Acceleration")
            label = f"{motion} ($\mathregular{{{units}}}$)"
            self.ax2.set_ylabel(label)

            col = df_vessel.columns[2]
            motion = col[0]
            units = col[1]
            self.ax3.plot(df_vessel[col], "purple", lw=linewidth, label=motion + " Acceleration")
            label = f"{motion} ($\mathregular{{{units}}}$)"
            self.ax3.set_ylabel(label)
            plot = True

        # Plot secondary axis channel
        if "axis2_data" in self.plot_data:
            df = self.plot_data["axis2_data"]
            index_test_value = df.index[0]
            label = self.plot_data["label"]
            ylabel = self.plot_data["ylabel"]

            self.ax1b.yaxis.set_visible(True)
            self.ax2b.yaxis.set_visible(True)
            self.ax3b.yaxis.set_visible(True)
            self.ax1b.plot(df, c="dodgerblue", lw=linewidth, label=label)
            self.ax2b.plot(df, c="dodgerblue", lw=linewidth)
            self.ax3b.plot(df, c="dodgerblue", lw=linewidth)
            self.ax2b.set_ylabel(ylabel)
            self.ax1b.set_ylabel(ylabel)
            self.ax3b.set_ylabel(ylabel)
            plot = True

        # Complete plot if at least one channel was plotted
        if plot is True:
            self.ax1.margins(0)
            self.ax2.margins(0)
            self.ax3.margins(0)
            self.ax1b.margins(0)
            self.ax2b.margins(0)
            self.ax3b.margins(0)

            # Format x-axis if index is timestamps
            if isinstance(index_test_value, pd.Timestamp):
                days = mdates.DayLocator(interval=7)
                fmt = mdates.DateFormatter("%d-%b-%y")
                self.ax3.xaxis.set_major_locator(days)
                self.ax3.xaxis.set_major_formatter(fmt)
                self.fig.autofmt_xdate()
            else:
                self.ax3.set_xlabel("File Number (Load Case)")

            self.fig.legend(loc="lower center", ncol=4, fontsize=11)
            # Ensure plots don't overlap suptitle and legend
            self.fig.tight_layout(rect=[0, 0.05, 1, 0.9])  # (rect=[left, bottom, right, top])

        self.canvas.draw()

    def _set_title(self):
        """Set main plot title."""

        # Attempt to retrieve title from project setup dashboard
        project_name = self.parent.inputDataModule.control.project_name
        campaign_name = self.parent.inputDataModule.control.campaign_name

        if project_name == "":
            project_name = "Project Title"
        if campaign_name == "":
            campaign_name = "Campaign Title"

        if self.stat1 == "Std. Dev.":
            stat = "Standard Deviation"
        else:
            stat = self.stat1

        title = f"{project_name} - {campaign_name}\n{stat} Vessel Accelerations"
        self.fig.suptitle(title, **title_args)


class PlotStyle2H:
    def __init__(self, canvas, fig):
        self.canvas = canvas
        self.fig = fig
        self.logo_path = r"images\2H_logo.emf"

        # "2H blue"
        color_2H = np.array([0, 49, 80]) / 255

        # self.generalFont = {'family': 'sans-serif',
        #                     'sans-serif': ['Tahoma'],
        #                     'size': 13}
        # plt.rc('font', **self.generalFont)

        self.title1_props = {  # 'fontname': 'Tahoma',
            "fontsize": 14,
            "color": color_2H,
            "weight": "bold",
            "ha": "center",
            "va": "center",
        }

        self.title2_props = {  # 'fontname': 'Tahoma',
            "fontsize": 16,
            "color": color_2H,
            "weight": "bold",
            "ha": "center",
            "va": "center",
        }

        self.axis_props = {"weight": "bold", "fontsize": 13}

    def add_2H_icon(self):
        """ Add 2H icon to plot."""

        # im = plt.imread(self.logo_path)
        im = PIL.Image.open(self.logo_path)
        im.thumbnail((65, 65))
        w, h = im.size
        topleft = self.fig.bbox.ymax
        self.icon2h = self.fig.figimage(im, xo=10, yo=topleft - h - 30, zorder=10)
        self.canvas.draw()

        # print(im.size)
        # print(im.mode)
        # print(im.format)
        # print(im.palette)

        # w0, h0 = im.size
        # w = 60
        # dw = w / w0
        # h = int(h0 * dw)
        # im = im.resize((w, h), PIL.Image.ANTIALIAS)
        # im = np.array(im).astype(float) / 255

        # This method fixes image to figure corner but resolution is poo
        # ax_logo = self.fig.add_axes([0, 0.9, 0.1, 0.1], anchor='NW', zorder=10)
        # ax_logo.imshow(im)
        # ax_logo.axis('off')

    def remove_2H_icon(self):
        """Remove 2H icon from plot."""

        self.icon2h.remove()
        self.canvas.draw()

    def format_2h_style(self, title1, title2, title3):
        """Create a 2H style title."""

        ax = self.fig.axes[0]
        plt.sca(ax)
        # plt.rc('font', **self.generalFont)
        # plt.xlabel(self.xlabel, **axisArgs)
        # plt.ylabel(self.ylabel, **axisArgs)

        # ax.set_title('my special title', **self.title1_props)
        # ax.set_title('My Special Title')

        # plt.rcdefaults()
        # plt.style.use('default')

        plt.subplots_adjust(bottom=0.2, top=0.8, right=0.965, left=0.08)

        # Format title
        ax.set_title("")
        plt.text(0.5, 1.18, title1, transform=ax.transAxes, fontdict=self.title1_props)
        plt.text(0.5, 1.1, title2.upper(), transform=ax.transAxes, fontdict=self.title2_props)
        plt.text(0.5, 1.04, title3, transform=ax.transAxes, fontdict=self.title1_props)

        # Format axes labels
        # plt.xlabel(ax.get_xlabel(), fontdict=self.axis_props)
        # plt.ylabel(ax.get_ylabel(), fontdict=self.axis_props)

        # Format legend
        try:
            self.fig.axes[1].get_legend().remove()
        except:
            pass

        leg = self.fig.legend(
            loc="lower center",
            ncol=4,
            frameon=True,
            fancybox=False,
            edgecolor="none",
            facecolor="none",
        )

        # Set axis limits
        xLocs, _ = plt.xticks()
        yLocs, _ = plt.yticks()
        # plt.ylim(yLocs[0], yLocs[-1])
        # plt.xlim(xLocs[0], xLocs[-1])
        # font = findfont(FontProperties(family=['sans-serif']))
        # print(font)

        # w, h = self.fig.get_size_inches()
        # print(w, h)
        # self.fig.set_size_inches(6.4, 4.8)
        # self.fig.set_size_inches(10.18504, 6.653543)
        # plt.savefig('stats_def.png')
        # self.fig.set_size_inches(11.69, 8.27)
        # plt.savefig('stats_a4.png')
        # self.fig.tight_layout()
        self.canvas.draw()


# For testing layout
if __name__ == "__main__":
    np.random.seed(0)
    app = QtWidgets.QApplication(sys.argv)

    # Create dummy dataset
    # start_dates = ["2017-03-10 00:00:00", "2017-03-10 00:10:00", "2017-03-10 00:20:00"]
    # start_dates = [datetime.strptime(t, "%Y-%m-%d %H:%M:%S") for t in start_dates]
    # data = [[j + i * 10 for j in range(16)] for i in range(3)]
    # data = np.random.randn(3, 4)
    # df = pd.DataFrame(data=data, index=start_dates)
    # dataset = StatsDataset(logger_id="test", df=df)
    # dataset_names = ["test"]

    w = StatsWidget()
    # w = VesselStatsWidget()
    w.show()
    # w.datasets.append(dataset)
    # w.update_stats_datasets_list(dataset_names)
    # w.update_plot()

    # p = PlotStyle2H(w.canvas, w.fig)
    # p.add_2H_icon()
    # title = {'title1': '21239 Total WoS', 'title2': 'Glendronach Well Monitoring Campaign', 'title3': 'Mean'}
    # p.format_2h_style(**title)

    sys.exit(app.exec_())

# if __name__ == '__main__':
#     import sys
#     from PyQt5.QtWidgets import QApplication
#     import os
#
#     from core.read_files import read_spectrograms_hdf5
#
#     fpath = r'C:\Users\dickinsc\PycharmProjects\_2. DataLab Analysis Files\21239\3. Output\Spectrograms'
#     fname = 'Spectrograms_Data_BOP_AccelX.h5'
#     fpath = os.path.join(fpath, fname)
#     logger, df = read_spectrograms_hdf5(fpath)
#
#     app = QApplication(sys.argv)
#     # w = SpectrogramWidget()
#     # w.datasets[logger] = df
#     # w.update_spect_datasets_list(logger)
#     w = SpectroPlotSettings()
#     w.show()
#     sys.exit(app.exec_())
