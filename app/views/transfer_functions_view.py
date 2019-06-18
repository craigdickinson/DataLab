import os
import logging
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from app.core.calc_transfer_functions import TransferFunctions


class TransferFunctionsWidget(QtWidgets.QWidget):
    """Create raw time series plots widget."""

    # "2H blue"
    color_2H = np.array([0, 49, 80]) / 255

    def __init__(self, parent=None):
        super(TransferFunctionsWidget, self).__init__(parent)

        # So can access parent class
        self.parent = parent
        plt.style.use("seaborn")

        self.init_ui()
        self.connect_signals()
        self.tf = TransferFunctions()

    def init_ui(self):
        # Setup container
        self.vbox1 = QtWidgets.QVBoxLayout()

        self.setTTPathsButton = QtWidgets.QPushButton("Set Paths Time Traces")
        self.calcTFButton = QtWidgets.QPushButton("Generate Transfer Functions")
        self.exportSSTFButton = QtWidgets.QPushButton("Export Seastate TFs")
        self.exportAveTFButton = QtWidgets.QPushButton("Export Average TFs")
        self.loadFileButton = QtWidgets.QPushButton("Load Transfer Functions")
        self.loadFileButton.setToolTip("Load transfer functions file")

        self.filesLabel = QtWidgets.QLabel("Transfer Functions")
        self.transferFuncsList = QtWidgets.QListWidget()
        self.transferFuncsList.setFixedWidth(160)

        # Plot selection group
        self.plotGroup = QtWidgets.QGroupBox("Select Transfer Function")
        self.loggerCombo = QtWidgets.QComboBox()
        self.locCombo = QtWidgets.QComboBox()

        self.form = QtWidgets.QFormLayout(self.plotGroup)
        self.form.addRow(QtWidgets.QLabel("Logger:"), self.loggerCombo)
        self.form.addRow(QtWidgets.QLabel("Location:"), self.locCombo)

        self.plotButton = QtWidgets.QPushButton("Replot")

        # Add setup widgets
        self.vbox1.addWidget(self.setTTPathsButton)
        self.vbox1.addWidget(self.calcTFButton)
        self.vbox1.addWidget(self.exportSSTFButton)
        self.vbox1.addWidget(self.exportAveTFButton)
        self.vbox1.addWidget(self.loadFileButton)
        self.vbox1.addWidget(self.filesLabel)
        self.vbox1.addWidget(self.transferFuncsList)
        self.vbox1.addWidget(self.plotGroup)
        self.vbox1.addWidget(self.plotButton)
        # self.vbox1.addStretch()

        # Plot container
        self.vbox2 = QtWidgets.QVBoxLayout()

        # Plot figure and canvas to display figure
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # Add plot widgets
        self.vbox2.addWidget(navbar)
        self.vbox2.addWidget(self.canvas)

        # Final layout
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addLayout(self.vbox1)
        self.layout.addLayout(self.vbox2)

    def connect_signals(self):
        self.setTTPathsButton.clicked.connect(self.on_set_path_clicked)
        self.calcTFButton.clicked.connect(self.on_calc_trans_funcs_clicked)
        self.exportSSTFButton.clicked.connect(self.on_export_ss_tf_button_clicked)
        self.exportAveTFButton.clicked.connect(self.on_export_ave_tf_button_clicked)
        self.plotButton.clicked.connect(self.plot)

    def on_set_path_clicked(self):
        setPaths = SetPathDialog(self, self.tf)
        setPaths.set_dialog_data()
        setPaths.show()

    def on_calc_trans_funcs_clicked(self):
        """Calculate transfer functions from time series in csv files in folders of set paths."""

        debug = 1
        if debug == 1:
            root = r"C:\Users\dickinsc\PycharmProjects\DataLab\demo_data\3. Transfer Functions"
            self.tf.bm_dir = os.path.join(root, "Hot Spots BM Z")
            self.tf.disp_dir = os.path.join(root, "Loggers Disp Y")
            self.tf.rot_dir = os.path.join(root, "Loggers Rot Z")

        self.tf.get_files()
        self.tf.read_fea_time_traces()
        self.tf.calc_g_cont_accs()
        self.tf.clean_acc_and_bm_dataframes()
        self.tf.calc_logger_acc_psds()
        self.tf.calc_location_bm_psds()
        self.tf.calc_trans_funcs()
        self.tf.calc_weighted_ave_trans_funcs()

        # Populate gui
        self.transferFuncsList.clear()
        # self.transferFuncsList.addItems(self.tf.tf_names)

        for tf in self.tf.tf_names:
            item = QtWidgets.QListWidgetItem(tf)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
            self.transferFuncsList.addItem(item)

        self.loggerCombo.clear
        self.loggerCombo.addItems(self.tf.logger_names)
        self.locCombo.clear
        self.locCombo.addItems(self.tf.loc_names)

        self.plot()

    def on_export_ss_tf_button_clicked(self):
        # Export transfer functions to csv files (parse project root path)
        root_dir = self.parent.control.project_path
        if root_dir == "":
            root_dir = os.getcwd()

        retval = self.tf.export_seastate_transfer_functions(root_dir)

        if retval is True:
            path = os.path.join(root_dir, self.tf.output_folder1)
            msg = f"Transfer functions exported successfully to:\n{path}"
            return QtWidgets.QMessageBox.information(self, "Export Transfer Functions", msg)

    def on_export_ave_tf_button_clicked(self):
        # Export transfer functions to csv files (parse project root path)
        root_dir = self.parent.control.project_path
        if root_dir == "":
            root_dir = os.getcwd()

        retval = self.tf.export_weighted_ave_trans_funcs(root_dir)

        if retval is True:
            path = os.path.join(root_dir, self.tf.output_folder2)
            msg = f"Transfer functions exported successfully to:\n{path}"
            return QtWidgets.QMessageBox.information(self, "Export Transfer Functions", msg)

    def plot(self):
        self.ax.cla()
        try:
            # df = pd.read_clipboard()

            logger_i = self.loggerCombo.currentIndex()
            loc_i = self.locCombo.currentIndex()

            # Select TF data frame
            df = self.tf.trans_funcs[logger_i][loc_i]
            df.plot(ax=self.ax)
            # self.ax.set_yscale('log')
            self.ax.set_xlabel("Frequency (Hz)")
            self.ax.set_ylabel("PSD Bending Moment / PSD Acceleration")
            self.ax.set_title("Frequency-Dependent Transfer Functions")
            self.ax.set_xlim(0, 0.5)
            self.fig.tight_layout()
        except:
            pass
        self.canvas.draw()




# For testing layout
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = TransferFunctionsWidget()
    # win = SetPathDialog()
    win.show()
    sys.exit(app.exec_())
