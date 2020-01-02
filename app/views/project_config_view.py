"""Project config dashboard gui view. Handles all project setup."""

__author__ = "Craig Dickinson"

import logging
import os
import sys
from datetime import datetime
from glob import glob

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSlot

from app.core.azure_cloud_storage import check_azure_account_exists
from app.core.calc_seascatter import Seascatter
from app.core.calc_transfer_functions import TransferFunctions
from app.core.control import Control, InputError
from app.core.custom_date import get_datetime_format
from app.core.detect_file_timestamp_format import detect_file_timestamp_format
from app.core.file_props_2hps2_acc import (
    detect_2hps2_logger_properties,
    set_2hps2_acc_file_format,
)
from app.core.file_props_custom_format import set_custom_file_format
from app.core.file_props_fugro_csv import (
    detect_fugro_logger_properties,
    set_fugro_csv_file_format,
)
from app.core.file_props_pulse_acc import (
    detect_pulse_logger_properties,
    set_pulse_acc_file_format,
)
from app.core.logger_properties import LoggerError, LoggerProperties
from app.core.project_config import ProjectConfigJSONFile
from app.views.screening_setup_view import ScreeningSetupTab
from app.views.time_series_integration_view import TimeSeriesIntegrationSetupTab

# Module variables: Logger properties lists and dictionaries
delims_gui_to_logger = {"comma": ",", "space": " ", "tab": "\t"}
delims_logger_to_gui = {",": "comma", " ": "space", "\t": "tab"}
file_types = ["Custom", "Fugro-csv", "Pulse-acc", "2HPS2-acc"]
index_types = ["Timestamp", "Time Step"]
delimiters = ["comma", "space", "tab"]


class ConfigModule(QtWidgets.QWidget):
    """Main screen containing project configuration setup."""

    def __init__(self, parent=None):
        super(ConfigModule, self).__init__(parent)

        self.parent = parent
        self.skip_on_logger_item_edited = False
        self.del_logger = False
        self.control = Control()
        self.scatter = Seascatter()
        self.tf = TransferFunctions()
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # WIDGETS
        self.openConfigButton = QtWidgets.QPushButton("Open...")
        self.openConfigButton.setToolTip("Open config (*.json) file (Ctrl+O)")
        self.saveConfigButton = QtWidgets.QPushButton("Save")
        self.saveConfigButton.setToolTip(
            "Export project settings to config (*.json) file (Ctrl+S)"
        )
        self.newProjButton = QtWidgets.QPushButton("New Project")
        self.newProjButton.setShortcut("Ctrl+N")
        self.newProjButton.setToolTip("Clear all settings (Ctrl+N)")
        self.openProjDirButton = QtWidgets.QPushButton("Open Project Folder")
        self.openProjDirButton.setShortcut("Ctrl+D")
        self.openProjDirButton.setToolTip("Ctrl+D")
        self.addLoggerButton = QtWidgets.QPushButton("Add Dataset...")
        self.addLoggerButton.setShortcut("Ctrl+A")
        self.addLoggerButton.setToolTip("Ctrl+A")
        self.remLoggerButton = QtWidgets.QPushButton("Remove Dataset")
        self.remLoggerButton.setShortcut("Ctrl+Del")
        self.remLoggerButton.setToolTip("Ctrl+Del")
        self.loggersList = QtWidgets.QListWidget()
        self.columnList = QtWidgets.QListWidget()
        self.colSpacer = QtWidgets.QSpacerItem(20, 1)

        # Global screening check boxes
        self.reportScreenChkBox = QtWidgets.QCheckBox("Data Quality Screening")
        self.reportScreenChkBox.setChecked(True)
        self.reportScreenChkBox.setEnabled(False)
        self.statsScreenChkBox = QtWidgets.QCheckBox("Statistics Screening")
        self.statsScreenChkBox.setChecked(True)
        self.spectScreenChkBox = QtWidgets.QCheckBox("Spectral Screening")
        self.spectScreenChkBox.setChecked(True)

        # Process buttons
        h = 30
        self.processButton = QtWidgets.QPushButton("Process Screening")
        self.processButton.setFixedHeight(h)
        self.processButton.setToolTip(
            "Screen loggers and calculate stats and spectral data (F6)"
        )

        self.calcSeascatterButton = QtWidgets.QPushButton("Create Sea Scatter")
        self.calcSeascatterButton.setFixedHeight(h)
        self.calcSeascatterButton.setToolTip("Create Hs-Tp sea scatter diagram (F7)")

        self.calcTFButton = QtWidgets.QPushButton("Calculate Transfer Functions")
        self.calcTFButton.setFixedHeight(h)
        self.calcTFButton.setToolTip(
            "Calculate frequency-dependent transfer functions (F8)"
        )

        self.calcFatigueButton = QtWidgets.QPushButton("Calculate Fatigue")
        self.calcFatigueButton.setFixedHeight(h)
        self.calcFatigueButton.setToolTip("Run spectral fatigue analysis (F9)")
        self.spacer = QtWidgets.QSpacerItem(1, 20)

        # Config tab widgets
        self.generalTab = GeneralTab(self)
        self.loggerPropsTab = LoggerPropertiesTab(self)
        self.screeningTab = ScreeningSetupTab(self)
        self.integrationTab = TimeSeriesIntegrationSetupTab(self)
        self.scatterTab = SeascatterTab(self)
        self.tfSettingsTab = TransferFunctionsTab(self)

        # CONTAINERS
        # Config buttons container
        self.hboxConfig = QtWidgets.QHBoxLayout()
        self.hboxConfig.addWidget(QtWidgets.QLabel("Config File:"))
        self.hboxConfig.addWidget(self.openConfigButton)
        self.hboxConfig.addWidget(self.saveConfigButton)
        self.hboxConfig.addItem(self.colSpacer)
        self.hboxConfig.addWidget(self.newProjButton)
        self.hboxConfig.addWidget(self.openProjDirButton)
        self.hboxConfig.addStretch()

        # Loggers container
        self.loggersGroup = QtWidgets.QGroupBox("Project Datasets/Loggers")
        self.loggersGroup.setFixedWidth(180)
        self.vboxLoggers = QtWidgets.QVBoxLayout(self.loggersGroup)
        self.vboxLoggers.addWidget(self.addLoggerButton)
        self.vboxLoggers.addWidget(self.remLoggerButton)
        self.vboxLoggers.addWidget(QtWidgets.QLabel("Datasets"))
        self.vboxLoggers.addWidget(self.loggersList)
        self.vboxLoggers.addWidget(QtWidgets.QLabel("Columns"))
        self.vboxLoggers.addWidget(self.columnList)

        # Setup container
        self.setupTabs = QtWidgets.QTabWidget()
        self.setupTabs.addTab(self.generalTab, "Project Details")
        self.setupTabs.addTab(self.loggerPropsTab, "Logger File Properties")
        self.setupTabs.addTab(self.screeningTab, "Screening Setup")
        self.setupTabs.addTab(self.integrationTab, "Time Series Integration Setup")
        self.setupTabs.addTab(self.scatterTab, "Sea Scatter Setup")
        self.setupTabs.addTab(self.tfSettingsTab, "Transfer Functions Setup")

        # Screening check boxes and process buttons container
        self.screeningGroup = QtWidgets.QGroupBox("Global Screening Flags")
        self.vboxFlags = QtWidgets.QVBoxLayout(self.screeningGroup)
        self.vboxFlags.addWidget(self.reportScreenChkBox)
        self.vboxFlags.addWidget(self.statsScreenChkBox)
        self.vboxFlags.addWidget(self.spectScreenChkBox)

        self.vboxRun = QtWidgets.QVBoxLayout()
        self.vboxRun.addWidget(self.screeningGroup)
        self.vboxRun.addItem(self.spacer)
        self.vboxRun.addWidget(self.processButton)
        self.vboxRun.addItem(self.spacer)
        self.vboxRun.addWidget(self.calcSeascatterButton)
        self.vboxRun.addItem(self.spacer)
        self.vboxRun.addWidget(self.calcTFButton)
        self.vboxRun.addItem(self.spacer)
        self.vboxRun.addWidget(self.calcFatigueButton)
        self.vboxRun.addStretch()

        # LAYOUT
        self.hbox = QtWidgets.QHBoxLayout()
        self.hbox.addWidget(self.loggersGroup)
        self.hbox.addWidget(self.setupTabs)

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addLayout(self.hboxConfig)
        self.vbox.addLayout(self.hbox)

        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addLayout(self.vbox)
        self.layout.addLayout(self.vboxRun)

    def _connect_signals(self):
        self.openConfigButton.clicked.connect(self.on_open_config_clicked)
        self.saveConfigButton.clicked.connect(self.on_save_config_clicked)
        self.newProjButton.clicked.connect(self.on_new_project_clicked)
        self.openProjDirButton.clicked.connect(self.on_open_project_folder_clicked)
        self.addLoggerButton.clicked.connect(self.on_add_logger_clicked)
        self.remLoggerButton.clicked.connect(self.on_remove_logger_clicked)
        self.loggersList.currentItemChanged.connect(self.on_logger_selected)
        self.loggersList.itemChanged.connect(self.on_logger_item_edited)
        self.statsScreenChkBox.toggled.connect(self.on_stats_screen_toggled)
        self.spectScreenChkBox.toggled.connect(self.on_spect_screen_toggled)
        self.processButton.clicked.connect(self.on_process_screening_clicked)
        self.calcSeascatterButton.clicked.connect(self.on_calc_seascatter_clicked)
        self.calcTFButton.clicked.connect(self.on_calc_transfer_functions_clicked)
        self.calcFatigueButton.clicked.connect(self.on_calc_fatigue_clicked)

    def on_open_config_clicked(self):
        """Load config JSON file."""

        if not self.parent:
            return

        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, caption="Open Config File", filter="Config Files (*.json)"
        )

        if filepath:
            self.load_config_file(filepath)

    def on_save_config_clicked(self):
        """Save project configuration settings as a dictionary to a JSON file."""

        if self.control.project_num == "" and self.control.project_name == "":
            msg = (
                "A project number and project name are required to create a project config file.\n"
                "Input missing data in the Campaign Info tab of the Project Config dashboard."
            )
            return self.parent.warning(msg)

        # Compile configuration data into a dictionary and save as a json file
        try:
            config = ProjectConfigJSONFile()
            config.add_general_settings(self.control)
            config.add_loggers_settings(self.control.loggers)
            config.add_seascatter_settings(self.scatter)
            config.add_transfer_functions_settings(self.tf)
            config.save_config(
                proj_num=self.control.project_num,
                proj_name=self.control.project_name,
                proj_path=self.control.project_path,
            )
        except FileNotFoundError as e:
            msg = f"Error saving config file. No such directoy:\n{self.control.project_path}."
            self.parent.error(msg)
            logging.exception(e)
        except Exception as e:
            msg = "Unexpected error saving project config"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

        # Check file created
        if os.path.exists(config.full_path):
            # Update config dashboard with config filename and inform user
            self.control.config_file = config.filename
            self.generalTab.configFilename.setText(config.filename)
            msg = f"Project config settings saved to:\n{config.full_path}"
            QtWidgets.QMessageBox.information(self, "Save Project Config", msg)

            # Update control object in DataLab instance
            self.parent.control = self.control

    def on_new_project_clicked(self):
        """Clear project control object and all config dashboard values."""

        if not self.parent:
            return

        # Create new settings objects
        self.control = Control()
        self.scatter = Seascatter()
        self.tf = TransferFunctions()

        # Map settings objects to associated child widget objects
        self._map_setup_objects_to_tabs()

        # Reset global process check box states
        self.statsScreenChkBox.setChecked(self.control.global_process_stats)
        self.spectScreenChkBox.setChecked(self.control.global_process_spect)

        # Map settings objects to parent DataLab instance
        self.parent.control = self.control
        self.parent.scatter = self.scatter
        self.parent.tf = self.tf

        # Clear logger combo box
        # Note: This will trigger the clearing of the logger properties, stats and spectral dashboards
        self.loggersList.clear()
        self.columnList.clear()

        # Clear campaign data dashboard and update window title to include config file path
        self.generalTab.clear_dashboard()
        self.loggerPropsTab.clear_dashboard()
        self.screeningTab.clear_dashboard()
        self.integrationTab.clear_dashboard()
        self.scatterTab.clear_dashboard()
        self.tfSettingsTab.clear_dashboard()

        # Reset window title
        self.parent.set_window_title()

        # Select campaign tab and open setup dialog
        self.setupTabs.setCurrentWidget(self.generalTab)
        self.generalTab.on_edit_clicked()

        # Clear raw data dashboard
        self.parent.rawDataModule.clear_dashboard()

    def on_open_project_folder_clicked(self):
        try:
            os.startfile(self.control.project_path)
        except:
            QtWidgets.QMessageBox.warning(
                self, "Open Project Folder", "Couldn't open folder."
            )

    def on_add_logger_clicked(self):
        """Add new logger to list. Initial logger name is 'Logger n'."""

        n = self.loggersList.count()
        logger_id = f"Logger {n + 1}"

        # Create logger properties object and append to loggers list in control object
        logger = LoggerProperties(logger_id)
        self.control.loggers.append(logger)
        self.control.logger_ids.append(logger_id)
        self.control.logger_ids_upper.append(logger_id.upper())

        # Initialise as a general logger format
        logger = set_custom_file_format(logger)

        item = QtWidgets.QListWidgetItem(logger_id)
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        self.loggersList.addItem(item)
        self.loggersList.setCurrentRow(n)

        # Also add logger id to raw data module dataset combo box
        try:
            self.parent.rawDataModule.add_dataset(logger_id, self.control, index=n)
        except Exception as e:
            logging.exception(e)

        # Initialise dashboard layouts
        self.loggerPropsTab.set_logger_dashboard(logger)
        self.screeningTab.set_analysis_dashboard(logger)
        self.integrationTab.set_analysis_dashboard(logger)

        # Select logger properties tab and open edit dialog
        self.setupTabs.setCurrentWidget(self.loggerPropsTab)
        self.loggerPropsTab.on_edit_clicked()

    def on_remove_logger_clicked(self):
        """Remove selected logger."""

        if self.loggersList.count() == 0:
            return

        # Get logger selected in list to remove
        if self.loggersList.currentItem():
            i = self.loggersList.currentRow()
            logger = self.loggersList.currentItem().text()
        # Remove last item
        else:
            i = self.loggersList.count() - 1
            logger = self.loggersList.item(i).text()

        # Confirm with users
        msg = f"Are you sure you want to remove logger {logger}?"
        response = QtWidgets.QMessageBox.question(self, "Remove Logger", msg)

        if response == QtWidgets.QMessageBox.Yes:
            # Remove logger from control object
            logger = self.control.loggers[i]
            logger_id = logger.logger_id
            self.control.loggers.remove(logger)
            self.control.logger_ids.remove(logger_id)
            self.control.logger_ids_upper.remove(logger_id.upper())

            # Remove logger from loggers list
            self.del_logger = True
            self.loggersList.takeItem(i)
            self.del_logger = False

            # Remove logger from raw data dashboard combo box and data list
            self.parent.rawDataModule.remove_dataset(i)

            # Clear relevant dashboards if all loggers removed
            if self.loggersList.count() == 0:
                self.columnList.clear()
                self.loggerPropsTab.clear_dashboard()
                self.screeningTab.clear_dashboard()
                self.integrationTab.clear_dashboard()
                self.scatterTab.clear_dashboard()

    def on_logger_selected(self):
        """Update dashboard data pertaining to selected logger."""

        i = self.loggersList.currentRow()
        if i == -1:
            return

        if self.del_logger is True:
            # If first logger has been removed, set selected logger to be the new first logger
            if i == 1:
                i = 0

            # If second to last logger has been removed, set selected logger to be the last logger
            n = len(self.control.loggers) - 1
            if i > n:
                i = n

        logger = self.control.loggers[i]
        self.loggerPropsTab.set_logger_dashboard(logger)
        self.screeningTab.set_analysis_dashboard(logger)
        self.integrationTab.set_analysis_dashboard(logger)
        self.set_logger_columns_list(logger)

    def on_logger_item_edited(self):
        """Update logger combo box to match logger names of list widget."""

        # Skip function if logger id is edited through the edit dialog
        if self.skip_on_logger_item_edited is True:
            return

        # Retrieve new logger id from list
        i = self.loggersList.currentRow()
        new_logger_id = self.loggersList.currentItem().text()

        # Update logger id in control object
        self.control.loggers[i].logger_id = new_logger_id

        # Update dashboard logger id
        self.loggerPropsTab.loggerID.setText(new_logger_id)

        # Update the logger ids lists in the control object
        self.control.logger_ids[i] = new_logger_id
        self.control.logger_ids_upper[i] = new_logger_id.upper()

        # Update logger id in raw dashboard dataset combo box
        self.parent.rawDataModule.update_dateset_name(i, new_logger_id)

    def on_stats_screen_toggled(self):
        self.control.global_process_stats = self.statsScreenChkBox.isChecked()

    def on_spect_screen_toggled(self):
        self.control.global_process_spect = self.spectScreenChkBox.isChecked()

    def on_process_screening_clicked(self):
        self.parent.process_screening()

    def on_calc_seascatter_clicked(self):
        self.parent.calc_seascatter()

    def on_calc_transfer_functions_clicked(self):
        self.parent.calc_transfer_functions()

    def on_calc_fatigue_clicked(self):
        self.parent.calc_fatigue()

    def load_config_file(self, filepath):
        """Load config file and map properties."""

        try:
            # JSON config class - holds config data dictionary
            config = ProjectConfigJSONFile()

            # Connect warning signal
            config.signal_warning.connect(self.warning)

            # Read JSON file and store data in config object
            config.load_config_data(filepath)

            # Map JSON data to new objects that hold various setup data
            self.control = config.map_json_to_control(Control())
            self.scatter = config.map_json_to_seascatter(Seascatter())
            self.tf = config.map_json_to_transfer_functions(TransferFunctions())

            # Check a logger file formats exist in the drop-down
            self._check_logger_file_formats(self.control.loggers)

            # Assign config data to control object and project dashboard
            self._set_dashboards_on_load_config()
            self.parent.set_window_title(filepath)
        except InputError as e:
            self.parent.error(str(e))
            logging.exception(e)
        except Exception as e:
            msg = "Unexpected error loading config file"
            self.parent.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

        # Map settings objects to parent DataLab object
        self.parent.control = self.control
        self.parent.scatter = self.scatter
        self.parent.tf = self.tf

    def _check_logger_file_formats(self, loggers):
        """Check that all logger file formats are selectable in the logger properties drop-down."""

        for logger in loggers:
            if logger.file_format not in file_types:
                msg = (
                    f"{logger.logger_id} file format '{logger.file_format}' is not a selectable file format.\n\n"
                    f"File format has been set to '{file_types[0]}'. Check logger properties."
                )
                logger.file_format = file_types[0]
                self.warning(msg)

    def update_logger_id_list(self, logger_id, logger_idx):
        """Update logger name in the loggers list if logger id in edit dialog is changed."""

        # Set flag to skip logger list item edited action when triggered
        self.skip_on_logger_item_edited = True
        self.loggersList.item(logger_idx).setText(logger_id)
        self.skip_on_logger_item_edited = False

        # Update the logger ids lists in the control object
        self.control.logger_ids[logger_idx] = logger_id
        self.control.logger_ids_upper[logger_idx] = logger_id.upper()

        # Update logger id in raw dashboard dataset combo box
        self.parent.rawDataModule.update_dateset_name(logger_idx, logger_id)

    def set_logger_columns_list(self, logger):
        """Populate logger columns list with the column details from a test file."""

        self.columnList.clear()
        channels = logger.all_channel_names
        units = logger.all_channel_units

        # Populate list widget if channels list is not empty
        items = [f"1. {logger.index_col_name}"]
        items += [
            f"{i + 2}. {c}" if u == "-" else f"{i + 2}. {c} ({u})"
            for i, (c, u) in enumerate(zip(channels, units))
        ]
        for i in items:
            item = QtWidgets.QListWidgetItem(i)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
            self.columnList.addItem(item)

    def _set_dashboards_on_load_config(self):
        """Set dashboard values with data in setup objects after loading JSON file."""

        # Map the loaded settings objects to the associated tab widget objects
        self._map_setup_objects_to_tabs()

        # Set global process check box states
        self.statsScreenChkBox.setChecked(self.control.global_process_stats)
        self.spectScreenChkBox.setChecked(self.control.global_process_spect)

        # Set campaign data to dashboard
        self.generalTab.set_campaign_dashboard()

        self.loggersList.clear()
        self.columnList.clear()

        # Add loggers in control object to loggers list
        if self.control.loggers:
            for logger in self.control.loggers:
                item = QtWidgets.QListWidgetItem(logger.logger_id)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                self.loggersList.addItem(item)
                self.repaint()
                msg = f"Retrieving {logger.logger_id} raw file names..."
                self.parent.statusbar.showMessage(msg)
                self.repaint()

                # Attempt to retrieve raw filenames to populate dashboard
                try:
                    logger.get_filenames()
                except Exception as e:
                    self.warning(str(e))
                    logging.exception(e)

            self.parent.statusbar.showMessage("")

            # Select first logger and set dashboards
            self.loggersList.setCurrentRow(0)
            logger = self.control.loggers[0]
            self.loggerPropsTab.set_logger_dashboard(logger)
            self.screeningTab.set_analysis_dashboard(logger)
            self.integrationTab.set_analysis_dashboard(logger)

            # Add logger ids to raw data module dataset combo box and plot first file if exists
            self.parent.rawDataModule.add_datasets(self.control)

        # Set seascatter dashboard
        self.scatterTab.set_scatter_dashboard()

        # Set transfer functions dashboard
        self.tfSettingsTab.set_tf_dashboard()

    def _map_setup_objects_to_tabs(self):
        """Update the various project config tab objects with their associated settings objects."""

        self.generalTab.control = self.control
        self.loggerPropsTab.control = self.control
        self.screeningTab.control = self.control
        self.integrationTab.control = self.control
        self.scatterTab.control = self.control
        self.scatterTab.scatter = self.scatter
        self.tfSettingsTab.tf = self.tf

    @pyqtSlot(str)
    def warning(self, msg):
        print(f"Warning: {msg}")
        return QtWidgets.QMessageBox.information(self, "Warning", msg)


class GeneralTab(QtWidgets.QWidget):
    """GUI screen to control project setup."""

    def __init__(self, parent=None):
        super(GeneralTab, self).__init__(parent)

        self.parent = parent
        self.control = Control()
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # WIDGETS
        self.editButton = QtWidgets.QPushButton("Edit Data...")
        self.editButton.setShortcut("Ctrl+E")
        self.editButton.setToolTip("Ctrl+E")
        self.projNum = QtWidgets.QLabel("-")
        self.projNum.setFixedWidth(40)
        self.projName = QtWidgets.QLabel("-")
        self.campaignName = QtWidgets.QLabel("-")
        self.projPath = QtWidgets.QLabel("-")
        self.projPath.setWordWrap(True)
        self.configFilename = QtWidgets.QLabel("-")

        # CONTAINERS
        self.projGroup = QtWidgets.QGroupBox("Project Details")
        self.projGroup.setMinimumWidth(500)
        self.form = QtWidgets.QFormLayout(self.projGroup)
        self.form.addRow(QtWidgets.QLabel("Project number:"), self.projNum)
        self.form.addRow(QtWidgets.QLabel("Project name:"), self.projName)
        self.form.addRow(QtWidgets.QLabel("Campaign name:"), self.campaignName)
        self.form.addRow(QtWidgets.QLabel("Project location:"), self.projPath)
        self.form.addRow(QtWidgets.QLabel("Config file name:"), self.configFilename)

        # LAYOUT
        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.editButton, stretch=0, alignment=QtCore.Qt.AlignLeft)
        self.vbox.addWidget(self.projGroup)
        self.vbox.addStretch()

        self.hbox = QtWidgets.QHBoxLayout(self)
        self.hbox.addLayout(self.vbox)
        self.hbox.addStretch()

        # TABLE INPUT TEST - Could consider trying to use OrcaFlex style table input cells
        # self.tableInput = QtWidgets.QTableWidget()
        # self.tableInput.setFixedSize(60, 25)
        # self.tableInput.setRowCount(1)
        # self.tableInput.setColumnCount(1)
        # self.tableInput.horizontalHeader().hide()
        # self.tableInput.verticalHeader().hide()
        # self.form.addRow(QtWidgets.QLabel('table value:'), self.tableInput)
        #
        # item = QtWidgets.QTableWidgetItem('21239')
        # # item.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.tableInput.setItem(0, 0, item)
        # header = self.tableInput.horizontalHeader()
        # header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        # header = self.tableInput.verticalHeader()
        # header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        # # self.tableInput.resizeColumnsToContents()
        # # self.tableInput.resizeRowsToContents()
        # item = self.tableInput.item(0, 0)
        # print(item.text())

    def _connect_signals(self):
        self.editButton.clicked.connect(self.on_edit_clicked)

    def on_edit_clicked(self):
        """Open campaign settings edit dialog."""

        editInfo = EditGeneralDialog(self, self.control)
        editInfo.show()

    def set_campaign_dashboard(self):
        """Set config tab campaign info."""

        self.projNum.setText(self.control.project_num)
        self.projName.setText(self.control.project_name)
        if self.control.campaign_name == "":
            self.campaignName.setText("-")
        else:
            self.campaignName.setText(self.control.campaign_name)
        self.projPath.setText(self.control.project_path)
        self.configFilename.setText(self.control.config_file)

    def clear_dashboard(self):
        """Initialise all values in logger dashboard."""

        self.projNum.setText("-")
        self.projName.setText("-")
        self.campaignName.setText("-")
        self.projPath.setText("-")
        self.configFilename.setText("-")


class EditGeneralDialog(QtWidgets.QDialog):
    """Edit window for project and campaign data."""

    def __init__(self, parent=None, control=Control()):
        super(EditGeneralDialog, self).__init__(parent)

        self.parent = parent
        self.control = control
        self._init_ui()
        self._connect_signals()
        self._set_dialog_data()

    def _init_ui(self):
        self.setWindowTitle("Edit Project Details")
        self.setFixedWidth(500)

        # Sizing policy
        policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )

        # WIDGETS
        self.projNum = QtWidgets.QLineEdit()
        self.projNum.setFixedWidth(40)
        self.projName = QtWidgets.QLineEdit()
        self.campaignName = QtWidgets.QLineEdit()
        self.projPath = QtWidgets.QPlainTextEdit()
        self.projPath.setFixedHeight(40)
        self.projPath.setToolTip(
            "If not input the current working directory will be used."
        )
        self.browseButton = QtWidgets.QPushButton("&Browse...")
        self.browseButton.setSizePolicy(policy)
        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        # CONTAINERS
        self.formWidget = QtWidgets.QWidget()
        self.form = QtWidgets.QFormLayout(self.formWidget)
        self.form.addRow(QtWidgets.QLabel("Project number:"), self.projNum)
        self.form.addRow(QtWidgets.QLabel("Project name:"), self.projName)
        self.form.addRow(QtWidgets.QLabel("Campaign name:"), self.campaignName)
        self.form.addRow(QtWidgets.QLabel("Project location:"), self.projPath)
        self.form.addRow(QtWidgets.QLabel(""), self.browseButton)

        # LAYOUT
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.formWidget)
        self.layout.addWidget(self.buttonBox)

    def _connect_signals(self):
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.browseButton.clicked.connect(self.set_project_path)

    def _set_dialog_data(self):
        """Set dialog data with campaign info from control object."""

        control = self.control

        self.projNum.setText(control.project_num)
        self.projName.setText(control.project_name)
        self.campaignName.setText(control.campaign_name)
        self.projPath.setPlainText(control.project_path)

    def on_ok_clicked(self):
        """Assign values to the control object and update the dashboard."""

        if not self.parent:
            return

        self.set_control_data()
        self.parent.set_campaign_dashboard()

    def set_control_data(self):
        """Assign values to the control object."""

        control = self.control
        control.project_num = self.projNum.text()
        control.project_name = self.projName.text()
        control.campaign_name = self.campaignName.text()

        if self.projPath.toPlainText() == "":
            control.project_path = os.getcwd()
        else:
            control.project_path = self.projPath.toPlainText()

    def set_project_path(self):
        """Set location of project root directory."""

        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Project Location")

        if dir_path:
            self.projPath.setPlainText(dir_path)


class LoggerPropertiesTab(QtWidgets.QWidget):
    """Widget tabs for logger properties and analysis settings."""

    def __init__(self, parent=None):
        super(LoggerPropertiesTab, self).__init__(parent)

        self.parent = parent
        self.control = Control()
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Create widget layout."""

        # WIDGETS
        self.editButton = QtWidgets.QPushButton("Edit Data...")
        self.editButton.setShortcut("Ctrl+E")
        self.editButton.setToolTip("Ctrl+E")
        self.openFolderButton = QtWidgets.QPushButton("Open Source Folder...")
        self.openFolderButton.setShortcut("Ctrl+F")
        self.openFolderButton.setToolTip(
            "Ctrl+F (Disabled if source files stored on Azure Cloud Storage)"
        )
        self.loggerID = QtWidgets.QLabel("-")
        self.dataSource = QtWidgets.QLabel("-")
        self.loggerPath = QtWidgets.QLabel("-")
        self.loggerPath.setWordWrap(True)
        self.fileFormat = QtWidgets.QLabel("-")
        self.fileTimestampEmbedded = QtWidgets.QLabel("-")
        self.fileTimestampFormat = QtWidgets.QLabel("-")
        self.firstColData = QtWidgets.QLabel("-")
        self.fileExt = QtWidgets.QLabel("-")
        self.fileDelimiter = QtWidgets.QLabel("-")
        self.numHeaderRows = QtWidgets.QLabel("-")
        self.numColumns = QtWidgets.QLabel("-")
        self.channelHeaderRow = QtWidgets.QLabel("-")
        self.unitsHeaderRow = QtWidgets.QLabel("-")
        self.dataTimestampFormat = QtWidgets.QLabel("-")
        self.loggingFreq = QtWidgets.QLabel("-")
        self.loggingDuration = QtWidgets.QLabel("-")

        # CONTAINERS
        # Logger properties group
        self.loggerPropsGroup = QtWidgets.QGroupBox("Logger Properties")
        self.loggerPropsGroup.setMinimumWidth(500)
        self.form = QtWidgets.QFormLayout(self.loggerPropsGroup)
        self.form.addRow(QtWidgets.QLabel("Logger ID:"), self.loggerID)
        self.form.addRow(QtWidgets.QLabel("Logger source:"), self.dataSource)
        self.form.addRow(QtWidgets.QLabel("Logger path:"), self.loggerPath)
        self.form.addRow(QtWidgets.QLabel("File type:"), self.fileFormat)
        self.form.addRow(
            QtWidgets.QLabel("File timestamp embedded:"), self.fileTimestampEmbedded
        )
        self.form.addRow(QtWidgets.QLabel("File timestamp:"), self.fileTimestampFormat)
        self.form.addRow(QtWidgets.QLabel("First column data:"), self.firstColData)
        self.form.addRow(QtWidgets.QLabel("Extension:"), self.fileExt)
        self.form.addRow(QtWidgets.QLabel("Delimiter:"), self.fileDelimiter)
        self.form.addRow(QtWidgets.QLabel("Number of header rows:"), self.numHeaderRows)
        self.form.addRow(
            QtWidgets.QLabel("Number of expected columns:"), self.numColumns
        )
        self.form.addRow(QtWidgets.QLabel("Channel header row:"), self.channelHeaderRow)
        self.form.addRow(QtWidgets.QLabel("Units header row:"), self.unitsHeaderRow)
        self.form.addRow(QtWidgets.QLabel("Data timestamp:"), self.dataTimestampFormat)
        self.form.addRow(QtWidgets.QLabel("Logging frequency (Hz):"), self.loggingFreq)
        self.form.addRow(
            QtWidgets.QLabel("Logging duration (s):"), self.loggingDuration
        )

        # LAYOUT
        self.hboxButtons = QtWidgets.QHBoxLayout()
        self.hboxButtons.addWidget(self.editButton)
        self.hboxButtons.addWidget(self.openFolderButton)
        self.hboxButtons.setAlignment(QtCore.Qt.AlignLeft)

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addLayout(self.hboxButtons)
        self.vbox.addWidget(self.loggerPropsGroup)
        self.vbox.addStretch()

        self.hbox = QtWidgets.QHBoxLayout(self)
        self.hbox.addLayout(self.vbox)
        self.hbox.addStretch()

    def _connect_signals(self):
        self.editButton.clicked.connect(self.on_edit_clicked)
        self.openFolderButton.clicked.connect(self.on_open_folder_clicked)

    def on_edit_clicked(self):
        """Open logger properties edit dialog."""

        if self.parent.loggersList.count() == 0:
            msg = f"No loggers exist to edit. Add a logger first."
            return QtWidgets.QMessageBox.information(
                self, "Edit Logger Properties", msg
            )

        # Retrieve selected logger object
        # TODO: If adding logger, dialog should show new logger id - works but if remove one first, id may not be unique
        logger_idx = self.parent.loggersList.currentRow()

        # Create edit logger properties dialog window instance
        editLoggerProps = EditLoggerPropertiesDialog(self, self.control, logger_idx)
        editLoggerProps.show()

    def on_open_folder_clicked(self):
        """Open logger files source folder."""

        try:
            i = self.parent.loggersList.currentRow()
        except:
            return

        if i == -1:
            return

        try:
            os.startfile(self.control.loggers[i].logger_path)
        except:
            QtWidgets.QMessageBox.warning(
                self, "Open Raw Files Folder", "Couldn't open folder."
            )

    def set_logger_dashboard(self, logger):
        """Set dashboard with logger properties from logger object."""

        self.loggerID.setText(logger.logger_id)

        # Disable open folder button if files not stored locally
        if logger.data_on_azure:
            src = "Azure Cloud Storage"
            self.openFolderButton.setEnabled(False)
        else:
            src = "Local files"
            self.openFolderButton.setEnabled(True)

        self.dataSource.setText(src)
        self.loggerPath.setText(logger.logger_path)
        self.fileFormat.setText(logger.file_format)

        if logger.file_timestamp_embedded is True:
            self.fileTimestampEmbedded.setText("Yes")
        else:
            self.fileTimestampEmbedded.setText("No")

        self.fileTimestampFormat.setText(logger.file_timestamp_format)
        self.firstColData.setText(logger.first_col_data)
        self.fileExt.setText(logger.file_ext)
        self.fileDelimiter.setText(delims_logger_to_gui[logger.file_delimiter])
        self.numHeaderRows.setText(str(logger.num_headers))
        self.numColumns.setText(str(logger.num_columns))
        self.channelHeaderRow.setText(str(logger.channel_header_row))
        self.unitsHeaderRow.setText(str(logger.units_header_row))
        self.dataTimestampFormat.setText(logger.timestamp_format)
        self.loggingFreq.setText(str(logger.freq))
        self.loggingDuration.setText(str(logger.duration))

    def clear_dashboard(self):
        """Initialise all values in logger dashboard."""

        self.loggerID.setText("-")
        self.dataSource.setText("-")
        self.loggerPath.setText("-")
        self.fileFormat.setText("-")
        self.fileTimestampEmbedded.setText("-")
        self.fileTimestampFormat.setText("-")
        self.firstColData.setText("-")
        self.fileExt.setText("-")
        self.fileDelimiter.setText("-")
        self.numHeaderRows.setText("-")
        self.numColumns.setText("-")
        self.channelHeaderRow.setText("-")
        self.unitsHeaderRow.setText("-")
        self.dataTimestampFormat.setText("-")
        self.loggingFreq.setText("-")
        self.loggingDuration.setText("-")


class EditLoggerPropertiesDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, control=Control(), logger_idx=0):
        super(EditLoggerPropertiesDialog, self).__init__(parent)

        self.parent = parent

        # Store control settings and selected logger properties objects
        self.control = control
        self.logger_idx = logger_idx
        if control.loggers:
            self.logger = control.loggers[logger_idx]
        else:
            self.logger = LoggerProperties()

        # Store settings specific to initial file format that can be restored, if need be,
        # when selecting between file formats in the combo box
        self.init_logger = LoggerProperties()
        self.init_file_format = ""

        self._init_ui()
        self._connect_signals()
        self._set_dialog_data(self.logger)

        # Populate copy loggers combo box
        self._set_copy_logger_combo()

    def _init_ui(self):
        self.setWindowTitle("Edit Logger File Properties")
        self.setMinimumWidth(500)

        # Define input box validators
        int_validator = QtGui.QIntValidator()
        int_validator.setBottom(1)
        dbl_validator = QtGui.QDoubleValidator()

        # Sizing policy
        policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )

        # WIDGETS
        self.loggerID = QtWidgets.QLineEdit()
        self.loggerID.setFixedWidth(150)
        self.localFilesRadio = QtWidgets.QRadioButton("Local files")
        self.localFilesRadio.setChecked(True)
        self.azureCloudRadio = QtWidgets.QRadioButton("Azure Cloud Storage")
        self.setAzureButton = QtWidgets.QPushButton("Set &Azure Account Settings...")
        self.setAzureButton.setSizePolicy(policy)
        self.setAzureButton.setHidden(True)
        self.copyLogger = QtWidgets.QComboBox()
        self.copyLogger.setMinimumWidth(80)
        self.copyLogger.addItem("-")
        self.copyLoggerButton = QtWidgets.QPushButton("&Copy Properties")
        tooltip = "Note the file timestamp property is not copied since it is dependent on the raw file name structure."
        self.copyLoggerButton.setToolTip(tooltip)
        self.loggerPath = QtWidgets.QPlainTextEdit()
        self.loggerPath.setFixedHeight(40)
        self.browseButton = QtWidgets.QPushButton("&Browse...")
        self.browseButton.setSizePolicy(policy)
        self.fileFormat = QtWidgets.QComboBox()
        self.fileFormat.setFixedWidth(100)
        self.fileFormat.addItems(file_types)
        self.fileTimestampEmbeddedChkBox = QtWidgets.QCheckBox(
            "Timestamp embedded in file name"
        )
        self.fileTimestampEmbeddedChkBox.setChecked(True)
        self.detectTimestampFormatButton = QtWidgets.QPushButton(
            "Detect File &Timestamp Format"
        )
        self.detectTimestampFormatButton.setSizePolicy(policy)
        self.fileTimestampFormat = QtWidgets.QLineEdit()
        msg = (
            "Specify a format code to identify where the datetime info is located in the file names.\n"
            "E.g. For file names of the format:\n"
            "    BOP_2018_0607_1620,\n"
            "the required input is:\n"
            "    xxxxYYYYxmmDDxHHMM,\n"
            "where,\n"
            "Y = year\n"
            "m = month\n"
            "D = day\n"
            "H = hour\n"
            "M = minute\n"
            "S = second\n"
            "f = millisecond\n"
            "x = any other character."
        )
        self.fileTimestampFormat.setToolTip(msg)
        self.firstColData = QtWidgets.QComboBox()
        self.firstColData.setFixedWidth(100)
        self.firstColData.addItems(index_types)
        self.fileExt = QtWidgets.QLineEdit()
        self.fileExt.setFixedWidth(30)
        self.fileDelimiter = QtWidgets.QComboBox()
        self.fileDelimiter.setFixedWidth(60)
        self.fileDelimiter.addItems(delimiters)
        self.numHeaderRows = QtWidgets.QLineEdit()
        self.numHeaderRows.setFixedWidth(30)
        self.numHeaderRows.setValidator(int_validator)
        self.channelHeaderRow = QtWidgets.QLineEdit()
        self.channelHeaderRow.setFixedWidth(30)
        self.channelHeaderRow.setValidator(int_validator)
        self.unitsHeaderRow = QtWidgets.QLineEdit()
        self.unitsHeaderRow.setFixedWidth(30)
        self.unitsHeaderRow.setValidator(int_validator)
        self.detectPropsButton = QtWidgets.QPushButton("&Detect Properties")
        self.detectPropsButton.setSizePolicy(policy)
        self.dataTimestampFormat = QtWidgets.QLineEdit()
        self.numColumns = QtWidgets.QLineEdit()
        self.numColumns.setFixedWidth(30)
        self.numColumns.setValidator(int_validator)
        self.loggingFreq = QtWidgets.QLineEdit()
        self.loggingFreq.setFixedWidth(30)
        self.loggingFreq.setValidator(dbl_validator)
        self.loggingDuration = QtWidgets.QLineEdit()
        self.loggingDuration.setFixedWidth(50)
        self.loggingDuration.setValidator(dbl_validator)

        # Labels
        self.lblPath = QtWidgets.QLabel("Logger path:")
        self.lblCopy = QtWidgets.QLabel("Logger to copy:")
        self.lblFileFmt = QtWidgets.QLabel("File format:")
        self.lblFileTimestampFmt = QtWidgets.QLabel("File timestamp format:")
        self.lblFirstColData = QtWidgets.QLabel("First column data:")
        self.lblExt = QtWidgets.QLabel("File extension:")
        self.lblDelim = QtWidgets.QLabel("File delimiter:")
        self.lblNumRows = QtWidgets.QLabel("Number of header rows:")
        self.lblChanRow = QtWidgets.QLabel("Channel header row:")
        self.lblUnitsRow = QtWidgets.QLabel("Units header row:")
        self.lblTimestampFmt = QtWidgets.QLabel("Timestamp format:")
        self.lblNumCols = QtWidgets.QLabel("Number of expected columns:")
        self.lblFreq = QtWidgets.QLabel("Logging frequency (Hz):")
        self.lblDuration = QtWidgets.QLabel("Logging duration (s):")

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        # CONTAINERS
        # Logger name
        self.loggerIDLayout = QtWidgets.QFormLayout()
        self.loggerIDLayout.addRow(QtWidgets.QLabel("Logger ID:"), self.loggerID)

        # Location source group
        self.locSelectionGroup = QtWidgets.QGroupBox("Location Source")
        self.vbox = QtWidgets.QVBoxLayout(self.locSelectionGroup)
        self.vbox.addWidget(self.localFilesRadio)
        self.vbox.addWidget(self.azureCloudRadio)

        # Logger location group
        self.loggerLocGroup = QtWidgets.QGroupBox("Raw Data Location")
        self.hbox = QtWidgets.QHBoxLayout()
        self.hbox.addWidget(self.lblPath)
        self.hbox.addWidget(self.browseButton)
        self.hbox.addStretch()
        self.vbox2 = QtWidgets.QVBoxLayout(self.loggerLocGroup)
        self.vbox2.addWidget(self.setAzureButton)
        self.vbox2.addLayout(self.hbox)
        self.vbox2.addWidget(self.loggerPath)

        # Combine source and location containers
        self.locLayout = QtWidgets.QHBoxLayout()
        self.locLayout.addWidget(self.locSelectionGroup, alignment=QtCore.Qt.AlignTop)
        self.locLayout.addWidget(self.loggerLocGroup)

        # Copy logger group
        self.copyGroup = QtWidgets.QGroupBox(
            "Optional: Copy Properties from Another Logger"
        )
        self.hboxCopy = QtWidgets.QHBoxLayout(self.copyGroup)
        self.hboxCopy.addWidget(self.lblCopy)
        self.hboxCopy.addWidget(self.copyLogger)
        self.hboxCopy.addWidget(self.copyLoggerButton)
        self.hboxCopy.addStretch()

        # Logger type group
        self.loggerFilePropsGroup = QtWidgets.QGroupBox("Logger File Properties")
        self.typeForm = QtWidgets.QFormLayout(self.loggerFilePropsGroup)
        self.typeForm.addRow(self.lblFileFmt, self.fileFormat)
        self.typeForm.addRow(
            self.fileTimestampEmbeddedChkBox, self.detectTimestampFormatButton
        )
        self.typeForm.addRow(self.lblFileTimestampFmt, self.fileTimestampFormat)
        self.typeForm.addRow(self.lblFirstColData, self.firstColData)
        self.typeForm.addRow(self.lblExt, self.fileExt)
        self.typeForm.addRow(self.lblDelim, self.fileDelimiter)
        self.typeForm.addRow(self.lblNumRows, self.numHeaderRows)
        self.typeForm.addRow(self.lblChanRow, self.channelHeaderRow)
        self.typeForm.addRow(self.lblUnitsRow, self.unitsHeaderRow)

        # Logger properties group
        self.loggerDataPropsGroup = QtWidgets.QGroupBox("Logger Data Properties")
        self.propsForm = QtWidgets.QFormLayout(self.loggerDataPropsGroup)
        self.propsForm.addRow(self.detectPropsButton, QtWidgets.QLabel(""))
        self.propsForm.addRow(self.lblTimestampFmt, self.dataTimestampFormat)
        self.propsForm.addRow(self.lblNumCols, self.numColumns)
        self.propsForm.addRow(self.lblFreq, self.loggingFreq)
        self.propsForm.addRow(self.lblDuration, self.loggingDuration)

        # LAYOUT
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addLayout(self.loggerIDLayout)
        self.layout.addLayout(self.locLayout)
        self.layout.addWidget(self.copyGroup)
        self.layout.addWidget(self.loggerFilePropsGroup)
        self.layout.addWidget(self.loggerDataPropsGroup)
        self.layout.addStretch()
        self.layout.addWidget(self.buttonBox, stretch=0, alignment=QtCore.Qt.AlignRight)

    def _connect_signals(self):
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.azureCloudRadio.toggled.connect(self.on_azure_radio_toggled)
        self.setAzureButton.clicked.connect(self.on_set_azure_settings_clicked)
        self.browseButton.clicked.connect(self.on_browse_path_clicked)
        self.copyLoggerButton.clicked.connect(self.on_copy_logger_clicked)
        self.fileFormat.currentIndexChanged.connect(self.on_file_format_changed)
        self.fileTimestampEmbeddedChkBox.toggled.connect(
            self.on_file_timestamp_embedded_toggled
        )
        self.detectTimestampFormatButton.clicked.connect(
            self.on_detect_file_timestamp_format_clicked
        )
        self.firstColData.currentIndexChanged.connect(self.on_first_col_data_changed)
        self.detectPropsButton.clicked.connect(self.on_detect_props_clicked)

    def _set_dialog_data(self, logger):
        """Set dialog data with logger properties."""

        # Store logger properties specific to initial file format that can be restored, if need be, when selecting
        # between file formats. Note: self.logger is mapped to avoid mapping a temp logger if the copy another logger
        # function has been used
        self.init_logger = self.logger
        self.init_file_format = self.logger.file_format

        # Set radio for data source type
        if logger.data_on_azure:
            self.azureCloudRadio.setChecked(True)
        else:
            self.localFilesRadio.setChecked(True)

        # Check for empty string to guard against mapping values from a temp logger used when setting properties
        # copied from another logger
        if logger.logger_id != "":
            self.loggerID.setText(logger.logger_id)
        if logger.logger_path != "":
            self.loggerPath.setPlainText(logger.logger_path)

        self.fileFormat.setCurrentText(logger.file_format)
        self.fileTimestampEmbeddedChkBox.setChecked(logger.file_timestamp_embedded)
        self.fileTimestampFormat.setText(logger.file_timestamp_format)
        self.firstColData.setCurrentText(logger.first_col_data)
        self.fileExt.setText(logger.file_ext)
        self.fileDelimiter.setCurrentText(delims_logger_to_gui[logger.file_delimiter])
        self.numHeaderRows.setText(str(logger.num_headers))
        self.channelHeaderRow.setText(str(logger.channel_header_row))
        self.unitsHeaderRow.setText(str(logger.units_header_row))
        self.dataTimestampFormat.setText(logger.timestamp_format)
        self.numColumns.setText(str(logger.num_columns))
        self.loggingFreq.setText(str(logger.freq))
        self.loggingDuration.setText(str(logger.duration))

    def _set_copy_logger_combo(self):
        """Set the copy logger properties combo box with list of available loggers, excluding the current one."""

        # Get list of available loggers to copy
        loggers_to_copy = [
            i for i in self.control.logger_ids if i != self.logger.logger_id
        ]
        self.copyLogger.addItems(loggers_to_copy)

    def _set_enabled_inputs(self, file_format):
        """Enable or disable input fields based on selected file format (Custom, Fugro-csv, Pulse-csv, 2HPS2-acc)."""

        # Initialise for Fugro-csv format
        # self.lblExt.setHidden(True)
        # self.fileExt.setHidden(True)
        # self.lblDelim.setHidden(True)
        # self.fileDelimiter.setHidden(True)
        # self.lblNumRows.setHidden(True)
        # self.numHeaderRows.setHidden(True)
        # self.lblChanRow.setHidden(True)
        # self.channelHeaderRow.setHidden(True)
        # self.lblUnitsRow.setHidden(True)
        # self.unitsHeaderRow.setHidden(True)
        # self.lblTimestampFmt.setHidden(False)
        # self.dataTimestampFormat.setHidden(False)

        # Initialise for Custom
        self.fileTimestampEmbeddedChkBox.setEnabled(True)
        self.firstColData.setEnabled(True)
        self.fileExt.setEnabled(True)
        self.fileDelimiter.setEnabled(True)
        self.numHeaderRows.setEnabled(True)
        self.channelHeaderRow.setEnabled(True)
        self.unitsHeaderRow.setEnabled(True)
        self.dataTimestampFormat.setEnabled(True)

        if file_format == "Fugro-csv":
            # self.lblExt.setHidden(False)
            # self.fileExt.setHidden(False)
            # self.lblDelim.setHidden(False)
            # self.fileDelimiter.setHidden(False)
            # self.lblNumRows.setHidden(False)
            # self.numHeaderRows.setHidden(False)
            # self.lblChanRow.setHidden(False)
            # self.channelHeaderRow.setHidden(False)
            # self.lblUnitsRow.setHidden(False)
            # self.unitsHeaderRow.setHidden(False)
            self.fileTimestampEmbeddedChkBox.setEnabled(False)
            self.firstColData.setEnabled(False)
            self.fileExt.setEnabled(False)
            self.fileDelimiter.setEnabled(False)
            self.numHeaderRows.setEnabled(False)
            self.channelHeaderRow.setEnabled(False)
            self.unitsHeaderRow.setEnabled(False)
        elif file_format == "Pulse-acc" or file_format == "2HPS2-acc":
            # self.lblTimestampFmt.setHidden(True)
            # self.dataTimestampFormat.setHidden(True)
            self.fileTimestampEmbeddedChkBox.setEnabled(False)
            self.firstColData.setEnabled(False)
            self.fileExt.setEnabled(False)
            self.fileDelimiter.setEnabled(False)
            self.numHeaderRows.setEnabled(False)
            self.channelHeaderRow.setEnabled(False)
            self.unitsHeaderRow.setEnabled(False)
            self.dataTimestampFormat.setEnabled(False)

    def on_azure_radio_toggled(self):
        if self.azureCloudRadio.isChecked():
            self.lblPath.setText("Path to files (blobs):")
            self.setAzureButton.setHidden(False)
            self.browseButton.setHidden(True)
            msg = (
                "Path to files stored on Azure is to include the container name and any virtual folders.\n"
                "E.g. 21239-glendronach/raw_data/BOP."
            )
            self.loggerPath.setToolTip(msg)
        else:
            self.lblPath.setText("Logger path:")
            self.setAzureButton.setHidden(True)
            self.browseButton.setHidden(False)
            self.loggerPath.setToolTip("")

    def on_set_azure_settings_clicked(self):
        """Open Azure Cloud Storage settings dialog."""

        azureSettings = AzureAccountSetupDialog(
            self,
            account_name=self.control.azure_account_name,
            account_key=self.control.azure_account_key,
        )
        azureSettings.show()

    def on_browse_path_clicked(self):
        """Set location of logger directory."""

        logger_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Logger Location"
        )

        if logger_path:
            self.loggerPath.setPlainText(logger_path)

    def on_copy_logger_clicked(self):
        """Copy properties from another logger selected in the combo box."""

        # Get logger to copy
        ref_logger_id = self.copyLogger.currentText()

        if ref_logger_id == "-":
            return

        # Create a temp logger to copy setting so that settings can be confirmed by the user
        # before mapping to the control logger
        temp_logger = LoggerProperties()

        # Map logger properties from reference logger to active logger and update dialog values
        self.control.copy_logger_properties(ref_logger_id, temp_logger)
        self._set_dialog_data(temp_logger)

    def on_file_format_changed(self):
        """
        Set standard logger file settings and properties based on selected format.
        File format types:
            Custom
            Fugro-csv
            Pulse-acc
        """

        selected_file_format = self.fileFormat.currentText()
        logger = LoggerProperties()

        # Set which input fields are enabled/disabled based on file format set
        self._set_enabled_inputs(selected_file_format)

        # Depending on selection either: Create a new logger object with standard/default file format properties
        # of the selected logger type or revert initial logger properties
        # (Note Pulse-acc and 2HPS2-acc properties are not directly used by the respective read_pulse_acc and
        # read_2hps2_acc functions but they are used in other other file inspection routines)
        if selected_file_format == "Custom":
            if self.init_file_format == "Custom":
                logger = self.init_logger
            else:
                logger = set_custom_file_format(logger)
        elif selected_file_format == "Fugro-csv":
            if self.init_file_format == "Fugro-csv":
                logger = self.init_logger
            else:
                logger = set_fugro_csv_file_format(logger)
        elif selected_file_format == "Pulse-acc":
            if self.init_file_format == "Pulse-acc":
                logger = self.init_logger
            else:
                logger = set_pulse_acc_file_format(logger)
        elif selected_file_format == "2HPS2-acc":
            if self.init_file_format == "2HPS2-acc":
                logger = self.init_logger
            else:
                logger = set_2hps2_acc_file_format(logger)

        # Set test logger file format properties to the dialog Logger File Properties group
        self.fileTimestampEmbeddedChkBox.setChecked(logger.file_timestamp_embedded)
        self.firstColData.setCurrentText(logger.first_col_data)
        self.fileExt.setText(logger.file_ext)
        self.fileDelimiter.setCurrentText(delims_logger_to_gui[logger.file_delimiter])
        self.numHeaderRows.setText(str(logger.num_headers))
        self.channelHeaderRow.setText(str(logger.channel_header_row))
        self.unitsHeaderRow.setText(str(logger.units_header_row))
        self.dataTimestampFormat.setText(logger.timestamp_format)

    def on_file_timestamp_embedded_toggled(self):
        if self.fileTimestampEmbeddedChkBox.isChecked():
            self.detectTimestampFormatButton.setEnabled(True)
            self.fileTimestampFormat.setEnabled(True)
            self.fileTimestampFormat.setText(self.logger.file_timestamp_format)
        else:
            self.detectTimestampFormatButton.setEnabled(False)
            self.fileTimestampFormat.setEnabled(False)
            self.fileTimestampFormat.setText("N/A")

    def on_detect_file_timestamp_format_clicked(self):
        """
        Attempt to decipher the required file timestamp format to determine the datetime of a file.
        Example: For a filename BOP_2018_0607_1620
        File timestamp format = xxxxYYYYxmmDDxHHMM
        """

        # TODO: Add Azure support
        logger_path = self.loggerPath.toPlainText()
        if not os.path.exists(logger_path):
            msg = "Logger path does not exist. Set a logger path first."
            return QtWidgets.QMessageBox.information(
                self, "Detect File Timestamp Format", msg
            )

        raw_files = glob(logger_path + "/*." + self.fileExt.text())
        if not raw_files:
            msg = f"No files found in {logger_path}"
            return QtWidgets.QMessageBox.information(
                self, "Detect File Timestamp Format", msg
            )

        # Attempt to decipher file timestamp format code (e.g. xxxxYYYYxmmDDxHHMM)
        test_filename = os.path.basename(raw_files[0])
        file_timestamp_format = detect_file_timestamp_format(test_filename)

        # Test file timestamp format code
        # Extract timestamp embedded in test file with detected format code using methods of LoggerProperties class
        test_logger = LoggerProperties()
        test_logger.raw_filenames.append(test_filename)
        test_logger.file_timestamp_format = file_timestamp_format
        test_logger.get_timestamp_span()
        test_logger.check_file_timestamps()

        # Initialise with a failure message
        msg = (
            "File timestamp embedded in test file name:\n"
            f"{test_filename} could not be detected.\n\n"
            "File timestamp format code needs to be set manually."
        )

        # Check file timestamp list is populated
        if test_logger.file_timestamps:
            test_datetime = test_logger.file_timestamps[0]

            # Convert datetime to string - check whether seconds identifier is included
            if test_logger.sec_span[0] != -1:
                try:
                    test_timestamp = datetime.strftime(
                        test_datetime, "%Y-%m-%d %H:%M:%S"
                    )
                except:
                    test_timestamp = ""
            else:
                try:
                    test_timestamp = datetime.strftime(test_datetime, "%Y-%m-%d %H:%M")
                except:
                    test_timestamp = ""

            # Success message
            if test_timestamp:
                msg = (
                    f"File name tested: {test_filename}\n"
                    f"Timestamp detected in file name: {test_timestamp}\n\n"
                    "If this is not correct then the file timestamp format code needs manual correction."
                )

        QtWidgets.QMessageBox.information(
            self, "Detect File Timestamp Format Test", msg
        )

        # Set format to dialog
        self.fileTimestampFormat.setText(file_timestamp_format)

    def on_first_col_data_changed(self):
        """Set appropriate timestamp format input based on first column data selection."""

        if self.firstColData.currentText() == "Time Step":
            self.dataTimestampFormat.setText("N/A")
        else:
            self.dataTimestampFormat.setText(self.logger.timestamp_format)

    def on_detect_props_clicked(self):
        """Detect standard logger properties for selected file format."""

        logger_id = self.loggerID.text()
        file_format = self.fileFormat.currentText()
        logger_path = self.loggerPath.toPlainText()

        # TODO: Add Azure support
        if not os.path.exists(logger_path):
            msg = "Logger path does not exist. Set a logger path first."
            return QtWidgets.QMessageBox.information(
                self, "Detect Logger Properties", msg
            )

        # Create a test logger object to assign properties since we do not want to
        # assign them to the control object until the dialog OK button is clicked
        test_logger = LoggerProperties(logger_id)
        test_logger.logger_path = logger_path

        try:
            # Detect logger properties from file and assign to test logger object
            if file_format == "Custom":
                # Set current file format properties in the dialog
                test_logger.file_format = "Custom"
                test_logger.file_ext = self.fileExt.text()
                test_logger.file_delimiter = delims_gui_to_logger[
                    self.fileDelimiter.currentText()
                ]
                test_logger.num_headers = int(self.numHeaderRows.text())
                test_logger.channel_header_row = int(self.channelHeaderRow.text())
                test_logger.units_header_row = int(self.unitsHeaderRow.text())
            elif file_format == "Fugro-csv":
                test_logger = set_fugro_csv_file_format(test_logger)
                test_logger = detect_fugro_logger_properties(test_logger)
            elif file_format == "Pulse-acc":
                test_logger = set_pulse_acc_file_format(test_logger)
                test_logger = detect_pulse_logger_properties(test_logger)
            elif file_format == "2HPS2-acc":
                test_logger = set_2hps2_acc_file_format(test_logger)
                test_logger = detect_2hps2_logger_properties(test_logger)

            # Set detected file properties to dialog
            self._set_detected_file_props_to_dialog(test_logger)
        except LoggerError as e:
            self.warning(str(e))
            logging.exception(e)
        except FileNotFoundError as e:
            self.warning(str(e))
            logging.exception(e)
        except Exception as e:
            msg = "Unexpected error detecting logger file properties"
            self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def on_ok_clicked(self):
        """Assign logger properties to the control object and update the dashboard."""

        if not self.parent:
            return

        try:
            self.logger = self._set_control_data()

            try:
                self.logger.get_filenames()
            except Exception as e:
                self.warning(str(e))
                logging.exception(e)

            self._detect_header()
            self.parent.set_logger_dashboard(self.logger)
            self.parent.parent.update_logger_id_list(
                self.logger.logger_id, self.logger_idx
            )
            self.parent.parent.set_logger_columns_list(self.logger)

            # Set the process start/end labels in the Screening dashboard that pertain to the logger
            file_timestamp_embedded = self.logger.file_timestamp_embedded
            self.parent.parent.screeningTab.set_process_date_labels(
                file_timestamp_embedded
            )

            # Update file list in raw data module if required
            self.parent.parent.parent.rawDataModule.map_logger_props_to_dataset(
                self.logger_idx
            )
        except Exception as e:
            msg = "Unexpected error assigning logger properties"
            self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def _set_detected_file_props_to_dialog(self, test_logger):
        """
        Set the following detected (if found) logger properties to the edit dialog:
            sampling frequency
            timestamp format (user style format string)
            expected number of columns
            expected logging duration
        """

        # Set detected logger properties
        if test_logger.freq != 0:
            self.loggingFreq.setText(str(test_logger.freq))
        if test_logger.timestamp_format != "":
            self.dataTimestampFormat.setText(test_logger.timestamp_format)
        if test_logger.num_columns != 0:
            self.numColumns.setText(str(test_logger.num_columns))
        if test_logger.duration != 0:
            self.loggingDuration.setText(str(test_logger.duration))

    def _set_control_data(self):
        """Assign values to the specific logger attribute of the control object."""

        # Retrieve control logger to map confirmed settings to
        logger = self.control.loggers[self.logger_idx]

        # Map Azure account settings (if any) to logger
        if self.azureCloudRadio.isChecked():
            logger.data_on_azure = True
            logger.azure_account_name = self.control.azure_account_name
            logger.azure_account_key = self.control.azure_account_key
        else:
            logger.data_on_azure = False

        # Assign form values to control logger object
        logger.logger_id = self.loggerID.text()
        logger.logger_path = self.loggerPath.toPlainText()
        logger.file_format = self.fileFormat.currentText()

        if self.fileTimestampEmbeddedChkBox.isChecked():
            logger.file_timestamp_embedded = True
        else:
            logger.file_timestamp_embedded = False

        logger.file_timestamp_format = self.fileTimestampFormat.text()
        logger.first_col_data = self.firstColData.currentText()
        logger.file_ext = self.fileExt.text()
        logger.file_delimiter = delims_gui_to_logger[self.fileDelimiter.currentText()]
        logger.num_headers = int(self.numHeaderRows.text())
        logger.channel_header_row = int(self.channelHeaderRow.text())
        logger.units_header_row = int(self.unitsHeaderRow.text())
        logger.timestamp_format = self.dataTimestampFormat.text()

        # Get datetime format string by converting user input timestamp format
        logger.datetime_format = get_datetime_format(logger.timestamp_format)
        logger.num_columns = int(self.numColumns.text())
        logger.freq = float(self.loggingFreq.text())

        if float(self.loggingDuration.text()) < 0:
            msg = "Logging duration must be positive."
            QtWidgets.QMessageBox.information(
                self, "Invalid Logging Duration Input", msg
            )
        else:
            logger.duration = float(self.loggingDuration.text())

        # If file format is Custom, enforce stats/spectral sample length equal to the logger duration
        if logger.file_format == "Custom" and logger.first_col_data == "Time Step":
            logger.enforce_max_duration = True
            logger.stats_interval = logger.duration
            logger.spect_interval = logger.duration
        else:
            logger.enforce_max_duration = False

        # If stats or spectral sample length is zero set to logger duration and update screening tab
        if logger.stats_interval == 0:
            logger.stats_interval = logger.duration
            self.parent.parent.screeningTab.statsInterval.setText(
                str(logger.stats_interval)
            )
        if logger.spect_interval == 0:
            logger.spect_interval = logger.duration
            self.parent.parent.screeningTab.spectInterval.setText(
                str(logger.spect_interval)
            )

        return logger

    def _detect_header(self):
        """Store all channel and units names from a test file, if present. Header info will then be set in the gui."""

        try:
            self.logger.get_all_columns()
        except Exception as e:
            msg = "Unexpected error detecting logger file properties"
            self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def warn_info(self, msg):
        print(f"Warning: {msg}")
        return QtWidgets.QMessageBox.information(self, "Warning", msg)

    def warning(self, msg):
        print(f"Warning: {msg}")
        return QtWidgets.QMessageBox.warning(self, "Warning", msg)

    def error(self, msg):
        print(f"Error: {msg}")
        return QtWidgets.QMessageBox.critical(self, "Error", msg)


class SeascatterTab(QtWidgets.QWidget):
    """Tab to display transfer functions settings."""

    def __init__(self, parent=None):
        super(SeascatterTab, self).__init__(parent)

        self.parent = parent
        self.control = Control()
        self.scatter = Seascatter()
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # WIDGETS
        self.editButton = QtWidgets.QPushButton("Edit Data...")
        self.editButton.setShortcut("Ctrl+E")
        self.editButton.setToolTip("Ctrl+E")
        self.logger = QtWidgets.QLabel("-")
        self.hsCol = QtWidgets.QLabel("-")
        self.tpCol = QtWidgets.QLabel("-")

        # CONTAINERS
        self.detailsGroup = QtWidgets.QGroupBox("Sea Scatter Data Details")
        self.detailsGroup.setMinimumWidth(500)
        self.form = QtWidgets.QFormLayout(self.detailsGroup)
        self.form.addRow(
            QtWidgets.QLabel("Logger containing metocean data:"), self.logger
        )
        self.form.addRow(
            QtWidgets.QLabel("Significant wave height column:"), self.hsCol
        )
        self.form.addRow(
            QtWidgets.QLabel("Significant wave period column:"), self.tpCol
        )

        # LAYOUT
        self.layout1 = QtWidgets.QVBoxLayout()
        self.layout1.addWidget(
            self.editButton, stretch=0, alignment=QtCore.Qt.AlignLeft
        )
        self.layout1.addWidget(self.detailsGroup)
        self.layout1.addStretch()

        self.layout2 = QtWidgets.QHBoxLayout(self)
        self.layout2.addLayout(self.layout1)
        self.layout2.addStretch()

    def _connect_signals(self):
        self.editButton.clicked.connect(self.on_edit_clicked)

    def on_edit_clicked(self):
        """Show edit sea scatter settings dialog."""

        editInfo = EditSeascatterDialog(self, self.control, self.scatter)
        editInfo._set_dialog_data()
        editInfo.show()

    def set_scatter_dashboard(self):
        """Set config tab sea scatter setup."""

        self.logger.setText(self.scatter.metocean_logger)
        self.hsCol.setText(str(self.scatter.hs_col))
        self.tpCol.setText(str(self.scatter.tp_col))

    def clear_dashboard(self):
        """Initialise all values in sea scatter setup dashboard."""

        self.logger.setText("-")
        self.hsCol.setText("-")
        self.tpCol.setText("-")


class EditSeascatterDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, control=Control(), scatter=Seascatter()):
        super(EditSeascatterDialog, self).__init__(parent)

        self.parent = parent
        self.cols = []
        self.control = control
        self.scatter = scatter
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setWindowTitle("Edit Sea Scatter Settings")

        # WIDGETS
        self.loggerCombo = QtWidgets.QComboBox()
        self.hsColCombo = QtWidgets.QComboBox()
        msg = "Select the Hs column number that was set up in the screening tab."
        self.hsColCombo.setToolTip(msg)
        self.tpColCombo = QtWidgets.QComboBox()
        msg = "Select the Tp column number that was set up in the screening tab."
        self.tpColCombo.setToolTip(msg)

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        # CONTAINERS
        self.detailsGroup = QtWidgets.QGroupBox("Define Metocean Logger Details")
        self.form = QtWidgets.QFormLayout(self.detailsGroup)
        self.form.addRow(
            QtWidgets.QLabel("Logger containing metocean data:"), self.loggerCombo
        )
        self.form.addRow(
            QtWidgets.QLabel("Significant wave height column:"), self.hsColCombo
        )
        self.form.addRow(
            QtWidgets.QLabel("Significant wave period column:"), self.tpColCombo
        )

        # LAYOUT
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.detailsGroup)
        self.layout.addStretch()
        self.layout.addWidget(self.buttonBox)

    def _connect_signals(self):
        self.loggerCombo.currentIndexChanged.connect(self.on_logger_combo_changed)
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def _set_dialog_data(self):
        self.loggerCombo.clear()

        logger_ids = self.control.logger_ids
        if logger_ids:
            self.loggerCombo.addItems(logger_ids)

            logger = self.scatter.metocean_logger
            hs_col = self.scatter.hs_col
            tp_col = self.scatter.tp_col

            try:
                self.loggerCombo.setCurrentText(logger)
                self.hsColCombo.setCurrentText(str(hs_col))
                self.tpColCombo.setCurrentText(str(tp_col))
            except:
                pass

    def on_logger_combo_changed(self):
        i = self.loggerCombo.currentIndex()
        if i == -1:
            return

        self.cols = self.control.loggers[i].cols_to_process
        self.hsColCombo.clear()
        self.hsColCombo.addItems(map(str, self.cols))
        self.tpColCombo.clear()
        self.tpColCombo.addItems(map(str, self.cols))

    def on_ok_clicked(self):
        """Store time traces paths in transfer functions class."""

        if not self.parent:
            return

        self._set_seascatter_data()
        self.parent.set_scatter_dashboard()

    def _set_seascatter_data(self):
        """Assign values to the transfer functions object."""

        self.scatter.metocean_logger = self.loggerCombo.currentText()
        self.scatter.hs_col = int(self.hsColCombo.currentText())
        self.scatter.tp_col = int(self.tpColCombo.currentText())

        # Store the list index of the selected columns, which is the info actually needed to retrieve the stats data
        self.scatter.hs_col_idx = self.cols.index(self.scatter.hs_col)
        self.scatter.tp_col_idx = self.cols.index(self.scatter.tp_col)

    @pyqtSlot(str)
    def warning(self, msg):
        print(f"Warning: {msg}")
        return QtWidgets.QMessageBox.information(self, "Warning", msg)


class TransferFunctionsTab(QtWidgets.QWidget):
    """Tab to display transfer functions settings."""

    def __init__(self, parent=None):
        super(TransferFunctionsTab, self).__init__(parent)

        self.parent = parent
        self.tf = TransferFunctions()
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # WIDGETS
        self.editButton = QtWidgets.QPushButton("Edit Data...")
        self.editButton.setShortcut("Ctrl+E")
        self.editButton.setToolTip("Ctrl+E")
        self.loggerDispPath = QtWidgets.QLabel("-")
        self.loggerRotPath = QtWidgets.QLabel("-")
        self.locBMPath = QtWidgets.QLabel("-")
        self.numLoggers = QtWidgets.QLabel("-")
        self.numLocs = QtWidgets.QLabel("-")
        self.numSeastates = QtWidgets.QLabel("-")
        self.loggerNames = QtWidgets.QLabel("-")
        self.locNames = QtWidgets.QLabel("-")
        self.percOcc = QtWidgets.QLabel("-")

        # CONTAINERS
        self.pathsGroup = QtWidgets.QGroupBox("FEA Time Series Locations")
        self.pathsGroup.setMinimumWidth(500)
        self.form1 = QtWidgets.QFormLayout(self.pathsGroup)
        self.form1.addRow(
            QtWidgets.QLabel("Logger displacements directory:"), self.loggerDispPath
        )
        self.form1.addRow(
            QtWidgets.QLabel("Logger rotations directory:"), self.loggerRotPath
        )
        self.form1.addRow(
            QtWidgets.QLabel("Location bending moments directory:"), self.locBMPath
        )

        self.detailsGroup = QtWidgets.QGroupBox("FEA Details")
        self.form2 = QtWidgets.QFormLayout(self.detailsGroup)
        self.form2.addRow(
            QtWidgets.QLabel("Number of FEA loggers detected:"), self.numLoggers
        )
        self.form2.addRow(
            QtWidgets.QLabel("Number of FEA locations detected:"), self.numLocs
        )
        self.form2.addRow(
            QtWidgets.QLabel("Number of FEA sea states detected:"), self.numSeastates
        )

        self.group1 = QtWidgets.QGroupBox("Logger Names")
        self.vbox1 = QtWidgets.QVBoxLayout(self.group1)
        self.vbox1.addWidget(self.loggerNames, alignment=QtCore.Qt.AlignTop)

        self.group2 = QtWidgets.QGroupBox("Location Names")
        self.vbox2 = QtWidgets.QVBoxLayout(self.group2)
        self.vbox2.addWidget(self.locNames, alignment=QtCore.Qt.AlignTop)

        self.group3 = QtWidgets.QGroupBox("Sea State Percentage Occurrences")
        self.vbox3 = QtWidgets.QVBoxLayout(self.group3)
        self.vbox3.addWidget(self.percOcc, alignment=QtCore.Qt.AlignTop)

        self.vbox = QtWidgets.QVBoxLayout()
        self.vbox.addWidget(self.detailsGroup)
        self.vbox.addWidget(self.group1)
        self.vbox.addWidget(self.group2)

        self.hbox = QtWidgets.QHBoxLayout()
        self.hbox.addLayout(self.vbox)
        self.hbox.addWidget(self.group3)

        # LAYOUT
        self.layout1 = QtWidgets.QVBoxLayout()
        self.layout1.addWidget(
            self.editButton, stretch=0, alignment=QtCore.Qt.AlignLeft
        )
        self.layout1.addWidget(self.pathsGroup)
        self.layout1.addLayout(self.hbox)
        self.layout1.addStretch()

        self.layout2 = QtWidgets.QHBoxLayout(self)
        self.layout2.addLayout(self.layout1)
        self.layout2.addStretch()

    def _connect_signals(self):
        self.editButton.clicked.connect(self.on_edit_clicked)

    def on_edit_clicked(self):
        """Show edit transfer functions settings dialog."""

        editInfo = EditTransferFunctionsDialog(self, self.tf)
        editInfo._set_dialog_data()
        editInfo.show()

    def set_tf_dashboard(self):
        """Set config tab campaign info."""

        tf = self.tf
        self.loggerDispPath.setText(tf.disp_dir)
        self.loggerRotPath.setText(tf.rot_dir)
        self.locBMPath.setText(tf.bm_dir)
        self.numLoggers.setText(str(tf.num_loggers))
        self.numLocs.setText(str(tf.num_locs))
        self.numSeastates.setText(str(tf.num_ss))
        self.loggerNames.setText("\n".join(tf.logger_names))
        self.locNames.setText("\n".join(tf.loc_names))
        self.percOcc.setText("\n".join(map(str, tf.perc_occ)))

    def clear_dashboard(self):
        """Initialise all values in transfer functions dashboard."""

        self.loggerDispPath.setText("-")
        self.loggerRotPath.setText("-")
        self.locBMPath.setText("-")
        self.numLoggers.setText("-")
        self.numLocs.setText("-")
        self.numSeastates.setText("-")
        self.loggerNames.setText("-")
        self.locNames.setText("-")
        self.percOcc.setText("-")


class EditTransferFunctionsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, tf=TransferFunctions()):
        super(EditTransferFunctionsDialog, self).__init__(parent)

        self.parent = parent
        self.tf = tf
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setWindowTitle("Edit Transfer Functions Settings")
        self.setFixedHeight(500)

        # WIDGETS
        self.loggerDispPath = QtWidgets.QPlainTextEdit()
        self.loggerDispPath.setFixedHeight(40)
        self.loggerRotPath = QtWidgets.QPlainTextEdit()
        self.loggerRotPath.setFixedHeight(40)
        self.locBMPath = QtWidgets.QPlainTextEdit()
        self.locBMPath.setFixedHeight(40)
        self.setDispPathButton = QtWidgets.QPushButton("Browse...")
        self.setRotPathButton = QtWidgets.QPushButton("Browse...")
        self.setBMPathButton = QtWidgets.QPushButton("Browse...")
        self.detectButton = QtWidgets.QPushButton("&Detect Loggers and Locations")
        self.numLoggers = QtWidgets.QLabel("-")
        self.numLocs = QtWidgets.QLabel("-")
        self.numSeastates = QtWidgets.QLabel("-")
        self.loggerNames = QtWidgets.QPlainTextEdit()
        self.locNames = QtWidgets.QPlainTextEdit()
        self.percOcc = QtWidgets.QPlainTextEdit()
        self.percOcc.setFixedWidth(80)
        self.percOcc.setToolTip(
            "Optional: To calculate a weighted-average transfer function per location,\n"
            "input a list of sea state percentage occurrence values, e.g.\n"
            "19.040\n"
            "10.134\n"
            "20.049\n"
            "17.022\n"
            "14.644\n"
            "10.374\n"
            "5.448\n"
            "3.289\n"
        )
        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        # CONTAINERS
        self.pathsGroup = QtWidgets.QGroupBox("FEA Time Series Locations")
        self.grid = QtWidgets.QGridLayout(self.pathsGroup)
        self.grid.addWidget(
            QtWidgets.QLabel("Logger displacements directory:"),
            0,
            0,
            alignment=QtCore.Qt.AlignTop,
        )
        self.grid.addWidget(
            QtWidgets.QLabel("Logger rotations directory:"),
            1,
            0,
            alignment=QtCore.Qt.AlignTop,
        )
        self.grid.addWidget(
            QtWidgets.QLabel("Location bending moments directory:"),
            2,
            0,
            alignment=QtCore.Qt.AlignTop,
        )
        self.grid.addWidget(self.loggerDispPath, 0, 1)
        self.grid.addWidget(self.loggerRotPath, 1, 1)
        self.grid.addWidget(self.locBMPath, 2, 1)
        self.grid.addWidget(self.setDispPathButton, 0, 2, alignment=QtCore.Qt.AlignTop)
        self.grid.addWidget(self.setRotPathButton, 1, 2, alignment=QtCore.Qt.AlignTop)
        self.grid.addWidget(self.setBMPathButton, 2, 2, alignment=QtCore.Qt.AlignTop)

        self.detailsGroup = QtWidgets.QGroupBox("FEA Details")
        self.form = QtWidgets.QFormLayout(self.detailsGroup)
        self.form.addRow(
            QtWidgets.QLabel("Number of FEA loggers detected:"), self.numLoggers
        )
        self.form.addRow(
            QtWidgets.QLabel("Number of FEA locations detected:"), self.numLocs
        )
        self.form.addRow(
            QtWidgets.QLabel("Number of FEA sea states detected:"), self.numSeastates
        )

        self.vbox1 = QtWidgets.QVBoxLayout()
        self.vbox1.addWidget(QtWidgets.QLabel("Loggers Time Series"))
        self.vbox1.addWidget(self.loggerNames)
        self.vbox1.addWidget(QtWidgets.QLabel("Locations Time Series"))
        self.vbox1.addWidget(self.locNames)

        self.vbox2 = QtWidgets.QVBoxLayout()
        self.vbox2.addWidget(QtWidgets.QLabel("Sea State Percentage Occurrences"))
        self.vbox2.addWidget(self.percOcc)

        self.hbox = QtWidgets.QHBoxLayout()
        self.hbox.addLayout(self.vbox1)
        self.hbox.addLayout(self.vbox2)
        self.hbox.addStretch()
        self.hbox.addWidget(self.buttonBox, alignment=QtCore.Qt.AlignBottom)

        # LAYOUT
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.pathsGroup)
        self.layout.addWidget(
            self.detectButton, stretch=0, alignment=QtCore.Qt.AlignLeft
        )
        self.layout.addWidget(self.detailsGroup)
        self.layout.addLayout(self.hbox)

    def _connect_signals(self):
        self.setDispPathButton.clicked.connect(self.on_set_disp_path_clicked)
        self.setRotPathButton.clicked.connect(self.on_set_rot_path_clicked)
        self.setBMPathButton.clicked.connect(self.on_set_bm_path_clicked)
        self.detectButton.clicked.connect(self.on_detect_clicked)
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        # Connect warning signal to warning message box
        try:
            # Disconnect any existing connection to prevent repeated triggerings
            self.tf.signal_warning.disconnect()
        except:
            pass
        self.tf.signal_warning.connect(self.warning)

    def _set_dialog_data(self):
        self.loggerDispPath.setPlainText(self.tf.disp_dir)
        self.loggerRotPath.setPlainText(self.tf.rot_dir)
        self.locBMPath.setPlainText(self.tf.bm_dir)
        self.numLoggers.setText(str(self.tf.num_loggers))
        self.numLocs.setText(str(self.tf.num_locs))
        self.numSeastates.setText(str(self.tf.num_ss))

        # Convert list items to strings separated by newlines
        self.loggerNames.setPlainText("\n".join(self.tf.logger_names))
        self.locNames.setPlainText("\n".join(self.tf.loc_names))
        self.percOcc.setPlainText("\n".join(list(map(str, self.tf.perc_occ))))

    def on_set_disp_path_clicked(self):
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Logger Displacements Folder"
        )

        if dir_path:
            self.loggerDispPath.setPlainText(dir_path)

    def on_set_rot_path_clicked(self):
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Logger Rotations Folder"
        )

        if dir_path:
            self.loggerRotPath.setPlainText(dir_path)

    def on_set_bm_path_clicked(self):
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Location Bending Moments Folder"
        )

        if dir_path:
            self.locBMPath.setPlainText(dir_path)

    def on_ok_clicked(self):
        """Store time traces paths in transfer functions class."""

        if not self.parent:
            return

        self._set_tf_data()
        self.parent.set_tf_dashboard()

    def _set_tf_data(self):
        """Assign values to the transfer functions object."""

        self.tf.disp_dir = self.loggerDispPath.toPlainText()
        self.tf.rot_dir = self.loggerRotPath.toPlainText()
        self.tf.bm_dir = self.locBMPath.toPlainText()

        try:
            self.tf.num_loggers = int(self.numLoggers.text())
        except:
            self.tf.num_loggers = 0

        try:
            self.tf.num_locs = int(self.numLocs.text())
        except:
            self.tf.num_locs = 0

        try:
            self.tf.num_ss = int(self.numSeastates.text())
        except:
            self.tf.num_ss = 0

        # Convert logger and location names to lists
        loggers = [i.strip() for i in self.loggerNames.toPlainText().split("\n")]
        locs = [i.strip() for i in self.locNames.toPlainText().split("\n")]

        # Handle for blank inputs
        if loggers[0] == "":
            loggers = []
        if locs[0] == "":
            locs = []

        self.tf.logger_names = loggers
        self.tf.loc_names = locs

        # Convert percentage occurrences to numeric list
        perc_occ = self.percOcc.toPlainText()
        if perc_occ:
            try:
                # Convert values to float
                self.tf.perc_occ = list(
                    map(float, self.percOcc.toPlainText().split("\n"))
                )
            except ValueError as e:
                msg = "Percentage occurrences must be numeric."
                QtWidgets.QMessageBox.information(
                    self, "Invalid Percentage Occurrences Input", msg
                )
                logging.exception(e)
        else:
            self.tf.perc_occ = []

    def on_detect_clicked(self):
        """
        Analyse FEA time series files to detect the number of loggers, locations and sea states processed,
        and the logger and location names.
        """

        self.tf.get_files()

        # Check files exist
        num_ss = self.tf.get_number_of_seastates()
        if num_ss == 0:
            return

        # Get number of loggers from displacement time series
        df = self.tf.read_2httrace_csv(self.tf.disp_files[0])
        num_loggers = len(df.columns)
        loggers = df.columns.tolist()

        # Get number of locations from bending moment time series
        df = self.tf.read_2httrace_csv(self.tf.bm_files[0])
        num_locs = len(df.columns)
        locs = df.columns.tolist()

        # Data munging on logger and location names
        loggers = self.tf.munge_logger_cols(loggers)
        locs = self.tf.munge_location_cols(locs)

        # Populate dialog with detected properties
        self.numLoggers.setText(str(num_loggers))
        self.numLocs.setText(str(num_locs))
        self.numSeastates.setText(str(num_ss))

        # Convert list items to strings separated by newlines
        self.loggerNames.setPlainText("\n".join(loggers))
        self.locNames.setPlainText("\n".join(locs))

    @pyqtSlot(str)
    def warning(self, msg):
        print(f"Warning: {msg}")
        return QtWidgets.QMessageBox.information(self, "Warning", msg)


class AzureAccountSetupDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, account_name="", account_key=""):
        super(AzureAccountSetupDialog, self).__init__(parent)

        # Default settings
        if account_name == "":
            account_name = "agl2hpocdatalab1store"
        if account_key == "":
            account_key = "25ZKbPuwSrzqS3Tv8DVeF58x0cy3rMA8VQPKHj3wRZoiWKTPoyllqFOL0EnEy9Dq+poASjV9nFoSIIC7/sBt6Q=="

        self.parent = parent
        self.account_name = account_name
        self.account_key = account_key
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setWindowTitle("Connect to Microsoft Azure Cloud Storage Account")
        self.setFixedWidth(650)

        # WIDGETS
        self.accountName = QtWidgets.QLineEdit(self.account_name)
        self.accountName.setFixedWidth(200)
        self.accountKey = QtWidgets.QLineEdit(self.account_key)
        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.testButton = self.buttonBox.addButton(
            "&Test Connection", QtWidgets.QDialogButtonBox.ResetRole
        )

        # CONTAINERS
        self.form = QtWidgets.QFormLayout()
        self.form.addRow(QtWidgets.QLabel("Account name:"), self.accountName)
        self.form.addRow(QtWidgets.QLabel("Account key:"), self.accountKey)

        # LAYOUT
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addLayout(self.form)
        self.layout.addWidget(self.buttonBox)

    def _connect_signals(self):
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.testButton.clicked.connect(self.on_test_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def on_test_clicked(self):
        account_name = self.accountName.text()
        account_key = self.accountKey.text()

        if account_name == "" or account_key == "":
            msg = "Both account name and account key must be input."
            return QtWidgets.QMessageBox.warning(
                self, "Test Connection to Azure Cloud Storage Account", msg
            )

        try:
            check_azure_account_exists(account_name, account_key)
            msg = f"Connected successfully to Azure Cloud Storage account: {account_name}."
            return QtWidgets.QMessageBox.information(
                self, "Test Connection to Azure Cloud Storage Account", msg
            )
        except Exception:
            msg = "Could not connect to Azure Cloud Storage account. Check account name and key are correct."
            print(f"Error: {msg}")
            return QtWidgets.QMessageBox.critical(self, "Error", msg)

    def on_ok_clicked(self):
        """Store Azure settings in control object."""

        try:
            self.parent.control.azure_account_name = self.accountName.text()
            self.parent.control.azure_account_key = self.accountKey.text()
        except:
            pass


if __name__ == "__main__":
    # For testing widget layout
    app = QtWidgets.QApplication(sys.argv)
    # win = ConfigModule()
    # win = CampaignInfoTab()
    # win = EditCampaignInfoDialog()
    win = LoggerPropertiesTab()
    # win = EditLoggerPropertiesDialog()
    # win = SeascatterTab()
    # win = EditSeascatterDialog()
    # win = TransferFunctionsTab()
    # win = EditTransferFunctionsDialog()
    # win = AzureAccountSetupDialog()
    win.show()
    app.exit(app.exec_())
