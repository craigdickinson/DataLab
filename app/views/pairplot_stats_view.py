import sys
import seaborn as sns
import pandas as pd
from PyQt5 import QtCore, QtWidgets
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


class PairPlotView(QtWidgets.QWidget):
    """Pair plot widget."""

    def __init__(self, parent=None):
        super(PairPlotView, self).__init__(parent)

        self.parent = parent
        self.datasets = []

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # WIDGETS
        # Buttons and datasets list
        self.combineDatasetsButton = QtWidgets.QPushButton("Combine Datasets")
        self.clearDatasetsButton = QtWidgets.QPushButton("Clear Datasets")
        self.plotButton = QtWidgets.QPushButton("Replot")
        self.datasetsList = QtWidgets.QListWidget()

        # Channel selectors
        self.ch1Combo = QtWidgets.QComboBox()
        self.ch2Combo = QtWidgets.QComboBox()
        self.ch3Combo = QtWidgets.QComboBox()
        self.ch4Combo = QtWidgets.QComboBox()
        self.ch5Combo = QtWidgets.QComboBox()
        self.ch6Combo = QtWidgets.QComboBox()

        # Plot figure, canvas and navbar
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # CONTAINERS
        # Plot selection group
        self.plotGroup = QtWidgets.QGroupBox("Select Plot Channels")
        self.vbox = QtWidgets.QVBoxLayout(self.plotGroup)
        self.vbox.addWidget(QtWidgets.QLabel("Channel 1:"))
        self.vbox.addWidget(self.ch1Combo)
        self.vbox.addWidget(QtWidgets.QLabel("Channel 2:"))
        self.vbox.addWidget(self.ch2Combo)
        self.vbox.addWidget(QtWidgets.QLabel("Channel 3:"))
        self.vbox.addWidget(self.ch3Combo)
        self.vbox.addWidget(QtWidgets.QLabel("Channel 4:"))
        self.vbox.addWidget(self.ch4Combo)
        self.vbox.addWidget(QtWidgets.QLabel("Channel 5:"))
        self.vbox.addWidget(self.ch5Combo)
        self.vbox.addWidget(QtWidgets.QLabel("Channel 6:"))
        self.vbox.addWidget(self.ch6Combo)

        # Selection container
        self.selectionContainer = QtWidgets.QWidget()
        self.selectionContainer.setFixedWidth(200)
        self.vboxSel = QtWidgets.QVBoxLayout(self.selectionContainer)
        self.vboxSel.addWidget(self.combineDatasetsButton)
        self.vboxSel.addWidget(self.clearDatasetsButton)
        self.vboxSel.addWidget(QtWidgets.QLabel("Datasets"))
        self.vboxSel.addWidget(self.datasetsList)
        self.vboxSel.addWidget(self.plotGroup)
        self.vboxSel.addWidget(self.plotButton)
        self.vboxSel.addStretch()

        # Plot figure
        self.plotLayout = QtWidgets.QVBoxLayout()
        self.plotLayout.addWidget(navbar)
        self.plotLayout.addWidget(self.canvas)

        # LAYOUT
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(self.selectionContainer)
        self.layout.addLayout(self.plotLayout)

    def _connect_signals(self):
        self.plotButton.clicked.connect(self.on_plot_clicked)

    def on_plot_clicked(self):
        pass


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = PairPlotView()
    win.show()
    sys.exit(app.exec_())
