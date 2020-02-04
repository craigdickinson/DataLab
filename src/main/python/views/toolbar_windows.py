"""Setting dialogs used in QMainWindow toolbar.."""

__author__ = "Craig Dickinson"

import sys

from PyQt5 import QtWidgets, QtGui

from core.azure_cloud_storage import check_azure_account_exists
from core.control import Control


class AzureAccountSetupDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, control=Control()):
        super(AzureAccountSetupDialog, self).__init__(parent)

        account_name = control.azure_account_name
        account_key = control.azure_account_key

        # Default settings
        if account_name == "":
            account_name = "agl2hpocdatalab1store"
        if account_key == "":
            account_key = "25ZKbPuwSrzqS3Tv8DVeF58x0cy3rMA8VQPKHj3wRZoiWKTPoyllqFOL0EnEy9Dq+poASjV9nFoSIIC7/sBt6Q=="

        self.control = control
        self.account_name = account_name
        self.account_key = account_key
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setWindowTitle("Connect to Microsoft Azure Cloud Storage Account")

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
        self.setFixedSize(self.sizeHint())
        self.setFixedWidth(650)

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

        self.control.azure_account_name = self.accountName.text()
        self.control.azure_account_key = self.accountKey.text()


class FilterSettings(QtWidgets.QDialog):
    def __init__(self, parent=None, control=Control()):
        super(FilterSettings, self).__init__(parent)

        self.parent = parent
        self.control = control
        self.filter_types = ["Butterworth", "Rectangular"]
        self.filter_type = control.filter_type
        self.butterworth_order = control.butterworth_order
        self._init_ui()
        self._connect_signals()
        self._set_dialog_data()

    def _init_ui(self):
        self.setWindowTitle("Filter Type Settings")

        int_validator = QtGui.QIntValidator()
        int_validator.setBottom(1)

        # WIDGETS
        # Filter settings
        self.filterType = QtWidgets.QComboBox()
        self.filterType.addItems(self.filter_types)
        self.filterType.setFixedSize(self.filterType.sizeHint())
        self.butterOrder = QtWidgets.QLineEdit("6")
        self.butterOrder.setFixedWidth(20)
        self.butterOrder.setValidator(int_validator)

        # Button box
        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok
            | QtWidgets.QDialogButtonBox.Cancel
            | QtWidgets.QDialogButtonBox.Apply
            | QtWidgets.QDialogButtonBox.Reset
        )

        # CONTAINERS
        self.filterForm = QtWidgets.QFormLayout()
        self.filterForm.addRow(QtWidgets.QLabel("Filter type:"), self.filterType)
        self.filterForm.addRow(QtWidgets.QLabel("Butterworth order:"), self.butterOrder)

        # LAYOUT
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addLayout(self.filterForm)
        self.layout.addWidget(self.buttonBox)
        self.setFixedSize(self.sizeHint())

    def _connect_signals(self):
        self.filterType.currentIndexChanged.connect(self.on_filter_type_changed)
        self.buttonBox.accepted.connect(self.on_ok_clicked)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.on_ok_clicked)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Reset).clicked.connect(
            self.on_reset_clicked
        )

    def _set_dialog_data(self):
        self.filterType.setCurrentText(self.filter_type)
        self.butterOrder.setText(str(self.butterworth_order))

        # Call trigger to set widget state
        self.on_filter_type_changed()

    def on_filter_type_changed(self):
        if self.filterType.currentText() == "Butterworth":
            self.butterOrder.setEnabled(True)
        else:
            self.butterOrder.setEnabled(False)

    def on_ok_clicked(self):
        """Store filter settings in control object."""

        # Set filter settings
        self.control.filter_type = self.filterType.currentText()
        self.control.butterworth_order = int(self.butterOrder.text())

        # Replot plots on raw data dashboard to reflect any changes to filter settings
        self.parent.rawDataModule.filter_all_time_series()

        # This flag stops the on_xlims_changed event from processing
        self.parent.rawDataModule.skip_on_xlims_changed = True
        self.parent.rawDataModule.rebuild_plots()
        self.parent.rawDataModule.skip_on_xlims_changed = False

    def on_reset_clicked(self):
        """Reset plot settings to initial values set during file load."""

        self.filterType.setCurrentIndex(0)
        self.butterOrder.setText("6")


if __name__ == "__main__":
    # For testing widget layout
    app = QtWidgets.QApplication(sys.argv)
    # win = AzureAccountSetupDialog()
    win = FilterSettings()
    win.show()
    app.exit(app.exec_())
