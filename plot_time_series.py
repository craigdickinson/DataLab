import logging
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from scipy import signal

# from gui.gui_zoom_pan_factory import ZoomPan
from core.read_files import read_fugro_csv, read_pulse_acc, read_logger_hdf5
from core.signal_filtering import filter_signal

# "2H blue"
color_2H = np.array([0, 49, 80]) / 255


class TimeSeriesPlotWidget(QtWidgets.QWidget):
    """Create raw time series plots widget."""

    def __init__(self, parent=None):
        super(TimeSeriesPlotWidget, self).__init__(parent)

        # So can access parent class
        self.parent = parent
        plt.style.use('seaborn')

        self.files_list = []
        self.logger_id = ''
        # self.project = 'Project Title'
        self.project = 'Total WoS Glendronach Well Monitoring'

        # Plot settings
        self.plot_pri = False
        self.plot_sec = False
        self.plot_period = False
        self.log_scale = False
        self.psd_params_type = 'default'
        self.set_init_axis_limits = True
        self.ignore_on_xlim_change = True

        # Column index of channel to plot on pri/sec axis
        self.pri_ix = 1
        self.sec_ix = 0

        # Default PSD parameters
        self.def_num_ensembles = 1
        self.def_window = 'None'
        self.def_overlap = 0
        self.def_nperseg = 256

        # Default Welch PSD parameters
        self.welch_num_ensembles = 46.875
        self.welch_window = 'Hann'
        self.welch_overlap = 50
        self.welch_nperseg = 256

        # Custom Welch PSD parameters
        self.cust_num_ensembles = 1
        self.cust_window = 'None'
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
        self.apply_low_cutoff = True
        self.apply_high_cutoff = True
        self.low_cutoff = 0.05
        self.high_cutoff = 0.5

        # To hold file data
        self.df = pd.DataFrame()
        self.filtered_ts = np.array([])
        self.df_plot = pd.DataFrame()
        self.plot_units = []

        # Channel names and units in time series file
        self.channel_names = []
        self.current_channels = []
        self.units = []

        self.init_ui()
        self.connect_signals()

        # Instantiate plot settings widget
        self.plotSettings = LoggerPlotSettings(self)

    def init_ui(self):
        # Setup container
        setupWidget = QtWidgets.QWidget()
        setupWidget.setFixedWidth(200)
        vboxSetup = QtWidgets.QVBoxLayout(setupWidget)

        # Load file
        self.loadFile = QtWidgets.QPushButton('Load Raw Logger File')
        self.loadFile.setToolTip('Load raw logger file')

        # Files list
        filesLabel = QtWidgets.QLabel('Logger Files')
        self.filesList = QtWidgets.QListWidget()

        # Channels list
        channelsLabel = QtWidgets.QLabel('Channels (echo)')
        self.channelsList = QtWidgets.QListWidget()
        self.channelsList.setFixedHeight(120)

        # Primary and secondary axis combos
        priLabel = QtWidgets.QLabel('Primary Axis Channel:')
        secLabel = QtWidgets.QLabel('Secondary Axis Channel:')
        self.priAxis = QtWidgets.QComboBox()
        self.secAxis = QtWidgets.QComboBox()
        self.priAxis.addItem('None')
        self.secAxis.addItem('None')

        # Line separator
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)

        # Plot settings and replot buttons
        self.settingsButton = QtWidgets.QPushButton('Plot Settings')
        self.replotButton = QtWidgets.QPushButton('Replot')

        # Add setup widgets
        vboxSetup.addWidget(self.loadFile)
        vboxSetup.addWidget(filesLabel)
        vboxSetup.addWidget(self.filesList)
        vboxSetup.addWidget(channelsLabel)
        vboxSetup.addWidget(self.channelsList)
        vboxSetup.addWidget(priLabel)
        vboxSetup.addWidget(self.priAxis)
        vboxSetup.addWidget(secLabel)
        vboxSetup.addWidget(self.secAxis)
        vboxSetup.addWidget(line)
        vboxSetup.addWidget(self.settingsButton)
        vboxSetup.addWidget(self.replotButton)

        # Plot container
        plotWidget = QtWidgets.QWidget()
        vboxPlot = QtWidgets.QVBoxLayout(plotWidget)

        # Plot figure and canvas to display figure
        self.fig, (self.ax1, self.ax2) = plt.subplots(2)
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # Add plot widgets
        vboxPlot.addWidget(navbar)
        vboxPlot.addWidget(self.canvas)

        # Final layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(setupWidget)
        layout.addWidget(plotWidget)

    def connect_signals(self):
        self.loadFile.clicked.connect(self.parent.load_logger_file)
        self.settingsButton.clicked.connect(self.open_plot_options)
        self.replotButton.clicked.connect(self.replot)
        self.filesList.itemDoubleClicked.connect(self.on_file_double_clicked)

    def on_file_double_clicked(self):
        self.replot()

    def open_plot_options(self):
        """Show plot options window."""

        # Set current parameters from time series plot widget class
        self.plotSettings.get_params()
        self.plotSettings.show()

    def replot(self):
        """Load and process a selected logger file in the files list."""

        if self.filesList.count() == 0:
            return

        filename = self.filesList.currentItem().text()

        try:
            self.load_file(filename)
        except ValueError as e:
            self.parent.error(f'Error: {e}')
        except Exception as e:
            msg = 'Unexpected error loading logger file'
            self.parent.error(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
            logging.exception(msg)

    def load_file(self, filename):
        """Load logger file, update widget and plot first channel."""

        self.df = self.read_logger_file(filename)

        # Store logger ID (assume the first portion of the filename)
        self.logger_id = filename.split('_')[0]

        # Store channel names and units - ignore column 1 (Timestamps)
        self.channel_names = self.df.columns.get_level_values(0).tolist()[1:]
        self.units = self.df.columns.get_level_values(1).tolist()[1:]
        self.update_channels()

        # Extract data to be plotted based on selected channels and plot settings
        self.df_plot = self.set_plot_data(self.df)

        # Check plot data was set and store initial data limits (note column 1 is Timestamp so looking for > 1 columns)
        if len(self.df_plot.columns) > 1:
            self.init_xlim = (self.df_plot.index[0], self.df_plot.index[-1])

        # This flag stops the on_xlims_change event from processing
        self.ignore_on_xlim_change = True
        self.filtered_ts = self.calc_filtered_data(self.df_plot)
        self.update_plots()
        self.ignore_on_xlim_change = False

    def update_files_list(self, files_list, file_name):
        """Populate files list widget."""

        # Store list
        self.files_list = files_list

        # Repopulate files list widget
        self.filesList.clear()
        self.filesList.addItems(files_list)
        i = files_list.index(file_name)
        self.filesList.setCurrentRow(i)

    def read_logger_file(self, filename):
        """Read a raw logger file."""

        ext = filename.split('.')[-1].lower()

        if ext == 'csv':
            df = read_fugro_csv(filename)
        elif ext == 'acc':
            df = read_pulse_acc(filename)
        elif ext == 'h5':
            df = read_logger_hdf5(filename)
        else:
            raise FileNotFoundError(f'No files with the extension {ext} found.')

        return df

    def update_channels(self):
        """Populate drop-down channels if required."""

        # Store selected primary and secondary axis channel combo boxes indexes
        self.pri_ix = self.priAxis.currentIndex()
        self.sec_ix = self.secAxis.currentIndex()

        # Redefine channels list and plot series combo boxes if current channels don't match those in selected file
        if self.channel_names != self.current_channels:
            self.channelsList.clear()
            self.priAxis.clear()
            self.secAxis.clear()

            # Add channels to list and make unselectable since they are just an echo for reference
            for channel in self.channel_names:
                item = QtWidgets.QListWidgetItem(channel)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
                self.channelsList.addItem(item)

            self.priAxis.addItem('None')
            self.secAxis.addItem('None')
            self.priAxis.addItems(self.channel_names)
            self.secAxis.addItems(self.channel_names)
            self.current_channels = self.channel_names

            if self.channelsList.count() == 0:
                raise ValueError('No channels added')

            # Initialise so that only first channel is plotted on primary axis
            self.pri_ix = 1
            self.sec_ix = 0
            self.priAxis.setCurrentIndex(self.pri_ix)
            self.secAxis.setCurrentIndex(self.sec_ix)

            # Flag to set axis limits to dataset length
            self.set_init_axis_limits = True

    def set_plot_data(self, df):
        """
        Create plot dataset.
        :return: df_plot - data frame containing all series to be plotted with labels as column names
        """

        self.plot_units = []
        self.plot_pri = False
        self.plot_sec = False

        # Store timestamp column and rename column since original data frame is a multiindex header
        df_plot = df.iloc[:, 0].to_frame()
        df_plot.columns = ['Timestamp']

        # Append data columns to plot to data frame
        i = self.pri_ix
        if i > 0:
            self.plot_pri = True
            self.plot_units.append(self.units[i - 1])
            df_plot[self.channel_names[i - 1]] = df.iloc[:, i]

        i = self.sec_ix
        if i > 0:
            self.plot_sec = True
            self.plot_units.append(self.units[i - 1])
            df_plot[self.channel_names[i - 1]] = df.iloc[:, i]

        return df_plot

    def calc_filtered_data(self, df_raw):
        """Remove noise."""

        df_raw = df_raw.select_dtypes('number')

        low_cutoff = self.low_cutoff
        high_cutoff = self.high_cutoff

        # Set cut-off values to None if they are not to be applied
        if self.apply_low_cutoff is False:
            low_cutoff = None

        if self.apply_high_cutoff is False:
            high_cutoff = None

        filtered = filter_signal(df_raw, low_cutoff, high_cutoff)

        return filtered

    def update_plots(self):
        """Create time series plots for selected logger channels."""

        # First apply any filtering to the time series
        # df_filtered = filter_signal(self.df_plot, low_cutoff=0.05, high_cutoff=0.5)

        self.draw_axes()

        # Nothing to plot if data frame contains only the Timestamp column
        if len(self.df_plot.columns) == 1:
            return

        try:
            self.plot_time_series(self.df_plot, self.filtered_ts)
            self.plot_psd(self.df_plot[self.ts_xlim[0]:self.ts_xlim[1]])
        except ValueError as e:
            self.parent.error(str(e))
        except Exception as e:
            msg = 'Unexpected error processing loggers'
            self.parent.error(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
            logging.exception(msg)

        # Titles and legend
        self.plot_title(self.fig, self.df_plot)
        self.ax1.set_title('Time Series', size=12)
        self.ax2.set_title('Power Spectral Density', size=12)
        self.fig.legend(loc='lower center',
                        ncol=6,
                        fontsize=11,
                        # frameon=False,
                        # fancybox=False,
                        # edgecolor='none',
                        # facecolor='none',
                        )

        # Ensure plots don't overlap suptitle and legend
        self.fig.tight_layout(rect=[0, .05, 1, .9])  # (rect=[left, bottom, right, top])
        # (left, bottom, right, top, wspace, hspace)
        # self.fig.subplots_adjust(bottom=.15, top=.85, hspace=.5)
        self.canvas.draw()

        # Update parameters in plot settings window (could be open)
        self.plotSettings.get_params()

    def draw_axes(self):
        """Set up basic plot layout."""

        self.fig.clf()

        # Set up time series and PSD axes
        self.ax1 = self.fig.add_subplot(2, 1, 1)
        self.ax2 = self.fig.add_subplot(2, 1, 2)
        self.ax1b = self.ax1.twinx()
        self.ax2b = self.ax2.twinx()
        self.ax1b.yaxis.set_visible(False)
        self.ax2b.yaxis.set_visible(False)

        # self.ax2.set_ylabel(ylabel, size=11)  # Leave as example of error

        # TODO: Mouse scroll zoom - works
        # f = self.zoom_factory(self.ax, base_scale=1.1)
        # f = self.zoom_factory(self.ax2, base_scale=1.1)

        # zp = ZoomPan()
        # figZoom = zp.zoom_factory(self.ax, base_scale=1.1)
        # figPan = zp.pan_factory(self.ax)
        # figZoom = zp.zoom_factory(self.ax2, base_scale=1.1)
        # figPan = zp.pan_factory(self.ax2)

    def plot_time_series(self, df, filtered_ts=np.array([])):
        """Plot time series."""

        # Ignore timestamp column
        df = df.select_dtypes('number')

        self.ax1.cla()
        self.ax1b.cla()

        # Set displayed gridlines
        self.ax1.grid(True)
        self.ax1b.grid(False)

        # If primary axis not used, switch gridlines to secondary axis
        if self.plot_pri is False and self.plot_sec is True:
            self.ax1.grid(False)
            self.ax1b.grid(True)

        # Event connection to refresh PSD plot upon change of time series x-axis limits
        self.ax1.callbacks.connect('xlim_changed', self.on_xlims_change)

        # Plot primary axis channel time series
        if self.plot_pri is True:
            self.ax1.plot(df.iloc[:, 0], c='dodgerblue', label=df.columns[0], lw=1)
            ylabel = f'{df.columns[0]} ({self.plot_units[0]})'
            self.ax1.set_ylabel(ylabel)

            # Plot filtered time series if exists
            if filtered_ts.size > 0:
                self.ax1.plot(df.index, filtered_ts[:, 0],
                              c='red',
                              ls='--',
                              label=f'{df.columns[0]} (Filtered)',
                              lw=1)
        else:
            self.ax1.yaxis.set_visible(False)

        # Plot secondary axis channel time series
        if self.plot_sec is True:
            self.ax1b.plot(df.iloc[:, -1], c='purple', label=df.columns[-1], lw=1)
            ylabel = f'{df.columns[-1]} ({self.plot_units[-1]})'
            self.ax1b.set_ylabel(ylabel)
            self.ax1b.yaxis.set_visible(True)

            # Plot filtered time series if exists
            if filtered_ts.size > 0:
                self.ax1b.plot(df.index, filtered_ts[:, -1],
                               c='green',
                               ls='--',
                               label=f'{df.columns[-1]} (Filtered)',
                               lw=1)
        else:
            self.ax1b.yaxis.set_visible(False)

        self.ax1.set_xlabel('Time (s)', size=11)

        # Apply axis limits of full dataset if a new file or a file with a different number of columns is loaded
        if self.set_init_axis_limits is True:
            self.ts_xlim = self.init_xlim
            self.ax1.set_xlim(self.init_xlim)
            self.set_init_axis_limits = False
        # Apply currently stored axis limits
        else:
            self.ax1.set_xlim(self.ts_xlim)

        # Tight axes
        self.ax1.margins(x=0, y=0)
        self.ax1b.margins(x=0, y=0)
        # self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        # self.ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=2))
        # plt.sca(self.ax)
        # plt.xticks(rotation=30, ha='right')

    def plot_psd(self, df):
        """Plot PSD."""

        # If the first column is timestamp, drop it (this will be the case but doing the check for generality)
        if df.columns[0] == 'Timestamp':
            df = df.drop(df.columns[0], axis=1)

        self.ax2.cla()
        self.ax2b.cla()
        self.ax2.grid(True)
        self.ax2b.grid(False)

        # If primary axis not used, switch gridlines to secondary axis
        if self.plot_pri is False and self.plot_sec is True:
            self.ax2.grid(False)
            self.ax2b.grid(True)

        # Calculate PSD of selected channels
        f, pxx = self.calc_psd(df)

        # Set x-axis as frequency or period based on plot options
        if self.plot_period:
            # Handle for divide by zero
            f = 1 / f[1:]
            pxx = pxx[:, 1:]
            self.ax2.set_xlabel('Period (s)', size=11)
        else:
            self.ax2.set_xlabel('Frequency (Hz)', size=11)

        # Convert PSD to log10 if plot option selected
        if self.log_scale is True:
            pxx = np.log10(pxx)
            log10 = r'$\mathregular{log_{10}}$'
        else:
            log10 = ''

        # Plot primary axis channel PSD
        if self.plot_pri is True:
            self.ax2.plot(f, pxx[0], c='dodgerblue')
            channel = df.columns[0]
            units = self.plot_units[0]
            ylabel = f'{log10} {channel} PSD ($\mathregular{{({units})^2/Hz}})$'.lstrip()
            self.ax2.set_ylabel(ylabel, size=11)
            self.ax2.yaxis.set_visible(True)
        else:
            self.ax2.yaxis.set_visible(False)

        # Plot secondary axis channel PSD
        if self.plot_sec is True:
            self.ax2b.plot(f, pxx[-1], c='purple')
            channel = df.columns[-1]
            units = self.plot_units[-1]
            ylabel = f'{log10} {channel} PSD ($\mathregular{{({units})^2/Hz}})$'.lstrip()
            self.ax2b.set_ylabel(ylabel, size=11)
            self.ax2b.yaxis.set_visible(True)
        else:
            self.ax2b.yaxis.set_visible(False)

        # Store and set axis limits
        self.ax2.set_xlim(self.psd_xlim)

        # Tight axes
        self.ax2.margins(x=0, y=0)
        self.ax2b.margins(x=0, y=0)

    def calc_psd(self, df):
        """Compute PSD of all channels using the Welch method."""

        # TODO: Unit test this!
        # Sampling frequency
        fs = 1 / (df.index[1] - df.index[0])
        window = self.window.lower()
        if window == 'none':
            window = 'boxcar'
        nperseg = int(len(df) / self.num_ensembles)
        noverlap = nperseg * self.overlap // 100

        try:
            # Note the default Welch parameters are equivalent to running
            # f, pxx = signal.welch(df.T, fs=fs)
            f, pxx = signal.welch(df.T, fs=fs, window=window, nperseg=nperseg, noverlap=noverlap)
        except Exception as e:
            raise ValueError(f'Could not calculate PSD\n{e}')

        # TODO: Dataframe of PSD - give option to export to csv
        # df_psd = pd.DataFrame(pxx.T, index=f)

        # Store nperseg and sampling frequency so that plot settings window is up to date
        self.def_nperseg = int(len(df))
        self.cust_nperseg = nperseg
        self.fs = int(fs)

        return f, pxx

    def plot_title(self, fig, df):
        """Write main plot title."""

        # Store start and end timestamp of plot data for title
        tstart = df.iloc[0, 0].strftime('%d %b %Y %H:%M:%S').lstrip('0')
        tend = df.iloc[-1, 0].strftime('%d %b %Y %H:%M:%S')[-8:]
        self.subtitle = f'{self.logger_id} Logger - {tstart} to {tend}'
        title = self.project + '\n' + self.subtitle
        fig.suptitle(title,
                     # size=16,
                     fontname='tahoma',
                     color=color_2H,
                     weight='bold',
                     )

    def on_xlims_change(self, ax):
        # Convert to datetime
        # self.xmin, self.xmax = mdates.num2date(ax.get_xlim())

        if self.ignore_on_xlim_change is False:
            # Store current time series axis limits
            self.ts_xlim = tuple(round(x, 1) for x in ax.get_xlim())

            # Also store current PSD axis limits so current PSD limits are retained
            self.psd_xlim = tuple(round(x, 1) for x in self.ax2.get_xlim())

            # Update PSD plot and plot title with new timestamp range
            df_slice = self.df_plot[self.ts_xlim[0]:self.ts_xlim[1]]
            self.plot_psd(df_slice)
            self.plot_title(self.fig, df_slice)
            # print(f'updated xlims: {self.ts_xlim}')

    def format_data(self, y):
        """Formats data in plot coords box."""

        # return '%1.3f' % y
        return f'{y:1.3f}'

    def manual_calc_psd(self, df, col, n):
        """Calculate PSD."""

        # Number of samples
        N = len(df)
        s = int(N / n)

        # Time resolution and sampling frequency
        d = (df.index - df.index[0]).total_seconds()[1]
        fs = 1 / d

        for i in range(int(n)):
            t1 = i * s
            t2 = t1 + s
            dfi = df[t1:t2]
            N = len(dfi)

            # PSD of sample
            psdi = abs(np.fft.rfft(dfi[col])) ** 2 / (fs * N)
            psdi = psdi[1:]
            psdi[:-1] *= 2

            # Cumulative PSD
            if i == 0:
                psd = psdi
            else:
                psd = np.add(psd, psdi)

        # Average PSD
        psd = psd / int(n)

        # Spectral frequencies
        freq = np.fft.rfftfreq(N, d)[1:]

        return freq, psd

    # def zoom_factory(self, ax, base_scale=2.):
    #     def zoom_fun(event):
    #         # get the current x and y limits
    #         cur_xlim = ax.get_xlim()
    #         cur_ylim = ax.get_ylim()
    #         cur_xrange = (cur_xlim[1] - cur_xlim[0]) * .5
    #         cur_yrange = (cur_ylim[1] - cur_ylim[0]) * .5
    #         xdata = event.xdata  # get event x location
    #         ydata = event.ydata  # get event y location
    #         if event.button == 'up':
    #             # deal with zoom in
    #             scale_factor = 1 / base_scale
    #         elif event.button == 'down':
    #             # deal with zoom out
    #             scale_factor = base_scale
    #         else:
    #             # deal with something that should never happen
    #             scale_factor = 1
    #             print(event.button)
    #         # set new limits
    #         ax.set_xlim([xdata - cur_xrange * scale_factor,
    #                      xdata + cur_xrange * scale_factor])
    #         ax.set_ylim([ydata - cur_yrange * scale_factor,
    #                      ydata + cur_yrange * scale_factor])
    #         # plt.draw()  # force re-draw
    #         ax.figure.canvas.draw()
    #
    #     fig = ax.get_figure()  # get the figure of interest
    #     # attach the call back
    #     fig.canvas.mpl_connect('scroll_event', zoom_fun)
    #
    #     # return the function
    #     return zoom_fun
    #
    # def read_files_group(self, file, i, n):
    #     # Determine files to read; aim to also read adjacent files in list
    #     # Read files i, i+1
    #     if i == 0:
    #         file1 = file
    #         file2 = self.files_list[i + 1]
    #
    #         dfi = self.read_time_series_file(file1)
    #         df2 = self.read_time_series_file(file2)
    #         df = pd.concat([dfi, df2])
    #
    #     # Read files i-1, i
    #     elif i == n - 1:
    #         file1 = self.files_list[i - 1]
    #         file2 = file
    #
    #         df2 = self.read_time_series_file(file1)
    #         dfi = self.read_time_series_file(file2)
    #         df = pd.concat([df2, dfi])
    #
    #     # Read files i-1, i, i+1
    #     else:
    #         file1 = self.files_list[i - 1]
    #         file2 = file
    #         file3 = self.files_list[i + 1]
    #
    #         # Read logger file
    #         df1 = self.read_time_series_file(file1)
    #         dfi = self.read_time_series_file(file2)
    #         df2 = self.read_time_series_file(file3)
    #         df = pd.concat([df1, dfi, df2])
    #
    #     # Store default xmin, xmax of main file
    #     self.init_xmin = dfi.index[0]
    #     self.init_xmax = dfi.index[-1]
    #
    #     if len(df) > 0:
    #         self.logger_file = file
    #         self.df = df
    #
    #         # Set markers to force new files group to be read
    #         n = len(df)
    #         n1 = int(0.25 * n)
    #         n2 = int(0.75 * n)
    #         self.xmin_bound = df.index[n1]
    #         self.xmax_bound = df.index[n2]
    #
    #         # Need to add time zone for ccmpatibility with matplotlib num2date
    #         self.xmin_bound = self.xmin_bound.tz_localize('UTC')
    #         self.xmax_bound = self.xmax_bound.tz_localize('UTC')
    #
    #         try:
    #             self.update_time_series_plots()
    #         except Exception as e:
    #             msg = 'Unexpected error on plotting logger file'
    #             self.parent.error(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
    #             logging.exception(msg)
    #
    # def extend_backward(self):
    #     df_plot = self.df_plot
    #
    #     # Get file from list we want to load
    #     # i = self.filesList.currentRow()
    #     ix = self.focus_ix
    #
    #     if ix == 0:
    #         return df_plot
    #
    #     # self.filesList.setCurrentRow(i - 1)
    #     file = self.files_list[ix - 2]
    #     df = self.read_time_series_file(file)
    #     df_new = pd.DataFrame()
    #     labels = []
    #
    #     for i, active_pri in enumerate(self.channel_checkstates):
    #         if active_pri:
    #             # Plot label
    #             label = f'{self.channel_names[i]} ({self.units[i]})'
    #             labels.append(label)
    #             df_new[label] = df.iloc[:, i]
    #
    #     # Drop last file
    #     n = 2 * len(df_plot) // 3
    #     df_plot = df_plot.iloc[:n]
    #     df_plot = df_new.append(df_plot)
    #     n = len(df_plot)
    #     n1 = int(0.25 * n)
    #     n2 = int(0.75 * n)
    #     self.xmin_bound = df_plot.index[n1]
    #     self.xmax_bound = df_plot.index[n2]
    #
    #     # Need to add timezone for ccmpatibility with matplotlib num2date
    #     self.xmin_bound = self.xmin_bound.tz_localize('UTC')
    #     self.xmax_bound = self.xmax_bound.tz_localize('UTC')
    #
    #     self.xmin, self.xmax = self.ax.get_xlim()
    #
    #     # Store default xmin, xmax of main file
    #     # n1 = len(df_plot) // 3
    #     # n2 = 2 * len(df_plot) // 3
    #     # self.init_xmin = df_plot.index[n1]
    #     # self.init_xmax = df_plot.index[n2]
    #
    #     self.focus_ix = ix - 1
    #     # self.filesList.setCurrentRow(self.focus_ix)
    #
    #     return df_plot
    #
    # def extend_forward(self):
    #     df_plot = self.df_plot
    #
    #     # Get file from list we want to load
    #     # i = self.filesList.currentRow()
    #     ix = self.focus_ix
    #     print(f'ix={ix}')
    #
    #     if ix == len(self.files_list) - 1:
    #         return df_plot
    #
    #     # self.filesList.setCurrentRow(i + 1)
    #     file = self.files_list[ix + 2]
    #     df = self.read_time_series_file(file)
    #     df_new = pd.DataFrame()
    #     labels = []
    #
    #     for i, active_pri in enumerate(self.channel_checkstates):
    #         if active_pri:
    #             # Plot label
    #             label = f'{self.channel_names[i]} ({self.units[i]})'
    #             labels.append(label)
    #             df_new[label] = df.iloc[:, i]
    #
    #     # Drop first file
    #     n = len(df_plot) // 3
    #     df_plot = df_plot.iloc[n:]
    #     df_plot = df_plot.append(df_new)
    #     n = len(df_plot)
    #     n1 = int(0.25 * n)
    #     n2 = int(0.75 * n)
    #     self.xmin_bound = df_plot.index[n1]
    #     self.xmax_bound = df_plot.index[n2]
    #
    #     # Need to add timezone for ccmpatibility with matplotlib num2date
    #     self.xmin_bound = self.xmin_bound.tz_localize('UTC')
    #     self.xmax_bound = self.xmax_bound.tz_localize('UTC')
    #
    #     self.xmin, self.xmax = self.ax.get_xlim()
    #
    #     # Store default xmin, xmax of main file
    #     # n1 = len(df_plot) // 3
    #     # n2 = 2 * len(df_plot) // 3
    #     # self.init_xmin = df_plot.index[n1]
    #     # self.init_xmax = df_plot.index[n2]
    #
    #     self.focus_ix = ix + 1
    #     # self.filesList.setCurrentRow(self.focus_ix)
    #
    #     return df_plot


class LoggerPlotSettings(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(LoggerPlotSettings, self).__init__(parent)

        # Assign parent objects
        self.parent = parent

        # List of pairs of window combo options and corresponding signal.welch argument
        self.windows = ['None',
                        'Hann',
                        'Hamming',
                        'Bartlett',
                        'Blackman',
                        ]

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle('Logger Plot Settings')

        # Widget sizing policy - prevent expansion
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # Layout
        # self.setFixedSize(400, 300)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addStretch()

        # Title and axes labels form
        form = QtWidgets.QWidget()
        formLayout = QtWidgets.QFormLayout(form)
        self.optProject = QtWidgets.QLineEdit()
        formLayout.addRow(QtWidgets.QLabel('Project title:'), self.optProject)

        # Time series axes limits
        frameTS = QtWidgets.QGroupBox('Time Series Limits')
        grid = QtWidgets.QGridLayout(frameTS)
        self.optTSXmin = QtWidgets.QLineEdit('0')
        self.optTSXmax = QtWidgets.QLineEdit('1')
        # self.optTSYmin = QtWidgets.QLineEdit('0')
        # self.optTSYmax = QtWidgets.QLineEdit('1')
        self.optTSXmin.setFixedWidth(50)
        self.optTSXmax.setFixedWidth(50)
        # self.optTSYmin.setFixedWidth(50)
        # self.optTSYmax.setFixedWidth(50)
        grid.addWidget(QtWidgets.QLabel('X min:'), 0, 0)
        grid.addWidget(self.optTSXmin, 0, 1)
        grid.addWidget(QtWidgets.QLabel('X max:'), 0, 2)
        grid.addWidget(self.optTSXmax, 0, 3)
        # grid.addWidget(QtWidgets.QLabel('Y min:'), 1, 0)
        # grid.addWidget(self.optTSYmin, 1, 1)
        # grid.addWidget(QtWidgets.QLabel('Y max:'), 1, 2)
        # grid.addWidget(self.optTSYmax, 1, 3)

        # PSD axes limits
        framePSD = QtWidgets.QGroupBox('PSD Limits')
        grid = QtWidgets.QGridLayout(framePSD)
        self.optPSDXmin = QtWidgets.QLineEdit('0')
        self.optPSDXmax = QtWidgets.QLineEdit('1')
        # self.optPSDYmin = QtWidgets.QLineEdit('0')
        # self.optPSDYmax = QtWidgets.QLineEdit('1')
        self.optPSDXmin.setFixedWidth(50)
        self.optPSDXmax.setFixedWidth(50)
        # self.optPSDYmin.setFixedWidth(50)
        # self.optPSDYmax.setFixedWidth(50)
        grid.addWidget(QtWidgets.QLabel('X min:'), 0, 0)
        grid.addWidget(self.optPSDXmin, 0, 1)
        grid.addWidget(QtWidgets.QLabel('X max:'), 0, 2)
        grid.addWidget(self.optPSDXmax, 0, 3)
        # grid.addWidget(QtWidgets.QLabel('Y min:'), 1, 0)
        # grid.addWidget(self.optPSDYmin, 1, 1)
        # grid.addWidget(QtWidgets.QLabel('Y max:'), 1, 2)
        # grid.addWidget(self.optPSDYmax, 1, 3)

        # Combine axis limits group
        axesLimits = QtWidgets.QWidget()
        axesLimits.setSizePolicy(policy)
        hbox = QtWidgets.QHBoxLayout(axesLimits)
        hbox.addWidget(frameTS)
        hbox.addWidget(framePSD)

        # Low/high cut-off frequencies group
        freqCutoffsGroup = QtWidgets.QGroupBox('Frequency Cut-offs')
        freqCutoffsGroup.setSizePolicy(policy)
        grid = QtWidgets.QGridLayout(freqCutoffsGroup)

        self.lowCutoff = QtWidgets.QLineEdit('0.05')
        self.lowCutoff.setFixedWidth(50)
        self.highCutoff = QtWidgets.QLineEdit('0.50')
        self.highCutoff.setFixedWidth(50)
        self.lowFreqChkBox = QtWidgets.QCheckBox('Apply cut-off')
        self.lowFreqChkBox.setChecked(True)
        self.highFreqChkBox = QtWidgets.QCheckBox('Apply cut-off')
        self.highFreqChkBox.setChecked(True)
        grid.addWidget(QtWidgets.QLabel('Low freq cut-off (Hz):'), 0, 0)
        grid.addWidget(self.lowCutoff, 0, 1)
        grid.addWidget(self.lowFreqChkBox, 0, 2)
        grid.addWidget(QtWidgets.QLabel('High freq cut-off (Hz):'), 1, 0)
        grid.addWidget(self.highCutoff, 1, 1)
        grid.addWidget(self.highFreqChkBox, 1, 2)

        # Frequency or period radio buttons
        psdXAxisGroup = QtWidgets.QGroupBox('PSD X Axis')
        psdXAxisGroup.setSizePolicy(policy)
        vbox = QtWidgets.QVBoxLayout(psdXAxisGroup)
        self.radioFreq = QtWidgets.QRadioButton('Frequency')
        self.radioPeriod = QtWidgets.QRadioButton('Period')
        vbox.addWidget(self.radioFreq)
        vbox.addWidget(self.radioPeriod)
        self.radioFreq.setChecked(True)

        # PSD log scale checkbox
        self.logScale = QtWidgets.QCheckBox('PSD log scale')
        self.logScale.setChecked(False)

        # Combine PSD x-axis and log scale
        psdOpts = QtWidgets.QWidget()
        hbox = QtWidgets.QHBoxLayout(psdOpts)
        hbox.addWidget(psdXAxisGroup)
        hbox.addWidget(self.logScale)

        # PSD parameters
        # Create a dummy container to maintain correct alignment with other widgets
        psdParams = QtWidgets.QWidget()
        formLayout = QtWidgets.QVBoxLayout(psdParams)
        frame = QtWidgets.QGroupBox('Power Spectral Density Parameters')
        frame.setSizePolicy(policy)
        formLayout.addWidget(frame)

        # Parameters choice
        self.radioDefault = QtWidgets.QRadioButton('Default parameters')
        self.radioWelch = QtWidgets.QRadioButton('Default Welch parameters')
        self.radioCustom = QtWidgets.QRadioButton('Custom parameters')
        self.radioDefault.setChecked(True)

        # PSD parameters form
        params = QtWidgets.QWidget()
        params.setSizePolicy(policy)
        formLayout = QtWidgets.QFormLayout(params)

        self.optNumEnsembles = QtWidgets.QLineEdit()
        self.optWindow = QtWidgets.QComboBox()
        self.optWindow.addItems(self.windows)
        self.optOverlap = QtWidgets.QLineEdit('50')
        self.optNperseg = QtWidgets.QLineEdit()
        self.optFs = QtWidgets.QLineEdit()

        self.optNumEnsembles.setFixedWidth(50)
        self.optOverlap.setFixedWidth(50)
        self.optNperseg.setFixedWidth(50)
        self.optFs.setFixedWidth(50)

        self.optNumEnsembles.setEnabled(False)
        self.optWindow.setEnabled(False)
        self.optOverlap.setEnabled(False)
        self.optNperseg.setEnabled(False)
        self.optFs.setEnabled(False)

        formLayout.addRow(QtWidgets.QLabel('Number of ensembles:'), self.optNumEnsembles)
        formLayout.addRow(QtWidgets.QLabel('Window:'), self.optWindow)
        formLayout.addRow(QtWidgets.QLabel('Window overlap (%):'), self.optOverlap)
        formLayout.addRow(QtWidgets.QLabel('Number of points per ensemble (echo):'), self.optNperseg)
        formLayout.addRow(QtWidgets.QLabel('Sampling frequency (Hz) (echo):'), self.optFs)

        hbox = QtWidgets.QHBoxLayout(frame)
        paramsChoice = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(paramsChoice)
        vbox.addWidget(self.radioDefault)
        vbox.addWidget(self.radioWelch)
        vbox.addWidget(self.radioCustom)
        vbox.setAlignment(QtCore.Qt.AlignTop)
        hbox.addWidget(paramsChoice)
        hbox.addWidget(params)

        # Button box
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                    QtWidgets.QDialogButtonBox.Cancel |
                                                    QtWidgets.QDialogButtonBox.Apply |
                                                    QtWidgets.QDialogButtonBox.Reset)

        # Final layout
        # sectionLabel = QtWidgets.QLabel('Plot Title and Axes Labels')
        # bold = QtGui.QFont()
        # bold.setBold(True)
        # sectionLabel.setFont(bold)
        # mainLayout.addWidget(sectionLabel)
        layout.addWidget(form)
        layout.addWidget(axesLimits)
        layout.addWidget(psdOpts)
        layout.addWidget(freqCutoffsGroup)
        layout.addWidget(psdParams)
        layout.addWidget(self.buttonBox, stretch=0)

    def connect_signals(self):
        self.lowFreqChkBox.toggled.connect(self.set_low_freq_cutoff_state)
        self.highFreqChkBox.toggled.connect(self.set_high_freq_cutoff_state)
        self.radioFreq.toggled.connect(self.switch_psd_xaxis)
        self.radioDefault.toggled.connect(self.switch_welch_params)
        self.radioWelch.toggled.connect(self.switch_welch_params)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.accepted.connect(self.set_params)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.set_params)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Reset).clicked.connect(self.reset_values)

    def set_low_freq_cutoff_state(self):
        if self.lowFreqChkBox.isChecked() is True:
            self.lowCutoff.setEnabled(True)
        else:
            self.lowCutoff.setEnabled(False)

    def set_high_freq_cutoff_state(self):
        if self.highFreqChkBox.isChecked() is True:
            self.highCutoff.setEnabled(True)
        else:
            self.highCutoff.setEnabled(False)

    def get_params(self):
        """Get plot parameters from the time series widget and assign to settings widget."""

        self.optProject.setText(self.parent.project)
        self.optTSXmin.setText(f'{self.parent.ax1.get_xlim()[0]:.1f}')
        self.optTSXmax.setText(f'{self.parent.ax1.get_xlim()[1]:.1f}')
        self.optPSDXmin.setText(f'{self.parent.ax2.get_xlim()[0]:.1f}')
        self.optPSDXmax.setText(f'{self.parent.ax2.get_xlim()[1]:.1f}')

        # Freq cut-offs
        self.lowCutoff.setText(f'{self.parent.low_cutoff:.2f}')
        self.highCutoff.setText(f'{self.parent.high_cutoff:.2f}')

        if self.parent.plot_period is True:
            self.radioPeriod.setChecked(True)
        else:
            self.radioFreq.setChecked(True)

        if self.parent.log_scale is True:
            self.logScale.setChecked(True)
        else:
            self.logScale.setChecked(False)

        # Get PSD parameters
        if self.parent.psd_params_type == 'default':
            self.radioDefault.setChecked(True)
            self.optNumEnsembles.setText(str(self.parent.def_num_ensembles))
            self.optWindow.setCurrentText(self.parent.def_window)
            self.optOverlap.setText(str(self.parent.def_overlap))
            self.optNperseg.setText(str(int(self.parent.def_nperseg)))
        elif self.parent.psd_params_type == 'welch':
            self.radioWelch.setChecked(True)
            self.optNumEnsembles.setText(str(self.parent.welch_num_ensembles))
            self.optWindow.setCurrentText(self.parent.welch_window)
            self.optOverlap.setText(str(self.parent.welch_overlap))
            self.optNperseg.setText(str(int(self.parent.welch_nperseg)))
        else:
            self.radioCustom.setChecked(True)
            self.optNumEnsembles.setText(str(self.parent.cust_num_ensembles))
            self.optWindow.setCurrentText(self.parent.cust_window)
            self.optOverlap.setText(str(self.parent.cust_overlap))
            self.optNperseg.setText(str(int(self.parent.cust_nperseg)))

        # Get sampling frequency
        self.optFs.setText(str(self.parent.fs))

    def set_params(self):
        """Update time series widget class parameters with the plot settings and replot."""

        self.parent.project = self.optProject.text()

        # Check numeric parameters are of valid type
        try:
            # Assign axes limits
            self.parent.ts_xlim = (float(self.optTSXmin.text()), float(self.optTSXmax.text()))
            self.parent.psd_xlim = (float(self.optPSDXmin.text()), float(self.optPSDXmax.text()))

            if self.lowFreqChkBox.isChecked() is True:
                self.parent.apply_low_cutoff = True
                self.parent.low_cutoff = float(self.lowCutoff.text())
            else:
                self.parent.apply_low_cutoff = False

            if self.highFreqChkBox.isChecked() is True:
                self.parent.apply_high_cutoff = True
                self.parent.high_cutoff = float(self.highCutoff.text())
            else:
                self.parent.apply_high_cutoff = False

            # Assign PSD parameters
            self.parent.num_ensembles = float(self.optNumEnsembles.text())
            self.parent.window = self.optWindow.currentText()
            self.parent.overlap = float(self.optOverlap.text())

            # Now apply decimal formatting to plot settings
            self.optTSXmin.setText(str(round(self.parent.ts_xlim[0], 1)))
            self.optTSXmax.setText(str(round(self.parent.ts_xlim[1], 1)))
            self.optPSDXmin.setText(str(round(self.parent.psd_xlim[0], 1)))
            self.optPSDXmax.setText(str(round(self.parent.psd_xlim[1], 1)))
        except ValueError as e:
            # Notify error in main DataLab class
            val = str(e).split("'")[-2]
            self.parent.parent.error(f'Non-numeric input entered: "{val}" - {e}')
        else:
            # Store custom PSD parameters
            if self.radioCustom.isChecked():
                self.parent.cust_num_ensembles = self.parent.num_ensembles
                self.parent.cust_window = self.parent.window
                self.parent.cust_overlap = self.parent.overlap

            # Assign remaining settings to time series class
            self.parent.plot_period = self.radioPeriod.isChecked()
            self.parent.log_scale = self.logScale.isChecked()

            if self.radioDefault.isChecked():
                self.parent.psd_params_type = 'default'
            elif self.radioWelch.isChecked():
                self.parent.psd_params_type = 'welch'
            else:
                self.parent.psd_params_type = 'custom'

            # Check a logger files has already been loaded
            if self.parent.filesList.count() > 0:
                # This flag stops the on_xlims_change event from processing
                self.parent.ignore_on_xlim_change = True
                self.parent.filtered_ts = self.parent.calc_filtered_data(self.parent.df_plot)
                self.parent.update_plots()
                self.parent.ignore_on_xlim_change = False

    def reset_values(self):
        """Reset option settings to initial values set during file load."""

        self.radioFreq.setChecked(True)
        self.logScale.setChecked(False)
        self.optTSXmin.setText(str(round(self.parent.init_xlim[0], 1)))
        self.optTSXmax.setText(str(round(self.parent.init_xlim[1], 1)))
        self.optPSDXmin.setText('0.0')
        self.optPSDXmax.setText('1.0')
        self.radioDefault.setChecked(True)

    def switch_psd_xaxis(self):
        """Switch PSD x-axis limits in the options settings between frequency and period."""

        try:
            xmin, xmax = float(self.optPSDXmin.text()), float(self.optPSDXmax.text())
        except ValueError as e:
            print(f'Axis limits must be numeric - {e}')

        # Default min axis to 0
        self.optPSDXmin.setText('0.0')

        # Set frequency axis - default xlim max to 1 Hz/20s if current xlim min is 0s or 0 Hz respectively
        if self.radioFreq.isChecked():
            if xmin == 0:
                self.optPSDXmax.setText('1.0')
            else:
                self.optPSDXmax.setText(str(1 / xmin))
        # Set period axis
        else:
            if xmin == 0:
                self.optPSDXmax.setText('20.0')
            else:
                self.optPSDXmax.setText(str(1 / xmin))

    def switch_welch_params(self):
        """Switch between default and and custom FFT parameters."""

        self.optNumEnsembles.setEnabled(False)
        self.optWindow.setEnabled(False)
        self.optOverlap.setEnabled(False)

        if self.radioDefault.isChecked():
            self.optNumEnsembles.setText(str(self.parent.def_num_ensembles))
            self.optNperseg.setText(str(self.parent.def_nperseg))
            self.optWindow.setCurrentText(self.parent.def_window)
            self.optOverlap.setText(str(self.parent.def_overlap))
        elif self.radioWelch.isChecked():
            self.optNumEnsembles.setText(str(self.parent.welch_num_ensembles))
            self.optNperseg.setText(str(self.parent.welch_nperseg))
            self.optWindow.setCurrentText(self.parent.welch_window)
            self.optOverlap.setText(str(self.parent.welch_overlap))
        else:
            self.optNumEnsembles.setText(str(self.parent.cust_num_ensembles))
            self.optNperseg.setText(str(self.parent.cust_nperseg))
            self.optWindow.setCurrentText(self.parent.cust_window)
            self.optOverlap.setText(str(self.parent.cust_overlap))
            self.optNumEnsembles.setEnabled(True)
            self.optWindow.setEnabled(True)
            self.optOverlap.setEnabled(True)


# For testing layout
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # win = TimeSeriesPlotWidget()
    win = LoggerPlotSettings()
    win.show()
    sys.exit(app.exec_())

    # np.random.seed(0)
    # start_dates = np.array(['2017-03-10 00:00:00',
    #                         '2017-03-10 00:10:00',
    #                         '2017-03-10 00:20:00'],
    #                        dtype='datetime64')
    # data = np.random.randn(3, 4)
    # # df = pd.DataFrame(data=data, columns=['AccelX', 'AccelY', 'RateX', 'RateY'])
    #
    # header = pd.MultiIndex.from_arrays([['AccelX', 'AccelY', 'RateX', 'RateY'],
    #                                     ['m/s^2', 'm/s^2', 'rad/s', 'rad/s']],
    #                                    names=['channels', 'units'])
    # df = pd.DataFrame(data=data, columns=header)
    # df.insert(loc=0, column='Timestamp', value=start_dates)
    # df = df.set_index('Timestamp')
    #
    # app = QtWidgets.QApplication(sys.argv)
    # w = TimeSeriesPlotWidget()
    # # w.df = df
    # # w.update_time_series_plots()
    # w.show()
    # sys.exit(app.exec_())
