import os
import sys
import logging
import json

from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
from core.control_file import ControlFile, InputError
from core.logger_properties import LoggerProperties
from core.fugro_csv import fugro_file_format


class ProjectConfig:
    def __init__(self):
        # Config data dictionary to be written to a json file
        self.data = {}
        self.file_name = ''

    def load_config(self, file_name):
        """Load project config json file."""

        with open(file_name, encoding='utf-8') as f:
            self.data = json.load(f)

        # Store file name and set directory to project root
        fpath, self.file_name = os.path.split(file_name)
        os.chdir(fpath)

    def get_config_section(self, key):
        """Return requested subsection of the config dictionary."""

        if key in self.data.keys():
            return self.data[key].keys(), self.data[key]
        else:
            raise KeyError(key)

    def add_general_data(self, key, campaign_data):
        """Add project and campaign details."""

        d = dict()
        d['project_number'] = campaign_data.proj_num
        d['project_name'] = campaign_data.proj_name
        d['campaign_name'] = campaign_data.campaign_name
        d['project_location'] = campaign_data.proj_path

        self.add_data(key, d)

    def add_logger_props(self, key, loggers_data):
        """Add properties of all loggers."""

        d = dict()
        for logger in loggers_data:
            dict_props = logger.props_to_dict()
            d['loggers'][dict_props.logger_id] = dict_props

        self.add_data(key, d)

    def add_data(self, key, data):
        self.data[key] = data

    def export_config(self, proj_num, proj_name):
        """Export project configuration data as json file."""

        proj_name = '_'.join(proj_name.split(' '))
        self.file_name = '_'.join((proj_num, proj_name, 'Config.json'))

        # Save as json file
        # Prevents ascii characters in file. Indent gives nicer layout instead of one long line string
        with open(self.file_name, 'w', encoding='utf-8') as f:
            f.write(json.dumps(self.data, indent=4, sort_keys=False, ensure_ascii=False))


class ProjectConfigModule(QtWidgets.QWidget):
    """Main screen containing project configuration setup."""

    def __init__(self, parent=None):
        super(ProjectConfigModule, self).__init__(parent)

        self.parent = parent

        # Json config class - hold config data dictionary
        self.config = ProjectConfig()
        self.control = ControlFile()

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        layout = QtWidgets.QGridLayout(self)

        # vbox1 =QtWidgets.QVBoxLayout()

        # Buttons
        self.loadConfigButton = QtWidgets.QPushButton('&Load')
        self.saveConfigButton = QtWidgets.QPushButton('&Save')
        self.newProjButton = QtWidgets.QPushButton('&New Project')

        # Config tab widgets
        self.tabWidget = QtWidgets.QTabWidget()
        self.generalTab = GeneralData(self)
        self.loggerPropsTab = LoggerPropertiesGroup(self)
        self.tabWidget.addTab(self.generalTab, 'General Data')
        self.tabWidget.addTab(self.loggerPropsTab, 'Logger and Screening Settings')

        # Layout for config file load/save buttons
        configButtonsWidget = QtWidgets.QWidget()
        hbox = QtWidgets.QHBoxLayout(configButtonsWidget)
        hbox.addWidget(QtWidgets.QLabel('Config File:'))
        hbox.addWidget(self.loadConfigButton)
        hbox.addWidget(self.saveConfigButton)

        # Run analysis group
        runWidget = QtWidgets.QWidget()
        vbox1 = QtWidgets.QVBoxLayout(runWidget)
        runGroup = QtWidgets.QGroupBox('Selected Analysis')
        # policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        # runGroup.setSizePolicy(policy)
        vbox2 = QtWidgets.QVBoxLayout(runGroup)
        self.statsChkbox = QtWidgets.QCheckBox('Statistical analysis')
        self.spectralChkbox = QtWidgets.QCheckBox('Spectral analysis')
        vbox2.addWidget(self.statsChkbox)
        vbox2.addWidget(self.spectralChkbox)

        self.processButton = QtWidgets.QPushButton('Process')
        vbox1.addWidget(runGroup)
        vbox1.addWidget(self.processButton)

        # Main layout
        layout.addWidget(configButtonsWidget, 0, 0, QtCore.Qt.AlignLeft)
        layout.addWidget(self.tabWidget, 1, 0)
        layout.addWidget(self.newProjButton, 2, 0, QtCore.Qt.AlignLeft)
        layout.addWidget(runWidget, 0, 1, 2, 1, QtCore.Qt.AlignTop)

    def connect_signals(self):
        self.loadConfigButton.clicked.connect(self.load_config_file)
        self.saveConfigButton.clicked.connect(self.save_config_to_json_file)
        self.newProjButton.clicked.connect(self.create_new_project)

    def create_new_project(self):
        """Create new project config file."""
        pass

    def load_config_file(self):
        """Load config json file."""

        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                                                             caption='Open Config File',
                                                             filter='Config Files (*.json)',
                                                             )

        if file_name:
            try:
                # Read json file and store data in config object
                self.config.load_config(file_name)

                # Assign config data to project dashboard
                self.set_data_to_config_dashboard()
            except InputError as e:
                self.parent.error(str(e))
            except KeyError as e:
                msg = f'{e} key not found in config file'
                self.parent.error(msg)
            except Exception as e:
                msg = 'Unexpected error loading config file'
                self.parent.error(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
                logging.exception(str(e))

    def set_data_to_config_dashboard(self):

        # Assign general data to gui and control object
        keys, data = self.config.get_config_section('general')
        self.map_general_data_to_gui(data)
        self.map_general_data_to_control(data)

    def map_general_data_to_gui(self, data):

        # Assign data to tab attributes
        tab = self.generalTab

        try:
            tab.proj_num = data['project_number']
            tab.proj_name = data['project_name']
            tab.campaign_name = data['campaign_name']
            tab.proj_path = data['project_location']

            # Set config file name in gui (doesn't have an attribute)
            tab.configFileName.setText(self.config.file_name)
        except:
            raise

        # Assign attribute values to gui widgets
        tab.set_values()

    def map_general_data_to_control(self, data):
        """Assign general data to control object."""

        # Assign to control object
        self.control.project_num = data['project_number']
        self.control.project_name = data['project_name']
        self.control.campaign_name = data['campaign_name']
        self.control.output_folder = os.path.join(data['project_location'], 'Output')

    def save_config_to_json_file(self):
        """Save project configuration settings as a dictionary to a JSON file."""

        if self.generalTab.proj_num == '':
            self.parent.error('Project number required to create project config file.')
            return

        if self.generalTab.proj_name == '':
            self.parent.error('Project name required to create project config file.')
            return

        # Compile configuration data into a dictionary and save as a json file
        config = ProjectConfig()
        config.add_general_data(key='general', campaign_data=self.generalTab)
        config.add_logger_props(key='loggers', loggers_data=self.loggerPropsTab.loggers)
        config.export_config(proj_num=self.generalTab.proj_num,
                             proj_name=self.generalTab.proj_name,
                             )

        # Check file created
        file = Path(config.file_name)
        if file.is_file():
            # Write to gui and inform user
            self.generalTab.configFileName.setText(config.file_name)
            msg = f'Project config settings saved to {config.file_name}'
            QtWidgets.QMessageBox.information(self, 'Save Project Config', msg, QtWidgets.QMessageBox.Ok)


class GeneralData(QtWidgets.QWidget):
    """GUI screen to control project setup."""

    def __init__(self, parent=None):
        super(GeneralData, self).__init__(parent)

        self.parent = parent
        self.edit = EditGeneralData(self)

        self.proj_num = ''
        self.proj_name = ''
        self.campaign_name = ''
        self.proj_path = ''

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setFixedSize(700, 300)
        layout = QtWidgets.QVBoxLayout(self)

        # Form
        formWidget = QtWidgets.QGroupBox('Project and Campaign Details')
        form = QtWidgets.QFormLayout(formWidget)
        self.projNum = QtWidgets.QLabel('Not set')
        self.projNum.setFixedWidth(40)
        self.projName = QtWidgets.QLabel('Not set')
        self.campaignName = QtWidgets.QLabel('Not set')
        self.projPath = QtWidgets.QLabel('Not set')
        self.projPath.setWordWrap(True)
        self.configFileName = QtWidgets.QLabel('Not set')

        # Place widgets
        form.addRow(QtWidgets.QLabel('Project number:'), self.projNum)
        form.addRow(QtWidgets.QLabel('Project name:'), self.projName)
        form.addRow(QtWidgets.QLabel('Campaign name:'), self.campaignName)
        form.addRow(QtWidgets.QLabel('Project location:'), self.projPath)
        form.addRow(QtWidgets.QLabel('Config file name:'), self.configFileName)

        # Edit values button
        self.editButton = QtWidgets.QPushButton('Edit Values')
        self.editButton.setShortcut('Ctrl+E')
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.editButton.setSizePolicy(policy)

        layout.addWidget(formWidget)
        layout.addWidget(self.editButton)  # , stretch=0, alignment=QtCore.Qt.AlignRight)

        # TABLE INPUT TEST - Could consider trying to use OrcaFlex style table input cells
        # self.tableInput = QtWidgets.QTableWidget()
        # self.tableInput.setFixedSize(60, 25)
        # self.tableInput.setRowCount(1)
        # self.tableInput.setColumnCount(1)
        # self.tableInput.horizontalHeader().hide()
        # self.tableInput.verticalHeader().hide()
        # form.addRow(QtWidgets.QLabel('table value:'), self.tableInput)
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

    def connect_signals(self):
        self.editButton.clicked.connect(self.show_edit_window)

    def show_edit_window(self):
        self.edit.set_form_values()
        self.edit.show()

    def set_values(self):
        """Assign values to parent class attributes."""

        self.projNum.setText(self.proj_num)
        self.projName.setText(self.proj_name)
        self.campaignName.setText(self.campaign_name)
        self.projPath.setText(self.proj_path)


class EditGeneralData(QtWidgets.QDialog):
    """Edit window for project and campaign data."""

    def __init__(self, parent=None):
        super(EditGeneralData, self).__init__(parent)

        self.parent = parent
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle('Edit General Campaign Data')
        self.setFixedSize(500, 250)

        layout = QtWidgets.QVBoxLayout(self)
        formWidget = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(formWidget)
        self.projNum = QtWidgets.QLineEdit()
        self.projNum.setFixedWidth(40)
        self.projName = QtWidgets.QLineEdit()
        self.campaignName = QtWidgets.QLineEdit()
        self.projPath = QtWidgets.QLineEdit()
        self.browseButton = QtWidgets.QPushButton('Browse')
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.browseButton.setSizePolicy(policy)

        # Place widgets
        form.addRow(QtWidgets.QLabel('Project number:'), self.projNum)
        form.addRow(QtWidgets.QLabel('Project name:'), self.projName)
        form.addRow(QtWidgets.QLabel('Campaign name:'), self.campaignName)
        form.addRow(QtWidgets.QLabel('Project location:'), self.projPath)
        form.addRow(QtWidgets.QLabel(''), self.browseButton)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                    QtWidgets.QDialogButtonBox.Cancel)

        layout.addWidget(formWidget)
        layout.addWidget(self.buttonBox)

    def connect_signals(self):
        self.browseButton.clicked.connect(self.set_project_path)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.accepted.connect(self.store_form_values)
        self.buttonBox.rejected.connect(self.reject)

    def set_project_path(self):
        """Set location of project root directory."""

        file_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Project Location')

        if file_path:
            self.projPath.setText(file_path)
            os.chdir(file_path)

    def set_form_values(self):
        """Set form values with campaign data from parent widget."""

        self.projNum.setText(self.parent.proj_num)
        self.projName.setText(self.parent.proj_name)
        self.campaignName.setText(self.parent.campaign_name)
        self.projPath.setText(self.parent.proj_path)

    def store_form_values(self):
        """Assign form values to attributes."""

        # Assign values to parent class attributes
        self.parent.proj_num = self.projNum.text()
        self.parent.proj_name = self.projName.text()
        self.parent.campaign_name = self.campaignName.text()
        self.parent.proj_path = self.projPath.text()

        # Set values in config tab
        self.parent.set_form_values()


class LoggerPropertiesGroup(QtWidgets.QWidget):
    """GUI screen to control project setup."""

    def __init__(self, parent=None):
        super(LoggerPropertiesGroup, self).__init__(parent)

        self.parent = parent

        # Container for loggers
        self.loggers = []

        # Index of selected logger in combo
        self.logger_idx = 0

        # Edit logger properties dialog class
        self.editLoggerProps = EditLoggerProperties(self)
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Create widget layout."""

        layout = QtWidgets.QVBoxLayout(self)

        # Loggers setup
        loggersSetup = QtWidgets.QWidget()
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        loggersSetup.setSizePolicy(policy)
        grid = QtWidgets.QGridLayout(loggersSetup)

        # Logger list group
        addRemLoggersGroup = QtWidgets.QGroupBox('Campaign Loggers')
        addRemLoggersGroup.setFixedWidth(150)
        vbox1 = QtWidgets.QVBoxLayout(addRemLoggersGroup)
        self.addLoggerButton = QtWidgets.QPushButton('Add Logger')
        self.remLoggerButton = QtWidgets.QPushButton('Remove Logger')
        self.loggersList = QtWidgets.QListWidget()
        vbox1.addWidget(self.addLoggerButton)
        vbox1.addWidget(self.remLoggerButton)
        vbox1.addWidget(QtWidgets.QLabel('Loggers'))
        vbox1.addWidget(self.loggersList)

        # Selected logger combo
        selectedLogger = QtWidgets.QWidget()
        hbox = QtWidgets.QHBoxLayout(selectedLogger)
        self.loggerCombo = QtWidgets.QComboBox()
        self.loggerCombo.setMinimumWidth(100)
        self.loggerCombo.addItem('N/A')
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        selectedLogger.setSizePolicy(policy)
        hbox.addWidget(QtWidgets.QLabel('Selected logger:'))
        hbox.addWidget(self.loggerCombo)

        # Logger properties group
        loggerProps = QtWidgets.QGroupBox('Logger Properties')
        loggerProps.setFixedWidth(300)
        loggerForm = QtWidgets.QFormLayout(loggerProps)
        self.loggerID = QtWidgets.QLabel('N/A')
        self.fileType = QtWidgets.QLabel('N/A')
        self.loggerPath = QtWidgets.QLabel(r'C:\Users\dickinsc\PycharmProjects\DataLab\Demo Data\1. Raw Data\BOP')
        self.loggerPath.setWordWrap(True)
        self.fileTimestampFormat = QtWidgets.QLabel('N/A')
        self.dataTimestampFormat = QtWidgets.QLabel('N/A')
        self.fileExt = QtWidgets.QLabel('N/A')
        self.fileDelimiter = QtWidgets.QLabel('N/A')
        self.numHeaderRows = QtWidgets.QLabel('N/A')
        self.numColumns = QtWidgets.QLabel('N/A')
        self.channelHeaderRow = QtWidgets.QLabel('N/A')
        self.unitsHeaderRow = QtWidgets.QLabel('N/A')
        self.loggingFreq = QtWidgets.QLabel('N/A')
        self.loggingDuration = QtWidgets.QLabel('N/A')
        self.channelNames = QtWidgets.QLabel('N/A')
        self.channelUnits = QtWidgets.QLabel('N/A')

        # Place widgets
        loggerForm.addRow(QtWidgets.QLabel('Logger ID:'), self.loggerID)
        loggerForm.addRow(QtWidgets.QLabel('File type:'), self.fileType)
        loggerForm.addRow(QtWidgets.QLabel('Logger path:'), self.loggerPath)
        loggerForm.addRow(QtWidgets.QLabel('File timestamp:'), self.fileTimestampFormat)
        loggerForm.addRow(QtWidgets.QLabel('Data timestamp:'), self.dataTimestampFormat)
        loggerForm.addRow(QtWidgets.QLabel('Extension:'), self.fileExt)
        loggerForm.addRow(QtWidgets.QLabel('Delimiter:'), self.fileDelimiter)
        loggerForm.addRow(QtWidgets.QLabel('Number of header rows:'), self.numHeaderRows)
        loggerForm.addRow(QtWidgets.QLabel('Number of expected columns:'), self.numColumns)
        loggerForm.addRow(QtWidgets.QLabel('Channel header row:'), self.channelHeaderRow)
        loggerForm.addRow(QtWidgets.QLabel('Units header row:'), self.unitsHeaderRow)
        loggerForm.addRow(QtWidgets.QLabel('Logging frequency (Hz):'), self.loggingFreq)
        loggerForm.addRow(QtWidgets.QLabel('Logging duration (s):'), self.loggingDuration)
        loggerForm.addRow(QtWidgets.QLabel('Channel names:'), self.channelNames)
        loggerForm.addRow(QtWidgets.QLabel('Channel units:'), self.channelUnits)

        # Stats screening group
        statsSettings = QtWidgets.QGroupBox('Statistical Analysis Settings')
        statsSettings.setFixedWidth(300)
        statsForm = QtWidgets.QFormLayout(statsSettings)
        self.statsColumns = QtWidgets.QLabel('N/A')
        self.statsUnitConvs = QtWidgets.QLabel('N/A')
        self.statsInterval = QtWidgets.QLabel('N/A')
        self.statsStart = QtWidgets.QLabel('N/A')
        self.statsEnd = QtWidgets.QLabel('N/A')

        # Place widgets
        statsForm.addRow(QtWidgets.QLabel('Stats columns:'), self.statsColumns)
        statsForm.addRow(QtWidgets.QLabel('Stats unit conversion factors:'), self.statsUnitConvs)
        statsForm.addRow(QtWidgets.QLabel('Stats interval:'), self.statsInterval)
        statsForm.addRow(QtWidgets.QLabel('Stats start timestamp:'), self.statsStart)
        statsForm.addRow(QtWidgets.QLabel('Stats end timestamp:'), self.statsEnd)

        # Spectral screening group
        self.spectralColumns = QtWidgets.QLabel('N/A')
        self.spectralUnitConvs = QtWidgets.QLabel('N/A')
        self.spectralInterval = QtWidgets.QLabel('N/A')
        self.spectralStart = QtWidgets.QLabel('N/A')
        self.spectralEnd = QtWidgets.QLabel('N/A')

        spectralSettings = QtWidgets.QGroupBox('Spectral Analysis Settings')
        spectralSettings.setFixedWidth(300)
        spectralForm = QtWidgets.QFormLayout(spectralSettings)
        spectralForm.addRow(QtWidgets.QLabel('Stats columns:'), self.spectralColumns)
        spectralForm.addRow(QtWidgets.QLabel('Stats unit conversion factors:'), self.spectralUnitConvs)
        spectralForm.addRow(QtWidgets.QLabel('Stats interval:'), self.spectralInterval)
        spectralForm.addRow(QtWidgets.QLabel('Stats start timestamp:'), self.spectralStart)
        spectralForm.addRow(QtWidgets.QLabel('Stats end timestamp:'), self.spectralEnd)

        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.editLoggerButton = QtWidgets.QPushButton('Edit Values')
        self.editLoggerButton.setShortcut('Ctrl+1')
        self.editStatsButton = QtWidgets.QPushButton('Edit Values')
        self.editStatsButton.setShortcut('Ctrl+2')
        self.editSpectralButton = QtWidgets.QPushButton('Edit Values')
        self.editSpectralButton.setShortcut('Ctrl+3')

        # Assemble group boxes
        grid.addWidget(addRemLoggersGroup, 0, 0, 2, 1)
        grid.addWidget(selectedLogger, 0, 1, QtCore.Qt.AlignLeft)
        grid.addWidget(loggerProps, 1, 1, QtCore.Qt.AlignLeft)
        grid.addWidget(statsSettings, 1, 2, QtCore.Qt.AlignLeft)
        grid.addWidget(spectralSettings, 1, 3, QtCore.Qt.AlignLeft)
        grid.addWidget(self.editLoggerButton, 2, 1, QtCore.Qt.AlignLeft)
        grid.addWidget(self.editStatsButton, 2, 2, QtCore.Qt.AlignLeft)
        grid.addWidget(self.editSpectralButton, 2, 3, QtCore.Qt.AlignLeft)

        # Buttonbox
        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.buttonBox.addButton('Run Data Quality Checks', QtWidgets.QDialogButtonBox.AcceptRole)

        layout.addWidget(loggersSetup)
        # layout.addWidget(self.buttonBox)

    def connect_signals(self):
        self.addLoggerButton.clicked.connect(self.add_logger)
        self.remLoggerButton.clicked.connect(self.remove_logger)
        self.loggersList.itemChanged.connect(self.on_logger_item_edited)
        self.editLoggerButton.clicked.connect(self.show_edit_logger_props)

    def add_logger(self):
        """Add new logger to list. Initial logger name format is 'Logger n'."""

        n = self.loggersList.count()
        logger_id = f'Logger {n + 1}'

        item = QtWidgets.QListWidgetItem(logger_id)
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        self.loggersList.addItem(item)

        # Add logger to combo
        if self.loggerCombo.currentText() == 'N/A':
            self.loggerCombo.clear()

        self.loggerCombo.addItem(logger_id)
        self.loggerCombo.setCurrentText(logger_id)
        self.logger_idx = self.loggerCombo.currentIndex()

        # Create logger properties object
        self.loggers.append(LoggerProperties(logger_id))

        # Initialise logger properties and open logger properties edit widget
        self.init_logger_props()
        self.show_edit_logger_props()

    def remove_logger(self):
        """Remove selected logger."""

        if self.loggersList.count() == 0:
            return

        # If a logger isn't selected in the list, remove the last item
        if self.loggersList.currentItem() is None:
            i = self.loggersList.count() - 1
            logger = self.loggersList.item(i).text()
        else:
            i = self.loggersList.currentRow()
            logger = self.loggersList.currentItem().text()

        self.logger_idx = self.loggerCombo.currentIndex()

        # Confirm with user
        msg = f'Are you sure you want to remove the logger named {logger}?'
        response = QtWidgets.QMessageBox.question(self, 'Remove Logger?', msg)

        if response == QtWidgets.QMessageBox.Yes:
            self.loggersList.takeItem(i)
            self.loggerCombo.removeItem(i)

            if self.loggerCombo.count() == 0:
                self.loggerCombo.addItem('N/A')

    def on_logger_item_edited(self):
        """Update logger combobox to match logger names of list widget."""

        i = self.loggersList.currentRow()
        new_name = self.loggersList.currentItem().text()
        self.loggerCombo.setItemText(i, new_name)

    def init_logger_props(self):
        """Set initial logger properties for Fugro type upon adding a logger."""

        logger = self.loggers[self.logger_idx]

        # Assign Fugro standard logger properties
        logger = fugro_file_format(logger)

        self.set_form_values(logger)

    def show_edit_logger_props(self):
        """Open logger properties edit form."""

        # No logger added
        if self.loggersList.count() == 0:
            return

        logger = self.loggers[self.logger_idx]
        self.editLoggerProps.set_form_values(logger)
        self.editLoggerProps.show()

    def set_form_values(self, logger):
        """Set gui logger properties with logger properties from logger object."""

        self.loggerID.setText(logger.logger_id)
        self.fileType.setText(logger.file_format)
        self.fileExt.setText(logger.file_ext)
        self.fileDelimiter.setText('comma')
        self.numHeaderRows.setText(str(logger.num_headers))
        self.channelHeaderRow.setText(str(logger.channel_header_row))
        self.unitsHeaderRow.setText(str(logger.units_header_row))

        # self.loggerPath.setText(logger.logger_path)
        # self.fileTimestampFormat.setText(logger.file_timestamp_format)


class EditLoggerProperties(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(EditLoggerProperties, self).__init__(parent)

        self.parent = parent
        self.file_types = ['Fugro-csv',
                           'Pulse-acc',
                           'General-csv',
                           ]
        self.delimiters = ['comma',
                           'space',
                           ]
        self.delimiters_dict = {',': 'comma',
                                ' ': 'space',
                                }
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle('Edit Logger Properties')

        layout = QtWidgets.QVBoxLayout(self)
        # layout.addStretch()

        # Logger properties group
        loggerProps = QtWidgets.QGroupBox('Logger Properties')
        propsForm = QtWidgets.QFormLayout(loggerProps)
        self.loggerID = QtWidgets.QLineEdit()
        self.fileFormat = QtWidgets.QComboBox()
        self.fileFormat.setFixedWidth(100)
        self.fileFormat.addItems(self.file_types)
        self.loggerPath = QtWidgets.QLineEdit()
        self.setLoggerPath = QtWidgets.QPushButton('Browse Logger Path')
        self.setLoggerPath.setFixedWidth(130)
        self.fileTimstamp = QtWidgets.QLineEdit()
        self.dataTimstamp = QtWidgets.QLineEdit()
        self.fileExt = QtWidgets.QLineEdit()
        self.fileDelimiter = QtWidgets.QComboBox()
        self.fileDelimiter.setFixedWidth(60)
        self.fileDelimiter.addItems(self.delimiters)
        self.numHeaderRows = QtWidgets.QLineEdit()
        self.numColumns = QtWidgets.QLineEdit()
        self.channelHeaderRow = QtWidgets.QLineEdit()
        self.unitsHeaderRow = QtWidgets.QLineEdit()
        self.loggingFreq = QtWidgets.QLineEdit()
        self.loggingDuration = QtWidgets.QLineEdit()
        self.channelNames = QtWidgets.QLineEdit()
        self.channelUnits = QtWidgets.QLineEdit()

        # Place widgets
        propsForm.addRow(QtWidgets.QLabel('Logger ID:'), self.loggerID)
        propsForm.addRow(QtWidgets.QLabel('File format:'), self.fileFormat)
        propsForm.addRow(QtWidgets.QLabel('Logger path:'), self.loggerPath)
        propsForm.addRow(self.setLoggerPath, QtWidgets.QLabel(''))
        propsForm.addRow(QtWidgets.QLabel('File timestamp:'), self.fileTimstamp)
        propsForm.addRow(QtWidgets.QLabel('Data timestamp:'), self.dataTimstamp)
        propsForm.addRow(QtWidgets.QLabel('File extension:'), self.fileExt)
        propsForm.addRow(QtWidgets.QLabel('File delimiter:'), self.fileDelimiter)
        propsForm.addRow(QtWidgets.QLabel('Number of header rows:'), self.numHeaderRows)
        propsForm.addRow(QtWidgets.QLabel('Number of expected columns:'), self.numColumns)
        propsForm.addRow(QtWidgets.QLabel('Channel header row:'), self.channelHeaderRow)
        propsForm.addRow(QtWidgets.QLabel('Logging frequency (Hz):'), self.loggingFreq)
        propsForm.addRow(QtWidgets.QLabel('Logging duration (s):'), self.loggingDuration)
        propsForm.addRow(QtWidgets.QLabel('Channel names:'), self.channelNames)
        propsForm.addRow(QtWidgets.QLabel('Channel units:'), self.channelUnits)

        # Button box
        # self.assignButton = QtWidgets.QPushButton('Assign')
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                    QtWidgets.QDialogButtonBox.Cancel)
        # self.assignButton = QtWidgets.QPushButton('Assign')
        # self.buttons.addButton(self.assignButton, QtWidgets.QDialogButtonBox.AcceptRole)
        # self.buttons.addButton(QtWidgets.QDialogButtonBox.Cancel)

        layout.addWidget(loggerProps)
        layout.addWidget(self.buttonBox, stretch=0, alignment=QtCore.Qt.AlignRight)

    def connect_signals(self):
        self.fileFormat.currentIndexChanged.connect(self.on_file_format_change)

    def set_form_values(self, logger):
        """Assign form values with logger properties from logger object."""

        self.loggerID.setText(logger.logger_id)
        self.fileFormat.setCurrentText(logger.file_format)
        self.fileExt.setText(logger.file_ext)
        self.fileDelimiter.setCurrentText(self.delimiters_dict[logger.file_delimiter])
        self.numHeaderRows.setText(str(logger.num_headers))
        self.unitsHeaderRow.setText(str(logger.units_header_row))

    def on_file_format_change(self):
        """Set standard logger properties for selected file format."""

        # no logger added
        if self.parent.loggersList.count() == 0:
            return

        file_format = self.fileFormat.currentText()
        logger_id = self.parent.loggerCombo.currentText()
        logger_idx = self.parent.loggerCombo.currentIndex()
        logger = self.parent.loggers[logger_idx]

        if file_format == 'Fugro-csv':
            self.set_fugro_file_format(logger)
        elif file_format == 'Pulse-acc':
            pass
        else:
            pass

    def set_fugro_file_format(self, logger):
        """
        Set Fugro file format standard properties.
        :param logger: LoggerProperties object
        :return:
        """

        # Assign Fugro standard logger properties
        logger = fugro_file_format(logger)

        # Input in edit widget
        self.fileExt.setText(logger.file_ext)
        self.fileDelimiter.setCurrentText('comma')
        self.numHeaderRows.setText(str(logger.num_headers))
        self.channelHeaderRow.setText(str(logger.channel_header_row))
        self.unitsHeaderRow.setText(str(logger.units_header_row))


# class StatisticalSettings(QtWidgets.QWidget):
#     """GUI screen to control project setup."""
#
#     def __init__(self, parent=None):
#         super(StatisicalSettings, self).__init__(parent)
#
#         self.stats_columns = ''
#         self.stats_unit_convs = ''
#         self.stats_interval = ''
#         self.stats_start = ''
#         self.stats_end = ''
#
#         # Edit logger properties dialog class
#         self.init_ui()
#         self.connect_signals()
#
#     def init_ui(self):
#         """Create widget layout."""
#
#         layout = QtWidgets.QVBoxLayout(self)
#
#         self.statsColumns = QtWidgets.QLabel('N/A')
#         self.statsUnitConvs = QtWidgets.QLabel('N/A')
#         self.statsInterval = QtWidgets.QLabel('N/A')
#         self.statsStart = QtWidgets.QLabel('N/A')
#         self.statsEnd = QtWidgets.QLabel('N/A')
#
#         # Stats group
#         statParams = QtWidgets.QGroupBox('Statistical Analysis Parameters')
#         statsForm = QtWidgets.QFormLayout(statParams)
#         statsForm.addRow(QtWidgets.QLabel('Stats columns:'), self.statsColumns)
#         statsForm.addRow(QtWidgets.QLabel('Stats unit conversion factors:'), self.statsUnitConvs)
#         statsForm.addRow(QtWidgets.QLabel('Stats interval:'), self.statsInterval)
#         statsForm.addRow(QtWidgets.QLabel('Stats start timestamp:'), self.statsStart)
#         statsForm.addRow(QtWidgets.QLabel('Stats end timestamp:'), self.statsEnd)
#
#         layout.addWidget(statParams)
#
#     def connect_signals(self):
#         pass
#
#
# class SpectralSettings(QtWidgets.QWidget):
#     """GUI screen to control project setup."""
#
#     def __init__(self, parent=None):
#         super(SpectralSettings, self).__init__(parent)
#
#         self.stats_columns = ''
#         self.stats_unit_convs = ''
#         self.stats_interval = ''
#         self.stats_start = ''
#         self.stats_end = ''
#
#         # Edit logger properties dialog class
#         self.init_ui()
#         self.connect_signals()
#
#     def init_ui(self):
#         """Create widget layout."""
#
#         layout = QtWidgets.QVBoxLayout(self)
#
#         self.statsColumns = QtWidgets.QLabel('N/A')
#         self.statsUnitConvs = QtWidgets.QLabel('N/A')
#         self.statsInterval = QtWidgets.QLabel('N/A')
#         self.statsStart = QtWidgets.QLabel('N/A')
#         self.statsEnd = QtWidgets.QLabel('N/A')
#
#         spectralParams = QtWidgets.QGroupBox('Spectral Analysis Parameters')
#         spectralForm = QtWidgets.QFormLayout(spectralParams)
#         spectralForm.addRow(QtWidgets.QLabel('Stats columns:'), self.statsColumns)
#         spectralForm.addRow(QtWidgets.QLabel('Stats unit conversion factors:'), self.statsUnitConvs)
#         spectralForm.addRow(QtWidgets.QLabel('Stats interval:'), self.statsInterval)
#         spectralForm.addRow(QtWidgets.QLabel('Stats start timestamp:'), self.statsStart)
#         spectralForm.addRow(QtWidgets.QLabel('Stats end timestamp:'), self.statsEnd)
#
#         layout.addWidget(spectralParams)
#
#     def connect_signals(self):
#         pass


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # win = ProjectConfigModule()
    win = EditLoggerProperties()
    win.show()
    app.exit(app.exec_())
