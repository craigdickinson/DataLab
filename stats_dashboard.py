import sys
import logging
from datetime import datetime
import math

import PIL
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib import cm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib import gridspec
from datetime import timedelta

# To resolve a pandas warning in using timestamps with matplotlib - to investigate
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()

# from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap
# from matplotlib.patches import Rectangle
# from matplotlib.ticker import MaxNLocator
# from matplotlib.font_manager import findfont, FontProperties
# import colormap as cmaps

stat_ylabels = ['Acceleration ($\mathregular{m/s^2}$)',
                'Angular Rate ($\mathregular{deg/s}$)',
                ]

variance_channels_combo = ['Acceleration X',
                           'Acceleration Y',
                           'Angular Rate X',
                           'Angular Rate Y',
                           ]

# Dictionary of stats combo items and stats file column name pairs
dict_stats = {'Minimum': 'min',
              'Maximum': 'max',
              'Mean': 'mean',
              'Std. Dev.': 'std',
              }

motion_types = ['Surge/Sway/Heave',
                'Roll/Pitch/Yaw',
                ]

vessel_trans = ['AccSurge',
                'AccSway',
                'AccHeave',
                ]

vessel_rots = ['AccRoll',
               'AccPitch',
               'AccYaw',
               ]

labels_dict = {'SigWaveHeight': 'Significant Wave Height',
               'SigWavePeriod': 'Significant Wave Period',
               }

ylabels_dict = {'SigWaveHeight': 'Hs',
                'SigWavePeriod': 'Tp',
                }


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
        """
        Get plot data for a given logger and channel
        :param logger_combo: Logger drop-down widget
        :param channel_combo: Channel drop-down widget
        :param stat_col: statistic column name to slice on
        :return: DataFrame of plot data for a given axis
        """

        self.df = pd.DataFrame()
        self.channel = ''
        self.label = ''
        self.units = ''

    def set_plot_data(self, datasets, logger_combo, channel_combo, stat_col):
        # Selected logger info
        logger_i = logger_combo.currentIndex() - 1
        channel = channel_combo.currentText()

        # TODO: When processing we get a channel = '' bug
        if channel == '':
            channel = 'None'

        # If selected logger is not "None"
        if logger_i > -1 and channel != 'None':
            # Retrieve data frame from dataset objects list
            df = datasets[logger_i].df
            logger_id = datasets[logger_i].logger_id

            # Slice data frame for the selected statistic and then on channel
            df = df.xs(key=stat_col, axis=1, level=1)
            df = df[channel]
            units = df.columns[0]
            label = ' '.join((logger_id, channel))

            # Store data and info to dictionary
            self.df = df
            self.channel = channel
            self.label = label
            self.units = units


class StatsWidget(QtWidgets.QWidget):
    """Summary stats plot widget class."""

    def __init__(self, parent=None):
        super(StatsWidget, self).__init__(parent)

        # So can access parent class
        self.parent = parent
        plt.style.use('seaborn')

        # Skip routine flags; used to prevent unnecessary multiple calls to update plot routines
        self.skip_logger_combo_change = False
        self.skip_set_radios = False
        self.skip_radio_changed = False
        self.skip_update_plot = False

        self.num_plots = 1
        self.plot_num = 1
        self.axis = 1

        # List to hold subplot axes
        self.axes = []
        self.sec_axes = []

        # Plot data and settings
        self.project = '21239 Total WoS - Glendronach Well Monitoring Campaign'
        self.stat = ''
        self.plot_data = [PlotData()]

        # Container for StatsDataset objects
        self.datasets = []
        self.ylabel = stat_ylabels[0]

        # Set up layout
        self._init_ui()
        self._connect_signals()
        self._create_subplots()
        self.canvas.draw()

        # Add stats options and initialise to stdev
        self.skip_plot = True
        self._init_logger_channel_combos()
        self.skip_plot = False

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
        self.channelsList = QtWidgets.QListWidget()

        # Number of plots
        self.numPlotsSpinBox = QtWidgets.QSpinBox()
        self.numPlotsSpinBox.setFixedWidth(40)
        self.numPlotsSpinBox.setMinimum(1)
        self.numPlotsSpinBox.setMaximum(4)
        self.numPlotsContainer = QtWidgets.QWidget()
        self.numPlotsForm = QtWidgets.QFormLayout(self.numPlotsContainer)
        self.numPlotsForm.addRow(QtWidgets.QLabel('Number of plots:'), self.numPlotsSpinBox)

        # Plot data selection
        self.plotNumCombo = QtWidgets.QComboBox()
        self.plotNumCombo.setFixedWidth(40)
        plot_nums = self._get_plot_numbers_list(self.num_plots)
        self.plotNumCombo.addItems(plot_nums)
        self.axisCombo = QtWidgets.QComboBox()
        self.axisCombo.setFixedWidth(40)
        self.axisCombo.addItems(['1', '2'])
        self.loggerCombo = QtWidgets.QComboBox()
        self.channelCombo = QtWidgets.QComboBox()
        self.statCombo = QtWidgets.QComboBox()
        self.statCombo.addItems(dict_stats.keys())
        self.statCombo.setCurrentIndex(3)

        self.plotGroup = QtWidgets.QGroupBox('Select Plot Data')
        self.form = QtWidgets.QFormLayout(self.plotGroup)
        self.form.addRow(QtWidgets.QLabel('Plot:'), self.plotNumCombo)
        self.form.addRow(QtWidgets.QLabel('Axis:'), self.axisCombo)
        self.form.addRow(QtWidgets.QLabel('Logger:'), self.loggerCombo)
        self.form.addRow(QtWidgets.QLabel('Channel:'), self.channelCombo)
        self.form.addRow(QtWidgets.QLabel('Stat:'), self.statCombo)

        # Plot settings button
        self.settingsButton = QtWidgets.QPushButton('Plot Settings')
        self.replotButton = QtWidgets.QPushButton('Replot')

        # Combine selection widgets
        self.vbox = QtWidgets.QVBoxLayout(self.selectionContainer)
        self.vbox.addWidget(self.loadStatsButton)
        self.vbox.addWidget(self.clearDatasetsButton)
        self.vbox.addWidget(QtWidgets.QLabel('Loaded Datasets'))
        self.vbox.addWidget(self.datasetList)
        self.vbox.addWidget(QtWidgets.QLabel('Channels (echo)'))
        self.vbox.addWidget(self.channelsList)
        self.vbox.addWidget(self.numPlotsContainer)
        self.vbox.addWidget(self.plotGroup)
        self.vbox.addWidget(self.settingsButton)
        self.vbox.addWidget(self.replotButton)

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

    def _connect_signals(self):
        self.clearDatasetsButton.clicked.connect(self.clear_datasets)
        self.datasetList.currentItemChanged.connect(self.on_dataset_list_item_changed)
        self.numPlotsSpinBox.valueChanged.connect(self.on_spin_box_value_changed)
        self.plotNumCombo.currentIndexChanged.connect(self.on_plot_num_combo_changed)
        self.axisCombo.currentIndexChanged.connect(self.on_axis_combo_changed)
        self.loggerCombo.currentIndexChanged.connect(self.on_logger_combo_changed)
        self.channelCombo.currentIndexChanged.connect(self.on_channel_combo_changed)
        self.statCombo.currentIndexChanged.connect(self.on_stat_combo_changed)
        self.replotButton.clicked.connect(self.replot)

    @staticmethod
    def _get_plot_numbers_list(n):
        return list(map(str, range(1, n + 1)))

    def _create_subplots(self):
        """Clear figure canvas and initialise subplots."""

        self.fig.clf()

        # Create first subplot
        ax1 = self.fig.add_subplot(self.num_plots, 1, 1)
        # self.axes.append(self.fig.add_subplot(self.num_plots, 1, 1))

        # Create remaining subplots with a shared x-axis to ax1 then prepend ax1 to axes list
        self.axes = [self.fig.add_subplot(self.num_plots, 1, i + 1, sharex=ax1) for i in range(1, self.num_plots)]
        self.axes.insert(0, ax1)

        # Create secondary axes list and set properties
        # self.sec_axes = [ax.twinx() for ax in self.axes]
        # for ax in self.sec_axes:
        #     ax.yaxis.set_visible(False)
        #     ax.grid(False)

    def _update_plot_combo(self):
        """Update select plot drop-down."""

        i = self.plotNumCombo.currentIndex()

        self.plotNumCombo.clear()
        plot_nums = self._get_plot_numbers_list(self.num_plots)
        self.plotNumCombo.addItems(plot_nums)

        # Attempt to retain previously selected plot number, otherwise select plot 1
        if i < self.plotNumCombo.count():
            self.plotNumCombo.setCurrentIndex(i)
        else:
            self.plotNumCombo.setCurrentIndex(0)

    def _update_plot_containers(self):
        """Adds or removes PlotData objects from plot_data list to equal number of subplots."""

        n = self.num_plots
        m = len(self.plot_data)

        if n > m:
            for i in range(n - m):
                self.plot_data.append(PlotData())
        elif n < m:
            for i in range(m - n):
                del self.plot_data[-1]

    def _init_logger_channel_combos(self):
        """Reset logger and channel drop-downs."""

        self.loggerCombo.clear()
        self.loggerCombo.addItem('None')
        self.channelCombo.clear()
        self.channelCombo.addItem('None')

    def clear_datasets(self):
        """Clear all stored spectrogram datasets and reset layout."""

        # Set flag to prevent channel combos repopulating when clear the dataset combos
        self.skip_logger_combo_change = True

        self.datasets = []
        self.datasetList.clear()
        self.channelsList.clear()
        self._init_logger_channel_combos()

        self.skip_logger_combo_change = False

    def on_dataset_list_item_changed(self):
        self._update_channels_list()

    def on_spin_box_value_changed(self):
        self.num_plots = self.numPlotsSpinBox.value()
        self._update_plot_combo()
        self._create_subplots()
        self._update_plot_containers()
        self.canvas.draw()

    def on_plot_num_combo_changed(self):
        self.plot_num = self.plotNumCombo.currentIndex()

    def on_axis_combo_changed(self):
        pass

    def on_logger_combo_changed(self):
        if self.skip_plot is False:
            self._update_channel_combos(logger_combo=self.loggerCombo, channel_combo=self.channelCombo)

    def on_channel_combo_changed(self):
        pass

    def on_stat_combo_changed(self):
        """Update primary axis plots for selected statistic if datasets have been loaded"""

        if self.datasets:
            self.set_plot_data()
            self.update_plots()

    def replot(self):
        """Replot stats."""

        if self.datasets:
            self.set_plot_data()
            self.update_plots()

    def update_datasets_list(self, dataset_ids):
        """Populate loaded datasets list."""

        # Create dataset list and select first item (this will trigger an update of update_channels_list)
        self.datasetList.addItems(dataset_ids)

        # Add dataset ids to logger combo box
        self.loggerCombo.addItems(dataset_ids)

        self.datasetList.setCurrentRow(0)

    def _update_channels_list(self):
        """Update channels list to match selected dataset."""

        i = self.datasetList.currentRow()
        if i == -1:
            return

        # Add channels to list and make non-selectable since they are just an echo for reference
        self.channelsList.clear()
        for channel in self.datasets[i].channels:
            item = QtWidgets.QListWidgetItem(channel)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
            self.channelsList.addItem(item)

    def _update_channel_combos(self, logger_combo, channel_combo):
        """Update channel drop-down to pertain to the selected logger."""

        if self.skip_logger_combo_change is True:
            return

        dataset_id = logger_combo.currentText()

        # If no dataset is selected, re-initialise the channel drop-down
        if dataset_id == 'None':
            channel_combo.clear()
            channel_combo.addItem('None')
        else:
            # Retrieve channel names for selected dataset_id
            i = logger_combo.currentIndex() - 1
            channels = self.datasets[i].channels

            # Add channels to respective channel combo
            channel_combo.clear()
            channel_combo.addItems(channels)

    def set_plot_data(self, init=False):
        """Assign plot data for each axis based on respective selected logger and channel drop-downs."""

        # If flag is set it means no datasets were previously loaded; therefore set drop-downs to presets
        # to create an initial plot
        if init is True:
            self.loggerCombo.setCurrentIndex(1)
            self.channelCombo.setCurrentIndex(0)

        # Selected statistic info
        self.stat = self.statCombo.currentText()
        stat_col = dict_stats[self.stat]

        # Plot number
        i = self.plot_num

        self.plot_data[i - 1].set_plot_data(datasets=self.datasets,
                                            logger_combo=self.loggerCombo,
                                            channel_combo=self.channelCombo,
                                            stat_col=stat_col)

        # self.plot_data = self._get_axes_plot_data(logger_combo=self.loggerCombo,
        #                                           channel_combo=self.channelCombo,
        #                                           stat_col=stat_col)

    def _get_axes_plot_data(self, logger_combo, channel_combo, stat_col):
        """
        Get plot data for a given logger and channel
        :param logger_combo: Logger drop-down widget
        :param channel_combo: Channel drop-down widget
        :param stat_col: statistic column name to slice on
        :return: DataFrame of plot data for a given axis
        """

        # Dictionary to hold plot data frame, label and units
        plot_data = {}

        # Selected logger info
        logger_i = logger_combo.currentIndex() - 1
        channel = channel_combo.currentText()

        # TODO: When processing we get a channel = '' bug
        print(f'channel={channel}')
        if channel == '':
            channel = 'None'

        # If selected logger is not "None"
        if logger_i > -1 and channel != 'None':
            # Retrieve data frame from dataset objects list
            df = self.datasets[logger_i].df
            logger_id = self.datasets[logger_i].logger_id

            # Slice data frame for the selected statistic and then on channel
            df = df.xs(key=stat_col, axis=1, level=1)
            df = df[channel]
            units = df.columns[0]
            label = ' '.join((logger_id, channel))

            # Store data and info to dictionary
            plot_data['df'] = df
            plot_data['channel'] = channel
            plot_data['label'] = label
            plot_data['units'] = units

        return plot_data

    def update_plots(self):
        """Update stats plots."""

        self.update_subplot(self.axes[0])
        self.canvas.draw()

    def update_subplot(self, ax):

        # self._create_subplots()

        # Check that all loggers drop-down are not set to "None"!
        logger = self.loggerCombo.currentText()

        if logger == 'None':
            self.fig.tight_layout()
            self.canvas.draw()
            return

        # Flags to check which axes are plotted to modify gridlines shown
        plot = False
        plot_on_ax1 = False
        plot_on_ax2 = False
        linewidth = 1

        if self.stat == 'Std. Dev.':
            title = f'{self.project}\nStandard Deviation'
        else:
            title = f'{self.project}\n{self.stat}'

        self.fig.suptitle(title)

        # Plot 1 - axis 1
        if self.plot_data:
            df = self.plot_data[0].df
            label = self.plot_data[0].label
            channel = self.plot_data[0].channel
            units = self.plot_data[0].units
            ax.plot(df, c='dodgerblue', lw=linewidth, label=label)
            ax.set_ylabel(f'{channel} ($\mathregular{{{units}}}$)')
            plot = True
            plot_on_ax1 = True
        else:
            ax.yaxis.set_visible(False)

    def update_gridlines(self):
        # Modify gridlines shown
        if plot_on_ax1 is False and plot_on_ax2 is True:
            self.ax1.grid(False, axis='y')
            self.ax1b.grid(True)

    def set_xaxis(self, ax):

        days = mdates.DayLocator(interval=7)
        fmt = mdates.DateFormatter('%d-%b-%y')
        # fmt = mdates.DateFormatter('%Y-%b-%d %H:%M')

        # TODO: Bit of a fudge for now - x axis formatting
        if len(df) > 1000:
            ax.xaxis.set_major_locator(days)
            ax.xaxis.set_major_formatter(fmt)

        self.fig.autofmt_xdate()

    def plot_unlatched_period(self):
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

    def format_plot(self):

        self.ax1.margins(x=0, y=0)
        self.ax1b.margins(x=0, y=0)

        self.fig.legend(loc='lower center',
                        ncol=4,
                        fontsize=11,
                        )
        # Ensure plots don't overlap suptitle and legend
        self.fig.tight_layout(rect=[0, .05, 1, .9])  # (rect=[left, bottom, right, top])


class VesselStatsWidget(QtWidgets.QWidget):
    """Summary stats plot widget class."""

    def __init__(self, parent=None):
        super(VesselStatsWidget, self).__init__(parent)

        # So can access parent class
        self.parent = parent
        plt.style.use('seaborn')

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
        if channel in labels_dict:
            channel = labels_dict[channel]

        # # Construct label - prepend logger name unless channel source is the vessel (which would be superfluous)
        if logger_id != 'VESSEL':
            label = ' '.join((stat, logger_id, channel))
        else:
            label = ' '.join((stat, channel))

        return label

    def create_ylabel(self, channel, units):
        """Construct y axis label based on plotted channel and units."""

        # Check for a preferred channel name to use
        if channel in ylabels_dict:
            channel = ylabels_dict[channel]

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

    def update_variance_plot_upon_processing(self):
        """
        For some reason when processing stats, update of variance plot is not triggered by list connection.
        So execute this routine instead.
        Plot stats mean, range and std variability.
        NOT USED - DELETE...
        """

        self.ax.cla()

        channel_i = self.channelsCombo.currentIndex()
        channel = self.channelsCombo.currentText()
        logger = self.datasetList.item(0).text()
        title = '21148 Total Glenlivet G1 Well Monitoring Campaign\n' + logger + ' ' + channel
        df = self.datasets[logger]
        cols = [4 * channel_i + i for i in range(4)]

        # More complex plot if stat field equals first drop-down entry
        min = df.iloc[:, cols[0]]
        max = df.iloc[:, cols[1]]
        mean = df.iloc[:, cols[2]]
        std = df.iloc[:, cols[3]]
        self.ax.plot(mean)
        self.ax.fill_between(df.index, min, max, alpha=0.2)
        self.ax.fill_between(df.index, mean - std, mean + std, alpha=0.2, facecolor='r')
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
        self.fig.tight_layout()

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
    import sys

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
    w.update_plots()

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
