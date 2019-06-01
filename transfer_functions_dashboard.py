import logging
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


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

    def init_ui(self):
        # Setup container
        setupWidget = QtWidgets.QWidget()
        setupWidget.setFixedWidth(200)
        vboxSetup = QtWidgets.QVBoxLayout(setupWidget)

        self.loadFile = QtWidgets.QPushButton("Load Transfer Functions")
        self.loadFile.setToolTip("Load transfer functions file")
        filesLabel = QtWidgets.QLabel("Transfer Functions")
        self.transferFuncsList = QtWidgets.QListWidget()
        self.plotButton = QtWidgets.QPushButton("Plot Transfer Functions")

        # Add setup widgets
        vboxSetup.addWidget(self.loadFile)
        vboxSetup.addWidget(filesLabel)
        vboxSetup.addWidget(self.transferFuncsList)
        vboxSetup.addWidget(self.plotButton)

        # Plot container
        plotWidget = QtWidgets.QWidget()
        vboxPlot = QtWidgets.QVBoxLayout(plotWidget)

        # Plot figure and canvas to display figure
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # Add plot widgets
        vboxPlot.addWidget(navbar)
        vboxPlot.addWidget(self.canvas)

        # Final layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(setupWidget)
        layout.addWidget(plotWidget)

    def connect_signals(self):
        pass
        # self.loadFile.clicked.connect(self.parent.load_logger_file)
        # self.settingsButton.clicked.connect(self.open_plot_options)
        self.plotButton.clicked.connect(self.plot)
        # self.transferFuncsList.itemDoubleClicked.connect(self.on_file_double_clicked)

    def plot(self):
        self.ax.cla()
        try:
            df = pd.read_clipboard()
            df = df.set_index(df.columns[0])
            df.plot(ax=self.ax)
            # self.ax.set_yscale('log')
            self.ax.set_xlabel("Frequency (Hz)")
            self.ax.set_ylabel("PSD Bending Moment / PSD Acceleration")
            self.ax.set_title("Frequency Dependent Transfer Functions")
            self.ax.set_xlim(0, 0.5)
        except:
            pass
        self.canvas.draw()


# For testing layout
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = TransferFunctionsWidget()
    win.show()
    sys.exit(app.exec_())
