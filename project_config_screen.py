import os
import sys
import logging
import json

from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
from core.control_file import ControlFile, InputError
from core.logger_properties import LoggerProperties
from core.fugro_csv import set_fugro_file_format


class ProjectConfig:
    def __init__(self):
        # Config data dictionary to be written to a json file
        self.data = {}
        self.filename = ''

    def load_config(self, file_name):
        """Load project config json file."""

        with open(file_name, encoding='utf-8') as f:
            self.data = json.load(f)

        # Store file name and set directory to project root
        fpath, self.filename = os.path.split(file_name)
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
        d['project_number'] = campaign_data.project_num
        d['project_name'] = campaign_data.project_name
        d['campaign_name'] = campaign_data.campaign_name
        d['project_location'] = campaign_data.project_path

        self.data[key] = d

    def add_logger_props(self, key, loggers_data):
        """Add properties of all loggers."""

        d = dict()
        for logger in loggers_data:
            dict_props = {}
            dict_props['logger_id'] = logger.logger_id
            dict_props['file_format'] = logger.file_format
            dict_props['logger_path'] = logger.logger_path
            dict_props['file_timstamp'] = logger.file_timstamp
            dict_props['data_timstamp'] = logger.data_timstamp
            dict_props['file_ext'] = logger.file_ext
            dict_props['file_delimiter'] = logger.file_delimiter
            dict_props['num_header_rows'] = logger.num_header_rows
            dict_props['num_columns'] = logger.num_columns
            dict_props['channel_header_row'] = logger.channel_header_row
            dict_props['units_header_row'] = logger.units_header_row
            dict_props['logging_freq'] = logger.logging_freq
            dict_props['logging_duration'] = logger.logging_duration
            dict_props['channel_names'] = logger.channel_names
            dict_props['channel_units'] = logger.channel_units

            d['loggers'][logger.logger_id] = dict_props

        self.data[key] = d

    def export_config(self, proj_num, proj_name):
        """Export project configuration data as json file."""

        proj_name = '_'.join(proj_name.split(' '))
        self.filename = '_'.join((proj_num, proj_name, 'Config.json'))

        # Save as json file
        # Prevents ascii characters in file. Indent gives nicer layout instead of one long line string
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write(json.dumps(self.data, indent=4, sort_keys=False, ensure_ascii=False))


class ConfigModule(QtWidgets.QWidget):
    """Main screen containing project configuration setup."""

    def __init__(self, parent=None):
        super(ConfigModule, self).__init__(parent)

        self.parent = parent

        # JSON config class - hold config data dictionary
        self.config = ProjectConfig()
        self.control = ControlFile()

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.layout = QtWidgets.QGridLayout(self)

        # Container for load and save buttons and logger select drop down
        self.configButtonsWidget = QtWidgets.QWidget()
        hbox = QtWidgets.QHBoxLayout(self.configButtonsWidget)

        self.loadConfigButton = QtWidgets.QPushButton('&Load')
        self.saveConfigButton = QtWidgets.QPushButton('&Save')
        spacerItem = QtWidgets.QSpacerItem(40, 1)
        self.label = QtWidgets.QLabel('Selected logger:')
        self.loggerCombo = QtWidgets.QComboBox()
        self.loggerCombo.setMinimumWidth(100)
        self.loggerCombo.addItem('-')

        hbox.addWidget(QtWidgets.QLabel('Config File:'))
        hbox.addWidget(self.loadConfigButton)
        hbox.addWidget(self.saveConfigButton)
        hbox.addItem(spacerItem)
        hbox.addWidget(self.label)
        hbox.addWidget(self.loggerCombo)

        # Config tab widgets
        self.tabsContainer = QtWidgets.QTabWidget()
        self.campaignTab = CampaignInfoTab(self)
        self.loggerPropsTab = LoggerPropertiesTab(self)
        self.statsTab = StatsSettingsTab(self)
        self.spectralTab = SpectralSettingsTab(self)
        self.tabsContainer.addTab(self.campaignTab, 'Campaign Details')
        self.tabsContainer.addTab(self.loggerPropsTab, 'Logger Properties')
        self.tabsContainer.addTab(self.statsTab, 'Statistical Analysis')
        self.tabsContainer.addTab(self.spectralTab, 'Spectral Analysis')

        self.newProjButton = QtWidgets.QPushButton('&New Project')

        # Run analysis group
        self.runWidget = QtWidgets.QWidget()
        vbox1 = QtWidgets.QVBoxLayout(self.runWidget)
        runGroup = QtWidgets.QGroupBox('Selected Analysis')
        # policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        # runGroup.setSizePolicy(policy)
        vbox2 = QtWidgets.QVBoxLayout(runGroup)
        self.statsChkbox = QtWidgets.QCheckBox('Statistical Analysis')
        self.spectralChkbox = QtWidgets.QCheckBox('Spectral Analysis')
        vbox2.addWidget(self.statsChkbox)
        vbox2.addWidget(self.spectralChkbox)
        self.processButton = QtWidgets.QPushButton('Process')
        vbox1.addWidget(runGroup)
        vbox1.addWidget(self.processButton)

        # Main layout
        self.layout.addWidget(self.configButtonsWidget, 0, 0, QtCore.Qt.AlignLeft)
        self.layout.addWidget(self.tabsContainer, 1, 0)
        self.layout.addWidget(self.newProjButton, 2, 0, QtCore.Qt.AlignLeft)
        self.layout.addWidget(self.runWidget, 1, 1, 1, 1, QtCore.Qt.AlignTop)

    def connect_signals(self):
        self.loadConfigButton.clicked.connect(self.load_config_file)
        self.saveConfigButton.clicked.connect(self.save_config_file)
        self.loggerCombo.currentIndexChanged.connect(self.update_dashboard)
        self.newProjButton.clicked.connect(self.create_new_project)

    def create_new_project(self):
        """Create new project config file."""
        pass

    def load_config_file(self):
        """Load config JSON file."""

        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                                                            caption='Open Config File',
                                                            filter='Config Files (*.json)',
                                                            )

        if filename:
            try:
                # Read json file and store data in config object
                self.config.load_config(filename)

                # Assign config data to project dashboard
                self.store_campaign_info()
            except InputError as e:
                self.parent.error(str(e))
            except KeyError as e:
                msg = f'{e} key not found in config file'
                self.parent.error(msg)
            except Exception as e:
                msg = 'Unexpected error loading config file'
                self.parent.error(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
                logging.exception(str(e))

    def store_campaign_info(self):
        """Assign campaign info to control object and config dashboard."""

        keys, data = self.config.get_config_section('general')

        try:
            self.control.project_num = data['project_number']
            self.control.project_name = data['project_name']
            self.control.campaign_name = data['campaign_name']
            self.control.output_folder = os.path.join(data['project_location'], 'Output')
            self.control.config_file = self.config.filename
        except:
            raise

        self.campaignTab.set_dashboard_values()

    def save_config_file(self):
        """Save project configuration settings as a dictionary to a JSON file."""

        if self.control.project_num == '':
            self.parent.error('Project number required to create project config file.')
            return

        if self.control.project_name == '':
            self.parent.error('Project name required to create project config file.')
            return

        # Compile configuration data into a dictionary and save as a json file
        config = ProjectConfig()
        config.add_general_data(key='general', campaign_data=self.control)
        config.add_logger_props(key='loggers', loggers_data=self.control.loggers)
        config.export_config(proj_num=self.control.project_num,
                             proj_name=self.control.project_name,
                             )

        # Check file created
        file = Path(config.filename)
        if file.is_file():
            # Write to gui and inform user
            self.campaignTab.configFile.setText(config.filename)
            msg = f'Project config settings saved to {config.filename}'
            QtWidgets.QMessageBox.information(self, 'Save Project Config', msg, QtWidgets.QMessageBox.Ok)

    def update_dashboard(self):
        """Update dashboard data pertaining to logger."""

        # Check combo is not empty
        logger_idx = self.loggerCombo.currentIndex()
        if logger_idx == -1:
            return

        # Check that loggers list is not empty
        if self.control.loggers:
            logger = self.control.loggers[logger_idx]
            self.loggerPropsTab.set_dashboard_values(logger)
        # Clear values from dashboard
        else:
            self.loggerPropsTab.clear_dashboard()


class CampaignInfoTab(QtWidgets.QWidget):
    """GUI screen to control project setup."""

    def __init__(self, parent=None):
        super(CampaignInfoTab, self).__init__(parent)

        self.parent = parent

        # Map control object containing all setup data
        self.control = self.parent.control
        self.editInfo = CampaignInfoDialog(self)

        # Trick to get Pycharm's intellisense to detect the ControlFile class
        try:
            if isinstance(self.control, ControlFile):
                pass
        except:
            pass

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        # self.setFixedSize(700, 300)
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.setSizePolicy(policy)
        self.layout = QtWidgets.QVBoxLayout(self)

        # Form
        self.group = QtWidgets.QGroupBox('Project and Campaign Details')
        self.form = QtWidgets.QFormLayout(self.group)

        self.editButton = QtWidgets.QPushButton('Edit Values')
        self.editButton.setShortcut('Ctrl+E')
        self.projNum = QtWidgets.QLabel('Not set')
        self.projNum.setFixedWidth(40)
        self.projName = QtWidgets.QLabel('Not set')
        self.campaignName = QtWidgets.QLabel('Not set')
        self.projPath = QtWidgets.QLabel('Not set')
        self.projPath.setWordWrap(True)
        self.configFile = QtWidgets.QLabel('Not set')

        self.form.addRow(self.editButton, QtWidgets.QLabel(''))
        self.form.addRow(QtWidgets.QLabel('Project number:'), self.projNum)
        self.form.addRow(QtWidgets.QLabel('Project name:'), self.projName)
        self.form.addRow(QtWidgets.QLabel('Campaign name:'), self.campaignName)
        self.form.addRow(QtWidgets.QLabel('Project location:'), self.projPath)
        self.form.addRow(QtWidgets.QLabel('Config file name:'), self.configFile)

        # self.layout.addWidget(self.editButton, stretch=0, alignment=QtCore.Qt.AlignLeft)
        self.layout.addWidget(self.group)

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

    def connect_signals(self):
        self.editButton.clicked.connect(self.show_edit_dialog)

    def show_edit_dialog(self):
        self.editInfo.set_dialog_data()
        self.editInfo.show()

    def set_dashboard_values(self):
        """Set config tab campaign info."""

        self.projNum.setText(self.control.project_num)
        self.projName.setText(self.control.project_name)
        self.campaignName.setText(self.control.campaign_name)
        self.projPath.setText(self.control.project_path)
        self.configFile.setText(self.control.config_file)


class LoggerPropertiesTab(QtWidgets.QWidget):
    """Widget tabs for logger properties and analyis settings."""

    def __init__(self, parent=None):
        super(LoggerPropertiesTab, self).__init__(parent)

        self.parent = parent

        # Map control object containing all setup data
        self.control = self.parent.control

        # Edit logger properties dialog class
        self.editLoggerProps = LoggerPropertiesDialog(self)
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Create widget layout."""

        self.layout = QtWidgets.QGridLayout(self)

        # Logger list group
        self.loggersGroup = QtWidgets.QGroupBox('Campaign Loggers')
        self.loggersGroup.setFixedWidth(150)
        self.vbox = QtWidgets.QVBoxLayout(self.loggersGroup)

        self.addLoggerButton = QtWidgets.QPushButton('Add Logger')
        self.remLoggerButton = QtWidgets.QPushButton('Remove Logger')
        self.loggersList = QtWidgets.QListWidget()

        self.vbox.addWidget(self.addLoggerButton)
        self.vbox.addWidget(self.remLoggerButton)
        self.vbox.addWidget(QtWidgets.QLabel('Loggers'))
        self.vbox.addWidget(self.loggersList)

        # Logger properties group
        self.loggerPropsGroup = QtWidgets.QGroupBox('Logger Properties')
        self.form = QtWidgets.QFormLayout(self.loggerPropsGroup)

        self.editLoggerButton = QtWidgets.QPushButton('&Edit Values')
        self.editLoggerButton.setShortcut('Ctrl+E')
        self.editLoggerButton.setEnabled(False)

        # Logger properties form
        self.loggerID = QtWidgets.QLabel('N/A')
        self.fileFormat = QtWidgets.QLabel('N/A')
        self.loggerPath = QtWidgets.QLabel('N/A')
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

        self.form.addRow(self.editLoggerButton, QtWidgets.QLabel(''))
        self.form.addRow(QtWidgets.QLabel('Logger ID:'), self.loggerID)
        self.form.addRow(QtWidgets.QLabel('File type:'), self.fileFormat)
        self.form.addRow(QtWidgets.QLabel('Logger path:'), self.loggerPath)
        self.form.addRow(QtWidgets.QLabel('File timestamp:'), self.fileTimestampFormat)
        self.form.addRow(QtWidgets.QLabel('Data timestamp:'), self.dataTimestampFormat)
        self.form.addRow(QtWidgets.QLabel('Extension:'), self.fileExt)
        self.form.addRow(QtWidgets.QLabel('Delimiter:'), self.fileDelimiter)
        self.form.addRow(QtWidgets.QLabel('Number of header rows:'), self.numHeaderRows)
        self.form.addRow(QtWidgets.QLabel('Number of expected columns:'), self.numColumns)
        self.form.addRow(QtWidgets.QLabel('Channel header row:'), self.channelHeaderRow)
        self.form.addRow(QtWidgets.QLabel('Units header row:'), self.unitsHeaderRow)
        self.form.addRow(QtWidgets.QLabel('Logging frequency (Hz):'), self.loggingFreq)
        self.form.addRow(QtWidgets.QLabel('Logging duration (s):'), self.loggingDuration)

        # Assemble group boxes
        self.layout.addWidget(self.loggersGroup, 0, 0)
        self.layout.addWidget(self.loggerPropsGroup, 0, 1)

        # self.parent.label.setHidden(True)
        # self.parent.loggerCombo.setHidden(True)
        # self.parent.editLoggerButton.setHidden(True)

        # Buttonbox
        # self.buttonBox = QtWidgets.QDialogButtonBox()
        # self.buttonBox.addButton('Run Data Quality Checks', QtWidgets.QDialogButtonBox.AcceptRole)

    def connect_signals(self):
        self.addLoggerButton.clicked.connect(self.add_logger)
        self.remLoggerButton.clicked.connect(self.remove_logger)
        self.loggersList.itemChanged.connect(self.on_logger_item_edited)
        self.editLoggerButton.clicked.connect(self.show_edit_logger_form)

    def add_logger(self):
        """Add new logger to list. Initial logger name format is 'Logger n'."""

        n = self.loggersList.count()
        logger_id = f'Logger {n + 1}'

        # Create logger properties object and append to loggers list in control object
        logger = LoggerProperties(logger_id)
        self.control.loggers.append(logger)

        # Initialise logger with Fugro standard logger properties as default
        set_fugro_file_format(logger)

        item = QtWidgets.QListWidgetItem(logger_id)
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        self.loggersList.addItem(item)

        # Add logger to combo
        if self.parent.loggerCombo.currentText() == '-':
            self.parent.loggerCombo.clear()

        self.parent.loggerCombo.addItem(logger_id)
        self.parent.loggerCombo.setCurrentText(logger_id)

        # Enable edit values button
        self.editLoggerButton.setEnabled(True)

        # Open logger properties edit widget
        self.show_edit_logger_form()

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

        # Confirm with user
        msg = f'Are you sure you want to remove the logger named {logger}?'
        response = QtWidgets.QMessageBox.question(self, 'Remove Logger?', msg)

        if response == QtWidgets.QMessageBox.Yes:
            # Remove logger from control object
            logger = self.control.loggers[i]
            self.control.loggers.remove(logger)

            # Remove logger from loggers list and combobox
            self.loggersList.takeItem(i)
            self.parent.loggerCombo.removeItem(i)

            if self.parent.loggerCombo.count() == 0:
                self.parent.loggerCombo.addItem('-')
                self.editLoggerButton.setEnabled(False)

    def on_logger_item_edited(self):
        """Update logger combobox to match logger names of list widget."""

        i = self.loggersList.currentRow()
        new_name = self.loggersList.currentItem().text()
        self.parent.loggerCombo.setItemText(i, new_name)

    def show_edit_logger_form(self):
        """Open logger properties edit form."""

        # Retrieve selected logger object
        logger_idx = self.parent.loggerCombo.currentIndex()
        logger = self.control.loggers[logger_idx]
        self.editLoggerProps.logger_idx = logger_idx
        self.editLoggerProps.set_dialog_data(logger)
        self.editLoggerProps.show()

    def set_dashboard_values(self, logger):
        """Set gui logger properties with logger properties from logger object."""

        delimiters_dict = {',': 'comma',
                           ' ': 'space',
                           }

        self.loggerID.setText(logger.logger_id)
        self.fileFormat.setText(logger.file_format)
        self.loggerPath.setText(logger.logger_path)
        self.fileTimestampFormat.setText(logger.file_timestamp_format)
        self.dataTimestampFormat.setText(logger.timestamp_format)
        self.fileExt.setText(logger.file_ext)
        self.fileDelimiter.setText(delimiters_dict[logger.file_delimiter])
        self.numHeaderRows.setText(str(logger.num_headers))
        self.numColumns.setText(str(logger.num_columns))
        self.channelHeaderRow.setText(str(logger.channel_header_row))
        self.unitsHeaderRow.setText(str(logger.units_header_row))
        self.loggingFreq.setText(str(logger.freq))
        self.loggingDuration.setText(str(logger.duration))
        # channel_items_str = ' '.join([i for i in logger.user_channel_names])
        # self.channelNames.setText(channel_items_str)
        # units_items_str = ' '.join([i for i in logger.user_channel_units])
        # self.channelUnits.setText(units_items_str)

    def clear_dashboard(self):
        """Initialise all values in logger dashboard."""
        self.loggerID.setText('-')
        self.fileFormat.setText('-')
        self.loggerPath.setText('-')
        self.fileTimestampFormat.setText('-')
        self.dataTimestampFormat.setText('-')
        self.fileExt.setText('-')
        self.fileDelimiter.setText('-')
        self.numHeaderRows.setText('-')
        self.numColumns.setText('-')
        self.channelHeaderRow.setText('-')
        self.unitsHeaderRow.setText('-')
        self.loggingFreq.setText('-')
        self.loggingDuration.setText('-')


class StatsSettingsTab(QtWidgets.QWidget):
    """GUI screen to control project setup."""

    def __init__(self, parent=None):
        super(StatsSettingsTab, self).__init__(parent)

        self.stats_columns = ''
        self.stats_unit_convs = ''
        self.stats_interval = ''
        self.stats_start = ''
        self.stats_end = ''

        # Edit logger properties dialog class
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Create widget layout."""

        self.layout = QtWidgets.QVBoxLayout(self)
        self.group = QtWidgets.QGroupBox('Statistical Analysis Settings')
        self.form = QtWidgets.QFormLayout(self.group)

        # Stats settings form
        self.statsColumns = QtWidgets.QLabel('N/A')
        self.statsUnitConvs = QtWidgets.QLabel('N/A')
        self.statsInterval = QtWidgets.QLabel('N/A')
        self.statsStart = QtWidgets.QLabel('N/A')
        self.statsEnd = QtWidgets.QLabel('N/A')
        self.statsChannelNames = QtWidgets.QLabel('N/A')
        self.statsChannelUnits = QtWidgets.QLabel('N/A')

        self.form.addRow(QtWidgets.QLabel('Stats columns:'), self.statsColumns)
        self.form.addRow(QtWidgets.QLabel('Stats unit conversion factors:'), self.statsUnitConvs)
        self.form.addRow(QtWidgets.QLabel('Stats interval:'), self.statsInterval)
        self.form.addRow(QtWidgets.QLabel('Stats start timestamp:'), self.statsStart)
        self.form.addRow(QtWidgets.QLabel('Stats end timestamp:'), self.statsEnd)
        self.form.addRow(QtWidgets.QLabel('Channel names:'), self.statsChannelNames)
        self.form.addRow(QtWidgets.QLabel('Channel units:'), self.statsChannelUnits)

        self.layout.addWidget(self.group)

    def connect_signals(self):
        pass


class SpectralSettingsTab(QtWidgets.QWidget):
    """GUI screen to control project setup."""

    def __init__(self, parent=None):
        super(SpectralSettingsTab, self).__init__(parent)

        self.stats_columns = ''
        self.stats_unit_convs = ''
        self.stats_interval = ''
        self.stats_start = ''
        self.stats_end = ''

        # Edit logger properties dialog class
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Create widget layout."""

        self.layout = QtWidgets.QVBoxLayout(self)
        self.group = QtWidgets.QGroupBox('Spectral Analysis Settings')
        self.form = QtWidgets.QFormLayout(self.group)

        # Spectral settings form
        self.spectralColumns = QtWidgets.QLabel('N/A')
        self.spectralUnitConvs = QtWidgets.QLabel('N/A')
        self.spectralInterval = QtWidgets.QLabel('N/A')
        self.spectralStart = QtWidgets.QLabel('N/A')
        self.spectralEnd = QtWidgets.QLabel('N/A')
        self.spectralChannelNames = QtWidgets.QLabel('N/A')
        self.spectralChannelUnits = QtWidgets.QLabel('N/A')

        self.form.addRow(QtWidgets.QLabel('Stats columns:'), self.spectralColumns)
        self.form.addRow(QtWidgets.QLabel('Stats unit conversion factors:'), self.spectralUnitConvs)
        self.form.addRow(QtWidgets.QLabel('Stats interval:'), self.spectralInterval)
        self.form.addRow(QtWidgets.QLabel('Stats start timestamp:'), self.spectralStart)
        self.form.addRow(QtWidgets.QLabel('Stats end timestamp:'), self.spectralEnd)
        self.form.addRow(QtWidgets.QLabel('Channel names:'), self.spectralChannelNames)
        self.form.addRow(QtWidgets.QLabel('Channel units:'), self.spectralChannelUnits)

        self.layout.addWidget(self.group)

    def connect_signals(self):
        pass


class CampaignInfoDialog(QtWidgets.QDialog):
    """Edit window for project and campaign data."""

    def __init__(self, parent=None):
        super(CampaignInfoDialog, self).__init__(parent)

        self.parent = parent
        self.control = self.parent.control
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle('Edit General Campaign Data')
        self.setFixedSize(500, 250)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.formWidget = QtWidgets.QWidget()
        self.form = QtWidgets.QFormLayout(self.formWidget)
        self.projNum = QtWidgets.QLineEdit()
        self.projNum.setFixedWidth(40)
        self.projName = QtWidgets.QLineEdit()
        self.campaignName = QtWidgets.QLineEdit()
        self.projPath = QtWidgets.QLineEdit()
        self.browseButton = QtWidgets.QPushButton('Browse')
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.browseButton.setSizePolicy(policy)

        # Place widgets
        self.form.addRow(QtWidgets.QLabel('Project number:'), self.projNum)
        self.form.addRow(QtWidgets.QLabel('Project name:'), self.projName)
        self.form.addRow(QtWidgets.QLabel('Campaign name:'), self.campaignName)
        self.form.addRow(QtWidgets.QLabel('Project location:'), self.projPath)
        self.form.addRow(QtWidgets.QLabel(''), self.browseButton)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                    QtWidgets.QDialogButtonBox.Cancel)

        self.layout.addWidget(self.formWidget)
        self.layout.addWidget(self.buttonBox)

    def connect_signals(self):
        self.browseButton.clicked.connect(self.set_project_path)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.accepted.connect(self.set_control_data)
        self.buttonBox.rejected.connect(self.reject)

    def set_dialog_data(self):
        """Set dialog data with campaign info from control object."""

        self.projNum.setText(self.control.project_num)
        self.projName.setText(self.control.project_name)
        self.campaignName.setText(self.control.campaign_name)
        self.projPath.setText(self.control.project_path)

    def set_control_data(self):
        """Assign values to the control object and update dashboard."""

        self.control.project_num = self.projNum.text()
        self.control.project_name = self.projName.text()
        self.control.campaign_name = self.campaignName.text()
        self.control.project_path = self.projPath.text()

        self.parent.set_dashboard_values()

    def set_project_path(self):
        """Set location of project root directory."""

        file_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Project Location')

        if file_path:
            self.projPath.setText(file_path)
            os.chdir(file_path)


class LoggerPropertiesDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(LoggerPropertiesDialog, self).__init__(parent)

        self.parent = parent
        self.file_types = ['Fugro-csv',
                           'Pulse-acc',
                           'General-csv',
                           ]
        self.delimiters = ['comma',
                           'space',
                           ]

        # Index of selected logger in combo
        self.logger_idx = 0

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle('Edit Logger Properties')
        self.setMinimumWidth(500)

        self.layout = QtWidgets.QVBoxLayout(self)
        # self.layout.addStretch()

        # Logger properties group
        self.loggerProps = QtWidgets.QGroupBox('Logger Properties')
        propsForm = QtWidgets.QFormLayout(self.loggerProps)
        self.loggerID = QtWidgets.QLineEdit()
        self.fileFormat = QtWidgets.QComboBox()
        self.fileFormat.setFixedWidth(100)
        self.fileFormat.addItems(self.file_types)
        self.loggerPath = QtWidgets.QTextEdit()
        self.loggerPath.setFixedHeight(40)
        self.browseLoggerPathButton = QtWidgets.QPushButton('Browse')
        self.browseLoggerPathButton.setFixedWidth(70)
        self.fileTimestampFormat = QtWidgets.QLineEdit()
        self.dataTimestampFormat = QtWidgets.QLineEdit()
        self.fileExt = QtWidgets.QLineEdit()
        self.fileDelimiter = QtWidgets.QComboBox()
        self.fileDelimiter.setFixedWidth(60)
        self.fileDelimiter.addItems(self.delimiters)
        self.numHeaderRows = QtWidgets.QLineEdit()
        self.numHeaderRows.setFixedWidth(30)
        self.numColumns = QtWidgets.QLineEdit()
        self.numColumns.setFixedWidth(30)
        self.channelHeaderRow = QtWidgets.QLineEdit()
        self.channelHeaderRow.setFixedWidth(30)
        self.unitsHeaderRow = QtWidgets.QLineEdit()
        self.unitsHeaderRow.setFixedWidth(30)
        self.loggingFreq = QtWidgets.QLineEdit()
        self.loggingFreq.setFixedWidth(30)
        self.loggingDuration = QtWidgets.QLineEdit()
        self.loggingDuration.setFixedWidth(50)
        # self.channelNames = QtWidgets.QLineEdit()
        # self.channelUnits = QtWidgets.QLineEdit()

        # Place widgets
        propsForm.addRow(QtWidgets.QLabel('Logger ID:'), self.loggerID)
        propsForm.addRow(QtWidgets.QLabel('File format:'), self.fileFormat)
        propsForm.addRow(QtWidgets.QLabel('Logger path:'), self.loggerPath)
        propsForm.addRow(QtWidgets.QLabel(''), self.browseLoggerPathButton)
        propsForm.addRow(QtWidgets.QLabel('File timestamp:'), self.fileTimestampFormat)
        propsForm.addRow(QtWidgets.QLabel('Data timestamp:'), self.dataTimestampFormat)
        propsForm.addRow(QtWidgets.QLabel('File extension:'), self.fileExt)
        propsForm.addRow(QtWidgets.QLabel('File delimiter:'), self.fileDelimiter)
        propsForm.addRow(QtWidgets.QLabel('Number of header rows:'), self.numHeaderRows)
        propsForm.addRow(QtWidgets.QLabel('Number of expected columns:'), self.numColumns)
        propsForm.addRow(QtWidgets.QLabel('Channel header row:'), self.channelHeaderRow)
        propsForm.addRow(QtWidgets.QLabel('Units header row:'), self.unitsHeaderRow)
        propsForm.addRow(QtWidgets.QLabel('Logging frequency (Hz):'), self.loggingFreq)
        propsForm.addRow(QtWidgets.QLabel('Logging duration (s):'), self.loggingDuration)
        # propsForm.addRow(QtWidgets.QLabel('Channel names:'), self.channelNames)
        # propsForm.addRow(QtWidgets.QLabel('Channel units:'), self.channelUnits)

        # Button box
        # self.assignButton = QtWidgets.QPushButton('Assign')
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                    QtWidgets.QDialogButtonBox.Cancel)
        # self.buttons.addButton(self.assignButton, QtWidgets.QDialogButtonBox.AcceptRole)
        # self.buttons.addButton(QtWidgets.QDialogButtonBox.Cancel)

        self.layout.addWidget(self.loggerProps)
        self.layout.addWidget(self.buttonBox, stretch=0, alignment=QtCore.Qt.AlignRight)

    def connect_signals(self):
        self.buttonBox.accepted.connect(self.set_control_data)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.fileFormat.currentIndexChanged.connect(self.on_file_format_change)
        self.browseLoggerPathButton.clicked.connect(self.set_logger_path)

    def set_dialog_data(self, logger):
        """Set dialog data with logger properties from control object."""

        delimiters_dict = {',': 'comma',
                           ' ': 'space',
                           }

        # Trick to get Pycharm's intellisense to detect the LoggerProperties class
        try:
            if isinstance(logger, LoggerProperties):
                pass
        except:
            pass

        self.loggerID.setText(logger.logger_id)
        self.fileFormat.setCurrentText(logger.file_format)
        self.loggerPath.setText(logger.logger_path)
        self.fileTimestampFormat.setText(logger.file_timestamp_format)
        self.dataTimestampFormat.setText(logger.timestamp_format)
        self.fileExt.setText(logger.file_ext)
        self.fileDelimiter.setCurrentText(delimiters_dict[logger.file_delimiter])
        self.numHeaderRows.setText(str(logger.num_headers))
        self.numColumns.setText(str(logger.num_columns))
        self.channelHeaderRow.setText(str(logger.channel_header_row))
        self.unitsHeaderRow.setText(str(logger.units_header_row))
        self.loggingFreq.setText(str(logger.freq))
        self.loggingDuration.setText(str(logger.duration))
        # channel_items_str = ' '.join([i for i in logger.user_channel_names])
        # self.channelNames.setText(channel_items_str)
        # units_items_str = ' '.join([i for i in logger.user_channel_units])
        # self.channelUnits.setText(units_items_str)

    def set_control_data(self):
        """Assign values to the control object and update dashboard."""

        delimiters_dict = {'comma': ',',
                           'space': ' ',
                           }

        # Retrieve selected logger object
        logger = self.parent.control.loggers[self.logger_idx]

        # Assign form values to control logger object
        logger.logger_id = self.loggerID.text()
        logger.file_format = self.fileFormat.currentText()
        logger.logger_path = self.loggerPath.toPlainText()
        logger.file_timestamp_format = self.fileTimestampFormat.text()
        logger.timestamp_format = self.dataTimestampFormat.text()
        logger.file_ext = self.fileExt.text()
        logger.file_delimiter = delimiters_dict[self.fileDelimiter.currentText()]
        logger.num_headers = int(self.numHeaderRows.text())
        logger.num_columns = int(self.numColumns.text())
        logger.channel_header_row = int(self.channelHeaderRow.text())
        logger.units_header_row = int(self.unitsHeaderRow.text())
        logger.freq = int(self.loggingFreq.text())
        logger.duration = int(self.loggingDuration.text())
        # logger.user_channel_names = self.channelNames.text().split()
        # logger.user_channel_units = self.channelUnits.text().split()

        self.parent.set_dashboard_values(logger)

    def on_file_format_change(self):
        """Set standard logger properties for selected file format."""

        # no logger added
        if self.parent.loggersList.count() == 0:
            return

        file_format = self.fileFormat.currentText()
        logger = self.parent.control.loggers[self.logger_idx]

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
        logger = set_fugro_file_format(logger)

        # Input in edit widget
        self.fileExt.setText(logger.file_ext)
        self.fileDelimiter.setCurrentText('comma')
        self.numHeaderRows.setText(str(logger.num_headers))
        self.channelHeaderRow.setText(str(logger.channel_header_row))
        self.unitsHeaderRow.setText(str(logger.units_header_row))

    def set_logger_path(self):
        """Set location of project root directory."""

        file_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Logger Location')

        if file_path:
            self.loggerPath.setText(file_path)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # win = ProjectConfigModule()
    win = LoggerPropertiesDialog()
    win.show()
    app.exit(app.exec_())
