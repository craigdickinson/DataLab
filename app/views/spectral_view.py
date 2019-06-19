import logging
import sys
from datetime import timedelta

import math
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib import cm
from matplotlib import gridspec
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

# To resolve a pandas warning in using timestamps with matplotlib - to investigate
from pandas.plotting import register_matplotlib_converters

register_matplotlib_converters()


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
        self.skip_on_slider_change_event = False

        self._init_ui()
        self._connect_signals()

        # Initialise axes
        self._draw_axes()
        self.canvas.draw()

        # Instantiate plot settings widget
        self.plotSettings = SpectroPlotSettings(self)

    def _init_ui(self):
        # Main layout
        layout = QtWidgets.QHBoxLayout(self)

        # Selection layout
        selection = QtWidgets.QWidget()
        selection.setFixedWidth(170)
        grid = QtWidgets.QGridLayout(selection)

        self.openSpectButton = QtWidgets.QPushButton("Open Spectrograms")
        self.openSpectButton.setToolTip("Open logger spectrograms (*.h5;*.csv;*.xlsx) (F4)")
        lbl = QtWidgets.QLabel("Loaded Datasets")
        self.datasetList = QtWidgets.QListWidget()
        self.datasetList.setFixedHeight(100)
        self.datetimeEdit = QtWidgets.QDateTimeEdit()
        lbl2 = QtWidgets.QLabel("Timestamps (reversed)")
        self.timestampList = QtWidgets.QListWidget()

        self.slider = QtWidgets.QSlider()
        self.slider.setOrientation(QtCore.Qt.Vertical)
        self.slider.setValue(50)

        self.openPlotSettingsButton = QtWidgets.QPushButton("Plot Settings")
        self.calcNatFreqButton = QtWidgets.QPushButton("Estimate Nat. Freq.")
        self.clearDatasetsButton = QtWidgets.QPushButton("Clear Datasets")

        grid.addWidget(self.openSpectButton, 0, 0)
        grid.addWidget(self.clearDatasetsButton, 1, 0)
        grid.addWidget(lbl, 2, 0)
        grid.addWidget(self.datasetList, 3, 0)
        grid.addWidget(self.datetimeEdit, 4, 0)
        grid.addWidget(lbl2, 5, 0)
        grid.addWidget(self.timestampList, 6, 0)
        grid.addWidget(self.slider, 6, 1)
        grid.addWidget(self.openPlotSettingsButton, 7, 0)
        grid.addWidget(self.calcNatFreqButton, 8, 0)

        # Plot layout
        # Create plot figure, canvas widget to display figure and navbar
        plot = QtWidgets.QWidget()
        plotLayout = QtWidgets.QGridLayout(plot)
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

        # Widget sizing policy - prevent vertical expansion
        policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
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

    def _connect_signals(self):
        self.calcNatFreqButton.clicked.connect(self.on_calc_nat_freq_clicked)
        self.clearDatasetsButton.clicked.connect(self.on_clear_datasets_clicked)
        self.openPlotSettingsButton.clicked.connect(self.on_open_plot_settings_clicked)
        self.datasetList.itemDoubleClicked.connect(self.on_dataset_double_clicked)
        self.timestampList.itemDoubleClicked.connect(
            self.on_timestamp_list_double_clicked
        )
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
        """Clear all stored spectrogram datasets and reset layout."""
        self.datasets = {}
        self.nat_freqs = {}
        self.timestamps = []
        self.datasetList.clear()
        self.timestampList.clear()
        self.natFreq.setText("")
        self._draw_axes()
        self.canvas.draw()

    def on_open_plot_settings_clicked(self):
        self.plotSettings.get_params()
        self.plotSettings.show()

    def on_dataset_double_clicked(self):
        """Plot spectrogram."""

        self.create_plots()

        # Check dataset key exists
        dataset = self.datasetList.currentItem().text()
        if dataset in self.nat_freqs:
            mean_nat_freq = self.nat_freqs[dataset]
            self.natFreq.setText(
                f"Estimated natural response: {mean_nat_freq:.2f} Hz, {1 / mean_nat_freq:.2f} s"
            )
        else:
            self.natFreq.setText("")

    def on_slider_changed(self):
        """Update event PSD plot."""

        # Ignore if initial spectrogram is being plotted
        if self.skip_on_slider_change_event is True:
            return

        i = self.slider.value()
        n = self.slider.maximum()
        row = n - i
        self.timestampList.setCurrentRow(row)

        if self.timestampList.count() > 0:
            t = self.timestamps[i]
            self._set_datetime_edit(t)

            # Update plot data (faster than replotting)
            t_psd = mdates.date2num(t)
            self._update_event_marker(t_psd)
            self._update_psd_plot(i)
            self.canvas.draw()
            self.canvas.flush_events()

    def on_timestamp_list_double_clicked(self):
        """Update the PSD event slice for the selected timestamp."""

        # Timestamp list is in reverse order so index needs to be inverted
        i = self.timestampList.currentRow()
        n = self.timestampList.count()
        self.slider.setValue(n - i - 1)

    def on_calc_nat_freq_clicked(self):
        """Estimate mean natural frequency for selected dataset."""

        if self.datasetList.count() == 0:
            self.parent.error(
                "No data currently plotted. Load a spectrogram file first."
            )
            return

        # self.parent.statusbar.showMessage('Calculating estimate natural frequency...')
        dataset = self.datasetList.currentItem().text()
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

    def update_spect_datasets_list(self, logger):
        """Populate loaded datasets list."""

        self.logger_names = logger
        self.datasetList.addItem(logger)
        n = self.datasetList.count()
        self.datasetList.setCurrentRow(n - 1)

        # Get and plot data
        try:
            self.create_plots()
        except Exception as e:
            msg = "Unexpected error loading plotting spectrogram"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def create_plots(self):
        """Create spectrograms plots dashboard."""

        self._set_plot_data()
        self._draw_axes()
        self._plot_spectrogram()
        self._plot_event_psd()

    def _set_datetime_edit(self, t):
        yr = t.year
        mth = t.month
        day = t.day
        hr = t.hour
        m = t.minute
        dt = QtCore.QDateTime(yr, mth, day, hr, m)
        self.datetimeEdit.setDateTime(dt)

    def _set_plot_data(self):
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
        self.zmin = math.floor(self.z.min())
        self.zmax = math.ceil(self.z.max())

        # Populate timestamps list
        self.timestampList.clear()
        [
            self.timestampList.addItem(t.strftime("%Y-%m-%d %H:%M"))
            for t in reversed(self.timestamps)
        ]

        # Set slider to middle event
        # if self.slider.value() == 50:
        n = len(self.timestamps)
        i = n // 2 - 1
        j = n - i - 1
        self.ts_i = i

        # Update slider parameters but disable it's event change first while setting up plot
        self.skip_on_slider_change_event = True
        self.slider.setMaximum(n - 1)
        self.slider.setValue(i)
        self.skip_on_slider_change_event = False

        # Set timestamp list and datetime edit widget
        self.timestampList.setCurrentRow(j)
        self.t = self.timestamps[i]
        self._set_datetime_edit(self.t)

    def _plot_spectrogram(self):
        ax1 = self.ax1
        ax2 = self.ax2
        ax1.grid(False)

        # Plot title
        channel = self.datasetList.currentItem().text()
        title = (
            "21239 Total WoS - Glendronach Well Monitoring Campaign\nSpectrogram: "
            + channel
        )

        f0 = self.freqs[0]
        f1 = self.freqs[-1]
        t0 = mdates.date2num(self.timestamps[0])
        t1 = mdates.date2num(self.timestamps[-1])

        # Set colour map
        cmap = cm.get_cmap("coolwarm")

        # Continuous contour plot option
        # im = ax1.imshow(
        #     self.z,
        #     aspect="auto",
        #     interpolation="bilinear",
        #     origin="lower",
        #     extent=[f0, f1, t0, t1],
        #     cmap=cmap,
        # )

        # Contour plot with discrete levels
        im = ax1.contourf(self.freqs, self.timestamps, self.z, cmap=cmap)
        # ticks = np.linspace(self.zmin, self.zmax, 8, endpoint=True)
        # im = ax1.contourf(self.freqs, self.timestamps, self.z, levels=ticks, cmap=cmap)

        # Maximise figure space before applying colour bar as colour bar will not reposition if applied after
        self.fig.tight_layout(
            rect=[0, 0.1, 1, 0.92]
        )  # (rect=[left, bottom, right, top])

        # Apply colour bar
        self.cbar = self.fig.colorbar(im, ax=[ax1, ax2])
        # self.cbar = self.fig.colorbar(im, ax=[ax1, ax2], ticks=ticks)

        if self.log_scale is True:
            log10 = r"$\mathregular{log_{10}}$"
        else:
            log10 = ""

        # TODO: Store and read units!
        units = r"$\mathregular{(mm/s^2)^2/Hz}$"
        label = f"{log10}PSD ({units})".lstrip()
        self.cbar.set_label(label)
        # self.cbar.ax.tick_params(length=3.5)
        # self.cbar.outline.set_edgecolor('black')
        # self.cbar.outline.set_linewidth(1)

        # Plot event slice line for middle timestamp
        ti = mdates.date2num(self.t)
        self.event_line, = ax1.plot([f0, f1], [ti, ti], "k--")

        ax1.set_title(title)
        ax1.margins(0)
        ax1.set_xlim(self.xlim)
        ax1.yaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        ax1.yaxis.set_major_locator(mdates.DayLocator(interval=7))
        plt.sca(ax1)
        # plt.xticks(fontsize=11)
        # plt.yticks(fontsize=11)
        # self.fig.tight_layout()

    def _plot_event_psd(self):
        """Plot PSD of spectrogram timestamp slice."""

        # Slice spectrogram dataset at middle timestamp
        i = self.ts_i
        zi = self.z[i, :]

        # Create legend label
        timestamp1 = self.timestamps[i]
        timestamp2 = timestamp1 + timedelta(minutes=20)
        msg_d1 = timestamp1.strftime("%d %b %Y %H:%M").lstrip("0")
        msg_d2 = timestamp2.strftime("%d %b %Y %H:%M")[-5:]
        label = f"{msg_d1} to {msg_d2}"

        self.ax2.cla()
        # self.ax2.patch.set_facecolor('none')
        self.psd_line, = self.ax2.plot(self.freqs, zi, "k")
        self.ax2.set_ylim(self.zmin, self.zmax)
        self.ax2.margins(0, 0)
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
        timestamp1 = self.timestamps[i]
        timestamp2 = timestamp1 + timedelta(minutes=20)
        msg_d1 = timestamp1.strftime("%d %b %Y %H:%M").lstrip("0")
        msg_d2 = timestamp2.strftime("%d %b %Y %H:%M")[-5:]
        label = " ".join((msg_d1, "to", msg_d2))

        # Update plot data and label text
        self.psd_line.set_ydata(zi)
        self.label.set_text(label)


class SpectroPlotSettings(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(SpectroPlotSettings, self).__init__(parent)

        # Assign parent objects
        self.parent = parent

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setWindowTitle("Spectrogram Plot Settings")

        # Widget sizing policy - prevent expansion
        policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )

        # Layout
        # self.setFixedSize(400, 300)
        mainLayout = QtWidgets.QVBoxLayout(self)
        mainLayout.addStretch()

        # Title and axes labels form
        form = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(form)
        self.optProject = QtWidgets.QLineEdit()

        layout.addRow(QtWidgets.QLabel("Project title:"), self.optProject)

        # Frequency axis limits
        frameFreq = QtWidgets.QGroupBox("Frequency Axis")
        grid = QtWidgets.QGridLayout(frameFreq)
        self.optFreqMin = QtWidgets.QLineEdit("0")
        self.optFreqMax = QtWidgets.QLineEdit("3")
        self.optFreqMin.setFixedWidth(50)
        self.optFreqMax.setFixedWidth(50)
        grid.addWidget(QtWidgets.QLabel("Min:"), 0, 0)
        grid.addWidget(self.optFreqMin, 0, 1)
        grid.addWidget(QtWidgets.QLabel("Max:"), 1, 0)
        grid.addWidget(self.optFreqMax, 1, 1)

        # Combine axis limits frames
        axesLimits = QtWidgets.QWidget()
        axesLimits.setSizePolicy(policy)
        vbox = QtWidgets.QHBoxLayout(axesLimits)
        vbox.addWidget(frameFreq)

        # PSD log scale checkbox
        self.logScale = QtWidgets.QCheckBox("PSD log scale")
        self.logScale.setChecked(False)

        # Combine PSD x-axis and log scale
        psdOpts = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(psdOpts)
        vbox.addWidget(self.logScale)

        # Button box
        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok
            | QtWidgets.QDialogButtonBox.Cancel
            | QtWidgets.QDialogButtonBox.Apply
            | QtWidgets.QDialogButtonBox.Reset
        )

        # Final layout
        mainLayout.addWidget(form)
        mainLayout.addWidget(axesLimits)
        mainLayout.addWidget(psdOpts)
        mainLayout.addWidget(self.buttonBox, stretch=0, alignment=QtCore.Qt.AlignRight)

    def _connect_signals(self):
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.accepted.connect(self.set_params)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(
            self.set_params
        )
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Reset).clicked.connect(
            self.reset_values
        )

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
            self.parent.xlim = (
                float(self.optFreqMin.text()),
                float(self.optFreqMax.text()),
            )

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
    win.show()
    sys.exit(app.exec_())
