"""Rainflow counting setup tab and edit dialog."""

__author__ = "Craig Dickinson"

import logging
import sys

from PyQt5 import QtCore, QtGui, QtWidgets
from dateutil.parser import parse

from app.core.control import Control
from app.core.logger_properties import LoggerProperties


class RainflowHistogramSetupTab(QtWidgets.QWidget):
    """Tab to display rainflow histogram settings."""

    def __init__(self, parent=None, control=Control()):
        super(RainflowHistogramSetupTab, self).__init__(parent)

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
        self.processChkBox = QtWidgets.QCheckBox("Include in processing")
        self.processChkBox.setChecked(True)
        self.columns = QtWidgets.QLabel("-")
        self.unitConvs = QtWidgets.QLabel("-")
        self.channelNames = QtWidgets.QLabel("-")
        self.channelUnits = QtWidgets.QLabel("-")
        self.processStart = QtWidgets.QLabel("-")
        self.processEnd = QtWidgets.QLabel("-")

        # Process range labels
        self.lblProcessStart = QtWidgets.QLabel("Start timestamp:")
        self.lblProcessEnd = QtWidgets.QLabel("End timestamp:")

        # CONTAINERS
        # Edit button and process check box
        self.hbox = QtWidgets.QHBoxLayout()
        self.hbox.addWidget(self.editButton)
        self.hbox.addWidget(self.processChkBox)
        self.hbox.addStretch()

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

        # LAYOUT
        # Combine all layouts
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addLayout(self.hbox)
        # self.vbox.addWidget(self.editButton, stretch=0, alignment=QtCore.Qt.AlignLeft)
        self.vbox.addWidget(self.colsGroup)
        self.vbox.addWidget(self.processRangeGroup)
        self.vbox.addStretch()

        self.hbox = QtWidgets.QHBoxLayout(self)
        self.hbox.addLayout(self.vbox)
        self.hbox.addStretch()

    def _connect_signals(self):
        self.editButton.clicked.connect(self.on_edit_clicked)
        self.processChkBox.toggled.connect(self.on_process_check_box_toggled)

    def on_edit_clicked(self):
        """Open logger screening edit dialog."""

        if self.parent.loggersList.count() == 0:
            msg = f"No loggers exist to edit. Add a logger first."
            return QtWidgets.QMessageBox.information(
                self, "Edit Logger Statistics and Spectral Analysis Settings", msg
            )

        # Retrieve selected logger object
        logger_idx = self.parent.loggersList.currentRow()

        # Edit stats dialog class
        editStatsSettings = EditRainflowSetupDialog(self, self.control, logger_idx)
        editStatsSettings.show()

    def on_process_check_box_toggled(self):
        """Set include in processing state in logger object."""

        if self.parent.loggersList.count() > 0:
            self.logger.process_rainflow = self.processStatsChkBox.isChecked()

    def set_analysis_dashboard(self, logger):
        """Set dashboard with logger stats and spectral settings from logger object."""

        self.logger = logger

        # Process check state
        self.processChkBox.setChecked(logger.process_rainflow)

        # Columns
        cols_str = " ".join([str(i) for i in logger.rf_cols_to_process])
        self.columns.setText(cols_str)

        # Unit conversion factors
        # unit_conv_factors_str = " ".join([str(i) for i in logger.unit_conv_factors])
        # self.unitConvs.setText(unit_conv_factors_str)

        # Channel names
        # channel_items_str = ", ".join([i for i in logger.user_channel_names])
        # self.channelNames.setText(channel_items_str)

        # Channel units
        # units_items_str = " ".join([i for i in logger.user_channel_units])
        # self.channelUnits.setText(units_items_str)

        # Set the process start/end labels in the Screening dashboard that pertain to the first logger (if exists)
        self.set_process_date_labels(logger.file_timestamp_embedded)

        # Set start/end timestamp/index
        process_start = self._set_process_start(logger)
        self.processStart.setText(process_start)
        process_end = self._set_process_end(logger)
        self.processEnd.setText(process_end)

    @staticmethod
    def _set_process_start(logger):
        # Start timestamp/index
        if logger.rf_process_start is None:
            process_start = "First"
        else:
            if logger.file_timestamp_embedded is True:
                process_start = logger.rf_process_start.strftime("%Y-%m-%d %H:%M")
            else:
                process_start = str(logger.rf_process_start)

        return process_start

    @staticmethod
    def _set_process_end(logger):
        # End timestamp/index
        if logger.rf_process_end is None:
            process_end = "Last"
        else:
            if logger.file_timestamp_embedded is True:
                process_end = logger.rf_process_end.strftime("%Y-%m-%d %H:%M")
            else:
                process_end = str(logger.rf_process_end)

        return process_end

    def clear_dashboard(self):
        """Initialise all values in stats and spectral analysis dashboard."""

        self.columns.setText("-")
        self.unitConvs.setText("-")
        self.channelNames.setText("-")
        self.channelUnits.setText("-")
        self.processStart.setText("-")
        self.processEnd.setText("-")

    def set_process_date_labels(self, file_timestamp_embedded):
        """Set process start and end labels to refer to dates or file indexes depending on setup of current logger."""

        if file_timestamp_embedded is True:
            self.lblProcessStart.setText("Start timestamp:")
            self.lblProcessEnd.setText("End timestamp:")
        else:
            self.lblProcessStart.setText("Start file number:")
            self.lblProcessEnd.setText("End file number:")


class EditRainflowSetupDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, control=Control(), logger_idx=0):
        super(EditRainflowSetupDialog, self).__init__(parent)

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

    def _init_ui(self):
        self.setWindowTitle("Edit Logger Rainflow Counting Settings")
        self.setMinimumWidth(500)

        # Define input validators
        int_validator = QtGui.QIntValidator()
        int_validator.setBottom(1)
        dbl_validator = QtGui.QDoubleValidator()

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
        # self.unitConvs = QtWidgets.QLineEdit()
        # self.unitConvs.setToolTip(
        #     "SPACE-separated column unit conversion factors.\n"
        #     "E.g. 0.001 0.001 57.29578 57.29578."
        # )
        # self.channelNames = QtWidgets.QLineEdit()
        # self.channelNames.setToolTip(
        #     "COMMA-separated custom channel names.\n"
        #     "E.g. AccelX AccelY AngRateX AngRateY."
        # )
        # self.channelUnits = QtWidgets.QLineEdit()
        # self.channelUnits.setToolTip(
        #     "SPACE-separated custom channel units.\n" "E.g. m/s^2 m/s^2 deg/s deg/s."
        # )
        self.processStart = QtWidgets.QLineEdit()
        self.processStart.setFixedWidth(100)
        self.processEnd = QtWidgets.QLineEdit()
        self.processEnd.setFixedWidth(100)

        # Labels
        self.lblCopy = QtWidgets.QLabel("Logger to copy:")
        self.lblColumns = QtWidgets.QLabel("Column numbers to process:")
        # self.lblUnitConvs = QtWidgets.QLabel("Unit conversion factors (optional):")
        # self.lblChannelNames = QtWidgets.QLabel("Channel names override (optional):")
        # self.lblChannelUnits = QtWidgets.QLabel("Channel units override (optional):")

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
        # Copy logger group
        self.copyGroup = QtWidgets.QGroupBox(
            "Optional: Copy Settings from Another Logger"
        )
        self.hboxCopy = QtWidgets.QHBoxLayout(self.copyGroup)
        self.hboxCopy.addWidget(self.lblCopy)
        self.hboxCopy.addWidget(self.copyLogger)
        self.hboxCopy.addWidget(self.copyLoggerButton)
        self.hboxCopy.addStretch()

        # Columns to process settings group
        self.colsGroup = QtWidgets.QGroupBox("Columns to Process Settings")
        self.colsForm = QtWidgets.QFormLayout(self.colsGroup)
        self.colsForm.addRow(self.lblColumns, self.columns)
        # self.colsForm.addRow(self.lblUnitConvs, self.unitConvs)
        # self.colsForm.addRow(self.lblChannelNames, self.channelNames)
        # self.colsForm.addRow(self.lblChannelUnits, self.channelUnits)

        # Processing range group
        self.processRangeGroup = QtWidgets.QGroupBox("Processing Range")
        self.processRangeForm = QtWidgets.QFormLayout(self.processRangeGroup)
        self.processRangeForm.addRow(self.lblProcessStart, self.processStart)
        self.processRangeForm.addRow(self.lblProcessEnd, self.processEnd)

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        # LAYOUT
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.copyGroup)
        self.layout.addWidget(self.colsGroup)
        self.layout.addWidget(self.processRangeGroup)
        self.layout.addWidget(self.buttonBox, stretch=0, alignment=QtCore.Qt.AlignRight)

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
        cols_str = " ".join([str(i) for i in logger.rf_cols_to_process])
        if cols_str == "":
            cols_str = "All"
        self.columns.setText(cols_str)

        # Unit conversion factors
        # unit_conv_factors_str = " ".join([str(i) for i in logger.unit_conv_factors])
        # self.unitConvs.setText(unit_conv_factors_str)

        # Channel names
        # channel_items_str = ", ".join([i for i in logger.user_channel_names])
        # self.channelNames.setText(channel_items_str)

        # Channel units
        # units_items_str = " ".join([i for i in logger.user_channel_units])
        # self.channelUnits.setText(units_items_str)

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

    def _set_copy_logger_combo(self):
        """Set the copy screening settings combo box with list of available loggers, excluding the current one."""

        # Get list of available loggers to copy
        loggers_to_copy = [
            i for i in self.control.logger_ids if i != self.logger.logger_id
        ]
        self.copyLogger.addItems(loggers_to_copy)

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
            logger.rf_cols_to_process = list(range(2, n + 1))
        else:
            # Convert strings to lists
            try:
                logger.rf_cols_to_process = list(map(int, self.columns.text().split()))
            except ValueError:
                msg = (
                    "Only integer column numbers are allowed.\n"
                    "Separate each number with a space, e.g. 2 3 4 5."
                )
                QtWidgets.QMessageBox.information(
                    self, "Invalid Requested Columns Input", msg
                )

        # try:
        #     logger.unit_conv_factors = list(map(float, self.unitConvs.text().split()))
        # except ValueError:
        #     msg = (
        #         "Unit conversion factors must be numeric.\n"
        #         "Separate each input with a space, e.g. 0.001 0.001 57.29578 57.29578."
        #     )
        #     QtWidgets.QMessageBox.information(
        #         self, "Invalid Unit Conversion Factors Input", msg
        #     )
        #
        # # Extract channel names to list
        # # Note, because splitting by comma, if input is empty, [""] is returned but want [] so check if populated
        # if self.channelNames.text():
        #     channel_names = [c.strip() for c in self.channelNames.text().split(",")]
        # else:
        #     channel_names = []
        # logger.user_channel_names = channel_names
        # logger.user_channel_units = self.channelUnits.text().split()

        # Process start and end dates or file indexes
        process_start = self.processStart.text()
        process_end = self.processEnd.text()

        # Process selection made by timestamps
        if logger.file_timestamp_embedded is True:
            if process_start == "" or process_start.lower() == "first":
                logger.rf_process_start = self.get_timestamp_in_filename(
                    logger, file_idx=0
                )
            else:
                try:
                    logger.rf_process_start = parse(process_start, yearfirst=True)
                except ValueError:
                    msg = "Process start datetime format not recognised; timestamp unchanged."
                    QtWidgets.QMessageBox.information(self, "Process Start Input", msg)

            if process_end == "" or process_end.lower() == "last":
                logger.rf_process_end = self.get_timestamp_in_filename(
                    logger, file_idx=-1
                )
            else:
                try:
                    logger.rf_process_end = parse(process_end, yearfirst=True)
                except ValueError:
                    msg = "Process end datetime format not recognised; timestamp unchanged."
                    QtWidgets.QMessageBox.information(self, "Process End Input", msg)
        # Process selection made by file number (load case)
        else:
            if process_start == "" or process_start.lower() == "first":
                process_start = 1

            try:
                logger.rf_process_start = int(process_start)
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
                logger.rf_process_end = None
                msg = "Process end file number could not be set; no files found."
                QtWidgets.QMessageBox.information(self, "Process End Input", msg)
            else:
                try:
                    logger.rf_process_end = int(process_end)
                except ValueError:
                    msg = "Process end file number must be an integer."
                    QtWidgets.QMessageBox.information(self, "Process End Input", msg)

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
    win = RainflowHistogramSetupTab()
    win.show()
    app.exit(app.exec_())
