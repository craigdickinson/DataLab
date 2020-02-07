"""Acceleration and angular rate conversion to displacement and angle setup tab and edit dialog."""

__author__ = "Craig Dickinson"

import logging
import sys

from PyQt5 import QtWidgets

from core.control import Control
from core.logger_properties import LoggerProperties


class TimeSeriesIntegrationSetupTab(QtWidgets.QWidget):
    """Tab widget to present time series integration setup."""

    def __init__(self, parent=None):
        super(TimeSeriesIntegrationSetupTab, self).__init__(parent)

        self.parent = parent
        self.control = Control()
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
        self.accXCol = QtWidgets.QLabel("-")
        self.accYCol = QtWidgets.QLabel("-")
        self.accZCol = QtWidgets.QLabel("-")
        self.angRateXCol = QtWidgets.QLabel("-")
        self.angRateYCol = QtWidgets.QLabel("-")
        self.applyGCorr = QtWidgets.QLabel("-")
        self.integrationFolder = QtWidgets.QLabel("-")

        # Labels
        self.lblAccX = QtWidgets.QLabel("Acceleration X:")
        self.lblAccY = QtWidgets.QLabel("Acceleration Y:")
        self.lblAccZ = QtWidgets.QLabel("Acceleration Z:")
        self.lblAngRateX = QtWidgets.QLabel("Angular rate X:")
        self.lblAngRateY = QtWidgets.QLabel("Angular rate Y:")
        self.lblGCorr = QtWidgets.QLabel("Apply gravity correction:")
        self.lblIntegrationFolder = QtWidgets.QLabel("Output folder:")

        # CONTAINERS
        self.setupGroup = QtWidgets.QGroupBox("Acceleration and Angular Rate Columns")
        self.setupForm = QtWidgets.QFormLayout(self.setupGroup)
        self.setupForm.addRow(self.lblAccX, self.accXCol)
        self.setupForm.addRow(self.lblAccY, self.accYCol)
        self.setupForm.addRow(self.lblAccZ, self.accZCol)
        self.setupForm.addRow(self.lblAngRateX, self.angRateXCol)
        self.setupForm.addRow(self.lblAngRateY, self.angRateYCol)
        self.setupForm.addRow(self.lblGCorr, self.applyGCorr)
        self.setupForm.addRow(self.lblIntegrationFolder, self.integrationFolder)

        # LAYOUT
        self.hboxControls = QtWidgets.QHBoxLayout()
        self.hboxControls.addWidget(self.editButton)
        self.hboxControls.addWidget(self.processChkBox)
        self.hboxControls.addStretch()

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addLayout(self.hboxControls)
        self.vbox.addWidget(self.setupGroup)
        self.vbox.addStretch()

        self.hbox = QtWidgets.QHBoxLayout(self)
        self.hbox.addLayout(self.vbox)
        self.hbox.addStretch()

    def _connect_signals(self):
        self.editButton.clicked.connect(self.on_edit_clicked)
        self.processChkBox.toggled.connect(self.on_process_check_box_toggled)

    def on_edit_clicked(self):
        """Open logger screening edit dialog."""

        if self.parent is None:
            return

        if self.parent.loggerList.count() == 0:
            msg = f"No loggers exist to edit. Add a logger first."
            return QtWidgets.QMessageBox.information(
                self, "Edit Time Series Integration Settings", msg
            )

        # Retrieve selected logger object
        logger_idx = self.parent.loggerList.currentRow()

        # Edit stats dialog class
        editIntegrationSettings = EditIntegrationSetupDialog(self, self.control, logger_idx)
        editIntegrationSettings.show()

    def on_process_check_box_toggled(self):
        """Set include in processing state in logger object."""

        if self.parent.loggerList.count() > 0:
            self.logger.process_integration = self.processChkBox.isChecked()

    def set_analysis_dashboard(self, logger):
        """Set dashboard with logger stats and spectral settings from logger object."""

        self.logger = logger

        # Process check state
        self.processChkBox.setChecked(logger.process_integration)

        # Columns
        self.accXCol.setText(logger.acc_x_col)
        self.accYCol.setText(logger.acc_y_col)
        self.accZCol.setText(logger.acc_z_col)
        self.angRateXCol.setText(logger.ang_rate_x_col)
        self.angRateYCol.setText(logger.ang_rate_y_col)
        self.integrationFolder.setText(self.control.integration_output_folder)
        if logger.apply_gcorr:
            self.applyGCorr.setText("Yes")
        else:
            self.applyGCorr.setText("No")

    def clear_dashboard(self):
        """Initialise all values in stats and spectral analysis dashboard."""

        self.accXCol.setText("-")
        self.accYCol.setText("-")
        self.accZCol.setText("-")
        self.angRateXCol.setText("-")
        self.angRateYCol.setText("-")
        self.applyGCorr.setText("Yes")
        self.integrationFolder.setText("Displacements and Angles")


class EditIntegrationSetupDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, control=Control(), logger_idx=0):
        super(EditIntegrationSetupDialog, self).__init__(parent)

        self.parent = parent

        # Store control settings and selected logger properties objects
        self.control = control
        self.logger_idx = logger_idx

        # Combobox lists
        # Units
        self.disp_units = ["-", "mm to m"]
        self.angle_units = ["-", "rad to deg"]

        try:
            self.logger = control.loggers[logger_idx]
        except IndexError:
            self.logger = LoggerProperties()

        self._init_ui()
        self._connect_signals()
        self._set_dialog_data(self.logger)

        # Populate copy loggers combo box
        self._set_copy_logger_combo()

    def _init_ui(self):
        self.setWindowTitle("Edit Time Series Integration Settings")
        # self.setMinimumWidth(600)

        # WIDGETS
        self.copyLogger = QtWidgets.QComboBox()
        self.copyLogger.setMinimumWidth(80)
        self.copyLogger.addItem("-")
        self.copyLoggerButton = QtWidgets.QPushButton("&Copy")

        # Check boxes and output folder
        self.applyGCorr = QtWidgets.QCheckBox("Apply gravity correction")
        self.outputRMSSummary = QtWidgets.QCheckBox("Output logger RMS summary")
        self.integrationFolder = QtWidgets.QLineEdit()
        self.integrationFolder.setFixedWidth(200)

        # Column selectors
        self.accXCombo = QtWidgets.QComboBox()
        self.accXCombo.setFixedWidth(200)
        self.accYCombo = QtWidgets.QComboBox()
        self.accYCombo.setFixedWidth(200)
        self.accZCombo = QtWidgets.QComboBox()
        self.accZCombo.setFixedWidth(200)
        self.angRateXCombo = QtWidgets.QComboBox()
        self.angRateXCombo.setFixedWidth(200)
        self.angRateYCombo = QtWidgets.QComboBox()
        self.angRateYCombo.setFixedWidth(200)

        # Unit conversions
        self.accXUnitConvCombo = QtWidgets.QComboBox()
        self.accXUnitConvCombo.setFixedWidth(80)
        self.accXUnitConvCombo.addItems(self.disp_units)
        self.accYUnitConvCombo = QtWidgets.QComboBox()
        self.accYUnitConvCombo.setFixedWidth(80)
        self.accYUnitConvCombo.addItems(self.disp_units)
        self.accZUnitConvCombo = QtWidgets.QComboBox()
        self.accZUnitConvCombo.setFixedWidth(80)
        self.accZUnitConvCombo.addItems(self.disp_units)
        self.angRateXUnitConvCombo = QtWidgets.QComboBox()
        self.angRateXUnitConvCombo.setFixedWidth(80)
        self.angRateXUnitConvCombo.addItems(self.angle_units)
        self.angRateYUnitConvCombo = QtWidgets.QComboBox()
        self.angRateYUnitConvCombo.setFixedWidth(80)
        self.angRateYUnitConvCombo.addItems(self.angle_units)

        # Low cut-off frequencies
        self.accXLowCutoff = QtWidgets.QLineEdit("0.25")
        self.accXLowCutoff.setFixedWidth(40)
        self.accYLowCutoff = QtWidgets.QLineEdit("0.25")
        self.accYLowCutoff.setFixedWidth(40)
        self.accZLowCutoff = QtWidgets.QLineEdit("0.25")
        self.accZLowCutoff.setFixedWidth(40)
        self.angRateXLowCutoff = QtWidgets.QLineEdit("0.25")
        self.angRateXLowCutoff.setFixedWidth(40)
        self.angRateYLowCutoff = QtWidgets.QLineEdit("0.25")
        self.angRateYLowCutoff.setFixedWidth(40)

        # High cut-off frequencies
        self.accXHighCutoff = QtWidgets.QLineEdit("2.0")
        self.accXHighCutoff.setFixedWidth(40)
        self.accYHighCutoff = QtWidgets.QLineEdit("2.0")
        self.accYHighCutoff.setFixedWidth(40)
        self.accZHighCutoff = QtWidgets.QLineEdit("2.0")
        self.accZHighCutoff.setFixedWidth(40)
        self.angRateXHighCutoff = QtWidgets.QLineEdit("2.0")
        self.angRateXHighCutoff.setFixedWidth(40)
        self.angRateYHighCutoff = QtWidgets.QLineEdit("2.0")
        self.angRateYHighCutoff.setFixedWidth(40)

        # Labels
        lblCopy = QtWidgets.QLabel("Logger settings to copy (optional):")
        lblAccX = QtWidgets.QLabel("Acceleration X:")
        lblAccY = QtWidgets.QLabel("Acceleration Y:")
        lblAccZ = QtWidgets.QLabel("Acceleration Z:")
        lblAngRateX = QtWidgets.QLabel("Angular rate X:")
        lblAngRateY = QtWidgets.QLabel("Angular rate Y:")
        lblIntegrationFolder = QtWidgets.QLabel("Output folder:")

        # Header labels
        lblChannel = QtWidgets.QLabel("Column")
        lblUnitConv = QtWidgets.QLabel("Units Conversion")
        lblCutoffFreqs = QtWidgets.QLabel("Cut-off Freqs (Hz)")
        lblLowCutoff = QtWidgets.QLabel("Low")
        lblHighCutoff = QtWidgets.QLabel("High")

        # CONTAINERS
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # Copy logger group and output folder container
        self.hboxCopy = QtWidgets.QHBoxLayout()
        self.hboxCopy.addWidget(lblCopy)
        self.hboxCopy.addWidget(self.copyLogger)
        self.hboxCopy.addWidget(self.copyLoggerButton)
        self.hboxCopy.addStretch()

        # Columns to process settings group
        self.setupGroup = QtWidgets.QGroupBox("Channel Settings to Convert to Displacements/Angles")
        self.setupGroup.setSizePolicy(policy)
        self.grid = QtWidgets.QGridLayout(self.setupGroup)

        # Header row
        self.grid.addWidget(self.applyGCorr, 0, 0, 1, 2)
        self.grid.addWidget(lblCutoffFreqs, 0, 3, 1, 2)
        self.grid.addWidget(lblChannel, 1, 1)
        self.grid.addWidget(lblUnitConv, 1, 2)
        self.grid.addWidget(lblLowCutoff, 1, 3)
        self.grid.addWidget(lblHighCutoff, 1, 4)

        # Col 1 - labels
        self.grid.addWidget(lblAccX, 2, 0)
        self.grid.addWidget(lblAccY, 3, 0)
        self.grid.addWidget(lblAccZ, 4, 0)
        self.grid.addWidget(lblAngRateX, 5, 0)
        self.grid.addWidget(lblAngRateY, 6, 0)

        # Col 2 - columns
        self.grid.addWidget(self.accXCombo, 2, 1)
        self.grid.addWidget(self.accYCombo, 3, 1)
        self.grid.addWidget(self.accZCombo, 4, 1)
        self.grid.addWidget(self.angRateXCombo, 5, 1)
        self.grid.addWidget(self.angRateYCombo, 6, 1)

        # Col 3 - unit conversions
        self.grid.addWidget(self.accXUnitConvCombo, 2, 2)
        self.grid.addWidget(self.accYUnitConvCombo, 3, 2)
        self.grid.addWidget(self.accZUnitConvCombo, 4, 2)
        self.grid.addWidget(self.angRateXUnitConvCombo, 5, 2)
        self.grid.addWidget(self.angRateYUnitConvCombo, 6, 2)

        # Col 4 - low cut-offs
        self.grid.addWidget(self.accXLowCutoff, 2, 3)
        self.grid.addWidget(self.accYLowCutoff, 3, 3)
        self.grid.addWidget(self.accZLowCutoff, 4, 3)
        self.grid.addWidget(self.angRateXLowCutoff, 5, 3)
        self.grid.addWidget(self.angRateYLowCutoff, 6, 3)

        # Col 5 - high cut-offs
        self.grid.addWidget(self.accXHighCutoff, 2, 4)
        self.grid.addWidget(self.accYHighCutoff, 3, 4)
        self.grid.addWidget(self.accZHighCutoff, 4, 4)
        self.grid.addWidget(self.angRateXHighCutoff, 5, 4)
        self.grid.addWidget(self.angRateYHighCutoff, 6, 4)

        self.setupForm = QtWidgets.QFormLayout()
        self.setupForm.addRow(self.outputRMSSummary)
        self.setupForm.addRow(lblIntegrationFolder, self.integrationFolder)

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        # LAYOUT
        # Horizontal groups
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addLayout(self.hboxCopy)
        self.layout.addWidget(self.setupGroup)
        self.layout.addLayout(self.setupForm)
        self.layout.addStretch()
        self.layout.addWidget(self.buttonBox)
        self.setFixedSize(self.sizeHint())

    def _connect_signals(self):
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.copyLoggerButton.clicked.connect(self.on_copy_logger_clicked)

    def _set_dialog_data(self, logger):
        """Set dialog data with logger stats from control object."""

        if not self.parent:
            return

        # Set gravity correction and output folder
        self.applyGCorr.setChecked(logger.apply_gcorr)
        self.outputRMSSummary.setChecked(logger.output_rms_summary)
        self.integrationFolder.setText(self.control.integration_output_folder)

        # Ned to clear combo boxes if copying settings from another logger
        self.accXCombo.clear()
        self.accYCombo.clear()
        self.accZCombo.clear()
        self.angRateXCombo.clear()
        self.angRateYCombo.clear()

        # Get combo columns
        columns = ["Not used"] + logger.all_channel_names

        # Populate channel section combo boxes
        self.accXCombo.addItems(columns)
        self.accYCombo.addItems(columns)
        self.accZCombo.addItems(columns)
        self.angRateXCombo.addItems(columns)
        self.angRateYCombo.addItems(columns)

        # Set channels to convert
        self.accXCombo.setCurrentText(logger.acc_x_col)
        self.accYCombo.setCurrentText(logger.acc_y_col)
        self.accZCombo.setCurrentText(logger.acc_z_col)
        self.angRateXCombo.setCurrentText(logger.ang_rate_x_col)
        self.angRateYCombo.setCurrentText(logger.ang_rate_y_col)

        # Set units conversion
        self.accXUnitConvCombo.setCurrentText(logger.acc_x_units_conv)
        self.accYUnitConvCombo.setCurrentText(logger.acc_y_units_conv)
        self.accZUnitConvCombo.setCurrentText(logger.acc_z_units_conv)
        self.angRateXUnitConvCombo.setCurrentText(logger.ang_rate_x_units_conv)
        self.angRateYUnitConvCombo.setCurrentText(logger.ang_rate_y_units_conv)

        # Set low cut-off frequencies
        self.accXLowCutoff.setText(freq_val_to_str(logger.acc_x_low_cutoff))
        self.accYLowCutoff.setText(freq_val_to_str(logger.acc_y_low_cutoff))
        self.accZLowCutoff.setText(freq_val_to_str(logger.acc_z_low_cutoff))
        self.angRateXLowCutoff.setText(freq_val_to_str(logger.ang_rate_x_low_cutoff))
        self.angRateYLowCutoff.setText(freq_val_to_str(logger.ang_rate_y_low_cutoff))

        # Set high cut-off frequencies
        self.accXHighCutoff.setText(freq_val_to_str(logger.acc_x_high_cutoff))
        self.accYHighCutoff.setText(freq_val_to_str(logger.acc_y_high_cutoff))
        self.accZHighCutoff.setText(freq_val_to_str(logger.acc_z_high_cutoff))
        self.angRateXHighCutoff.setText(freq_val_to_str(logger.ang_rate_x_high_cutoff))
        self.angRateYHighCutoff.setText(freq_val_to_str(logger.ang_rate_y_high_cutoff))

    def _set_copy_logger_combo(self):
        """Set the copy screening settings combo box with list of available loggers, excluding the current one."""

        # Get list of available loggers to copy
        loggers_to_copy = [i for i in self.control.logger_ids if i != self.logger.logger_id]
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

        # Map integration settings from reference logger to active logger and update dialog properties
        self.control.copy_logger_integration_settings(ref_logger_id, temp_logger)

        # Set dialog with temp settings so they can confirmed by the user
        self._set_dialog_data(temp_logger)

    def on_ok_clicked(self):
        """Assign logger stats settings to the control object and update the dashboard."""

        if self.parent is None:
            return

        self.logger = self._set_control_data()
        self.parent.set_analysis_dashboard(self.logger)

    def _set_control_data(self):
        """Assign values to the control object."""

        # Retrieve control logger to map confirmed settings to
        logger = self.control.loggers[self.logger_idx]
        logger.apply_gcorr = self.applyGCorr.isChecked()
        logger.output_rms_summary = self.outputRMSSummary.isChecked()
        self.control.integration_output_folder = self.integrationFolder.text()

        # Channels to convert
        logger.acc_x_col = self.accXCombo.currentText()
        logger.acc_y_col = self.accYCombo.currentText()
        logger.acc_z_col = self.accZCombo.currentText()
        logger.ang_rate_x_col = self.angRateXCombo.currentText()
        logger.ang_rate_y_col = self.angRateYCombo.currentText()

        # Units conversion
        logger.acc_x_units_conv = self.accXUnitConvCombo.currentText()
        logger.acc_y_units_conv = self.accYUnitConvCombo.currentText()
        logger.acc_z_units_conv = self.accZUnitConvCombo.currentText()
        logger.ang_rate_x_units_conv = self.angRateXUnitConvCombo.currentText()
        logger.ang_rate_y_units_conv = self.angRateYUnitConvCombo.currentText()

        # Low cut-off frequencies
        logger.acc_x_low_cutoff = freq_str_to_val(self.accXLowCutoff.text())
        logger.acc_y_low_cutoff = freq_str_to_val(self.accYLowCutoff.text())
        logger.acc_z_low_cutoff = freq_str_to_val(self.accZLowCutoff.text())
        logger.ang_rate_x_low_cutoff = freq_str_to_val(self.angRateXLowCutoff.text())
        logger.ang_rate_y_low_cutoff = freq_str_to_val(self.angRateYLowCutoff.text())

        # High cut-off frequencies
        logger.acc_x_high_cutoff = freq_str_to_val(self.accXHighCutoff.text())
        logger.acc_y_high_cutoff = freq_str_to_val(self.accYHighCutoff.text())
        logger.acc_z_high_cutoff = freq_str_to_val(self.accZHighCutoff.text())
        logger.ang_rate_x_high_cutoff = freq_str_to_val(self.angRateXHighCutoff.text())
        logger.ang_rate_y_high_cutoff = freq_str_to_val(self.angRateYHighCutoff.text())

        return logger


def freq_val_to_str(freq):
    """Convert logger frequency value to string to set to widget."""

    if freq is None:
        str_val = "None"
    else:
        str_val = f"{freq:.2f}"

    return str_val


def freq_str_to_val(str_val):
    """Convert widget string input to frequency value."""

    try:
        freq = float(str_val)
        if freq == 0:
            freq = None
    except ValueError:
        freq = None

    return freq


if __name__ == "__main__":
    # For testing widget layout
    app = QtWidgets.QApplication(sys.argv)
    # win = TimeSeriesIntegrationSetupTab()
    win = EditIntegrationSetupDialog()
    win.show()
    app.exit(app.exec_())
