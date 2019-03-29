from datetime import datetime

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
stats_dict = {'Minimum': 'min',
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

        # self.plot_on_pri_axis = [False] * len(self.channels)
        # self.plot_on_sec_axis = [False] * len(self.channels)


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

        # Plot data and settings
        self.project = '21239 Total WoS - Glendronach Well Monitoring Campaign'
        self.stat1 = ''
        self.plot_data_1a = {}
        self.plot_data_1b = {}
        self.plot_data_2a = {}
        self.plot_data_2b = {}

        # Container for StatsDataset objects
        self.datasets = []
        self.ylabel = stat_ylabels[0]

        # Set up layout
        self.init_ui()
        self.connect_signals()
        self.draw_axes()
        self.canvas.draw()

        # Add stats options and initialise to stdev - don't do this in layout creation to keep it separate
        self.axis1StatsCombo.addItems(stats_dict.keys())
        self.axis1StatsCombo.setCurrentIndex(3)
        self.axis2StatsCombo.addItems(stats_dict.keys())
        self.axis2StatsCombo.setCurrentIndex(3)

        # Store logger and channel drop-down widgets in lists for convenience in later use
        self.logger_combos = [self.log1a,
                              self.log1b,
                              self.log2a,
                              self.log2b,
                              ]
        self.channel_combos = [self.ch1a,
                               self.ch1b,
                               self.ch2a,
                               self.ch2b,
                               ]

        self.skip_plot = True
        self.init_logger_channel_combos()
        self.skip_plot = False

    def init_ui(self):
        # Main layout
        layout = QtWidgets.QHBoxLayout(self)

        # Selection layout
        selection = QtWidgets.QWidget()
        selection.setFixedWidth(250)
        vbox = QtWidgets.QGridLayout(selection)
        # policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        # selection.setSizePolicy(policy)

        self.loadStats = QtWidgets.QPushButton('Load Statistics')
        self.clearDatasets = QtWidgets.QPushButton('Clear Datasets')
        lbl1 = QtWidgets.QLabel('Loaded Datasets')
        lbl2 = QtWidgets.QLabel('Channels (echo)')
        self.datasetList = QtWidgets.QListWidget()
        self.channelsList = QtWidgets.QListWidget()
        self.axis1StatsCombo = QtWidgets.QComboBox()
        self.axis2StatsCombo = QtWidgets.QComboBox()
        self.plotSettings = QtWidgets.QPushButton('Plot Settings')
        self.replotButton = QtWidgets.QPushButton('Replot')

        # Plot drop-downs
        self.log1a = QtWidgets.QComboBox()
        self.log1b = QtWidgets.QComboBox()
        self.log2a = QtWidgets.QComboBox()
        self.log2b = QtWidgets.QComboBox()
        self.ch1a = QtWidgets.QComboBox()
        self.ch1b = QtWidgets.QComboBox()
        self.ch2a = QtWidgets.QComboBox()
        self.ch2b = QtWidgets.QComboBox()

        plotGroup1 = QtWidgets.QGroupBox('Plot 1')
        grid = QtWidgets.QGridLayout(plotGroup1)
        grid.addWidget(QtWidgets.QLabel('Logger (Axis 1):'), 0, 0)
        grid.addWidget(self.log1a, 1, 0)
        grid.addWidget(QtWidgets.QLabel('Channel (Axis1):'), 0, 1)
        grid.addWidget(self.ch1a, 1, 1)
        grid.addWidget(QtWidgets.QLabel('Logger (Axis 2):'), 2, 0)
        grid.addWidget(self.log1b, 3, 0)
        grid.addWidget(QtWidgets.QLabel('Channel (Axis 2):'), 2, 1)
        grid.addWidget(self.ch1b, 3, 1)

        plotGroup2 = QtWidgets.QGroupBox('Plot 2')
        grid = QtWidgets.QGridLayout(plotGroup2)
        grid.addWidget(QtWidgets.QLabel('Logger (Axis 1):'), 0, 0)
        grid.addWidget(self.log2a, 1, 0)
        grid.addWidget(QtWidgets.QLabel('Channel (Axis 1):'), 0, 1)
        grid.addWidget(self.ch2a, 1, 1)
        grid.addWidget(QtWidgets.QLabel('Logger (Axis 2):'), 2, 0)
        grid.addWidget(self.log2b, 3, 0)
        grid.addWidget(QtWidgets.QLabel('Channel (Axis 2):'), 2, 1)
        grid.addWidget(self.ch2b, 3, 1)

        # Stats combo layout - place in a dummy widget for better alignment
        statsWidget = QtWidgets.QGroupBox('Statistic')
        grid = QtWidgets.QGridLayout(statsWidget)
        grid.addWidget(QtWidgets.QLabel('Primary Axis:'), 0, 0)
        grid.addWidget(self.axis1StatsCombo, 1, 0)
        grid.addWidget(QtWidgets.QLabel('Secondary Axis:'), 0, 1)
        grid.addWidget(self.axis2StatsCombo, 1, 1)

        # Combine selection widgets
        vbox.addWidget(self.loadStats, 0, 0)
        vbox.addWidget(self.clearDatasets, 0, 1)
        vbox.addWidget(lbl1, 1, 0)
        vbox.addWidget(lbl2, 1, 1)
        vbox.addWidget(self.datasetList, 2, 0)
        vbox.addWidget(self.channelsList, 2, 1)
        vbox.addWidget(plotGroup1, 3, 0, 1, 2)
        vbox.addWidget(plotGroup2, 4, 0, 1, 2)
        vbox.addWidget(statsWidget, 5, 0, 1, 2)
        vbox.addWidget(self.plotSettings, 6, 0)
        vbox.addWidget(self.replotButton, 6, 1)

        # # Toolbutton version testing
        # self.ch2Sec = QtWidgets.QToolButton()
        # self.ch2Sec.setFixedWidth(150)
        # self.ch2Sec.setText('Select Channel')
        # self.ch2Sec.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        #
        # channels = ['Accel X',
        #             'Accel Y',
        #             'Ang Rate X',
        #             'Ang Rate Y']
        # menu = QtWidgets.QMenu()
        # self.ch2Sec.setMenu(menu)
        # for c in channels:
        #     action = menu.addAction(c)
        #     action.setCheckable(True)
        #
        # for i, action in enumerate(self.ch2Sec.menu().actions()):
        #     if action.isChecked():
        #         print('f')

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
        self.loadStats.clicked.connect(self.parent.load_stats_file)
        self.clearDatasets.clicked.connect(self.clear_datasets)
        self.datasetList.currentItemChanged.connect(self.on_datasetList_change)
        self.log1a.currentIndexChanged.connect(self.on_logger1a_combo_change)
        self.log1b.currentIndexChanged.connect(self.on_logger1b_combo_change)
        self.log2a.currentIndexChanged.connect(self.on_logger2a_combo_change)
        self.log2b.currentIndexChanged.connect(self.on_logger2b_combo_change)
        self.axis1StatsCombo.currentIndexChanged.connect(self.on_stats1_combo_change)
        self.axis2StatsCombo.currentIndexChanged.connect(self.on_stats2_combo_change)
        self.replotButton.clicked.connect(self.replot)

    def draw_axes(self):
        """(Re)construct a blank figure workspace."""

        self.fig.clf()
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212, sharex=self.ax1)
        self.ax1b = self.ax1.twinx()
        self.ax2b = self.ax2.twinx()
        self.ax1b.yaxis.set_visible(False)
        self.ax2b.yaxis.set_visible(False)
        self.ax1b.grid(False)
        self.ax2b.grid(False)

    def init_logger_channel_combos(self):
        """Reset logger and channel drop-downs."""

        for logger_combo in self.logger_combos:
            logger_combo.clear()
            logger_combo.addItem('None')

        for channel_combo in self.channel_combos:
            channel_combo.clear()
            channel_combo.addItem('None')

    def clear_datasets(self):
        """Clear all stored spectrogram datasets and reset layout."""

        # Set flag to prevent channel combos repopulating when clear the dataset combos
        self.skip_logger_combo_change = True

        self.datasets = []
        self.datasetList.clear()
        self.channelsList.clear()
        self.init_logger_channel_combos()
        # self.draw_axes()
        # self.canvas.draw()

        self.skip_logger_combo_change = False

    def on_datasetList_change(self):
        self.update_channels_list()

    def on_logger1a_combo_change(self):
        if self.skip_plot is False:
            self.update_channel_combos(logger_combo=self.log1a, channel_combo=self.ch1a)

    def on_logger1b_combo_change(self):
        if self.skip_plot is False:
            self.update_channel_combos(logger_combo=self.log1b, channel_combo=self.ch1b)

    def on_logger2a_combo_change(self):
        if self.skip_plot is False:
            self.update_channel_combos(logger_combo=self.log2a, channel_combo=self.ch2a)

    def on_logger2b_combo_change(self):
        if self.skip_plot is False:
            self.update_channel_combos(logger_combo=self.log2b, channel_combo=self.ch2b)

    def on_stats1_combo_change(self):
        """Update primary axis plots for selected statistic if datasets have been loaded"""

        if self.datasets:
            self.set_plot_data()
            self.update_plots()

    def on_stats2_combo_change(self):
        """Update secondary axis plots for selected statistic if datasets have been loaded"""

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

        # Add dataset ids to logger combo boxes
        self.add_datasets_to_logger_combos(dataset_ids)
        self.datasetList.setCurrentRow(0)

    def add_datasets_to_logger_combos(self, dataset_ids):
        """Add new dataset names to the logger drop-downs."""

        for logger in self.logger_combos:
            logger.addItems(dataset_ids)

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

    def update_channel_combos(self, logger_combo, channel_combo):
        """Update the channel drop-down to reflect the respective logger drop-down selection."""

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
            self.log1a.setCurrentIndex(1)
            self.log1b.setCurrentIndex(1)
            self.log2b.setCurrentIndex(1)
            self.log2a.setCurrentIndex(1)
            self.ch1a.setCurrentIndex(0)
            self.ch1b.setCurrentIndex(1)
            self.ch2a.setCurrentIndex(2)
            self.ch2b.setCurrentIndex(3)

        # Selected statistic info
        self.stat1 = self.axis1StatsCombo.currentText()
        self.stat2 = self.axis2StatsCombo.currentText()
        stat1_col = stats_dict[self.stat1]
        stat2_col = stats_dict[self.stat2]

        self.plot_data_1a = self.get_axes_plot_data(logger_combo=self.log1a,
                                                    channel_combo=self.ch1a,
                                                    stat_col=stat1_col)
        self.plot_data_1b = self.get_axes_plot_data(logger_combo=self.log1b,
                                                    channel_combo=self.ch1b,
                                                    stat_col=stat2_col)
        self.plot_data_2a = self.get_axes_plot_data(logger_combo=self.log2a,
                                                    channel_combo=self.ch2a,
                                                    stat_col=stat1_col)
        self.plot_data_2b = self.get_axes_plot_data(logger_combo=self.log2b,
                                                    channel_combo=self.ch2b,
                                                    stat_col=stat2_col)

    def get_axes_plot_data(self, logger_combo, channel_combo, stat_col):
        """
        Get plot data for a given logger and channel
        :param logger_combo: Logger drop-down widget
        :param channel_combo: Channel drop-down widget
        :param stat_col: statistic column name to slice on
        :return: Dataframe of plot data for a given axis
        """

        # Dictionary to hold plot dataframe, label and units
        plot_data = {}

        # Selected logger info
        logger_i = logger_combo.currentIndex() - 1
        channel = channel_combo.currentText()

        # TODO: There when processing we get a channel = '' bug
        print(f'channel={channel}')
        if channel == '':
            channel = 'None'

        # If selected logger is not "None"
        if logger_i > -1 and channel != 'None':
            # Retrieve dataframe from dataset objects list
            df = self.datasets[logger_i].df
            logger_id = self.datasets[logger_i].logger_id

            # Slice dataframe for the selected statistic and then on channel
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

        self.draw_axes()

        # Check that not all loggers drop-down aren't set to "None"!
        log1a = self.log1a.currentText()
        log1b = self.log1b.currentText()
        log2a = self.log2a.currentText()
        log2b = self.log2b.currentText()

        if log1a == 'None' and log1b == 'None' and log2a == 'None' and log2b == 'None':
            self.fig.tight_layout()
            self.canvas.draw()
            return

        # Flags to check which axes are plotted to modify gridlines shown
        plot = False
        plot1_ax1 = False
        plot1_ax2 = False
        plot2_ax1 = False
        plot2_ax2 = False
        linewidth = 1

        if self.stat1 == 'Std. Dev.':
            title = f'{self.project}\nStandard Deviation'
        else:
            title = f'{self.project}\n{self.stat1}'

        self.fig.suptitle(title)

        # Plot 1 - axis 1
        if self.plot_data_1a:
            df = self.plot_data_1a['df']
            label = self.plot_data_1a['label']
            channel = self.plot_data_1a['channel']
            units = self.plot_data_1a['units']
            self.ax1.plot(df, c='dodgerblue', lw=linewidth, label=label)
            self.ax1.set_ylabel(f'{channel} ($\mathregular{{{units}}}$)')
            plot = True
            plot1_ax1 = True
        else:
            self.ax1.yaxis.set_visible(False)

        # Plot 1 - axis 2
        if self.plot_data_1b:
            df = self.plot_data_1b['df']
            label = self.plot_data_1b['label']
            channel = self.plot_data_1b['channel']
            units = self.plot_data_1b['units']
            self.ax1b.plot(df, c='red', lw=linewidth, label=label)
            self.ax1b.set_ylabel(f'{channel} ($\mathregular{{{units}}}$)')
            plot = True
            plot1_ax2 = True
            self.ax1b.yaxis.set_visible(True)

        # Plot 2 - axis 1
        if self.plot_data_2a:
            df = self.plot_data_2a['df']
            label = self.plot_data_2a['label']
            channel = self.plot_data_2a['channel']
            units = self.plot_data_2a['units']
            self.ax2.plot(df, c='deepskyblue', lw=linewidth, label=label)
            self.ax2.set_ylabel(f'{channel} ($\mathregular{{{units}}}$)')
            plot = True
            plot2_ax1 = True
        else:
            self.ax2.yaxis.set_visible(False)

        # Plot 2 - axis 2
        if self.plot_data_2b:
            df = self.plot_data_2b['df']
            label = self.plot_data_2b['label']
            channel = self.plot_data_2b['channel']
            units = self.plot_data_2b['units']
            self.ax2b.plot(df, c='orange', lw=linewidth, label=label)
            self.ax2b.set_ylabel(f'{channel} ($\mathregular{{{units}}}$)')
            plot = True
            plot2_ax2 = True
            self.ax2b.yaxis.set_visible(True)

        # Complete plot if at least one channel was plotted
        if plot is True:
            # TODO: Finish this properly!
            # Unlatched period
            # d1 = mdates.date2num(datetime(2018, 7, 13, 19, 40))
            # d2 = mdates.date2num(datetime(2018, 7, 14, 15, 40))
            # ymin, ymax = self.ax.get_ylim()
            # w = d2 - d1
            # h = 1.1 * (ymax - ymin)
            # rect = Rectangle(xy=(d1, ymin), width=w, height=h, edgecolor=None, facecolor='yellow', alpha=0.2)
            # self.ax.add_patch(rect)

            # Modify gridlines shown
            if plot1_ax1 is False and plot1_ax2 is True:
                self.ax1.grid(False)
                self.ax1b.grid(True)

            if plot2_ax1 is False and plot2_ax2 is True:
                self.ax2.grid(False)
                self.ax2b.grid(True)

            self.ax1.margins(x=0, y=0)
            self.ax1b.margins(x=0, y=0)
            self.ax2.margins(x=0, y=0)
            self.ax2b.margins(x=0, y=0)

            days = mdates.DayLocator(interval=7)
            fmt = mdates.DateFormatter('%d-%b-%y')
            # fmt = mdates.DateFormatter('%Y-%b-%d %H:%M')
            self.ax2.xaxis.set_major_locator(days)
            self.ax2.xaxis.set_major_formatter(fmt)

            self.fig.autofmt_xdate()
            self.fig.legend(loc='lower center',
                            ncol=4,
                            fontsize=11,
                            )
            # Ensure plots don't overlap suptitle and legend
            self.fig.tight_layout(rect=[0, .05, 1, .9])  # (rect=[left, bottom, right, top])

        self.canvas.draw()


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
        self.stats1Combo.addItems(stats_dict.keys())
        self.stats1Combo.setCurrentIndex(3)
        self.stats2Combo.addItems(stats_dict.keys())
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
        self.loadStats.clicked.connect(self.parent.load_stats_file)
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
        stat1_col = stats_dict[self.stat1]
        stat2_col = stats_dict[self.stat2]

        # Plot title
        if self.stat1 == 'Std. Dev.':
            stat = 'Standard Deviation'
        else:
            stat = self.stat1

        self.title = f'{self.project}\n{stat} Vessel Accelerations'

        # Dictionary to hold plot vessel motions dataframe and axis 2 channel dataframe, label and units
        plot_data = {}

        # Get axis 1 plot data
        # Get vessel motions data from vessel dataframe - it is required that the vessel dataset is called "VESSEL"
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
            logger = self.datasetList.item(0).text()
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


class SpectrogramWidget(QtWidgets.QWidget):
    """Spectrogram plot tab widget. Creates layout and all contains plotting routines."""

    def __init__(self, parent=None):
        super(SpectrogramWidget, self).__init__(parent)

        # So can access parent class
        self.parent = parent
        plt.style.use('seaborn')
        # plt.style.use('seaborn-pastel')
        # plt.style.use('bmh')

        self.project = 'Project Title'  # 'Total WoS Glendronach Well Monitoring'
        self.logger_names = []
        self.datasets = {}
        self.nat_freqs = {}
        self.timestamps = []
        self.t = None
        self.freqs = []
        self.z = []
        self.zmin = 0
        self.zmax = 0
        self.ts_i = 0

        # Initial axis limits upon loading a file
        self.init_xlim = (0.0, 3.0)
        self.xlim = (0.0, 3.0)
        self.log_scale = True

        # Placeholder for colorbar, plot line and label handles
        self.cbar = None
        self.event_line = None
        self.psd_line = None
        self.label = None
        self.skip = False

        self.init_ui()
        self.connect_signals()

        # Initialise axes
        self.draw_axes()
        self.canvas.draw()

        # Instantiate plot settings widget
        self.plotSettings = SpectroPlotSettings(self)

    def init_ui(self):
        # Main layout
        layout = QtWidgets.QHBoxLayout(self)

        # Selection layout
        selection = QtWidgets.QWidget()
        selection.setFixedWidth(170)
        grid = QtWidgets.QGridLayout(selection)
        self.loadDataset = QtWidgets.QPushButton('Load Dataset')
        lbl = QtWidgets.QLabel('Loaded Datasets')
        self.datasetList = QtWidgets.QListWidget()
        self.datasetList.setFixedHeight(100)
        self.datetimeEdit = QtWidgets.QDateTimeEdit()
        lbl2 = QtWidgets.QLabel('Timestamps (reversed)')
        self.timestampList = QtWidgets.QListWidget()
        self.slider = QtWidgets.QSlider()
        self.slider.setOrientation(QtCore.Qt.Vertical)
        self.slider.setValue(50)
        self.openPlotSettings = QtWidgets.QPushButton('Plot Settings')
        self.calcNatFreq = QtWidgets.QPushButton('Estimate Nat. Freq.')
        self.clearDatasets = QtWidgets.QPushButton('Clear Datasets')
        grid.addWidget(self.loadDataset, 0, 0)
        grid.addWidget(lbl, 1, 0)
        grid.addWidget(self.datasetList, 2, 0)
        grid.addWidget(self.datetimeEdit, 3, 0)
        grid.addWidget(lbl2, 4, 0)
        grid.addWidget(self.timestampList, 5, 0)
        grid.addWidget(self.slider, 5, 1)
        grid.addWidget(self.openPlotSettings, 6, 0)
        grid.addWidget(self.calcNatFreq, 7, 0)
        grid.addWidget(self.clearDatasets, 8, 0)

        # Plot layout
        # Create plot figure, canvas widget to display figure and navbar
        plot = QtWidgets.QWidget()
        plotLayout = QtWidgets.QGridLayout(plot)
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # Natural frequency calculation label
        self.natFreq = QtWidgets.QLabel()
        self.natFreq.setToolTip('The natural response is estimated by evaluating the mean peak frequency '
                                'of all events between 0.2 Hz and 2.0 Hz.\n'
                                'This assumes the wave energy is ignored.')

        # Widget sizing policy - prevent vertical expansion
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.natFreq.setSizePolicy(policy)

        font = QtGui.QFont()
        font.setPointSize(12)
        self.natFreq.setFont(font)
        plotLayout.addWidget(navbar, 0, 0)
        plotLayout.addWidget(self.canvas, 1, 0)
        plotLayout.addWidget(self.natFreq, 2, 0)

        # Combine layouts
        layout.addWidget(selection)
        layout.addWidget(plot)

    def connect_signals(self):
        self.loadDataset.clicked.connect(self.parent.load_spectrograms_file)
        self.calcNatFreq.clicked.connect(self.estimate_mean_natural_freq)
        self.clearDatasets.clicked.connect(self.clear_datasets)
        self.openPlotSettings.clicked.connect(self.open_plot_settings)
        self.datasetList.itemDoubleClicked.connect(self.on_dataset_double_clicked)
        self.timestampList.itemDoubleClicked.connect(self.on_timestamp_list_double_clicked)
        self.slider.valueChanged.connect(self.on_slider_change)

    def draw_axes(self):
        self.fig.clf()
        gs = gridspec.GridSpec(nrows=2, ncols=1, height_ratios=[4, 1])
        self.ax1 = self.fig.add_subplot(gs[0])
        self.ax2 = self.fig.add_subplot(gs[1], sharex=self.ax1)
        self.ax1.get_xaxis().set_visible(False)
        self.fig.subplots_adjust(hspace=0.05)
        # self.ax1 = plt.subplot2grid(shape=(4, 1), loc=(0, 0), rowspan=3)
        # self.ax2 = plt.subplot2grid(shape=(4, 1), loc=(3, 0))

    def clear_datasets(self):
        """Clear all stored spectrogram datasets and reset layout."""
        self.datasets = {}
        self.nat_freqs = {}
        self.timestamps = []
        self.datasetList.clear()
        self.timestampList.clear()
        self.natFreq.setText('')
        self.draw_axes()
        self.canvas.draw()

    def open_plot_settings(self):
        self.plotSettings.get_params()
        self.plotSettings.show()

    def update_spect_datasets_list(self, logger):
        """Populate loaded datasets list."""

        self.logger_names = logger
        self.datasetList.addItem(logger)
        n = self.datasetList.count()
        self.datasetList.setCurrentRow(n - 1)

        # Get and plot data
        self.set_plot_data()
        self.draw_axes()
        self.plot_spectrogram()
        self.plot_event_psd()

    def on_dataset_double_clicked(self):
        """Plot spectrogram."""

        self.set_plot_data()
        self.draw_axes()
        self.plot_spectrogram()
        self.plot_event_psd()

        # Check dataset key exists
        dataset = self.datasetList.currentItem().text()
        if dataset in self.nat_freqs:
            mean_nat_freq = self.nat_freqs[dataset]
            self.natFreq.setText(f'Estimated natural response: {mean_nat_freq:.2f} Hz, {1 / mean_nat_freq:.2f} s')
        else:
            self.natFreq.setText('')

    def on_slider_change(self):
        """Update event PSD plot."""

        # Ignore if initial spectrogram is being plotted
        if self.skip is True:
            return

        i = self.slider.value()
        n = self.slider.maximum()
        row = n - i
        self.timestampList.setCurrentRow(row)

        if self.timestampList.count() > 0:
            t = self.timestamps[i]
            self.set_datetime_edit(t)

            # Update plot data (faster than replotting)
            t_psd = mdates.date2num(t)
            self.update_event_marker(t_psd)
            self.update_psd_plot(i)
            self.canvas.draw()
            self.canvas.flush_events()

    def on_timestamp_list_double_clicked(self):
        """Update the PSD event slice for the selected timestamp."""

        # Timestamp list is in reverse order so index needs to be inverted
        i = self.timestampList.currentRow()
        n = self.timestampList.count()
        self.slider.setValue(n - i)

    def set_datetime_edit(self, t):
        yr = t.year
        mth = t.month
        day = t.day
        hr = t.hour
        m = t.minute
        dt = QtCore.QDateTime(yr, mth, day, hr, m)
        self.datetimeEdit.setDateTime(dt)

    def set_plot_data(self):
        """Retrieve spectrogram dataset from list and extract relevant data."""

        # Get plot data
        dataset = self.datasetList.currentItem().text()
        df = self.datasets[dataset]

        # Extract data
        self.timestamps = df.index
        self.freqs = df.columns

        if self.log_scale is True:
            self.z = np.log10(df.values)
        else:
            self.z = df.values

        # Min/max amplitudes
        self.zmin = round(self.z.min())
        self.zmax = round(self.z.max())

        # Populate timestamps list
        self.timestampList.clear()
        [self.timestampList.addItem(t.strftime('%Y-%m-%d %H:%M')) for t in reversed(self.timestamps)]

        # Set slider to middle event
        # if self.slider.value() == 50:
        n = len(self.timestamps)
        i = n // 2 - 1
        j = n - i - 1
        self.ts_i = i
        self.slider.setMaximum(n - 1)
        self.skip = True
        self.slider.setValue(i)
        self.skip = False
        self.timestampList.setCurrentRow(j)

        # Set datetime edit widget
        self.t = self.timestamps[i]
        self.set_datetime_edit(self.t)

    def estimate_mean_natural_freq(self):
        """Estimate mean natural frequency for selected dataset."""

        if self.datasetList.count() == 0:
            self.parent.error('No data currently plotted. Load a spectrogram file first.')
            return

        # self.parent.statusbar.showMessage('Calculating estimate natural frequency...')
        dataset = self.datasetList.currentItem().text()
        df = self.datasets[dataset]

        # Get the frequency of the max PSD in the given frequency range for all events
        nat_freqs = np.array([df.iloc[i][(df.iloc[i].index > 0.2) &
                                         (df.iloc[i].index < 2.0)].idxmax()
                              for i in range(len(df))])

        mean_nat_freq = nat_freqs.mean()

        # Store natural frequency in dictionary and write to plot widget
        self.nat_freqs[dataset] = mean_nat_freq
        self.natFreq.setText(f'Estimated natural response: {mean_nat_freq:.2f} Hz, {1 / mean_nat_freq:.2f} s')
        # self.parent.statusbar.showMessage('')

    def plot_spectrogram(self):
        ax1 = self.ax1
        ax2 = self.ax2
        ax1.grid(False)

        # Plot title
        channel = self.datasetList.currentItem().text()
        title = '21239 Total WoS - Glendronach Well Monitoring Campaign\nSpectrogram: ' + channel

        f0 = self.freqs[0]
        f1 = self.freqs[-1]
        t0 = mdates.date2num(self.timestamps[0])
        t1 = mdates.date2num(self.timestamps[-1])

        cmap = cm.get_cmap('coolwarm')
        im = ax1.imshow(self.z,
                        aspect='auto',
                        interpolation='bilinear',
                        origin='lower',
                        extent=[f0, f1, t0, t1],
                        cmap=cmap,
                        )

        # Plot event slice line for middle timestamp
        ti = mdates.date2num(self.t)
        self.event_line, = ax1.plot([f0, f1], [ti, ti], 'k--')

        self.cbar = self.fig.colorbar(im, ax=[ax1, ax2])
        # self.cbar = self.fig.colorbar(im, ax1=self.axes.ravel().tolist(), pad=0.04, aspect=30)

        if self.log_scale is True:
            log10 = r'$\mathregular{log_{10}}$'
        else:
            log10 = ''

        units = r'$\mathregular{(mm/s^2)^2/Hz}$'
        label = f'{log10}PSD ({units})'.lstrip()

        self.cbar.set_label(label)
        self.cbar.ax.tick_params(label)

        ax1.set_title(title)
        ax1.margins(x=0, y=0)
        ax1.set_xlim(self.xlim)
        ax1.yaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        ax1.yaxis.set_major_locator(mdates.DayLocator(interval=7))
        plt.sca(ax1)
        # plt.xticks(fontsize=11)
        # plt.yticks(fontsize=11)
        # plt.tight_layout()

    def plot_event_psd(self):
        """Plot PSD of spectrogram timestamp slice."""

        # Slice spectrogram dataset at middle timestamp
        i = self.ts_i
        zi = self.z[i, :]

        # Create legend label
        timestamp1 = self.timestamps[i]
        timestamp2 = timestamp1 + timedelta(minutes=20)
        msg_d1 = timestamp1.strftime('%d %b %Y %H:%M').lstrip('0')
        msg_d2 = timestamp2.strftime('%d %b %Y %H:%M')[-5:]
        label = ' '.join((msg_d1, 'to', msg_d2))

        self.ax2.cla()
        # self.ax2.patch.set_facecolor('none')
        self.psd_line, = self.ax2.plot(self.freqs, zi, 'k')
        self.ax2.set_ylim(self.zmin, self.zmax)
        self.ax2.margins(0, 0)
        self.ax2.set_xlabel('Frequency (Hz)')
        self.ax2.set_ylabel('PSD')
        self.label = self.ax2.annotate(label,
                                       xy=(1, 1),
                                       xycoords='axes fraction',
                                       xytext=(-2, -10),
                                       textcoords='offset points',
                                       ha='right')
        self.canvas.draw()

    def update_event_marker(self, t):
        self.event_line.set_ydata([t, t])

    def update_psd_plot(self, i):
        """Update PSD plot data for selected timestamp slice of spectrogram."""

        # Slice spectrogram dataframe for timestamp index i
        zi = self.z[i, :]

        # Create new legend label
        timestamp1 = self.timestamps[i]
        timestamp2 = timestamp1 + timedelta(minutes=20)
        msg_d1 = timestamp1.strftime('%d %b %Y %H:%M').lstrip('0')
        msg_d2 = timestamp2.strftime('%d %b %Y %H:%M')[-5:]
        label = ' '.join((msg_d1, 'to', msg_d2))

        # Update plot data and label text
        self.psd_line.set_ydata(zi)
        self.label.set_text(label)


class SpectroPlotSettings(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(SpectroPlotSettings, self).__init__(parent)

        # Assign parent objects
        self.parent = parent

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle('Spectrogram Plot Settings')

        # Widget sizing policy - prevent expansion
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # Layout
        # self.setFixedSize(400, 300)
        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.addStretch()

        # Title and axes labels form
        form = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(form)
        self.optProject = QtWidgets.QLineEdit()

        layout.addRow(QtWidgets.QLabel('Project title:'), self.optProject)

        # Frequency axis limits
        frameFreq = QtWidgets.QGroupBox('Frequency Axis')
        grid = QtWidgets.QGridLayout(frameFreq)
        self.optFreqMin = QtWidgets.QLineEdit('0')
        self.optFreqMax = QtWidgets.QLineEdit('3')
        self.optFreqMin.setFixedWidth(50)
        self.optFreqMax.setFixedWidth(50)
        grid.addWidget(QtWidgets.QLabel('Min:'), 0, 0)
        grid.addWidget(self.optFreqMin, 0, 1)
        grid.addWidget(QtWidgets.QLabel('Max:'), 1, 0)
        grid.addWidget(self.optFreqMax, 1, 1)

        # Combine axis limits frames
        axesLimits = QtWidgets.QWidget()
        axesLimits.setSizePolicy(policy)
        vbox = QtWidgets.QHBoxLayout(axesLimits)
        vbox.addWidget(frameFreq)

        # PSD log scale checkbox
        self.logScale = QtWidgets.QCheckBox('PSD log scale')
        self.logScale.setChecked(False)

        # Combine PSD x-axis and log scale
        psdOpts = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(psdOpts)
        vbox.addWidget(self.logScale)

        # Button box
        self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                  QtWidgets.QDialogButtonBox.Cancel |
                                                  QtWidgets.QDialogButtonBox.Apply |
                                                  QtWidgets.QDialogButtonBox.Reset)

        # Final layout
        mainLayout.addWidget(form)
        mainLayout.addWidget(axesLimits)
        mainLayout.addWidget(psdOpts)
        mainLayout.addWidget(self.buttons, stretch=0, alignment=QtCore.Qt.AlignRight)

    def connect_signals(self):
        self.buttons.accepted.connect(self.accept)
        self.buttons.accepted.connect(self.set_params)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.set_params)
        self.buttons.button(QtWidgets.QDialogButtonBox.Reset).clicked.connect(self.reset_values)

    def get_params(self):
        """Get plot parameters from the spectrogram widget and assign to settings widget."""

        self.optProject.setText(self.parent.project)
        self.optFreqMin.setText(str(round(self.parent.ax1.get_xlim()[0], 1)))
        self.optFreqMax.setText(str(round(self.parent.ax1.get_xlim()[1], 1)))

        if self.parent.log_scale is True:
            self.logScale.setChecked(True)
        else:
            self.logScale.setChecked(False)

    def set_params(self):
        """Update spectrogram widget class parameters with the plot settings and replot."""

        self.parent.project = self.optProject.text()

        # Check numeric parameters are of valid type
        try:
            # Assign axes limits
            self.parent.xlim = (float(self.optFreqMin.text()), float(self.optFreqMax.text()))

            # Now apply decimal formatting to plot settings
            self.optFreqMin.setText(str(round(self.parent.xlim[0], 1)))
            self.optFreqMax.setText(str(round(self.parent.xlim[1], 1)))
        except ValueError as e:
            # Notify error in main DataLab class
            val = str(e).split("'")[-2]
            self.parent.parent.error(f'Non-numeric input entered: "{val}" - {e}')
        else:
            # Assign settings to spectrogram class
            self.parent.log_scale = self.logScale.isChecked()

            # Check a spectrogram dataset has already been loaded
            if self.parent.datasetList.count() > 0:
                self.parent.set_plot_data()
                self.parent.draw_axes()
                self.parent.plot_spectrogram()
                self.parent.plot_event_psd()

    def reset_values(self):
        """Reset option settings to initial values set during file load."""

        # Pointer to spectrogram widget class
        self.logScale.setChecked(True)
        self.optFreqMin.setText(str(round(self.parent.init_xlim[0], 1)))
        self.optFreqMax.setText(str(round(self.parent.init_xlim[1], 1)))


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


class StatsWidgetOld(QtWidgets.QWidget):
    """Summary stats plot widget class."""

    def __init__(self):
        super().__init__()

        # Skip routine flags; used to prevent unnecessary multiple calls to update plot routines
        self.skip_set_radios = False
        self.skip_radio_changed = False
        self.skip_update_plot = False

        # Dataframes to current plot data
        self.ax1_df = pd.DataFrame()
        self.ax2_df = pd.DataFrame()

        # Container for StatsDataset objects
        self.datasets = []
        self.ylabel = stat_ylabels[0]

        # plt.style.use('default')
        plt.style.use('seaborn')
        # plt.style.use('ggplot')
        # sns.set()

        # Main layout
        layout = QtWidgets.QHBoxLayout(self)

        gridWidget = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout()
        gridWidget.setLayout(grid)

        # Create plot figure, canvas widget to display figure and navbar
        self.fig, self.ax = plt.subplots(figsize=(11.69, 8.27))
        self.ax2 = self.ax.twinx()
        self.ax2.yaxis.set_visible(False)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.draw()
        navbar = NavigationToolbar(self.canvas, self)

        # Channel and stats selection container
        # selectionWidget = QtWidgets.QWidget()
        # selectionWidget.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))
        # hbox = QtWidgets.QHBoxLayout()
        # selectionWidget.setLayout(hbox)
        # grid.addWidget(selectionWidget, 0, 0, Qt.AlignLeft)
        grid.addWidget(navbar, 0, 0)
        grid.addWidget(self.canvas, 1, 0)

        selection = QtWidgets.QWidget()
        selection.setFixedWidth(150)
        vbox = QtWidgets.QVBoxLayout(selection)

        # Statistic label and drop-down
        lbl_stat = QtWidgets.QLabel('Plot statistic:')
        self.statsCombo = QtWidgets.QComboBox()
        self.statsCombo.addItems(self.stat_dict)

        lbl1 = QtWidgets.QLabel('Loaded Datasets')
        lbl2 = QtWidgets.QLabel('Channels')
        self.datasetList = QtWidgets.QListWidget()
        self.channelsList = QtWidgets.QListWidget()

        # Hs & Tp mean override checkbox
        self.meanWaveChkBox = QtWidgets.QCheckBox('Mean Hs/Tp override')
        self.meanWaveChkBox.setChecked(True)

        # Plot axis radio buttons
        radioFrame = QtWidgets.QGroupBox('Plot axis')
        vbox2 = QtWidgets.QVBoxLayout()
        radioFrame.setLayout(vbox2)
        self.radioNone = QtWidgets.QRadioButton('None')
        self.radioPri = QtWidgets.QRadioButton('Primary')
        self.radioSec = QtWidgets.QRadioButton('Secondary')
        vbox2.addWidget(self.radioNone)
        vbox2.addWidget(self.radioPri)
        vbox2.addWidget(self.radioSec)

        # Stack plot settings widgets
        vbox.addWidget(lbl_stat)
        vbox.addWidget(self.statsCombo)
        vbox.addWidget(lbl1)
        vbox.addWidget(self.datasetList)
        vbox.addWidget(lbl2)
        vbox.addWidget(self.channelsList)
        vbox.addWidget(self.meanWaveChkBox)
        vbox.addWidget(radioFrame)

        # frame = QtWidgets.QGroupBox('Plot settings')
        # frame.setFixedWidth(150)
        # frame.setLayout(vbox)

        # Add widgets to main layout
        # layout.addWidget(frame)
        layout.addWidget(selection)
        layout.addWidget(gridWidget)

        self.connect_signals()

    def connect_signals(self):
        self.statsCombo.currentIndexChanged.connect(self.update_plot)
        self.datasetList.currentItemChanged.connect(self.update_channels_list)
        self.channelsList.currentItemChanged.connect(self.set_radios)
        self.meanWaveChkBox.stateChanged.connect(self.update_plot)
        self.radioNone.toggled.connect(self.radio_changed)
        self.radioPri.toggled.connect(self.radio_changed)
        self.radioSec.toggled.connect(self.radio_changed)

    def update_stats_datasets_list(self, dataset_names, append=True):
        """Populate loaded datasets list."""

        # Set first checkstate of primary series as checked if no datasets previously loaded
        # to ensure an initial plot
        if self.datasetList.count() == 0:
            self.datasets[0].plot_on_pri_axis[0] = True

        # Update loaded datasets list
        if not append:
            self.datasetList.clear()

        # Create dataset list and select first item (this will trigger an update of update_channels_list)
        [self.datasetList.addItem(x) for x in dataset_names]
        self.datasetList.setCurrentRow(0)

    def update_channels_list(self):
        """Update channels list to match selected dataset."""

        i = self.datasetList.currentRow()
        if i == -1:
            return

        # Set flag to prevent radio_changed being mistakenly triggered
        self.skip_set_radios = True
        self.channelsList.clear()
        self.skip_set_radios = False

        # Create new channels list for selected dataset and select first item (this will trigger an
        # update of set_radios)
        [self.channelsList.addItem(x) for x in self.datasets[i].channels]
        self.channelsList.setCurrentRow(0)

    def set_radios(self):
        """Update radio button for selected channel."""

        if self.skip_set_radios:
            return

        i = self.datasetList.currentRow()
        j = self.channelsList.currentRow()

        # Set flag to prevent radio_changed being mistakenly triggered
        self.skip_radio_changed = True

        # Set radio button based on stored flag
        if self.datasets[i].plot_on_pri_axis[j] == True:
            self.radioPri.setChecked(True)
        elif self.datasets[i].plot_on_sec_axis[j] == True:
            self.radioSec.setChecked(True)
        else:
            self.radioNone.setChecked(True)

        self.skip_radio_changed = False

    def radio_changed(self):
        """Update channel plot flags for change in triggered radio button."""

        if self.skip_radio_changed:
            return

        if self.skip_update_plot:
            self.skip_update_plot = False
            return

        i = self.datasetList.currentRow()
        j = self.channelsList.currentRow()

        # Initialise channel plot axis flags
        self.datasets[i].plot_on_pri_axis[j] = False
        self.datasets[i].plot_on_sec_axis[j] = False

        # Set axis to plot channel on, if any
        if self.radioPri.isChecked():
            self.datasets[i].plot_on_pri_axis[j] = True
        elif self.radioSec.isChecked():
            self.datasets[i].plot_on_sec_axis[j] = True

        self.update_plot()

        # This flag prevents the plot being updated twice, since when a radio button is changed the routine is triggered
        # twice, once for the switch to "on" and once for switch to "off"
        self.skip_update_plot = True

    def update_plot(self):
        """Update time series stats plot."""

        plot = False
        self.ax.cla()
        self.ax2.cla()
        self.ax2.yaxis.set_visible(False)
        self.ax2.grid(None)
        stat_i = self.statsCombo.currentIndex()
        stat = self.statsCombo.currentText()
        # title = '21148 Total Glenlivet G1 Well Monitoring Campaign\n' + stat
        title = '21239 Total WoS - Glendronach Well Monitoring Campaign\n' + stat

        # Dataframes to current plot data
        self.ax1_df = pd.DataFrame()
        self.ax2_df = pd.DataFrame()

        for i in range(self.datasetList.count()):
            logger_id = self.datasets[i].logger_id
            t = self.datasets[i].df.index

            # Plot channels on primary axis
            for j, plot_channel in enumerate(self.datasets[i].plot_on_pri_axis):
                if plot_channel:
                    channel = self.datasets[i].channels[j]
                    plot = True
                    channel_i = 4 * j

                    # Check if channel is wave height or period (i.e. contains 'wave' in name) and only plot the mean
                    # if mean Hs/Tp override is set
                    if 'wave' in channel.lower() and self.meanWaveChkBox.isChecked():
                        col = channel_i + 2
                        label = ' '.join((logger_id, 'Mean', channel, '(axis 1)'))
                    else:
                        col = channel_i + stat_i
                        label = ' '.join((logger_id, channel, '(axis 1)'))

                    data = self.datasets[i].df.iloc[:, col]
                    self.ax1_df[label] = data
                    self.ax.plot(t, data.values, lw=1)

                    # Legend fudge: plot dummy series on ax2
                    self.ax2.plot(t[0], 0, lw=1, label=label)

            # Plot channels secondary axis
            for j, plot_channel in enumerate(self.datasets[i].plot_on_sec_axis):
                if plot_channel:
                    self.ax2.yaxis.set_visible(True)
                    channel = self.datasets[i].channels[j]
                    plot = True
                    channel_i = 4 * j

                    # Check if channel is wave height or period (i.e. contains 'wave' in name) and only plot the mean
                    # if mean Hs/Tp override is set
                    if 'wave' in channel.lower() and self.meanWaveChkBox.isChecked():
                        col = channel_i + 2
                        label = ' '.join((logger_id, 'Mean', channel, '(axis 2)'))
                    else:
                        col = channel_i + stat_i
                        label = ' '.join((logger_id, channel, 'axis 2'))

                    data = self.datasets[i].df.iloc[:, col]
                    self.ax2_df[label] = data
                    self.ax2.plot(t, data.values, lw=1, label=label)

        # Complete plot if at least one channel was plotted
        if plot:
            # TODO: Finish this properly!
            # Unlatched period
            # d1 = mdates.date2num(datetime(2018, 7, 13, 19, 40))
            # d2 = mdates.date2num(datetime(2018, 7, 14, 15, 40))
            # ymin, ymax = self.ax.get_ylim()
            # w = d2 - d1
            # h = 1.1 * (ymax - ymin)
            # rect = Rectangle(xy=(d1, ymin), width=w, height=h, edgecolor=None, facecolor='yellow', alpha=0.2)
            # self.ax.add_patch(rect)

            self.ax2.legend(loc='best')
            self.ax.set_xlabel('Timestamp')
            self.ax.set_ylabel(self.ylabel)
            self.ax.set_title(title)
            self.ax.margins(x=0, y=0)

            days = mdates.DayLocator(interval=7)
            self.ax.xaxis.set_major_locator(days)
            fmt = mdates.DateFormatter('%d-%b-%y')
            # fmt = mdates.DateFormatter('%Y-%b-%d %H:%M')
            self.ax.xaxis.set_major_formatter(fmt)
            self.fig.autofmt_xdate()
            # self.fig.tight_layout()

        self.canvas.draw()

        # self.p.apply_2H_formatting()


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
