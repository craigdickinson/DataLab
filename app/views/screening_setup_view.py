"""Screening setup tab and edit dialog."""

__author__ = "Craig Dickinson"

import logging
import sys

from PyQt5 import QtCore, QtGui, QtWidgets
from dateutil.parser import parse

from app.core.control import Control
from app.core.logger_properties import LoggerProperties


class ScreeningSetupTab(QtWidgets.QWidget):
    """GUI screen to control project setup."""

    def __init__(self, parent=None, control=Control()):
        super(ScreeningSetupTab, self).__init__(parent)

        self.parent = parent
        self.control = control
        self.logger = LoggerProperties()
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Create widget layout."""

        # WIDGETS
        self.editButton = QtWidgets.QPushButton("Edit Data...")
        self.editButton.setShortcut("Ctrl+E")
        self.editButton.setToolTip("Ctrl+E")
        self.columns = QtWidgets.QLabel("-")
        self.unitConvs = QtWidgets.QLabel("-")
        self.channelNames = QtWidgets.QLabel("-")
        self.channelUnits = QtWidgets.QLabel("-")
        self.processStart = QtWidgets.QLabel("-")
        self.processEnd = QtWidgets.QLabel("-")
        self.processType = QtWidgets.QLabel("-")
        self.lowCutoff = QtWidgets.QLabel("-")
        self.highCutoff = QtWidgets.QLabel("-")

        # Stats settings
        self.processStatsChkBox = QtWidgets.QCheckBox("Include in processing")
        self.processStatsChkBox.setChecked(True)
        self.statsFolder = QtWidgets.QLabel()
        self.statsInterval = QtWidgets.QLabel("-")
        self.statsCSVChkBox = QtWidgets.QCheckBox(".csv")
        self.statsCSVChkBox.setChecked(True)
        self.statsXLSXChkBox = QtWidgets.QCheckBox(".xlsx")
        self.statsH5ChkBox = QtWidgets.QCheckBox(".h5 (fast read/write)")

        # Spectral settings
        self.processSpectChkBox = QtWidgets.QCheckBox("Include in processing")
        self.processSpectChkBox.setChecked(True)
        self.spectFolder = QtWidgets.QLabel()
        self.spectInterval = QtWidgets.QLabel("-")
        self.psdNperseg = QtWidgets.QLabel("-")
        self.psdWindow = QtWidgets.QLabel("-")
        self.psdOverlap = QtWidgets.QLabel("-")
        self.spectCSVChkBox = QtWidgets.QCheckBox(".csv")
        self.spectCSVChkBox.setChecked(True)
        self.spectXLSXChkBox = QtWidgets.QCheckBox(".xlsx")
        self.spectH5ChkBox = QtWidgets.QCheckBox(".h5 (fast read/write)")

        # Rainflow counting settings
        self.processRainflowChkBox = QtWidgets.QCheckBox("Include in processing")
        self.processRainflowChkBox.setChecked(True)

        self.rainflowFolder = QtWidgets.QLabel()
        self.binSize = QtWidgets.QLabel("-")

        # Process range labels
        self.lblProcessStart = QtWidgets.QLabel("Start timestamp:")
        self.lblProcessEnd = QtWidgets.QLabel("End timestamp:")

        # CONTAINERS
        # Columns to process group
        self.colsGroup = QtWidgets.QGroupBox("Columns to Process Settings")
        self.colsForm = QtWidgets.QFormLayout(self.colsGroup)
        self.colsForm.addRow(
            QtWidgets.QLabel("Column numbers to process:"), self.columns
        )
        self.colsForm.addRow(
            QtWidgets.QLabel("Unit conversion factors:"), self.unitConvs
        )
        self.colsForm.addRow(
            QtWidgets.QLabel("Channel names override (optional):"), self.channelNames
        )
        self.colsForm.addRow(
            QtWidgets.QLabel("Channel units override (optional):"), self.channelUnits
        )

        # Processing range group
        self.processRangeGroup = QtWidgets.QGroupBox("Processing Range")
        self.processRangeForm = QtWidgets.QFormLayout(self.processRangeGroup)
        self.processRangeForm.addRow(self.lblProcessStart, self.processStart)
        self.processRangeForm.addRow(self.lblProcessEnd, self.processEnd)

        # Filters group
        self.filtersGroup = QtWidgets.QGroupBox("Frequency Filters")
        self.filtersForm = QtWidgets.QFormLayout(self.filtersGroup)
        self.filtersForm.addRow(QtWidgets.QLabel("Screen on:"), self.processType)
        self.filtersForm.addRow(
            QtWidgets.QLabel("Low cut-off frequency (Hz):"), self.lowCutoff
        )
        self.filtersForm.addRow(
            QtWidgets.QLabel("High cut-off frequency (Hz):"), self.highCutoff
        )

        # Stats settings group
        self.statsGroup = QtWidgets.QGroupBox("Statistical Analysis Settings")
        self.statsGroup.setMinimumWidth(250)
        self.statsForm = QtWidgets.QFormLayout(self.statsGroup)
        self.statsForm.addRow(self.processStatsChkBox, QtWidgets.QLabel(""))
        self.statsForm.addRow(QtWidgets.QLabel("Output folder:"), self.statsFolder)
        self.statsForm.addRow(
            QtWidgets.QLabel("Sample length (s):"), self.statsInterval
        )

        # Spectral settings group
        self.spectGroup = QtWidgets.QGroupBox("Spectral Analysis Settings")
        self.spectGroup.setMinimumWidth(250)
        self.spectForm = QtWidgets.QFormLayout(self.spectGroup)
        self.spectForm.addRow(self.processSpectChkBox, QtWidgets.QLabel(""))
        self.spectForm.addRow(QtWidgets.QLabel("Output folder:"), self.spectFolder)
        self.spectForm.addRow(
            QtWidgets.QLabel("Sample length (s):"), self.spectInterval
        )
        self.spectForm.addRow(
            QtWidgets.QLabel("Number of points per segment:"), self.psdNperseg
        )
        self.spectForm.addRow(QtWidgets.QLabel("Window:"), self.psdWindow)
        self.spectForm.addRow(QtWidgets.QLabel("Segment overlap (%):"), self.psdOverlap)

        # Stats output file formats group
        self.statsOutputGroup = QtWidgets.QGroupBox("Stats File Formats to Output")
        self.statsOutputGroup.setFixedWidth(170)
        self.vbox = QtWidgets.QVBoxLayout(self.statsOutputGroup)
        self.vbox.addWidget(self.statsCSVChkBox)
        self.vbox.addWidget(self.statsXLSXChkBox)
        self.vbox.addWidget(self.statsH5ChkBox)

        # Spectral output file formats group
        self.spectOutputGroup = QtWidgets.QGroupBox("Spectral File Formats to Output")
        self.spectOutputGroup.setFixedWidth(170)
        self.vbox = QtWidgets.QVBoxLayout(self.spectOutputGroup)
        self.vbox.addWidget(self.spectCSVChkBox)
        self.vbox.addWidget(self.spectXLSXChkBox)
        self.vbox.addWidget(self.spectH5ChkBox)

        # Rainflow settings group
        self.rainflowGroup = QtWidgets.QGroupBox("Rainflow Cycle Histogram Settings")
        self.rainflowGroup.setMinimumWidth(250)
        self.rainflowForm = QtWidgets.QFormLayout(self.rainflowGroup)
        self.rainflowForm.addRow(self.processRainflowChkBox, QtWidgets.QLabel(""))
        self.rainflowForm.addRow(
            QtWidgets.QLabel("Output folder:"), self.rainflowFolder
        )
        self.rainflowForm.addRow(QtWidgets.QLabel("Bin size:"), self.binSize)

        # LAYOUT
        self.hboxStats = QtWidgets.QHBoxLayout()
        self.hboxStats.setAlignment(QtCore.Qt.AlignLeft)
        self.hboxStats.addWidget(self.statsGroup)
        self.hboxStats.addWidget(self.statsOutputGroup, alignment=QtCore.Qt.AlignTop)

        # Now add spectral group box vertical layouts to a horizontal one
        self.hboxSpect = QtWidgets.QHBoxLayout()
        self.hboxSpect.setAlignment(QtCore.Qt.AlignLeft)
        self.hboxSpect.addWidget(self.spectGroup)
        self.hboxSpect.addWidget(self.spectOutputGroup, alignment=QtCore.Qt.AlignTop)

        # Combine all layouts
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.editButton, stretch=0, alignment=QtCore.Qt.AlignLeft)
        self.vbox.addWidget(self.colsGroup)
        self.vbox.addWidget(self.processRangeGroup)
        self.vbox.addWidget(self.filtersGroup)
        self.vbox.addLayout(self.hboxStats)
        self.vbox.addLayout(self.hboxSpect)
        self.vbox.addWidget(self.rainflowGroup)
        self.vbox.addStretch()

        self.hbox = QtWidgets.QHBoxLayout(self)
        self.hbox.addLayout(self.vbox)
        self.hbox.addStretch()

    def _connect_signals(self):
        self.editButton.clicked.connect(self.on_edit_clicked)
        self.processStatsChkBox.toggled.connect(self.on_process_stats_check_box_toggled)
        self.processSpectChkBox.toggled.connect(self.on_process_spect_check_box_toggled)
        self.statsH5ChkBox.toggled.connect(self.on_stats_h5_toggled)
        self.statsCSVChkBox.toggled.connect(self.on_stats_csv_toggled)
        self.statsXLSXChkBox.toggled.connect(self.on_stats_xlsx_toggled)
        self.spectH5ChkBox.toggled.connect(self.on_spect_h5_toggled)
        self.spectCSVChkBox.toggled.connect(self.on_spect_csv_toggled)
        self.spectXLSXChkBox.toggled.connect(self.on_spect_xlsx_toggled)

    def on_edit_clicked(self):
        """Open logger screening edit dialog."""

        if not self.parent:
            return

        if self.parent.loggersList.count() == 0:
            msg = f"No loggers exist to edit. Add a logger first."
            return QtWidgets.QMessageBox.information(
                self, "Edit Logger Statistics and Spectral Analysis Settings", msg
            )

        # Retrieve selected logger object
        logger_idx = self.parent.loggersList.currentRow()

        # Edit stats dialog class
        editStatsSettings = EditScreeningSetupDialog(self, self.control, logger_idx)
        editStatsSettings.show()

    def on_process_stats_check_box_toggled(self):
        """Set include in processing state in logger object."""

        if self.parent.loggersList.count() > 0:
            self.logger.process_stats = self.processStatsChkBox.isChecked()

    def on_process_spect_check_box_toggled(self):
        """Set include in processing state in logger object."""

        if self.parent.loggersList.count() > 0:
            self.logger.process_spect = self.processSpectChkBox.isChecked()

    def on_stats_h5_toggled(self):
        if self.parent.loggersList.count() > 0:
            if self.statsH5ChkBox.isChecked():
                self.control.stats_to_h5 = True
            else:
                self.control.stats_to_h5 = False

    def on_stats_csv_toggled(self):
        if self.parent.loggersList.count() > 0:
            if self.statsCSVChkBox.isChecked():
                self.control.stats_to_csv = True
            else:
                self.control.stats_to_csv = False

    def on_stats_xlsx_toggled(self):
        if self.parent.loggersList.count() > 0:
            if self.statsXLSXChkBox.isChecked():
                self.control.stats_to_xlsx = True
            else:
                self.control.stats_to_xlsx = False

    def on_spect_h5_toggled(self):
        if self.parent.loggersList.count() > 0:
            if self.spectH5ChkBox.isChecked():
                self.control.spect_to_h5 = True
            else:
                self.control.spect_to_h5 = False

    def on_spect_csv_toggled(self):
        if self.parent.loggersList.count() > 0:
            if self.spectCSVChkBox.isChecked():
                self.control.spect_to_csv = True
            else:
                self.control.spect_to_csv = False

    def on_spect_xlsx_toggled(self):
        if self.parent.loggersList.count() > 0:
            if self.spectXLSXChkBox.isChecked():
                self.control.spect_to_xlsx = True
            else:
                self.control.spect_to_xlsx = False

    def set_analysis_dashboard(self, logger):
        """Set dashboard with logger stats and spectral settings from logger object."""

        self.logger = logger

        # Process check states
        self.processStatsChkBox.setChecked(logger.process_stats)
        self.processSpectChkBox.setChecked(logger.process_spect)

        # Columns
        cols_str = " ".join([str(i) for i in logger.cols_to_process])
        self.columns.setText(cols_str)

        # Unit conversion factors
        unit_conv_factors_str = " ".join([str(i) for i in logger.unit_conv_factors])
        self.unitConvs.setText(unit_conv_factors_str)

        # Channel names
        channel_items_str = ", ".join([i for i in logger.user_channel_names])
        self.channelNames.setText(channel_items_str)

        # Channel units
        units_items_str = " ".join([i for i in logger.user_channel_units])
        self.channelUnits.setText(units_items_str)

        # Set the process start/end labels in the Screening dashboard that pertain to the first logger (if exists)
        self.set_process_date_labels(logger.file_timestamp_embedded)

        # Set start/end timestamp/index
        process_start = self._set_process_start(logger)
        self.processStart.setText(process_start)
        process_end = self._set_process_end(logger)
        self.processEnd.setText(process_end)

        # Low cut-off frequency
        if logger.low_cutoff_freq is None:
            self.lowCutoff.setText("None")
        else:
            self.lowCutoff.setText(f"{logger.low_cutoff_freq:.2f}")

        # High cut-off frequency
        if logger.high_cutoff_freq is None:
            self.highCutoff.setText("None")
        else:
            self.highCutoff.setText(f"{logger.high_cutoff_freq:.2f}")

        # Screen on
        self.processType.setText(logger.process_type)

        # Stats and spectral interval
        self.statsInterval.setText(str(logger.stats_interval))
        self.spectInterval.setText(str(logger.spect_interval))

        # Set PSD parameters
        self._set_psd_params(logger)

        # Output folders
        self.statsFolder.setText(self.parent.control.stats_output_folder)
        self.spectFolder.setText(self.parent.control.spect_output_folder)

        # Selected stats file formats to output
        self.statsH5ChkBox.setChecked(self.control.stats_to_h5)
        self.statsCSVChkBox.setChecked(self.control.stats_to_csv)
        self.statsXLSXChkBox.setChecked(self.control.stats_to_xlsx)

        # Selected spectral file formats to output
        self.spectH5ChkBox.setChecked(self.control.spect_to_h5)
        self.spectCSVChkBox.setChecked(self.control.spect_to_csv)
        self.spectXLSXChkBox.setChecked(self.control.spect_to_xlsx)

    @staticmethod
    def _set_process_start(logger):
        # Start timestamp/index
        if logger.process_start is None:
            process_start = "First"
        else:
            if logger.file_timestamp_embedded is True:
                process_start = logger.process_start.strftime("%Y-%m-%d %H:%M")
            else:
                process_start = str(logger.process_start)

        return process_start

    @staticmethod
    def _set_process_end(logger):
        # End timestamp/index
        if logger.process_end is None:
            process_end = "Last"
        else:
            if logger.file_timestamp_embedded is True:
                process_end = logger.process_end.strftime("%Y-%m-%d %H:%M")
            else:
                process_end = str(logger.process_end)

        return process_end

    def _set_psd_params(self, logger):
        self.psdNperseg.setText(str(logger.psd_nperseg))
        self.psdWindow.setText(logger.psd_window)
        self.psdOverlap.setText(f"{logger.psd_overlap:.1f}")

    def clear_dashboard(self):
        """Initialise all values in stats and spectral analysis dashboard."""

        self.columns.setText("-")
        self.unitConvs.setText("-")
        self.channelNames.setText("-")
        self.channelUnits.setText("-")
        self.processStart.setText("-")
        self.processEnd.setText("-")
        self.lowCutoff.setText("-")
        self.highCutoff.setText("-")
        self.processType.setText("-")
        self.statsInterval.setText("-")
        self.spectInterval.setText("-")
        self.psdNperseg.setText("-")
        self.psdWindow.setText("-")
        self.psdOverlap.setText("-")
        self.statsFolder.setText("Statistics")
        self.spectFolder.setText("Spectrograms")

    def set_process_date_labels(self, file_timestamp_embedded):
        """Set process start and end labels to refer to dates or file indexes depending on setup of current logger."""

        if file_timestamp_embedded is True:
            self.lblProcessStart.setText("Start timestamp:")
            self.lblProcessEnd.setText("End timestamp:")
        else:
            self.lblProcessStart.setText("Start file number:")
            self.lblProcessEnd.setText("End file number:")


class EditScreeningSetupDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, control=Control(), logger_idx=0):
        super(EditScreeningSetupDialog, self).__init__(parent)

        self.parent = parent

        # Store control settings and selected logger properties objects
        self.control = control
        self.logger_idx = logger_idx
        if control.loggers:
            self.logger = control.loggers[logger_idx]
        else:
            self.logger = LoggerProperties()

        self._init_ui()
        self._connect_signals()
        self._set_dialog_data(self.logger)

        # Populate copy loggers combo box and enable/disable stats/spectral interval inputs
        self._set_copy_logger_combo()
        self._configure_interval_inputs()

    def _init_ui(self):
        self.setWindowTitle("Edit Logger Statistics and Spectral Analysis Settings")
        self.setMinimumWidth(600)

        # Define input validators
        int_validator = QtGui.QIntValidator()
        int_validator.setBottom(1)
        dbl_validator = QtGui.QDoubleValidator()

        # Message for stats/spectral interval inputs
        tooltip_msg = (
            "Note: This input will be disabled if logger file format is 'Custom' "
            "and first column data is set to 'Time Step'"
        )

        # Window combo options
        windows = ["None", "Hann", "Hamming", "Bartlett", "Blackman"]

        # WIDGETS
        self.copyLogger = QtWidgets.QComboBox()
        self.copyLogger.setMinimumWidth(80)
        self.copyLogger.addItem("-")
        self.copyLoggerButton = QtWidgets.QPushButton("&Copy Settings")

        self.columns = QtWidgets.QLineEdit()
        self.columns.setToolTip(
            "SPACE-separated column numbers to process.\n"
            "If blank or 'All' all columns will be processed.\n"
            "E.g. 2 3 4 5 (column 1 (time index) does not need to be included)."
        )
        self.unitConvs = QtWidgets.QLineEdit()
        self.unitConvs.setToolTip(
            "SPACE-separated column unit conversion factors.\n"
            "E.g. 0.001 0.001 57.29578 57.29578."
        )
        self.channelNames = QtWidgets.QLineEdit()
        self.channelNames.setToolTip(
            "COMMA-separated custom channel names.\n"
            "E.g. AccelX, AccelY, AngRateX, AngRateY."
        )
        self.channelUnits = QtWidgets.QLineEdit()
        self.channelUnits.setToolTip(
            "SPACE-separated custom channel units.\n" "E.g. m/s^2 m/s^2 deg/s deg/s."
        )
        self.processStart = QtWidgets.QLineEdit()
        self.processStart.setFixedWidth(100)
        self.processEnd = QtWidgets.QLineEdit()
        self.processEnd.setFixedWidth(100)
        self.processType = QtWidgets.QComboBox()
        self.processType.addItems(
            ["Both unfiltered and filtered", "Unfiltered only", "Filtered only"]
        )
        self.processType.setFixedWidth(160)
        self.lowCutoff = QtWidgets.QLineEdit()
        self.lowCutoff.setFixedWidth(40)
        self.lowCutoff.setValidator(dbl_validator)
        self.highCutoff = QtWidgets.QLineEdit()
        self.highCutoff.setFixedWidth(40)
        self.highCutoff.setValidator(dbl_validator)

        self.statsFolder = QtWidgets.QLineEdit()
        self.statsFolder.setFixedWidth(210)
        self.statsInterval = QtWidgets.QLineEdit()
        self.statsInterval.setFixedWidth(50)
        self.statsInterval.setValidator(int_validator)
        self.statsInterval.setToolTip(tooltip_msg)

        self.spectFolder = QtWidgets.QLineEdit()
        self.spectFolder.setFixedWidth(210)
        self.spectInterval = QtWidgets.QLineEdit()
        self.spectInterval.setFixedWidth(50)
        self.spectInterval.setValidator(int_validator)
        self.spectInterval.setToolTip(tooltip_msg)
        self.psdNperseg = QtWidgets.QLineEdit()
        self.psdNperseg.setFixedWidth(50)
        self.psdNperseg.setToolTip("Number of points to use per PSD.")
        self.psdNperseg.setValidator(int_validator)
        self.psdWindowCombo = QtWidgets.QComboBox()
        self.psdWindowCombo.setFixedWidth(70)
        self.psdWindowCombo.setToolTip("PSD window function to apply.")
        self.psdWindowCombo.addItems(windows)
        self.psdOverlap = QtWidgets.QLineEdit()
        self.psdOverlap.setFixedWidth(50)
        self.psdOverlap.setToolTip("Percentage of points to overlap each PSD segment.")
        self.psdOverlap.setValidator(dbl_validator)

        # Rainflow cycle histogram settings
        self.histFolder = QtWidgets.QLineEdit()
        self.histFolder.setFixedWidth(210)
        self.binSize = QtWidgets.QLineEdit()
        self.binSize.setFixedWidth(50)
        self.binSize.setValidator(dbl_validator)

        # Labels
        self.lblCopy = QtWidgets.QLabel("Logger to copy:")
        self.lblColumns = QtWidgets.QLabel("Column numbers to process:")
        self.lblUnitConvs = QtWidgets.QLabel("Unit conversion factors (optional):")
        self.lblChannelNames = QtWidgets.QLabel("Channel names override (optional):")
        self.lblChannelUnits = QtWidgets.QLabel("Channel units override (optional):")
        self.lblProcessType = QtWidgets.QLabel("Screen on:")
        self.lblLowCutoff = QtWidgets.QLabel("Low cut-off frequency (Hz):")
        self.lblHighCutoff = QtWidgets.QLabel("High cut-off frequency (Hz):")

        self.lblStatsFolder = QtWidgets.QLabel("Output folder:")
        self.lblStatsInterval = QtWidgets.QLabel("Sample length (s):")

        self.lblSpectFolder = QtWidgets.QLabel("Output folder:")
        self.lblSpectInterval = QtWidgets.QLabel("Sample length (s):")
        self.lblPsdNperseg = QtWidgets.QLabel("Number of points per segment:")
        self.lblPsdWindow = QtWidgets.QLabel("Window:")
        self.lblPsdOverlap = QtWidgets.QLabel("Segment overlap (%):")

        self.lblRainflowFolder = QtWidgets.QLabel("Output folder:")
        self.lblBinSize = QtWidgets.QLabel("Cycle histogram bin size:")

        # Set appropriate process start and end input depending on whether filenames include timestamps
        if self.logger.file_timestamp_embedded is True:
            self.lblProcessStart = QtWidgets.QLabel("Start timestamp:")
            self.lblProcessEnd = QtWidgets.QLabel("End timestamp:")
            proc_start_tip = "If blank or 'First', the timestamp of the first file will be used (if detected)."
            proc_end_tip = "If blank or 'Last', the timestamp of the last file will be used (if detected)."
        else:
            self.lblProcessStart = QtWidgets.QLabel("Start file number:")
            self.lblProcessEnd = QtWidgets.QLabel("End file number:")
            proc_start_tip = "If blank or 'First', the first file number will be used."
            proc_end_tip = (
                "If blank or 'Last', the last file number will be used (if detected)."
            )

        # Set appropriate process start and end tooltip
        self.processStart.setToolTip(proc_start_tip)
        self.processEnd.setToolTip(proc_end_tip)

        # CONTAINERS
        policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )

        # Copy logger group
        self.copyGroup = QtWidgets.QGroupBox(
            "Optional: Copy Settings from Another Logger"
        )
        self.copyGroup.setSizePolicy(policy)
        self.hboxCopy = QtWidgets.QHBoxLayout(self.copyGroup)
        self.hboxCopy.addWidget(self.lblCopy)
        self.hboxCopy.addWidget(self.copyLogger)
        self.hboxCopy.addWidget(self.copyLoggerButton)
        self.hboxCopy.addStretch()

        # Columns to process settings group
        self.colsGroup = QtWidgets.QGroupBox("Columns to Process Settings")
        self.colsForm = QtWidgets.QFormLayout(self.colsGroup)
        self.colsForm.addRow(self.lblColumns, self.columns)
        self.colsForm.addRow(self.lblUnitConvs, self.unitConvs)
        self.colsForm.addRow(self.lblChannelNames, self.channelNames)
        self.colsForm.addRow(self.lblChannelUnits, self.channelUnits)

        # Processing range group
        self.processRangeGroup = QtWidgets.QGroupBox("Processing Range")
        self.processRangeGroup.setSizePolicy(policy)
        self.processRangeForm = QtWidgets.QFormLayout(self.processRangeGroup)
        self.processRangeForm.addRow(self.lblProcessStart, self.processStart)
        self.processRangeForm.addRow(self.lblProcessEnd, self.processEnd)

        # Filters group
        self.filtersGroup = QtWidgets.QGroupBox("Frequency Filters")
        self.filtersGroup.setSizePolicy(policy)
        self.filtersForm = QtWidgets.QFormLayout(self.filtersGroup)
        self.filtersForm.addRow(self.lblProcessType, self.processType)
        self.filtersForm.addRow(self.lblLowCutoff, self.lowCutoff)
        self.filtersForm.addRow(self.lblHighCutoff, self.highCutoff)

        # Stats settings group
        self.statsGroup = QtWidgets.QGroupBox("Statistics Screening Settings")
        self.statsForm = QtWidgets.QFormLayout(self.statsGroup)
        self.statsForm.addRow(self.lblStatsFolder, self.statsFolder)
        self.statsForm.addRow(self.lblStatsInterval, self.statsInterval)

        # Spectral settings group
        self.spectGroup = QtWidgets.QGroupBox("Spectral Screening Settings")
        self.spectForm = QtWidgets.QFormLayout(self.spectGroup)
        self.spectForm.addRow(self.lblSpectFolder, self.spectFolder)
        self.spectForm.addRow(self.lblSpectInterval, self.spectInterval)
        self.spectForm.addRow(self.lblPsdNperseg, self.psdNperseg)
        self.spectForm.addRow(self.lblPsdWindow, self.psdWindowCombo)
        self.spectForm.addRow(self.lblPsdOverlap, self.psdOverlap)

        # Rainflow histograms group
        self.rainflowGroup = QtWidgets.QGroupBox("Rainflow Cycle Histogram Settings")
        self.rainflowForm = QtWidgets.QFormLayout(self.rainflowGroup)
        self.rainflowForm.addRow(self.lblRainflowFolder, self.histFolder)
        self.rainflowForm.addRow(self.lblBinSize, self.binSize)

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        # LAYOUT
        # Horizontal groups
        self.hboxRangeAndFilters = QtWidgets.QHBoxLayout()
        self.hboxRangeAndFilters.addWidget(
            self.processRangeGroup, alignment=QtCore.Qt.AlignTop
        )
        self.hboxRangeAndFilters.addWidget(self.filtersGroup)
        self.hboxRangeAndFilters.addStretch()

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.copyGroup)
        self.layout.addWidget(self.colsGroup)
        self.layout.addLayout(self.hboxRangeAndFilters)
        self.layout.addWidget(self.statsGroup)
        self.layout.addWidget(self.spectGroup)
        self.layout.addWidget(self.rainflowGroup)
        self.layout.addWidget(self.buttonBox)

    def _connect_signals(self):
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.copyLoggerButton.clicked.connect(self.on_copy_logger_clicked)

    def _set_dialog_data(self, logger):
        """Set dialog data with logger stats from control object."""

        if not self.parent:
            return

        # Columns to process
        cols_str = " ".join([str(i) for i in logger.cols_to_process])
        if cols_str == "":
            cols_str = "All"
        self.columns.setText(cols_str)

        # Unit conversion factors
        unit_conv_factors_str = " ".join([str(i) for i in logger.unit_conv_factors])
        self.unitConvs.setText(unit_conv_factors_str)

        # Channel names
        channel_items_str = ", ".join([i for i in logger.user_channel_names])
        self.channelNames.setText(channel_items_str)

        # Channel units
        units_items_str = " ".join([i for i in logger.user_channel_units])
        self.channelUnits.setText(units_items_str)

        # Process start
        if logger.process_start is None:
            process_start = "First"
        else:
            # Determine if process start is a file number or timestamp
            if type(logger.process_start) is int:
                process_start = str(logger.process_start)
            else:
                process_start = logger.process_start.strftime("%Y-%m-%d %H:%M")
        self.processStart.setText(process_start)

        # Process end
        if logger.process_end is None:
            process_end = "Last"
        else:
            # Determine if process end is a file number or timestamp
            if type(logger.process_end) is int:
                process_end = str(logger.process_end)
            else:
                process_end = logger.process_end.strftime("%Y-%m-%d %H:%M")
        self.processEnd.setText(process_end)

        # Low cut-off frequency
        if logger.low_cutoff_freq is None:
            self.lowCutoff.setText("None")
        else:
            self.lowCutoff.setText(f"{logger.low_cutoff_freq:.2f}")

        # High cut-off frequency
        if logger.high_cutoff_freq is None:
            self.highCutoff.setText("None")
        else:
            self.highCutoff.setText(f"{logger.high_cutoff_freq:.2f}")

        # Data to screen on
        self.processType.setCurrentText(logger.process_type)

        # Stats and spectral sample length
        self.statsInterval.setText(str(logger.stats_interval))
        self.spectInterval.setText(str(logger.spect_interval))

        # PSD parameters
        self.psdNperseg.setText(str(logger.psd_nperseg))
        self.psdWindowCombo.setCurrentText(logger.psd_window)
        self.psdOverlap.setText(f"{logger.psd_overlap:.1f}")

        # Rainflow histograms settings
        self.binSize.setText(str(logger.bin_size))

        # Folders - global control settings
        self.statsFolder.setText(self.parent.control.stats_output_folder)
        self.spectFolder.setText(self.parent.control.spect_output_folder)
        self.histFolder.setText(self.parent.control.hist_output_folder)

    def _set_copy_logger_combo(self):
        """Set the copy screening settings combo box with list of available loggers, excluding the current one."""

        # Get list of available loggers to copy
        loggers_to_copy = [
            i for i in self.control.logger_ids if i != self.logger.logger_id
        ]
        self.copyLogger.addItems(loggers_to_copy)

    def _configure_interval_inputs(self):
        if self.logger.enforce_max_duration is True:
            self.statsInterval.setEnabled(False)
            self.spectInterval.setEnabled(False)
        else:
            self.statsInterval.setEnabled(True)
            self.spectInterval.setEnabled(True)

    def on_copy_logger_clicked(self):
        """Copy screening settings from another logger selected in the combo box."""

        # Get logger to copy
        ref_logger_id = self.copyLogger.currentText()

        if ref_logger_id == "-":
            return

        # Create a temp logger to copy setting so that settings can be confirmed by the user
        # before mapping to the control logger
        temp_logger = LoggerProperties()

        # Map logger properties from reference logger to active logger and update dialog values
        self.control.copy_logger_screening_settings(ref_logger_id, temp_logger)

        # Set dialog with temp settings so they can confirmed by the user
        self._set_dialog_data(temp_logger)

    def on_ok_clicked(self):
        """Assign logger stats settings to the control object and update the dashboard."""

        if not self.parent:
            return

        try:
            self.logger = self._set_control_data()
            self.parent.set_analysis_dashboard(self.logger)
        except Exception as e:
            msg = "Unexpected error assigning screening settings."
            self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def _set_control_data(self):
        """Assign values to the control object."""

        if not self.parent:
            return

        # Retrieve control logger to map confirmed settings to
        logger = self.control.loggers[self.logger_idx]

        # Processed columns group
        # Set column numbers to process
        cols_str = self.columns.text()
        if cols_str == "" or cols_str.lower() == "all":
            # Use expected number of columns property to set full list
            n = logger.num_columns
            logger.cols_to_process = list(range(2, n + 1))
        else:
            # Convert strings to lists
            try:
                logger.cols_to_process = list(map(int, self.columns.text().split()))
            except ValueError:
                msg = (
                    "Only integer column numbers are allowed.\n"
                    "Separate each number with a space, e.g. 2 3 4 5."
                )
                QtWidgets.QMessageBox.information(
                    self, "Invalid Requested Columns Input", msg
                )

        try:
            logger.unit_conv_factors = list(map(float, self.unitConvs.text().split()))
        except ValueError:
            msg = (
                "Unit conversion factors must be numeric.\n"
                "Separate each input with a space, e.g. 0.001 0.001 57.29578 57.29578."
            )
            QtWidgets.QMessageBox.information(
                self, "Invalid Unit Conversion Factors Input", msg
            )

        # Extract channel names to list
        # Note, because splitting by comma, if input is empty, [""] is returned but want [] so check if populated
        if self.channelNames.text():
            channel_names = [c.strip() for c in self.channelNames.text().split(",")]
        else:
            channel_names = []
        logger.user_channel_names = channel_names
        logger.user_channel_units = self.channelUnits.text().split()

        # Process start and end dates or file indexes
        process_start = self.processStart.text()
        process_end = self.processEnd.text()

        # Process selection made by timestamps
        if logger.file_timestamp_embedded is True:
            if process_start == "" or process_start.lower() == "first":
                logger.process_start = self.get_timestamp_in_filename(
                    logger, file_idx=0
                )
            else:
                try:
                    logger.process_start = parse(process_start, yearfirst=True)
                except ValueError:
                    msg = "Process start datetime format not recognised; timestamp unchanged."
                    QtWidgets.QMessageBox.information(self, "Process Start Input", msg)

            if process_end == "" or process_end.lower() == "last":
                logger.process_end = self.get_timestamp_in_filename(logger, file_idx=-1)
            else:
                try:
                    logger.process_end = parse(process_end, yearfirst=True)
                except ValueError:
                    msg = "Process end datetime format not recognised; timestamp unchanged."
                    QtWidgets.QMessageBox.information(self, "Process End Input", msg)
        # Process selection made by file number (load case)
        else:
            if process_start == "" or process_start.lower() == "first":
                process_start = 1

            try:
                logger.process_start = int(process_start)
            except ValueError:
                msg = "Process start file number must be an integer."
                QtWidgets.QMessageBox.information(self, "Process Start Input", msg)

            if process_end == "" or process_end.lower() == "last":
                try:
                    logger.get_filenames()
                except Exception as e:
                    logging.exception(e)
                finally:
                    process_end = len(logger.raw_filenames)

            if process_end == 0:
                logger.process_end = None
                msg = "Process end file number could not be set; no files found."
                QtWidgets.QMessageBox.information(self, "Process End Input", msg)
            else:
                try:
                    logger.process_end = int(process_end)
                except ValueError:
                    msg = "Process end file number must be an integer."
                    QtWidgets.QMessageBox.information(self, "Process End Input", msg)

        # Low cut-off freq
        try:
            logger.low_cutoff_freq = float(self.lowCutoff.text())
            if logger.low_cutoff_freq == 0:
                logger.low_cutoff_freq = None
        except:
            logger.low_cutoff_freq = None

        # High cut-off freq
        try:
            logger.high_cutoff_freq = float(self.highCutoff.text())
            if logger.high_cutoff_freq == 0:
                logger.high_cutoff_freq = None
        except:
            logger.high_cutoff_freq = None

        # Store combo box index of data to screen on selection
        logger.process_type = self.processType.currentText()

        # Stats settings group
        if (
            self.statsInterval.text() == ""
            or int(float(self.statsInterval.text())) == 0
        ):
            logger.stats_interval = int(logger.duration)
        else:
            # TODO: Question why this is forced to be an int not float?
            logger.stats_interval = int(float(self.statsInterval.text()))

        # Spectral settings group
        if (
            self.spectInterval.text() == ""
            or int(float(self.spectInterval.text())) == 0
        ):
            logger.spect_interval = int(logger.duration)
        else:
            # TODO: Question why this is forced to be an int not float?
            logger.spect_interval = int(float(self.spectInterval.text()))

        # PSD parameters
        num_pts = int(logger.spect_interval * logger.freq)
        try:
            logger.psd_nperseg = int(self.psdNperseg.text())

            if logger.psd_nperseg == 0 or logger.psd_nperseg > num_pts:
                logger.psd_nperseg = num_pts
        except:
            logger.psd_nperseg = num_pts

        logger.psd_window = self.psdWindowCombo.currentText()

        try:
            logger.psd_overlap = float(self.psdOverlap.text())
        except:
            logger.psd_overlap = 50

        # Rainflow histograms settings
        logger.bin_size = float(self.binSize.text())

        # Output folders - store as global control settings
        self.parent.control.stats_output_folder = self.statsFolder.text()
        self.parent.control.spect_output_folder = self.spectFolder.text()
        self.parent.control.hist_output_folder = self.histFolder.text()

        return logger

    @staticmethod
    def get_timestamp_in_filename(logger, file_idx):
        """Attempt to retrieve the timestamp embedded in the filename of the file in the parsed list index."""

        try:
            # Process filenames to get list of files and extract the datetimes embedded in each filename
            filenames = logger.get_filenames()
            logger.get_timestamp_span()
            timestamp = logger.get_file_timestamp(filenames[file_idx])
            return timestamp
        except Exception:
            return None

    def error(self, msg):
        print(f"Error: {msg}")
        return QtWidgets.QMessageBox.critical(self, "Error", msg)


if __name__ == "__main__":
    # For testing widget layout
    app = QtWidgets.QApplication(sys.argv)
    # win = ScreeningSetupTab()
    win = EditScreeningSetupDialog()
    win.show()
    app.exit(app.exec_())
