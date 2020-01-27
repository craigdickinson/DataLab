"""Main DataLab gui hub."""

__author__ = "Craig Dickinson"

import sys

from PyQt5 import QtWidgets

from views.data_screening_view import DataQualityReport
from views.fatigue_view import FatigueDashboard
from views.input_data_view import InputDataModule
from views.histograms_view import HistogramDashboard
from views.raw_data_view import RawDataDashboard
from views.seascatter_view import SeascatterDiagram
from views.spectral_view import SpectrogramWidget
from views.stats_view import PlotStyle2H, StatsWidget, VesselStatsWidget
from views.transfer_functions_view import TransferFunctionsWidget


class DataLabGui(QtWidgets.QMainWindow):
    """Class to create DataLab ui widgets and layout."""

    def __init__(self):
        super().__init__()

        # TODO: Consider initialising data objects (control, tf, etc) here in the program root
        #  instead of declaring in subclasses to prevent mixed forward/backwards object mapping
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

        # Input data module
        self.inputDataModule = InputDataModule(self)

        # Raw data inspection module
        self.rawDataModule = RawDataDashboard(self)

        # Data quality screening report module
        self.dataQualityModule = DataQualityReport(self)

        # Stats screening module
        self.statsScreeningModule = QtWidgets.QTabWidget()
        self.statsTab = StatsWidget(self)
        self.vesselStatsTab = VesselStatsWidget(self)
        # self.pairplotTab = PairPlotView(self)
        self.statsScreeningModule.addTab(self.statsTab, "Statistics")
        self.statsScreeningModule.addTab(self.vesselStatsTab, "Vessel Statistics")
        # self.statsScreeningModule.addTab(self.pairplotTab, "Pair-Plot")

        # Spectral screening module
        self.spectralScreeningModule = QtWidgets.QTabWidget()
        self.spectrogramTab = SpectrogramWidget(self)
        self.spectralScreeningModule.addTab(self.spectrogramTab, "Spectrograms")

        # Seascatter diagram module
        self.seascatterModule = SeascatterDiagram(self)

        # Transfer functions module
        self.transFuncsModule = QtWidgets.QTabWidget()
        self.transFuncsTab = TransferFunctionsWidget(self)
        self.transFuncsModule.addTab(self.transFuncsTab, "2HFATLASA Transfer Functions")

        # Fatigue processing module
        self.fatigueModule = QtWidgets.QTabWidget()
        self.histogramsTab = HistogramDashboard(self)
        self.fatigueTab = FatigueDashboard(self)
        self.fatigueModule.addTab(self.histogramsTab, "Rainflow Counting Histograms")
        self.fatigueModule.addTab(self.fatigueTab, "2HFATLASA")

        # Add stacked widgets
        self.modulesWidget.addWidget(self.inputDataModule)
        self.modulesWidget.addWidget(self.rawDataModule)
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

        # Menus
        self.menuFile = menubar.addMenu("&File")
        # self.menuView = menubar.addMenu("&View")
        self.menuProcess = menubar.addMenu("&Process")
        # self.menuLogic = menubar.addMenu("&Applied Logic")
        self.menuPlotSettings = menubar.addMenu("Plot &Settings")
        self.menuExport = menubar.addMenu("&Export")
        self.menuAzure = menubar.addMenu("&Azure")
        self.menuHelp = menubar.addMenu("&Help")

        # File menu actions
        self.openConfigAction = QtWidgets.QAction("Open Config File...")
        self.openConfigAction.setShortcut("Ctrl+O")
        self.saveConfigAction = QtWidgets.QAction("Save Config File")
        self.saveConfigAction.setShortcut("Ctrl+S")
        self.openLoggerFileAction = QtWidgets.QAction("Open Logger File...")
        self.openLoggerFileAction.setShortcut("F2")
        self.openStatsAction = QtWidgets.QAction("Open Logger Stats...")
        self.openStatsAction.setShortcut("F3")
        self.openSpectrogramsAction = QtWidgets.QAction("Open Logger Spectrograms...")
        self.openSpectrogramsAction.setShortcut("F4")
        self.openSeascatterAction = QtWidgets.QAction("Open Transfer Functions...")
        self.openSeascatterAction.setShortcut("F5")
        self.menuFile.addAction(self.openConfigAction)
        self.menuFile.addAction(self.saveConfigAction)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.openLoggerFileAction)
        self.menuFile.addAction(self.openStatsAction)
        self.menuFile.addAction(self.openSpectrogramsAction)

        # View menu actions
        # self.showPlotScreen = QtWidgets.QAction("Plots")
        # self.menuView.addAction(self.showPlotScreen)

        # Process menu actions
        self.processScreeningAction = QtWidgets.QAction("Process Screening")
        self.processScreeningAction.setShortcut("F6")
        self.calcSeascatterAction = QtWidgets.QAction("Create Seascatter")
        self.calcSeascatterAction.setShortcut("F7")
        self.calcTFAction = QtWidgets.QAction("Calculate Transfer Functions")
        self.calcTFAction.setShortcut("F8")
        self.calcFatigueAction = QtWidgets.QAction("Calculate Fatigue")
        self.calcFatigueAction.setShortcut("F9")
        self.menuProcess.addAction(self.processScreeningAction)
        self.menuProcess.addAction(self.calcSeascatterAction)
        self.menuProcess.addAction(self.calcTFAction)
        self.menuProcess.addAction(self.calcFatigueAction)

        # Applied logic menu actions
        # self.filter = QtWidgets.QAction("Apply Low/High Pass Filter")
        # self.spikeRemoval = QtWidgets.QAction("Spike Removal")
        # menuLogic.addAction(self.filter)
        # menuLogic.addAction(self.spikeRemoval)

        # Plot settings menu actions
        # self.add2HIcon = QtWidgets.QAction("Add 2H Icon")
        # self.add2HIcon.setCheckable(True)
        self.loggerPlotSettingsAction = QtWidgets.QAction("Logger Plot Settings...")
        self.loggerPlotSettingsAction.setShortcut("Alt+1")
        self.spectPlotSettingsAction = QtWidgets.QAction("Spectrogram Plot Settings...")
        self.spectPlotSettingsAction.setShortcut("Alt+3")
        # self.menuPlotSettings.addAction(self.add2HIcon)
        self.menuPlotSettings.addAction(self.loggerPlotSettingsAction)
        self.menuPlotSettings.addAction(self.spectPlotSettingsAction)

        # Export menu actions
        self.exportScatterDiagAction = QtWidgets.QAction("Export Sea Scatter Diagram")
        self.exportScatterDiagAction.setStatusTip("Export sea scatter diagram to Excel")
        self.menuExport.addAction(self.exportScatterDiagAction)

        # Azure menu actions
        self.azureSettingsAction = QtWidgets.QAction("Azure Cloud Storage Account Settings")
        self.menuAzure.addAction(self.azureSettingsAction)

        # Help menu actions
        self.helpAction = QtWidgets.QAction("DataLab Guidance")
        self.helpAction.setShortcut("F1")
        self.aboutAction = QtWidgets.QAction("&About")
        self.menuHelp.addAction(self.helpAction)
        self.menuHelp.addAction(self.aboutAction)

    def _tool_bar(self):
        """Create toolbar with button to show dashboards."""

        self.toolBar = self.addToolBar("Modules")
        self.toolBar.setStyleSheet("QToolBar{spacing:5px}")

        self.projConfigButton = QtWidgets.QPushButton("1. Input Data")
        self.projConfigButton.setShortcut("Ctrl+1")
        self.rawDataButton = QtWidgets.QPushButton("2. Inspect Raw Data")
        self.rawDataButton.setShortcut("Ctrl+2")
        self.dataQualityButton = QtWidgets.QPushButton("3. Data Quality Screening")
        self.dataQualityButton.setShortcut("Ctrl+3")
        self.statsScreeningButton = QtWidgets.QPushButton("4. Statistics Screening")
        self.statsScreeningButton.setShortcut("Ctrl+4")
        self.spectralScreeningButton = QtWidgets.QPushButton("5. Spectral Screening")
        self.spectralScreeningButton.setShortcut("Ctrl+5")
        self.seascatterButton = QtWidgets.QPushButton("6. Sea Scatter")
        self.seascatterButton.setShortcut("Ctrl+6")
        self.transFuncsButton = QtWidgets.QPushButton("7. Transfer Functions")
        self.transFuncsButton.setShortcut("Ctrl+7")
        self.fatigueButton = QtWidgets.QPushButton("8. Fatigue Analysis")
        self.fatigueButton.setShortcut("Ctrl+8")

        self.toolBar.addWidget(QtWidgets.QLabel("Dashboards:"))
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
