"""
Project config dashboard widget. Handles all project setup.
"""
__author__ = 'Craig Dickinson'

import json
import logging
import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets
from dateutil.parser import parse

from core.control_file import ControlFile, InputError
from core.custom_date import get_datetime_format
from core.fugro_csv_properties import detect_fugro_logger_properties, set_fugro_csv_file_format, \
    set_general_csv_file_format
from core.logger_properties import LoggerError, LoggerProperties
from core.pulse_acc_properties import detect_pulse_logger_properties, set_pulse_acc_file_format


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

            # Add logger stats and spectral settings
            dict_props = self.add_logger_analysis_settings(logger, dict_props)

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
        dict_props['all_channel_names'] = logger.all_channel_names
        dict_props['all_channel_units'] = logger.all_channel_units

        return dict_props

    def add_logger_analysis_settings(self, logger, dict_props):
        """Add control object logger stats and spectral settings to JSON dictionary."""

        # Processed columns group
        dict_props['requested_columns'] = logger.requested_cols
        dict_props['unit_convs'] = logger.unit_conv_factors
        dict_props['user_channel_names'] = logger.user_channel_names
        dict_props['user_channel_units'] = logger.user_channel_units

        # Stats settings group
        dict_props['process_stats'] = logger.process_stats
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

        # Stats low and high cut-off frequencies
        dict_props['stats_low_cutoff_freq'] = logger.stats_low_cutoff_freq
        dict_props['stats_high_cutoff_freq'] = logger.stats_high_cutoff_freq

        # Spectral settings group
        dict_props['process_spectral'] = logger.process_spectral
        dict_props['spectral_interval'] = logger.spectral_interval

        # Spectral start
        if logger.spectral_start is None:
            dict_props['spectral_start'] = None
        else:
            dict_props['spectral_start'] = logger.spectral_start.strftime('%Y-%m-%d %H:%M')

        # Spectral end
        if logger.spectral_end is None:
            dict_props['spectral_end'] = None
        else:
            dict_props['spectral_end'] = logger.spectral_end.strftime('%Y-%m-%d %H:%M')

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
        self.skip_on_logger_item_edited = False

        # JSON config class - hold config data dictionary
        self.config = ProjectConfigJSONFile()
        self.control = ControlFile()
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.layout = QtWidgets.QGridLayout(self)

        # Container for load and save buttons and logger select drop down
        self.configButtonsWidget = QtWidgets.QWidget()

        self.loadConfigButton = QtWidgets.QPushButton('&Load')
        self.saveConfigButton = QtWidgets.QPushButton('&Save')
        # spacerItem = QtWidgets.QSpacerItem(40, 1)

        hbox = QtWidgets.QHBoxLayout(self.configButtonsWidget)
        hbox.addWidget(QtWidgets.QLabel('Config File:'))
        hbox.addWidget(self.loadConfigButton)
        hbox.addWidget(self.saveConfigButton)
        # hbox.addItem(spacerItem)

        # Loggers list group
        self.loggersGroup = QtWidgets.QGroupBox('Campaign Loggers')
        self.loggersGroup.setFixedWidth(180)

        self.addLoggerButton = QtWidgets.QPushButton('Add Logger')
        self.remLoggerButton = QtWidgets.QPushButton('Remove Logger')
        self.loggersList = QtWidgets.QListWidget()
        self.columnsList = QtWidgets.QListWidget()

        self.vbox = QtWidgets.QVBoxLayout(self.loggersGroup)
        self.vbox.addWidget(self.addLoggerButton)
        self.vbox.addWidget(self.remLoggerButton)
        self.vbox.addWidget(QtWidgets.QLabel('Project Loggers'))
        self.vbox.addWidget(self.loggersList)
        self.vbox.addWidget(QtWidgets.QLabel('Logger Header Details'))
        self.vbox.addWidget(self.columnsList)

        # Config tab widgets
        self.setupTabs = QtWidgets.QTabWidget()
        self.campaignTab = CampaignInfoTab(self)
        self.loggerPropsTab = LoggerPropertiesTab(self)
        self.analysisTab = StatsAndSpectralSettingsTab(self)

        self.setupTabs.addTab(self.campaignTab, 'Campaign Info')
        self.setupTabs.addTab(self.loggerPropsTab, 'Logger File Properties')
        self.setupTabs.addTab(self.analysisTab, 'Statistical and Spectral Analysis')

        self.newProjButton = QtWidgets.QPushButton('&New Project')

        # Run analysis group
        self.runWidget = QtWidgets.QWidget()

        self.runGroup = QtWidgets.QGroupBox('Selected Analysis')
        self.statsChkBox = QtWidgets.QCheckBox('Statistical Analysis')
        self.spectralChkBox = QtWidgets.QCheckBox('Spectral Analysis')

        self.vbox2 = QtWidgets.QVBoxLayout(self.runGroup)
        self.vbox2.addWidget(self.statsChkBox)
        self.vbox2.addWidget(self.spectralChkBox)

        self.processButton = QtWidgets.QPushButton('Process')

        self.vbox1 = QtWidgets.QVBoxLayout(self.runWidget)
        self.vbox1.addWidget(self.runGroup)
        self.vbox1.addWidget(self.processButton)

        # Main layout
        self.layout.addWidget(self.configButtonsWidget, 0, 0, 1, 2, QtCore.Qt.AlignLeft)
        self.layout.addWidget(self.loggersGroup, 1, 0)
        self.layout.addWidget(self.setupTabs, 1, 1)
        self.layout.addWidget(self.newProjButton, 2, 0, QtCore.Qt.AlignLeft)
        self.layout.addWidget(self.runWidget, 1, 2, QtCore.Qt.AlignTop)

    def connect_signals(self):
        self.loadConfigButton.clicked.connect(self.load_config_file)
        self.saveConfigButton.clicked.connect(self.save_config_file)
        self.addLoggerButton.clicked.connect(self.add_logger)
        self.remLoggerButton.clicked.connect(self.remove_logger)
        self.loggersList.itemClicked.connect(self.on_logger_selected)
        self.loggersList.itemChanged.connect(self.on_logger_item_edited)
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
                self.control = self.map_campaign_json_section(data, self.control)
                self.control = self.map_loggers_json_section(data, self.control)
                self.set_dashboards()
                self.set_window_title(filename)
            except InputError as e:
                self.parent.error(str(e))
                logging.exception(e)
            except Exception as e:
                msg = 'Unexpected error loading config file'
                self.parent.error(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
                logging.exception(e)

    def save_config_file(self):
        """Save project configuration settings as a dictionary to a JSON file."""

        if self.control.project_num == '':
            msg = 'Project number required to create project config file. Add data to the Campaign Info tab.'
            return self.parent.warning(msg)

        if self.control.project_name == '':
            msg = 'Project name required to create project config file. Input data to the Campaign Info tab.'
            return self.parent.warning(msg)

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

    def add_logger(self):
        """Add new logger to list. Initial logger name format is 'Logger n'."""

        n = self.loggersList.count()
        logger_id = f'Logger {n + 1}'

        # Create logger properties object and append to loggers list in control object
        logger = LoggerProperties(logger_id)
        self.control.loggers.append(logger)

        # Initialise logger file as a Fugro logger format
        set_fugro_csv_file_format(logger)

        item = QtWidgets.QListWidgetItem(logger_id)
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        self.loggersList.addItem(item)

        # TODO: Address that adding item triggers combo box change which sets dashboards values before confirmed by user
        self.loggersList.setCurrentRow(n)

        # Open logger properties edit widget
        self.setupTabs.setCurrentWidget(self.loggerPropsTab)
        self.loggerPropsTab.show_edit_dialog()

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
        msg = f'Are you sure you want to remove the logger {logger}?'
        response = QtWidgets.QMessageBox.question(self, 'Remove Logger', msg)

        if response == QtWidgets.QMessageBox.Yes:
            # Remove logger from control object
            logger = self.control.loggers[i]
            self.control.loggers.remove(logger)

            # Remove logger from loggers list
            self.loggersList.takeItem(i)

            if self.loggersList.count() == 0:
                self.new_project()

    def on_logger_selected(self):
        """Update dashboard data pertaining to selected logger."""

        logger_idx = self.loggersList.currentRow()
        logger = self.control.loggers[logger_idx]
        self.loggerPropsTab.set_logger_dashboard(logger)
        self.analysisTab.set_analysis_dashboard(logger)
        self.set_logger_header_list(logger)

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

    def update_logger_id_list(self, logger_id, logger_idx):
        """Update logger name in the loggers list if logger id in edit dialog is changed."""

        # Set flag to skip logger list item edited action when triggered
        self.skip_on_logger_item_edited = True
        self.loggersList.item(logger_idx).setText(logger_id)
        self.skip_on_logger_item_edited = False

    def set_logger_header_list(self, logger):
        """Populate logger header details list with the header info from a test file."""

        self.columnsList.clear()
        channels = logger.all_channel_names
        units = logger.all_channel_units

        # Populate list widget if channels list is not empty
        if channels:
            items = ['1. Timestamp'] + [f'{i + 2}. {c} ({u})' for i, (c, u) in enumerate(zip(channels, units))]
            for i in items:
                item = QtWidgets.QListWidgetItem(i)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
                self.columnsList.addItem(item)

    def new_project(self):
        """Clear project control object and all config dashboard values."""

        # Create new control object and map to campaign, logger properties and analysis tabs
        self.control = ControlFile()
        self.campaignTab.control = self.control
        self.loggerPropsTab.control = self.control
        self.analysisTab.control = self.control

        # Clear logger combo box
        # Note: This will trigger the clearing of the logger properties, stats and spectral dashboards
        self.loggersList.clear()
        self.columnsList.clear()

        # Clear campaign data dashboard and update window title to include config file path
        self.campaignTab.clear_dashboard()
        self.loggerPropsTab.clear_dashboard()
        self.analysisTab.clear_dashboard()

        # Reset window title
        self.set_window_title()

    def run_analysis(self):
        """Run DataLab processing engine - call function in main DataLab class."""

        self.parent.analyse_config_setup(self.control)

    def map_campaign_json_section(self, data, control):
        """Map the config campaign section to the control object."""

        key = 'campaign'
        if key in data.keys():
            data = data[key]
        else:
            msg = f'\'{key}\' key not found in config file'
            self.parent.warning(msg)
            return control

        control.project_num = self.get_key_value(logger_id=key,
                                                 data=data,
                                                 key='project_number',
                                                 attr=self.control.project_num)
        control.project_name = self.get_key_value(logger_id=key,
                                                  data=data,
                                                  key='project_name',
                                                  attr=self.control.project_name)
        control.campaign_name = self.get_key_value(logger_id=key,
                                                   data=data,
                                                   key='campaign_name',
                                                   attr=control.campaign_name)
        control.project_path = self.get_key_value(logger_id=key,
                                                  data=data,
                                                  key='project_location',
                                                  attr=control.project_path)
        control.output_folder = os.path.join(control.project_path, 'Output')
        control.config_file = self.config.filename

        return control

    def map_loggers_json_section(self, data, control):
        """Map the config loggers section to the control object for all logger."""

        key = 'loggers'
        if key in data.keys():
            data = data[key]
        else:
            msg = f'\'{key}\' key not found in config file'
            self.parent.warning(msg)
            return control

        for logger_id, dict_logger in data.items():
            # Create new logger properties object and assign attributes from JSON dictionary
            logger = LoggerProperties()
            logger.logger_id = logger_id

            # Logger properties
            logger = self.map_logger_props(logger, dict_logger)

            # Logger columns to process settings
            logger = self.map_logger_requested_cols_settings(logger, dict_logger)

            # Logger stats settings
            logger = self.map_logger_stats_settings(logger, dict_logger)

            # Logger spectral settings
            logger = self.map_logger_spectral_settings(logger, dict_logger)

            # Finally, assign logger to control object
            control.logger_ids.append(logger_id)
            control.logger_ids_upper.append(logger_id.upper())
            control.loggers.append(logger)

        return control

    def map_logger_props(self, logger, dict_logger):
        """Retrieve logger properties from JSON dictionary and map to logger object."""

        logger.file_format = self.get_key_value(logger_id=logger.logger_id,
                                                data=dict_logger,
                                                key='file_format',
                                                attr=logger.file_format)
        logger.logger_path = self.get_key_value(logger_id=logger.logger_id,
                                                data=dict_logger,
                                                key='logger_path',
                                                attr=logger.logger_path)
        logger.file_timestamp_format = self.get_key_value(logger_id=logger.logger_id,
                                                          data=dict_logger,
                                                          key='file_timestamp_format',
                                                          attr=logger.file_timestamp_format)
        logger.timestamp_format = self.get_key_value(logger_id=logger.logger_id,
                                                     data=dict_logger,
                                                     key='data_timestamp_format',
                                                     attr=logger.timestamp_format)
        logger.datetime_format = self.get_key_value(logger_id=logger.logger_id,
                                                    data=dict_logger,
                                                    key='data_datetime_format',
                                                    attr=logger.datetime_format)
        logger.file_ext = self.get_key_value(logger_id=logger.logger_id,
                                             data=dict_logger,
                                             key='file_ext',
                                             attr=logger.file_ext)
        logger.file_delimiter = self.get_key_value(logger_id=logger.logger_id,
                                                   data=dict_logger,
                                                   key='file_delimiter',
                                                   attr=logger.file_delimiter)
        logger.num_headers = self.get_key_value(logger_id=logger.logger_id,
                                                data=dict_logger,
                                                key='num_header_rows',
                                                attr=logger.num_headers)
        logger.num_columns = self.get_key_value(logger_id=logger.logger_id,
                                                data=dict_logger,
                                                key='num_columns',
                                                attr=logger.num_columns)
        logger.channel_header_row = self.get_key_value(logger_id=logger.logger_id,
                                                       data=dict_logger,
                                                       key='channel_header_row',
                                                       attr=logger.channel_header_row)
        logger.units_header_row = self.get_key_value(logger_id=logger.logger_id,
                                                     data=dict_logger,
                                                     key='units_header_row',
                                                     attr=logger.units_header_row)
        logger.freq = self.get_key_value(logger_id=logger.logger_id,
                                         data=dict_logger,
                                         key='logging_freq',
                                         attr=logger.freq)
        logger.duration = self.get_key_value(logger_id=logger.logger_id,
                                             data=dict_logger,
                                             key='logging_duration',
                                             attr=logger.duration)
        logger.all_channel_names = self.get_key_value(logger_id=logger.logger_id,
                                                      data=dict_logger,
                                                      key='all_channel_names',
                                                      attr=logger.all_channel_names)
        logger.all_channel_units = self.get_key_value(logger_id=logger.logger_id,
                                                      data=dict_logger,
                                                      key='all_channel_units',
                                                      attr=logger.all_channel_units)

        return logger

    def map_logger_requested_cols_settings(self, logger, dict_logger):
        """Retrieve logger requested columns settings from JSON dictionary and map to logger object."""

        logger.requested_cols = self.get_key_value(logger_id=logger.logger_id,
                                                   data=dict_logger,
                                                   key='requested_columns',
                                                   attr=logger.requested_cols)
        logger.unit_conv_factors = self.get_key_value(logger_id=logger.logger_id,
                                                      data=dict_logger,
                                                      key='unit_convs',
                                                      attr=logger.unit_conv_factors)
        logger.user_channel_names = self.get_key_value(logger_id=logger.logger_id,
                                                       data=dict_logger,
                                                       key='user_channel_names',
                                                       attr=logger.user_channel_names)
        logger.user_channel_units = self.get_key_value(logger_id=logger.logger_id,
                                                       data=dict_logger,
                                                       key='user_channel_units',
                                                       attr=logger.user_channel_units)
        return logger

    def map_logger_stats_settings(self, logger, dict_logger):
        """Retrieve logger stats settings from JSON dictionary and map to logger object."""

        logger.process_stats = self.get_key_value(logger_id=logger.logger_id,
                                                  data=dict_logger,
                                                  key='process_stats',
                                                  attr=logger.process_stats)
        logger.stats_interval = self.get_key_value(logger_id=logger.logger_id,
                                                   data=dict_logger,
                                                   key='stats_interval',
                                                   attr=logger.stats_interval)
        stats_start = self.get_key_value(logger_id=logger.logger_id,
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

        stats_end = self.get_key_value(logger_id=logger.logger_id,
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

        logger.stats_low_cutoff_freq = self.get_key_value(logger_id=logger.logger_id,
                                                          data=dict_logger,
                                                          key='stats_low_cutoff_freq',
                                                          attr=logger.stats_low_cutoff_freq)
        logger.stats_high_cutoff_freq = self.get_key_value(logger_id=logger.logger_id,
                                                           data=dict_logger,
                                                           key='stats_high_cutoff_freq',
                                                           attr=logger.stats_high_cutoff_freq)

        return logger

    def map_logger_spectral_settings(self, logger, dict_logger):
        """Retrieve logger spectral settings from JSON dictionary and map to logger object."""

        logger.process_spectral = self.get_key_value(logger_id=logger.logger_id,
                                                     data=dict_logger,
                                                     key='process_spectral',
                                                     attr=logger.process_spectral)
        logger.spectral_interval = self.get_key_value(logger_id=logger.logger_id,
                                                      data=dict_logger,
                                                      key='spectral_interval',
                                                      attr=logger.spectral_interval)
        spectral_start = self.get_key_value(logger_id=logger.logger_id,
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

        spectral_end = self.get_key_value(logger_id=logger.logger_id,
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

        return logger

    def get_key_value(self, logger_id, data, key, attr=None):
        """Assign data from a JSON key to control object attribute."""

        if key in data.keys():
            return data[key]
        else:
            self.parent.warning(f'{key} key not found in config file for {logger_id} logger')
            return attr

    def set_dashboards(self):
        """Set dashboard values with data in control object after loading JSON file."""

        # First need to map the newly loaded control object to campaignTab and loggerTab
        self.campaignTab.control = self.control
        self.loggerPropsTab.control = self.control
        self.analysisTab.control = self.control

        # Set campaign data to dashboard
        self.campaignTab.set_campaign_dashboard()

        self.loggersList.clear()
        self.columnsList.clear()

        # Add loggers to logger list if loggers have been loaded to the control object
        if self.control.loggers:
            for logger_id in self.control.logger_ids:
                item = QtWidgets.QListWidgetItem(logger_id)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                self.loggersList.addItem(item)

            # Select first logger and set dashboards
            self.loggersList.setCurrentRow(0)
            logger = self.control.loggers[0]

            self.loggerPropsTab.set_logger_dashboard(logger)
            self.analysisTab.set_analysis_dashboard(logger)
            self.set_logger_header_list(logger)

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

        self.editButton = QtWidgets.QPushButton('Edit Data')
        self.editButton.setShortcut('Ctrl+E')
        self.projNum = QtWidgets.QLabel('-')
        self.projNum.setFixedWidth(40)
        self.projName = QtWidgets.QLabel('-')
        self.campaignName = QtWidgets.QLabel('-')
        self.projPath = QtWidgets.QLabel('-')
        self.projPath.setWordWrap(True)
        self.configFile = QtWidgets.QLabel('-')

        self.form = QtWidgets.QFormLayout(self.group)
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
        editInfo = EditCampaignInfoDialog(self, self.control)
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

    delims_logger_to_gui = {',': 'comma',
                            ' ': 'space',
                            }

    def __init__(self, parent=None):
        super(LoggerPropertiesTab, self).__init__(parent)

        self.parent = parent

        # Map control object containing all setup data
        self.control = self.parent.control
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Create widget layout."""

        self.layout = QtWidgets.QVBoxLayout(self)

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
        self.layout.addWidget(self.loggerPropsGroup)

    def connect_signals(self):
        self.editButton.clicked.connect(self.show_edit_dialog)

    def show_edit_dialog(self):
        """Open logger properties edit form."""

        if self.parent.loggersList.count() == 0:
            msg = f'No loggers exist to edit. Add a logger first.'
            return QtWidgets.QMessageBox.information(self, 'Edit Logger Properties', msg)

        # Retrieve selected logger object
        # TODO: If adding logger, dialog should show new logger id - works but if remove one first, id may not be unique
        logger_idx = self.parent.loggersList.currentRow()
        logger = self.control.loggers[logger_idx]

        # Create edit logger properties dialog window instance
        editLoggerProps = EditLoggerPropertiesDialog(self, logger, logger_idx)
        editLoggerProps.show()

    def set_logger_dashboard(self, logger):
        """Set dashboard with logger properties from logger object."""

        self.loggerID.setText(logger.logger_id)
        self.fileFormat.setText(logger.file_format)
        self.loggerPath.setText(logger.logger_path)
        self.fileTimestampFormat.setText(logger.file_timestamp_format)
        self.dataTimestampFormat.setText(logger.timestamp_format)
        self.fileExt.setText(logger.file_ext)
        self.fileDelimiter.setText(self.delims_logger_to_gui[logger.file_delimiter])
        self.numHeaderRows.setText(str(logger.num_headers))
        self.numColumns.setText(str(logger.num_columns))
        self.channelHeaderRow.setText(str(logger.channel_header_row))
        self.unitsHeaderRow.setText(str(logger.units_header_row))
        self.loggingFreq.setText(str(logger.freq))
        self.loggingDuration.setText(str(logger.duration))

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


class StatsAndSpectralSettingsTab(QtWidgets.QWidget):
    """GUI screen to control project setup."""

    def __init__(self, parent=None):
        super(StatsAndSpectralSettingsTab, self).__init__(parent)

        self.parent = parent
        self.control = self.parent.control
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Create widget layout."""

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setAlignment(QtCore.Qt.AlignTop)

        self.editButton = QtWidgets.QPushButton('Edit Data')
        self.editButton.setShortcut('Ctrl+E')

        # Processed columns group
        self.colsGroup = QtWidgets.QGroupBox('Processed Columns')
        self.columns = QtWidgets.QLabel('-')
        self.unitConvs = QtWidgets.QLabel('-')
        self.channelNames = QtWidgets.QLabel('-')
        self.channelUnits = QtWidgets.QLabel('-')

        self.colsForm = QtWidgets.QFormLayout(self.colsGroup)
        self.colsForm.addRow(QtWidgets.QLabel('Requested columns:'), self.columns)
        self.colsForm.addRow(QtWidgets.QLabel('Unit conversion factors:'), self.unitConvs)
        self.colsForm.addRow(QtWidgets.QLabel('Channel names override (optional):'), self.channelNames)
        self.colsForm.addRow(QtWidgets.QLabel('Channel units override (optional):'), self.channelUnits)

        # Stats settings group
        self.statsGroup = QtWidgets.QGroupBox('Statistical Analysis Settings')
        self.processStatsChkBox = QtWidgets.QCheckBox('Include in processing')
        self.processStatsChkBox.setChecked(True)
        self.statsInterval = QtWidgets.QLabel('-')
        self.statsStart = QtWidgets.QLabel('-')
        self.statsEnd = QtWidgets.QLabel('-')

        # Filtered RMS lower and upper cut-off frequencies
        self.lowCutoff = QtWidgets.QLabel('-')
        self.highCutoff = QtWidgets.QLabel('-')

        self.statsForm = QtWidgets.QFormLayout(self.statsGroup)
        self.statsForm.addRow(self.processStatsChkBox, QtWidgets.QLabel(''))
        self.statsForm.addRow(QtWidgets.QLabel('Interval (s):'), self.statsInterval)
        self.statsForm.addRow(QtWidgets.QLabel('Start timestamp:'), self.statsStart)
        self.statsForm.addRow(QtWidgets.QLabel('End timestamp:'), self.statsEnd)
        self.statsForm.addRow(QtWidgets.QLabel('Low frequency cut-off (Hz):'), self.lowCutoff)
        self.statsForm.addRow(QtWidgets.QLabel('High frequency cut-off (Hz):'), self.highCutoff)

        # Spectral settings group
        self.spectralGroup = QtWidgets.QGroupBox('Spectral Analysis Settings')
        self.processSpectralChkBox = QtWidgets.QCheckBox('Include in processing')
        self.processSpectralChkBox.setChecked(True)
        self.spectralInterval = QtWidgets.QLabel('-')
        self.spectralStart = QtWidgets.QLabel('-')
        self.spectralEnd = QtWidgets.QLabel('-')

        self.spectralForm = QtWidgets.QFormLayout(self.spectralGroup)
        self.spectralForm.addRow(self.processSpectralChkBox, QtWidgets.QLabel(''))
        self.spectralForm.addRow(QtWidgets.QLabel('Interval (s):'), self.spectralInterval)
        self.spectralForm.addRow(QtWidgets.QLabel('Start timestamp:'), self.spectralStart)
        self.spectralForm.addRow(QtWidgets.QLabel('End timestamp:'), self.spectralEnd)

        # Spacer widgets to separate the group boxes a bit
        spacer = QtWidgets.QSpacerItem(1, 15)

        self.layout.addWidget(self.editButton, stretch=0, alignment=QtCore.Qt.AlignLeft)
        self.layout.addWidget(self.colsGroup, alignment=QtCore.Qt.AlignTop)
        self.layout.addItem(spacer)
        self.layout.addWidget(self.statsGroup, alignment=QtCore.Qt.AlignTop)
        self.layout.addItem(spacer)
        self.layout.addWidget(self.spectralGroup, alignment=QtCore.Qt.AlignTop)

    def connect_signals(self):
        self.editButton.clicked.connect(self.show_edit_dialog)
        self.processStatsChkBox.toggled.connect(self.set_process_stats_check_state)
        self.processSpectralChkBox.toggled.connect(self.set_process_spectral_check_state)

    def show_edit_dialog(self):
        """Open logger stats edit form."""

        if self.parent.loggersList.count() == 0:
            msg = f'No loggers exist to edit. Add a logger first.'
            return QtWidgets.QMessageBox.information(self, 'Edit Logger Statistics and Spectral Analysis Settings', msg)

        # Retrieve selected logger object
        logger_idx = self.parent.loggersList.currentRow()
        logger = self.control.loggers[logger_idx]

        # Edit stats dialog class
        editStatsSettings = EditStatsAndSpectralDialog(self, logger, logger_idx)
        editStatsSettings.show()

    def set_process_stats_check_state(self):
        """Set include in processing state in logger object."""

        if self.parent.loggersList.count() == 0:
            return

        logger_idx = self.parent.loggersList.currentRow()
        logger = self.control.loggers[logger_idx]
        logger.process_stats = self.processStatsChkBox.isChecked()

    def set_process_spectral_check_state(self):
        """Set include in processing state in logger object."""

        if self.parent.loggersList.count() == 0:
            return

        logger_idx = self.parent.loggersList.currentRow()
        logger = self.control.loggers[logger_idx]
        logger.process_spectral = self.processSpectralChkBox.isChecked()

    def set_analysis_dashboard(self, logger):
        """Set dashboard with logger stats and spectral settings from logger object."""

        # Process check states
        self.processStatsChkBox.setChecked(logger.process_stats)
        self.processSpectralChkBox.setChecked(logger.process_spectral)

        # Columns
        cols_str = ' '.join([str(i) for i in logger.requested_cols])
        self.columns.setText(cols_str)

        # Unit conversion factors
        unit_conv_factors_str = ' '.join([str(i) for i in logger.unit_conv_factors])
        self.unitConvs.setText(unit_conv_factors_str)

        # Channel names
        channel_items_str = ' '.join([i for i in logger.user_channel_names])
        self.channelNames.setText(channel_items_str)

        # Channel units
        units_items_str = ' '.join([i for i in logger.user_channel_units])
        self.channelUnits.setText(units_items_str)

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

        # Stats low cut-off freq
        if logger.stats_low_cutoff_freq is None:
            self.lowCutoff.setText('None')
        else:
            self.lowCutoff.setText(f'{logger.stats_low_cutoff_freq:.2f}')

        # Stats high cut-off freq
        if logger.stats_high_cutoff_freq is None:
            self.highCutoff.setText('None')
        else:
            self.highCutoff.setText(f'{logger.stats_high_cutoff_freq:.2f}')

        # Spectral interval
        self.spectralInterval.setText(str(logger.spectral_interval))

        # Spectral start
        if logger.spectral_start is None:
            spectral_start = 'Not used'
        else:
            spectral_start = logger.spectral_start.strftime('%Y-%m-%d %H:%M')
        self.spectralStart.setText(spectral_start)

        # Spectral end
        if logger.spectral_end is None:
            spectral_end = 'Not used'
        else:
            spectral_end = logger.spectral_end.strftime('%Y-%m-%d %H:%M')
        self.spectralEnd.setText(spectral_end)

    def clear_dashboard(self):
        """Initialise all values in stats and spectral analysis dashboard."""

        self.columns.setText('-')
        self.unitConvs.setText('-')
        self.channelNames.setText('-')
        self.channelUnits.setText('-')
        self.statsInterval.setText('-')
        self.statsStart.setText('-')
        self.statsEnd.setText('-')
        self.lowCutoff.setText('-')
        self.highCutoff.setText('-')
        self.spectralInterval.setText('-')
        self.spectralStart.setText('-')
        self.spectralEnd.setText('-')


class EditCampaignInfoDialog(QtWidgets.QDialog):
    """Edit window for project and campaign data."""

    def __init__(self, parent=None, control=None):
        super(EditCampaignInfoDialog, self).__init__(parent)

        self.parent = parent
        self.control = control
        self.init_ui()
        self.connect_signals()
        self.set_dialog_data()

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


class EditLoggerPropertiesDialog(QtWidgets.QDialog):
    delims_gui_to_logger = {'comma': ',',
                            'space': ' ',
                            }
    delims_logger_to_gui = {',': 'comma',
                            ' ': 'space',
                            }
    file_types = ['Fugro-csv',
                  'Pulse-acc',
                  'General-csv',
                  ]
    delimiters = ['comma',
                  'space',
                  ]

    def __init__(self, parent=None, logger=None, logger_idx=0):
        super(EditLoggerPropertiesDialog, self).__init__(parent)

        self.parent = parent

        # Logger properties object and index of selected logger in combo box
        self.logger = logger
        self.logger_idx = logger_idx

        # To hold a copy of the original timestamp format upon opening the dialog so it can be restored, if need be,
        # when selecting between file formats in the combo box
        self.timestamp_format = ''

        self.all_channel_names = []
        self.all_channel_units = []

        self.init_ui()
        self.connect_signals()
        self.set_dialog_data()

    def init_ui(self):
        self.setWindowTitle('Edit Logger File Properties')
        self.setMinimumWidth(500)

        self.layout = QtWidgets.QVBoxLayout(self)
        # self.layout.addStretch()

        # Logger details group
        self.loggerDetails = QtWidgets.QGroupBox('Logger Details')
        self.detailsForm = QtWidgets.QFormLayout(self.loggerDetails)
        self.loggerID = QtWidgets.QLineEdit()
        self.loggerPath = QtWidgets.QTextEdit()
        self.loggerPath.setFixedHeight(40)
        self.browseButton = QtWidgets.QPushButton('Browse')

        self.detailsForm.addRow(QtWidgets.QLabel('Logger ID:'), self.loggerID)
        self.detailsForm.addRow(QtWidgets.QLabel('Logger path:'), self.loggerPath)
        self.detailsForm.addRow(QtWidgets.QLabel(''), self.browseButton)

        # Logger type group
        self.loggerType = QtWidgets.QGroupBox('Logger Type')
        self.typeForm = QtWidgets.QFormLayout(self.loggerType)
        self.fileFormat = QtWidgets.QComboBox()
        self.fileFormat.setFixedWidth(100)
        self.fileFormat.addItems(self.file_types)
        self.fileTimestampFormat = QtWidgets.QLineEdit()
        self.fileExt = QtWidgets.QLineEdit()
        self.fileExt.setFixedWidth(30)
        self.fileDelimiter = QtWidgets.QComboBox()
        self.fileDelimiter.setFixedWidth(60)
        self.fileDelimiter.addItems(self.delimiters)
        self.numHeaderRows = QtWidgets.QLineEdit()
        self.numHeaderRows.setFixedWidth(30)
        self.channelHeaderRow = QtWidgets.QLineEdit()
        self.channelHeaderRow.setFixedWidth(30)
        self.unitsHeaderRow = QtWidgets.QLineEdit()
        self.unitsHeaderRow.setFixedWidth(30)

        self.typeForm.addRow(QtWidgets.QLabel('File format:'), self.fileFormat)
        self.typeForm.addRow(QtWidgets.QLabel('File timestamp format:'), self.fileTimestampFormat)
        self.typeForm.addRow(QtWidgets.QLabel('File extension:'), self.fileExt)
        self.typeForm.addRow(QtWidgets.QLabel('File delimiter:'), self.fileDelimiter)
        self.typeForm.addRow(QtWidgets.QLabel('Number of header rows:'), self.numHeaderRows)
        self.typeForm.addRow(QtWidgets.QLabel('Channel header row:'), self.channelHeaderRow)
        self.typeForm.addRow(QtWidgets.QLabel('Units header row:'), self.unitsHeaderRow)

        # Logger properties group
        self.loggerProps = QtWidgets.QGroupBox('Logger Properties')
        self.propsForm = QtWidgets.QFormLayout(self.loggerProps)

        self.detectButton = QtWidgets.QPushButton('Detect Properties')
        self.dataTimestampFormat = QtWidgets.QLineEdit()
        self.numColumns = QtWidgets.QLineEdit()
        self.numColumns.setFixedWidth(30)
        self.loggingFreq = QtWidgets.QLineEdit()
        self.loggingFreq.setFixedWidth(30)
        self.loggingDuration = QtWidgets.QLineEdit()
        self.loggingDuration.setFixedWidth(50)

        self.propsForm.addRow(self.detectButton, QtWidgets.QLabel(''))
        self.propsForm.addRow(QtWidgets.QLabel('Timestamp format:'), self.dataTimestampFormat)
        self.propsForm.addRow(QtWidgets.QLabel('Number of expected columns:'), self.numColumns)
        self.propsForm.addRow(QtWidgets.QLabel('Logging frequency (Hz):'), self.loggingFreq)
        self.propsForm.addRow(QtWidgets.QLabel('Logging duration (s):'), self.loggingDuration)

        # Set button sizing policy
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.browseButton.setSizePolicy(policy)
        self.detectButton.setSizePolicy(policy)

        # Define input box validators
        int_validator = QtGui.QIntValidator()
        int_validator.setBottom(1)
        dbl_validator = QtGui.QDoubleValidator()

        # Apply validators
        self.numHeaderRows.setValidator(int_validator)
        self.numColumns.setValidator(int_validator)
        self.channelHeaderRow.setValidator(int_validator)
        self.unitsHeaderRow.setValidator(int_validator)
        self.loggingFreq.setValidator(int_validator)
        self.loggingDuration.setValidator(dbl_validator)

        # Button box
        # self.assignButton = QtWidgets.QPushButton('Assign')
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                    QtWidgets.QDialogButtonBox.Cancel)
        # self.buttons.addButton(self.assignButton, QtWidgets.QDialogButtonBox.AcceptRole)
        # self.buttons.addButton(QtWidgets.QDialogButtonBox.Cancel)

        # Assemble widget containers
        self.layout.addWidget(self.loggerDetails)
        self.layout.addWidget(self.loggerType)
        self.layout.addWidget(self.loggerProps)
        self.layout.addWidget(self.buttonBox, stretch=0, alignment=QtCore.Qt.AlignRight)

    def connect_signals(self):
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.browseButton.clicked.connect(self.set_logger_path)
        self.fileFormat.currentIndexChanged.connect(self.on_file_format_changed)
        self.detectButton.clicked.connect(self.detect_properties)

    def set_dialog_data(self):
        """Set dialog data with logger properties from control object."""

        # Logger properties object of selected logger
        logger = self.logger

        # Store existing timestamp format
        self.timestamp_format = logger.timestamp_format

        self.loggerID.setText(logger.logger_id)
        self.fileFormat.setCurrentText(logger.file_format)
        self.loggerPath.setText(logger.logger_path)
        self.fileTimestampFormat.setText(logger.file_timestamp_format)
        self.dataTimestampFormat.setText(logger.timestamp_format)
        self.fileExt.setText(logger.file_ext)
        self.fileDelimiter.setCurrentText(self.delims_logger_to_gui[logger.file_delimiter])
        self.numHeaderRows.setText(str(logger.num_headers))
        self.numColumns.setText(str(logger.num_columns))
        self.channelHeaderRow.setText(str(logger.channel_header_row))
        self.unitsHeaderRow.setText(str(logger.units_header_row))
        self.loggingFreq.setText(str(logger.freq))
        self.loggingDuration.setText(str(logger.duration))

        # Initialise which input fields are enabled/disabled based on file format set
        self.set_enabled_inputs(logger.file_format)

    def set_enabled_inputs(self, file_format):
        """Enable or disable input fields based on selected file format (Fugro-csv, Pulse-csv, General-csv)."""

        # Initialise for Fugro-csv format
        self.fileExt.setEnabled(False)
        self.fileDelimiter.setEnabled(False)
        self.numHeaderRows.setEnabled(False)
        self.channelHeaderRow.setEnabled(False)
        self.unitsHeaderRow.setEnabled(False)
        self.dataTimestampFormat.setEnabled(True)

        if file_format == 'Pulse-acc':
            self.dataTimestampFormat.setEnabled(False)
        elif file_format == 'General-csv':
            self.fileExt.setEnabled(True)
            self.fileDelimiter.setEnabled(True)
            self.numHeaderRows.setEnabled(True)
            self.channelHeaderRow.setEnabled(True)
            self.unitsHeaderRow.setEnabled(True)

    def set_logger_path(self):
        """Set location of project root directory."""

        logger_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Logger Location')

        if logger_path:
            self.loggerPath.setText(logger_path)

    def on_file_format_changed(self):
        selected_file_format = self.fileFormat.currentText()
        test_logger = LoggerProperties()

        # Set which input fields are enabled/disabled based on file format set
        self.set_enabled_inputs(selected_file_format)

        # Create a test logger object with standard file format properties of the selected logger file type and assign
        # to edit dialog
        # Note Pulse-acc properties are more for info as they are not directly used by the read pulse-acc function
        if selected_file_format == 'Fugro-csv':
            test_logger = set_fugro_csv_file_format(test_logger)

            # Restore timestamp format to value when dialog was opened (useful if previous selection was Pulse-acc)
            self.dataTimestampFormat.setText(self.timestamp_format)
        elif selected_file_format == 'Pulse-acc':
            test_logger = set_pulse_acc_file_format(test_logger)

            # Timestamp format field is not required for Pulse-acc
            self.dataTimestampFormat.setText(test_logger.timestamp_format)
        elif selected_file_format == 'General-csv':
            test_logger = set_general_csv_file_format(test_logger)

            # Restore timestamp format to value when dialog was opened (useful if previous selection was Pulse-acc)
            self.dataTimestampFormat.setText(self.timestamp_format)

        # Assign test logger file format properties to the dialog File Type group
        self.set_standard_file_format_props_to_dialog(test_logger)

    def set_standard_file_format_props_to_dialog(self, test_logger):
        """
        Set the following standard logger file format properties to the edit dialog:
            file extension
            file delimiter
            number of header rows
            channel header row
            units header row
        """

        # Set file format properties
        self.fileExt.setText(test_logger.file_ext)
        self.fileDelimiter.setCurrentText(self.delims_logger_to_gui[test_logger.file_delimiter])
        self.numHeaderRows.setText(str(test_logger.num_headers))
        self.channelHeaderRow.setText(str(test_logger.channel_header_row))
        self.unitsHeaderRow.setText(str(test_logger.units_header_row))

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
            # Detect logger properties from file and assign to test logger object
            if file_format == 'Fugro-csv':
                test_logger = set_fugro_csv_file_format(test_logger)
                test_logger = detect_fugro_logger_properties(test_logger)
            elif file_format == 'Pulse-acc':
                test_logger = set_pulse_acc_file_format(test_logger)
                test_logger = detect_pulse_logger_properties(test_logger)
            elif file_format == 'General-csv':
                # Set current file format properties in the dialog
                test_logger.file_format = 'General-csv'
                test_logger.file_ext = self.fileExt.text()
                test_logger.file_delimiter = self.delims_gui_to_logger[self.fileDelimiter.currentText()]
                test_logger.num_headers = int(self.numHeaderRows.text())
                test_logger.channel_header_row = int(self.channelHeaderRow.text())
                test_logger.units_header_row = int(self.unitsHeaderRow.text())

            # Set detected file properties to dialog
            self.set_detected_file_props_to_dialog(test_logger)
        except LoggerError as e:
            QtWidgets.QMessageBox.warning(self, 'Error', str(e))
            logging.exception(e)
        except FileNotFoundError as e:
            QtWidgets.QMessageBox.warning(self, 'Error', str(e))
            logging.exception(e)
        except Exception as e:
            msg = 'Unexpected error detecting logger file properties'
            QtWidgets.QMessageBox.critical(self, 'Error', f'{msg}:\n{e}\n{sys.exc_info()[0]}')
            logging.exception(e)

    def set_detected_file_props_to_dialog(self, test_logger):
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
        if test_logger.timestamp_format != '':
            self.dataTimestampFormat.setText(test_logger.timestamp_format)
        if test_logger.num_columns != 0:
            self.numColumns.setText(str(test_logger.num_columns))
        if test_logger.duration != 0:
            self.loggingDuration.setText(str(test_logger.duration))

    def on_ok_clicked(self):
        """Assign logger properties to the control object and update the dashboard."""

        try:
            self.set_control_data()
            self.detect_header()
            self.parent.set_logger_dashboard(self.logger)
            self.parent.parent.update_logger_id_list(self.logger.logger_id, self.logger_idx)
            self.parent.parent.set_logger_header_list(self.logger)
        except Exception as e:
            msg = 'Unexpected error assigning logger properties'
            QtWidgets.QMessageBox.critical(self, 'Error', f'{msg}:\n{e}\n{sys.exc_info()[0]}')
            logging.exception(e)

    def set_control_data(self):
        """Assign values to the control object."""

        logger = self.logger

        # Assign form values to control logger object
        logger.logger_id = self.loggerID.text()
        logger.file_format = self.fileFormat.currentText()
        logger.logger_path = self.loggerPath.toPlainText()
        logger.file_timestamp_format = self.fileTimestampFormat.text()
        logger.timestamp_format = self.dataTimestampFormat.text()

        # Get datetime format string from attempting to converting user input timestamp format
        logger.datetime_format = get_datetime_format(logger.timestamp_format)

        logger.file_ext = self.fileExt.text()
        logger.file_delimiter = self.delims_gui_to_logger[self.fileDelimiter.currentText()]
        logger.num_headers = int(self.numHeaderRows.text())
        logger.num_columns = int(self.numColumns.text())
        logger.channel_header_row = int(self.channelHeaderRow.text())
        logger.units_header_row = int(self.unitsHeaderRow.text())
        logger.freq = int(self.loggingFreq.text())
        logger.duration = float(self.loggingDuration.text())

    def detect_header(self):
        """Store all channel and units names from a test file, if present. Header info will then be set in the gui."""

        try:
            self.logger.get_all_channel_and_unit_names()
        except FileNotFoundError as e:
            QtWidgets.QMessageBox.warning(self, 'Error', str(e))
            logging.exception(e)
        except Exception as e:
            msg = 'Unexpected error detecting logger file properties'
            QtWidgets.QMessageBox.critical(self, 'Error', f'{msg}:\n{e}\n{sys.exc_info()[0]}')
            logging.exception(e)


class EditStatsAndSpectralDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, logger=None, logger_idx=0):
        super(EditStatsAndSpectralDialog, self).__init__(parent)

        self.parent = parent

        # Logger properties object and index of selected logger in combo box
        self.logger = logger
        self.logger_idx = logger_idx

        self._init_ui()
        self._connect_signals()
        self._set_dialog_data()

    def _init_ui(self):
        self.setWindowTitle('Edit Logger Statistics and Spectral Analysis Settings')
        self.setMinimumWidth(500)

        self.layout = QtWidgets.QVBoxLayout(self)

        # Processed columns group
        self.colsGroup = QtWidgets.QGroupBox('Processed Columns')
        self.columns = QtWidgets.QLineEdit()
        self.unitConvs = QtWidgets.QLineEdit()
        self.channelNames = QtWidgets.QLineEdit()
        msg = 'Optional: Add custom channel names separated by a space (e.g. AccelX AccelY AngRateX AngRateY)'
        self.channelNames.setToolTip(msg)
        self.channelUnits = QtWidgets.QLineEdit()
        msg = 'Optional: Add custom channel units separated by a space (e.g. m/s^2 m/s^2 deg/s deg/s)'
        self.channelUnits.setToolTip(msg)

        self.colsForm = QtWidgets.QFormLayout(self.colsGroup)
        self.colsForm.addRow(QtWidgets.QLabel('Requested columns:'), self.columns)
        self.colsForm.addRow(QtWidgets.QLabel('Unit conversion factors:'), self.unitConvs)
        self.colsForm.addRow(QtWidgets.QLabel('Channel names override (optional):'), self.channelNames)
        self.colsForm.addRow(QtWidgets.QLabel('Channel units override (optional):'), self.channelUnits)

        # Stats settings group
        self.statsGroup = QtWidgets.QGroupBox('Logger Statistics Settings')
        self.statsInterval = QtWidgets.QLineEdit()
        self.statsInterval.setFixedWidth(40)
        self.statsStart = QtWidgets.QLineEdit()
        self.statsStart.setFixedWidth(100)
        self.statsEnd = QtWidgets.QLineEdit()
        self.statsEnd.setFixedWidth(100)

        # Filtered low and high cut-off frequencies
        self.lowCutoff = QtWidgets.QLineEdit()
        self.lowCutoff.setFixedWidth(40)
        self.highCutoff = QtWidgets.QLineEdit()
        self.highCutoff.setFixedWidth(40)

        # Define input validators
        int_validator = QtGui.QIntValidator()
        int_validator.setBottom(1)
        dbl_validator = QtGui.QDoubleValidator()

        # Apply validators
        self.statsInterval.setValidator(int_validator)
        self.lowCutoff.setValidator(dbl_validator)
        self.highCutoff.setValidator(dbl_validator)

        self.statsForm = QtWidgets.QFormLayout(self.statsGroup)
        self.statsForm.addRow(QtWidgets.QLabel('Interval (s):'), self.statsInterval)
        self.statsForm.addRow(QtWidgets.QLabel('Start timestamp:'), self.statsStart)
        self.statsForm.addRow(QtWidgets.QLabel('End timestamp:'), self.statsEnd)
        self.statsForm.addRow(QtWidgets.QLabel('Low frequency cut-off (Hz):'), self.lowCutoff)
        self.statsForm.addRow(QtWidgets.QLabel('High frequency cut-off (Hz):'), self.highCutoff)

        # Spectral settings group
        self.spectralGroup = QtWidgets.QGroupBox('Logger Spectral Settings')
        self.spectralForm = QtWidgets.QFormLayout(self.spectralGroup)
        self.spectralInterval = QtWidgets.QLineEdit()
        self.spectralInterval.setFixedWidth(40)
        self.spectralStart = QtWidgets.QLineEdit()
        self.spectralStart.setFixedWidth(100)
        self.spectralEnd = QtWidgets.QLineEdit()
        self.spectralEnd.setFixedWidth(100)

        # Define input validators
        int_validator = QtGui.QIntValidator()
        int_validator.setBottom(1)

        # Apply validators
        self.spectralInterval.setValidator(int_validator)

        self.spectralForm.addRow(QtWidgets.QLabel('Interval (s):'), self.spectralInterval)
        self.spectralForm.addRow(QtWidgets.QLabel('Start timestamp:'), self.spectralStart)
        self.spectralForm.addRow(QtWidgets.QLabel('End timestamp:'), self.spectralEnd)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok |
                                                    QtWidgets.QDialogButtonBox.Cancel)

        self.layout.addWidget(self.colsGroup)
        self.layout.addWidget(self.statsGroup)
        self.layout.addWidget(self.spectralGroup)
        self.layout.addWidget(self.buttonBox, stretch=0, alignment=QtCore.Qt.AlignRight)

    def _connect_signals(self):
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def _set_dialog_data(self):
        """Set dialog data with logger stats from control object."""

        logger = self.logger

        # Processed columns group
        # Columns
        cols_str = ' '.join([str(i) for i in logger.requested_cols])
        self.columns.setText(cols_str)

        # Unit conversion factors
        unit_conv_factors_str = ' '.join([str(i) for i in logger.unit_conv_factors])
        self.unitConvs.setText(unit_conv_factors_str)

        # Channel names
        channel_items_str = ' '.join([i for i in logger.user_channel_names])
        self.channelNames.setText(channel_items_str)

        # Channel units
        units_items_str = ' '.join([i for i in logger.user_channel_units])
        self.channelUnits.setText(units_items_str)

        # Stats settings group
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

        # Low cut-off freq
        if logger.stats_low_cutoff_freq is None:
            self.lowCutoff.setText('None')
        else:
            self.lowCutoff.setText(f'{logger.stats_low_cutoff_freq:.2f}')

        # High cut-off freq
        if logger.stats_high_cutoff_freq is None:
            self.highCutoff.setText('None')
        else:
            self.highCutoff.setText(f'{logger.stats_high_cutoff_freq:.2f}')

        # Spectral settings group
        # Spectral interval
        self.spectralInterval.setText(str(logger.spectral_interval))

        # Spectral start
        if logger.spectral_start is None:
            spectral_start = 'Not used'
        else:
            spectral_start = logger.spectral_start.strftime('%Y-%m-%d %H:%M')
        self.spectralStart.setText(spectral_start)

        # Spectral end
        if logger.spectral_end is None:
            spectral_end = 'Not used'
        else:
            spectral_end = logger.spectral_end.strftime('%Y-%m-%d %H:%M')
        self.spectralEnd.setText(spectral_end)

    def on_ok_clicked(self):
        """Assign logger stats settings to the control object and update the dashboard."""

        self._set_control_data()
        self.parent.set_analysis_dashboard(self.logger)

    def _set_control_data(self):
        """Assign values to the control object."""

        logger = self.logger

        # Processed columns group
        # Convert strings to lists
        try:
            logger.requested_cols = list(map(int, self.columns.text().split()))
        except ValueError:
            msg = 'Only integer column numbers are allowed.\nSeparate each number with a space, e.g. 2 3 4 5.'
            QtWidgets.QMessageBox.information(self, 'Invalid Requested Columns Input', msg)

        try:
            logger.unit_conv_factors = list(map(float, self.unitConvs.text().split()))
        except ValueError:
            msg = 'Unit conversion factors must be numeric.\nSeparate each input with a space, e.g. 0.001 0.001.'
            QtWidgets.QMessageBox.information(self, 'Invalid Unit Conversion Factors Input', msg)

        logger.user_channel_names = self.channelNames.text().split()
        logger.user_channel_units = self.channelUnits.text().split()

        # Stats settings group
        logger.stats_interval = int(self.statsInterval.text())

        stats_start = self.statsStart.text()
        if stats_start == '' or stats_start == 'Not used':
            logger.stats_start = None
        else:
            try:
                logger.stats_start = parse(stats_start, yearfirst=True)
            except ValueError:
                msg = 'Stats start datetime format not recognised; timestamp unchanged'
                QtWidgets.QMessageBox.information(self, 'Stats Start Input', msg)

        stats_end = self.statsEnd.text()
        if stats_end == '' or stats_end == 'Not used':
            logger.stats_end = None
        else:
            try:
                logger.stats_end = parse(stats_end, yearfirst=True)
            except ValueError:
                msg = 'Stats end datetime format not recognised; timestamp unchanged'
                QtWidgets.QMessageBox.information(self, 'Stats End Input', msg)

        # Stats low cut-off freq
        try:
            logger.stats_low_cutoff_freq = float(self.lowCutoff.text())
            if logger.stats_low_cutoff_freq == 0:
                logger.stats_low_cutoff_freq = None
        except:
            logger.stats_low_cutoff_freq = None

        # Stats high cut-off freq
        try:
            logger.stats_high_cutoff_freq = float(self.highCutoff.text())
            if logger.stats_high_cutoff_freq == 0:
                logger.stats_high_cutoff_freq = None
        except:
            logger.stats_high_cutoff_freq = None

        # Spectral settings group
        logger.spectral_interval = int(self.spectralInterval.text())

        spectral_start = self.spectralStart.text()
        if spectral_start == '' or spectral_start == 'Not used':
            logger.spectral_start = None
        else:
            try:
                logger.spectral_start = parse(spectral_start, yearfirst=True)
            except ValueError:
                msg = 'Spectral start datetime format not recognised; timestamp unchanged'
                QtWidgets.QMessageBox.information(self, 'Spectral Start Input', msg)

        spectral_end = self.spectralEnd.text()
        if spectral_end == '' or spectral_end == 'Not used':
            logger.spectral_end = None
        else:
            try:
                logger.spectral_end = parse(spectral_end, yearfirst=True)
            except ValueError:
                msg = 'Spectral end datetime format not recognised; timestamp unchanged'
                QtWidgets.QMessageBox.information(self, 'Spectral End Input', msg)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = ConfigModule()
    # win = EditLoggerPropertiesDialog()
    win.show()
    app.exit(app.exec_())
