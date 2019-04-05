import logging
import sys

from PyQt5 import QtCore, QtGui, QtWidgets


class ProjectConfigModule(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(ProjectConfigModule, self).__init__(parent)

        self.proj_num = ''
        self.proj_name = ''
        self.campaign_name = ''
        self.proj_root = ''

        self.init_ui()

    def init_ui(self):
        grid = QtWidgets.QGridLayout(self)
        self.tabWidget = QtWidgets.QTabWidget()

        self.projSettingsTab = ProjectSettings(self)
        self.analysisSettingsTab = AnalysisSettings(self)

        self.tabWidget.addTab(self.projSettingsTab, 'Project Settings')
        self.tabWidget.addTab(self.analysisSettingsTab, 'Campaign Logger')
        self.tabWidget.addTab(self.analysisSettingsTab, 'Analysis Settings')

        self.buttonBox = QtWidgets.QDialogButtonBox()
        self.newProjButton = QtWidgets.QPushButton('New Project')

        self.buttonBox.addButton(self.newProjButton, QtWidgets.QDialogButtonBox.ResetRole)
        self.buttonBox.addButton(QtWidgets.QDialogButtonBox.Save)

        grid.addWidget(self.tabWidget)
        grid.addWidget(self.buttonBox)

    def connect_signals(self):
        pass


class ProjectSettings(QtWidgets.QWidget):
    """GUI screen to control project setup."""

    def __init__(self, parent=None):
        super(ProjectSettings, self).__init__(parent)

        self.parent = parent

        self.proj_num = ''
        self.proj_name = ''
        self.campaign_name = ''
        self.proj_root = ''

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        layout = QtWidgets.QGridLayout(self)

        # General project controls
        projSettings = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(projSettings)
        self.projNum = QtWidgets.QLineEdit()
        self.projNum.setFixedWidth(40)
        self.projName = QtWidgets.QLineEdit()
        self.campaignName = QtWidgets.QLineEdit()
        self.projRoot = QtWidgets.QLineEdit()
        self.setRoot = QtWidgets.QPushButton('Set Path')
        self.setRoot.setFixedWidth(100)

        # self.mylist = QtWidgets.QListWidget()
        # self.mylist.addItems(['aaa', 'bbb'])
        #
        # for i in range(self.mylist.count()):
        #     item = self.mylist.item(i)
        #     item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)

        # Place widgets
        form.addRow(QtWidgets.QLabel('Project number:'), self.projNum)
        form.addRow(QtWidgets.QLabel('Project name:'), self.projName)
        form.addRow(QtWidgets.QLabel('Campaign name:'), self.campaignName)
        form.addRow(QtWidgets.QLabel('Project root path:'), self.projRoot)
        form.addRow(QtWidgets.QLabel(''), self.setRoot)

        layout.addWidget(projSettings, 0, 0)

    def connect_signals(self):
        self.setRoot.clicked.connect(self.set_project_root_path)

    def set_project_root_path(self):
        file_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Project Location')

        if file_path:
            self.proj_root = file_path
            self.projRoot.setText(file_path)


class AnalysisSettings(QtWidgets.QWidget):
    """GUI screen to control project setup."""

    def __init__(self, parent=None):
        super(AnalysisSettings, self).__init__(parent)

        self.logger_id = ''
        self.file_format = 'Fugro-csv'
        self.file_path = ''
        self.file_timstamp = ''
        self.data_timstamp = ''
        self.file_ext = ''
        self.file_delimiter = ''
        self.num_header_rows = ''
        self.num_columns = ''
        self.channel_header_row = ''
        self.units_header_row = ''
        self.logging_freq = ''
        self.logging_duration = ''
        self.channel_names = ''
        self.channel_units = ''
        self.stats_columns = ''
        self.stats_unit_convs = ''
        self.stats_interval = ''
        self.stats_start = ''
        self.stats_end = ''

        # Edit logger properties dialog class
        self.editLoggerProps = LoggerPropertiesEdit(self)
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """Create widget layout."""

        layout = QtWidgets.QVBoxLayout(self)

        # General project controls
        genSettings = QtWidgets.QGroupBox('Project Settings')
        form = QtWidgets.QFormLayout(genSettings)
        self.projNum = QtWidgets.QLineEdit()
        self.projName = QtWidgets.QLineEdit()
        self.campaignName = QtWidgets.QLineEdit()
        self.projRoot = QtWidgets.QLineEdit()

        # Place widgets
        form.addRow(QtWidgets.QLabel('Project number:'), self.projNum)
        form.addRow(QtWidgets.QLabel('Project name:'), self.projName)
        form.addRow(QtWidgets.QLabel('Campaign name:'), self.campaignName)
        form.addRow(QtWidgets.QLabel('Project root:'), self.projRoot)

        # Loggers setup
        loggersSetup = QtWidgets.QWidget()
        hbox = QtWidgets.QHBoxLayout(loggersSetup)

        # Logger list group
        addRemLoggersGroup = QtWidgets.QGroupBox('Campaign Loggers')
        addRemLoggersGroup.setFixedWidth(150)
        vbox1 = QtWidgets.QVBoxLayout(addRemLoggersGroup)
        self.addLoggerButton = QtWidgets.QPushButton('Add Logger')
        self.editLoggerButton = QtWidgets.QPushButton('Edit Logger')
        self.remLoggerButton = QtWidgets.QPushButton('Remove Logger')
        self.loggersList = QtWidgets.QListWidget()
        vbox1.addWidget(self.addLoggerButton)
        vbox1.addWidget(self.editLoggerButton)
        vbox1.addWidget(self.remLoggerButton)
        vbox1.addWidget(QtWidgets.QLabel('Loggers'))
        vbox1.addWidget(self.loggersList)

        # Logger properties group
        loggerProps = QtWidgets.QGroupBox('Logger Properties')
        propsForm = QtWidgets.QFormLayout(loggerProps)
        self.loggerID = QtWidgets.QLabel('N/A')
        self.fileFormat = QtWidgets.QLabel('N/A')
        self.filePath = QtWidgets.QLabel('N/A')
        self.fileTimstamp = QtWidgets.QLabel('N/A')
        self.dataTimstamp = QtWidgets.QLabel('N/A')
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
        self.statsColumns = QtWidgets.QLabel('N/A')
        self.statsUnitConvs = QtWidgets.QLabel('N/A')
        self.statsInterval = QtWidgets.QLabel('N/A')
        self.statsStart = QtWidgets.QLabel('N/A')
        self.statsEnd = QtWidgets.QLabel('N/A')

        # Place widgets
        propsForm.addRow(QtWidgets.QLabel('Logger ID:'), self.loggerID)
        propsForm.addRow(QtWidgets.QLabel('File format:'), self.fileFormat)
        propsForm.addRow(QtWidgets.QLabel('File path:'), self.filePath)
        propsForm.addRow(QtWidgets.QLabel('File timestamp:'), self.fileTimstamp)
        propsForm.addRow(QtWidgets.QLabel('Data timestamp:'), self.dataTimstamp)
        propsForm.addRow(QtWidgets.QLabel('Extension:'), self.fileExt)
        propsForm.addRow(QtWidgets.QLabel('Delimiter:'), self.fileDelimiter)
        propsForm.addRow(QtWidgets.QLabel('Number of header rows:'), self.numHeaderRows)
        propsForm.addRow(QtWidgets.QLabel('Number of expected columns:'), self.numColumns)
        propsForm.addRow(QtWidgets.QLabel('Channel header row:'), self.channelHeaderRow)
        propsForm.addRow(QtWidgets.QLabel('Logging frequency (Hz):'), self.unitsHeaderRow)
        propsForm.addRow(QtWidgets.QLabel('Logging duration (s):'), self.loggingFreq)
        propsForm.addRow(QtWidgets.QLabel('Channel names:'), self.loggingDuration)
        propsForm.addRow(QtWidgets.QLabel('Channel units:'), self.channelNames)

        # Stats group
        statParams = QtWidgets.QGroupBox('Statistical Analysis Parameters')
        statsForm = QtWidgets.QFormLayout(statParams)
        statsForm.addRow(QtWidgets.QLabel('Stats columns:'), self.channelUnits)
        statsForm.addRow(QtWidgets.QLabel('Stats unit conversion factors:'), self.statsUnitConvs)
        statsForm.addRow(QtWidgets.QLabel('Stats interval:'), self.statsInterval)
        statsForm.addRow(QtWidgets.QLabel('Stats start timestamp:'), self.statsStart)
        statsForm.addRow(QtWidgets.QLabel('Stats end timestamp:'), self.statsEnd)

        spectroParams = QtWidgets.QGroupBox('Spectral Analysis Parameters')
        spectroForm = QtWidgets.QFormLayout(spectroParams)
        spectroForm.addRow(QtWidgets.QLabel('Stats columns:'), self.channelUnits)
        spectroForm.addRow(QtWidgets.QLabel('Stats unit conversion factors:'), self.statsUnitConvs)
        spectroForm.addRow(QtWidgets.QLabel('Stats interval:'), self.statsInterval)
        spectroForm.addRow(QtWidgets.QLabel('Stats start timestamp:'), self.statsStart)
        spectroForm.addRow(QtWidgets.QLabel('Stats end timestamp:'), self.statsEnd)

        hbox.addWidget(addRemLoggersGroup)
        hbox.addWidget(loggerProps)
        hbox.addWidget(statParams)
        hbox.addWidget(spectroParams)

        # Buttonbox
        buttonbox = QtWidgets.QDialogButtonBox()
        buttonbox.addButton('Run Data Quality Checks', QtWidgets.QDialogButtonBox.AcceptRole)

        layout.addWidget(genSettings)
        layout.addWidget(loggersSetup)
        layout.addWidget(buttonbox)

    def connect_signals(self):
        self.editLoggerButton.clicked.connect(self.show_edit_logger_props)

    def create_new_project(self):
        """Create new project config file."""
        pass

    def set_project_root(self):
        """Select project root directory."""
        pass

    def show_edit_logger_props(self):
        self.editLoggerProps.show()


class LoggerPropertiesEdit(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(LoggerPropertiesEdit, self).__init__(parent)

        self.parent = parent
        self.file_formats = ['Fugro-csv',
                             'Pulse-acc',
                             'General-csv',
                             ]
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Edit Logger Properties')

        layout = QtWidgets.QVBoxLayout(self)
        layout.addStretch()

        # Logger properties group
        loggerProps = QtWidgets.QGroupBox('Logger Properties')
        propsForm = QtWidgets.QFormLayout(loggerProps)
        self.loggerID = QtWidgets.QLineEdit()
        self.fileFormat = QtWidgets.QComboBox()
        self.fileFormat.setFixedWidth(100)
        self.fileFormat.addItems(self.file_formats)
        self.setLoggerPath = QtWidgets.QPushButton('Set Logger Path')
        self.setLoggerPath.setFixedWidth(130)
        self.loggerPath = QtWidgets.QLineEdit()
        self.fileTimstamp = QtWidgets.QLineEdit()
        self.dataTimstamp = QtWidgets.QLineEdit()
        self.fileExt = QtWidgets.QLineEdit()
        self.fileDelimiter = QtWidgets.QLineEdit()
        self.numHeaderRows = QtWidgets.QLineEdit()
        self.numColumns = QtWidgets.QLineEdit()
        self.channelHeaderRow = QtWidgets.QLineEdit()
        self.unitsHeaderRow = QtWidgets.QLineEdit()
        self.loggingFreq = QtWidgets.QLineEdit()
        self.loggingDuration = QtWidgets.QLineEdit()
        self.channelNames = QtWidgets.QLineEdit()
        self.channelUnits = QtWidgets.QLineEdit()
        self.statsColumns = QtWidgets.QLineEdit()
        self.statsUnitConvs = QtWidgets.QLineEdit()
        self.statsInterval = QtWidgets.QLineEdit()
        self.statsStart = QtWidgets.QLineEdit()
        self.statsEnd = QtWidgets.QLineEdit()

        # Place widgets
        propsForm.addRow(QtWidgets.QLabel('Logger ID:'), self.loggerID)
        propsForm.addRow(QtWidgets.QLabel('File Format:'), self.fileFormat)
        propsForm.addRow(self.setLoggerPath, QtWidgets.QLabel(''))
        propsForm.addRow(QtWidgets.QLabel('Logger Path:'), self.loggerPath)
        propsForm.addRow(QtWidgets.QLabel('File Timestamp:'), self.fileTimstamp)
        propsForm.addRow(QtWidgets.QLabel('Data Timestamp:'), self.dataTimstamp)
        propsForm.addRow(QtWidgets.QLabel('File Extension:'), self.fileExt)
        propsForm.addRow(QtWidgets.QLabel('File Delimiter:'), self.fileDelimiter)
        propsForm.addRow(QtWidgets.QLabel('Number of Header Rows:'), self.numHeaderRows)
        propsForm.addRow(QtWidgets.QLabel('Number of Expected Columns:'), self.numColumns)
        propsForm.addRow(QtWidgets.QLabel('Channel Header Row:'), self.channelHeaderRow)
        propsForm.addRow(QtWidgets.QLabel('Logging Frequency (Hz):'), self.unitsHeaderRow)
        propsForm.addRow(QtWidgets.QLabel('Logging Duration (s):'), self.loggingFreq)
        propsForm.addRow(QtWidgets.QLabel('Channel Names:'), self.loggingDuration)
        propsForm.addRow(QtWidgets.QLabel('Channel Units:'), self.channelNames)
        propsForm.addRow(QtWidgets.QLabel('Stats Columns:'), self.channelUnits)
        propsForm.addRow(QtWidgets.QLabel('Stats Unit Conversion Factors:'), self.statsUnitConvs)
        propsForm.addRow(QtWidgets.QLabel('Stats Interval:'), self.statsInterval)
        propsForm.addRow(QtWidgets.QLabel('Stats Start Timestamp:'), self.statsStart)
        propsForm.addRow(QtWidgets.QLabel('Stats End Timestamp:'), self.statsEnd)

        # Button box
        # self.assignButton = QtWidgets.QPushButton('Assign')
        self.buttons = QtWidgets.QDialogButtonBox()
        self.assignButton = QtWidgets.QPushButton('Assign')
        self.buttons.addButton(self.assignButton, QtWidgets.QDialogButtonBox.AcceptRole)
        self.buttons.addButton(QtWidgets.QDialogButtonBox.Cancel)

        layout.addWidget(loggerProps)
        layout.addWidget(self.buttons, stretch=0, alignment=QtCore.Qt.AlignRight)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = ProjectConfigModule()
    # win = LoggerPropertiesEdit()
    win.show()
    app.exit(app.exec_())
