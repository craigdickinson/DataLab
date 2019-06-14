__author__ = "Craig Dickinson"

import sys

from PyQt5 import QtWidgets

from views.data_screening_view import DataQualityReport
from views.fatigue_view import FatigueProcessingWidget
from views.project_config_view import ConfigModule
from views.raw_data_view import RawDataDashboard
from views.seascatter_view import SeascatterDiagram
from views.spectral_view import SpectrogramWidget
from views.stats_view import PlotStyle2H, StatsWidget, VesselStatsWidget
from views.transfer_functions_view import TransferFunctionsWidget


class DataLabGui(QtWidgets.QMainWindow):
    """Class to create DataLab ui widgets and layout."""

    def __init__(self):
        super().__init__()

        self._init_ui()

    def _init_ui(self):
        """Initialise gui."""

        self.setGeometry(50, 50, 1400, 800)

        # Create stacked central widget
        self.modulesWidget = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.modulesWidget)
        self.statusbar = self.statusBar()

        # Create menu bar and tool bar
        self._menu_bar()
        self._tool_bar()

        # Raw data inspection module
        self.rawDataModule = QtWidgets.QTabWidget()
        self.rawDataTab = RawDataDashboard(self)
        self.rawDataModule.addTab(self.rawDataTab, "Time Series")

        # Project config module
        self.projConfigModule = ConfigModule(self)

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
        self.transFuncsTab = TransferFunctionsWidget(self)
        self.transFuncsModule.addTab(
            self.transFuncsTab, "2HFATLASA Transfer Functions"
        )

        # Fatigue processing module
        self.fatigueModule = QtWidgets.QTabWidget()
        self.fatigueTab = FatigueProcessingWidget(self)
        self.fatigueModule.addTab(self.fatigueTab, "2HFATLASA")

        # Add stacked widgets
        self.modulesWidget.addWidget(self.rawDataModule)
        self.modulesWidget.addWidget(self.projConfigModule)
        self.modulesWidget.addWidget(self.dataQualityModule)
        self.modulesWidget.addWidget(self.statsScreeningModule)
        self.modulesWidget.addWidget(self.spectralScreeningModule)
        self.modulesWidget.addWidget(self.seascatterModule)
        self.modulesWidget.addWidget(self.transFuncsModule)
        self.modulesWidget.addWidget(self.fatigueModule)

        # 2H plotting class
        self.plot_2h = PlotStyle2H(self.statsTab.canvas, self.statsTab.fig)

    def _menu_bar(self):
        """Create menu bar."""

        # Menu bar
        menubar = self.menuBar()

        # Primary menus
        menuFile = menubar.addMenu("&File")
        menuView = menubar.addMenu("&View")
        menuProcess = menubar.addMenu("&Process")
        # menuLogic = menubar.addMenu("&Applied Logic")
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
        # self.showControlScreen = QtWidgets.QAction("Control/Processing")
        self.showPlotScreen = QtWidgets.QAction("Plots")
        # menuView.addAction(self.showControlScreen)
        menuView.addAction(self.showPlotScreen)

        # Process menu
        self.calcStats = QtWidgets.QAction("Calculate Statistics")
        # self.calcStats.setShortcut("Ctrl+R")
        self.calcStats.setStatusTip("Run Control File (*.dat)")
        self.genScatterDiag = QtWidgets.QAction("Generate Seascatter Diagram")
        menuProcess.addAction(self.calcStats)
        menuProcess.addAction(self.genScatterDiag)

        # Applied logic menu
        # self.filter = QtWidgets.QAction("Apply Low/High Pass Filter")
        # self.spikeRemoval = QtWidgets.QAction("Spike Removal")
        # menuLogic.addAction(self.filter)
        # menuLogic.addAction(self.spikeRemoval)

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

    def _tool_bar(self):
        """Create toolbar with button to show dashboards."""

        self.toolBar = self.addToolBar("Modules")
        self.toolBar.setStyleSheet("QToolBar{spacing:5px}")

        self.rawDataButton = QtWidgets.QPushButton("0. Raw Data Screen")
        self.projConfigButton = QtWidgets.QPushButton("1. Project Config")
        self.dataQualityButton = QtWidgets.QPushButton("2. Data Quality Screening")
        self.statsScreeningButton = QtWidgets.QPushButton("3. Statistics Screening")
        self.spectralScreeningButton = QtWidgets.QPushButton("4. Spectral Screening")
        self.seascatterButton = QtWidgets.QPushButton("5. Seascatter")
        self.transFuncsButton = QtWidgets.QPushButton("6. Transfer Functions")
        self.fatigueButton = QtWidgets.QPushButton("7. Fatigue Analysis")

        self.toolBar.addWidget(QtWidgets.QLabel("Dashboards:"))
        self.toolBar.addWidget(self.rawDataButton)
        self.toolBar.addWidget(self.projConfigButton)
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
