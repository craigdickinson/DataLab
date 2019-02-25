__author__ = 'Craig Dickinson'
__program__ = 'DataLab'
__version__ = '0.4'
__date__ = '25 February 2019'

import logging
import os
import sys
from datetime import timedelta
from glob import glob
from time import time

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import pyqtSignal

from core.control_file import InputError
from core.datalab_main import DataLab
from core.read_files import (read_spectrograms_csv, read_spectrograms_excel, read_spectrograms_hdf5, read_stats_csv,
                             read_stats_excel, read_stats_hdf5)
from plot_stats import PlotStyle2H, SpectrogramWidget, StatsDataset, StatsWidget, VarianceWidget
from plot_time_series import PlotOptions, TimeSeriesPlotWidget
import datalab_gui_layout


class DataLabGui(QtWidgets.QMainWindow):
    """Class to create main gui."""

    # thread_status = pyqtSignal(bool)

    def __init__(self):
        super().__init__()

        # Set root path because path is changed when using file tree
        self.root = os.getcwd()
        self.datfile = None
        self.setWindowTitle('Monitoring Data Lab')
        self.init_ui()
        self.connect_signals()
        self.plotOptions = PlotOptions(self)
        # self._centre()

        # self.output_folder = r'C:\Users\dickinsc\PycharmProjects\DSPLab\output\Glenlivet G1G2'
        # self.summary_stats_file = 'dd10 Statistics.xlsx'

    def init_ui(self):
        """Initialise gui."""

        self.setGeometry(50, 50, 1400, 800)

        # Create stacked central widget
        self.modulesWidget = QtWidgets.QStackedWidget()
        self.w = QtWidgets.QTabWidget()
        # self.setCentralWidget(self.w)
        self.setCentralWidget(self.modulesWidget)
        # vbox = QtWidgets.QVBoxLayout(self.w)
        # vbox.addWidget(self.dashboardsWidget)
        self.statusBar()

        # Create menu bar and tool bar
        self.menu_bar()
        self.tool_bar()

        # Module views
        # Raw data inspection module
        self.rawDataModule = QtWidgets.QTabWidget()
        self.timeSeriesTab = TimeSeriesPlotWidget(self)
        self.rawDataModule.addTab(self.timeSeriesTab, 'Time Series')

        # Screening module container and tab widgets
        self.screeningModule = QtWidgets.QTabWidget()
        self.controlTab = self.control_widget()
        self.statsTab = StatsWidget()
        self.varianceTab = VarianceWidget()
        self.spectrogramTab = SpectrogramWidget()
        self.screeningModule.addTab(self.controlTab, 'Input')
        self.screeningModule.addTab(self.statsTab, 'Statistics')
        self.screeningModule.addTab(self.varianceTab, 'Variance Plot')
        self.screeningModule.addTab(self.spectrogramTab, 'Spectrograms')

        # Add stacked central widgets
        self.modulesWidget.addWidget(self.rawDataModule)
        self.modulesWidget.addWidget(self.screeningModule)

        # 2H plotting class
        self.plot_2h = PlotStyle2H(self.statsTab.canvas, self.statsTab.fig)

    def menu_bar(self):
        """Create menu bar."""

        # Menu bar
        menubar = self.menuBar()

        # Primary menus
        menuFile = menubar.addMenu('&File')
        menuView = menubar.addMenu('&View')
        menuProcess = menubar.addMenu('&Process')
        menuLogic = menubar.addMenu('&Applied Logic')
        menuPlot = menubar.addMenu('&Plot')
        menuExport = menubar.addMenu('&Export')
        menuAbout = menubar.addMenu('&Help')

        # File menu
        # Open submenu
        openMenu = menuFile.addMenu('&Open')
        self.openControlFile = QtWidgets.QAction('Control File')
        self.openControlFile.setShortcut('Ctrl+C')
        self.openControlFile.setStatusTip('Open control file (*.dat)')
        self.openLoggerFile = QtWidgets.QAction('Logger File')
        self.openLoggerFile.setShortcut('Ctrl+O')
        self.openLoggerStats = QtWidgets.QAction('Logger Stats')
        self.openLoggerStats.setShortcut('Ctrl+Shift+O')
        self.openSpectrograms = QtWidgets.QAction('Spectrograms')
        self.openSpectrograms.setShortcut('Ctrl+Shift+S')
        openMenu.addAction(self.openControlFile)
        openMenu.addAction(self.openLoggerFile)
        openMenu.addAction(self.openLoggerStats)
        openMenu.addAction(self.openSpectrograms)

        # Save control file
        self.saveControlFile = QtWidgets.QAction('Save Control File')
        # self.saveControlFile.setShortcut('Ctrl+Shift+S')
        self.saveControlFile.setStatusTip('Save control file (*.dat)')
        menuFile.addAction(self.saveControlFile)

        # Logger paths submenu
        loggerPathMenu = menuFile.addMenu('Set Logger File Paths')
        self.BOPPrimary = QtWidgets.QAction('BOP Primary')
        self.BOPBackup = QtWidgets.QAction('BOP Backup')
        self.LMRPPrimary = QtWidgets.QAction('LMRP Primary')
        self.LMRPBackup = QtWidgets.QAction('LMRP Backup')
        loggerPathMenu.addAction(self.BOPPrimary)
        loggerPathMenu.addAction(self.BOPBackup)
        loggerPathMenu.addAction(self.LMRPPrimary)
        loggerPathMenu.addAction(self.LMRPBackup)

        # View menu
        self.showControlScreen = QtWidgets.QAction('Control/Processing')
        self.showPlotScreen = QtWidgets.QAction('Plots')
        menuView.addAction(self.showControlScreen)
        menuView.addAction(self.showPlotScreen)

        # Process menu
        self.calcStats = QtWidgets.QAction('Calculate Statistics')
        self.calcStats.setShortcut('Ctrl+R')
        self.calcStats.setStatusTip('Run Control File (*.dat)')
        menuProcess.addAction(self.calcStats)

        # Applied logic menu
        self.filter = QtWidgets.QAction('Apply Low/High Pass Filter')
        self.spikeRemoval = QtWidgets.QAction('Spike Removal')
        menuLogic.addAction(self.filter)
        menuLogic.addAction(self.spikeRemoval)

        # Plot menu
        self.add2HIcon = QtWidgets.QAction('Add 2H Icon')
        self.add2HIcon.setCheckable(True)
        self.plotSettings = QtWidgets.QAction('Plot Settings')
        self.plotSettings.setShortcut('Ctrl+S')
        menuPlot.addAction(self.add2HIcon)
        menuPlot.addAction(self.plotSettings)

        # Help menu
        self.showHelp = QtWidgets.QAction('Help')
        self.showAbout = QtWidgets.QAction('About')
        menuAbout.addAction(self.showHelp)
        menuAbout.addAction(self.showAbout)

    def tool_bar(self):
        """Create toolbar with button to show dashboards."""

        self.toolBar = self.addToolBar('Modules')
        self.rawDataButton = QtWidgets.QPushButton('Raw Data Inspection')
        self.screeningButton = QtWidgets.QPushButton('Logger Screening')
        self.TFButton = QtWidgets.QPushButton('Transfer Functions')
        self.fatigueButton = QtWidgets.QPushButton('Fatigue Analysis')
        self.toolBar.addWidget(QtWidgets.QLabel('Dashboards:'))
        self.toolBar.addWidget(self.rawDataButton)
        self.toolBar.addWidget(self.screeningButton)
        self.toolBar.addWidget(self.TFButton)
        self.toolBar.addWidget(self.fatigueButton)

        self.update_tool_buttons('raw')
        # self.toolBar.setStyleSheet('QToolBar{spacing:3px;}')

    def control_widget(self):
        """Control/input widget."""

        controlScreen = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout()
        controlScreen.setLayout(grid)

        self.controls = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout()
        self.controls.setLayout(vbox)
        self.controls.setFixedHeight(150)

        # Widgets
        self.controlFileEdit = QtWidgets.QTextEdit()
        self.openDatFileButton = QtWidgets.QPushButton('Open Control File')
        self.analyseDatFileButton = QtWidgets.QPushButton('Analyse Control File')
        self.processStatsButton = QtWidgets.QPushButton('Process Stats')
        self.loadStatsButton = QtWidgets.QPushButton('Load Stats')

        vbox.addWidget(self.openDatFileButton, QtCore.Qt.AlignTop)
        vbox.addWidget(self.analyseDatFileButton, QtCore.Qt.AlignTop)
        vbox.addWidget(self.processStatsButton, QtCore.Qt.AlignTop)
        vbox.addWidget(self.loadStatsButton, QtCore.Qt.AlignTop)
        grid.addWidget(self.controls, 0, 0, QtCore.Qt.AlignTop)
        grid.addWidget(self.controlFileEdit, 0, 1)

        return controlScreen

    def message(self, title, message, buttons=QtWidgets.QMessageBox.Ok):
        return QtWidgets.QMessageBox.information(self, title, message, buttons)

    def error(self, message):
        print(f'Error: {message}')
        self.message('Error', message)

    def connect_signals(self):
        """Connect widget signals to methods/actions."""

        # File menu signals
        self.openLoggerFile.triggered.connect(self.load_logger_file)
        self.openControlFile.triggered.connect(self.open_control_file)
        self.saveControlFile.triggered.connect(self.save_control_file)
        self.openLoggerStats.triggered.connect(self.open_stats_file)
        self.openSpectrograms.triggered.connect(self.open_spectrograms_file)
        self.BOPPrimary.triggered.connect(self.set_directory)

        # View menu signals
        self.showControlScreen.triggered.connect(self.show_control_view)
        self.showPlotScreen.triggered.connect(self.show_screening_view)

        # Run menu signals
        self.calcStats.triggered.connect(self.process_control_file)

        # Plot menu signals
        self.add2HIcon.triggered.connect(self.add_2h_icon)
        self.plotSettings.triggered.connect(self.open_plot_options)

        # Help menu signals
        self.showHelp.triggered.connect(self.show_help)
        self.showAbout.triggered.connect(self.show_version)

        # Toolbar dashboard button signals
        self.rawDataButton.clicked.connect(self.show_raw_data_view)
        self.screeningButton.clicked.connect(self.show_screening_view)

        # Processing signals
        self.openDatFileButton.clicked.connect(self.open_control_file)
        self.analyseDatFileButton.clicked.connect(self.analyse_control_file)
        self.processStatsButton.clicked.connect(self.process_control_file)
        self.loadStatsButton.clicked.connect(self.open_stats_file)

    def open_control_file(self):
        """Open control file *.dat."""

        self.datfile, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Control File',
                                                                filter='Control Files (*.dat)')
        if self.datfile:
            self.show_control_view()

            with open(self.datfile, 'r') as f:
                text = f.read()
                self.controlFileEdit.setText(text)

    def load_logger_file(self):
        """Browse to open time series/logger file."""

        self.ts_file, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                                                                caption='Open Logger File',
                                                                filter='Logger Files (*.h5;*.csv)',
                                                                )
        if self.ts_file:
            fpath = '/'.join(self.ts_file.split('/')[:-1])
            filename = self.ts_file.split('/')[-1]
            ext = filename.split('.')[-1]
            os.chdir(fpath)
            files_list = glob('*.' + ext)

            try:
                # Populate files list widget and read file
                self.timeSeriesTab.update_files_list(files_list, filename)
                self.timeSeriesTab.load_file(filename)
            except FileNotFoundError as e:
                self.error(f'Error: {e}')
            except ValueError as e:
                self.error(f'Error: {e}')
            except Exception as e:
                msg = 'Unexpected error processing loggers'
                self.error(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
                logging.exception(msg)

            self.modulesWidget.setCurrentWidget(self.screeningModule)

    def open_plot_options(self):
        """Show logger file plot options window."""

        # Set current parameters from time series plot widget class
        self.plotOptions.get_params()
        self.plotOptions.show()

    def open_stats_file(self):
        """Open summary stats spreadsheet."""

        # Prompt user to select file with open file dialog
        stats_file, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                                                              caption='Open Logger Statistics File',
                                                              filter='Logger Statistics Files (*.h5 *.csv *.xlsx)')

        if stats_file:
            # Get file extension
            ext = stats_file.split('.')[-1]

            # Read spreadsheet to dataframe
            # TODO: Check that file read is valid
            if ext == 'h5':
                stats_dict = read_stats_hdf5(stats_file)
            elif ext == 'csv':
                stats_dict = read_stats_csv(stats_file)
            elif ext == 'xlsx':
                stats_dict = read_stats_excel(stats_file)

            # Set update plot flag so that plot is not updated if datasets dictionary already contains data
            # (i.e. a plot already exists)
            if self.statsTab.datasets:
                plot_flag = False
            else:
                plot_flag = True

            # For each logger create stats dataset object containing data, logger id, list of channels and
            # pri/sec plot flags and add to stats plot class
            for logger, df in stats_dict.items():
                dataset = StatsDataset(logger_id=logger, df=df)
                self.statsTab.datasets.append(dataset)

            # Store dataset/logger names from dictionary keys
            dataset_names = list(stats_dict.keys())
            self.statsTab.update_stats_datasets_list(dataset_names)

            # Plot stats
            if plot_flag:
                self.statsTab.update_plot()

            # Update variance plot tab - plot update is triggered upon setting dataset list index
            self.varianceTab.datasets = stats_dict
            self.varianceTab.update_variance_datasets_list(dataset_names)

            # Show dashboard
            self.show_stats_view()

    def open_spectrograms_file(self):
        """Open spectrograms spreadsheet."""

        spect_file, _ = QtWidgets.QFileDialog.getOpenFileName(self,
                                                              caption='Open Spectrogram File',
                                                              filter='Spectrogram Files (*.h5 *.csv *.xlsx)')

        if spect_file:
            # Get file extension
            ext = spect_file.split('.')[-1]

            # Read spreadsheet to dataframe
            # TODO: Check that file read is valid
            if ext == 'h5':
                logger, df = read_spectrograms_hdf5(spect_file)
            elif ext == 'csv':
                logger, df = read_spectrograms_csv(spect_file)
            elif ext == 'xlsx':
                logger, df = read_spectrograms_excel(spect_file)

            # Store spectrogram datasets and update plot tab
            self.spectrogramTab.datasets[logger] = df
            self.spectrogramTab.update_spect_datasets_list(logger)

            # Show dashboard
            self.show_spectrogram_view()

    # def update_logger_plot_settings(self):
    #     """Update time series and PSD plots with parameters from plot option window."""
    #
    #     ts_xmin = self.plot_options.ts_xmin
    #     ts_xmax = self.plot_options.ts_xmax
    #
    #     self.timeSeriesTab.adjust_axes_limits(ts_xmin, ts_xmax)

    def add_2h_icon(self):
        if self.add2HIcon.isChecked():
            title = {'title1': '21239 Total WoS',
                     'title2': 'Glendronach Well Monitoring Campaign',
                     'title3': 'Mean'}
            self.plot_2h.format_2h_style(**title)
            self.plot_2h.add_2H_icon()
        else:
            self.plot_2h.remove_2H_icon()

    def set_directory(self):
        """Set root path for logger files."""

        self.bop_p_path = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Directory')

    def save_control_file(self):
        """Save control file *.dat."""

        fname, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Control File', filter='Control Files (*.dat)')
        if fname:
            with open(fname, 'w') as f:
                text = self.controlFileEdit.toPlainText()
                f.write(text)

    def show_version(self):
        """Show program version info message box."""

        msgbox = QtWidgets.QMessageBox(self)
        msg = 'Program: ' + __program__ + '\n'
        msg += 'Version: ' + __version__ + '\n'
        msg += 'Date: ' + __date__ + '\n'
        msgbox.setText(msg)
        msgbox.setWindowTitle('About')
        msgbox.show()

    def show_help(self):
        """Show program overview and instructions message box."""

        msgbox = QtWidgets.QMessageBox(self)
        msg = 'Instructions for using ' + __program__ + ':\n\n'
        msgbox.setText(msg)
        msgbox.setWindowTitle('Help')
        msgbox.show()

    def show_error_msg(self, msg):
        self.errorBar.setAutoFillBackground(True)
        self.errorBar.setStyleSheet('background:rgba(255,255,0,255)')
        self.errorLabel.setText(msg)
        self.errorBar.show()

    def clear_error_msg(self):
        self.errorLabel.setStyleSheet('background:rgba(0,0,0,0)')
        self.errorLabel.setText('')
        self.errorBar.hide()

    def show_raw_data_view(self):
        self.update_tool_buttons('raw')
        self.modulesWidget.setCurrentWidget(self.rawDataModule)

    def show_control_view(self):
        self.update_tool_buttons('screening')
        self.modulesWidget.setCurrentWidget(self.screeningModule)
        self.screeningModule.setCurrentWidget(self.controlTab)

    def show_screening_view(self):
        self.update_tool_buttons('screening')
        self.modulesWidget.setCurrentWidget(self.screeningModule)

    def show_stats_view(self):
        self.update_tool_buttons('screening')
        self.modulesWidget.setCurrentWidget(self.screeningModule)
        self.screeningModule.setCurrentWidget(self.statsTab)

    def show_spectrogram_view(self):
        self.update_tool_buttons('screening')
        self.modulesWidget.setCurrentWidget(self.screeningModule)
        self.screeningModule.setCurrentWidget(self.spectrogramTab)

    def update_tool_buttons(self, active_button):
        # button_style = 'font-weight: bold'
        active_style = 'background-color: blue; color: white'
        inactive_style = 'background-color: none; color: none'

        # Reset all button colours
        self.rawDataButton.setStyleSheet(inactive_style)
        self.screeningButton.setStyleSheet(inactive_style)
        self.TFButton.setStyleSheet(inactive_style)
        self.fatigueButton.setStyleSheet(inactive_style)

        # Colour active dashboard button
        if active_button == 'raw':
            self.rawDataButton.setStyleSheet(active_style)
        if active_button == 'screening':
            self.screeningButton.setStyleSheet(active_style)
        if active_button == 'tf':
            self.TFButton.setStyleSheet(active_style)
        if active_button == 'fatigue':
            self.fatigueButton.setStyleSheet(active_style)

    def centre(self):
        """Centres window on screen (not sure if works correctly)."""

        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def analyse_control_file(self):
        """Read control file *.dat and check inputs."""

        os.chdir(self.root)

        # Inform user no dat file loaded
        if not self.datfile:
            self.statusBar().showMessage('Error: Load a control file (*.dat) first')
        else:
            try:
                # Create DataLab processing instance
                self.datalab = DataLab(self.datfile)
                self.datalab.analyse_control_file()
                self.statusBar().showMessage('Control file analysed successfully')
            except InputError as e:
                self.statusBar().showMessage('Error: ' + str(e))
                self.error('Error: ' + str(e))
                print(e)

    def process_control_file(self):
        """Run control file *.dat."""

        os.chdir(self.root)

        # Inform user no dat file loaded
        if not self.datfile:
            self.statusBar().showMessage('Error: Load a control file (*.dat) first')
        else:
            try:
                self.worker = ControlFileWorker(self)
            except InputError as e:
                self.error(f'Reading control file error: {e}')
            except Exception as e:
                msg = 'Unexpected error on processing control file'
                self.error(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
                logging.exception(msg)
            else:
                self.setEnabled(False)
                self.worker.start()
                self.worker.signal_error.connect(self.error)


class ControlFileWorker(QtCore.QThread):
    """Worker class to process control file in separate thread."""

    signal_status = pyqtSignal(bool)
    runtime = pyqtSignal(str)
    signal_error = pyqtSignal(str)

    def __init__(self, parent=None):
        """Worker class to allow control file processing on a separate thread to the gui."""
        super(ControlFileWorker, self).__init__(parent)

        # self.id = QtCore.QThread.currentThreadId()
        # print(self.id)
        self.parent = parent

        # DataLab processing object
        self.datalab = DataLab(self.parent.datfile)
        try:
            self.datalab.analyse_control_file()
        except:
            # Handle error in parent class
            raise

        # Initialise progress bar
        self.pb = ControlFileProgressBar()
        self.pb.quit_worker_signal.connect(self.quit_worker)
        self.datalab.notify_progress.connect(self.pb.update_progress_bar)
        self.runtime.connect(self.pb.report_runtime)

    def run(self):
        """Override of thread run method to process control file."""

        try:
            t0 = time()
            self.parent.statusBar().showMessage('')

            # Run DataLab processing; compute and write requested logger statistics and spectrograms
            self.datalab.process_control_file()

            # For each logger create stats dataset object containing data, logger id, list of channels and
            # pri/sec plot flags and add to stats plot class
            for logger, df in self.datalab.stats_dict.items():
                dataset = StatsDataset(logger_id=logger, df=df)
                self.parent.statsTab.datasets.append(dataset)

            # Store dataset/logger names from dictionary keys
            dataset_names = list(self.datalab.stats_dict.keys())
            self.parent.statsTab.update_stats_datasets_list(dataset_names)

            # Plot stats
            self.parent.statsTab.update_plot()

            # Update variance plot tab - plot update is triggered upon setting dataset list index
            self.parent.varianceTab.datasets = self.datalab.stats_dict
            self.parent.varianceTab.update_variance_datasets_list(dataset_names)
            self.parent.varianceTab.datasetList.setCurrentRow(0)
            self.parent.varianceTab.update_variance_plot(init_plot=True)
            self.parent.show_stats_view()
            t = str(timedelta(seconds=round(time() - t0)))
            self.runtime.emit(t)
        except Exception as e:
            msg = 'Unexpected error on processing control file'
            self.signal_error.emit(f'{msg}:\n{e}\n{sys.exc_info()[0]}')
        finally:
            self.parent.setEnabled(True)
            # self.quit()
            # self.wait()

    def quit_worker(self):
        """Quit thread on progress bar cancel button clicked."""

        if self.isRunning():
            # TODO: Should find a better way of doing this by setting an external flag
            self.terminate()
            self.wait()

        self.pb.close()
        self.parent.setEnabled(True)


class ControlFileProgressBar(QtWidgets.QDialog):
    """Progress bar window for processing control file."""

    quit_worker_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        # self.setFixedSize(400, 80)
        self.setFixedWidth(400)
        self.setWindowTitle('Processing Logger Statistics')
        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(self)
        self.progressBar = QtWidgets.QProgressBar(self)
        self.msgProcessingComplete = QtWidgets.QLabel(self)
        layout.addWidget(self.label)
        layout.addWidget(self.progressBar)
        layout.addWidget(self.msgProcessingComplete)

        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.cancel)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        layout.addWidget(self.buttonBox)

        self.show()

    def cancel(self):
        """Cancel progress bar."""

        print('\nStop!!!')
        self.quit_worker_signal.emit()

    def update_progress_bar(self, i, n):
        """Update progress bar window."""

        self.label.setText('Processing logger file ' + str(i) + ' of ' + str(n))

        p = (i / n) * 100
        self.progressBar.setValue(p)
        if int(p) == 100:
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        # self.close()

    def report_runtime(self, t):
        self.msgProcessingComplete.setText('Processing complete: elapsed time = ' + t)


class QtDesignerGui(QtWidgets.QMainWindow, datalab_gui_layout.Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.setupUi(self)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # gui = QtDesignerGui()
    gui = DataLabGui()
    debug = 0

    # Load initial file for debugging
    if debug == 1:
        direc = os.getcwd()
        direc = r'C:\Users\dickinsc\PycharmProjects\_2. DataLab Analysis Files'
        os.chdir(direc)
        filename = 'dd10_2017_0310_0000.csv'
        gui.timeSeriesTab.update_files_list([filename], filename)
        gui.timeSeriesTab.load_file(filename)
        gui.modulesWidget.setCurrentWidget(gui.screeningModule)

    gui.show()
    sys.exit(app.exec_())
