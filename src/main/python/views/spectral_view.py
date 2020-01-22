"""Spectral screening dashboard gui view."""

__author__ = "Craig Dickinson"

import logging
import sys
from datetime import datetime, timedelta

import math
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib import cm
from matplotlib import gridspec
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

# To resolve a pandas warning in using timestamps with matplotlib - to investigate
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()

# 2H blue colour font
color_2H = np.array([0, 49, 80]) / 255

# Title style args
title_args = dict(size=14, fontname="tahoma", color=color_2H, weight="bold")


class SpectrogramWidget(QtWidgets.QWidget):
    """Spectrogram plot tab widget. Creates layout and all contains plotting routines."""

    def __init__(self, parent=None):
        super(SpectrogramWidget, self).__init__(parent)

        # So can access parent class
        self.parent = parent
        plt.style.use("seaborn")
        # plt.style.use("default")
        # plt.style.use('seaborn-pastel')
        # plt.style.use('bmh')

        self.project = "Project Title"  # 'Total WoS Glendronach Well Monitoring'
        self.datasets = {}
        self.nat_freqs = {}
        self.index = []
        self.index_is_dates = True
        self.t = 0
        self.freqs = np.array([])
        self.z = np.array([])
        self.zmin = 0
        self.zmax = 0
        self.ts_i = 0

        # Initial axis limits upon loading a file
        self.init_xlim = (0.0, 3.0)
        self.xlim = (0.0, 3.0)
        self.log_scale = False

        # Placeholder for colorbar, plot line and label handles
        self.cbar = None
        self.event_line = None
        self.psd_line = None
        self.label = None
        self.skip_on_slider_change_event = False

        self._init_ui()
        self._connect_signals()

        # Initialise axes
        self._draw_axes()
        self.canvas.draw()

        # Instantiate plot settings widget
        self.plotSettings = SpectroPlotSettings(self)

    def _init_ui(self):
        # WIDGETS
        self.openSpectButton = QtWidgets.QPushButton("Open Spectrograms...")
        self.openSpectButton.setToolTip("Open logger spectrograms (*.h5;*.csv;*.xlsx) (F4)")
        self.lblDatasets = QtWidgets.QLabel("Loaded Datasets")
        self.datasetsList = QtWidgets.QListWidget()
        self.datasetsList.setFixedHeight(100)
        self.lblIndex = QtWidgets.QLabel("Timestamps (reversed)")
        self.timestampList = QtWidgets.QListWidget()
        self.slider = QtWidgets.QSlider()
        self.slider.setOrientation(QtCore.Qt.Vertical)
        self.slider.setValue(50)
        self.openPlotSettingsButton = QtWidgets.QPushButton("Plot Settings...")
        self.calcNatFreqButton = QtWidgets.QPushButton("Estimate Nat. Freq.")
        self.clearDatasetsButton = QtWidgets.QPushButton("Clear Datasets")

        # Plot canvas
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # Natural frequency calculation label
        self.natFreq = QtWidgets.QLabel()
        self.natFreq.setToolTip(
            "The natural response is estimated by evaluating the mean peak frequency "
            "of all events between 0.2 Hz and 2.0 Hz.\n"
            "This assumes the wave energy is ignored."
        )
        font = QtGui.QFont()
        font.setPointSize(12)
        self.natFreq.setFont(font)

        # Widget sizing policy - prevent vertical expansion
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.natFreq.setSizePolicy(policy)

        # CONTAINERS
        # Selection layout
        self.selection = QtWidgets.QWidget()
        self.selection.setMinimumWidth(200)
        self.grid = QtWidgets.QGridLayout(self.selection)
        self.grid.addWidget(self.openSpectButton, 0, 0)
        self.grid.addWidget(self.clearDatasetsButton, 1, 0)
        self.grid.addWidget(self.lblDatasets, 2, 0)
        self.grid.addWidget(self.datasetsList, 3, 0)
        self.grid.addWidget(self.lblIndex, 4, 0)
        self.grid.addWidget(self.timestampList, 5, 0)
        self.grid.addWidget(self.slider, 5, 1)
        self.grid.addWidget(self.openPlotSettingsButton, 6, 0)
        self.grid.addWidget(self.calcNatFreqButton, 7, 0)

        # Plot layout
        # Create plot figure, canvas widget to display figure and navbar
        self.plotWidget = QtWidgets.QWidget()
        self.vbox = QtWidgets.QVBoxLayout(self.plotWidget)
        self.vbox.addWidget(navbar)
        self.vbox.addWidget(self.canvas)
        self.vbox.addWidget(self.natFreq)

        # Splitter to allow resizing of widget containers
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.selection)
        splitter.addWidget(self.plotWidget)
        splitter.setSizes([200, 10000])

        # LAYOUT
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(splitter)

    def _connect_signals(self):
        self.calcNatFreqButton.clicked.connect(self.on_calc_nat_freq_clicked)
        self.clearDatasetsButton.clicked.connect(self.on_clear_datasets_clicked)
        self.openPlotSettingsButton.clicked.connect(self.on_open_plot_settings_clicked)
        self.datasetsList.itemDoubleClicked.connect(self.on_dataset_double_clicked)
        self.timestampList.itemDoubleClicked.connect(self.on_timestamp_list_double_clicked)
        self.slider.valueChanged.connect(self.on_slider_changed)

    def _draw_axes(self):
        self.fig.clf()
        gs = gridspec.GridSpec(nrows=2, ncols=1, height_ratios=[4, 1])
        self.ax1 = self.fig.add_subplot(gs[0])
        self.ax2 = self.fig.add_subplot(gs[1], sharex=self.ax1)

        # plt.figure(self.fig.number)
        # self.ax1 = plt.subplot2grid(shape=(4, 1), loc=(0, 0), rowspan=3)
        # self.ax2 = plt.subplot2grid(shape=(4, 1), loc=(3, 0), sharex=self.ax1)

        self.ax1.get_xaxis().set_visible(False)
        self.fig.subplots_adjust(hspace=0.05)

    def on_clear_datasets_clicked(self):
        self.clear_dashboard()

    def on_open_plot_settings_clicked(self):
        self.plotSettings.set_dialog_data()
        self.plotSettings.show()

    def on_dataset_double_clicked(self):
        """Plot spectrogram."""

        try:
            self.create_plots()

            # Check dataset key exists
            dataset = self.datasetsList.currentItem().text()
            if dataset in self.nat_freqs:
                mean_nat_freq = self.nat_freqs[dataset]
                self.natFreq.setText(
                    f"Estimated natural response: {mean_nat_freq:.2f} Hz, {1 / mean_nat_freq:.2f} s"
                )
            else:
                self.natFreq.setText("")
        except Exception as e:
            msg = "Unexpected error on spectrogram dataset double click"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def on_slider_changed(self):
        """Update event PSD plot."""

        # Ignore if initial spectrogram is being plotted
        if self.skip_on_slider_change_event is True:
            return

        try:
            i = self.slider.value()
            n = self.slider.maximum()
            row = n - i
            self.timestampList.setCurrentRow(row)

            if self.timestampList.count() > 0:
                t = self.index[i]

                # Update plot data (faster than replotting)
                if self.index_is_dates:
                    t_psd = mdates.date2num(t)
                else:
                    t_psd = t

                self._update_event_marker(t_psd)
                self._update_psd_plot(i)
                self.canvas.draw()
                self.canvas.flush_events()
        except Exception as e:
            msg = "Unexpected error on spectrogram slider change"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def on_timestamp_list_double_clicked(self):
        """Update the PSD event slice for the selected timestamp."""

        # Timestamp list is in reverse order so index needs to be inverted
        i = self.timestampList.currentRow()
        n = self.timestampList.count()
        self.slider.setValue(n - i - 1)

    def on_calc_nat_freq_clicked(self):
        """Estimate mean natural frequency for selected dataset."""

        if self.datasetsList.count() == 0:
            return self.parent.error("No data currently plotted. Load a spectrogram file first.")

        # self.parent.statusbar.showMessage('Calculating estimate natural frequency...')
        dataset = self.datasetsList.currentItem().text()
        df = self.datasets[dataset]

        # Get the frequency of the max PSD in the given frequency range for all events
        nat_freqs = np.array(
            [
                df.iloc[i][(df.iloc[i].index > 0.2) & (df.iloc[i].index < 2.0)].idxmax()
                for i in range(len(df))
            ]
        )

        mean_nat_freq = nat_freqs.mean()

        # Store natural frequency in dictionary and write to plot widget
        self.nat_freqs[dataset] = mean_nat_freq
        self.natFreq.setText(
            f"Estimated natural response: {mean_nat_freq:.2f} Hz, {1 / mean_nat_freq:.2f} s"
        )
        # self.parent.statusbar.showMessage('')

    def clear_dashboard(self):
        """Clear all stored spectrogram datasets and reset layout."""

        self.datasets = {}
        self.nat_freqs = {}
        self.index = []
        self.datasetsList.clear()
        self.timestampList.clear()
        self.natFreq.setText("")
        self._draw_axes()
        self.canvas.draw()

    def append_spect_to_datasets_list(self, dataset_id):
        """Add loaded spectrogram to datasets list."""

        self.datasetsList.addItem(dataset_id)
        n = self.datasetsList.count()
        self.datasetsList.setCurrentRow(n - 1)

    def append_multiple_spect_to_datasets_list(self, dataset_ids):
        """Add multiple spectrogram to datasets list."""

        self.datasetsList.addItems(dataset_ids)
        self.datasetsList.setCurrentRow(0)

    def create_plots(self, set_init_xlim=False):
        """Create spectrograms plots dashboard."""

        try:
            self._set_plot_data()
            if set_init_xlim is True:
                self._set_init_xlim()
            self._draw_axes()
            self._plot_spectrogram()
            self._plot_event_psd()
        except Exception as e:
            msg = "Unexpected error plotting spectrogram"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def _set_init_xlim(self):
        """Set spectrogram plot frequency limits on loading a file."""

        self.xlim = (self.freqs.min(), self.freqs.max())
        self.init_xlim = self.xlim

    def _set_plot_data(self):
        """Retrieve spectrogram dataset from list and extract relevant data."""

        # Get plot data
        dataset = self.datasetsList.currentItem().text()
        df = self.datasets[dataset]

        # Extract data
        self.index = df.index
        self.freqs = df.columns.values

        # Determine if have a datetime or numeric index
        if isinstance(self.index[0], datetime):
            self.index_is_dates = True
        else:
            self.index_is_dates = False

        if self.log_scale is True:
            self.z = np.log10(df.values)

            # Replace any inf values with nan
            self.z[np.isinf(self.z)] = np.nan
        else:
            self.z = df.values

        # Min/max amplitudes
        self.zmin = math.floor(np.nanmin(self.z))

        # If amplitudes are < 1 don't integer round (need to plot on a smaller scale)
        if self.z.max() < 1:
            self.zmax = self.z.max()
        else:
            self.zmax = math.ceil(np.nanmax(self.z))

        # Populate index/timestamps list and update list label
        if self.index_is_dates:
            idx = [t.strftime("%Y-%m-%d %H:%M") for t in reversed(self.index)]
            self.lblIndex.setText("Timestamps (reversed)")
        else:
            idx = [str(t) for t in reversed(self.index)]
            self.lblIndex.setText("File Numbers (reversed)")

        self.timestampList.clear()
        self.timestampList.addItems(idx)

        # Set slider to middle event
        # if self.slider.value() == 50:
        n = len(self.index)
        i = n // 2 - 1
        j = n - i - 1
        self.ts_i = i

        # Update slider parameters but disable its event change while setting up plot
        self.skip_on_slider_change_event = True
        self.slider.setMaximum(n - 1)
        self.slider.setValue(i)
        self.skip_on_slider_change_event = False
        self.timestampList.setCurrentRow(j)
        self.t = self.index[i]

    def _plot_spectrogram(self):
        ax1 = self.ax1
        ax2 = self.ax2
        ax1.grid(False)

        f0 = self.freqs[0]
        f1 = self.freqs[-1]

        # Set colour map
        cmap = cm.get_cmap("coolwarm")

        # Continuous contour plot option
        # t0 = mdates.date2num(self.index[0])
        # t1 = mdates.date2num(self.index[-1])
        # im = ax1.imshow(
        #     self.z,
        #     aspect="auto",
        #     interpolation="bilinear",
        #     origin="lower",
        #     extent=[f0, f1, t0, t1],
        #     cmap=cmap,
        # )

        # Contour plot with discrete levels (z must be at least a 2x2 array)
        try:
            im = ax1.contourf(self.freqs, self.index, self.z, cmap=cmap)
        except TypeError:
            if len(self.z) == 1:
                msg = "Warning plotting spectrograms: Cannot plot a spectrogram for only one event."
                self.parent.warning(msg)

        # ticks = np.linspace(self.zmin, self.zmax, 8, endpoint=True)
        # im = ax1.contourf(self.freqs, self.index, self.z, levels=ticks, cmap=cmap)

        if self.log_scale is True:
            log10 = r"$\mathregular{log_{10}}$"
        else:
            log10 = ""

        # Plot event slice line for middle index/timestamp
        if self.index_is_dates:
            ti = mdates.date2num(self.t)
        else:
            ti = self.t
        (self.event_line,) = ax1.plot([f0, f1], [ti, ti], "k--")

        self._set_title()
        ax1.margins(0)
        ax1.set_xlim(self.xlim)

        if self.index_is_dates:
            ax1.yaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            ax1.yaxis.set_major_locator(mdates.DayLocator(interval=7))
        else:
            ax1.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax1.set_ylabel("File Number (Load Case)")

        # Maximise figure space before applying colour bar as colour bar will not reposition if applied after
        self.fig.tight_layout(rect=[0, 0.1, 1, 0.92])  # (rect=[left, bottom, right, top])

        # Apply colour bar
        try:
            self.cbar = self.fig.colorbar(im, ax=[ax1, ax2])
        except UnboundLocalError:
            pass
        # self.cbar = self.fig.colorbar(im, ax=[ax1, ax2], ticks=ticks)

        # TODO: Store and read units!
        units = r"$\mathregular{(units/s^2)^2/Hz}$"
        label = f"{log10}PSD ({units})".lstrip()
        try:
            self.cbar.set_label(label)
        except AttributeError:
            pass
        # self.cbar.ax.tick_params(length=3.5)
        # self.cbar.outline.set_edgecolor('black')
        # self.cbar.outline.set_linewidth(1)

        # plt.sca(ax1)
        # plt.xticks(fontsize=11)
        # plt.yticks(fontsize=11)

    def _plot_event_psd(self):
        """Plot PSD of spectrogram timestamp slice."""

        # Slice spectrogram dataset at middle index/timestamp
        i = self.ts_i
        zi = self.z[i, :]

        # Create legend label
        label = self._get_psd_label(i)

        self.ax2.cla()
        # self.ax2.patch.set_facecolor('none')
        (self.psd_line,) = self.ax2.plot(self.freqs, zi, "k")
        self.ax2.set_ylim(self.zmin, self.zmax)
        self.ax2.margins(0)
        self.ax2.set_xlabel("Frequency (Hz)")
        self.ax2.set_ylabel("PSD")
        self.label = self.ax2.annotate(
            label,
            xy=(1, 1),
            xycoords="axes fraction",
            xytext=(-2, -10),
            textcoords="offset points",
            ha="right",
        )
        self.canvas.draw()

    def _update_event_marker(self, t):
        self.event_line.set_ydata([t, t])

    def _update_psd_plot(self, i):
        """Update PSD plot data for selected timestamp slice of spectrogram."""

        # Slice spectrogram data frame for timestamp index i
        zi = self.z[i, :]

        # Create new legend label
        label = self._get_psd_label(i)

        # Update plot data and label text
        self.psd_line.set_ydata(zi)
        self.label.set_text(label)

    def _get_psd_label(self, i):
        """
        Create new legend label for PSD plot.
        :param i: Timestamp or file number list index
        :return: PSD legend label
        """

        if self.index_is_dates:
            ts1 = self.index[i]
            msg_d1 = ts1.strftime("%d %b %Y %H:%M").lstrip("0")

            # Get time delta between selected index and next one
            try:
                ts2 = self.index[i + 1]
                msg_d2 = ts2.strftime("%d %b %Y %H:%M")[-5:]
                label = " ".join((msg_d1, "to", msg_d2))
            except:
                label = msg_d1
        else:
            label = f"File {self.index[i]}"

        return label

    def _set_title(self):
        """Set plot title."""

        # Attempt to retrieve title from project setup dashboard
        project_name = self.parent.inputDataModule.control.project_name
        campaign_name = self.parent.inputDataModule.control.campaign_name

        if project_name == "":
            project_name = "Project Title"
        if campaign_name == "":
            campaign_name = "Campaign Title"

        dataset = self.datasetsList.currentItem().text()
        title = f"{project_name} - {campaign_name}\n{dataset} Spectrogram"
        self.ax1.set_title(title, **title_args)


class SpectroPlotSettings(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(SpectroPlotSettings, self).__init__(parent)

        # Assign parent objects
        self.parent = parent

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setWindowTitle("Spectrogram Plot Settings")

        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # WIDGETS
        # Title
        self.optProject = QtWidgets.QLineEdit()

        # Frequency axis limits
        self.optFreqMin = QtWidgets.QLineEdit("0")
        self.optFreqMax = QtWidgets.QLineEdit("3")
        self.optFreqMin.setFixedWidth(50)
        self.optFreqMax.setFixedWidth(50)

        # PSD log scale checkbox
        self.logScale = QtWidgets.QCheckBox("PSD log scale")
        self.logScale.setChecked(False)

        # Button box
        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok
            | QtWidgets.QDialogButtonBox.Cancel
            | QtWidgets.QDialogButtonBox.Apply
            | QtWidgets.QDialogButtonBox.Reset
        )

        # CONTAINERS
        # Title and axes labels form
        self.form = QtWidgets.QFormLayout()
        self.form.addRow(QtWidgets.QLabel("Project title:"), self.optProject)

        # Frequency axis limits
        self.frameFreq = QtWidgets.QGroupBox("Frequency Axis")
        self.frameFreq.setSizePolicy(policy)
        self.form2 = QtWidgets.QFormLayout(self.frameFreq)
        self.form2.addRow(QtWidgets.QLabel("Min:"), self.optFreqMin)
        self.form2.addRow(QtWidgets.QLabel("Max:"), self.optFreqMax)

        # Combine PSD x-axis and log scale
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.logScale)

        # LAYOUT
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addLayout(self.form)
        self.layout.addWidget(self.frameFreq)
        self.layout.addLayout(self.vbox)
        self.layout.addStretch()
        self.layout.addWidget(self.buttonBox, stretch=0, alignment=QtCore.Qt.AlignRight)

    def _connect_signals(self):
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.on_ok_clicked)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Reset).clicked.connect(self.reset_values)

    def set_dialog_data(self):
        """Get plot parameters from the spectrogram widget and assign to settings widget."""

        self.optProject.setText(self.parent.project)
        self.optFreqMin.setText(str(round(self.parent.ax1.get_xlim()[0], 3)))
        self.optFreqMax.setText(str(round(self.parent.ax1.get_xlim()[1], 3)))
        self.logScale.setChecked(self.parent.log_scale)

    def on_ok_clicked(self):
        """Update spectrogram widget class parameters with the plot settings and replot."""

        self.parent.project = self.optProject.text()

        # Check numeric parameters are of valid type
        try:
            # Assign axes limits
            self.parent.xlim = (float(self.optFreqMin.text()), float(self.optFreqMax.text()))

            # Now apply decimal formatting to plot settings
            self.optFreqMin.setText(str(round(self.parent.xlim[0], 3)))
            self.optFreqMax.setText(str(round(self.parent.xlim[1], 3)))
        except ValueError as e:
            # Notify error in main DataLab class
            val = str(e).split("'")[-2]
            self.parent.parent.error(f'Non-numeric input entered: "{val}" - {e}')
        else:
            # Assign settings to spectrogram class
            self.parent.log_scale = self.logScale.isChecked()

            # Check a spectrogram dataset has already been loaded
            if self.parent.datasetsList.count() > 0:
                self.parent.create_plots()

    def reset_values(self):
        """Reset option settings to initial values set during file load."""

        # Pointer to spectrogram widget class
        self.logScale.setChecked(True)
        self.optFreqMin.setText(str(round(self.parent.init_xlim[0], 1)))
        self.optFreqMax.setText(str(round(self.parent.init_xlim[1], 1)))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = SpectrogramWidget()
    # win = SpectroPlotSettings()
    win.show()
    sys.exit(app.exec_())
