"""Transfer functions dashboard gui view."""

__author__ = "Craig Dickinson"

import os
import logging
import sys

import matplotlib.pyplot as plt
import numpy as np
from PyQt5 import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from app.core.calc_transfer_functions import TransferFunctions

# 2H blue colour font
color_2H = np.array([0, 49, 80]) / 255

# Title style args
title_args = dict(size=14, fontname="tahoma", color=color_2H, weight="bold")


class TransferFunctionsWidget(QtWidgets.QWidget):
    """Create raw time series plots widget."""

    def __init__(self, parent=None):
        super(TransferFunctionsWidget, self).__init__(parent)

        # So can access parent class
        self.parent = parent
        plt.style.use("seaborn")
        self._init_ui()
        self._connect_signals()
        self.tf = TransferFunctions()

    def _init_ui(self):
        # WIDGETS
        self.openTFsButton = QtWidgets.QPushButton("Open Transfer Functions...")
        self.openTFsButton.setToolTip("Open transfer functions (*.csv) (F5)")
        self.exportSSTFButton = QtWidgets.QPushButton("Export Sea State TFs")
        self.exportAveTFButton = QtWidgets.QPushButton("Export Averaged TFs")
        self.filesLabel = QtWidgets.QLabel("Transfer Functions")
        self.transferFuncsList = QtWidgets.QListWidget()
        self.transferFuncsList.setFixedWidth(210)
        self.loggerCombo = QtWidgets.QComboBox()
        self.locCombo = QtWidgets.QComboBox()
        self.plotButton = QtWidgets.QPushButton("Replot")

        # Plot figure and canvas to display figure
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # CONTAINERS
        # Plot selection group
        self.plotGroup = QtWidgets.QGroupBox("Select Transfer Function")
        self.form = QtWidgets.QFormLayout(self.plotGroup)
        self.form.addRow(QtWidgets.QLabel("Logger:"), self.loggerCombo)
        self.form.addRow(QtWidgets.QLabel("Location:"), self.locCombo)

        # Setup container
        self.vbox1 = QtWidgets.QVBoxLayout()
        self.vbox1.addWidget(self.openTFsButton)
        self.vbox1.addWidget(self.exportSSTFButton)
        self.vbox1.addWidget(self.exportAveTFButton)
        self.vbox1.addWidget(self.filesLabel)
        self.vbox1.addWidget(self.transferFuncsList)
        self.vbox1.addWidget(self.plotGroup)
        self.vbox1.addWidget(self.plotButton)

        # Plot container
        self.vbox2 = QtWidgets.QVBoxLayout()
        self.vbox2.addWidget(navbar)
        self.vbox2.addWidget(self.canvas)

        # LAYOUT
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addLayout(self.vbox1)
        self.layout.addLayout(self.vbox2)

    def _connect_signals(self):
        self.openTFsButton.clicked.connect(self.on_open_tfs_clicked)
        self.exportSSTFButton.clicked.connect(self.on_export_ss_tf_button_clicked)
        self.exportAveTFButton.clicked.connect(self.on_export_ave_tf_button_clicked)
        self.plotButton.clicked.connect(self.plot)

    def plot_transfer_functions(self):
        # Populate gui
        self.transferFuncsList.clear()

        for tf in self.tf.tf_names:
            item = QtWidgets.QListWidgetItem(tf)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
            self.transferFuncsList.addItem(item)

        self.loggerCombo.clear()
        self.loggerCombo.addItems(self.tf.logger_names)
        self.locCombo.clear()
        self.locCombo.addItems(self.tf.loc_names)
        self.plot()

    def on_open_tfs_clicked(self):
        """Open existing transfer functions csv file to visualise plots."""

        return QtWidgets.QMessageBox.information(
            self, "To Do", "Feature coming in a future update."
        )

    def on_export_ss_tf_button_clicked(self):
        """Export individual sea state transfer functions to csv files."""

        root_dir = ""
        if self.parent:
            root_dir = self.parent.control.project_path

        if root_dir == "":
            root_dir = os.getcwd()

        # Write transfer functions to file
        retval = self.tf.export_seastate_transfer_functions(root_dir)

        if retval is True:
            path = os.path.join(root_dir, self.tf.output_folder1)
            msg = f"Transfer functions exported successfully to:\n{path}"
            return QtWidgets.QMessageBox.information(
                self, "Export Transfer Functions", msg
            )

    def on_export_ave_tf_button_clicked(self):
        """Export sea state percentage occurrence averaged transfer functions to csv files."""

        root_dir = ""
        if self.parent:
            root_dir = self.parent.control.project_path

        if root_dir == "":
            root_dir = os.getcwd()

        # Write transfer functions to file
        retval = self.tf.export_weighted_ave_trans_funcs(root_dir)

        if retval is True:
            path = os.path.join(root_dir, self.tf.output_folder2)
            msg = f"Transfer functions exported successfully to:\n{path}"
            return QtWidgets.QMessageBox.information(
                self, "Export Transfer Functions", msg
            )

    def plot(self):
        self.ax.cla()
        try:
            # df = pd.read_clipboard()

            logger = self.loggerCombo.currentText()
            loc = self.locCombo.currentText()
            logger_i = self.loggerCombo.currentIndex()
            loc_i = self.locCombo.currentIndex()

            # Select TF data frame
            df = self.tf.trans_funcs[logger_i][loc_i]
            df.plot(ax=self.ax)
            labels = [f"Sea State {i + 1}" for i in range(self.tf.num_ss)]

            # Plot weighted-averaged transfer function if exists
            if self.tf.ave_tfs:
                df = self.tf.ave_tfs[logger_i].iloc[:, loc_i]
                labels.append("Weighted-average")
                self.ax.plot(df, c="k", lw=2)

            # Update legend
            self.ax.legend(labels)

            # self.ax.set_yscale('log')
            ylabel = "Acceleration to Bending Moment TF\n$\mathregular{(Nm)^2}$/$\mathregular{(m/s^2)^2}$"
            title = f"Frequency-Dependent Transfer Functions\n{logger} {loc}"
            self.ax.set_xlabel("Frequency (Hz)")
            self.ax.set_ylabel(ylabel)
            self.ax.set_title(title, **title_args)
            self.ax.set_xlim(0, 0.5)
            self.fig.tight_layout()
        except Exception as e:
            logging.exception(e)
        self.canvas.draw()


# For testing layout
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = TransferFunctionsWidget()
    win.show()
    sys.exit(app.exec_())
