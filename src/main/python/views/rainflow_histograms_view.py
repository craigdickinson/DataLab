"""Rainflow counting histograms dashboard view."""

__author__ = "Craig Dickinson"

import sys

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

# 2H blue colour font
color_2H = np.array([0, 49, 80]) / 255

# Title style args
title_args = dict(size=14, fontname="tahoma", color=color_2H, weight="bold")


class RainflowHistograms(object):
    def __init__(self):
        self.dataset_name = ""
        self.columns = []
        self.histograms = {}


class RainflowHistogramDashboard(QtWidgets.QWidget):
    """Create dashboard for rainflow counting histograms."""

    def __init__(self, parent=None):
        super(RainflowHistogramDashboard, self).__init__(parent)

        # So can access parent class
        self.parent = parent
        plt.style.use("seaborn")

        self.datasets = {}
        self.dataset_ids = []
        self.columns = []
        self.files = []
        self.df_hist = pd.DataFrame()

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        # WIDGETS
        self.openHistFileButton = QtWidgets.QPushButton("Open Histograms File...")
        self.openHistFileButton.setToolTip("Open rainflow histograms file")
        self.clearDatasetsButton = QtWidgets.QPushButton("Clear Datasets")
        self.datasetCombo = QtWidgets.QComboBox()
        self.columnCombo = QtWidgets.QComboBox()
        self.histogramsList = QtWidgets.QListWidget()

        # Labels
        self.lblDataset = QtWidgets.QLabel("Dataset:")
        self.lblColumn = QtWidgets.QLabel("Column:")
        self.lblHistograms = QtWidgets.QLabel("Histograms")

        # Plot figure and canvas to display figure
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # CONTAINERS
        self.form = QtWidgets.QFormLayout()
        self.form.addRow(self.lblDataset, self.datasetCombo)
        self.form.addRow(self.lblColumn, self.columnCombo)

        # Setup container
        self.setupWidget = QtWidgets.QWidget()
        self.setupWidget.setFixedWidth(200)
        self.vboxSetup = QtWidgets.QVBoxLayout(self.setupWidget)
        self.vboxSetup.addWidget(self.openHistFileButton)
        self.vboxSetup.addWidget(self.clearDatasetsButton)
        self.vboxSetup.addLayout(self.form)
        self.vboxSetup.addWidget(self.lblHistograms)
        self.vboxSetup.addWidget(self.histogramsList)

        # Plot container
        self.plotWidget = QtWidgets.QWidget()
        self.vboxPlot = QtWidgets.QVBoxLayout(self.plotWidget)
        self.vboxPlot.addWidget(navbar)
        self.vboxPlot.addWidget(self.canvas)

        # LAYOUT
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(self.setupWidget)
        self.layout.addWidget(self.plotWidget)

    def connect_signals(self):
        self.openHistFileButton.clicked.connect(self.on_open_histogram_file_clicked)
        self.histogramsList.itemDoubleClicked.connect(
            self.on_histogram_file_double_clicked
        )

    def on_open_histogram_file_clicked(self):
        self.parent.open_wcfat_damage_file()

    def on_histogram_file_double_clicked(self):
        self.plot_histogram()

    def process_fatigue_damage_file(self, df_dam):
        # Backup original fatigue damage file
        self.df_dam_per_yr = df_dam.copy()
        self.update_histograms_list(fatigue_locs=df_dam.columns)

        # Determine the duration of each file (in minutes)
        self.event_length = self.get_event_length(df_dam)

        # Rescale reported fatigue damage rate
        self.df_dam_per_event = self.rescale_damage_rate(
            df_dam, period=self.event_length
        )

        if self.scale_dam_rate_to_event_len is True:
            self.df_dam = self.df_dam_per_event
        else:
            self.df_dam = self.df_dam_per_yr

        # Calculate cumulative fatigue damage and plot damage rate and CFD
        self.df_cfd = self.df_dam_per_event.cumsum()
        self.plot_histogram()

    def add_datasets(self, datasets):
        """Add datasets to combo."""

        self.dataset_ids = datasets
        self.datasetCombo.clear()
        self.datasetCombo.addItems(datasets)

    def update_columns_combo(self):
        """Update columns combo for selected dataset."""

        id = self.datasetCombo.currentText()
        dataset = self.datasets[id]
        self.columns = list(dataset.keys())
        self.columnCombo.clear()
        self.columnCombo.addItems(self.columns)

        # Store files
        df = dataset[self.columns[0]]
        self.files = df.columns.tolist()

        self.update_histograms_list()

    def update_histograms_list(self):
        self.histogramsList.clear()
        self.histogramsList.addItems(self.files)
        self.histogramsList.setCurrentRow(0)

    def plot_histogram(self):
        if self.histogramsList.count() == 0:
            return

        hist_name = self.histogramsList.currentItem().text()

        df = self.datasets[self.dataset_ids[0]][self.columns[0]]
        x = df.index.values
        y = df[hist_name].values
        try:
            width = x[1] - x[0]
        except:
            width = 0.1

        ax = self.ax
        ax.cla()

        # Fatigue damage rate plot
        ax.bar(x, y, width=width, align="edge")
        ax.set_xlabel("Range Bins")
        ax.set_ylabel("Number of Cycles")
        title = "Rainflow Counting Histogram"
        ax.set_title(title)
        ax.margins(0)

        self._set_title()
        self.fig.tight_layout(rect=[0, 0, 1, 0.9])
        self.canvas.draw()

    def _set_title(self):
        """Set plot title."""

        # Attempt to retrieve title from project setup dashboard
        project_name = self.parent.projConfigModule.control.project_name
        campaign_name = self.parent.projConfigModule.control.campaign_name

        if project_name == "":
            project_name = "Project Title"
        if campaign_name == "":
            campaign_name = "Campaign Title"

        fat_loc = self.histogramsList.currentItem().text()
        title = f"{project_name} - {campaign_name}\n{fat_loc}"
        self.fig.suptitle(title, **title_args)


# For testing layout
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = RainflowHistogramDashboard()
    win.show()
    sys.exit(app.exec_())
