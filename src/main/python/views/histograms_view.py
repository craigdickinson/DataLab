"""Rainflow counting histograms dashboard view."""

__author__ = "Craig Dickinson"

import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5 import QtWidgets
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


class HistogramDashboard(QtWidgets.QWidget):
    """Create dashboard for rainflow counting histograms."""

    def __init__(self, parent=None):
        super(HistogramDashboard, self).__init__(parent)

        # So can access parent class
        self.parent = parent
        plt.style.use("seaborn")

        # Container for data screen object of each processed logger
        self.data_screen_sets = []

        # Histogram data and widget lists
        self.dict_datasets = {}

        # Channel units for every processed dataset
        self.dict_dataset_units = {}

        # Flags to control processing combo box selection changes
        self.user_changed_dataset = False
        self.user_changed_column = False

        # Selected plot data parameters
        self.dataset = ""
        self.dataset_i = 0
        self.dataset_col = ""
        self.dataset_col_i = 0
        self.hist_col = ""
        self.hist_col_i = 0
        self.df_hist = pd.DataFrame()

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # WIDGETS
        self.openHistFileButton = QtWidgets.QPushButton("Open Histograms...")
        self.openHistFileButton.setToolTip("Open histograms file")
        self.clearDatasetsButton = QtWidgets.QPushButton("Clear Datasets")
        self.datasetCombo = QtWidgets.QComboBox()
        self.columnCombo = QtWidgets.QComboBox()
        self.histogramList = QtWidgets.QListWidget()

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
        self.settingsWidget = QtWidgets.QWidget()
        self.settingsWidget.setMinimumWidth(200)
        self.vboxSetup = QtWidgets.QVBoxLayout(self.settingsWidget)
        self.vboxSetup.addWidget(self.openHistFileButton)
        self.vboxSetup.addWidget(self.clearDatasetsButton)
        self.vboxSetup.addLayout(self.form)
        self.vboxSetup.addWidget(self.lblHistograms)
        self.vboxSetup.addWidget(self.histogramList)

        # Plot container
        self.plotWidget = QtWidgets.QWidget()
        self.vboxPlot = QtWidgets.QVBoxLayout(self.plotWidget)
        self.vboxPlot.addWidget(navbar)
        self.vboxPlot.addWidget(self.canvas)

        # Splitter to allow resizing of widget containers
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.settingsWidget)
        splitter.addWidget(self.plotWidget)
        splitter.setSizes([200, 10000])

        # LAYOUT
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(splitter)

    def _connect_signals(self):
        self.openHistFileButton.clicked.connect(self.on_open_histogram_file_clicked)
        self.datasetCombo.currentIndexChanged.connect(self.on_dataset_combo_changed)
        self.columnCombo.currentIndexChanged.connect(self.on_column_combo_changed)
        self.histogramList.itemDoubleClicked.connect(self.on_histogram_double_clicked)

    def on_open_histogram_file_clicked(self):
        self.parent.open_wcfat_damage_file()

    def on_dataset_combo_changed(self):
        if self.datasetCombo.currentIndex() == -1:
            return

        if self.user_changed_column is True:
            return

        self.user_changed_dataset = True
        self.dataset = self.datasetCombo.currentText()
        self.dataset_i = self.datasetCombo.currentIndex()
        self.update_column_combo()
        df_histogram = self.dict_datasets[self.dataset][self.dataset_col]
        self.update_histogram_list(df_histogram)
        self.plot_histogram(df_histogram)
        self.user_changed_dataset = False

    def on_column_combo_changed(self):
        if self.columnCombo.currentIndex() == -1:
            return

        if self.user_changed_dataset is True:
            return

        self.user_changed_column = True
        self.dataset_col = self.columnCombo.currentText()
        self.dataset_col_i = self.columnCombo.currentIndex()
        df_histogram = self.dict_datasets[self.dataset][self.dataset_col]
        self.update_histogram_list(df_histogram)
        self.plot_histogram(df_histogram)
        self.user_changed_column = False

    def on_histogram_double_clicked(self):
        self.dataset_col = self.columnCombo.currentText()
        self.dataset_col_i = self.columnCombo.currentIndex()
        self.hist_col = self.histogramList.currentItem().text()
        self.hist_col_i = self.histogramList.currentRow()

        # Retrieve dataframe of load case histograms for a given dataset and column
        df_histogram = self.dict_datasets[self.dataset][self.dataset_col]
        self.plot_histogram(df_histogram)

    def store_dataset_units(self, data_screen_sets):
        """Retrieve units from data screen objects."""

        self.dict_dataset_units = {
            data_screen.logger_id: data_screen.logger.channel_units
            for data_screen in data_screen_sets
        }

    def update_dataset_combo(self, datasets):
        """Add datasets to combo."""

        self.dataset = datasets[0]
        self.datasetCombo.clear()
        self.datasetCombo.addItems(datasets)

    def update_column_combo(self):
        """Update column combo for selected dataset."""

        dict_dataset = self.dict_datasets[self.dataset]
        self.columnCombo.clear()
        self.columnCombo.addItems(list(dict_dataset.keys()))
        self.columnCombo.setCurrentIndex(self.dataset_col_i)
        self.dataset_col = self.columnCombo.currentText()

    def update_histogram_list(self, df_histogram: pd.DataFrame):
        hist_cols = df_histogram.columns.tolist()
        self.hist_col = hist_cols[self.hist_col_i]
        self.histogramList.clear()
        self.histogramList.addItems(hist_cols)
        self.histogramList.setCurrentRow(self.hist_col_i)

    def plot_histogram(self, df_histogram: pd.DataFrame):
        if self.histogramList.count() == 0:
            return

        x = df_histogram.index.values
        y = df_histogram[self.hist_col].values
        units = self.dict_dataset_units[self.dataset][self.dataset_col_i]
        try:
            width = x[1] - x[0]
        except IndexError:
            width = 0.1

        ax = self.ax
        ax.cla()

        # Fatigue damage rate plot
        ax.bar(x, y, width=width, align="edge")
        ax.set_xlabel(f"Bins ({units})")
        ax.set_ylabel("Number of Cycles")
        ax.margins(0)

        self._set_title()
        # self.fig.tight_layout(rect=[0, 0, 1, 0.9])
        self.fig.tight_layout()
        self.canvas.draw()

    def _set_title(self):
        """Set plot title."""

        # Attempt to retrieve title from project setup dashboard
        project_name = self.parent.inputDataModule.control.project_name
        campaign_name = self.parent.inputDataModule.control.campaign_name

        if project_name == "":
            project_name = "Project Title"
        if campaign_name == "":
            campaign_name = "Campaign Title"

        fat_loc = f"{self.dataset} {self.dataset_col} - {self.hist_col} Histogram"
        title = f"{project_name} - {campaign_name}\n{fat_loc}"
        # self.fig.suptitle(title, **title_args)
        self.ax.set_title(title, **title_args)


# For testing layout
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = HistogramDashboard()
    win.show()
    sys.exit(app.exec_())
