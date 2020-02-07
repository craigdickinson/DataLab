"""Rainflow counting histograms dashboard view."""

__author__ = "Craig Dickinson"

import sys
import threading

# import dash
# import dash_core_components as dcc
# import dash_html_components as html
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5 import QtWidgets
from PyQt5.QtCore import QUrl

# from PyQt5.QtWebEngineWidgets import QWebEngineView
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.ticker import MultipleLocator, AutoLocator, AutoMinorLocator

# 2H blue colour font
color_2H = np.array([0, 49, 80]) / 255

# Title style args
title_args = dict(size=14, fontname="tahoma", color=color_2H, weight="bold")


# def run_dash(data, layout):
#     app = dash.Dash()
#
#     app.layout = html.Div(
#         children=[dcc.Graph(id="example-graph", figure={"data": data, "layout": layout})]
#     )
#     app.run_server(debug=False)


class RainflowHistograms(object):
    def __init__(self):
        self.dataset_name = ""
        self.columns = []
        self.histograms = {}


class CycleHistogramDashboard(QtWidgets.QWidget):
    """Create dashboard for rainflow counting histograms."""

    def __init__(self, parent=None):
        super(CycleHistogramDashboard, self).__init__(parent)

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

        # Plot controls
        self.xaxis_interval = "Auto"
        self.fixed_ymax = None
        self.bin_size = 0.1
        self.ymax = 1

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        # WIDGETS
        self.openHistFileButton = QtWidgets.QPushButton("Open Cycle Histograms...")
        self.openHistFileButton.setToolTip("Open cycle histograms file")
        self.clearDatasetsButton = QtWidgets.QPushButton("Clear Datasets")
        self.datasetCombo = QtWidgets.QComboBox()
        self.columnCombo = QtWidgets.QComboBox()
        self.histogramList = QtWidgets.QListWidget()
        self.xaxisInterval = QtWidgets.QLineEdit("Auto")
        self.xaxisInterval.setFixedWidth(50)
        self.fixedYmax = QtWidgets.QLineEdit("None")
        self.fixedYmax.setFixedWidth(50)

        # Labels
        self.lblDataset = QtWidgets.QLabel("Dataset:")
        self.lblColumn = QtWidgets.QLabel("Column:")
        self.lblHistograms = QtWidgets.QLabel("Cycle Histograms")
        self.lblFixedYmax = QtWidgets.QLabel("Fixed y-axis max:")
        self.lblXAxisInterval = QtWidgets.QLabel("X-axis interval:")

        # Plot figure and canvas to display figure
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # CONTAINERS
        self.form = QtWidgets.QFormLayout()
        self.form.addRow(self.lblDataset, self.datasetCombo)
        self.form.addRow(self.lblColumn, self.columnCombo)

        self.form2 = QtWidgets.QFormLayout()
        self.form2.addRow(self.lblXAxisInterval, self.xaxisInterval)
        self.form2.addRow(self.lblFixedYmax, self.fixedYmax)

        # Setup container
        self.settingsWidget = QtWidgets.QWidget()
        self.settingsWidget.setMinimumWidth(200)
        self.vboxSetup = QtWidgets.QVBoxLayout(self.settingsWidget)
        self.vboxSetup.addWidget(self.openHistFileButton)
        self.vboxSetup.addWidget(self.clearDatasetsButton)
        self.vboxSetup.addLayout(self.form)
        self.vboxSetup.addWidget(self.lblHistograms)
        self.vboxSetup.addWidget(self.histogramList)
        self.vboxSetup.addLayout(self.form2)

        # Plot container
        self.plotWidget = QtWidgets.QWidget()
        self.vboxPlot = QtWidgets.QVBoxLayout(self.plotWidget)
        self.vboxPlot.addWidget(navbar)
        self.vboxPlot.addWidget(self.canvas)

        # Plotly and dash alternative
        # self.webPlot = QWebEngineView(self)
        # self.vboxPlot.addWidget(self.webPlot)

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
        self.xaxisInterval.returnPressed.connect(self.on_xaxis_interval_changed)
        self.fixedYmax.returnPressed.connect(self.on_fixed_ymax_changed)

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

    def on_xaxis_interval_changed(self):
        val = self.xaxisInterval.text()
        try:
            self.xaxis_interval = float(val)
        except ValueError:
            self.xaxis_interval = "Auto"
            self.xaxisInterval.setText(val)

        self._set_xaxis_interval()
        self.canvas.draw()

    def on_fixed_ymax_changed(self):
        val = self.fixedYmax.text()
        try:
            self.fixed_ymax = float(val)
        except ValueError:
            self.fixed_ymax = None
            self.fixedYmax.setText("None")

        self._set_ylim()
        self.canvas.draw()

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
        self.histogramList.clear()
        hist_cols = df_histogram.columns.tolist()

        # If only one column then implies no histograms as only the Aggregate column exists
        if len(hist_cols) == 1:
            return
        else:
            self.histogramList.addItems(hist_cols)

            # Select previous item
            try:
                self.hist_col = hist_cols[self.hist_col_i]
                self.histogramList.setCurrentRow(self.hist_col_i)
            except IndexError:
                pass

    def plot_histogram(self, df_histogram: pd.DataFrame):
        self.pyplot_histogram(df_histogram)
        # self.webplot_histogram(df_histogram)

    def pyplot_histogram(self, df_histogram: pd.DataFrame):
        """Create histogram plot."""

        if self.histogramList.count() == 0:
            return

        x = df_histogram.index.values
        y = df_histogram[self.hist_col].values
        units = self.dict_dataset_units[self.dataset][self.dataset_col_i]
        try:
            self.bin_size = x[1] - x[0]
        except IndexError:
            self.bin_size = 0.1

        ax = self.ax
        ax.cla()

        # Plot cycle histogram
        ax.bar(x, y, width=self.bin_size, align="edge", edgecolor="k")
        ax.set_xlabel(f"Bins ({units})")
        ax.set_ylabel("Number of Cycles")
        ax.margins(x=0)

        # Store y max for retrieval if not using fixed y-axis y max
        self.ymax = ax.get_ylim()[1]
        self._set_ylim()
        # ax.set_ylim(0, np.ceil(y.max()))

        # Set x axis intervals
        self._set_xaxis_interval()
        # ax.xaxis.set_major_locator(AutoLocator())
        # ax.xaxis.set_major_locator(MultipleLocator(width))
        # ax.xaxis.set_minor_locator(MultipleLocator(self.bin_size))
        ax.tick_params(which="major", length=5)
        ax.tick_params(which="minor", length=2)

        title = self._plot_title()
        # self.fig.suptitle(title, **title_args)
        self.ax.set_title(title, **title_args)

        # self.fig.tight_layout(rect=[0, 0, 1, 0.9])
        self.fig.tight_layout()
        self.canvas.draw()

    # def webplot_histogram(self, df_histogram: pd.DataFrame):
    #     """Create histogram plot."""
    #
    #     if self.histogramList.count() == 0:
    #         return
    #
    #     x = df_histogram.index.values
    #     y = df_histogram[self.hist_col].values
    #     units = self.dict_dataset_units[self.dataset][self.dataset_col_i]
    #     try:
    #         width = x[1] - x[0]
    #     except IndexError:
    #         width = 0.1
    #
    #     data = [dict(x=x, y=y, type="bar")]
    #     title = self._plot_title()
    #     layout = dict(title=title)
    #
    #     # TODO: How to update for other plots?
    #     threading.Thread(target=run_dash, args=(data, layout), daemon=True).start()
    #     self.webPlot.load(QUrl("http://127.0.0.1:8050/"))
    #     self.webPlot.show()

    def _plot_title(self):
        """Set plot title."""

        # Attempt to retrieve title from project setup dashboard
        project_name = self.parent.inputDataModule.control.project_name
        campaign_name = self.parent.inputDataModule.control.campaign_name

        title = project_name
        if project_name == "":
            title = "Project Title"
        if campaign_name != "":
            title += " - " + campaign_name

        fat_loc = f"{self.dataset} {self.dataset_col} - {self.hist_col} Cycle Histogram"
        title = f"{title}\n{fat_loc}"

        return title

    def _set_xaxis_interval(self):
        """Set x-axis bin tick intervals to user value or plot auto."""

        if self.xaxis_interval == "Auto":
            self.ax.xaxis.set_major_locator(AutoLocator())
        else:
            self.ax.xaxis.set_major_locator(MultipleLocator(self.xaxis_interval))

        # self.ax.xaxis.set_minor_locator(MultipleLocator(self.bin_size))

    def _set_ylim(self):
        """Set y-limit max to either a user set value or default plot max."""

        if self.fixed_ymax:
            self.ax.set_ylim(0, self.fixed_ymax)
        else:
            self.ax.set_ylim(0, self.ymax)


# For testing layout
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = CycleHistogramDashboard()
    win.show()
    sys.exit(app.exec_())
