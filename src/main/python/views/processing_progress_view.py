"""Screening processing progress bar dialog."""

__author__ = "Craig Dickinson"

import sys
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot


class ProcessingProgressBar(QtWidgets.QDialog):
    """Progress bar window for processing control file."""

    signal_quit_worker = pyqtSignal()

    def __init__(self, logger_ids=[]):
        super().__init__()

        self._init_ui()
        self._populate_loggers_list(logger_ids)
        self._connect_signals()

    def _init_ui(self):
        # self.setFixedWidth(400)
        self.setWindowTitle("Processing Loggers")
        self.setFixedHeight(350)

        # WIDGETS
        self.loggersLabel = QtWidgets.QLabel("Logger Status")
        self.loggerList = QtWidgets.QListWidget()
        self.loggerList.setFixedWidth(160)
        self.loggerList.setFixedHeight(100)
        self.outputFilesLabel = QtWidgets.QLabel("Files Output to Project Location")
        self.outputFilesList = QtWidgets.QListWidget()
        self.pb = QtWidgets.QProgressBar()
        self.pb.setFixedWidth(350)
        self.progLabel = QtWidgets.QLabel()
        self.progLabel2 = QtWidgets.QLabel()
        self.elapsedTimeLabel = QtWidgets.QLabel()
        self.procCompleteLabel = QtWidgets.QLabel()
        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        # CONTAINERS
        self.vbox1 = QtWidgets.QVBoxLayout()
        self.vbox1.addWidget(self.loggersLabel)
        self.vbox1.addWidget(self.loggerList)

        self.vbox2 = QtWidgets.QVBoxLayout()
        self.vbox2.addWidget(self.progLabel)
        self.vbox2.addWidget(self.pb)
        self.vbox2.addWidget(self.progLabel2)
        self.vbox2.addWidget(self.elapsedTimeLabel)
        self.vbox2.addWidget(self.procCompleteLabel)
        self.vbox2.addStretch()

        self.hbox = QtWidgets.QHBoxLayout()
        self.hbox.addLayout(self.vbox1)
        self.hbox.addLayout(self.vbox2)

        self.vbox3 = QtWidgets.QVBoxLayout()
        self.vbox3.addWidget(self.outputFilesLabel)
        self.vbox3.addWidget(self.outputFilesList)
        self.vbox3.addWidget(self.buttonBox)

        # LAYOUT
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addLayout(self.hbox)
        self.layout.addLayout(self.vbox3)

    def _connect_signals(self):
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.cancel)

    def _populate_loggers_list(self, logger_ids):
        self.loggerList.addItems(logger_ids)

    def cancel(self):
        """Cancel progress bar."""

        print("\nRun cancelled")
        self.signal_quit_worker.emit()

    @pyqtSlot(dict)
    def update_progress_bar(self, dict_progress):
        """Update progress bar window."""

        logger_ids = dict_progress["logger_ids"]
        logger_i = dict_progress["logger_i"]
        file_i = dict_progress["file_i"]
        filename = dict_progress["filename"]
        n = dict_progress["num_logger_files"]
        total_file_count = dict_progress["file_count"]
        total_files = dict_progress["total_files"]
        elapsed_time = dict_progress["elapsed_time"]

        # Update loggers status list
        logger = logger_ids[logger_i]
        self.loggerList.item(logger_i).setText(f"{logger} - Processing")

        if logger_i > 0:
            prev_logger = logger_ids[logger_i - 1]
            self.loggerList.item(logger_i - 1).setText(f"{prev_logger} - Complete")

        # Update progress label
        self.progLabel.setText(f"Processing file {filename} (file {file_i + 1} of {n})")
        self.progLabel2.setText(f"Processed {total_file_count} of {total_files} files in total")
        self.elapsedTimeLabel.setText(f"Elapsed time = {elapsed_time}")

        # Set percentage progress
        try:
            perc = total_file_count / total_files * 100
        except ZeroDivisionError:
            perc = 100
        self.pb.setValue(perc)

        # On 100% update last logger in list to "Complete", report runtime and re-enable OK button
        if int(perc) == 100:
            self.loggerList.item(logger_i).setText(f"{logger} - Complete")
            self.procCompleteLabel.setText("Processing complete")
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    @pyqtSlot(list)
    def add_output_files(self, output_files):
        self.outputFilesList.clear()
        self.outputFilesList.addItems(output_files)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = ProcessingProgressBar()
    win.show()
    sys.exit(app.exec_())
