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
        self.angRateZCol = QtWidgets.QLabel("-")
        self.applyGCorr = QtWidgets.QLabel("-")
        self.integrationFolder = QtWidgets.QLabel("-")

        # Labels
        self.lblAccX = QtWidgets.QLabel("Acceleration X:")
        self.lblAccY = QtWidgets.QLabel("Acceleration Y:")
        self.lblAccZ = QtWidgets.QLabel("Acceleration Z:")
        self.lblAngRateX = QtWidgets.QLabel("Angular rate X:")
        self.lblAngRateY = QtWidgets.QLabel("Angular rate Y:")
        self.lblAngRateZ = QtWidgets.QLabel("Angular rate Z:")
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
        self.setupForm.addRow(self.lblAngRateZ, self.angRateZCol)
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

        if not self.parent:
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
        self.angRateZCol.setText(logger.ang_rate_z_col)
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
        self.angRateZCol.setText("-")
        self.applyGCorr.setText("Yes")
        self.integrationFolder.setText("Displacements and Angles")


class EditIntegrationSetupDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, control=Control(), logger_idx=0):
        super(EditIntegrationSetupDialog, self).__init__(parent)

        self.parent = parent

        # Store control settings and selected logger properties objects
        self.control = control
        self.logger_idx = logger_idx

        try:
            self.logger = control.loggers[logger_idx]
        except:
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
        self.copyLoggerButton = QtWidgets.QPushButton("&Copy Settings")

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
        self.angRateZCombo = QtWidgets.QComboBox()
        self.angRateZCombo.setFixedWidth(200)

        # Unit conversions
        self.accXUnitConv = QtWidgets.QComboBox()
        self.accYUnitConv = QtWidgets.QComboBox()
        self.accZUnitConv = QtWidgets.QComboBox()
        self.angRateXUnitConv = QtWidgets.QComboBox()
        self.angRateYUnitConv = QtWidgets.QComboBox()
        self.angRateZUnitConv = QtWidgets.QComboBox()

        # Low cut-off frequencies
        self.accXLowCutoff = QtWidgets.QLineEdit()
        self.accXLowCutoff.setFixedWidth(40)
        self.accYLowCutoff = QtWidgets.QLineEdit()
        self.accYLowCutoff.setFixedWidth(40)
        self.accZLowCutoff = QtWidgets.QLineEdit()
        self.accZLowCutoff.setFixedWidth(40)
        self.angRateXLowCutoff = QtWidgets.QLineEdit()
        self.angRateXLowCutoff.setFixedWidth(40)
        self.angRateYLowCutoff = QtWidgets.QLineEdit()
        self.angRateYLowCutoff.setFixedWidth(40)
        self.angRateZLowCutoff = QtWidgets.QLineEdit()
        self.angRateZLowCutoff.setFixedWidth(40)

        # High cut-off frequencies
        self.accXHighCutoff = QtWidgets.QLineEdit()
        self.accXHighCutoff.setFixedWidth(40)
        self.accYHighCutoff = QtWidgets.QLineEdit()
        self.accYHighCutoff.setFixedWidth(40)
        self.accZHighCutoff = QtWidgets.QLineEdit()
        self.accZHighCutoff.setFixedWidth(40)
        self.angRateXHighCutoff = QtWidgets.QLineEdit()
        self.angRateXHighCutoff.setFixedWidth(40)
        self.angRateYHighCutoff = QtWidgets.QLineEdit()
        self.angRateYHighCutoff.setFixedWidth(40)
        self.angRateZHighCutoff = QtWidgets.QLineEdit()
        self.angRateZHighCutoff.setFixedWidth(40)

        # General inputs
        self.applyGCorr = QtWidgets.QCheckBox("Apply gravity correction")
        self.integrationFolder = QtWidgets.QLineEdit()
        self.integrationFolder.setFixedWidth(200)

        # Labels
        lblCopy = QtWidgets.QLabel("Logger to copy:")
        lblAccX = QtWidgets.QLabel("Acceleration X:")
        lblAccY = QtWidgets.QLabel("Acceleration Y:")
        lblAccZ = QtWidgets.QLabel("Acceleration Z:")
        lblAngRateX = QtWidgets.QLabel("Angular rate X:")
        lblAngRateY = QtWidgets.QLabel("Angular rate Y:")
        lblAngRateZ = QtWidgets.QLabel("Angular rate Z:")
        lblIntegrationFolder = QtWidgets.QLabel("Output folder:")

        # Header labels
        lblChannel = QtWidgets.QLabel("Column")
        lblUnitConv = QtWidgets.QLabel("Unit Conversion")
        lblCutoffFreqs = QtWidgets.QLabel("Cut-off Freqs (Hz)")
        lblLowCutoff = QtWidgets.QLabel("Low")
        lblHighCutoff = QtWidgets.QLabel("High")

        # CONTAINERS
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # Copy logger group
        self.copyGroup = QtWidgets.QGroupBox("Optional: Copy Settings from Another Logger")
        self.copyGroup.setSizePolicy(policy)
        self.hboxCopy = QtWidgets.QHBoxLayout(self.copyGroup)
        self.hboxCopy.addWidget(lblCopy)
        self.hboxCopy.addWidget(self.copyLogger)
        self.hboxCopy.addWidget(self.copyLoggerButton)
        self.hboxCopy.addStretch()

        # Columns to process settings group
        self.setupGroup = QtWidgets.QGroupBox("Channel Settings to Convert to Displacements/Angles")
        self.setupGroup.setSizePolicy(policy)

        self.grid = QtWidgets.QGridLayout()

        # Header row
        self.grid.addWidget(self.applyGCorr)
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
        self.grid.addWidget(lblAngRateZ, 7, 0)

        # Col 2 - columns
        self.grid.addWidget(self.accXCombo, 2, 1)
        self.grid.addWidget(self.accYCombo, 3, 1)
        self.grid.addWidget(self.accZCombo, 4, 1)
        self.grid.addWidget(self.angRateXCombo, 5, 1)
        self.grid.addWidget(self.angRateYCombo, 6, 1)
        self.grid.addWidget(self.angRateZCombo, 7, 1)

        # Col 3 - unit conversions
        self.grid.addWidget(self.accXUnitConv, 2, 2)
        self.grid.addWidget(self.accYUnitConv, 3, 2)
        self.grid.addWidget(self.accZUnitConv, 4, 2)
        self.grid.addWidget(self.angRateXUnitConv, 5, 2)
        self.grid.addWidget(self.angRateYUnitConv, 6, 2)
        self.grid.addWidget(self.angRateZUnitConv, 7, 2)

        # Col 4 - low cut-offs
        self.grid.addWidget(self.accXLowCutoff, 2, 3)
        self.grid.addWidget(self.accYLowCutoff, 3, 3)
        self.grid.addWidget(self.accZLowCutoff, 4, 3)
        self.grid.addWidget(self.angRateXLowCutoff, 5, 3)
        self.grid.addWidget(self.angRateYLowCutoff, 6, 3)
        self.grid.addWidget(self.angRateZLowCutoff, 7, 3)

        # Col 5 - high cut-offs
        self.grid.addWidget(self.accXHighCutoff, 2, 4)
        self.grid.addWidget(self.accYHighCutoff, 3, 4)
        self.grid.addWidget(self.accZHighCutoff, 4, 4)
        self.grid.addWidget(self.angRateXHighCutoff, 5, 4)
        self.grid.addWidget(self.angRateYHighCutoff, 6, 4)
        self.grid.addWidget(self.angRateZHighCutoff, 7, 4)

        self.setupForm = QtWidgets.QFormLayout()
        # self.setupForm.addRow(QtWidgets.QLabel(""), self.applyGCorr)
        self.setupForm.addRow(lblIntegrationFolder, self.integrationFolder)

        self.vbox = QtWidgets.QVBoxLayout(self.setupGroup)
        self.vbox.addLayout(self.grid)
        self.vbox.addLayout(self.setupForm)

        # self.setupForm = QtWidgets.QFormLayout(self.setupGroup)
        # self.setupForm.addRow(self.lblAccX, self.accXCombo)
        # self.setupForm.addRow(self.lblAccY, self.accYCombo)
        # self.setupForm.addRow(self.lblAccZ, self.accZCombo)
        # self.setupForm.addRow(self.lblAngRateX, self.angRateXCombo)
        # self.setupForm.addRow(self.lblAngRateY, self.angRateYCombo)
        # self.setupForm.addRow(self.lblAngRateZ, self.angRateZCombo)
        # self.setupForm.addRow(QtWidgets.QLabel(""), self.applyGCorr)
        # self.setupForm.addRow(self.lblIntegrationFolder, self.integrationFolder)

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        # LAYOUT
        # Horizontal groups
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.copyGroup)
        self.layout.addWidget(self.setupGroup)
        self.layout.addStretch()
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

        # Get combo columns
        columns = ["-"] + logger.all_channel_names

        # Columns to process
        self.accXCombo.addItems(columns)
        self.accYCombo.addItems(columns)
        self.accZCombo.addItems(columns)
        self.angRateXCombo.addItems(columns)
        self.angRateYCombo.addItems(columns)
        self.angRateZCombo.addItems(columns)

        self.accXCombo.setCurrentText(logger.acc_x_col)
        self.accYCombo.setCurrentText(logger.acc_y_col)
        self.accZCombo.setCurrentText(logger.acc_z_col)
        self.angRateXCombo.setCurrentText(logger.ang_rate_x_col)
        self.angRateYCombo.setCurrentText(logger.ang_rate_y_col)
        self.angRateZCombo.setCurrentText(logger.ang_rate_z_col)

        self.applyGCorr.setChecked(logger.apply_gcorr)
        self.integrationFolder.setText(self.control.integration_output_folder)

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

        logger.acc_x_col = self.accXCombo.currentText()
        logger.acc_y_col = self.accYCombo.currentText()
        logger.acc_z_col = self.accZCombo.currentText()
        logger.ang_rate_x_col = self.angRateXCombo.currentText()
        logger.ang_rate_y_col = self.angRateYCombo.currentText()
        logger.ang_rate_z_col = self.angRateZCombo.currentText()
        logger.apply_gcorr = self.applyGCorr.isChecked()
        self.control.integration_output_folder = self.integrationFolder.text()

        return logger

    def error(self, msg):
        print(f"Error: {msg}")
        return QtWidgets.QMessageBox.critical(self, "Error", msg)


if __name__ == "__main__":
    # For testing widget layout
    app = QtWidgets.QApplication(sys.argv)
    # win = TimeSeriesIntegrationSetupTab()
    win = EditIntegrationSetupDialog()
    win.show()
    app.exit(app.exec_())
