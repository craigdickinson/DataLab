"""Raw data inspection plots dashboard gui view."""

__author__ = "Craig Dickinson"

import logging
import os
import sys
from glob import glob

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from app.core.azure_cloud_storage import connect_to_azure_account, stream_blob
from app.core.control import Control
from app.core.read_files import (
    read_2hps2_acc,
    read_fugro_csv,
    read_logger_hdf5,
    read_logger_txt,
    read_pulse_acc,
)
from app.core.raw_time_series_dataset import RawDataRead, RawDataPlotSettings
from app.core.signal_processing import calc_psd, filter_signal

# from gui.gui_zoom_pan_factory import ZoomPan
# "2H blue"
color_2H = np.array([0, 49, 80]) / 255


class RawDataDashboard(QtWidgets.QWidget):
    """Create raw time series plots widget."""

    def __init__(self, parent=None):
        super(RawDataDashboard, self).__init__(parent)

        # So can access parent class
        self.parent = parent
        self.control = Control()

        # List of RawDataRead class instances to read and stores time series files of a dataset/logger
        self.raw_datasets = []

        # Flags to skip on change event functions as required
        self.resetting_dashboard = False
        self.skip_on_dataset_changed = False
        self.skip_on_xlims_changed = True

        self.path_to_files = ""

        # Plot settings
        plt.style.use("seaborn")

        self._init_ui()
        self._connect_signals()

        # Plot settings class
        self.plot_setup = RawDataPlotSettings()

        # Instantiate plot settings dialog
        self.plotSettings = LoggerPlotSettings(self, self.plot_setup)

    def _init_ui(self):
        # WIDGETS
        self.openRawButton = QtWidgets.QPushButton("Open Raw Logger File...")
        self.openRawButton.setToolTip("Open raw logger data (*.csv;*.acc) (F2)")
        self.clearDatasetsButton = QtWidgets.QPushButton("Clear Datasets")
        self.clearDatasetsButton.setShortcut("Ctrl+C")
        self.lblAxis = QtWidgets.QLabel("Axis:")
        self.axisCombo = QtWidgets.QComboBox()
        self.axisCombo.setFixedWidth(40)
        self.axisCombo.addItems(["1", "2"])
        self.lblSeries = QtWidgets.QLabel("Series number:")
        self.seriesCombo = QtWidgets.QComboBox()
        self.seriesCombo.setFixedWidth(40)
        self.seriesCombo.addItems(["1", "2", "3", "4"])
        self.lblDataset = QtWidgets.QLabel("Dataset:")
        self.datasetCombo = QtWidgets.QComboBox()
        self.datasetCombo.addItem("None")
        self.lblFiles = QtWidgets.QLabel("Files")
        self.fileList = QtWidgets.QListWidget()
        self.lblSelectedFile = QtWidgets.QLabel("Selected file:")
        self.lblFile = QtWidgets.QLabel("-")
        self.columnsLabel = QtWidgets.QLabel("Columns")
        self.columnList = QtWidgets.QListWidget()
        self.columnList.setFixedHeight(120)
        self.lblSelectedColumn = QtWidgets.QLabel("Selected column:")
        self.lblColumn = QtWidgets.QLabel("-")
        self.plotSettingsButton = QtWidgets.QPushButton("Plot Settings...")

        # Plot figure and canvas to display figure
        self.fig, (self.ax1, self.ax2) = plt.subplots(2)
        self.ax1.set_title("Time Series", size=12)
        self.ax2.set_title("Power Spectral Density", size=12)
        self.fig.tight_layout()
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # CONTAINERS
        # Axis, series and dataset selections
        self.formSelection = QtWidgets.QFormLayout()
        self.formSelection.addRow(self.lblAxis, self.axisCombo)
        self.formSelection.addRow(self.lblSeries, self.seriesCombo)
        self.formSelection.addRow(self.lblDataset, self.datasetCombo)

        self.formFile = QtWidgets.QFormLayout()
        self.formFile.addRow(self.lblSelectedFile, self.lblFile)
        self.formColumn = QtWidgets.QFormLayout()
        self.formColumn.addRow(self.lblSelectedColumn, self.lblColumn)

        # Plot selection group
        self.plotGroup = QtWidgets.QGroupBox("Select Plot Data")
        self.vboxSelect = QtWidgets.QVBoxLayout(self.plotGroup)
        self.vboxSelect.addLayout(self.formSelection)
        self.vboxSelect.addWidget(self.lblFiles)
        self.vboxSelect.addWidget(self.fileList)
        self.vboxSelect.addLayout(self.formFile)
        self.vboxSelect.addWidget(self.columnsLabel)
        self.vboxSelect.addWidget(self.columnList)
        self.vboxSelect.addLayout(self.formColumn)

        # Setup container
        self.setupWidget = QtWidgets.QWidget()
        self.setupWidget.setFixedWidth(250)
        self.vboxSetup = QtWidgets.QVBoxLayout(self.setupWidget)
        self.vboxSetup.addWidget(self.openRawButton)
        self.vboxSetup.addWidget(self.clearDatasetsButton)
        self.vboxSetup.addWidget(self.plotGroup)
        self.vboxSetup.addWidget(self.plotSettingsButton)

        # Plot container
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(navbar)
        self.vbox.addWidget(self.canvas)

        # LAYOUT
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(self.setupWidget)
        self.layout.addLayout(self.vbox)

    def _connect_signals(self):
        self.clearDatasetsButton.clicked.connect(self.on_clear_datasets_clicked)
        self.datasetCombo.currentIndexChanged.connect(self.on_dataset_changed)
        self.plotSettingsButton.clicked.connect(self.on_plot_settings_clicked)
        self.fileList.itemDoubleClicked.connect(self.on_file_double_clicked)
        self.columnList.itemDoubleClicked.connect(self.on_column_double_clicked)

    def on_clear_datasets_clicked(self):
        self.clear_dashboard()

    def on_axis_changed(self):
        self._set_plot_selections()

    def on_series_changed(self):
        self._set_plot_selections()

    def on_dataset_changed(self):
        """Update source files list."""

        if self.resetting_dashboard is True:
            return

        if self.skip_on_dataset_changed is True:
            return

        if self.datasetCombo.currentText() == "None":
            self.fileList.clear()
            self.columnList.clear()
            return

        try:
            i = self.datasetCombo.currentIndex() - 1
            self._update_file_list(i)

            # Plot first file
            if self.fileList.count() > 0:
                filename = self.fileList.currentItem().text()
                self.load_file(filename)
        except Exception as e:
            logging.exception(e)

    def on_file_double_clicked(self):
        """Update current plot series for selected file."""

        # Update stored series selections
        filename = self.fileList.currentItem().text()

        try:
            self.load_file(filename)
        except ValueError as e:
            self.parent.error(f"Error: {e}")
            logging.exception(e)
        except Exception as e:
            msg = "Unexpected error loading logger file"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def on_column_double_clicked(self):
        """Update current plot series for selected channel."""

        try:
            srs = self.get_series()

            # Update stored selections in current series object
            srs = self._store_series_selections(srs)

            # Extract data to be plotted based on selected channels and plot settings
            srs.set_series_data(self.df)

            # Check plot data was set and store initial data limits
            # (note column 1 is Timestamp so looking for > 1 columns)
            if len(srs.y) > 0:
                self.plot_setup.init_xlim = (srs.x[0], srs.x[-1])

            self.calc_filtered_data()

            # This flag stops the on_xlims_change event from processing
            self.skip_on_xlims_changed = True
            # self.plot_series()
            self.update_plots2()
            self.skip_on_xlims_changed = False

        except ValueError as e:
            self.parent.error(f"Error: {e}")
            logging.exception(e)
        except Exception as e:
            msg = "Unexpected error loading logger file"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def on_plot_settings_clicked(self):
        """Show plot options window."""

        self.plotSettings.set_dialog_data()
        self.plotSettings.show()

    def clear_dashboard(self):
        """Clear all stored datasets and reset layout."""

        self.resetting_dashboard = True
        self.raw_datasets = []
        self.plot_setup.reset_series_lists()
        self.datasetCombo.clear()
        self.datasetCombo.addItem("None")
        self.fileList.clear()
        self.columnList.clear()
        self.lblFile.setText("-")
        self.lblColumn.setText("-")
        self.draw_axes()
        self.fig.tight_layout()
        self.canvas.draw()
        self.resetting_dashboard = False

    def add_dataset(self, dataset_name, control, index):
        """Add dataset to combo box and update mapping of control object"""

        # Create new dataset object containing dataset file properties
        logger = control.loggers[index]
        self.raw_datasets.append(RawDataRead(logger))

        # Add to combo box
        self.datasetCombo.addItem(dataset_name)
        self.control = control

    def add_datasets(self, control):
        """Add datasets to combo box and update mapping of control object upon opening a project config JSON file."""

        # For each logger create a new dataset object containing dataset file properties
        for i in range(len(control.logger_ids)):
            logger = control.loggers[i]
            self.raw_datasets.append(RawDataRead(logger))

        # Map control properties and add dataset to combo box
        # (triggers dataset changed event))
        self.control = control
        self.datasetCombo.addItems(control.logger_ids)

        # Select first dataset
        self.skip_on_dataset_changed = True
        self.datasetCombo.setCurrentIndex(1)
        self.skip_on_dataset_changed = False

        try:
            # Set file list for first dataset loaded
            self._update_file_list(dataset_idx=0)

            # Plot first file
            if self.fileList.count() > 0:
                filename = self.fileList.currentItem().text()
                self.load_file(filename)
        except Exception as e:
            logging.exception(e)

    def remove_dataset(self, index):
        """Remove dataset from combo box."""

        if self.datasetCombo.currentText() == "None":
            return

        self.datasetCombo.removeItem(index)
        del self.raw_datasets[index]

    def update_dateset_name(self, index, dataset_name):
        """Update dataset name pertaining to changed logger id in setup module."""

        self.datasetCombo.setItemText(index + 1, dataset_name)

    def map_logger_props_to_dataset(self, logger_idx):
        """
        Map updated logger properties to dataset and check if selected dataset is the same as the logger in
        project config; if so, update files list.
        """

        # Update dataset properties of current logger (in case file read properties have been updated)
        logger = self.control.loggers[logger_idx]
        self.raw_datasets[logger_idx].set_logger(logger)

        # logger_idx + 1 to account for the 'None' dataset
        if self.datasetCombo.currentIndex() == logger_idx + 1:
            self._update_file_list(logger_idx)

    def get_series(self):
        """Return the series object of the selected series in the dashboard."""

        axis_i = self.axisCombo.currentIndex()
        series_i = self.seriesCombo.currentIndex()

        if axis_i == 0:
            srs = self.plot_setup.axis1_series_list[series_i]
        else:
            srs = self.plot_setup.axis2_series_list[series_i]

        return srs

    def _store_series_selections(self, srs):
        """Retrieve current plot selections from the dashboard and store in series object."""

        # Store plot details of selected series
        srs.dataset_i = self.datasetCombo.currentIndex() - 1
        srs.dataset = self.datasetCombo.currentText()
        srs.file_i = self.fileList.currentRow()
        srs.file = self.fileList.currentItem().text()
        srs.column_i = self.columnList.currentRow()
        try:
            srs.column = self.columnList.currentItem().text()
        except AttributeError:
            srs.column = None

        return srs

    def _set_plot_selections(self):
        """Set plot drop-down selections."""

        axis_i = self.axisCombo.currentIndex()
        series_i = self.seriesCombo.currentIndex()

        if axis_i == 0:
            series = self.plot_setup.axis1_series_list[series_i]
        else:
            series = self.plot_setup.axis2_series_list[series_i]

        # Update selections as per properties in associated series list
        self.datasetCombo.setCurrentIndex(series.dataset_i)
        self.fileList.setCurrentRow(series.file_i)
        self.columnList.setCurrentRow(series.column_i)

    def _update_file_list(self, dataset_idx):
        """Update dataset file list widget for current selected dataset."""

        filenames = self.raw_datasets[dataset_idx].filenames
        self.path_to_files = self.raw_datasets[dataset_idx].path_to_files
        self.fileList.clear()
        self.fileList.addItems(filenames)
        self.fileList.setCurrentRow(0)

    def update_file_list_from_open_file_dialog(self, filename):
        """Update file list widget using a file selected using QFileDialog."""

        ext = os.path.splitext(filename)[1]
        files = glob(self.path_to_files + "/*" + ext)
        filenames = [os.path.basename(f) for f in files]
        self.fileList.clear()
        self.fileList.addItems(filenames)
        self.fileList.setCurrentRow(filenames.index(filename))

    def load_file(self, filename, open_file_dialog=False):
        """Load logger file, update widget and plot first channel."""

        # Check if logger exists for selected dataset and retrieve logger id
        try:
            i = self.datasetCombo.currentIndex() - 1
            self.plot_setup.logger_id = self.control.logger_ids[i]
        # Store logger ID (assume the first portion of the filename)
        except Exception:
            self.plot_setup.logger_id = filename.split("_")[0]
            open_file_dialog = True

        # Read time series file to data frame
        if open_file_dialog is True:
            self.df = self._read_logger_file_from_open_file_dialog(filename)
        else:
            self.df = self._read_time_series_file(filename)

        if self.df is None:
            return

        # Get and column names and units from data frame
        channel_names, channel_units = self._get_columns()

        # Get current series object
        srs = self.get_series()

        # Check if series' channel names have changed and update column list widget if so
        if self.columnList.count() == 0 or channel_names != srs.channel_names:
            srs.channel_names = channel_names
            srs.channel_units = channel_units
            self._update_column_list(channel_names)

        # Select channel
        self.columnList.setCurrentRow(srs.column_i)

        # Update stored selections in current series object
        srs = self._store_series_selections(srs)

        # Extract data to be plotted based on selected channels and plot settings
        srs.set_series_data(self.df)

        # Check plot data was set and store initial data limits (note column 1 is Timestamp so looking for > 1 columns)
        if len(srs.y) > 0:
            self.plot_setup.init_xlim = (srs.x[0], srs.x[-1])

        # if len(self.df_plot.columns) > 1:
        #     self.init_xlim = (self.df_plot.index[0], self.df_plot.index[-1])

        self.calc_filtered_data()

        # This flag stops the on_xlims_change event from processing
        self.skip_on_xlims_changed = True
        # self.plot_series()
        self.update_plots2()
        self.skip_on_xlims_changed = False

    def _read_time_series_file(self, filename):
        """Read a raw logger file based on logger file properties provided in setup."""

        i = self.datasetCombo.currentIndex() - 1
        dataset = self.raw_datasets[i]
        logger = self.control.loggers[i]

        try:
            # Get filestream from Azure
            if logger.data_on_azure:
                blob_idx = logger.raw_filenames.index(filename)
                blob = logger.blobs[blob_idx]
                bloc_blob_service = connect_to_azure_account(
                    self.control.azure_account_name, self.control.azure_account_key
                )
                filepath = stream_blob(bloc_blob_service, logger.container_name, blob)
            else:
                filepath = os.path.join(self.path_to_files, filename)

            # Read file from either local file path or Azure file stream
            df = dataset.read_file(filepath)

            return df
        except FileNotFoundError as e:
            msg = f"Attempted to load {filename} to Raw Data Inspection dashboard but file not found."
            self.parent.warn_info(msg)
            logging.exception(e)

            return None
        except Exception as e:
            msg = (
                f"Unable to load {filename} to Raw Data Inspection dashboard. "
                f"Check file layout is suitable and logger settings are correct."
            )
            self.parent.error(msg)
            logging.exception(e)

            return None

    def _read_logger_file_from_open_file_dialog(self, filename):
        """Read a raw logger file."""

        ext = filename.split(".")[-1].lower()
        file = os.path.join(self.path_to_files, filename)

        if ext == "csv":
            df = read_fugro_csv(file)
        elif ext == "acc":
            try:
                # Read expected, new acc file format
                df = read_pulse_acc(file)
            except Exception:
                # Attempt to read older acc file format generated by (obsolete) 2HPS2
                df = read_2hps2_acc(file)
        elif ext == "h5":
            df = read_logger_hdf5(file)
        elif ext == "txt":
            df = read_logger_txt(file)
        else:
            raise FileNotFoundError(f"No files with the extension {ext} found.")

        return df

    def _get_columns(self):
        """Retrieve and store column names and units (if exist) from loaded file."""

        # Store channel names and units - ignore column 1 (timestamps or time index)
        # Also ensure str type (will be int if no header used)
        columns = self.df.columns.get_level_values(0).tolist()[1:]
        channel_names = [str(c) for c in columns]

        # Attempt to retrieve channel units from second column index row
        try:
            channel_units = self.df.columns.get_level_values(1).tolist()[1:]
        except IndexError:
            i = self.datasetCombo.currentIndex() - 1

            # Use units for all channels stored in control object if exists, else create dummy list
            if self.raw_datasets[i].channel_units:
                channel_units = self.raw_datasets[i].channel_units
            else:
                channel_units = ["-"] * len(self.channel_names)

        return channel_names, channel_units

    def _update_column_list(self, channel_names):
        """Update column list with column names of selected file."""

        self.columnList.clear()
        self.columnList.addItems(channel_names)

        if self.columnList.count() == 0:
            raise ValueError("No channels added.")

        # Flag to set axis limits to dataset length
        self.set_init_axis_limits = True
        # self.columnList.setCurrentRow(0)

    def calc_filtered_data(self):
        """
        Search all series objects for data and filter out low frequencies (drift) and high frequencies (noise).
        Filtered signal is stored in the y_filt property of each series object.
        """

        low_cutoff = self.plot_setup.low_cutoff
        high_cutoff = self.plot_setup.high_cutoff

        # Set cut-off values to None if they are not to be applied
        if self.plot_setup.apply_low_cutoff is False:
            low_cutoff = None

        if self.plot_setup.apply_high_cutoff is False:
            high_cutoff = None

        all_srs = self.plot_setup.axis1_series_list + self.plot_setup.axis2_series_list
        for srs in all_srs:
            # Apply bandpass filter (takes a data frame as input)
            # TODO: Should create a filter function that accepts an x and y array as well
            if len(srs.y) > 0:
                df = pd.DataFrame(srs.y, index=srs.x)
                df_filt = filter_signal(df, low_cutoff, high_cutoff)
                srs.y_filt = df_filt.values

    def update_plots2(self):
        """Create time series plots for selected logger channels."""

        self.draw_axes()

        # Event connection to refresh PSD plot upon change of time series x-axis limits
        self.ax1.callbacks.connect("xlim_changed", self.on_xlims_changed)

        # Plot all populated axis 1 series
        for srs in self.plot_setup.axis1_series_list:
            # Plot unfiltered time series
            if len(srs.y) > 0:
                self.plot_series(srs, axis=1, filtered=False)

            # Plot filtered time series
            if len(srs.y_filt) > 0:
                self.plot_series(srs, axis=1, filtered=True)

        # Plot all populated axis 2 series
        for srs in self.plot_setup.axis2_series_list:
            # Plot unfiltered time series
            if len(srs.y) > 0:
                self.plot_series(srs, axis=2, filtered=False)

            # Plot filtered time series
            if len(srs.y_filt) > 0:
                self.plot_series(srs, axis=2, filtered=True)

        # Titles and legend
        self.plot_title()
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
        self.plotSettings.set_dialog_data()

    def plot_series(self, srs, axis, filtered):
        """Add line plot."""

        if axis == 1:
            ax = self.ax1
        else:
            ax = self.ax1b

        if filtered is True:
            y = srs.y_filt
            column = f"{srs.column} (Filtered)"
        else:
            y = srs.y
            column = srs.column

        x = srs.x
        units = srs.units

        # Add line plot
        ax.plot(x, y, label=column)
        ylabel = f"{column} ({units})"
        ax.set_ylabel(ylabel)

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
        self.plot_title(self.df_plot)
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
        self.plotSettings.set_dialog_data()

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

        # Drop timestamp column
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
        self.ax1.margins(0)
        self.ax1b.margins(0)
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
        f, pxx = self._compute_psd(df)

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
        self.ax2.margins(0)
        self.ax2b.margins(0)

    def _compute_psd(self, df):
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

    def plot_title(self, df=None):
        """Write main plot title."""

        # Store start and end timestamp of plot data for title
        try:
            tstart = df.iloc[0, 0].strftime("%d %b %Y %H:%M:%S").lstrip("0")
            tend = df.iloc[-1, 0].strftime("%d %b %Y %H:%M:%S")[-8:]
            subtitle = f"{self.plot_setup.logger_id} Logger - {tstart} to {tend}"
        except:
            subtitle = f"{self.plot_setup.logger_id}"

        title = self.plot_setup.project + "\n" + subtitle
        self.fig.suptitle(
            title,
            # size=16,
            fontname="tahoma",
            color=color_2H,
            weight="bold",
        )

    def on_xlims_changed(self, ax):
        # Convert to datetime
        # self.xmin, self.xmax = mdates.num2date(ax.get_xlim())

        if self.skip_on_xlims_changed is False:
            # Store current time series axis limits
            self.ts_xlim = tuple(round(x, 1) for x in ax.get_xlim())

            # Also store current PSD axis limits so current PSD limits are retained
            self.psd_xlim = tuple(round(x, 1) for x in self.ax2.get_xlim())

            # Update PSD plot and plot title with new timestamp range
            df_slice = self.df_plot[self.ts_xlim[0] : self.ts_xlim[1]]
            self.plot_psd(df_slice)
            self.plot_title(df_slice)
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
    #         # Need to add time zone for compatibility with matplotlib num2date
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
    #     # i = self.fileList.currentRow()
    #     ix = self.focus_ix
    #
    #     if ix == 0:
    #         return df_plot
    #
    #     # self.fileList.setCurrentRow(i - 1)
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
    #     # Need to add timezone for compatibility with matplotlib num2date
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
    #     # self.fileList.setCurrentRow(self.focus_ix)
    #
    #     return df_plot
    #
    # def extend_forward(self):
    #     df_plot = self.df_plot
    #
    #     # Get file from list we want to load
    #     # i = self.fileList.currentRow()
    #     ix = self.focus_ix
    #     print(f'ix={ix}')
    #
    #     if ix == len(self.files_list) - 1:
    #         return df_plot
    #
    #     # self.fileList.setCurrentRow(i + 1)
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
    #     # Need to add timezone for compatibility with matplotlib num2date
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
    #     # self.fileList.setCurrentRow(self.focus_ix)
    #
    #     return df_plot


class LoggerPlotSettings(QtWidgets.QDialog):
    def __init__(self, parent=None, plot_settings=RawDataPlotSettings()):
        super(LoggerPlotSettings, self).__init__(parent)

        self.parent = parent
        self.plot_settings = plot_settings

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
        self.formLayout.addRow(
            QtWidgets.QLabel("Segment overlap (%):"), self.optOverlap
        )
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
            self.optNumEnsembles.setText(str(self.plot_settings.def_num_ensembles))
            self.optNperseg.setText(str(self.plot_settings.def_nperseg))
            self.optWindow.setCurrentText(self.plot_settings.def_window)
            self.optOverlap.setText(str(self.plot_settings.def_overlap))
        elif self.radioWelch.isChecked():
            self.optNumEnsembles.setText(str(self.plot_settings.welch_num_ensembles))
            self.optNperseg.setText(str(self.plot_settings.welch_nperseg))
            self.optWindow.setCurrentText(self.plot_settings.welch_window)
            self.optOverlap.setText(str(self.plot_settings.welch_overlap))
        else:
            self.optNumEnsembles.setText(str(self.plot_settings.cust_num_ensembles))
            self.optNperseg.setText(str(self.plot_settings.cust_nperseg))
            self.optWindow.setCurrentText(self.plot_settings.cust_window)
            self.optOverlap.setText(str(self.plot_settings.cust_overlap))
            self.optNumEnsembles.setEnabled(True)
            self.optWindow.setEnabled(True)
            self.optOverlap.setEnabled(True)

    def on_ok_clicked(self):
        """Update time series widget class parameters with the plot settings and replot."""

        self._update_plot_settings_data()

        # Update plots if files exist
        if self.parent.fileList.count() > 0:
            # This flag stops the on_xlims_change event from processing
            self.parent.skip_on_xlims_changed = True
            self.parent.calc_filtered_data()
            # self.parent.update_plots()
            self.parent.update_plots2()
            self.parent.skip_on_xlims_changed = False

    def set_dialog_data(self):
        """Get plot parameters from the time series widget and assign to settings widget."""

        self.optProject.setText(self.plot_settings.project)
        # self.optTSXmin.setText(f"{self.parent.ax1.get_xlim()[0]:.1f}")
        # self.optTSXmax.setText(f"{self.parent.ax1.get_xlim()[1]:.1f}")
        # self.optPSDXmin.setText(f"{self.parent.ax2.get_xlim()[0]:.1f}")
        # self.optPSDXmax.setText(f"{self.parent.ax2.get_xlim()[1]:.1f}")
        self.optTSXmin.setText(str(self.parent.ax1.get_xlim()[0]))
        self.optTSXmax.setText(str(self.parent.ax1.get_xlim()[1]))
        self.optPSDXmin.setText(str(self.parent.ax2.get_xlim()[0]))
        self.optPSDXmax.setText(str(self.parent.ax2.get_xlim()[1]))

        # Freq cut-offs
        # self.lowCutoff.setText(f"{self.plot_settings.low_cutoff:.2f}")
        # self.highCutoff.setText(f"{self.plot_settings.high_cutoff:.2f}")
        self.lowCutoff.setText(str(self.plot_settings.low_cutoff))
        self.highCutoff.setText(str(self.plot_settings.high_cutoff))

        if self.plot_settings.plot_period is True:
            self.radioPeriod.setChecked(True)
        else:
            self.radioFreq.setChecked(True)

        if self.plot_settings.log_scale is True:
            self.logScale.setChecked(True)
        else:
            self.logScale.setChecked(False)

        # Get PSD parameters
        if self.plot_settings.psd_params_type == "default":
            self.radioDefault.setChecked(True)
            self.optNumEnsembles.setText(str(self.plot_settings.def_num_ensembles))
            self.optWindow.setCurrentText(self.plot_settings.def_window)
            self.optOverlap.setText(str(self.plot_settings.def_overlap))
            self.optNperseg.setText(str(int(self.plot_settings.def_nperseg)))
        elif self.plot_settings.psd_params_type == "welch":
            self.radioWelch.setChecked(True)
            self.optNumEnsembles.setText(str(self.plot_settings.welch_num_ensembles))
            self.optWindow.setCurrentText(self.plot_settings.welch_window)
            self.optOverlap.setText(str(self.plot_settings.welch_overlap))
            self.optNperseg.setText(str(int(self.plot_settings.welch_nperseg)))
        else:
            self.radioCustom.setChecked(True)
            self.optNumEnsembles.setText(str(self.plot_settings.cust_num_ensembles))
            self.optWindow.setCurrentText(self.plot_settings.cust_window)
            self.optOverlap.setText(str(self.plot_settings.cust_overlap))
            self.optNperseg.setText(str(int(self.plot_settings.cust_nperseg)))

        # Get sampling frequency
        self.optFs.setText(str(self.plot_settings.fs))

    def _update_plot_settings_data(self):
        """Update the plot properties of the plot settings object."""

        self.plot_settings.project = self.optProject.text()

        # Check numeric parameters are of valid type
        try:
            # Assign axes limits
            self.plot_settings.ts_xlim = (
                float(self.optTSXmin.text()),
                float(self.optTSXmax.text()),
            )
            self.plot_settings.psd_xlim = (
                float(self.optPSDXmin.text()),
                float(self.optPSDXmax.text()),
            )

            if self.lowFreqChkBox.isChecked():
                self.plot_settings.apply_low_cutoff = True
                self.plot_settings.low_cutoff = float(self.lowCutoff.text())
            else:
                self.plot_settings.apply_low_cutoff = False

            if self.highFreqChkBox.isChecked():
                self.plot_settings.apply_high_cutoff = True
                self.plot_settings.high_cutoff = float(self.highCutoff.text())
            else:
                self.plot_settings.apply_high_cutoff = False

            # Assign PSD parameters
            self.plot_settings.num_ensembles = float(self.optNumEnsembles.text())
            self.plot_settings.window = self.optWindow.currentText()
            self.plot_settings.overlap = float(self.optOverlap.text())

            # Apply decimal formatting to axes limits
            self.optTSXmin.setText(str(round(self.plot_settings.ts_xlim[0], 1)))
            self.optTSXmax.setText(str(round(self.plot_settings.ts_xlim[1], 1)))
            self.optPSDXmin.setText(str(round(self.plot_settings.psd_xlim[0], 1)))
            self.optPSDXmax.setText(str(round(self.plot_settings.psd_xlim[1], 1)))
        except ValueError as e:
            # Notify error in main DataLab class
            self.parent.parent.error(f"Non-numeric input entered: {e}")
            return

        # Store custom PSD parameters
        if self.radioCustom.isChecked():
            self.plot_settings.cust_num_ensembles = self.plot_settings.num_ensembles
            self.plot_settings.cust_window = self.plot_settings.window
            self.plot_settings.cust_overlap = self.plot_settings.overlap

        # Assign remaining settings to time series class
        self.plot_settings.plot_period = self.radioPeriod.isChecked()
        self.plot_settings.log_scale = self.logScale.isChecked()

        if self.radioDefault.isChecked():
            self.plot_settings.psd_params_type = "default"
        elif self.radioWelch.isChecked():
            self.plot_settings.psd_params_type = "welch"
        else:
            self.plot_settings.psd_params_type = "custom"

    def reset_values(self):
        """Reset option settings to initial values set during file load."""

        self.radioFreq.setChecked(True)
        self.logScale.setChecked(False)
        self.optTSXmin.setText(str(round(self.plot_settings.init_xlim[0], 1)))
        self.optTSXmax.setText(str(round(self.plot_settings.init_xlim[1], 1)))
        self.optPSDXmin.setText("0.0")
        self.optPSDXmax.setText("1.0")
        self.radioDefault.setChecked(True)


# For testing layout
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = RawDataDashboard()
    # win = LoggerPlotSettings()
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
