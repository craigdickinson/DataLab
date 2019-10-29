"""Raw data inspection plots dashboard gui view."""

__author__ = "Craig Dickinson"

import logging
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from app.core.azure_cloud_storage import connect_to_azure_account, stream_blob
from app.core.control import Control
from app.core.raw_data_plot_properties import RawDataPlotProperties, RawDataRead
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

        # List of RawDataRead class instances to read and store time series files of a dataset/logger
        self.proj_datasets = []

        # Flags to skip on change event functions as required
        self.resetting_dashboard = False
        self.skip_on_dataset_changed = False
        self.skip_on_xlims_changed = True

        self.path_to_files = ""
        self.df = pd.DataFrame()

        self.current_axis_i = 0
        self.current_series_i = 0

        self._init_ui()
        self._connect_signals()

        # Plot settings class
        self.plot_setup = RawDataPlotProperties()

        # Instantiate plot settings dialog
        self.plotControls = PlotControlsDialog(self, self.plot_setup)

    def _init_ui(self):
        # WIDGETS
        self.axisCombo = QtWidgets.QComboBox()
        self.axisCombo.setFixedWidth(40)
        self.axisCombo.addItems(["1", "2"])
        self.seriesCombo = QtWidgets.QComboBox()
        self.seriesCombo.setFixedWidth(40)
        self.seriesCombo.addItems(["1", "2", "3", "4"])
        self.datasetCombo = QtWidgets.QComboBox()
        self.datasetCombo.addItem("None")
        self.fileList = QtWidgets.QListWidget()
        self.columnsLabel = QtWidgets.QLabel("Columns")
        self.columnList = QtWidgets.QListWidget()
        self.columnList.setFixedHeight(110)
        self.lowCutoff = QtWidgets.QLineEdit("None")
        self.lowCutoff.setFixedWidth(40)
        self.highCutoff = QtWidgets.QLineEdit("None")
        self.highCutoff.setFixedWidth(40)
        self.plotFiltOnlyChkBox = QtWidgets.QCheckBox("Plot filtered only")
        self.exportButton = QtWidgets.QPushButton("Export Plot Data")
        self.exportButton.setShortcut("Ctrl+E")
        self.plotSettingsButton = QtWidgets.QPushButton("Plot Settings...")

        # Labels
        self.lblAxis = QtWidgets.QLabel("Axis:")
        self.lblDataset = QtWidgets.QLabel("Dataset:")
        self.lblSeries = QtWidgets.QLabel("Series number:")
        self.lblSelectedFile = QtWidgets.QLabel("Selected file:")
        self.lblFile = QtWidgets.QLabel("-")
        self.lblSelectedColumn = QtWidgets.QLabel("Selected column:")
        self.lblColumn = QtWidgets.QLabel("-")
        self.lblFiles = QtWidgets.QLabel("Files")
        self.lblLowCutoff = QtWidgets.QLabel("Low frequency cut-off (Hz):")
        self.lblHighCutoff = QtWidgets.QLabel("High frequency cut-off (Hz):")

        # Frequency/period radio buttons
        self.freqRadio = QtWidgets.QRadioButton("Frequency")
        self.freqRadio.setChecked(True)
        self.periodRadio = QtWidgets.QRadioButton("Period")

        # PSD log scale checkbox
        self.logScale = QtWidgets.QCheckBox("Log scale")
        self.logScale.setChecked(False)

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
        self.selectGroup = QtWidgets.QGroupBox("Select Plot Data")
        self.vboxSelect = QtWidgets.QVBoxLayout(self.selectGroup)
        self.vboxSelect.addLayout(self.formSelection)
        self.vboxSelect.addLayout(self.formFile)
        self.vboxSelect.addLayout(self.formColumn)
        self.vboxSelect.addWidget(self.lblFiles)
        self.vboxSelect.addWidget(self.fileList)
        self.vboxSelect.addWidget(self.columnsLabel)
        self.vboxSelect.addWidget(self.columnList)

        # Filter cut-off frequencies group
        self.filterGroup = QtWidgets.QGroupBox("Selected Series Filters")
        self.filterForm = QtWidgets.QFormLayout(self.filterGroup)
        self.filterForm.addRow(self.lblLowCutoff, self.lowCutoff)
        self.filterForm.addRow(self.lblHighCutoff, self.highCutoff)
        # self.filterForm.addRow(self.plotFiltOnlyChkBox, self.logScale)

        # Frequency/period group
        # self.psdXAxisGroup = QtWidgets.QGroupBox("PSD Settings")
        # self.grid = QtWidgets.QGridLayout(self.psdXAxisGroup)
        # self.grid.addWidget(self.radioFreq, 0, 0)
        # self.grid.addWidget(self.radioPeriod, 1, 0)
        # self.grid.addWidget(self.plotFiltOnlyChkBox, 0, 1)
        # self.grid.addWidget(self.logScale, 1, 1)

        # PSD x-axis frequency or period group
        self.psdXAxisGroup = QtWidgets.QGroupBox("PSD X-Axis")
        self.vbox1 = QtWidgets.QVBoxLayout(self.psdXAxisGroup)
        self.vbox1.addWidget(self.freqRadio)
        self.vbox1.addWidget(self.periodRadio)

        # PSD plot settings group
        self.psdGroup = QtWidgets.QGroupBox("PSD Plot Settings")
        self.vbox2 = QtWidgets.QVBoxLayout(self.psdGroup)
        self.vbox2.addWidget(self.plotFiltOnlyChkBox)
        self.vbox2.addWidget(self.logScale)

        # PSD options container
        self.hboxPSD = QtWidgets.QHBoxLayout()
        self.hboxPSD.addWidget(self.psdXAxisGroup)
        self.hboxPSD.addWidget(self.psdGroup)

        # Buttons containers
        self.hboxButtons = QtWidgets.QHBoxLayout()
        self.hboxButtons.addWidget(self.exportButton)
        self.hboxButtons.addWidget(self.plotSettingsButton)

        # Setup container
        self.setupWidget = QtWidgets.QWidget()
        self.setupWidget.setFixedWidth(250)
        self.vboxSetup = QtWidgets.QVBoxLayout(self.setupWidget)
        self.vboxSetup.addWidget(self.selectGroup)
        self.vboxSetup.addWidget(self.filterGroup)
        # self.vboxSetup.addWidget(self.psdXAxisGroup)
        self.vboxSetup.addLayout(self.hboxPSD)
        self.vboxSetup.addLayout(self.hboxButtons)

        # Plot container
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(navbar)
        self.vbox.addWidget(self.canvas)

        # LAYOUT
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(self.setupWidget)
        self.layout.addLayout(self.vbox)

    def _connect_signals(self):
        self.axisCombo.currentIndexChanged.connect(self.on_axis_changed)
        self.seriesCombo.currentIndexChanged.connect(self.on_series_changed)
        self.datasetCombo.currentIndexChanged.connect(self.on_dataset_changed)
        self.fileList.itemDoubleClicked.connect(self.on_file_double_clicked)
        self.columnList.itemDoubleClicked.connect(self.on_column_double_clicked)
        self.lowCutoff.returnPressed.connect(self.on_low_cutoff_changed)
        self.highCutoff.returnPressed.connect(self.on_high_cutoff_changed)
        self.freqRadio.toggled.connect(self.on_psd_xaxis_type_toggled)
        self.plotFiltOnlyChkBox.toggled.connect(self.on_plot_filt_only_toggled)
        self.logScale.toggled.connect(self.on_log_scale_toggled)
        self.exportButton.clicked.connect(self.on_export_plot_data_clicked)
        self.plotSettingsButton.clicked.connect(self.on_plot_settings_clicked)

    def on_axis_changed(self):
        self._set_widget_series_selections()

    def on_series_changed(self):
        self._set_widget_series_selections()

    def on_dataset_changed(self):
        """Update source files list."""

        if self.resetting_dashboard is True:
            return

        if self.skip_on_dataset_changed is True:
            return

        srs = self._get_series()

        if self.datasetCombo.currentText() == "None":
            srs.reset_series()

            # Set axis and series number
            srs.axis = self.current_axis_i + 1
            srs.series = self.current_series_i + 1

            self.fileList.clear()
            self.columnList.clear()

            # This flag stops the on_xlims_changed event from processing
            self.skip_on_xlims_changed = True
            self.rebuild_plots()
            self.skip_on_xlims_changed = False

            # Report selected file and column
            self.lblFile.setText(srs.file)
            self.lblColumn.setText(srs.column)
        else:
            # If previous dataset was "None" set the filters to the current default values (a convenience)
            if srs.dataset == "None":
                srs.low_cutoff = self.plot_setup.def_low_cutoff
                srs.high_cutoff = self.plot_setup.def_high_cutoff

            try:
                i = self.datasetCombo.currentIndex() - 1
                srs.path_to_files = self.proj_datasets[i].path_to_files

                filenames = self.proj_datasets[i].filenames
                srs.filenames = filenames
                self._set_file_list(filenames)

                if self.fileList.count() > 0:
                    try:
                        self.fileList.setCurrentRow(srs.file_i)
                    except Exception:
                        self.fileList.setCurrentRow(0)

                    filename = self.fileList.currentItem().text()

                    self._process_file(filename)
            except Exception as e:
                logging.exception(e)

        # Set series filters
        self.lowCutoff.setText(str(srs.low_cutoff))
        self.highCutoff.setText(str(srs.high_cutoff))

    def on_file_double_clicked(self):
        """Update current plot series for selected file."""

        # Update stored series selections
        filename = self.fileList.currentItem().text()

        try:
            self._process_file(filename)
        except ValueError as e:
            self.parent.error(f"Error: {e}")
            logging.exception(e)
        except Exception as e:
            msg = "Unexpected error updating plot"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def on_column_double_clicked(self):
        """Update current plot series for selected channel."""

        try:
            srs = self._get_series()
            # Store gui plot selections to current series object
            srs = self._store_series_selections(srs)
            self._update_plots(srs)
        except ValueError as e:
            self.parent.error(f"Error: {e}")
            logging.exception(e)
        except Exception as e:
            msg = "Unexpected error updating plot"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def on_low_cutoff_changed(self):
        val = self.lowCutoff.text()
        srs = self._get_series()

        if val == "" or val.lower() == "none":
            srs.low_cutoff = None
        else:
            try:
                srs.low_cutoff = float(val)
            except ValueError:
                pass

        # Confirm or reject value and update plot setting default value
        self.lowCutoff.setText(str(srs.low_cutoff))
        self.plot_setup.def_low_cutoff = srs.low_cutoff

        # Recalculate filtered signal for selected time series
        self._filter_time_series(srs)

        # This flag stops the on_xlims_changed event from processing
        self.skip_on_xlims_changed = True
        self.rebuild_plots()
        self.skip_on_xlims_changed = False

    def on_high_cutoff_changed(self):
        val = self.highCutoff.text()
        srs = self._get_series()

        if val == "" or val.lower() == "none":
            srs.high_cutoff = None
        else:
            try:
                srs.high_cutoff = float(val)
            except ValueError:
                pass

        # Confirm or reject value and update plot setting default value
        self.highCutoff.setText(str(srs.high_cutoff))
        self.plot_setup.def_high_cutoff = srs.high_cutoff

        # Recalculate filtered signal for selected time series
        self._filter_time_series(srs)

        # This flag stops the on_xlims_changed event from processing
        self.skip_on_xlims_changed = True
        self.rebuild_plots()
        self.skip_on_xlims_changed = False

    def on_plot_filt_only_toggled(self):
        self.plot_setup.plot_filt_only = self.plotFiltOnlyChkBox.isChecked()

        # This flag stops the on_xlims_changed event from processing
        self.skip_on_xlims_changed = True
        self.rebuild_plots()
        self.skip_on_xlims_changed = False

    def on_psd_xaxis_type_toggled(self):
        """Switch PSD x-axis between frequency and period."""

        # Get current x-axis limits
        xmin, xmax = self.ax2.get_xlim()

        # Default min axis to 0
        xmin = 0

        # Set frequency x-axis limits (Hz)
        if self.freqRadio.isChecked():
            # Default xmax to 1 Hz if current xmin is 0 s
            if xmin == 0:
                xmax = 1
            else:
                xmax = 1 / xmin
        # Set period x-axis limits (s)
        else:
            # Default xmax to 20 s if current xmin is 0 Hz
            if xmin == 0:
                xmax = 20
            else:
                xmax = 1 / xmin

        # Update plot setup properties
        self.plot_setup.plot_period = self.periodRadio.isChecked()
        self.plot_setup.psd_xlim = (xmin, xmax)

        # Redraw PSD plot
        self._remove_all_psd_series()
        self._plot_psd()
        self.canvas.draw()

    def on_log_scale_toggled(self):
        self.plot_setup.log_scale = self.logScale.isChecked()

        # This flag stops the on_xlims_changed event from processing
        self.skip_on_xlims_changed = True
        self.rebuild_plots()
        self.skip_on_xlims_changed = False

        # Redraw PSD plot
        # self._remove_all_psd_series()
        # self._plot_psd()
        # self.canvas.draw()

    def on_export_plot_data_clicked(self):
        self.export_plot_data_to_excel()

    def on_plot_settings_clicked(self):
        """Show plot options window."""

        self.plotControls.set_dialog_data()
        self.plotControls.show()

    def on_xlims_changed(self, ax):
        """Recalculate PSDs for new time series x-axis limits and replot."""

        if self.skip_on_xlims_changed is True:
            return

        # Store current time series x-axis limits
        self.plot_setup.ts_xlim = tuple(round(x, 1) for x in ax.get_xlim())

        # Store current PSD x-axis limits so current PSD limits are retained are creating new PSD plot
        self.plot_setup.psd_xlim = tuple(round(x, 1) for x in self.ax2.get_xlim())

        # Remove existing PSD line plots
        self._remove_all_psd_series()

        # Update PSD plot and plot title with new timestamp range
        self._plot_psd()
        self._set_title()

    def clear_dashboard(self):
        """Clear all stored datasets and reset layout."""

        self.resetting_dashboard = True
        self.axisCombo.setCurrentIndex(0)
        self.seriesCombo.setCurrentIndex(0)
        self.proj_datasets = []
        self.plot_setup.reset()
        self.datasetCombo.clear()
        self.datasetCombo.addItem("None")
        self.lblFile.setText("-")
        self.lblColumn.setText("-")
        self.fileList.clear()
        self.columnList.clear()
        self.lowCutoff.setText("None")
        self.highCutoff.setText("None")
        self._draw_axes()
        self.canvas.draw()
        self.resetting_dashboard = False

    def add_dataset(self, dataset_name, control, index):
        """Add dataset to combo box and update mapping of control object"""

        # Update control object mapping
        self.control = control

        # Store control project name to project setup
        self._map_control_project_name()

        # Create new dataset object containing dataset file properties
        logger = control.loggers[index]
        self.proj_datasets.append(RawDataRead(logger))

        # Add to dataset drop down
        self.datasetCombo.addItem(dataset_name)

    def add_datasets(self, control):
        """Add datasets to combo box and update mapping of control object upon opening a project config JSON file."""

        # Map control object
        self.control = control

        # First reset the raw data dashboard and clear any previous datasets
        self.clear_dashboard()

        # Store control project name to project setup
        self._map_control_project_name()

        # For each logger create a new dataset object containing dataset file properties
        for i in range(len(control.logger_ids)):
            logger = control.loggers[i]
            self.proj_datasets.append(RawDataRead(logger))

        # Add dataset to combo box (triggers dataset changed event)
        self.datasetCombo.addItems(control.logger_ids)

        # Select first dataset
        self.skip_on_dataset_changed = True
        self.datasetCombo.setCurrentIndex(1)
        self.skip_on_dataset_changed = False

        try:
            srs = self._get_series()

            # Set file list for first dataset loaded
            srs.path_to_files = self.proj_datasets[0].path_to_files
            filenames = self.proj_datasets[0].filenames
            srs.filenames = filenames
            self._set_file_list(filenames)

            # Assign first file as selected
            self.fileList.setCurrentRow(0)

            # Plot first file
            if self.fileList.count() > 0:
                filename = self.fileList.currentItem().text()
                self._process_file(filename)
        except Exception as e:
            self.parent.error(str(e))
            logging.exception(e)

    def remove_dataset(self, index):
        """Remove selected dataset data and item from dataset combo box."""

        # Remove dataset/logger from list
        del self.proj_datasets[index]

        # index + 1 because first combo item is "None"
        self.datasetCombo.removeItem(index + 1)

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
        self.proj_datasets[logger_idx].set_logger(logger)

        # logger_idx + 1 to account for the 'None' dataset
        if self.datasetCombo.currentIndex() == logger_idx + 1:
            srs = self._get_series()
            srs.path_to_files = self.proj_datasets[logger_idx].path_to_files

            filenames = self.proj_datasets[logger_idx].filenames
            srs.filenames = filenames
            self._set_file_list(filenames)

            columns = self.proj_datasets[logger_idx].channel_names
            srs.channel_names = columns
            self._set_column_list(columns)

    def _map_control_project_name(self):
        self.plot_setup.project_name = self.control.project_name

    def _set_file_list(self, filenames):
        """Update dataset file list widget for current selected dataset."""

        # Populate file list widget
        self.fileList.clear()
        self.fileList.addItems(filenames)

    def _set_column_list(self, channel_names):
        """Update column list with column names of selected file."""

        self.columnList.clear()
        self.columnList.addItems(channel_names)

    def _set_widget_series_selections(self):
        """Update plot drop-downs of selected series as per properties in associated series object."""

        srs = self._get_series()
        self.skip_on_dataset_changed = True
        self.datasetCombo.setCurrentIndex(srs.dataset_i)
        self.skip_on_dataset_changed = False
        self.lblFile.setText(srs.file)
        self.lblColumn.setText(srs.column)
        self._set_file_list(srs.filenames)
        self._set_column_list(srs.channel_names)
        self.fileList.setCurrentRow(srs.file_i)
        self.columnList.setCurrentRow(srs.column_i)

        # Set series filters - use default filters if a blank dataset
        if srs.dataset == "None":
            self.lowCutoff.setText(str(self.plot_setup.def_low_cutoff))
            self.highCutoff.setText(str(self.plot_setup.def_high_cutoff))
        else:
            self.lowCutoff.setText(str(srs.low_cutoff))
            self.highCutoff.setText(str(srs.high_cutoff))

    def _process_file(self, filename):
        self.df = self._read_time_series_file(filename)

        if self.df.empty:
            return

        # Get current series object
        srs = self._get_series()

        self._process_time_series(srs)

        # Store gui plot selections to current series object
        srs = self._store_series_selections(srs)

        self._update_plots(srs)

    def _read_time_series_file(self, filename):
        """Read a raw logger file based on logger file properties provided in setup."""

        i = self.datasetCombo.currentIndex() - 1
        dataset = self.proj_datasets[i]
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
                srs = self._get_series()
                filepath = os.path.join(srs.path_to_files, filename)

            # Read file from either local file path or Azure file stream
            df = dataset.read_file(filepath)

            return df
        except FileNotFoundError as e:
            msg = f"Attempted to load {filename} to Raw Data Inspection dashboard but file not found."
            self.parent.warn_info(msg)
            logging.exception(e)

            return pd.DataFrame()
        except Exception as e:
            msg = (
                f"Unable to load {filename} to Raw Data Inspection dashboard. "
                f"Check file layout is suitable and logger settings are correct."
            )
            self.parent.error(f"{msg}\n\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

            return pd.DataFrame()

    def _get_series(self):
        """Return the series object of the selected series in the dashboard."""

        axis_i = self.axisCombo.currentIndex()
        series_i = self.seriesCombo.currentIndex()

        # Store current axis and series index
        self.current_axis_i = axis_i
        self.current_series_i = series_i

        if axis_i == 0:
            srs = self.plot_setup.axis1_series_list[series_i]
        else:
            srs = self.plot_setup.axis2_series_list[series_i]

        return srs

    def _process_time_series(self, srs):
        """Process time series data frame and plot."""

        # Get and column names and units from data frame
        channel_names, channel_units = self._get_columns()

        # Set flag to set x-axis limits to duration of time series if a new file is loaded/selected
        if self.columnList.count() == 0:
            self.plot_setup.set_init_axis_limits = True

        # Check if series' channel names have changed and update column list widget if so
        # if self.columnList.count() == 0 or channel_names != srs.channel_names:
        srs.channel_names = channel_names
        srs.channel_units = channel_units
        self._set_column_list(channel_names)

        # Select channel
        try:
            self.columnList.setCurrentRow(srs.column_i)
        except Exception:
            self.columnList.setCurrentRow(0)

    def _get_columns(self):
        """Retrieve and store column names and units (if exist) from loaded file."""

        # Store channel names and units - ignore column 1 (timestamps or time index)
        # Also ensure str type (will be int if no header used)
        channel_names = self.df.columns.get_level_values(0).tolist()[1:]

        # Attempt to retrieve channel units from second column index row
        try:
            channel_units = self.df.columns.get_level_values(1).tolist()[1:]
        except IndexError:
            i = self.datasetCombo.currentIndex() - 1

            # Use units for all channels stored in control object if exists, else create dummy list
            if self.proj_datasets[i].channel_units:
                channel_units = self.proj_datasets[i].channel_units
            else:
                channel_units = ["-"] * len(channel_names)

        return channel_names, channel_units

    def _store_series_selections(self, srs):
        """Retrieve current plot selections from the dashboard and store in series object."""

        # Store plot details of selected series
        srs.dataset_i = self.datasetCombo.currentIndex()
        srs.dataset = self.datasetCombo.currentText()

        # Retrieve and store filenames for dataset
        if srs.dataset == "None":
            srs.filename = []
        else:
            filenames = self.proj_datasets[srs.dataset_i - 1].filenames
            srs.filenames = filenames

        srs.file_i = self.fileList.currentRow()
        srs.column_i = self.columnList.currentRow()

        if srs.file_i == -1:
            srs.file = "-"
        else:
            srs.file = self.fileList.currentItem().text()

        if srs.column_i == -1:
            srs.column = "-"
        else:
            srs.column = self.columnList.currentItem().text()

        return srs

    def _update_plots(self, srs):
        """Update plot series data for current selections and plot."""

        # Select series plot data from file data frame
        srs = self._set_series_data(srs, self.df)

        # Check plot data was set and store initial data limits (note column 1 is Timestamp so looking for > 1 columns)
        if len(srs.y) > 0:
            self.plot_setup.init_xlim = (srs.x[0], srs.x[-1])

        self.filter_all_time_series()

        # This flag stops the on_xlims_changed event from processing
        self.skip_on_xlims_changed = True
        self.rebuild_plots()
        self.skip_on_xlims_changed = False

        # Report selected file and column
        self.lblFile.setText(srs.file)
        self.lblColumn.setText(srs.column)

    def _set_series_data(self, srs, df):
        """Set series plot data."""

        srs.x = df.index.values

        # Store first and last time steps
        srs.tmin = srs.x[0]
        srs.tmax = srs.x[-1]

        try:
            srs.y = df[srs.column].values.ravel()
        except KeyError:
            srs.y = []

        srs.units = srs.channel_units[srs.column_i]
        srs.timestamps = df.iloc[:, 0].values
        # srs.set_series_data(self.df, channels, units)

        return srs

    def filter_all_time_series(self):
        """
        Search all series objects for data and filter out low frequencies (drift) and high frequencies (noise).
        Filtered signal is stored in the y_filt property of each series object.
        """

        all_srs = self.plot_setup.axis1_series_list + self.plot_setup.axis2_series_list
        for srs in all_srs:
            self._filter_time_series(srs)

    @staticmethod
    def _filter_time_series(srs):
        """Calculate filtered signal of a single series."""

        # Apply bandpass filter (takes a data frame as input)
        # TODO: Should create a filter function that accepts an x and y array as well
        if len(srs.y) > 0:
            df = pd.DataFrame(srs.y, index=srs.x)
            df_filt = filter_signal(df, srs.low_cutoff, srs.high_cutoff)
            srs.y_filt = df_filt.values.ravel()

    def rebuild_plots(self):
        """Create time series plots for selected logger channels."""

        self._draw_axes()

        # Event connection to refresh PSD plot upon change of time series x-axis limits
        self.ax1.callbacks.connect("xlim_changed", self.on_xlims_changed)

        # Plot all time series
        axis1_is_plotted, axis2_is_plotted = self._plot_time_series()

        # Check something plotted
        if axis1_is_plotted is False and axis2_is_plotted is False:
            self.canvas.draw()
            return

        # Store plot flags
        self.plot_setup.axis1_is_plotted = axis1_is_plotted
        self.plot_setup.axis2_is_plotted = axis2_is_plotted

        # Set x-axis limits of time series subplot to be the file duration id a new file was loaded/selected
        if self.plot_setup.set_init_axis_limits is True:
            self.plot_setup.ts_xlim = self.plot_setup.init_xlim
            self.plot_setup.set_init_axis_limits = False

        # Set time series x-axis limits
        self.ax1.set_xlim(self.plot_setup.ts_xlim)

        # Plot all PSD series
        self._plot_psd()

        # Configure gridlines and axes visibility
        self._set_gridlines()

        # Title and legend
        self._set_title()
        self._set_legend()

        # Ensure plots don't overlap suptitle and legend
        # self.fig.tight_layout(rect=[0, 0.05, 1, 0.9])
        # self.fig.tight_layout(rect=[0, 0.05, 1, 0.95])
        # self.fig.tight_layout()
        # (rect=[left, bottom, right, top])
        self.fig.subplots_adjust(
            left=0.07, bottom=0.15, right=0.93, top=0.9, hspace=0.4
        )
        # (left, bottom, right, top, wspace, hspace)
        self.canvas.draw()

        # Update parameters in plot settings window (could be open)
        self.plotControls.set_dialog_data()

    def _draw_axes(self):
        """Set up basic plot layout."""

        self.fig.clf()

        # Set up time series and PSD axes
        self.ax1 = self.fig.add_subplot(2, 1, 1)
        self.ax2 = self.fig.add_subplot(2, 1, 2)
        self.ax1b = self.ax1.twinx()
        self.ax2b = self.ax2.twinx()
        self.ax1b.yaxis.set_visible(False)
        self.ax2b.yaxis.set_visible(False)
        self.ax2.margins(0)
        self.ax2b.margins(0)

        # Labels
        self.ax1.set_title("Time Series")
        self.ax2.set_title("Power Spectral Density")
        self.ax1.set_xlabel("Time (s)")
        self.ax2.set_xlabel("Frequency (Hz)")

        # TODO: Mouse scroll zoom - works
        # f = self.zoom_factory(self.ax, base_scale=1.1)
        # f = self.zoom_factory(self.ax2, base_scale=1.1)

        # zp = ZoomPan()
        # figZoom = zp.zoom_factory(self.ax, base_scale=1.1)
        # figPan = zp.pan_factory(self.ax)
        # figZoom = zp.zoom_factory(self.ax2, base_scale=1.1)
        # figPan = zp.pan_factory(self.ax2)

    def _remove_all_psd_series(self):
        """Clear the PSD subplot """

        all_srs = self.plot_setup.axis1_series_list + self.plot_setup.axis2_series_list
        for srs in all_srs:
            if srs.psd_line is not None:
                srs.psd_line.remove()
                srs.psd_line = None
            if srs.psd_line_filt is not None:
                srs.psd_line_filt.remove()
                srs.psd_line_filt = None

    def _plot_time_series(self):
        """Plot all time series."""

        axis1_is_plotted = False
        axis2_is_plotted = False
        plot_filt_only = self.plot_setup.plot_filt_only

        # Plot all populated axis 1 series
        for srs in self.plot_setup.axis1_series_list:
            # Plot unfiltered time series
            if len(srs.y) > 0 and plot_filt_only is False:
                srs.ts_line = self._add_ts_line_plot(srs, ax=self.ax1, filtered=False)
                axis1_is_plotted = True

            # Plot filtered time series
            if len(srs.y_filt) > 0:
                srs.ts_line_filt = self._add_ts_line_plot(
                    srs, ax=self.ax1, filtered=True
                )
                axis1_is_plotted = True

        # Plot all populated axis 2 series
        for srs in self.plot_setup.axis2_series_list:
            # Plot unfiltered time series
            if len(srs.y) > 0 and plot_filt_only is False:
                srs.ts_line = self._add_ts_line_plot(srs, ax=self.ax1b, filtered=False)
                axis2_is_plotted = True

            # # Plot filtered time series
            if len(srs.y_filt) > 0:
                srs.ts_line_filt = self._add_ts_line_plot(
                    srs, ax=self.ax1b, filtered=True
                )
                axis2_is_plotted = True

        return axis1_is_plotted, axis2_is_plotted

    def _plot_psd(self):
        """Compute and plot all PSD series."""

        plot_filt_only = self.plot_setup.plot_filt_only

        # Plot all populated axis 1 series
        for srs in self.plot_setup.axis1_series_list:
            # Plot unfiltered time series
            if len(srs.y) > 0 and plot_filt_only is False:
                srs.psd_line = self._add_psd_line_plot(srs, ax=self.ax2, filtered=False)

            # Plot filtered time series
            if len(srs.y_filt) > 0:
                srs.psd_line_filt = self._add_psd_line_plot(
                    srs, ax=self.ax2, filtered=True
                )

        # Plot all populated axis 2 series
        for srs in self.plot_setup.axis2_series_list:
            # Plot unfiltered time series
            if len(srs.y) > 0 and plot_filt_only is False:
                srs.psd_line = self._add_psd_line_plot(
                    srs, ax=self.ax2b, filtered=False
                )

            # Plot filtered time series
            if len(srs.y_filt) > 0:
                srs.psd_line_filt = self._add_psd_line_plot(
                    srs, ax=self.ax2b, filtered=True
                )

        # Set x and y axis limits from stored values
        self.ax2.set_xlim(self.plot_setup.psd_xlim)

        # X-axis label
        if self.plot_setup.plot_period:
            self.ax2.set_xlabel("Period (s)")
        else:
            self.ax2.set_xlabel("Frequency (Hz)")

    def _add_ts_line_plot(self, srs, ax, filtered):
        """Add time series line plot."""

        x = srs.x
        linewidth = srs.linewidth
        srs.label = self._construct_label(srs, filtered)

        if filtered is True:
            y = srs.y_filt
            color = srs.color_filt
        else:
            y = srs.y
            color = srs.color

        # Add line plot
        line, = ax.plot(x, y, label=srs.label, c=color, lw=linewidth)

        if srs.units == "-":
            ylabel = ""
        else:
            ylabel = srs.units
        ax.set_ylabel(ylabel, size=10)

        # Return line handle
        return line

    def _add_psd_line_plot(self, srs, ax, filtered):
        """Compute PSD of a single series and plot."""

        if filtered is True:
            y = srs.y_filt
            color = srs.color_filt
        else:
            y = srs.y
            color = srs.color

        # Retrieve time series x-limits to calculate PSD on
        xmin, xmax = self.plot_setup.ts_xlim
        x = srs.x

        # This method works if x is integers not floats
        xs = np.where((x >= xmin) & (x <= xmax))
        x = x[xs]
        y = y[xs]

        # Create and slice data frame
        df = pd.DataFrame(y, index=x)
        df.index = df.index.astype(float)
        # df = df[xmin:xmax]

        # Calculate PSD of series
        f, pxx = self._compute_psd(df)

        # Set x-axis as frequency or period based on plot options
        if self.plot_setup.plot_period:
            # Handle for divide by zero
            f = 1 / f[1:]
            pxx = pxx[1:]

        # Set units text
        if srs.units == "-":
            units = "units"
        else:
            units = srs.units

        # Convert PSD to log10 if plot option selected
        if self.plot_setup.log_scale is True:
            # pxx = np.log10(pxx)
            ax.set_yscale("log")
            ylabel = f"$\mathregular{{log_{{10}} [({units})^2/Hz}}]$".strip()
        else:
            ylabel = f"$\mathregular{{({units})^2/Hz}}$".strip()

        linewidth = srs.linewidth

        # Plot PSD
        line, = ax.plot(f, pxx, c=color, lw=linewidth)
        ax.set_ylabel(ylabel, size=10)

        # Store frequencies and amplitudes
        srs.freq = f
        if filtered is True:
            srs.pxx = pxx
        else:
            srs.pxx_filt = pxx

        # Return line handle
        return line

    def _compute_psd(self, df):
        """Compute PSD of all channels using the Welch method."""

        # TODO: Unit test this!
        # Sampling frequency
        fs = 1 / (df.index[1] - df.index[0])
        window = self.plot_setup.window.lower()
        if window == "none":
            window = "boxcar"
        nperseg = int(len(df) / self.plot_setup.num_ensembles)
        noverlap = nperseg * self.plot_setup.overlap // 100

        try:
            # Note the default Welch parameters are equivalent to running
            # f, pxx = signal.welch(df.T, fs=fs)
            # Calculate PSD using Welch method
            f, pxx = calc_psd(
                data=df.values.ravel(),
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
        self.plot_setup.def_nperseg = int(len(df))
        self.plot_setup.cust_nperseg = nperseg
        self.plot_setup.fs = int(fs)

        return f, pxx

    def _construct_label(self, srs, filtered):
        """Create legend label."""

        # Construct legend label
        label = ""

        if self.plot_setup.filename_in_legend is True:
            label += f"{srs.file} "

        if self.plot_setup.dataset_in_legend is True:
            label += f"{srs.dataset} "

        if self.plot_setup.column_in_legend is True:
            label += f"{srs.column}"

        if filtered is True:
            label += " (Filtered)"

        return label.strip()

    def _set_gridlines(self):
        """Set displayed gridlines and axis visibility."""

        # If primary axis not used, switch gridlines to axis 2
        axis1_is_plotted = self.plot_setup.axis1_is_plotted
        axis2_is_plotted = self.plot_setup.axis2_is_plotted

        # Set gridlines on axis 1 only
        if not axis1_is_plotted and axis2_is_plotted:
            self.ax1.grid(False)
            self.ax2.grid(False)
            self.ax1b.grid(True)
            self.ax2b.grid(True)
        # Set gridlines on axis 2 only
        else:
            self.ax1.grid(True)
            self.ax2.grid(True)
            self.ax1b.grid(False)
            self.ax2b.grid(False)

        if axis1_is_plotted:
            self.ax1.yaxis.set_visible(True)
            self.ax2.yaxis.set_visible(True)
        else:
            self.ax1.yaxis.set_visible(False)
            self.ax2.yaxis.set_visible(False)

        if axis2_is_plotted:
            self.ax1b.yaxis.set_visible(True)
            self.ax2b.yaxis.set_visible(True)
        else:
            self.ax1b.yaxis.set_visible(False)
            self.ax2b.yaxis.set_visible(False)

    def _set_title(self):
        """Write main plot title."""

        # Store start and end timestamp of plot data for title
        # try:
        #     tstart = df.iloc[0, 0].strftime("%d %b %Y %H:%M:%S").lstrip("0")
        #     tend = df.iloc[-1, 0].strftime("%d %b %Y %H:%M:%S")[-8:]
        #     subtitle = f"{tstart} to {tend}"
        # except:
        #     subtitle = ""
        subtitle = ""
        title = f"{self.plot_setup.project_name} {subtitle}".strip()
        self.fig.suptitle(
            title,
            # size=16,
            fontname="tahoma",
            color=color_2H,
            weight="bold",
        )

    def _set_legend(self):
        self.fig.legend(loc="lower center", ncol=4, fontsize=9)

    def export_plot_data_to_excel(self):
        """Export all plot data to Excel."""

        all_srs = self.plot_setup.axis1_series_list + self.plot_setup.axis2_series_list

        # Collate all time series to data frame
        df_ts_list = []
        for srs in all_srs:
            y = srs.y
            if len(y) > 0:
                df = pd.DataFrame(y, index=srs.x, columns=[srs.label])
                df_ts_list.append(df)

            y = srs.y_filt
            if len(y) > 0:
                df = pd.DataFrame(y, index=srs.x, columns=[srs.label])
                df_ts_list.append(df)

        # Collate all psd series to data frame
        df_psd_list = []
        for srs in all_srs:
            pxx = srs.pxx
            if len(pxx) > 0:
                df = pd.DataFrame(pxx, index=srs.freq, columns=[srs.label])
                df_psd_list.append(df)

            pxx = srs.pxx_filt
            if len(pxx) > 0:
                df = pd.DataFrame(pxx, index=srs.freq, columns=[srs.label])
                df_psd_list.append(df)

        # Concatenate to sheet data frame
        try:
            df_ts = pd.concat(df_ts_list, axis=1, sort=False)
            df_ts.index.name = "Time (s)"
            df_psd = pd.concat(df_psd_list, axis=1, sort=False)
            df_psd.index.name = "Freq (Hz)"
        except ValueError:
            print("Export plot data fail")
            return

        # Write to Excel
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Plot Data", filter="Excel File (*.xlsx)"
        )
        if filename:
            writer = pd.ExcelWriter(filename, engine="xlsxwriter")
            wb = writer.book
            fmt = wb.add_format({"text_wrap": True})

            # Time series
            df_ts.to_excel(writer, sheet_name="Time Series", float_format="%.3f")
            ws = writer.sheets["Time Series"]
            # ws.set_row(1, None, fmt)
            # ws.set_column("B:B", None, fmt)

            # PSD sheet
            df_psd.to_excel(writer, sheet_name="PSD")
            ws = writer.sheets["PSD"]
            # ws.set_row(1, None, fmt)
            # ws.set_column("A:A", None, fmt)
            # ws.write("B1", "Craig BOP_2018_0607_1620.csv BOP AccelX", fmt)
            writer.save()

            msg = "Plot data exported successfully."
            QtWidgets.QMessageBox.information(self, "Export Plot Data", msg)

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


class PlotControlsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, plot_settings=RawDataPlotProperties()):
        super(PlotControlsDialog, self).__init__(parent)

        self.parent = parent
        self.plot_settings = plot_settings

        # Window combo options
        self.windows = ["None", "Hann", "Hamming", "Bartlett", "Blackman"]

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setWindowTitle("Raw Data Dashboard Plot Settings")

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

        # Legend settings
        self.filenameInLegend = QtWidgets.QCheckBox("Include file name in legend")
        self.filenameInLegend.setChecked(True)
        self.datasetInLegend = QtWidgets.QCheckBox("Include dataset in legend")
        self.datasetInLegend.setChecked(True)
        self.columnInLegend = QtWidgets.QCheckBox("Include column in legend")
        self.columnInLegend.setChecked(True)

        # CONTAINERS
        # Title and axes labels form
        self.formTitle = QtWidgets.QFormLayout()
        self.formTitle.addRow(QtWidgets.QLabel("Project title:"), self.optProject)

        # Time series axes limits
        self.tsGroup = QtWidgets.QGroupBox("Time Series Limits")
        self.tsGroup.setSizePolicy(policy)
        self.grid = QtWidgets.QGridLayout(self.tsGroup)
        self.grid.addWidget(QtWidgets.QLabel("X min:"), 0, 0)
        self.grid.addWidget(self.optTSXmin, 0, 1)
        self.grid.addWidget(QtWidgets.QLabel("X max:"), 0, 2)
        self.grid.addWidget(self.optTSXmax, 0, 3)
        # self.grid.addWidget(QtWidgets.QLabel('Y min:'), 1, 0)
        # self.grid.addWidget(self.optTSYmin, 1, 1)
        # self.grid.addWidget(QtWidgets.QLabel('Y max:'), 1, 2)
        # self.grid.addWidget(self.optTSYmax, 1, 3)

        # PSD axes limits
        self.psdGroup = QtWidgets.QGroupBox("PSD Limits")
        self.psdGroup.setSizePolicy(policy)
        self.grid = QtWidgets.QGridLayout(self.psdGroup)
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
        self.hboxLimits.addWidget(self.tsGroup)
        self.hboxLimits.addWidget(self.psdGroup)
        self.hboxLimits.addStretch()

        # Legend group
        self.legendGroup = QtWidgets.QGroupBox("Legend Format")
        self.legendGroup.setSizePolicy(policy)
        self.vboxLeg = QtWidgets.QVBoxLayout(self.legendGroup)
        self.vboxLeg.addWidget(self.filenameInLegend)
        self.vboxLeg.addWidget(self.datasetInLegend)
        self.vboxLeg.addWidget(self.columnInLegend)

        # Parameters choice radios
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.radioDefault)
        self.vbox.addWidget(self.radioWelch)
        self.vbox.addWidget(self.radioCustom)
        self.vbox.addStretch()

        # PSD parameters form
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.addRow(
            QtWidgets.QLabel("Number of segments:"), self.optNumEnsembles
        )
        self.formLayout.addRow(QtWidgets.QLabel("Window:"), self.optWindow)
        self.formLayout.addRow(
            QtWidgets.QLabel("Segment overlap (%):"), self.optOverlap
        )
        self.formLayout.addRow(
            QtWidgets.QLabel("Number of points per segment (echo):"), self.optNperseg
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
        self.layout.addWidget(self.paramGroup)
        self.layout.addWidget(self.legendGroup)
        self.layout.addStretch()
        self.layout.addWidget(self.buttonBox)

    def _connect_signals(self):
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

        self._set_plot_settings()

        # This flag stops the on_xlims_changed event from processing
        self.parent.skip_on_xlims_changed = True
        self.parent.rebuild_plots()
        self.parent.skip_on_xlims_changed = False

    def set_dialog_data(self):
        """Get plot parameters from the time series widget and assign to settings widget."""

        self.optProject.setText(self.plot_settings.project_name)
        # self.optTSXmin.setText(f"{self.parent.ax1.get_xlim()[0]:.1f}")
        # self.optTSXmax.setText(f"{self.parent.ax1.get_xlim()[1]:.1f}")
        # self.optPSDXmin.setText(f"{self.parent.ax2.get_xlim()[0]:.1f}")
        # self.optPSDXmax.setText(f"{self.parent.ax2.get_xlim()[1]:.1f}")
        self.optTSXmin.setText(str(self.parent.ax1.get_xlim()[0]))
        self.optTSXmax.setText(str(self.parent.ax1.get_xlim()[1]))
        self.optPSDXmin.setText(str(self.parent.ax2.get_xlim()[0]))
        self.optPSDXmax.setText(str(self.parent.ax2.get_xlim()[1]))

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

        # Legend options
        self.filenameInLegend.setChecked(self.plot_settings.filename_in_legend)
        self.datasetInLegend.setChecked(self.plot_settings.dataset_in_legend)
        self.columnInLegend.setChecked(self.plot_settings.column_in_legend)

    def _set_plot_settings(self):
        """Update the plot properties of the plot settings object."""

        self.plot_settings.project_name = self.optProject.text()

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

        if self.radioDefault.isChecked():
            self.plot_settings.psd_params_type = "default"
        elif self.radioWelch.isChecked():
            self.plot_settings.psd_params_type = "welch"
        else:
            self.plot_settings.psd_params_type = "custom"

        # Legend options
        self.plot_settings.filename_in_legend = self.filenameInLegend.isChecked()
        self.plot_settings.dataset_in_legend = self.datasetInLegend.isChecked()
        self.plot_settings.column_in_legend = self.columnInLegend.isChecked()

    def reset_values(self):
        """Reset option settings to initial values set during file load."""

        self.optTSXmin.setText(str(round(self.plot_settings.init_xlim[0], 1)))
        self.optTSXmax.setText(str(round(self.plot_settings.init_xlim[1], 1)))
        self.optPSDXmin.setText("0.0")
        self.optPSDXmax.setText("1.0")
        self.radioDefault.setChecked(True)
        self.filenameInLegend.setChecked(True)
        self.datasetInLegend.setChecked(True)
        self.columnInLegend.setChecked(True)


# For testing layout
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # win = RawDataDashboard()
    win = PlotControlsDialog()
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
