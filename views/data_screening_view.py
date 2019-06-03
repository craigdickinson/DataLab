import sys
from PyQt5 import QtCore, QtWidgets
from core.datalab_main import DataLab


class DataQualityReport(QtWidgets.QWidget):
    """Main screen containing project configuration setup."""

    def __init__(self, parent=None):
        super(DataQualityReport, self).__init__(parent)

        self.parent = parent
        self.datalab = DataLab(no_dat=True)
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        self.layout = QtWidgets.QGridLayout(self)
        self.layout.setAlignment(QtCore.Qt.AlignTop)

        # Container for selected logger combo box
        self.selectedLoggerWidget = QtWidgets.QWidget()
        self.selectedLoggerWidget.setFixedSize(300, 50)
        self.hbox = QtWidgets.QHBoxLayout(self.selectedLoggerWidget)

        self.loggerCombo = QtWidgets.QComboBox()
        self.loggerCombo.setMinimumWidth(100)
        self.loggerCombo.addItem("-")

        self.hbox.addWidget(QtWidgets.QLabel("Selected logger:"))
        self.hbox.addWidget(self.loggerCombo)

        # Data quality report group
        self.qualityGroup = QtWidgets.QGroupBox("Data Quality Screening Results")
        self.qualityGroup.setFixedSize(300, 100)
        self.form = QtWidgets.QFormLayout(self.qualityGroup)
        self.numFiles = QtWidgets.QLabel("-")
        self.numBadFilenames = QtWidgets.QLabel("-")
        self.percCompleteData = QtWidgets.QLabel("-")
        self.minResTable = QtWidgets.QTableWidget()
        self.minResTable.setColumnCount(2)
        self.minResTable.setRowCount(4)

        self.form.addRow(QtWidgets.QLabel("Number of files:"), self.numFiles)
        self.form.addRow(
            QtWidgets.QLabel("Number of bad file names:"), self.numBadFilenames
        )
        self.form.addRow(
            QtWidgets.QLabel("Percentage of complete data:"), self.percCompleteData
        )
        # self.form.addRow(QtWidgets.QLabel('Percentage of complete data:'), self.minResTable)

        self.layout.addWidget(self.selectedLoggerWidget, 0, 0)
        self.layout.addWidget(self.qualityGroup, 1, 0)
        # self.layout.addWidget(self.minResTable, 2, 0)

    def connect_signals(self):
        self.loggerCombo.currentIndexChanged.connect(self.on_logger_combo_changed)

    def set_data_quality_results(self):
        logger_ids = self.datalab.control.logger_ids
        self.populate_logger_combo(logger_ids)

    def on_logger_combo_changed(self):
        """Update dashboard data pertaining to selected logger."""

        # Check combo is not empty
        logger_idx = self.loggerCombo.currentIndex()
        if logger_idx == -1:
            return

        logger_data_screen = self.datalab.data_screen[logger_idx]
        logger = self.datalab.control.loggers[logger_idx]

        # Update report
        self.numFiles.setText(str(len(logger_data_screen.files)))
        self.numBadFilenames.setText(str(len(logger.dict_bad_filenames)))
        perc_complete_data = f"{int(logger_data_screen.data_completeness.min())}%"
        self.percCompleteData.setText(perc_complete_data)

    def populate_logger_combo(self, logger_ids):
        # Populate logger combo box
        # Note: This will trigger the setting of the logger properties, stats and spectral dashboards
        self.loggerCombo.clear()
        self.loggerCombo.addItems(logger_ids)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = DataQualityReport()
    win.show()
    app.exit(app.exec_())
