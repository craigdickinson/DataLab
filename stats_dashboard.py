import sys
import logging
from datetime import datetime

import PIL
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
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
# from matplotlib.ticker import MaxNLocator
# from matplotlib.font_manager import findfont, FontProperties
# import colormap as cmaps

stat_ylabels = [
    'Acceleration ($\mathregular{m/s^2}$)',
    'Angular Rate ($\mathregular{deg/s}$)',
]

variance_channels_combo = [
    'Acceleration X',
    'Acceleration Y',
    'Angular Rate X',
    'Angular Rate Y',
]

motion_types = [
    'Surge/Sway/Heave',
    'Roll/Pitch/Yaw',
]

vessel_trans = [
    'AccSurge',
    'AccSway',
    'AccHeave',
]

vessel_rots = [
    'AccRoll',
    'AccPitch',
    'AccYaw',
]

# Dictionary of stats combo items and stats file column name pairs
dict_stats = {
    'Minimum': 'min',
    'Maximum': 'max',
    'Mean': 'mean',
    'Std. Dev.': 'std',
    'Combined': 'combined',
}

dict_stats_abbrev = {
    'Minimum': 'Min',
    'Maximum': 'Max',
    'Std. Dev.': 'Std. Dev.',
}

dict_labels = {
    'SigWaveHeight': 'Sig. Wave Height',
    'SigWavePeriod': 'Sig. Wave Period',
}

dict_ylabels = {
    'SigWaveHeight': 'Hs',
    'SigWavePeriod': 'Tp',
}

# 2H blue colour font
color_2H = np.array([0, 49, 80]) / 255

# Title style args
title_args = dict(
    size=14,
    fontname='tahoma',
    color=color_2H,
    weight='bold',
)

plt.style.use('seaborn')


# plt.style.use('default')

class StatsDataset:
    """Class to hold stats datasets and associated properties."""

    def __init__(self, logger_id='', df=pd.DataFrame()):
        self.logger_id = logger_id
        self.df = df

        try:
            # Get unique channels list and filter out None/False entries
            self.channels = list(filter(None, self.df.columns.unique(level='channels')))
        except:
            self.channels = ['N/A']


class PlotData:
    def __init__(self):
        """Class to hold data and related info for a primary and secondary axes and to plot it."""

        # Primary axes combo selections
        self.logger_1 = '-'
        self.channel_1 = '-'
        self.stat_1 = 'Std. Dev.'

        # Primary axes plot data
        self.ax1 = None
        self.handles_1 = []
        self.df_1 = pd.DataFrame()
        self.label_1 = ''
        self.units_1 = ''
        self.color_1 = 'dodgerblue'

        # Secondary axes combo selections
        self.logger_2 = '-'
        self.channel_2 = '-'
        self.stat_2 = 'Std. Dev.'

        # Secondary axes plot data
        self.ax2 = None
        self.handles_2 = []
        self.df_2 = pd.DataFrame()
        self.label_2 = ''
        self.units_2 = ''
        self.color_2 = 'orange'

        # Flags to identify if axes are plotted
        self.ax1_in_use = False
        self.ax2_in_use = False

    def set_ax1_plot_data(self, datasets, logger_i, channel_name, stat):
        self.df_1 = pd.DataFrame()
        self.channel_1 = ''
        self.label_1 = ''
        self.units_1 = ''

        # Logger index and default id
        i = logger_i - 1
        logger_id = '-'

        # If a channel is selected
        if i > -1 and channel_name != '-':
            # Retrieve logger stats data
            logger_id = datasets[i].logger_id
            df = datasets[i].df

            # Column name in stats dataset
            stat_col = dict_stats[stat]

            # Check for preferred stat label for legend
            if stat in dict_stats_abbrev:
                stat_lbl = dict_stats_abbrev[stat]
            else:
                stat_lbl = stat

            # Slice data frame for the selected statistic and then on channel
            if stat != 'Combined':
                df = df.loc[:, (channel_name, stat_col)]
                units = df.columns[0]
                label = ' '.join((stat_lbl, logger_id, channel_name))
            else:
                df = datasets[i].df[channel_name]
                units = df.columns[0][1]
                label = ' '.join((logger_id, channel_name))

            # Store plot data
            self.df_1 = df
            self.label_1 = label
            self.units_1 = units

        # Store combo selections
        self.logger_1 = logger_id
        self.channel_1 = channel_name
        self.stat_1 = stat

    def set_ax2_plot_data(self, datasets, logger_i, channel_name, stat):
        self.df_2 = pd.DataFrame()
        self.channel_2 = ''
        self.label_2 = ''
        self.units_2 = ''

        # Logger index and default id
        i = logger_i - 1
        logger_id = '-'

        # If a channel is selected
        if i > -1 and channel_name != '-':
            # Retrieve logger stats data
            logger_id = datasets[i].logger_id
            df = datasets[i].df

            # Column name in stats datasets
            stat_col = dict_stats[stat]

            # Check for preferred stat label for legend
            if stat in dict_stats_abbrev:
                stat_lbl = dict_stats_abbrev[stat]
            else:
                stat_lbl = stat

            # Slice data frame for the selected statistic and then on channel
            if stat != 'Combined':
                df = df.loc[:, (channel_name, stat_col)]
                units = df.columns[0]
                label = ' '.join((stat_lbl, logger_id, channel_name))
            # Slice data frame on channel
            else:
                df = datasets[i].df[channel_name]
                units = df.columns[0][1]
                label = ' '.join((logger_id, channel_name))

            # Store plot data
            self.df_2 = df
            self.label_2 = label
            self.units_2 = units

        # Store combo selections
        self.logger_2 = logger_id
        self.channel_2 = channel_name
        self.stat_2 = stat

    def plot_on_axes(self, axes=0, num_plots=1):
        """Plot on selected subplot axes."""

        if axes == 0:
            kwargs = dict(ax=self.ax1,
                          df=self.df_1,
                          label=self.label_1,
                          channel=self.channel_1,
                          units=self.units_1,
                          color=self.color_1,
                          )
            self.ax1_in_use, self.handles_1 = self._plot_data(num_plots, **kwargs)
        else:
            kwargs = dict(ax=self.ax2,
                          df=self.df_2,
                          label=self.label_2,
                          channel=self.channel_2,
                          units=self.units_2,
                          color=self.color_2,
                          )
            self.ax2_in_use, self.handles_2 = self._plot_data(num_plots, **kwargs)

    @staticmethod
    def _plot_data(num_plots, ax, df, label, channel, units, color, linewidth=1):
        """Plot data on the specified axes."""

        # Set y-axis font size depending on number of plots
        if num_plots > 2:
            ylabel_size = 10
        else:
            ylabel_size = 11

        ax.cla()
        handles = []
        ax_in_use = False
        if df.empty is False:
            line = ax.plot(df, c=color, lw=linewidth, label=label)
            handles.append(line[0])

            # Check for a preferred channel name to use
            if channel in dict_ylabels:
                channel = dict_ylabels[channel]

            ax.set_ylabel(f'{channel}\n($\mathregular{{{units}}}$)', size=ylabel_size)
            ax.margins(x=0, y=0)
            ax_in_use = True

        return ax_in_use, handles

    def create_compound_plot(self, num_plots=1):
        """Create plot of all stats on the specified axes."""

        ax = self.ax1
        df = self.df_1
        channel = self.channel_1
        units = self.units_1

        # Set y-axis font size depending on number of plots
        if num_plots > 2:
            ylabel_size = 10
        else:
            ylabel_size = 11

        ax.cla()
        self.handles_1 = []
        if df.empty is False:
            t = df.index.values
            mn = df['min'].values.flatten()
            mx = df['max'].values.flatten()
            ave = df['mean'].values.flatten()
            std = df['std'].values.flatten()

            line1 = ax.plot(t, ave, label='Mean')
            line2 = ax.fill_between(t, mn, mx, alpha=0.2, label='Range')
            line3 = ax.fill_between(t, ave - std, ave + std, alpha=0.2, facecolor='r', label='SD')
            self.handles_1 = [line1[0], line2, line3]

            # Check for a preferred channel name to use
            if channel in dict_ylabels:
                channel = dict_ylabels[channel]

            ax.set_ylabel(f'{channel}\n($\mathregular{{{units}}}$)', size=ylabel_size)
            ax.margins(x=0, y=0)

            self.ax1_in_use = True
        else:
            self.ax1_in_use = False

    def create_compound_plot2(self, num_plots=1):
        """Create plot of all stats on the specified axes."""

        ax = self.ax2
        df = self.df_2
        channel = self.channel_2
        units = self.units_2

        # Set y-axis font size depending on number of plots
        if num_plots > 2:
            ylabel_size = 10
        else:
            ylabel_size = 11

        ax.cla()
        self.handles_1 = []
        if df.empty is False:
            t = df.index.values
            mn = df['min'].values.flatten()
            mx = df['max'].values.flatten()
            ave = df['mean'].values.flatten()
            std = df['std'].values.flatten()

            line1 = ax.plot(t, ave, label='Mean')
            line2 = ax.fill_between(t, mn, mx, alpha=0.2, label='Range')
            line3 = ax.fill_between(t, ave - std, ave + std, alpha=0.2, facecolor='r', label='SD')
            self.handles_2 = [line1[0], line2, line3]

            # Check for a preferred channel name to use
            if channel in dict_ylabels:
                channel = dict_ylabels[channel]

            ax.set_ylabel(f'{channel}\n($\mathregular{{{units}}}$)', size=ylabel_size)
            ax.margins(x=0, y=0)

            self.ax2_in_use = True
        else:
            self.ax2_in_use = False


class StatsWidget(QtWidgets.QWidget):
    """Summary stats plot widget class."""

    # List of plot colours for each subplot (limited to 4 plots)
    ax1_colors = ['dodgerblue',
                  'red',
                  'blue',
                  'green',
                  ]
    ax2_colors = ['deepskyblue',
                  'orange',
                  'yellow',
                  'purple',
                  ]

    def __init__(self, parent=None):
        super(StatsWidget, self).__init__(parent)

        # So can access parent class
        self.parent = parent

        # Skip routine flags; used to prevent unnecessary multiple calls to update plot routines
        self.resetting_dashboard = False
        self.skip_set_radios = False
        self.skip_radio_changed = False
        self.skip_update_plot = False

        self.plot_capacity = 4
        self.num_plots = 1

        # Combo box selection indexes
        self.plot_i = 0
        self.axis_i = 0
        self.logger_i = 0
        self.channel_i = 0

        # Combo box selection text
        self.logger_id = ''
        self.channel_name = ''
        self.stat = ''

        # Plot data and settings
        self.project = '21239 Total WoS - Glendronach Well Monitoring Campaign'

        # Container to hold plot data for each subplot
        self.subplots = [PlotData()]

        # Container for StatsDataset objects
        self.datasets = []
        self.ylabel = stat_ylabels[0]

        # Flag to prevent plot being updated during combo boxes updates
        self.skip_plotting = False

        # Set layout and initialise combo boxes
        self._init_ui()
        self._init_combos()

        self._connect_signals()
        self._create_subplots()
        self.fig.tight_layout()
        self.canvas.draw()

    def _init_ui(self):
        # Main layout
        self.layout = QtWidgets.QHBoxLayout(self)

        # Selection layout
        self.selectionContainer = QtWidgets.QWidget()
        self.selectionContainer.setFixedWidth(200)

        # policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        # selection.setSizePolicy(policy)

        # Load/clear buttons and datasets and channels lists
        self.loadStatsButton = QtWidgets.QPushButton('Load Statistics')
        self.clearDatasetsButton = QtWidgets.QPushButton('Clear Datasets')
        self.datasetList = QtWidgets.QListWidget()
        self.channelsLabel = QtWidgets.QLabel('Available Channels')
        self.channelsList = QtWidgets.QListWidget()

        # Number of plots
        self.numPlotsCombo = QtWidgets.QComboBox()
        self.numPlotsCombo.setFixedWidth(40)
        self.numPlotsContainer = QtWidgets.QWidget()
        self.numPlotsForm = QtWidgets.QFormLayout(self.numPlotsContainer)
        self.numPlotsForm.addRow(QtWidgets.QLabel('Number of plots:'), self.numPlotsCombo)

        # Plot data selection
        self.plotNumCombo = QtWidgets.QComboBox()
        self.plotNumCombo.setFixedWidth(40)
        self.axisCombo = QtWidgets.QComboBox()
        self.axisCombo.setFixedWidth(80)
        self.loggerCombo = QtWidgets.QComboBox()
        self.channelCombo = QtWidgets.QComboBox()
        self.statCombo = QtWidgets.QComboBox()

        self.plotGroup = QtWidgets.QGroupBox('Select Plot Data')
        self.form = QtWidgets.QFormLayout(self.plotGroup)
        self.form.addRow(QtWidgets.QLabel('Plot:'), self.plotNumCombo)
        self.form.addRow(QtWidgets.QLabel('Axis:'), self.axisCombo)
        self.form.addRow(QtWidgets.QLabel('Logger:'), self.loggerCombo)
        self.form.addRow(QtWidgets.QLabel('Channel:'), self.channelCombo)
        self.form.addRow(QtWidgets.QLabel('Stat:'), self.statCombo)

        # Plot settings button
        self.settingsButton = QtWidgets.QPushButton('Plot Settings')

        # Combine selection widgets
        self.vbox = QtWidgets.QVBoxLayout(self.selectionContainer)
        self.vbox.addWidget(self.loadStatsButton)
        self.vbox.addWidget(self.clearDatasetsButton)
        self.vbox.addWidget(QtWidgets.QLabel('Loaded Datasets'))
        self.vbox.addWidget(self.datasetList)
        self.vbox.addWidget(self.channelsLabel)
        self.vbox.addWidget(self.channelsList)
        self.vbox.addWidget(self.numPlotsContainer)
        self.vbox.addWidget(self.plotGroup)
        self.vbox.addWidget(self.settingsButton)

        # Create plot figure, canvas widget to display figure and navbar
        self.plotWidget = QtWidgets.QWidget()
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.navbar = NavigationToolbar(self.canvas, self)

        self.plotLayout = QtWidgets.QVBoxLayout(self.plotWidget)
        self.plotLayout.addWidget(self.navbar)
        self.plotLayout.addWidget(self.canvas)

        # Add widgets to main layout
        self.layout.addWidget(self.selectionContainer)
        self.layout.addWidget(self.plotWidget)

    def _init_combos(self):
        """Populate combo boxes and store initial selections."""

        plot_capacity = self._get_plot_numbers_list(self.plot_capacity)
        self.numPlotsCombo.addItems(plot_capacity)
        plot_nums = self._get_plot_numbers_list(self.num_plots)
        self.plotNumCombo.addItems(plot_nums)
        self.axisCombo.addItems(['Primary', 'Secondary'])
        self.statCombo.addItems(dict_stats.keys())
        self.statCombo.setCurrentIndex(3)
        self.stat = self.statCombo.currentText()
        self.loggerCombo.addItem('-')
        self.channelCombo.addItem('-')

    def _connect_signals(self):
        self.clearDatasetsButton.clicked.connect(self.on_clear_datasets_clicked)
        self.datasetList.currentItemChanged.connect(self.on_dataset_list_item_changed)
        self.numPlotsCombo.currentIndexChanged.connect(self.on_num_plots_combo_changed)
        self.plotNumCombo.currentIndexChanged.connect(self.on_plot_num_combo_changed)
        self.axisCombo.currentIndexChanged.connect(self.on_axis_combo_changed)
        self.loggerCombo.currentIndexChanged.connect(self.on_logger_combo_changed)
        self.channelCombo.currentIndexChanged.connect(self.on_channel_combo_changed)
        self.statCombo.currentIndexChanged.connect(self.on_stat_combo_changed)

    @staticmethod
    def _get_plot_numbers_list(n):
        return list(map(str, range(1, n + 1)))

    def on_clear_datasets_clicked(self):
        self.reset_dashboard()

    def on_dataset_list_item_changed(self):
        self._update_channels_list()

    def on_num_plots_combo_changed(self):
        self.num_plots = self.numPlotsCombo.currentIndex() + 1
        self._set_subplot_containers()
        self._update_plot_num_combo()

        try:
            self._create_subplots()
            self._plot_all_stored_data()
        except Exception as e:
            msg = 'Unexpected error plotting stats'
            self.parent.error(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
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
        except Exception as e:
            msg = 'Unexpected error plotting stats'
            self.parent.error(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
            logging.exception(e)

    def on_channel_combo_changed(self):
        self.channel_i = self.channelCombo.currentIndex()
        self.channel_name = self.channelCombo.currentText()

        if self.resetting_dashboard is True:
            return

        try:
            self.update_plot()
        except Exception as e:
            msg = 'Unexpected error plotting stats'
            self.parent.error(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
            logging.exception(e)

    def on_stat_combo_changed(self):
        """Update primary axis plots for selected statistic if datasets have been loaded"""

        # Set stat selection details
        self.stat = self.statCombo.currentText()

        if self.datasets:
            try:
                self.update_plot()
            except Exception as e:
                msg = 'Unexpected error plotting stats'
                self.parent.error(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
                logging.exception(e)

    def _create_subplots(self):
        """Create figure with required number of subplots."""

        # TODO: Make as user settings
        share_pri_y_axes = True
        share_sec_y_axes = True

        self.fig.clf()

        # Create first subplot
        ax1 = self.fig.add_subplot(self.num_plots, 1, 1)

        # Create remaining subplots with a shared x-axis to ax1 then prepend ax1 to axes list
        if share_pri_y_axes is True:
            sharey_ax = ax1
        else:
            sharey_ax = None

        pri_axes = [self.fig.add_subplot(self.num_plots, 1, i + 1, sharex=ax1, sharey=sharey_ax) for i in
                    range(1, self.num_plots)]
        pri_axes.insert(0, ax1)

        # Create secondary axes list and set properties
        sec_axes = [ax.twinx() for ax in pri_axes]
        ax0 = sec_axes[0]

        for ax in sec_axes:
            # Share secondary axes with first subplot
            if share_sec_y_axes is True:
                if ax != ax0:
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

    def reset_dashboard(self):
        """Clear all stored datasets and reset layout."""

        self.resetting_dashboard = True
        self.datasets = []
        self.datasetList.clear()
        self.channelsList.clear()
        self.channelsLabel.setText('Available Channels')

        # Remove all but the first item in each combo box
        [self.loggerCombo.removeItem(i) for i in range(self.loggerCombo.count(), 0, -1)]
        [self.channelCombo.removeItem(i) for i in range(self.channelCombo.count(), 0, -1)]

        self.logger_i = 0
        self.channel_i = 0
        self.subplots = [PlotData() for _ in range(self.num_plots)]
        self._create_subplots()
        self.fig.tight_layout()
        self.canvas.draw()
        self.resetting_dashboard = False

    def set_preset_logger_and_channel(self):
        """When no datasets previously loaded, set drop-downs to presets to create an initial plot."""

        self.skip_plotting = True

        if self.loggerCombo.count() > 1:
            self.loggerCombo.setCurrentIndex(1)
        if self.channelCombo.count() > 1:
            self.channelCombo.setCurrentIndex(1)

        self.skip_plotting = False

    def _set_plot_selections(self):
        """Set plot drop-downs selections."""

        i = self.plot_i

        if self.axis_i == 0:
            logger = self.subplots[i].logger_1
            channel = self.subplots[i].channel_1
            stat = self.subplots[i].stat_1
        else:
            logger = self.subplots[i].logger_2
            channel = self.subplots[i].channel_2
            stat = self.subplots[i].stat_2

        # Assign settings to combos
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
                self.subplots.append(PlotData())
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
        self.channelsLabel.setText(f'Available {logger_id} Channels')

        # Add channels to list and make non-selectable since they are just an echo for reference
        self.channelsList.clear()
        for channel in self.datasets[i].channels:
            item = QtWidgets.QListWidgetItem(channel)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
            self.channelsList.addItem(item)

    def _update_plot_num_combo(self):
        """Update plot number drop-down."""

        self.plotNumCombo.clear()
        plot_nums = self._get_plot_numbers_list(self.num_plots)
        self.plotNumCombo.addItems(plot_nums)

        # Attempt to retain previously selected plot number, otherwise select plot 1
        if self.plot_i < self.plotNumCombo.count():
            self.plotNumCombo.setCurrentIndex(self.plot_i)
        else:
            self.plotNumCombo.setCurrentIndex(0)

    def _update_logger_combo(self, logger_ids):
        """Add logger ids to logger combo box."""

        self.loggerCombo.addItems(logger_ids)

    def _update_channel_combo(self):
        """Repopulate channel combo box with channels that pertain to selected logger."""

        # Remove all but first item
        [self.channelCombo.removeItem(i) for i in range(self.channelCombo.count(), 0, -1)]

        # Don't add any channels if no logger selected;
        # otherwise retrieve channel names for selected logger and add to combo box
        i = self.logger_i - 1
        if i > -1:
            channels = self.datasets[i].channels
            self.channelCombo.addItems(channels)

    def update_plot(self):
        """Update selected subplot for selected axes (primary or secondary)."""

        if self.skip_plotting is True:
            return
        print('Updating plot!')

        i = self.plot_i
        subplot = self.subplots[i]

        # Plot on the primary axes
        if self.axis_i == 0:
            # Set plot data for selected subplot primary axes
            subplot.set_ax1_plot_data(datasets=self.datasets,
                                      logger_i=self.logger_i,
                                      channel_name=self.channel_name,
                                      stat=self.stat)

            # Create combined stats plot
            if self.stat == 'Combined':
                subplot.create_compound_plot(self.num_plots)
            else:
                # Plot the data
                subplot.plot_on_axes(axes=0, num_plots=self.num_plots)

            # Check if no data was plotted on primary axes but the secondary axes is in use.
            # If so then need to replot the secondary axes data due to ax2 being twinned to ax1 but ax1 was cleared,
            # screwing up ax2
            if subplot.ax1_in_use is False and subplot.ax2_in_use is True:
                subplot.plot_on_axes(axes=0, num_plots=self.num_plots)
        # Plot on the secondary axes
        else:
            # Set plot data for selected subplot secondary axes
            subplot.set_ax2_plot_data(datasets=self.datasets,
                                      logger_i=self.logger_i,
                                      channel_name=self.channel_name,
                                      stat=self.stat)

            # Create combined stats plot
            if self.stat == 'Combined':
                subplot.create_compound_plot2(self.num_plots)
            else:
                # Plot the data
                subplot.plot_on_axes(axes=1, num_plots=self.num_plots)

        # Format plot
        self._format_plot()
        self._set_yaxes_and_gridlines(subplot)
        self._add_subplot_legend(subplot)
        self._adjust_fig_layout()
        self.canvas.draw()

    def _plot_all_stored_data(self):
        """Plot all axes that have stored plot data."""

        data_plotted = False

        for subplot in self.subplots:
            # Check data exists
            if subplot.ax1_in_use is True:
                subplot.plot_on_axes(axes=0, num_plots=self.num_plots)
                data_plotted = True
            if subplot.ax2_in_use is True:
                subplot.plot_on_axes(axes=1, num_plots=self.num_plots)
                data_plotted = True

        if data_plotted is True:
            self._format_plot()

            for subplot in self.subplots:
                self._set_yaxes_and_gridlines(subplot)
                self._add_subplot_legend(subplot)

            self._adjust_fig_layout()
        else:
            self.fig.tight_layout()

        self.canvas.draw()

    def _format_plot(self):
        """Format plot routines."""

        # self._add_figure_legend()
        self._set_xaxis()
        self._set_title()

    def _set_title(self):
        """Set main plot title."""

        # Attempt to retrieve title from project setup dashboard
        project_name = self.parent.projConfigModule.control.project_name
        campaign_name = self.parent.projConfigModule.control.campaign_name

        if project_name == '':
            project_name = 'Project Title'
        if campaign_name == '':
            campaign_name = 'Campaign Title'

        title = f'{project_name}\n{campaign_name}'
        self.fig.suptitle(title, **title_args)

    def _set_yaxes_and_gridlines(self, subplot):
        """Modify y-axes and gridlines shown."""

        ax1 = subplot.ax1
        ax2 = subplot.ax2

        if subplot.ax1_in_use is False and subplot.ax2_in_use is True:
            ax1.yaxis.set_visible(False)
            ax2.yaxis.set_visible(True)
            ax1.grid(False, axis='y')
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

    def _set_xaxis(self, date_fmt='%d-%b-%y', day_interval=7):
        """Set x-axis format."""

        ax = self.subplots[0].ax1
        days = mdates.DayLocator(interval=day_interval)
        fmt = mdates.DateFormatter(date_fmt)
        # fmt = mdates.DateFormatter('%Y-%b-%d %H:%M')
        ax.xaxis.set_major_locator(days)
        ax.xaxis.set_major_formatter(fmt)
        self.fig.autofmt_xdate()

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

    def _add_figure_legend(self):
        """Add legend to bottom of figure."""

        if self.fig.legends:
            self.fig.legends = []

        self.fig.legend(
            loc='lower center',
            ncol=4,
            fontsize=11,
        )

    def _add_subplot_legend(self, subplot):
        """
        Add legend to subplot.
        Creates list of line objects contained in both axes, then gets label for each line and creates legend.
        """

        lines = subplot.handles_1 + subplot.handles_2
        labels = [l.get_label() for l in lines]
        subplot.ax1.legend(
            lines,
            labels,
            loc='upper right',
            ncol=4,
            fontsize=9,
        )

    def _adjust_fig_layout(self):
        """Size plots so that it doesn't overlap suptitle and legend."""

        self.fig.tight_layout(rect=[0, 0, 1, .92])  # (rect=[left, bottom, right, top])
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
        self.project = '21239 Total WoS - Glendronach Well Monitoring Campaign'
        self.motions = ''
        self.title = ''
        self.plot_data = {}

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
        # Main layout
        layout = QtWidgets.QHBoxLayout(self)

        # Selection layout
        selection = QtWidgets.QWidget()
        selection.setFixedWidth(160)
        vbox = QtWidgets.QVBoxLayout(selection)

        self.loadStats = QtWidgets.QPushButton('Load Statistics')
        self.clearDatasets = QtWidgets.QPushButton('Clear Datasets')
        lbl1 = QtWidgets.QLabel('Loaded Datasets')
        lbl2 = QtWidgets.QLabel('Channels (echo)')
        self.datasetList = QtWidgets.QListWidget()
        self.channelsList = QtWidgets.QListWidget()
        self.vesselMotionsCombo = QtWidgets.QComboBox()
        self.stats1Combo = QtWidgets.QComboBox()
        self.stats2Combo = QtWidgets.QComboBox()
        self.plotSettings = QtWidgets.QPushButton('Plot Settings')
        self.replotButton = QtWidgets.QPushButton('Replot')

        # Plot drop-downs
        self.axis2Logger = QtWidgets.QComboBox()
        self.axis2Channel = QtWidgets.QComboBox()

        # Primary axis controls
        statsWidget = QtWidgets.QGroupBox('Primary Axis')
        vbox1 = QtWidgets.QVBoxLayout(statsWidget)
        vbox1.addWidget(QtWidgets.QLabel('Motions:'))
        vbox1.addWidget(self.vesselMotionsCombo)
        vbox1.addWidget(QtWidgets.QLabel('Statistic:'))
        vbox1.addWidget(self.stats1Combo)

        # Secondary axis controls
        axis2Group = QtWidgets.QGroupBox('Secondary Axis')
        vbox2 = QtWidgets.QVBoxLayout(axis2Group)
        vbox2.addWidget(QtWidgets.QLabel('Logger:'))
        vbox2.addWidget(self.axis2Logger)
        vbox2.addWidget(QtWidgets.QLabel('Channel:'))
        vbox2.addWidget(self.axis2Channel)
        vbox2.addWidget(QtWidgets.QLabel('Statistic:'))
        vbox2.addWidget(self.stats2Combo)

        # Combine selection widgets
        vbox.addWidget(self.loadStats)
        vbox.addWidget(self.clearDatasets)
        vbox.addWidget(lbl1)
        vbox.addWidget(self.datasetList)
        vbox.addWidget(lbl2)
        vbox.addWidget(self.channelsList)
        vbox.addWidget(statsWidget)
        vbox.addWidget(axis2Group)
        vbox.addWidget(self.plotSettings)
        vbox.addWidget(self.replotButton)

        # Plot layout
        plot = QtWidgets.QWidget()
        plotLayout = QtWidgets.QVBoxLayout(plot)

        # Create plot figure, canvas widget to display figure and navbar
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        plotLayout.addWidget(navbar)
        plotLayout.addWidget(self.canvas)

        # Add widgets to main layout
        layout.addWidget(selection)
        layout.addWidget(plot)

    def connect_signals(self):
        # self.loadStats.clicked.connect(self.parent.load_stats_file)
        self.clearDatasets.clicked.connect(self.clear_datasets)
        self.datasetList.currentItemChanged.connect(self.on_datasetList_change)
        self.vesselMotionsCombo.currentIndexChanged.connect(self.on_motions_combo_change)
        self.stats1Combo.currentIndexChanged.connect(self.on_stats1_combo_change)
        self.axis2Logger.currentIndexChanged.connect(self.on_axis2logger_combo_change)
        self.stats2Combo.currentIndexChanged.connect(self.on_stats2_combo_change)
        self.replotButton.clicked.connect(self.replot)

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
        self.axis2Logger.addItem('None')
        self.axis2Channel.clear()
        self.axis2Channel.addItem('None')

    def clear_datasets(self):
        """Clear all stored spectrogram datasets and reset layout."""

        # Set flag to prevent channel combos repopulating when clear the dataset combos
        self.skip_logger_combo_change = True

        self.datasets = []
        self.datasetList.clear()
        self.channelsList.clear()
        self.init_logger_channel_combos()
        self.skip_logger_combo_change = False

    def on_datasetList_change(self):
        self.update_channels_list()

    def on_axis2logger_combo_change(self):
        if self.skip_plot is False:
            self.update_channels_combo()

    def on_motions_combo_change(self):
        """Update plots for selected vessel motions."""

        if self.datasets:
            self.set_plot_data()
            self.update_plots()

    def on_stats1_combo_change(self):
        """Update vessel motion plots for selected statistic."""

        if self.datasets:
            self.set_plot_data()
            self.update_plots()

    def on_stats2_combo_change(self):
        """Update secondary axis plots for selected statistic."""

        if self.datasets:
            self.set_plot_data()
            self.update_plots()

    def replot(self):
        """Replot stats."""

        if self.datasets:
            self.set_plot_data()
            self.update_plots()

    def update_stats_datasets_list(self, dataset_ids):
        """Populate loaded datasets list."""

        # Create dataset list and select first item (this will trigger an update of update_channels_list)
        self.datasetList.addItems(dataset_ids)

        # Add dataset ids to logger combo box
        self.axis2Logger.addItems(dataset_ids)
        self.datasetList.setCurrentRow(0)

    def update_channels_list(self):
        """Update channels list to match selected dataset."""

        i = self.datasetList.currentRow()
        if i == -1:
            return

        # Add channels to list and make unselectable since they are just an echo for reference
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
        if dataset_id == 'None':
            self.axis2Channel.clear()
            self.axis2Channel.addItem('None')
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
            if 'SigWaveHeight' in self.datasets[0].channels:
                self.axis2Channel.setCurrentText('SigWaveHeight')
                self.stats2Combo.setCurrentText('Mean')

        # Selected motions and statistic to get data for
        self.motions = self.vesselMotionsCombo.currentText()

        if self.motions == 'Surge/Sway/Heave':
            motion_cols = vessel_trans
        else:
            motion_cols = vessel_rots

        self.stat1 = self.stats1Combo.currentText()
        self.stat2 = self.stats2Combo.currentText()
        stat1_col = dict_stats[self.stat1]
        stat2_col = dict_stats[self.stat2]

        # Plot title
        if self.stat1 == 'Std. Dev.':
            stat = 'Standard Deviation'
        else:
            stat = self.stat1

        self.title = f'{self.project}\n{stat} Vessel Accelerations'

        # Dictionary to hold plot vessel motions data frame and axis 2 channel data frame, label and units
        plot_data = {}

        # Get axis 1 plot data
        # Get vessel motions data from vessel data frame - it is required that the vessel dataset is called "VESSEL"
        for i in range(len(self.datasets)):
            if self.datasets[i].logger_id == 'VESSEL':
                df_vessel = self.datasets[i].df
                df_vessel = df_vessel.xs(key=stat1_col, axis=1, level=1)
                df_vessel = df_vessel[motion_cols]
                plot_data['vessel_data'] = df_vessel
                break

        # Selected logger info
        logger_i = self.axis2Logger.currentIndex() - 1
        channel = self.axis2Channel.currentText()

        if channel == '':
            channel = 'None'

        # Get axis 2 plot data
        if logger_i > -1 and channel != 'None':
            # Retrieve data frame from dataset objects list
            df_axis2 = self.datasets[logger_i].df
            logger_id = self.datasets[logger_i].logger_id

            # Slice data frame for the selected statistic and then select channel
            df_axis2 = df_axis2.xs(key=stat2_col, axis=1, level=1)
            df_axis2 = df_axis2[channel]
            units = df_axis2.columns[0]

            # Create legend label and y-axis label
            label = self.create_legend_label(self.stat2, logger_id, channel)
            ylabel = self.create_ylabel(channel, units)

            # Store vessel data from and channel data and info to dictionary
            plot_data['axis2_data'] = df_axis2
            plot_data['channel'] = channel
            plot_data['label'] = label
            plot_data['ylabel'] = ylabel
            plot_data['units'] = units

        self.plot_data = plot_data

    def create_legend_label(self, stat, logger_id, channel):
        """Construct legend label based on plotted stat, logger id and channel."""

        # Check for a preferred channel name to use
        if channel in dict_labels:
            channel = dict_labels[channel]

        # # Construct label - prepend logger name unless channel source is the vessel (which would be superfluous)
        if logger_id != 'VESSEL':
            label = ' '.join((stat, logger_id, channel))
        else:
            label = ' '.join((stat, channel))

        return label

    def create_ylabel(self, channel, units):
        """Construct y axis label based on plotted channel and units."""

        # Check for a preferred channel name to use
        if channel in dict_ylabels:
            channel = dict_ylabels[channel]

        # Construct label
        ylabel = f'{channel} ($\mathregular{{{units}}}$)'

        return ylabel

    def update_plots(self):
        """Update stats plots."""

        self.draw_axes()

        # Flags to check which axes are plotted to modify gridlines shown
        plot = False
        linewidth = 1
        self.fig.suptitle(self.title)

        # Plot vessel motions
        if 'vessel_data' in self.plot_data:
            df_vessel = self.plot_data['vessel_data']
            col = df_vessel.columns[0]
            motion = col[0][3:]
            units = col[1]
            self.ax1.plot(df_vessel[col], 'r', lw=linewidth, label=motion + ' Acceleration')
            label = f'{motion} ($\mathregular{{{units}}}$)'
            self.ax1.set_ylabel(label)

            col = df_vessel.columns[1]
            motion = col[0][3:]
            units = col[1]
            self.ax2.plot(df_vessel[col], 'g', lw=linewidth, label=motion + ' Acceleration')
            label = f'{motion} ($\mathregular{{{units}}}$)'
            self.ax2.set_ylabel(label)

            col = df_vessel.columns[2]
            motion = col[0][3:]
            units = col[1]
            self.ax3.plot(df_vessel[col], 'purple', lw=linewidth, label=motion + ' Acceleration')
            label = f'{motion} ($\mathregular{{{units}}}$)'
            self.ax3.set_ylabel(label)
            plot = True

        # Plot secondary axis channel
        if 'axis2_data' in self.plot_data:
            df = self.plot_data['axis2_data']
            label = self.plot_data['label']
            ylabel = self.plot_data['ylabel']

            self.ax1b.yaxis.set_visible(True)
            self.ax2b.yaxis.set_visible(True)
            self.ax3b.yaxis.set_visible(True)
            self.ax1b.plot(df, c='dodgerblue', lw=linewidth, label=label)
            self.ax2b.plot(df, c='dodgerblue', lw=linewidth)
            self.ax3b.plot(df, c='dodgerblue', lw=linewidth)
            self.ax2b.set_ylabel(ylabel)
            self.ax1b.set_ylabel(ylabel)
            self.ax3b.set_ylabel(ylabel)
            plot = True

        # Complete plot if at least one channel was plotted
        if plot is True:
            self.ax1.margins(x=0, y=0)
            self.ax1b.margins(x=0, y=0)
            self.ax2.margins(x=0, y=0)
            self.ax2b.margins(x=0, y=0)
            self.ax3.margins(x=0, y=0)
            self.ax3b.margins(x=0, y=0)

            days = mdates.DayLocator(interval=7)
            fmt = mdates.DateFormatter('%d-%b-%y')
            self.ax3.xaxis.set_major_locator(days)
            self.ax3.xaxis.set_major_formatter(fmt)

            self.fig.autofmt_xdate()
            self.fig.legend(loc='lower center',
                            ncol=4,
                            fontsize=11,
                            )
            # Ensure plots don't overlap suptitle and legend
            self.fig.tight_layout(rect=[0, .05, 1, .9])  # (rect=[left, bottom, right, top])

        self.canvas.draw()


class VarianceWidget(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()

        self.logger_names = []
        self.datasets = {}

        # Create plot figure, canvas widget to display figure and navbar
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.draw()
        navbar = NavigationToolbar(self.canvas, self)

        # Main layout
        layout = QtWidgets.QHBoxLayout(self)

        # Plot layout
        plot = QtWidgets.QWidget()
        plot_layout = QtWidgets.QVBoxLayout()
        plot.setLayout(plot_layout)
        plot_layout.addWidget(navbar)
        plot_layout.addWidget(self.canvas)

        # Selection layout
        selection = QtWidgets.QWidget()
        selection.setFixedWidth(150)
        vbox = QtWidgets.QVBoxLayout(selection)

        lbl1 = QtWidgets.QLabel('Channel:')
        self.channelsCombo = QtWidgets.QComboBox()
        self.channelsCombo.addItems(variance_channels_combo)
        lbl2 = QtWidgets.QLabel('Loaded Datasets')
        self.datasetList = QtWidgets.QListWidget()

        vbox.addWidget(lbl1)
        vbox.addWidget(self.channelsCombo)
        vbox.addWidget(lbl2)
        vbox.addWidget(self.datasetList)

        layout.addWidget(selection)
        layout.addWidget(plot)

        self.connect_signals()

    def connect_signals(self):
        self.channelsCombo.currentIndexChanged.connect(self.update_variance_plot)
        self.datasetList.currentItemChanged.connect(self.update_variance_plot)

    def update_variance_datasets_list(self, dataset_names):
        """Populate loaded datasets list."""

        # Create active channels flag lists
        self.logger_names = dataset_names

        # Repopulate datasets list
        self.datasetList.clear()
        [self.datasetList.addItem(x) for x in dataset_names]
        self.datasetList.setCurrentRow(0)

    def update_variance_plot(self, init_plot=False):
        """Plot stats mean, range and std variability."""

        self.ax.cla()

        # For some reason when processing stats, update of variance plot is not triggered by change in dataset list item
        # Therefore force plotting of first dataset in list
        if init_plot:
            if self.datasetList.count() > 0:
                logger = self.datasetList.item(0).text()
            else:
                return
        # Get dataset list index; quit routine if list is empty
        else:
            logger_i = self.datasetList.currentRow()
            if logger_i == -1:
                return

            logger = self.datasetList.currentItem().text()

        channel_i = self.channelsCombo.currentIndex()
        channel = self.channelsCombo.currentText()
        # title = '21148 Total Glenlivet G1 Well Monitoring Campaign\n' + logger + ' ' + channel
        title = '21239 Total WoS - Glendronach Well Monitoring Campaign\n' + logger + ' ' + channel
        df = self.datasets[logger]
        cols = [4 * channel_i + i for i in range(4)]

        min = df.iloc[:, cols[0]]
        max = df.iloc[:, cols[1]]
        mean = df.iloc[:, cols[2]]
        std = df.iloc[:, cols[3]]
        self.ax.plot(mean)
        self.ax.fill_between(df.index, min, max, alpha=0.2)
        self.ax.fill_between(df.index, mean - std, mean + std, alpha=0.2, facecolor='r')
        # self.ax.errorbar(x=df.index, y=mean, yerr=std, fmt='o', ecolor='gray', linewidth=1)
        self.ax.legend(['Mean', 'Range', 'Standard deviation'])

        # Determine y label
        if channel_i < 2:
            ylabel = stat_ylabels[0]
        else:
            ylabel = stat_ylabels[1]

        self.ax.set_xlabel('Timestamp')
        self.ax.set_ylabel(ylabel)
        self.ax.set_title(title)
        self.ax.margins(x=0, y=0)
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b-%y %H:%M'))
        self.fig.autofmt_xdate()
        # self.fig.tight_layout()
        # self.ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
        # self.ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        # self.ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=10))
        # self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y:%m:%d'))

        self.canvas.draw()


class PlotStyle2H:
    def __init__(self, canvas, fig):
        self.canvas = canvas
        self.fig = fig
        self.logo_path = r'images\2H_logo.emf'

        # "2H blue"
        color_2H = np.array([0, 49, 80]) / 255

        # self.generalFont = {'family': 'sans-serif',
        #                     'sans-serif': ['Tahoma'],
        #                     'size': 13}
        # plt.rc('font', **self.generalFont)

        self.title1_props = {  # 'fontname': 'Tahoma',
            'fontsize': 14,
            'color': color_2H,
            'weight': 'bold',
            'ha': 'center',
            'va': 'center'}

        self.title2_props = {  # 'fontname': 'Tahoma',
            'fontsize': 16,
            'color': color_2H,
            'weight': 'bold',
            'ha': 'center',
            'va': 'center'}

        self.axis_props = {'weight': 'bold',
                           'fontsize': 13}

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
        ax.set_title('')
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

        leg = self.fig.legend(loc='lower center', ncol=4, frameon=True, fancybox=False, edgecolor='none',
                              facecolor='none')

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
if __name__ == '__main__':
    np.random.seed(0)
    app = QtWidgets.QApplication(sys.argv)

    # Create dummy dataset
    start_dates = ['2017-03-10 00:00:00',
                   '2017-03-10 00:10:00',
                   '2017-03-10 00:20:00']

    start_dates = [datetime.strptime(t, '%Y-%m-%d %H:%M:%S') for t in start_dates]

    data = [[j + i * 10 for j in range(16)] for i in range(3)]
    data = np.random.randn(3, 4)
    df = pd.DataFrame(data=data, index=start_dates)
    dataset = StatsDataset(logger_id='test', df=df)
    dataset_names = ['test']

    w = StatsWidget()
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
