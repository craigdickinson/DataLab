"""Fatigue damage plots dashboard gui view."""

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


class FatigueProcessingWidget(QtWidgets.QWidget):
    """Create raw time series plots widget."""

    def __init__(self, parent=None):
        super(FatigueProcessingWidget, self).__init__(parent)

        # So can access parent class
        self.parent = parent
        plt.style.use("seaborn")

        self.df_dam_per_yr = pd.DataFrame()
        self.df_dam_per_event = pd.DataFrame()
        self.df_dam = pd.DataFrame()
        self.df_cfd = pd.DataFrame()
        self.fat_loc = ""
        self.log_scale = True

        # None implies damage rate is per year
        self.scale_dam_rate_to_event_len = True
        self.period = "year"
        self.event_length = 20

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        # WIDGETS
        self.openWCFATFileButton = QtWidgets.QPushButton("Open 2HWCFAT Damage File...")
        self.openWCFATFileButton.setToolTip("Open 2HWCFAT fatigue damage (.dmg) file")
        self.openFATLASAFileButton = QtWidgets.QPushButton(
            "Open 2HFATLASA Damage File..."
        )
        self.openFATLASAFileButton.setToolTip(
            "Open 2HFATLASA max fatigue damage (.csv) file"
        )
        self.fatigueLocsList = QtWidgets.QListWidget()
        self.fatigueLocsList.setFixedHeight(150)
        self.damLogScale = QtWidgets.QCheckBox("Fatigue damage log scale")
        self.damLogScale.setChecked(True)
        self.damRatePerEvent = QtWidgets.QCheckBox("Scale damage rate per event")
        self.damRatePerEvent.setChecked(False)

        # Plot figure and canvas to display figure
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, sharex=True)
        self.canvas = FigureCanvas(self.fig)
        navbar = NavigationToolbar(self.canvas, self)

        # CONTAINERS
        # Setup container
        self.settingsWidget = QtWidgets.QWidget()
        self.settingsWidget.setMinimumWidth(200)
        self.vboxSetup = QtWidgets.QVBoxLayout(self.settingsWidget)
        self.vboxSetup.addWidget(self.openWCFATFileButton)
        self.vboxSetup.addWidget(self.openFATLASAFileButton)
        self.vboxSetup.addWidget(QtWidgets.QLabel("Assessed Fatigue Locations"))
        self.vboxSetup.addWidget(self.fatigueLocsList)
        self.vboxSetup.addWidget(self.damLogScale)
        self.vboxSetup.addWidget(self.damRatePerEvent)
        self.vboxSetup.addStretch()

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

    def connect_signals(self):
        self.openWCFATFileButton.clicked.connect(self.on_open_wcfat_file_clicked)
        self.openFATLASAFileButton.clicked.connect(self.on_open_fatlasa_file_clicked)
        self.fatigueLocsList.itemDoubleClicked.connect(
            self.on_fatigue_loc_double_clicked
        )
        self.damLogScale.stateChanged.connect(self.on_log_scale_changed)
        self.damRatePerEvent.stateChanged.connect(self.on_scale_damage_rate_changed)

    def on_open_wcfat_file_clicked(self):
        self.parent.open_wcfat_damage_file()

    def on_open_fatlasa_file_clicked(self):
        self.parent.open_fatlasa_damage_file()

    def on_fatigue_loc_double_clicked(self):
        self.plot_fatigue_damage()

    def on_log_scale_changed(self):
        if self.damLogScale.isChecked():
            self.log_scale = True
        else:
            self.log_scale = False

        self.plot_fatigue_damage()

    def on_scale_damage_rate_changed(self):
        if self.damRatePerEvent.isChecked():
            self.df_dam = self.df_dam_per_event
            self.period = f"{self.event_length} mins"
        else:
            self.df_dam = self.df_dam_per_yr
            self.period = "year"

        self.plot_fatigue_damage()

    def process_fatigue_damage_file(self, df_dam):
        # Backup original fatigue damage file
        self.df_dam_per_yr = df_dam.copy()
        self.update_fatigue_locs_list(fatigue_locs=df_dam.columns)

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
        self.plot_fatigue_damage()

    def update_fatigue_locs_list(self, fatigue_locs):
        self.fatigueLocsList.clear()
        self.fatigueLocsList.addItems(fatigue_locs)
        self.fatigueLocsList.setCurrentRow(0)

    def get_event_length(self, df):
        """Return the duration in minutes of each processed fatigue event."""

        # Assume all events are of the same length so only look at the interval between the first and second event
        td = df.index[1] - df.index[0]
        event_length = td.seconds // 60

        return event_length

    def rescale_damage_rate(self, df, period=None):
        """
        Transform fatigue damage rates from 1/year to period input (e.g. 20 minutes).
        :param df: Fatigue damage data frame - will be 1/year by default
        :param period: Event length in minutes to transform damage rate to. If None (default) damage rate is unchanged.
        :return: Fatigue damage data frame for transformed period
        """

        if period is None:
            return df
        else:
            factor = 365.24 * 24 * 60 / period
            return df / factor

    def plot_fatigue_damage(self):
        if self.fatigueLocsList.count() == 0:
            return

        fat_loc = self.fatigueLocsList.currentItem().text()

        if self.log_scale is True:
            damage = np.log10(self.df_dam[fat_loc])
            log10 = r"$\mathregular{log_{10}}$"
        else:
            damage = self.df_dam[fat_loc]
            log10 = ""

        cum_dam = self.df_cfd[fat_loc]

        ax1 = self.ax1
        ax2 = self.ax2
        ax1.cla()
        ax2.cla()

        # Fatigue damage rate plot
        ax1.plot(damage)
        ax1.set_ylabel(f"{log10}Fatigue Damage (1/{self.period})")
        title = f"Unfactored Fatigue Damage"
        ax1.set_title(title)
        ax1.margins(0)

        # Cumulative fatigue damage plot
        ax2.plot(cum_dam)
        ax2.set_ylabel("Cumulative Fatigue Damage")
        title = f"Unfactored Cumulative Fatigue Damage"
        ax2.set_title(title)
        ax2.margins(0)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b-%y"))
        ax2.xaxis.set_major_locator(mdates.DayLocator(interval=7))

        self.fig.autofmt_xdate()
        self._set_title()
        self.fig.tight_layout(rect=[0, 0, 1, 0.9])
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

        fat_loc = self.fatigueLocsList.currentItem().text()
        title = f"{project_name} - {campaign_name}\n{fat_loc}"
        self.fig.suptitle(title, **title_args)


# For testing layout
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = FatigueProcessingWidget()
    win.show()
    sys.exit(app.exec_())
