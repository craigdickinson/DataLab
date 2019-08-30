import logging
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

# from gui.gui_zoom_pan_factory import ZoomPan
from app.core.read_files import (
    read_fugro_csv,
    read_logger_hdf5,
    read_logger_txt,
    read_pulse_acc,
)
from app.core.signal_processing import calc_psd, filter_signal

# "2H blue"
color_2H = np.array([0, 49, 80]) / 255


class RawDataDashboard(QtWidgets.QWidget):
    """Create raw time series plots widget."""

    def __init__(self, parent=None):
        super(RawDataDashboard, self).__init__(parent)

        # So can access parent class
        self.parent = parent
        plt.style.use("seaborn")

        self.root = ""
        self.files_list = []
        self.logger_id = ""
        # self.project = 'Project Title'
        self.project = "Total WoS Glendronach Well Monitoring"

        # Plot settings
        self.plot_pri = False
        self.plot_sec = False
        self.plot_period = False
        self.log_scale = False
        self.psd_params_type = "default"
        self.set_init_axis_limits = True
        self.ignore_on_xlim_change = True

        # Column index of channel to plot on pri/sec axis
        self.pri_ix = 1
        self.sec_ix = 0

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

        # Channel names and units in time series file
        self.channel_names = []
        self.current_channels = []
        self.units = []

        self._init_ui()
        self._connect_signals()

        # Instantiate plot settings widget
        self.plotSettings = LoggerPlotSettings(self)

    def _init_ui(self):
        # WIDGETS
        self.openRawButton = QtWidgets.QPushButton("Open Raw Logger File...")
        self.openRawButton.setToolTip("Open raw logger data (*.csv;*.acc) (F2)")
        self.filesLabel = QtWidgets.QLabel("Logger Files")
        self.filesList = QtWidgets.QListWidget()
        self.channelsLabel = QtWidgets.QLabel("Channels (echo)")
        self.channelsList = QtWidgets.QListWidget()
        self.channelsList.setFixedHeight(120)
        self.priLabel = QtWidgets.QLabel("Primary Axis Channel:")
        self.secLabel = QtWidgets.QLabel("Secondary Axis Channel:")
        self.priAxis = QtWidgets.QComboBox()
        self.secAxis = QtWidgets.QComboBox()
        self.priAxis.addItem("None")
        self.secAxis.addItem("None")
        self.line = QtWidgets.QFrame()
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.plotSettingsButton = QtWidgets.QPushButton("Plot Settings...")
        self.replotButton = QtWidgets.QPushButton("Replot")

        # Plot figure and canvas to display figure
        self.fig, (self.ax1, self.ax2) = plt.subplots(2)
        self.ax1.set_title("Time Series", size=12)
        self.ax2.set_title("Power Spectral Density", size=12)
        self.fig.tight_layout()
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # CONTAINERS
        # Setup container
        self.setupWidget = QtWidgets.QWidget()
        self.setupWidget.setFixedWidth(230)
        self.vboxSetup = QtWidgets.QVBoxLayout(self.setupWidget)
        self.vboxSetup.addWidget(self.openRawButton)
        self.vboxSetup.addWidget(self.filesLabel)
        self.vboxSetup.addWidget(self.filesList)
        self.vboxSetup.addWidget(self.channelsLabel)
        self.vboxSetup.addWidget(self.channelsList)
        self.vboxSetup.addWidget(self.priLabel)
        self.vboxSetup.addWidget(self.priAxis)
        self.vboxSetup.addWidget(self.secLabel)
        self.vboxSetup.addWidget(self.secAxis)
        self.vboxSetup.addWidget(self.line)
        self.vboxSetup.addWidget(self.plotSettingsButton)
        self.vboxSetup.addWidget(self.replotButton)

        # Plot container
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(navbar)
        self.vbox.addWidget(self.canvas)

        # LAYOUT
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(self.setupWidget)
        self.layout.addLayout(self.vbox)

    def _connect_signals(self):
        self.plotSettingsButton.clicked.connect(self.on_plot_settings_clicked)
        self.replotButton.clicked.connect(self.on_replot_clicked)
        self.filesList.itemDoubleClicked.connect(self.on_file_double_clicked)

    def on_plot_settings_clicked(self):
        """Show plot options window."""

        # Set current parameters from time series plot widget class
        self.plotSettings.get_params()
        self.plotSettings.show()

    def on_replot_clicked(self):
        """Load and process a selected logger file in the files list."""

        if self.filesList.count() == 0:
            return

        filename = self.filesList.currentItem().text()
        file = os.path.join(self.root, filename)

        try:
            self.load_file(file)
        except ValueError as e:
            self.parent.error(f"Error: {e}")
            logging.exception(e)
        except Exception as e:
            msg = "Unexpected error loading logger file"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def on_file_double_clicked(self):
        self.on_replot_clicked()

    def load_file(self, file):
        """Load logger file, update widget and plot first channel."""

        self.df = self.read_logger_file(file)

        # Store logger ID (assume the first portion of the filename)
        filename = os.path.basename(file)
        self.logger_id = filename.split("_")[0]

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
        self.df_filtered = self.calc_filtered_data(self.df_plot)
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

    @staticmethod
    def read_logger_file(file):
        """Read a raw logger file."""

        ext = file.split(".")[-1].lower()

        if ext == "csv":
            df = read_fugro_csv(file)
        elif ext == "acc":
            df = read_pulse_acc(file)
        elif ext == "h5":
            df = read_logger_hdf5(file)
        elif ext == "txt":
            df = read_logger_txt(file)
        else:
            raise FileNotFoundError(f"No files with the extension {ext} found.")

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

            self.priAxis.addItem("None")
            self.secAxis.addItem("None")
            self.priAxis.addItems(self.channel_names)
            self.secAxis.addItems(self.channel_names)
            self.current_channels = self.channel_names

            if self.channelsList.count() == 0:
                raise ValueError("No channels added")

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

        # Store timestamp column and rename column since original data frame is a multi-index header
        df_plot = df.iloc[:, 0].to_frame()
        df_plot.columns = ["Timestamp"]

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
        """Filter out low frequencies (drift) and high frequencies (noise)."""

        df_raw = df_raw.select_dtypes("number")
        low_cutoff = self.low_cutoff
        high_cutoff = self.high_cutoff

        # Set cut-off values to None if they are not to be applied
        if self.apply_low_cutoff is False:
            low_cutoff = None

        if self.apply_high_cutoff is False:
            high_cutoff = None

        # Apply bandpass filter
        df_filtered = filter_signal(df_raw, low_cutoff, high_cutoff)

        return df_filtered

    def update_plots(self):
        """Create time series plots for selected logger channels."""

        self.draw_axes()

        # Nothing to plot if data frame contains only the Timestamp column
        if len(self.df_plot.columns) == 1:
            return

        try:
            self.plot_time_series(self.df_plot, self.df_filtered)
            self.plot_psd(self.df_plot[self.ts_xlim[0] : self.ts_xlim[1]])
        except ValueError as e:
            self.parent.error(str(e))
        except Exception as e:
            msg = "Unexpected error processing loggers"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

        # Titles and legend
        self.plot_title(self.fig, self.df_plot)
        self.ax1.set_title("Time Series", size=12)
        self.ax2.set_title("Power Spectral Density", size=12)
        self.fig.legend(
            loc="lower center",
            ncol=6,
            fontsize=11,
            # frameon=False,
            # fancybox=False,
            # edgecolor='none',
            # facecolor='none',
        )

        # Ensure plots don't overlap suptitle and legend
        self.fig.tight_layout(
            rect=[0, 0.05, 1, 0.9]
        )  # (rect=[left, bottom, right, top])
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

    def plot_time_series(self, df, df_filtered=pd.DataFrame()):
        """Plot time series."""

        # Ignore timestamp column
        # df = df.select_dtypes("number")
        df = df.iloc[:, 1:]

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
        self.ax1.callbacks.connect("xlim_changed", self.on_xlims_changed)

        # Plot primary axis channel time series
        if self.plot_pri is True:
            self.ax1.plot(df.iloc[:, 0], c="blue", label=df.columns[0], lw=1, alpha=0.8)
            ylabel = f"{df.columns[0]} ({self.plot_units[0]})"
            self.ax1.set_ylabel(ylabel)

            # Plot filtered time series if exists
            if not df_filtered.empty:
                self.ax1.plot(
                    df_filtered.iloc[:, 0],
                    c="red",
                    ls="--",
                    label=f"{df.columns[0]} (Filtered)",
                    lw=1,
                    alpha=0.8,
                )
        else:
            self.ax1.yaxis.set_visible(False)

        # Plot secondary axis channel time series
        if self.plot_sec is True:
            self.ax1b.plot(
                df.iloc[:, -1], c="green", label=df.columns[-1], lw=1, alpha=0.8
            )
            ylabel = f"{df.columns[-1]} ({self.plot_units[-1]})"
            self.ax1b.set_ylabel(ylabel)
            self.ax1b.yaxis.set_visible(True)

            # Plot filtered time series if exists
            if not df_filtered.empty:
                self.ax1b.plot(
                    df_filtered.iloc[:, -1],
                    c="purple",
                    ls="--",
                    label=f"{df.columns[-1]} (Filtered)",
                    lw=1,
                    alpha=0.8,
                )
        else:
            self.ax1b.yaxis.set_visible(False)

        self.ax1.set_xlabel("Time (s)", size=11)

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
        if df.columns[0] == "Timestamp":
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
        f, pxx = self.compute_psd(df)

        # Set x-axis as frequency or period based on plot options
        if self.plot_period:
            # Handle for divide by zero
            f = 1 / f[1:]
            pxx = pxx[:, 1:]
            self.ax2.set_xlabel("Period (s)", size=11)
        else:
            self.ax2.set_xlabel("Frequency (Hz)", size=11)

        # Convert PSD to log10 if plot option selected
        if self.log_scale is True:
            pxx = np.log10(pxx)
            log10 = r"$\mathregular{log_{10}}$"
        else:
            log10 = ""

        # Plot primary axis channel PSD
        if self.plot_pri is True:
            self.ax2.plot(f, pxx[0], c="blue", alpha=0.8)
            channel = df.columns[0]
            units = self.plot_units[0]
            ylabel = (
                f"{log10} {channel} PSD ($\mathregular{{({units})^2/Hz}})$".lstrip()
            )
            self.ax2.set_ylabel(ylabel, size=11)
            self.ax2.yaxis.set_visible(True)
        else:
            self.ax2.yaxis.set_visible(False)

        # Plot secondary axis channel PSD
        if self.plot_sec is True:
            self.ax2b.plot(f, pxx[-1], c="green", alpha=0.8)
            channel = df.columns[-1]
            units = self.plot_units[-1]
            ylabel = (
                f"{log10} {channel} PSD ($\mathregular{{({units})^2/Hz}})$".lstrip()
            )
            self.ax2b.set_ylabel(ylabel, size=11)
            self.ax2b.yaxis.set_visible(True)
        else:
            self.ax2b.yaxis.set_visible(False)

        # Store and set axis limits
        self.ax2.set_xlim(self.psd_xlim)

        # Tight axes
        self.ax2.margins(x=0, y=0)
        self.ax2b.margins(x=0, y=0)

    def compute_psd(self, df):
        """Compute PSD of all channels using the Welch method."""

        # TODO: Unit test this!
        # Sampling frequency
        fs = 1 / (df.index[1] - df.index[0])
        window = self.window.lower()
        if window == "none":
            window = "boxcar"
        nperseg = int(len(df) / self.num_ensembles)
        noverlap = nperseg * self.overlap // 100

        try:
            # Note the default Welch parameters are equivalent to running
            # f, pxx = signal.welch(df.T, fs=fs)
            # f, pxx = signal.welch(
            #     df.T, fs=fs, window=window, nperseg=nperseg, noverlap=noverlap
            # )
            # Calculate PSD using Welch method
            f, pxx = calc_psd(
                data=df.T.values,
                fs=fs,
                window=window,
                nperseg=nperseg,
                noverlap=noverlap,
            )
        except Exception as e:
            raise ValueError(f"Could not calculate PSD\n{e}")

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
        try:
            tstart = df.iloc[0, 0].strftime("%d %b %Y %H:%M:%S").lstrip("0")
            tend = df.iloc[-1, 0].strftime("%d %b %Y %H:%M:%S")[-8:]
            self.subtitle = f"{self.logger_id} Logger - {tstart} to {tend}"
        except:
            self.subtitle = f"{self.logger_id}"

        title = self.project + "\n" + self.subtitle
        fig.suptitle(
            title,
            # size=16,
            fontname="tahoma",
            color=color_2H,
            weight="bold",
        )

    def on_xlims_changed(self, ax):
        # Convert to datetime
        # self.xmin, self.xmax = mdates.num2date(ax.get_xlim())

        if self.ignore_on_xlim_change is False:
            # Store current time series axis limits
            self.ts_xlim = tuple(round(x, 1) for x in ax.get_xlim())

            # Also store current PSD axis limits so current PSD limits are retained
            self.psd_xlim = tuple(round(x, 1) for x in self.ax2.get_xlim())

            # Update PSD plot and plot title with new timestamp range
            df_slice = self.df_plot[self.ts_xlim[0] : self.ts_xlim[1]]
            self.plot_psd(df_slice)
            self.plot_title(self.fig, df_slice)
            # print(f'updated xlims: {self.ts_xlim}')

    @staticmethod
    def format_data(y):
        """Formats data in plot coords box."""

        # return '%1.3f' % y
        return f"{y:1.3f}"

    @staticmethod
    def manual_calc_psd(df, col, n):
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
    #             logging.exception(e)
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

        # Window combo options
        self.windows = ["None", "Hann", "Hamming", "Bartlett", "Blackman"]

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setWindowTitle("Logger Plot Settings")

        # Widget sizing policy - prevent expansion
        policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )

        # WIDGETS
        self.optProject = QtWidgets.QLineEdit()

        # Time series axes limits
        self.optTSXmin = QtWidgets.QLineEdit("0")
        self.optTSXmax = QtWidgets.QLineEdit("1")
        # self.optTSYmin = QtWidgets.QLineEdit('0')
        # self.optTSYmax = QtWidgets.QLineEdit('1')
        self.optTSXmin.setFixedWidth(50)
        self.optTSXmax.setFixedWidth(50)
        # self.optTSYmin.setFixedWidth(50)
        # self.optTSYmax.setFixedWidth(50)

        # PSD axes limits
        self.optPSDXmin = QtWidgets.QLineEdit("0")
        self.optPSDXmax = QtWidgets.QLineEdit("1")
        # self.optPSDYmin = QtWidgets.QLineEdit('0')
        # self.optPSDYmax = QtWidgets.QLineEdit('1')
        self.optPSDXmin.setFixedWidth(50)
        self.optPSDXmax.setFixedWidth(50)
        # self.optPSDYmin.setFixedWidth(50)
        # self.optPSDYmax.setFixedWidth(50)

        # Cut-off frequencies
        self.lowCutoff = QtWidgets.QLineEdit("0.05")
        self.lowCutoff.setFixedWidth(50)
        self.lowCutoff.setEnabled(False)
        self.highCutoff = QtWidgets.QLineEdit("0.50")
        self.highCutoff.setFixedWidth(50)
        self.highCutoff.setEnabled(False)
        self.lowFreqChkBox = QtWidgets.QCheckBox("Apply cut-off")
        self.lowFreqChkBox.setChecked(False)
        self.highFreqChkBox = QtWidgets.QCheckBox("Apply cut-off")
        self.highFreqChkBox.setChecked(False)

        # Frequency/period radio buttons
        self.radioFreq = QtWidgets.QRadioButton("Frequency")
        self.radioFreq.setChecked(True)
        self.radioPeriod = QtWidgets.QRadioButton("Period")

        # PSD log scale checkbox
        self.logScale = QtWidgets.QCheckBox("PSD log scale")
        self.logScale.setChecked(False)

        # PSD parameters
        self.radioDefault = QtWidgets.QRadioButton("Default parameters")
        self.radioWelch = QtWidgets.QRadioButton("Default Welch parameters")
        self.radioCustom = QtWidgets.QRadioButton("Custom parameters")
        self.radioDefault.setChecked(True)
        self.optNumEnsembles = QtWidgets.QLineEdit()
        self.optNumEnsembles.setFixedWidth(50)
        self.optNumEnsembles.setEnabled(False)
        self.optWindow = QtWidgets.QComboBox()
        self.optWindow.addItems(self.windows)
        self.optWindow.setEnabled(False)
        self.optOverlap = QtWidgets.QLineEdit("50")
        self.optOverlap.setFixedWidth(50)
        self.optOverlap.setEnabled(False)
        self.optNperseg = QtWidgets.QLineEdit()
        self.optNperseg.setFixedWidth(50)
        self.optNperseg.setEnabled(False)
        self.optFs = QtWidgets.QLineEdit()
        self.optFs.setFixedWidth(50)
        self.optFs.setEnabled(False)

        # CONTAINERS
        # Title and axes labels form
        self.formTitle = QtWidgets.QFormLayout()
        self.formTitle.addRow(QtWidgets.QLabel("Project title:"), self.optProject)

        # Time series axes limits
        self.frameTS = QtWidgets.QGroupBox("Time Series Limits")
        self.frameTS.setSizePolicy(policy)
        self.grid = QtWidgets.QGridLayout(self.frameTS)
        self.grid.addWidget(QtWidgets.QLabel("X min:"), 0, 0)
        self.grid.addWidget(self.optTSXmin, 0, 1)
        self.grid.addWidget(QtWidgets.QLabel("X max:"), 0, 2)
        self.grid.addWidget(self.optTSXmax, 0, 3)
        # self.grid.addWidget(QtWidgets.QLabel('Y min:'), 1, 0)
        # self.grid.addWidget(self.optTSYmin, 1, 1)
        # self.grid.addWidget(QtWidgets.QLabel('Y max:'), 1, 2)
        # self.grid.addWidget(self.optTSYmax, 1, 3)

        # PSD axes limits
        self.framePSD = QtWidgets.QGroupBox("PSD Limits")
        self.framePSD.setSizePolicy(policy)
        self.grid = QtWidgets.QGridLayout(self.framePSD)
        self.grid.addWidget(QtWidgets.QLabel("X min:"), 0, 0)
        self.grid.addWidget(self.optPSDXmin, 0, 1)
        self.grid.addWidget(QtWidgets.QLabel("X max:"), 0, 2)
        self.grid.addWidget(self.optPSDXmax, 0, 3)
        # self.grid.addWidget(QtWidgets.QLabel('Y min:'), 1, 0)
        # self.grid.addWidget(self.optPSDYmin, 1, 1)
        # self.grid.addWidget(QtWidgets.QLabel('Y max:'), 1, 2)
        # self.grid.addWidget(self.optPSDYmax, 1, 3)

        # Combine axes limits group
        self.hboxLimits = QtWidgets.QHBoxLayout()
        self.hboxLimits.addWidget(self.frameTS)
        self.hboxLimits.addWidget(self.framePSD)
        self.hboxLimits.addStretch()

        # Frequency/period group
        self.psdXAxisGroup = QtWidgets.QGroupBox("PSD X Axis")
        self.psdXAxisGroup.setSizePolicy(policy)
        self.vbox = QtWidgets.QVBoxLayout(self.psdXAxisGroup)
        self.vbox.addWidget(self.radioFreq)
        self.vbox.addWidget(self.radioPeriod)

        # Combine PSD x-axis and log scale
        self.hboxPSD = QtWidgets.QHBoxLayout()
        self.hboxPSD.addWidget(self.psdXAxisGroup)
        self.hboxPSD.addWidget(self.logScale)

        # Cut-off frequencies group
        self.freqCutoffsGroup = QtWidgets.QGroupBox("Cut-off Frequencies")
        self.freqCutoffsGroup.setSizePolicy(policy)
        self.grid = QtWidgets.QGridLayout(self.freqCutoffsGroup)
        self.grid.addWidget(QtWidgets.QLabel("Low freq cut-off (Hz):"), 0, 0)
        self.grid.addWidget(self.lowCutoff, 0, 1)
        self.grid.addWidget(self.lowFreqChkBox, 0, 2)
        self.grid.addWidget(QtWidgets.QLabel("High freq cut-off (Hz):"), 1, 0)
        self.grid.addWidget(self.highCutoff, 1, 1)
        self.grid.addWidget(self.highFreqChkBox, 1, 2)

        # Parameters choice radios
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.radioDefault)
        self.vbox.addWidget(self.radioWelch)
        self.vbox.addWidget(self.radioCustom)
        self.vbox.addStretch()

        # PSD parameters form
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.addRow(
            QtWidgets.QLabel("Number of ensembles:"), self.optNumEnsembles
        )
        self.formLayout.addRow(QtWidgets.QLabel("Window:"), self.optWindow)
        self.formLayout.addRow(QtWidgets.QLabel("Segment overlap (%):"), self.optOverlap)
        self.formLayout.addRow(
            QtWidgets.QLabel("Number of points per ensemble (echo):"), self.optNperseg
        )
        self.formLayout.addRow(
            QtWidgets.QLabel("Sampling frequency (Hz) (echo):"), self.optFs
        )

        # PSD parameters group
        self.paramGroup = QtWidgets.QGroupBox("Power Spectral Density Parameters")
        self.paramGroup.setSizePolicy(policy)
        self.hbox = QtWidgets.QHBoxLayout(self.paramGroup)
        self.hbox.addLayout(self.vbox)
        self.hbox.addLayout(self.formLayout)

        # Button box
        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok
            | QtWidgets.QDialogButtonBox.Cancel
            | QtWidgets.QDialogButtonBox.Apply
            | QtWidgets.QDialogButtonBox.Reset
        )

        # LAYOUT
        # self.setFixedSize(400, 300)
        self.layout = QtWidgets.QVBoxLayout(self)
        # sectionLabel = QtWidgets.QLabel('Plot Title and Axes Labels')
        # bold = QtGui.QFont()
        # bold.setBold(True)
        # sectionLabel.setFont(bold)
        # mainLayout.addWidget(sectionLabel)
        self.layout.addLayout(self.formTitle)
        self.layout.addLayout(self.hboxLimits)
        self.layout.addLayout(self.hboxPSD)
        self.layout.addWidget(self.freqCutoffsGroup)
        self.layout.addWidget(self.paramGroup)
        self.layout.addStretch()
        self.layout.addWidget(self.buttonBox)

    def _connect_signals(self):
        self.lowFreqChkBox.toggled.connect(self.on_low_freq_cutoff_toggled)
        self.highFreqChkBox.toggled.connect(self.on_high_freq_cutoff_toggled)
        self.radioFreq.toggled.connect(self.on_psd_xaxis_type_toggled)
        self.radioDefault.toggled.connect(self.on_psd_params_type_toggled)
        self.radioWelch.toggled.connect(self.on_psd_params_type_toggled)
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.on_ok_clicked
        )
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Reset).clicked.connect(
            self.reset_values
        )

    def on_psd_xaxis_type_toggled(self):
        """Switch PSD x-axis limits in the options settings between frequency and period."""

        try:
            xmin, xmax = float(self.optPSDXmin.text()), float(self.optPSDXmax.text())
        except ValueError as e:
            print(f"Axis limits must be numeric - {e}")

        # Default min axis to 0
        self.optPSDXmin.setText("0.0")

        # Set frequency axis - default xlim max to 1 Hz/20s if current xlim min is 0s or 0 Hz respectively
        if self.radioFreq.isChecked():
            if xmin == 0:
                self.optPSDXmax.setText("1.0")
            else:
                self.optPSDXmax.setText(str(1 / xmin))
        # Set period axis
        else:
            if xmin == 0:
                self.optPSDXmax.setText("20.0")
            else:
                self.optPSDXmax.setText(str(1 / xmin))

    def on_low_freq_cutoff_toggled(self):
        if self.lowFreqChkBox.isChecked():
            self.lowCutoff.setEnabled(True)
        else:
            self.lowCutoff.setEnabled(False)

    def on_high_freq_cutoff_toggled(self):
        if self.highFreqChkBox.isChecked():
            self.highCutoff.setEnabled(True)
        else:
            self.highCutoff.setEnabled(False)

    def on_psd_params_type_toggled(self):
        """Switch between default and custom PSD parameters."""

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

    def on_ok_clicked(self):
        """Update time series widget class parameters with the plot settings and replot."""

        self.parent.project = self.optProject.text()

        # Check numeric parameters are of valid type
        try:
            # Assign axes limits
            self.parent.ts_xlim = (
                float(self.optTSXmin.text()),
                float(self.optTSXmax.text()),
            )
            self.parent.psd_xlim = (
                float(self.optPSDXmin.text()),
                float(self.optPSDXmax.text()),
            )

            if self.lowFreqChkBox.isChecked():
                self.parent.apply_low_cutoff = True
                self.parent.low_cutoff = float(self.lowCutoff.text())
            else:
                self.parent.apply_low_cutoff = False

            if self.highFreqChkBox.isChecked():
                self.parent.apply_high_cutoff = True
                self.parent.high_cutoff = float(self.highCutoff.text())
            else:
                self.parent.apply_high_cutoff = False

            # Assign PSD parameters
            self.parent.num_ensembles = float(self.optNumEnsembles.text())
            self.parent.window = self.optWindow.currentText()
            self.parent.overlap = float(self.optOverlap.text())

            # Apply decimal formatting to axes limits
            self.optTSXmin.setText(str(round(self.parent.ts_xlim[0], 1)))
            self.optTSXmax.setText(str(round(self.parent.ts_xlim[1], 1)))
            self.optPSDXmin.setText(str(round(self.parent.psd_xlim[0], 1)))
            self.optPSDXmax.setText(str(round(self.parent.psd_xlim[1], 1)))
        except ValueError as e:
            # Notify error in main DataLab class
            self.parent.parent.error(f"Non-numeric input entered: {e}")
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
                self.parent.psd_params_type = "default"
            elif self.radioWelch.isChecked():
                self.parent.psd_params_type = "welch"
            else:
                self.parent.psd_params_type = "custom"

            # Check logger files have already been loaded
            if self.parent.filesList.count() > 0:
                # This flag stops the on_xlims_change event from processing
                self.parent.ignore_on_xlim_change = True
                self.parent.df_filtered = self.parent.calc_filtered_data(
                    self.parent.df_plot
                )
                self.parent.update_plots()
                self.parent.ignore_on_xlim_change = False

    def get_params(self):
        """Get plot parameters from the time series widget and assign to settings widget."""

        self.optProject.setText(self.parent.project)
        # self.optTSXmin.setText(f"{self.parent.ax1.get_xlim()[0]:.1f}")
        # self.optTSXmax.setText(f"{self.parent.ax1.get_xlim()[1]:.1f}")
        # self.optPSDXmin.setText(f"{self.parent.ax2.get_xlim()[0]:.1f}")
        # self.optPSDXmax.setText(f"{self.parent.ax2.get_xlim()[1]:.1f}")
        self.optTSXmin.setText(str(self.parent.ax1.get_xlim()[0]))
        self.optTSXmax.setText(str(self.parent.ax1.get_xlim()[1]))
        self.optPSDXmin.setText(str(self.parent.ax2.get_xlim()[0]))
        self.optPSDXmax.setText(str(self.parent.ax2.get_xlim()[1]))

        # Freq cut-offs
        # self.lowCutoff.setText(f"{self.parent.low_cutoff:.2f}")
        # self.highCutoff.setText(f"{self.parent.high_cutoff:.2f}")
        self.lowCutoff.setText(str(self.parent.low_cutoff))
        self.highCutoff.setText(str(self.parent.high_cutoff))

        if self.parent.plot_period is True:
            self.radioPeriod.setChecked(True)
        else:
            self.radioFreq.setChecked(True)

        if self.parent.log_scale is True:
            self.logScale.setChecked(True)
        else:
            self.logScale.setChecked(False)

        # Get PSD parameters
        if self.parent.psd_params_type == "default":
            self.radioDefault.setChecked(True)
            self.optNumEnsembles.setText(str(self.parent.def_num_ensembles))
            self.optWindow.setCurrentText(self.parent.def_window)
            self.optOverlap.setText(str(self.parent.def_overlap))
            self.optNperseg.setText(str(int(self.parent.def_nperseg)))
        elif self.parent.psd_params_type == "welch":
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

    def reset_values(self):
        """Reset option settings to initial values set during file load."""

        self.radioFreq.setChecked(True)
        self.logScale.setChecked(False)
        self.optTSXmin.setText(str(round(self.parent.init_xlim[0], 1)))
        self.optTSXmax.setText(str(round(self.parent.init_xlim[1], 1)))
        self.optPSDXmin.setText("0.0")
        self.optPSDXmax.setText("1.0")
        self.radioDefault.setChecked(True)


# For testing layout
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # win = RawDataDashboard()
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
