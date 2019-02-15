from datetime import datetime

import PIL
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                             QListWidget,
                             QRadioButton, QVBoxLayout, QWidget)
from matplotlib import cm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator


# from matplotlib.font_manager import findfont, FontProperties


# import colormap as cmaps

class StatsDataset:
    """Class to hold stats datasets and associated properties."""

    def __init__(self, logger_id='', df=pd.DataFrame()):
        self.logger_id = logger_id
        self.df = df

        try:
            self.channels = list(filter(None, self.df.columns.unique(level='channels')))
        except:
            self.channels = ['N/A']

        self.plot_on_pri_axis = [False] * len(self.channels)
        self.plot_on_sec_axis = [False] * len(self.channels)


class StatsWidget(QWidget):
    """Summary stats plot widget class."""

    ylabels = ['Acceleration ($\mathregular{m/s^2}$)',
               'Angular Rate ($\mathregular{deg/s}$)']

    stats = ['Minimum',
             'Maximum',
             'Mean',
             'Standard Deviation']

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
        self.ylabel = self.ylabels[0]

        # plt.style.use('default')
        plt.style.use('seaborn')
        # plt.style.use('ggplot')
        # sns.set()

        # Main layout
        layout = QHBoxLayout(self)

        gridWidget = QWidget()
        grid = QGridLayout()
        gridWidget.setLayout(grid)

        # Create plot figure, canvas widget to display figure and navbar
        self.fig, self.ax = plt.subplots(figsize=(11.69, 8.27))
        self.ax2 = self.ax.twinx()
        self.ax2.yaxis.set_visible(False)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.draw()
        navbar = NavigationToolbar(self.canvas, self)

        # Channel and stats selection container
        # selectionWidget = QWidget()
        # selectionWidget.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))
        # hbox = QHBoxLayout()
        # selectionWidget.setLayout(hbox)
        # grid.addWidget(selectionWidget, 0, 0, Qt.AlignLeft)
        grid.addWidget(navbar, 0, 0)
        grid.addWidget(self.canvas, 1, 0)

        selection = QWidget()
        selection.setFixedWidth(150)
        vbox = QVBoxLayout(selection)

        # Statistic label and drop-down
        lbl_stat = QLabel('Plot statistic:')
        self.statsCombo = QComboBox()
        self.statsCombo.addItems(self.stats)

        lbl1 = QLabel('Loaded Datasets')
        lbl2 = QLabel('Channels')
        self.datasetList = QListWidget()
        self.channelsList = QListWidget()

        # Hs & Tp mean override checkbox
        self.meanWaveChkBox = QCheckBox('Mean Hs/Tp override')
        self.meanWaveChkBox.setChecked(True)

        # Plot axis radio buttons
        radioFrame = QGroupBox('Plot axis')
        vbox2 = QVBoxLayout()
        radioFrame.setLayout(vbox2)
        self.radioNone = QRadioButton('None')
        self.radioPri = QRadioButton('Primary')
        self.radioSec = QRadioButton('Secondary')
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

        # frame = QGroupBox('Plot settings')
        # frame.setFixedWidth(150)
        # frame.setLayout(vbox)

        # Add widgets to main layout
        # layout.addWidget(frame)
        layout.addWidget(selection)
        layout.addWidget(gridWidget)

        self._connect_signals()

    def _connect_signals(self):
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
            d1 = mdates.date2num(datetime(2018, 7, 13, 19, 40))
            d2 = mdates.date2num(datetime(2018, 7, 14, 15, 40))
            ymin, ymax = self.ax.get_ylim()
            w = d2 - d1
            h = 1.1 * (ymax - ymin)
            rect = Rectangle(xy=(d1, ymin), width=w, height=h, edgecolor=None, facecolor='yellow', alpha=0.2)
            self.ax.add_patch(rect)

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


class VarianceWidget(QWidget):
    ylabels = ['Acceleration ($\mathregular{m/s^2}$)',
               'Angular Rate ($\mathregular{deg/s}$)']
    channels = ['Acceleration X',
                'Acceleration Y',
                'Angular Rate X',
                'Angular Rate Y']

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
        layout = QHBoxLayout(self)

        # Plot layout
        plot = QWidget()
        plot_layout = QVBoxLayout()
        plot.setLayout(plot_layout)
        plot_layout.addWidget(navbar)
        plot_layout.addWidget(self.canvas)

        # Selection layout
        selection = QWidget()
        selection.setFixedWidth(150)
        vbox = QVBoxLayout(selection)

        lbl1 = QLabel('Channel:')
        self.channelsCombo = QComboBox()
        self.channelsCombo.addItems(self.channels)
        lbl2 = QLabel('Loaded Datasets')
        self.datasetList = QListWidget()

        vbox.addWidget(lbl1)
        vbox.addWidget(self.channelsCombo)
        vbox.addWidget(lbl2)
        vbox.addWidget(self.datasetList)

        layout.addWidget(selection)
        layout.addWidget(plot)

        self._connect_signals()

    def _connect_signals(self):
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
            ylabel = self.ylabels[0]
        else:
            ylabel = self.ylabels[1]

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
            ylabel = self.ylabels[0]
        else:
            ylabel = self.ylabels[1]

        self.ax.set_xlabel('Timestamp')
        self.ax.set_ylabel(ylabel)
        self.ax.set_title(title)
        self.ax.margins(x=0, y=0)
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b-%y %H:%M'))
        self.fig.autofmt_xdate()
        self.fig.tight_layout()

        self.canvas.draw()


class SpectrogramWidget(QWidget):
    ylabels = ['Acceleration ($\mathregular{m/s^2}$)',
               'Angular Rate ($\mathregular{deg/s}$)']
    channels = ['Acceleration X',
                'Acceleration Y',
                'Angular Rate X',
                'Angular Rate Y']

    def __init__(self):
        super().__init__()

        self.logger_names = []
        self.datasets = {}

        # Create plot figure, canvas widget to display figure and navbar
        self.fig, self.ax = plt.subplots()
        # self.fig, (self.ax0, self.ax1) = plt.subplots(nrows=2)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.draw()
        navbar = NavigationToolbar(self.canvas, self)

        # Placeholder for colorbar
        self.cbar = None

        # Main layout
        layout = QHBoxLayout(self)

        # Plot layout
        plot = QWidget()
        plot_layout = QVBoxLayout()
        plot.setLayout(plot_layout)
        plot_layout.addWidget(navbar)
        plot_layout.addWidget(self.canvas)

        # Selection layout
        selection = QWidget()
        selection.setFixedWidth(150)
        vbox = QVBoxLayout(selection)

        lbl1 = QLabel('Channel:')
        self.channelsCombo = QComboBox()
        self.channelsCombo.addItems(self.channels)
        lbl2 = QLabel('Loaded Datasets')
        self.datasetList = QListWidget()

        # vbox.addWidget(lbl1)
        # vbox.addWidget(self.channelsCombo)
        vbox.addWidget(lbl2)
        vbox.addWidget(self.datasetList)

        layout.addWidget(selection)
        layout.addWidget(plot)

        self._connect_signals()

    def _connect_signals(self):
        # self.channelsCombo.currentIndexChanged.connect(self.update_spect_plot)
        self.datasetList.currentItemChanged.connect(self.update_spect_plot)

    def update_spect_datasets_list(self, dataset_names):
        """Populate loaded datasets list."""

        # Create active channels flag lists
        self.logger_names = dataset_names

        # Repopulate datasets list
        # self.datasetList.clear()
        if isinstance(dataset_names, str):
            self.datasetList.addItem(dataset_names)
        else:
            [self.datasetList.addItem(x) for x in dataset_names]

        self.datasetList.setCurrentRow(0)

    def update_spect_plot(self):
        """Plot spectrogram."""

        ax = self.ax
        ax.cla()

        # Exit function if no dataset in list selected (i.e. list is empty)
        i = self.datasetList.currentRow()
        if i == -1:
            return

        # Plot title
        channel = self.datasetList.currentItem().text()
        # title = '21148 Total Glenlivet G1 Well Monitoring Campaign\nSpectrogram: ' + channel
        title = '21239 Total WoS - Glendronach Well Monitoring Campaign\nSpectrogram: ' + channel

        # Get plot data
        dataset = self.datasetList.currentItem().text()
        df = self.datasets[dataset]

        # Use for old data
        # df = df.T

        t = df.index
        f = df.columns[1:]
        amps = df.values[:, 1:]
        z = np.log10(amps)
        # z = amps

        # x, y = np.meshgrid(t, f)
        #
        # plt.sca(ax)
        # print(t.min())
        # print(t.max())
        # print(f.min())
        # print(f.max())
        # print(z.min())
        # print(z.max())

        cmap = cm.get_cmap('viridis')
        levels = MaxNLocator(nbins=15).tick_values(z.min(), z.max())
        norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

        # im = ax.contourf(f, t, z, levels=levels, cmap=cmap, norm=norm)
        im = ax.pcolormesh(f, t, z, cmap=cmap)

        cmap_name = 'Spectrum Plot'
        colors = [(0, 0, 1), (0, 1, 0), (1, 0, 0)]  # RGB
        cmap = LinearSegmentedColormap.from_list(name=cmap_name, colors=colors, N=200)
        # im = ax.pcolormesh(f, t, z, cmap=cmap)

        if self.cbar:
            self.cbar.remove()

        self.cbar = self.fig.colorbar(im, ax=ax)
        self.cbar.set_label('PSD ($\mathregular{(m^2)^2/Hz}$)')

        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Date')
        ax.set_title(title)

        ax.margins(x=0, y=0)
        ax.yaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        ax.yaxis.set_major_locator(mdates.DayLocator(interval=7))
        # ax.set_ylim(0, 1)

        plt.tight_layout()

        # Rich's GRDView code

        # cmap_name = 'Spectrum Plot'
        # colors = [(0, 0, 1), (0, 1, 0), (1, 0, 0)]  # RGB
        # cmap = LinearSegmentedColormap.from_list(name=cmap_name, colors=colors, N=200)
        # # cmap = LinearSegmentedColormap(name=cmap_name, segmentdata=colors, N=200)
        # self.ax.pcolormesh(t, f, np.log10(amps), cmap=cmap)

        # im = self.ax.imshow(amps,
        #                     aspect='auto',
        #                     interpolation='bilinear',
        #                     origin='lower',
        #                     # extent=[r_freq[Nmin], r_freq[Nmax], 0, Nloop],
        #                     cmap=cmap)
        #
        # self.fig.colorbar(im, ax=self.ax)

        # Plot Spectrogram
        # if self.ShowSpectrogram.isChecked() == True:
        #     # determine the maximum value on the data..
        #     try:
        #         Nmin = 1
        #         for j in range(0, len(r_freq)):
        #             if (r_freq[j] < (self.MaxFreqSpec - self.MinFreqSpec) * 4 / 5 + self.MinFreqSpec) \
        #                     and (r_freq[j] > 0):
        #                 Nmax = j
        #             if (r_freq[j] < self.MinFreqSpec) and (r_freq[j] > 0):
        #                 Nmin = j
        #         Nloop = self.num_samples
        #         cmap_name = 'Spectrum Plot'
        #         colors = [(0, 0, 1), (0, 1, 0), (1, 0, 0)]  # RGB
        #         cm = LinearSegmentedColormap.from_list(cmap_name, colors, 200)
        #         im = self.ax4a.imshow(self.enfft, aspect='auto', interpolation='bilinear', origin='lower',
        #                               extent=[r_freq[Nmin], r_freq[Nmax], 0, Nloop], cmap=cm)
        #         self.figure.colorbar(im)
        #         self.ax4a.plot(r_freq[Nmin:Nmax], Nloop * 1 * r_freq[Nmin:Nmax] / r_freq[Nmax], zorder=-1)
        #     except Exception as e:
        #         self.show_error_msg(str(e))

        self.canvas.draw()

    def example_plot(self):
        # PCOLORMESH EXAMPLE

        # make these smaller to increase the resolution
        dx, dy = 0.05, 0.05

        # generate 2 2d grids for the x & y bounds
        y, x = np.mgrid[slice(1, 5 + dy, dy),
                        slice(1, 5 + dx, dx)]

        z = np.sin(x) ** 10 + np.cos(10 + y * x) * np.cos(x)

        # x and y are bounds, so z should be the value *inside* those bounds.
        # Therefore, remove the last value from the z array.
        z = z[:-1, :-1]
        levels = MaxNLocator(nbins=15).tick_values(z.min(), z.max())

        # pick the desired colormap, sensible levels, and define a normalization
        # instance which takes data values and translates those into levels.
        cmap = plt.get_cmap('PiYG')
        norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

        im = self.ax0.pcolormesh(x, y, z, cmap=cmap, norm=norm)
        self.fig.colorbar(im, ax=self.ax0)
        self.ax0.set_title('pcolormesh with levels')

        # contours are *point* based plots, so convert our bound into point
        # centers
        cf = self.ax1.contourf(x[:-1, :-1] + dx / 2.,
                               y[:-1, :-1] + dy / 2., z, levels=levels,
                               cmap=cmap)
        self.fig.colorbar(cf, ax=self.ax1)
        self.ax1.set_title('contourf with levels')

        # adjust spacing between subplots so `ax1` title and `ax0` tick labels
        # don't overlap
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
    from PyQt5.QtWidgets import QApplication

    np.random.seed(0)
    app = QApplication(sys.argv)

    # Create dummy dataset
    start_dates = ['2017-03-10 00:00:00',
                   '2017-03-10 00:10:00',
                   '2017-03-10 00:20:00']

    start_dates = [datetime.strptime(t, '%Y-%m-%d %H:%M:%S') for t in start_dates]

    data = [[j + i * 10 for j in range(16)] for i in range(3)]
    stats = np.asarray(data)
    data = np.random.randn(3, 4)
    df = pd.DataFrame(data=data, index=start_dates)
    dataset = StatsDataset(logger_id='test', df=df)
    dataset_names = ['test']

    w = StatsWidget()
    w.show()
    w.datasets.append(dataset)
    w.update_stats_datasets_list(dataset_names)
    w.update_plot()

    p = PlotStyle2H(w.canvas, w.fig)
    p.add_2H_icon()

    title = {'title1': '21239 Total WoS', 'title2': 'Glendronach Well Monitoring Campaign', 'title3': 'Mean'}
    p.format_2h_style(**title)

    sys.exit(app.exec_())
#
# if __name__ == '__main__':
#     import sys
#     from PyQt5.QtWidgets import QApplication
#     from spectrograms import read_spectrograms_excel
#
#     # fpath = r'C:\Users\dickinsc\PycharmProjects\DSPLab\example_control_files\Output dd10 Sample'
#     # fname = 'Spectrograms2.xlsx'
#     # fpath = r'C:\Users\dickinsc\PycharmProjects\DSPLab\example_control_files\Output G1 dd10 Spect'
#     # fname = 'Spectrograms.xlsx'
#     #
#     # fpath = os.path.join(fpath, fname)
#     # spect_dict = read_spectrograms_excel(fpath)
#     # # spect_dict = {'dd10': np.ones(3)}
#     # names = list(spect_dict.keys())
#
#     app = QApplication(sys.argv)
#     # w = VarianceWidget()
#     w = SpectrogramWidget()
#     # w.datasets = spect_dict
#     # w.update_spect_datasets_list(names)
#
#     w.example_plot()
#
#     w.show()
#     sys.exit(app.exec_())

# if __name__ == '__main__':
#     d = StatsDataset()
