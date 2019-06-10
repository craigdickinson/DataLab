import sys
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot


class ProcessingProgressBar(QtWidgets.QDialog):
    """Progress bar window for processing control file."""

    signal_quit_worker = pyqtSignal()

    def __init__(self, logger_ids=[]):
        super().__init__()

        # self.setFixedWidth(400)
        self.setWindowTitle("Processing Loggers")
        self.setFixedHeight(150)

        self.hbox = QtWidgets.QHBoxLayout(self)
        self.vbox1 = QtWidgets.QVBoxLayout()
        self.vbox2 = QtWidgets.QVBoxLayout()

        self.loggersLabel = QtWidgets.QLabel("Logger Status")
        self.loggersList = QtWidgets.QListWidget()
        self.loggersList.setFixedWidth(160)

        self.progLabel = QtWidgets.QLabel()
        self.pb = QtWidgets.QProgressBar()
        self.pb.setFixedWidth(350)
        self.progLabel2 = QtWidgets.QLabel()
        self.procCompleteLabel = QtWidgets.QLabel()

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.cancel)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

        # Create layout
        self.vbox1.addWidget(self.loggersLabel)
        self.vbox1.addWidget(self.loggersList)

        self.vbox2.addWidget(self.progLabel)
        self.vbox2.addWidget(self.pb)
        self.vbox2.addWidget(self.progLabel2)
        self.vbox2.addWidget(self.procCompleteLabel)
        self.vbox2.addStretch()
        self.vbox2.addWidget(self.buttonBox)

        self.hbox.addLayout(self.vbox1)
        self.hbox.addLayout(self.vbox2)

        self._populate_loggers_list(logger_ids)

        self.show()

    def _populate_loggers_list(self, logger_ids):
        if logger_ids:
            self.loggersList.addItems(logger_ids)

    def cancel(self):
        """Cancel progress bar."""

        print("\nRun cancelled")
        self.signal_quit_worker.emit()

    @pyqtSlot(dict)
    def update_progress_bar(self, dict_progress):
        # str, int, int, int, int, int
        # self, logger, logger_i, file_i, n, file_num, total_num_files
        """Update progress bar window."""

        logger_ids = dict_progress["logger_ids"]
        logger_i = dict_progress["logger_i"]
        file_i = dict_progress["file_i"]
        filename = dict_progress["filename"]
        n = dict_progress["num_logger_files"]
        total_file_count = dict_progress["file_count"]
        total_files = dict_progress["total_files"]

        logger = logger_ids[logger_i]
        num_loggers = len(logger_ids)

        # Update loggers status list
        self.loggersList.item(logger_i).setText(f"{logger} - Processing")

        if logger_i > 0:
            prev_logger = logger_ids[logger_i - 1]
            self.loggersList.item(logger_i - 1).setText(f"{prev_logger} - Complete")

        # Update progress label
        self.progLabel.setText(f"Processing file {filename} (file {file_i + 1} of {n})")
        self.progLabel2.setText(f"Processed {total_file_count - 1} of {total_files} files in total")

        perc = total_file_count / total_files * 100
        self.pb.setValue(perc)
        if int(perc) == 100:
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    @pyqtSlot(str, int)
    def on_processing_complete(self, t, total_files):
        """Update progress bar dialog when processing is complete and report runtime."""

        # Update last logger in list to "Complete" (first strip " - Processing")
        i = self.loggersList.count() - 1
        logger = self.loggersList.item(i).text()
        pos = logger.find(" - Processing")
        self.loggersList.item(i).setText(f"{logger[:pos]} - Complete")

        # Update progress label to indicate all files have been processed
        self.progLabel2.setText(f"Processed {total_files} of {total_files} files in total")

        # Write runtime
        self.procCompleteLabel.setText("Processing complete: elapsed time = " + t)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    win = ProcessingProgressBar()
    win.show()
    sys.exit(app.exec_())
