__author__ = "Craig Dickinson"

import sys

from PyQt5 import QtWidgets

from data_screening_view import DataQualityReport
from fatigue_view import FatigueProcessingWidget
from project_config_view import ConfigModule
from raw_data_view import TimeSeriesPlotWidget
from seascatter_view import SeascatterDiagram
from spectral_view import SpectrogramWidget
from stats_view import PlotStyle2H, StatsWidget, VesselStatsWidget
from transfer_functions_view import TransferFunctionsWidget


class DataLabGui(QtWidgets.QMainWindow):
    """Class to create DataLab ui widgets and layout."""

    def __init__(self):
        super().__init__()

        self.init_ui()

    def init_ui(self):
        """Initialise gui."""

        self.setGeometry(50, 50, 1400, 800)

        # Create stacked central widget
        self.modulesWidget = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.modulesWidget)
        self.statusbar = self.statusBar()

        # Create menu bar and tool bar
        self.menu_bar()
        self.tool_bar()

        # Project config module
        self.projConfigModule = ConfigModule(self)

        # Raw data inspection module
        self.rawDataModule = QtWidgets.QTabWidget()
        self.timeSeriesTab = TimeSeriesPlotWidget(self)
        self.rawDataModule.addTab(self.timeSeriesTab, "Time Series")

        # Data quality screening report module
        self.dataQualityModule = DataQualityReport(self)

        # Stats screening module
        self.statsScreeningModule = QtWidgets.QTabWidget()
        self.statsTab = StatsWidget(self)
        self.vesselStatsTab = VesselStatsWidget(self)
        self.statsScreeningModule.addTab(self.statsTab, "Statistics")
        self.statsScreeningModule.addTab(self.vesselStatsTab, "Vessel Statistics")

        # Spectral screening module
        self.spectralScreeningModule = QtWidgets.QTabWidget()
        self.spectrogramTab = SpectrogramWidget(self)
        self.spectralScreeningModule.addTab(self.spectrogramTab, "Spectrograms")

        # Seascatter diagram module
        self.seascatterModule = SeascatterDiagram(self)

        # Transfer functions module
        self.transFuncsModule = QtWidgets.QTabWidget()
        self.transferFuncsTab = TransferFunctionsWidget(self)
        self.transFuncsModule.addTab(
            self.transferFuncsTab, "2HFATLASA Transfer Functions"
        )

        # Fatigue processing module
        self.fatigueModule = QtWidgets.QTabWidget()
        self.fatigueTab = FatigueProcessingWidget(self)
        self.fatigueModule.addTab(self.fatigueTab, "2HFATLASA")

        # Add stacked widgets
        self.modulesWidget.addWidget(self.projConfigModule)
        self.modulesWidget.addWidget(self.rawDataModule)
        self.modulesWidget.addWidget(self.dataQualityModule)
        self.modulesWidget.addWidget(self.statsScreeningModule)
        self.modulesWidget.addWidget(self.spectralScreeningModule)
        self.modulesWidget.addWidget(self.seascatterModule)
        self.modulesWidget.addWidget(self.transFuncsModule)
        self.modulesWidget.addWidget(self.fatigueModule)

        # 2H plotting class
        self.plot_2h = PlotStyle2H(self.statsTab.canvas, self.statsTab.fig)

    def menu_bar(self):
        """Create menu bar."""

        # Menu bar
        menubar = self.menuBar()

        # Primary menus
        menuFile = menubar.addMenu("&File")
        menuView = menubar.addMenu("&View")
        menuProcess = menubar.addMenu("&Process")
        menuLogic = menubar.addMenu("&Applied Logic")
        menuPlotSettings = menubar.addMenu("&Plot Settings")
        menuExport = menubar.addMenu("&Export")
        menuAbout = menubar.addMenu("&Help")

        # File menu
        # Open submenu
        openMenu = menuFile.addMenu("&Open")
        self.loadConfigFile = QtWidgets.QAction("Config File")
        self.loadConfigFile.setShortcut("Ctrl+Shift+C")
        self.loadConfigFile.setStatusTip("Load config file (*.json)")
        self.openLoggerFile = QtWidgets.QAction("Logger File")
        self.openLoggerFile.setShortcut("Ctrl+O")
        self.openLoggerStats = QtWidgets.QAction("Logger Stats")
        self.openLoggerStats.setShortcut("Ctrl+Shift+O")
        self.openSpectrograms = QtWidgets.QAction("Spectrograms")
        self.openSpectrograms.setShortcut("Ctrl+Shift+S")
        openMenu.addAction(self.loadConfigFile)
        openMenu.addAction(self.openLoggerFile)
        openMenu.addAction(self.openLoggerStats)
        openMenu.addAction(self.openSpectrograms)

        # View menu
        self.showControlScreen = QtWidgets.QAction("Control/Processing")
        self.showPlotScreen = QtWidgets.QAction("Plots")
        menuView.addAction(self.showControlScreen)
        menuView.addAction(self.showPlotScreen)

        # Process menu
        self.calcStats = QtWidgets.QAction("Calculate Statistics")
        self.calcStats.setShortcut("Ctrl+R")
        self.calcStats.setStatusTip("Run Control File (*.dat)")
        self.genScatterDiag = QtWidgets.QAction("Generate Seascatter Diagram")
        menuProcess.addAction(self.calcStats)
        menuProcess.addAction(self.genScatterDiag)

        # Applied logic menu
        self.filter = QtWidgets.QAction("Apply Low/High Pass Filter")
        self.spikeRemoval = QtWidgets.QAction("Spike Removal")
        menuLogic.addAction(self.filter)
        menuLogic.addAction(self.spikeRemoval)

        # Plot settings menu
        self.add2HIcon = QtWidgets.QAction("Add 2H Icon")
        self.add2HIcon.setCheckable(True)
        self.loggerPlotSettings = QtWidgets.QAction("Logger Plot Settings")
        self.loggerPlotSettings.setShortcut("Ctrl+S")
        self.spectPlotSettings = QtWidgets.QAction("Spectrogram Plot Settings")
        menuPlotSettings.addAction(self.add2HIcon)
        menuPlotSettings.addAction(self.loggerPlotSettings)
        menuPlotSettings.addAction(self.spectPlotSettings)

        # Export menu
        self.exportScatterDiag = QtWidgets.QAction("Export Seascatter Diagram")
        self.exportScatterDiag.setStatusTip("Export seascatter diagram to Excel")
        menuExport.addAction(self.exportScatterDiag)

        # Help menu
        self.showHelp = QtWidgets.QAction("Help")
        self.showAbout = QtWidgets.QAction("About")
        menuAbout.addAction(self.showHelp)
        menuAbout.addAction(self.showAbout)

    def tool_bar(self):
        """Create toolbar with button to show dashboards."""

        self.toolBar = self.addToolBar("Modules")
        self.toolBar.setStyleSheet("QToolBar{spacing:5px}")

        self.projConfigButton = QtWidgets.QPushButton("Project Config")
        self.rawDataButton = QtWidgets.QPushButton("Raw Data")
        self.dataQualityButton = QtWidgets.QPushButton("Data Quality Report")
        self.statsScreeningButton = QtWidgets.QPushButton("Statistics Screening")
        self.spectralScreeningButton = QtWidgets.QPushButton("Spectral Screening")
        self.seascatterButton = QtWidgets.QPushButton("Seascatter Diagram")
        self.transFuncsButton = QtWidgets.QPushButton("Transfer Functions")
        self.fatigueButton = QtWidgets.QPushButton("Fatigue Analysis")

        self.toolBar.addWidget(QtWidgets.QLabel("Modules:"))
        self.toolBar.addWidget(self.projConfigButton)
        self.toolBar.addWidget(self.rawDataButton)
        self.toolBar.addWidget(self.dataQualityButton)
        self.toolBar.addWidget(self.statsScreeningButton)
        self.toolBar.addWidget(self.spectralScreeningButton)
        self.toolBar.addWidget(self.seascatterButton)
        self.toolBar.addWidget(self.transFuncsButton)
        self.toolBar.addWidget(self.fatigueButton)


# class QtDesignerGui(QtWidgets.QMainWindow, datalab_gui_layout.Ui_MainWindow):
#     def __init__(self):
#         super().__init__()
#
#         self.setupUi(self)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # win = QtDesignerGui()
    win = DataLabGui()
    win.show()
    sys.exit(app.exec_())