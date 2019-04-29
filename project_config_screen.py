import json
import logging
import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets
from dateutil.parser import parse
from core.control_file import ControlFile, InputError
from core.fugro_csv import set_fugro_file_format
from core.logger_properties import LoggerProperties, LoggerError


class ProjectConfigJSONFile:
    def __init__(self):
        # Config data dictionary to be written to a JSON file
        self.data = {}
        self.filename = ''

    def load_config_data(self, file_name):
        """Load project config JSON file and return the dictionary data."""

        with open(file_name, encoding='utf-8') as f:
            data = json.load(f)

        # Store filename and set directory to project root
        file_path, self.filename = os.path.split(file_name)
        os.chdir(file_path)

        return data

    def get_config_section(self, data, key):
        """Return requested subsection of the config dictionary."""

        if key in data.keys():
            return data[key].keys(), data[key]
        else:
            raise KeyError(key)

    def add_campaign_data(self, control):
        """Add project and campaign details."""

        d = dict()
        d['project_number'] = control.project_num
        d['project_name'] = control.project_name
        d['campaign_name'] = control.campaign_name
        d['project_location'] = control.project_path

        self.data['campaign'] = d

    def add_logger_data(self, loggers):
        """Add properties of all loggers."""

        if not loggers:
            return

        self.data['loggers'] = dict()

        for logger in loggers:
            dict_props = dict()

            # Add logger properties
            dict_props = self.add_logger_props(logger, dict_props)

            # Add logger stats settings
            dict_props = self.add_logger_stats_settings(logger, dict_props)

            # Add logger spectral settings
            dict_props = self.add_logger_spectral_settings(logger, dict_props)

            # Add logger props dictionary to loggers dictionary
            self.data['loggers'][logger.logger_id] = dict_props

    def add_logger_props(self, logger, dict_props):
        """Add control object logger properties to JSON dictionary."""

        dict_props['file_format'] = logger.file_format
        dict_props['logger_path'] = logger.logger_path
        dict_props['file_timestamp_format'] = logger.file_timestamp_format
        dict_props['data_timestamp_format'] = logger.timestamp_format
        dict_props['data_datetime_format'] = logger.datetime_format
        dict_props['file_ext'] = logger.file_ext
        dict_props['file_delimiter'] = logger.file_delimiter
        dict_props['num_header_rows'] = logger.num_headers
        dict_props['num_columns'] = logger.num_columns
        dict_props['channel_header_row'] = logger.channel_header_row
        dict_props['units_header_row'] = logger.units_header_row
        dict_props['logging_freq'] = logger.freq
        dict_props['logging_duration'] = logger.duration
        dict_props['channel_names'] = logger.channel_names
        dict_props['channel_units'] = logger.channel_units

        return dict_props

    def add_logger_stats_settings(self, logger, dict_props):
        """Add control object logger stats settings to JSON dictionary."""

        dict_props['stats_columns'] = logger.stats_cols
        dict_props['stats_unit_convs'] = logger.stats_unit_conv_factors
        dict_props['stats_interval'] = logger.stats_interval

        # Need to convert start and end datetimes to strings to write to JSON format
        # Stats start
        if logger.stats_start is None:
            dict_props['stats_start'] = None
        else:
            dict_props['stats_start'] = logger.stats_start.strftime('%Y-%m-%d %H:%M')

        # Stats end
        if logger.stats_end is None:
            dict_props['stats_end'] = None
        else:
            dict_props['stats_end'] = logger.stats_end.strftime('%Y-%m-%d %H:%M')

        dict_props['stats_user_channel_names'] = logger.stats_user_channel_names
        dict_props['stats_user_channel_units'] = logger.stats_user_channel_units

        return dict_props

    def add_logger_spectral_settings(self, logger, dict_props):
        """Add control object logger spectral settings to JSON dictionary."""

        dict_props['spectral_columns'] = logger.spectral_cols
        dict_props['spectral_unit_convs'] = logger.spectral_unit_conv_factors
        dict_props['spectral_interval'] = logger.spectral_interval

        # Need to convert start and end datetimes to strings to write to JSON format
        # Stats start
        if logger.spectral_start is None:
            dict_props['spectral_start'] = None
        else:
            dict_props['spectral_start'] = logger.spectral_start.strftime('%Y-%m-%d %H:%M')

        # Stats end
        if logger.spectral_end is None:
            dict_props['spectral_end'] = None
        else:
            dict_props['spectral_end'] = logger.spectral_end.strftime('%Y-%m-%d %H:%M')

        dict_props['spectral_user_channel_names'] = logger.spectral_user_channel_names
        dict_props['spectral_user_channel_units'] = logger.spectral_user_channel_units

        return dict_props

    def export_config(self, proj_num, proj_name):
        """Export project configuration data as JSON file."""

        proj_name = '_'.join(proj_name.split())
        self.filename = '_'.join((proj_num, proj_name, 'Config.json'))

        # Save as JSON file
        # Prevents ascii characters in file. Indent gives nicer layout instead of one long line string
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write(json.dumps(self.data, indent=4, sort_keys=False, ensure_ascii=False))


class ConfigModule(QtWidgets.QWidget):
    """Main screen containing project configuration setup."""

    def __init__(self, parent=None):
        super(ConfigModule, self).__init__(parent)

        self.parent = parent

        # JSON config class - hold config data dictionary
        self.config = ProjectConfigJSONFile()
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

        self.tabsContainer.addTab(self.campaignTab, 'Campaign Info')
        self.tabsContainer.addTab(self.loggerPropsTab, 'Logger File Properties')
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
        self.loggerCombo.currentIndexChanged.connect(self.on_logger_combo_changed)
        self.newProjButton.clicked.connect(self.new_project)
        self.processButton.clicked.connect(self.run_analysis)

    def load_config_file(self):
        """Load config JSON file."""

        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                                                            caption='Open Config File',
                                                            filter='Config Files (*.json)',
                                                            )

        if filename:
            try:
                # Read JSON file and store data in config object
                data = self.config.load_config_data(filename)

                # Create new control object to hold setup data
                self.control = ControlFile()

                # Assign config data to control object and project dashboard
                self.map_campaign_json_section(data)
                self.map_loggers_json_section(data)
                self.set_dashboards()
                self.set_window_title(filename)
            except InputError as e:
                self.parent.error(str(e))
                logging.exception(str(e))
            except KeyError as e:
                msg = f'{e} key not found in config file'
                self.parent.warning(msg)
                logging.exception(str(e))
            except Exception as e:
                msg = 'Unexpected error loading config file'
                self.parent.error(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
                logging.exception(str(e))

    def save_config_file(self):
        """Save project configuration settings as a dictionary to a JSON file."""

        if self.control.project_num == '':
            return self.parent.warning('Project number required to create project config file.')

        if self.control.project_name == '':
            return self.parent.warning('Project name required to create project config file.')

        # Compile configuration data into a dictionary and save as a json file
        config = ProjectConfigJSONFile()
        config.add_campaign_data(self.control)
        config.add_logger_data(self.control.loggers)
        config.export_config(proj_num=self.control.project_num,
                             proj_name=self.control.project_name,
                             )

        # Check file created
        if os.path.exists(config.filename):
            # Write to gui and inform user
            self.campaignTab.configFile.setText(config.filename)
            msg = f'Project config settings saved to {config.filename}'
            QtWidgets.QMessageBox.information(self, 'Save Project Config', msg)

    def on_logger_combo_changed(self):
        """Update dashboard data pertaining to selected logger."""

        # Check combo is not empty
        logger_idx = self.loggerCombo.currentIndex()
        if logger_idx == -1:
            return

        # Check that control object contains at least one logger
        if self.control.loggers:
            logger = self.control.loggers[logger_idx]
            self.loggerPropsTab.set_logger_dashboard(logger)
            self.statsTab.set_stats_dashboard(logger)
            self.spectralTab.set_spectral_dashboard(logger)
        # Clear values from dashboard
        else:
            self.loggerPropsTab.clear_dashboard()
            self.statsTab.clear_dashboard()
            self.spectralTab.clear_dashboard()

    def new_project(self):
        """Clear project control object and all config dashboard values."""

        # Create new control object and map to campaignTab and loggerTab
        self.control = ControlFile()
        self.campaignTab.control = self.control
        self.loggerPropsTab.control = self.control

        # Clear logger combo box
        # Note: This will trigger the clearing of the logger properties, stats and spectral dashboards
        self.loggerCombo.clear()
        self.loggerCombo.addItem('-')

        # Clear campaign data dashboard and update window title to include config file path
        self.campaignTab.clear_dashboard()
        self.set_window_title()

    def run_analysis(self):
        """Run DataLab processing engine - call function in main DataLab class."""

        self.parent.process_datalab_config(self.control)

    def get_key_value(self, id, data, key, attr=None):
        """Assign data from a JSON key to control object attribute."""

        try:
            return data[key]
        except KeyError as e:
            self.parent.warning(f'{e} key not found in config file under {id} dictionary')
            logging.exception(str(e))
            return attr

    def map_campaign_json_section(self, data):
        """Map the config campaign section to the control object."""

        try:
            section = 'campaign'
            keys, data = self.config.get_config_section(data, key=section)
        except KeyError as e:
            msg = f'{e} key not found in config file'
            self.parent.warning(msg)
            logging.exception(str(e))
        else:
            self.control.project_num = self.get_key_value(id=section,
                                                          data=data,
                                                          key='project_number',
                                                          attr=self.control.project_num)
            self.control.project_name = self.get_key_value(id=section,
                                                           data=data,
                                                           key='project_name',
                                                           attr=self.control.project_name)
            self.control.campaign_name = self.get_key_value(id=section,
                                                            data=data,
                                                            key='campaign_name',
                                                            attr=self.control.campaign_name)
            self.control.project_path = self.get_key_value(id=section,
                                                           data=data,
                                                           key='project_location',
                                                           attr=self.control.project_path)
            self.control.output_folder = os.path.join(self.control.project_path, 'Output')
            self.control.config_file = self.config.filename

    def map_loggers_json_section(self, data):
        """Map the config loggers section to the control object for all logger."""

        try:
            keys, data = self.config.get_config_section(data, key='loggers')
        except KeyError as e:
            msg = f'{e} key not found in config file'
            self.parent.warning(msg)
            logging.exception(str(e))
        else:
            for logger_id, dict_logger in data.items():
                # Create new logger properties object and assign attributes from JSON dictionary
                logger = LoggerProperties()

                # Logger properties
                logger = self.map_logger_props(logger, dict_logger)

                # Logger stats settings
                logger = self.map_logger_stats_settings(logger, dict_logger)

                # Logger spectral settings
                logger = self.map_logger_spectral_settings(logger, dict_logger)

                # Finally, assign logger to control object
                self.control.logger_ids.append(logger_id)
                self.control.logger_ids_upper.append(logger_id.upper())
                self.control.loggers.append(logger)

    def map_logger_props(self, logger, dict_logger):
        """Retrieve logger properties from JSON dictionary and map to logger object."""

        logger.file_format = self.get_key_value(id=logger.logger_id,
                                                data=dict_logger,
                                                key='file_format',
                                                attr=logger.file_format)
        logger.logger_path = self.get_key_value(id=logger.logger_id,
                                                data=dict_logger,
                                                key='logger_path',
                                                attr=logger.logger_path)
        logger.file_timestamp_format = self.get_key_value(id=logger.logger_id,
                                                          data=dict_logger,
                                                          key='file_timestamp_format',
                                                          attr=logger.file_timestamp_format)
        logger.timestamp_format = self.get_key_value(id=logger.logger_id,
                                                     data=dict_logger,
                                                     key='data_timestamp_format',
                                                     attr=logger.timestamp_format)
        logger.datetime_format = self.get_key_value(id=logger.logger_id,
                                                    data=dict_logger,
                                                    key='data_datetime_format',
                                                    attr=logger.datetime_format)
        logger.file_ext = self.get_key_value(id=logger.logger_id,
                                             data=dict_logger,
                                             key='file_ext',
                                             attr=logger.file_ext)
        logger.file_delimiter = self.get_key_value(id=logger.logger_id,
                                                   data=dict_logger,
                                                   key='file_delimiter',
                                                   attr=logger.file_delimiter)
        logger.num_headers = self.get_key_value(id=logger.logger_id,
                                                data=dict_logger,
                                                key='num_header_rows',
                                                attr=logger.num_headers)
        logger.num_columns = self.get_key_value(id=logger.logger_id,
                                                data=dict_logger,
                                                key='num_columns',
                                                attr=logger.num_columns)
        logger.channel_header_row = self.get_key_value(id=logger.logger_id,
                                                       data=dict_logger,
                                                       key='channel_header_row',
                                                       attr=logger.channel_header_row)
        logger.units_header_row = self.get_key_value(id=logger.logger_id,
                                                     data=dict_logger,
                                                     key='units_header_row',
                                                     attr=logger.units_header_row)
        logger.freq = self.get_key_value(id=logger.logger_id,
                                         data=dict_logger,
                                         key='logging_freq',
                                         attr=logger.freq)
        logger.duration = self.get_key_value(id=logger.logger_id,
                                             data=dict_logger,
                                             key='logging_duration',
                                             attr=logger.duration)
        logger.channel_names = self.get_key_value(id=logger.logger_id,
                                                  data=dict_logger,
                                                  key='channel_names',
                                                  attr=logger.channel_names)
        logger.channel_units = self.get_key_value(id=logger.logger_id,
                                                  data=dict_logger,
                                                  key='channel_units',
                                                  attr=logger.channel_units)
        return logger

    def map_logger_stats_settings(self, logger, dict_logger):
        """Retrieve logger stats settings from JSON dictionary and map to logger object."""

        logger.stats_cols = self.get_key_value(id=logger.logger_id,
                                               data=dict_logger,
                                               key='stats_columns',
                                               attr=logger.stats_cols)
        logger.stats_unit_conv_factors = self.get_key_value(id=logger.logger_id,
                                                            data=dict_logger,
                                                            key='stats_unit_convs',
                                                            attr=logger.stats_unit_conv_factors)
        logger.stats_interval = self.get_key_value(id=logger.logger_id,
                                                   data=dict_logger,
                                                   key='stats_interval',
                                                   attr=logger.stats_interval)

        stats_start = self.get_key_value(id=logger.logger_id,
                                         data=dict_logger,
                                         key='stats_start',
                                         attr=logger.stats_start)
        if stats_start is None:
            logger.stats_start = None
        else:
            try:
                # Need to convert stats start to datetime
                logger.stats_start = parse(stats_start, yearfirst=True)
            except ValueError:
                self.parent.warning(f'stats_start datetime format not recognised for logger {logger.logger_id}')

        stats_end = self.get_key_value(id=logger.logger_id,
                                       data=dict_logger,
                                       key='stats_end',
                                       attr=logger.stats_end)
        if stats_end is None:
            logger.stats_end = None
        else:
            try:
                # Need to convert stats end to datetime
                logger.stats_end = parse(stats_end, yearfirst=True)
            except ValueError:
                self.parent.warning(f'stats_end datetime format not recognised for logger {logger.logger_id}')

        logger.stats_user_channel_names = self.get_key_value(id=logger.logger_id,
                                                             data=dict_logger,
                                                             key='stats_user_channel_names',
                                                             attr=logger.stats_user_channel_names)
        logger.stats_user_channel_units = self.get_key_value(id=logger.logger_id,
                                                             data=dict_logger,
                                                             key='stats_user_channel_units',
                                                             attr=logger.stats_user_channel_units)
        return logger

    def map_logger_spectral_settings(self, logger, dict_logger):
        """Retrieve logger spectral settings from JSON dictionary and map to logger object."""

        logger.spectral_cols = self.get_key_value(id=logger.logger_id,
                                                  data=dict_logger,
                                                  key='spectral_columns',
                                                  attr=logger.spectral_cols)
        logger.spectral_unit_conv_factors = self.get_key_value(id=logger.logger_id,
                                                               data=dict_logger,
                                                               key='spectral_unit_convs',
                                                               attr=logger.spectral_unit_conv_factors)
        logger.spectral_interval = self.get_key_value(id=logger.logger_id,
                                                      data=dict_logger,
                                                      key='spectral_interval',
                                                      attr=logger.spectral_interval)

        spectral_start = self.get_key_value(id=logger.logger_id,
                                            data=dict_logger,
                                            key='spectral_start',
                                            attr=logger.spectral_start)
        if spectral_start is None:
            logger.spectral_start = None
        else:
            try:
                # Need to convert spectral start to datetime
                logger.spectral_start = parse(spectral_start, yearfirst=True)
            except ValueError:
                self.parent.warning(f'spectral_start datetime format not recognised for logger {logger.logger_id}')

        spectral_end = self.get_key_value(id=logger.logger_id,
                                          data=dict_logger,
                                          key='spectral_end',
                                          attr=logger.spectral_end)
        if spectral_end is None:
            logger.spectral_end = None
        else:
            try:
                # Need to convert spectral end to datetime
                logger.spectral_end = parse(spectral_end, yearfirst=True)
            except ValueError:
                self.parent.warning(f'spectral_end datetime format not recognised for {logger.logger_id}')

        logger.spectral_user_channel_names = self.get_key_value(id=logger.logger_id,
                                                                data=dict_logger,
                                                                key='spectral_user_channel_names',
                                                                attr=logger.spectral_user_channel_names)
        logger.spectral_user_channel_units = self.get_key_value(id=logger.logger_id,
                                                                data=dict_logger,
                                                                key='spectral_user_channel_units',
                                                                attr=logger.spectral_user_channel_units)
        return logger

    def set_dashboards(self):
        """Set dashboard values with data in control object after loading JSON file."""

        # First need to map the newly loaded control object to campaignTab and loggerTab
        self.campaignTab.control = self.control
        self.loggerPropsTab.control = self.control
        self.statsTab.control = self.control
        self.spectralTab.control = self.control

        # Set campaign data to dashboard
        self.campaignTab.set_campaign_dashboard()

        # Add loggers to dashboard list and combo boxes if loggers have been loaded and exist in control object
        if self.control.loggers:
            self.loggerPropsTab.loggersList.clear()

            # Populate logger list
            for logger_id in self.control.logger_ids:
                item = QtWidgets.QListWidgetItem(logger_id)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                self.loggerPropsTab.loggersList.addItem(item)

            # Populate logger combo box
            # Note: This will trigger the setting of the logger properties, stats and spectral dashboards
            self.loggerCombo.clear()
            self.loggerCombo.addItems(self.control.logger_ids)

    def set_window_title(self, filename=None):
        """Update main window title with config filename."""

        if filename:
            self.parent.setWindowTitle(f'DataLab {self.parent.version} - Loaded Project: {filename}')
        else:
            self.parent.setWindowTitle(f'DataLab {self.parent.version}')


class CampaignInfoTab(QtWidgets.QWidget):
    """GUI screen to control project setup."""

    def __init__(self, parent=None):
        super(CampaignInfoTab, self).__init__(parent)

        self.parent = parent

        # Map control object containing all setup data
        self.control = self.parent.control

        # Trick to get Pycharm's intellisense to detect the ControlFile class
        # try:
        #     if isinstance(self.control, ControlFile):
        #         pass
        # except:
        #     pass

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        # self.setFixedSize(700, 300)
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.setSizePolicy(policy)
        self.layout = QtWidgets.QVBoxLayout(self)

        # Form
        self.group = QtWidgets.QGroupBox('Project and Campaign Info')
        self.form = QtWidgets.QFormLayout(self.group)

        self.editButton = QtWidgets.QPushButton('Edit Data')
        self.editButton.setShortcut('Ctrl+E')
        self.projNum = QtWidgets.QLabel('-')
        self.projNum.setFixedWidth(40)
        self.projName = QtWidgets.QLabel('-')
        self.campaignName = QtWidgets.QLabel('-')
        self.projPath = QtWidgets.QLabel('-')
        self.projPath.setWordWrap(True)
        self.configFile = QtWidgets.QLabel('-')

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
        editInfo = CampaignInfoDialog(self, self.control)
        editInfo.set_dialog_data()
        editInfo.show()

    def set_campaign_dashboard(self):
        """Set config tab campaign info."""

        self.projNum.setText(self.control.project_num)
        self.projName.setText(self.control.project_name)
        self.campaignName.setText(self.control.campaign_name)
        self.projPath.setText(self.control.project_path)
        self.configFile.setText(self.control.config_file)

    def clear_dashboard(self):
        """Initialise all values in logger dashboard."""

        self.projNum.setText('-')
        self.projName.setText('-')
        self.campaignName.setText('-')
        self.projPath.setText('-')
        self.configFile.setText('-')


class LoggerPropertiesTab(QtWidgets.QWidget):
    """Widget tabs for logger properties and analyis settings."""

    def __init__(self, parent=None):
        super(LoggerPropertiesTab, self).__init__(parent)

        self.parent = parent

        # Map control object containing all setup data
        self.control = self.parent.control

        self.skip_on_logger_item_edited = False

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Create widget layout."""

        self.layout = QtWidgets.QGridLayout(self)

        # Loggers list group
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

        self.editButton = QtWidgets.QPushButton('Edit Data')
        self.editButton.setShortcut('Ctrl+E')
        self.loggerID = QtWidgets.QLabel('-')
        self.fileFormat = QtWidgets.QLabel('-')
        self.loggerPath = QtWidgets.QLabel('-')
        self.loggerPath.setWordWrap(True)
        self.fileTimestampFormat = QtWidgets.QLabel('-')
        self.dataTimestampFormat = QtWidgets.QLabel('-')
        self.fileExt = QtWidgets.QLabel('-')
        self.fileDelimiter = QtWidgets.QLabel('-')
        self.numHeaderRows = QtWidgets.QLabel('-')
        self.numColumns = QtWidgets.QLabel('-')
        self.channelHeaderRow = QtWidgets.QLabel('-')
        self.unitsHeaderRow = QtWidgets.QLabel('-')
        self.loggingFreq = QtWidgets.QLabel('-')
        self.loggingDuration = QtWidgets.QLabel('-')

        self.form.addRow(self.editButton, QtWidgets.QLabel(''))
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
        self.editButton.clicked.connect(self.show_edit_dialog)

    def show_edit_dialog(self):
        """Open logger properties edit form."""

        if self.loggersList.count() == 0:
            msg = f'No loggers exist to edit. Add a logger first.'
            return QtWidgets.QMessageBox.information(self, 'Edit Logger Properties', msg)

        # Retrieve selected logger object
        # TODO: If adding logger, dialog should show new logger id - works but if remove one first id may not be unique
        logger_idx = self.parent.loggerCombo.currentIndex()
        logger = self.control.loggers[logger_idx]

        # Create edit logger properties dialog window instance
        editLoggerProps = LoggerPropertiesDialog(self, logger, logger_idx)
        editLoggerProps.set_dialog_data()
        editLoggerProps.show()

    def set_logger_dashboard(self, logger):
        """Set dashboard with logger properties from logger object."""

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

    def clear_dashboard(self):
        """Initialise all values in logger dashboard."""

        # Clear loggers list and properties
        self.loggersList.clear()
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

        # TODO: Adding item triggers combo change which sets dashboards values before confirmed by user
        self.parent.loggerCombo.addItem(logger_id)
        self.parent.loggerCombo.setCurrentText(logger_id)

        # Open logger properties edit widget
        self.show_edit_dialog()

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
        response = QtWidgets.QMessageBox.question(self, 'Remove Logger', msg)

        if response == QtWidgets.QMessageBox.Yes:
            # Remove logger from control object
            logger = self.control.loggers[i]
            self.control.loggers.remove(logger)

            # Remove logger from loggers list and combobox
            self.loggersList.takeItem(i)
            self.parent.loggerCombo.removeItem(i)

            if self.parent.loggerCombo.count() == 0:
                self.parent.loggerCombo.addItem('-')

    def on_logger_item_edited(self):
        """Update logger combo box to match logger names of list widget."""

        if self.skip_on_logger_item_edited is True:
            return

        # Retrieve new logger id from list and apply to combo box
        i = self.loggersList.currentRow()
        new_logger_id = self.loggersList.currentItem().text()
        self.parent.loggerCombo.setItemText(i, new_logger_id)

        # Update logger id in control object
        logger = self.control.loggers[i]
        logger.logger_id = new_logger_id

        # Update dashboard logger id if selected logger is the same as the one edited in the list
        combo_idx = self.parent.loggerCombo.currentIndex()
        if combo_idx == i:
            self.loggerID.setText(new_logger_id)

    def update_logger_id_list(self, logger_id, logger_idx):
        """Update logger name in the loggers list and combo box if logger id in form is changed."""

        # Set flag to skip logger list edit action when triggered
        self.skip_on_logger_item_edited = True
        self.loggersList.item(logger_idx).setText(logger_id)
        self.parent.loggerCombo.setItemText(logger_idx, logger_id)
        self.skip_on_logger_item_edited = False


class StatsSettingsTab(QtWidgets.QWidget):
    """GUI screen to control project setup."""

    def __init__(self, parent=None):
        super(StatsSettingsTab, self).__init__(parent)

        self.parent = parent
        self.control = self.parent.control
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Create widget layout."""

        self.layout = QtWidgets.QVBoxLayout(self)

        # Stats settings group
        self.group = QtWidgets.QGroupBox('Statistical Analysis Settings')
        self.form = QtWidgets.QFormLayout(self.group)

        self.editButton = QtWidgets.QPushButton('Edit Data')
        self.editButton.setShortcut('Ctrl+E')
        self.statsColumns = QtWidgets.QLabel('-')
        self.statsUnitConvs = QtWidgets.QLabel('-')
        self.statsInterval = QtWidgets.QLabel('-')
        self.statsStart = QtWidgets.QLabel('-')
        self.statsEnd = QtWidgets.QLabel('-')
        self.statsChannelNames = QtWidgets.QLabel('-')
        self.statsChannelUnits = QtWidgets.QLabel('-')

        self.form.addRow(self.editButton, QtWidgets.QLabel(''))
        self.form.addRow(QtWidgets.QLabel('Stats columns:'), self.statsColumns)
        self.form.addRow(QtWidgets.QLabel('Stats unit conversion factors:'), self.statsUnitConvs)
        self.form.addRow(QtWidgets.QLabel('Stats interval (s):'), self.statsInterval)
        self.form.addRow(QtWidgets.QLabel('Stats start timestamp:'), self.statsStart)
        self.form.addRow(QtWidgets.QLabel('Stats end timestamp:'), self.statsEnd)
        self.form.addRow(QtWidgets.QLabel('Channel names:'), self.statsChannelNames)
        self.form.addRow(QtWidgets.QLabel('Channel units:'), self.statsChannelUnits)

        self.layout.addWidget(self.group)

    def connect_signals(self):
        self.editButton.clicked.connect(self.show_edit_dialog)

    def show_edit_dialog(self):
        """Open logger stats edit form."""

        if self.parent.loggerCombo.currentText() == '-':
            msg = f'No loggers exist to edit. Add a logger first.'
            return QtWidgets.QMessageBox.information(self, 'Edit Logger Statistics Settings', msg)

        # Retrieve selected logger object
        logger_idx = self.parent.loggerCombo.currentIndex()
        logger = self.control.loggers[logger_idx]

        # Edit stats dialog class
        editStatsSettings = LoggerStatsDialog(self, logger, logger_idx)
        editStatsSettings.set_dialog_data()
        editStatsSettings.show()

    def set_stats_dashboard(self, logger):
        """Set dashboard with logger stats from logger object."""

        # Stats columns
        if logger.stats_cols is not None:
            cols_str = ' '.join([str(i) for i in logger.stats_cols])
            self.statsColumns.setText(cols_str)

        # Unit conversion factors
        if logger.stats_unit_conv_factors is not None:
            unit_conv_factors_str = ' '.join([str(i) for i in logger.stats_unit_conv_factors])
            self.statsUnitConvs.setText(unit_conv_factors_str)

            # Stats interval
            self.statsInterval.setText(str(logger.stats_interval))

            # Stats start
            if logger.stats_start is None:
                stats_start = 'Not used'
            else:
                stats_start = logger.stats_start.strftime('%Y-%m-%d %H:%M')
            self.statsStart.setText(stats_start)

            # Stats end
            if logger.stats_end is None:
                stats_end = 'Not used'
            else:
                stats_end = logger.stats_end.strftime('%Y-%m-%d %H:%M')
            self.statsEnd.setText(stats_end)

            # Stats channel names
            if logger.stats_user_channel_names is not None:
                channel_items_str = ' '.join([i for i in logger.stats_user_channel_names])
            self.statsChannelNames.setText(channel_items_str)

            # Stats units names
            if logger.stats_user_channel_units is not None:
                units_items_str = ' '.join([i for i in logger.stats_user_channel_units])
            self.statsChannelUnits.setText(units_items_str)

    def clear_dashboard(self):
        """Initialise all values in stats dashboard."""

        # Clear logger stats settings
        self.statsColumns.setText('-')
        self.statsUnitConvs.setText('-')
        self.statsInterval.setText('-')
        self.statsStart.setText('-')
        self.statsEnd.setText('-')
        self.statsChannelNames.setText('-')
        self.statsChannelUnits.setText('-')


class SpectralSettingsTab(QtWidgets.QWidget):
    """GUI screen to control project setup."""

    def __init__(self, parent=None):
        super(SpectralSettingsTab, self).__init__(parent)

        self.parent = parent
        self.control = self.parent.control
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Create widget layout."""

        self.layout = QtWidgets.QVBoxLayout(self)
        self.group = QtWidgets.QGroupBox('Spectral Analysis Settings')
        self.form = QtWidgets.QFormLayout(self.group)

        self.editButton = QtWidgets.QPushButton('Edit Data')
        self.editButton.setShortcut('Ctrl+E')
        self.spectralColumns = QtWidgets.QLabel('-')
        self.spectralUnitConvs = QtWidgets.QLabel('-')
        self.spectralInterval = QtWidgets.QLabel('-')
        self.spectralStart = QtWidgets.QLabel('-')
        self.spectralEnd = QtWidgets.QLabel('-')
        self.spectralChannelNames = QtWidgets.QLabel('-')
        self.spectralChannelUnits = QtWidgets.QLabel('-')

        self.form.addRow(self.editButton, QtWidgets.QLabel(''))
        self.form.addRow(QtWidgets.QLabel('Spectral columns:'), self.spectralColumns)
        self.form.addRow(QtWidgets.QLabel('Spectral unit conversion factors:'), self.spectralUnitConvs)
        self.form.addRow(QtWidgets.QLabel('Spectral interval (s):'), self.spectralInterval)
        self.form.addRow(QtWidgets.QLabel('Spectral start timestamp:'), self.spectralStart)
        self.form.addRow(QtWidgets.QLabel('Spectral end timestamp:'), self.spectralEnd)
        self.form.addRow(QtWidgets.QLabel('Channel names:'), self.spectralChannelNames)
        self.form.addRow(QtWidgets.QLabel('Channel units:'), self.spectralChannelUnits)

        self.layout.addWidget(self.group)

    def connect_signals(self):
        self.editButton.clicked.connect(self.show_edit_dialog)

    def show_edit_dialog(self):
        """Open logger spectral settings edit form."""

        if self.parent.loggerCombo.currentText() == '-':
            msg = f'No loggers exist to edit. Add a logger first.'
            return QtWidgets.QMessageBox.information(self, 'Edit Logger Spectral Settings', msg)

        # Retrieve selected logger object
        logger_idx = self.parent.loggerCombo.currentIndex()
        logger = self.control.loggers[logger_idx]

        # Edit stats dialog class
        editSpectralSettings = LoggerSpectralDialog(self, logger, logger_idx)
        editSpectralSettings.set_dialog_data()
        editSpectralSettings.show()

    def set_spectral_dashboard(self, logger):
        """Set dashboard with logger spectral settings from logger object."""

        # Stats columns
        if logger.spectral_cols is not None:
            cols_str = ' '.join([str(i) for i in logger.spectral_cols])
            self.spectralColumns.setText(cols_str)

        # Unit conversion factors
        if logger.spectral_unit_conv_factors is not None:
            unit_conv_factors_str = ' '.join([str(i) for i in logger.spectral_unit_conv_factors])
            self.spectralUnitConvs.setText(unit_conv_factors_str)

            # Stats interval
            self.spectralInterval.setText(str(logger.spectral_interval))

            # Stats start
            if logger.spectral_start is None:
                spectral_start = 'Not used'
            else:
                spectral_start = logger.spectral_start.strftime('%Y-%m-%d %H:%M')
            self.spectralStart.setText(spectral_start)

            # Stats end
            if logger.spectral_end is None:
                spectral_end = 'Not used'
            else:
                spectral_end = logger.spectral_end.strftime('%Y-%m-%d %H:%M')
            self.spectralEnd.setText(spectral_end)

            # Stats channel names
            if logger.stats_user_channel_names is not None:
                channel_items_str = ' '.join([i for i in logger.stats_user_channel_names])
            self.spectralChannelNames.setText(channel_items_str)

            # Stats units names
            if logger.stats_user_channel_units is not None:
                units_items_str = ' '.join([i for i in logger.stats_user_channel_units])
            self.spectralChannelUnits.setText(units_items_str)

    def clear_dashboard(self):
        """Initialise all values in spectral dashboard."""

        # Clear logger stats settings
        self.spectralColumns.setText('-')
        self.spectralUnitConvs.setText('-')
        self.spectralInterval.setText('-')
        self.spectralStart.setText('-')
        self.spectralEnd.setText('-')
        self.spectralChannelNames.setText('-')
        self.spectralChannelUnits.setText('-')


class CampaignInfoDialog(QtWidgets.QDialog):
    """Edit window for project and campaign data."""

    def __init__(self, parent=None, control=None):
        super(CampaignInfoDialog, self).__init__(parent)

        self.parent = parent
        self.control = control
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
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.rejected.connect(self.reject)

    def set_dialog_data(self):
        """Set dialog data with campaign info from control object."""

        control = self.control

        self.projNum.setText(control.project_num)
        self.projName.setText(control.project_name)
        self.campaignName.setText(control.campaign_name)
        self.projPath.setText(control.project_path)

    def on_ok_clicked(self):
        """Assign values to the control object and update the dashboard."""

        self.set_control_data()
        self.parent.set_campaign_dashboard()

    def set_control_data(self):
        """Assign values to the control object."""

        control = self.control

        control.project_num = self.projNum.text()
        control.project_name = self.projName.text()
        control.campaign_name = self.campaignName.text()
        control.project_path = self.projPath.text()

    def set_project_path(self):
        """Set location of project root directory."""

        file_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Project Location')

        if file_path:
            self.projPath.setText(file_path)
            os.chdir(file_path)


class LoggerPropertiesDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, logger=None, logger_idx=0):
        super(LoggerPropertiesDialog, self).__init__(parent)

        self.parent = parent

        # Logger properties object and index of selected logger in combo
        self.logger = logger
        self.logger_idx = logger_idx

        self.file_types = ['Fugro-csv',
                           'Pulse-acc',
                           'General-csv',
                           ]
        self.delimiters = ['comma',
                           'space',
                           ]

        # To hold the datetime format string detected from a test raw file, e.g. %d-%b-%Y %H:%M:%S.%f
        self.datetime_format = ''

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle('Edit Logger File Properties')
        self.setMinimumWidth(500)

        self.layout = QtWidgets.QVBoxLayout(self)
        # self.layout.addStretch()

        # Logger type group
        self.loggerType = QtWidgets.QGroupBox('Logger Type')
        self.typeForm = QtWidgets.QFormLayout(self.loggerType)
        self.loggerID = QtWidgets.QLineEdit()
        self.fileFormat = QtWidgets.QComboBox()
        self.fileFormat.setFixedWidth(100)
        self.fileFormat.addItems(self.file_types)
        self.loggerPath = QtWidgets.QTextEdit()
        self.loggerPath.setFixedHeight(40)
        self.browseButton = QtWidgets.QPushButton('Browse')

        # Detect properties button
        self.detectButton = QtWidgets.QPushButton('Detect Properties')

        # Set button sizing policy
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.browseButton.setSizePolicy(policy)
        self.detectButton.setSizePolicy(policy)

        # Logger properties group
        self.loggerProps = QtWidgets.QGroupBox('Logger Properties')
        self.propsForm = QtWidgets.QFormLayout(self.loggerProps)
        self.fileTimestampFormat = QtWidgets.QLineEdit()
        self.dataTimestampFormat = QtWidgets.QLineEdit()
        self.fileExt = QtWidgets.QLineEdit()
        self.fileExt.setFixedWidth(30)
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

        # Define input validators
        int_validator = QtGui.QIntValidator()
        int_validator.setBottom(1)
        dbl_validator = QtGui.QDoubleValidator()

        # Apply int validators
        self.numHeaderRows.setValidator(int_validator)
        self.numColumns.setValidator(int_validator)
        self.channelHeaderRow.setValidator(int_validator)
        self.unitsHeaderRow.setValidator(int_validator)
        self.loggingFreq.setValidator(int_validator)
        self.loggingDuration.setValidator(int_validator)

        self.typeForm.addRow(QtWidgets.QLabel('Logger ID:'), self.loggerID)
        self.typeForm.addRow(QtWidgets.QLabel('Logger path:'), self.loggerPath)
        self.typeForm.addRow(QtWidgets.QLabel(''), self.browseButton)
        self.typeForm.addRow(QtWidgets.QLabel('File format:'), self.fileFormat)

        self.propsForm.addRow(QtWidgets.QLabel('File timestamp:'), self.fileTimestampFormat)
        self.propsForm.addRow(QtWidgets.QLabel('Data timestamp:'), self.dataTimestampFormat)
        self.propsForm.addRow(QtWidgets.QLabel('File extension:'), self.fileExt)
        self.propsForm.addRow(QtWidgets.QLabel('File delimiter:'), self.fileDelimiter)
        self.propsForm.addRow(QtWidgets.QLabel('Number of header rows:'), self.numHeaderRows)
        self.propsForm.addRow(QtWidgets.QLabel('Number of expected columns:'), self.numColumns)
        self.propsForm.addRow(QtWidgets.QLabel('Channel header row:'), self.channelHeaderRow)
        self.propsForm.addRow(QtWidgets.QLabel('Units header row:'), self.unitsHeaderRow)
        self.propsForm.addRow(QtWidgets.QLabel('Logging frequency (Hz):'), self.loggingFreq)
        self.propsForm.addRow(QtWidgets.QLabel('Logging duration (s):'), self.loggingDuration)

        # Button box
        # self.assignButton = QtWidgets.QPushButton('Assign')
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                    QtWidgets.QDialogButtonBox.Cancel)
        # self.buttons.addButton(self.assignButton, QtWidgets.QDialogButtonBox.AcceptRole)
        # self.buttons.addButton(QtWidgets.QDialogButtonBox.Cancel)

        self.layout.addWidget(self.loggerType)
        self.layout.addWidget(self.detectButton, alignment=QtCore.Qt.AlignRight)
        self.layout.addWidget(self.loggerProps)
        self.layout.addWidget(self.buttonBox, stretch=0, alignment=QtCore.Qt.AlignRight)

    def connect_signals(self):
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.browseButton.clicked.connect(self.set_logger_path)
        self.detectButton.clicked.connect(self.detect_properties)

    def set_dialog_data(self):
        """Set dialog data with logger properties from control object."""

        delimiters_dict = {',': 'comma',
                           ' ': 'space',
                           }

        # Logger properties object of selected logger
        logger = self.logger

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

    def on_ok_clicked(self):
        """Assign logger properties to the control object and update the dashboard."""

        self.set_control_data()
        self.parent.set_logger_dashboard(self.logger)
        self.parent.update_logger_id_list(self.logger.logger_id, self.logger_idx)

    def set_control_data(self):
        """Assign values to the control object."""

        delimiters_dict = {'comma': ',',
                           'space': ' ',
                           }

        logger = self.logger

        # Assign form values to control logger object
        logger.logger_id = self.loggerID.text()
        logger.file_format = self.fileFormat.currentText()
        logger.logger_path = self.loggerPath.toPlainText()
        logger.file_timestamp_format = self.fileTimestampFormat.text()
        logger.timestamp_format = self.dataTimestampFormat.text()
        logger.datetime_format = self.datetime_format
        logger.file_ext = self.fileExt.text()
        logger.file_delimiter = delimiters_dict[self.fileDelimiter.currentText()]
        logger.num_headers = int(self.numHeaderRows.text())
        logger.num_columns = int(self.numColumns.text())
        logger.channel_header_row = int(self.channelHeaderRow.text())
        logger.units_header_row = int(self.unitsHeaderRow.text())
        logger.freq = int(self.loggingFreq.text())
        logger.duration = int(self.loggingDuration.text())

    def set_logger_path(self):
        """Set location of project root directory."""

        logger_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Logger Location')

        if logger_path:
            self.loggerPath.setText(logger_path)

    def detect_properties(self):
        """Detect standard logger properties for selected file format."""

        logger_id = self.loggerID.text()
        file_format = self.fileFormat.currentText()
        logger_path = self.loggerPath.toPlainText()

        if not os.path.exists(logger_path):
            msg = 'Logger path does not exist. Set a logger path first.'
            return QtWidgets.QMessageBox.information(self, 'Detect Logger Properties', msg)

        # Create a test logger object to assign properties since we do not want to
        # assign them to the control object until the dialog OK button is clicked
        test_logger = LoggerProperties(logger_id)
        test_logger.logger_path = logger_path

        try:
            if file_format == 'Fugro-csv':
                self.set_fugro_file_format(test_logger)
                self.detect_fugro_file_props(test_logger)
            elif file_format == 'Pulse-acc':
                pass
            else:
                pass
        except LoggerError as e:
            QtWidgets.QMessageBox.warning(self, 'Error', str(e))
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, 'Error', str(e))

    def set_fugro_file_format(self, test_logger):
        """
        Set Fugro file format standard properties.
        :param logger: LoggerProperties object
        :return:
        """

        # Assign Fugro standard logger properties
        test_logger = set_fugro_file_format(test_logger)

        # Set edit dialog values
        self.fileExt.setText(test_logger.file_ext)
        self.fileDelimiter.setCurrentText('comma')
        self.numHeaderRows.setText(str(test_logger.num_headers))
        self.channelHeaderRow.setText(str(test_logger.channel_header_row))
        self.unitsHeaderRow.setText(str(test_logger.units_header_row))

    def detect_fugro_file_props(self, test_logger):
        """
        For Fugro logger file detect:
            sampling frequency
            timestamp format (user style format string)
            datetime format (datetime/pandas format string)
            expected number of columns
            expected logging duration
        """

        test_logger = test_logger.detect_fugro_logger_properties(test_logger)

        # Assign detected properties to edit dialog
        self.loggingFreq.setText(str(test_logger.freq))
        self.dataTimestampFormat.setText(test_logger.timestamp_format)
        self.datetime_format = test_logger.datetime_format
        self.numColumns.setText(str(test_logger.num_columns))
        self.loggingDuration.setText(str(test_logger.duration))


class LoggerStatsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, logger=None, logger_idx=0):
        super(LoggerStatsDialog, self).__init__(parent)

        self.parent = parent

        # Logger properties object and index of selected logger in combo
        self.logger = logger
        self.logger_idx = logger_idx

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle('Edit Logger Statistics Analysis Settings')
        self.setMinimumWidth(500)

        self.layout = QtWidgets.QVBoxLayout(self)

        # Logger stats group
        self.loggerStats = QtWidgets.QGroupBox('Logger Statistics Settings')
        self.form = QtWidgets.QFormLayout(self.loggerStats)
        self.statsColumns = QtWidgets.QLineEdit()
        self.statsUnitConvs = QtWidgets.QLineEdit()
        self.statsInterval = QtWidgets.QLineEdit()
        self.statsInterval.setFixedWidth(40)
        self.statsStart = QtWidgets.QLineEdit()
        self.statsStart.setFixedWidth(100)
        self.statsEnd = QtWidgets.QLineEdit()
        self.statsEnd.setFixedWidth(100)
        self.statsChannelNames = QtWidgets.QLineEdit()
        self.statsChannelUnits = QtWidgets.QLineEdit()

        # Define input validators
        int_validator = QtGui.QIntValidator()
        int_validator.setBottom(1)
        dbl_validator = QtGui.QDoubleValidator()

        # Apply float validators
        self.statsInterval.setValidator(int_validator)

        self.form.addRow(QtWidgets.QLabel('Stats columns:'), self.statsColumns)
        self.form.addRow(QtWidgets.QLabel('Stats unit conversion factors:'), self.statsUnitConvs)
        self.form.addRow(QtWidgets.QLabel('Stats interval (s):'), self.statsInterval)
        self.form.addRow(QtWidgets.QLabel('Stats start timestamp:'), self.statsStart)
        self.form.addRow(QtWidgets.QLabel('Stats end timestamp:'), self.statsEnd)
        self.form.addRow(QtWidgets.QLabel('Channel names:'), self.statsChannelNames)
        self.form.addRow(QtWidgets.QLabel('Channel units:'), self.statsChannelUnits)

        # Button box
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                    QtWidgets.QDialogButtonBox.Cancel)

        self.layout.addWidget(self.loggerStats)
        self.layout.addWidget(self.buttonBox, stretch=0, alignment=QtCore.Qt.AlignRight)

    def connect_signals(self):
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def set_dialog_data(self):
        """Set dialog data with logger stats from control object."""

        logger = self.logger

        # Stats columns
        cols_str = ' '.join([str(i) for i in logger.stats_cols])
        self.statsColumns.setText(cols_str)

        # Unit conversion factors
        unit_conv_factors_str = ' '.join([str(i) for i in logger.stats_unit_conv_factors])
        self.statsUnitConvs.setText(unit_conv_factors_str)

        # Stats interval
        self.statsInterval.setText(str(logger.stats_interval))

        # Stats start
        if logger.stats_start is None:
            stats_start = 'Not used'
        else:
            stats_start = logger.stats_start.strftime('%Y-%m-%d %H:%M')
        self.statsStart.setText(stats_start)

        # Stats end
        if logger.stats_end is None:
            stats_end = 'Not used'
        else:
            stats_end = logger.stats_end.strftime('%Y-%m-%d %H:%M')
        self.statsEnd.setText(stats_end)

        # Channel and units names
        channel_items_str = ' '.join([i for i in logger.stats_user_channel_names])
        self.statsChannelNames.setText(channel_items_str)
        units_items_str = ' '.join([i for i in logger.stats_user_channel_units])
        self.statsChannelUnits.setText(units_items_str)

    def on_ok_clicked(self):
        """Assign logger stats settings to the control object and update the dashboard."""

        self.set_control_data()
        self.parent.set_stats_dashboard(self.logger)

    def set_control_data(self):
        """Assign values to the control object."""

        logger = self.logger

        # Assign form values to control logger object - convert strings to appropriate data type
        logger.stats_cols = list(map(int, self.statsColumns.text().split()))
        logger.stats_unit_conv_factors = list(map(float, self.statsUnitConvs.text().split()))
        logger.stats_interval = int(self.statsInterval.text())

        stats_start = self.statsStart.text()
        curr_start = logger.stats_start
        if stats_start == '' or stats_start == 'Not used':
            logger.stats_start = None
        else:
            try:
                logger.stats_start = parse(stats_start, yearfirst=True)
            except ValueError:
                logger.stats_start = curr_start
                msg = 'Stats start datetime format not recognised; timestamp unchanged'
                QtWidgets.QMessageBox.information(self, 'Stats Start Input', msg)

        stats_end = self.statsEnd.text()
        curr_end = logger.stats_end
        if stats_end == '' or stats_end == 'Not used':
            logger.stats_end = None
        else:
            try:
                logger.stats_end = parse(stats_end, yearfirst=True)
            except ValueError:
                logger.stats_end = curr_end
                msg = 'Stats end datetime format not recognised; timestamp unchanged'
                QtWidgets.QMessageBox.information(self, 'Stats End Input', msg)

        logger.stats_user_channel_names = self.statsChannelNames.text().split()
        logger.stats_user_channel_units = self.statsChannelUnits.text().split()


class LoggerSpectralDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, logger=None, logger_idx=0):
        super(LoggerSpectralDialog, self).__init__(parent)

        self.parent = parent

        # Logger properties object and index of selected logger in combo
        self.logger = logger
        self.logger_idx = logger_idx

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.setWindowTitle('Edit Logger Spectral Analysis Settings')
        self.setMinimumWidth(500)

        self.layout = QtWidgets.QVBoxLayout(self)

        # Logger stats group
        self.loggerSpectral = QtWidgets.QGroupBox('Logger Spectral Settings')
        self.form = QtWidgets.QFormLayout(self.loggerSpectral)
        self.spectralColumns = QtWidgets.QLineEdit()
        self.spectralUnitConvs = QtWidgets.QLineEdit()
        self.spectralInterval = QtWidgets.QLineEdit()
        self.spectralInterval.setFixedWidth(40)
        self.spectralStart = QtWidgets.QLineEdit()
        self.spectralStart.setFixedWidth(100)
        self.spectralEnd = QtWidgets.QLineEdit()
        self.spectralEnd.setFixedWidth(100)
        self.spectralChannelNames = QtWidgets.QLineEdit()
        self.spectralChannelUnits = QtWidgets.QLineEdit()

        # Define input validators
        int_validator = QtGui.QIntValidator()
        int_validator.setBottom(1)
        dbl_validator = QtGui.QDoubleValidator()

        # Apply float validators
        self.spectralInterval.setValidator(int_validator)

        self.form.addRow(QtWidgets.QLabel('Columns:'), self.spectralColumns)
        self.form.addRow(QtWidgets.QLabel('Unit conversion factors:'), self.spectralUnitConvs)
        self.form.addRow(QtWidgets.QLabel('Interval (s):'), self.spectralInterval)
        self.form.addRow(QtWidgets.QLabel('Start timestamp:'), self.spectralStart)
        self.form.addRow(QtWidgets.QLabel('End timestamp:'), self.spectralEnd)
        self.form.addRow(QtWidgets.QLabel('Channel names:'), self.spectralChannelNames)
        self.form.addRow(QtWidgets.QLabel('Channel units:'), self.spectralChannelUnits)

        # Button box
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                    QtWidgets.QDialogButtonBox.Cancel)

        self.layout.addWidget(self.loggerSpectral)
        self.layout.addWidget(self.buttonBox, stretch=0, alignment=QtCore.Qt.AlignRight)

    def connect_signals(self):
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def set_dialog_data(self):
        """Set dialog data with logger spectral settings from control object."""

        logger = self.logger

        # Stats columns
        cols_str = ' '.join([str(i) for i in logger.spectral_cols])
        self.spectralColumns.setText(cols_str)

        # Unit conversion factors
        unit_conv_factors_str = ' '.join([str(i) for i in logger.spectral_unit_conv_factors])
        self.spectralUnitConvs.setText(unit_conv_factors_str)

        # Stats interval
        self.spectralInterval.setText(str(logger.spectral_interval))

        # Stats start
        if logger.spectral_start is None:
            spectral_start = 'Not used'
        else:
            spectral_start = logger.spectral_start.strftime('%Y-%m-%d %H:%M')
        self.spectralStart.setText(spectral_start)

        # Stats end
        if logger.spectral_end is None:
            spectral_end = 'Not used'
        else:
            spectral_end = logger.spectral_end.strftime('%Y-%m-%d %H:%M')
        self.spectralEnd.setText(spectral_end)

        # Channel and units names
        channel_items_str = ' '.join([i for i in logger.stats_user_channel_names])
        self.spectralChannelNames.setText(channel_items_str)
        units_items_str = ' '.join([i for i in logger.stats_user_channel_units])
        self.spectralChannelUnits.setText(units_items_str)

    def on_ok_clicked(self):
        """Assign logger spectral settings to the control object and update the dashboard."""

        self.set_control_data()
        self.parent.set_spectral_dashboard(self.logger)

    def set_control_data(self):
        """Assign values to the control object."""

        logger = self.logger

        # Assign form values to control logger object - convert strings to appropriate data type
        logger.spectral_cols = list(map(int, self.spectralColumns.text().split()))
        logger.spectral_unit_conv_factors = list(map(float, self.spectralUnitConvs.text().split()))
        logger.spectral_interval = int(self.spectralInterval.text())

        spectral_start = self.spectralStart.text()
        curr_start = logger.spectral_start
        if spectral_start == '' or spectral_start == 'Not used':
            logger.spectral_start = None
        else:
            try:
                logger.spectral_start = parse(spectral_start, yearfirst=True)
            except ValueError:
                logger.spectral_start = curr_start
                msg = 'Spectral start datetime format not recognised; timestamp unchanged'
                QtWidgets.QMessageBox.information(self, 'Spectral Start Input', msg)

        spectral_end = self.spectralEnd.text()
        curr_end = logger.spectral_end
        if spectral_end == '' or spectral_end == 'Not used':
            logger.spectral_end = None
        else:
            try:
                logger.spectral_end = parse(spectral_end, yearfirst=True)
            except ValueError:
                logger.spectral_end = curr_end
                msg = 'Spectral end datetime format not recognised; timestamp unchanged'
                QtWidgets.QMessageBox.information(self, 'Spectral End Input', msg)

        logger.stats_user_channel_names = self.spectralChannelNames.text().split()
        logger.stats_user_channel_units = self.spectralChannelUnits.text().split()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # win = ProjectConfigModule()
    win = LoggerPropertiesDialog()
    # win = LoggerStatsDialog()
    # win = LoggerSpectralDialog()
    win.show()
    app.exit(app.exec_())
