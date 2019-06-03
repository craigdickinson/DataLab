__author__ = "Craig Dickinson"
__program__ = "DataLab"
__version__ = "0.31"
__date__ = "3 June 2019"

import logging
import os
import sys
from datetime import timedelta
from glob import glob
from time import time

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot

# import datalab_gui_layout
from core.control_file import InputError
from core.datalab_main import DataLab
from core.logger_properties import LoggerError
from core.read_files import (
    read_spectrograms_csv,
    read_spectrograms_excel,
    read_spectrograms_hdf5,
    read_stats_csv,
    read_stats_excel,
    read_stats_hdf5,
)
from core.read_files import read_wcfat_results
from views.stats_view import StatsDataset
from views.main_window_view import DataLabGui


class DataLabApp(DataLabGui):
    """Main class for DataLab program. Takes as arg the ui class."""

    def __init__(self):
        super().__init__()

        self.version = __version__
        self.setWindowTitle(f"DataLab {self.version}")

        # Set root path because path is changed when using file tree
        self.root = os.getcwd()
        self.datalab = None

        self.update_tool_buttons("config")
        self.connect_signals()
        self.connect_child_signals()

    def connect_signals(self):
        """Connect widget signals to methods/actions."""

        # File menu
        self.loadConfigFile.triggered.connect(self.projConfigModule.load_config_file)
        self.openLoggerFile.triggered.connect(self.load_logger_file)
        self.openLoggerStats.triggered.connect(self.load_stats_file_from_file_menu)
        self.openSpectrograms.triggered.connect(self.load_spectrograms_file)

        # View menu
        self.showPlotScreen.triggered.connect(self.view_mod_stats_screening)

        # Process menu
        # self.calcStats.triggered.connect(self.process_control_file)
        self.genScatterDiag.triggered.connect(self.gen_scatter_diag)

        # Plot menu
        self.add2HIcon.triggered.connect(self.add_2h_icon)
        self.loggerPlotSettings.triggered.connect(self.open_logger_plot_settings)
        self.spectPlotSettings.triggered.connect(self.open_spect_plot_settings)

        # Export menu
        self.exportScatterDiag.triggered.connect(self.save_scatter_diagram)

        # Help menu
        self.showHelp.triggered.connect(self.show_help)
        self.showAbout.triggered.connect(self.show_about)

        # Toolbar dashboard buttons
        self.projConfigButton.clicked.connect(self.view_proj_config_mod)
        self.rawDataButton.clicked.connect(self.view_mod_raw_data)
        self.dataQualityButton.clicked.connect(self.view_mod_data_quality)
        self.statsScreeningButton.clicked.connect(self.view_mod_stats_screening)
        self.spectralScreeningButton.clicked.connect(self.view_mod_spectral_screening)
        self.seascatterButton.clicked.connect(self.view_mod_seascatter)
        self.transFuncsButton.clicked.connect(self.view_mod_transfer_funcs)
        self.fatigueButton.clicked.connect(self.view_mod_fatigue)

    def connect_child_signals(self):
        self.timeSeriesTab.loadFileButton.clicked.connect(self.load_logger_file)
        self.statsTab.loadStatsButton.clicked.connect(self.load_stats_file)
        self.vesselStatsTab.loadStatsButton.clicked.connect(self.load_stats_file)
        self.spectrogramTab.loadDatasetButton.clicked.connect(self.load_spectrograms_file)
        self.fatigueTab.loadWCFATFileButton.clicked.connect(self.load_wcfat_results_file)

    def message_information(self, title, message, buttons=QtWidgets.QMessageBox.Ok):
        return QtWidgets.QMessageBox.information(self, title, message, buttons)

    def message_warning(self, title, message, buttons=QtWidgets.QMessageBox.Ok):
        return QtWidgets.QMessageBox.warning(self, title, message, buttons)

    def message_critical(self, title, message, buttons=QtWidgets.QMessageBox.Ok):
        return QtWidgets.QMessageBox.critical(self, title, message, buttons)

    @pyqtSlot(str)
    def error(self, message):
        print(f"Error: {message}")
        self.message_warning("Error", message)

    def warning(self, message):
        print(f"Warning: {message}")
        self.message_information("Warning", message)

    def load_logger_file(self):
        """Load raw logger time series file."""

        self.ts_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, caption="Open Logger File", filter="Logger Files (*.csv;*.acc;*.h5)"
        )

        if self.ts_file:
            fpath = "/".join(self.ts_file.split("/")[:-1])
            filename = self.ts_file.split("/")[-1]
            ext = filename.split(".")[-1]
            os.chdir(fpath)
            files_list = glob("*." + ext)

            try:
                # Populate files list widget and read file
                self.timeSeriesTab.update_files_list(files_list, filename)
                self.timeSeriesTab.load_file(filename)
            except FileNotFoundError as e:
                self.error(str(e))
            except ValueError as e:
                self.error(str(e))
            except Exception as e:
                msg = "Unexpected error processing loggers"
                self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
                logging.exception(msg)

            self.view_mod_raw_data()

    def load_stats_file_from_file_menu(self):
        """Load stats file when actioned from file menu."""

        self.load_stats_file(src="logger_stats")

    def load_stats_file(self, src=None):
        """Load summary stats file."""
        try:
            # Prompt user to select file with open file dialog
            stats_file, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                caption="Open Logger Statistics File",
                filter="Logger Statistics Files (*.h5 *.csv *.xlsx)",
            )

            if stats_file:
                # Get file extension
                ext = stats_file.split(".")[-1]

                # Read spreadsheet to data frame
                # TODO: Check that file read is valid
                if ext == "h5":
                    dict_stats = read_stats_hdf5(stats_file)
                elif ext == "csv":
                    dict_stats = read_stats_csv(stats_file)
                elif ext == "xlsx":
                    dict_stats = read_stats_excel(stats_file)

                # Set update plot flag so that plot is not updated if datasets dictionary already contains data
                # (i.e. a plot already exists)
                if self.statsTab.datasets:
                    plot_flag = False
                else:
                    plot_flag = True

                # For each logger create a stats dataset object containing data, logger id, list of channels and
                # pri/sec plot flags and add to stats plot class
                for logger, df in dict_stats.items():
                    dataset = StatsDataset(logger_id=logger, df=df)
                    self.statsTab.datasets.append(dataset)
                    self.vesselStatsTab.datasets.append(dataset)

                # Store dataset/logger names from dictionary keys
                dataset_ids = list(dict_stats.keys())
                self.statsTab.update_datasets_list(dataset_ids)
                self.vesselStatsTab.update_stats_datasets_list(dataset_ids)

                # Plot stats
                if plot_flag:
                    # Select preset logger and channel index if no dataset previously exist and plot stats
                    self.statsTab.set_preset_logger_and_channel()
                    self.statsTab.update_plot()

                    self.vesselStatsTab.set_plot_data(init=True)
                    self.vesselStatsTab.update_plots()

                # Show dashboard
                if src == "logger_stats":
                    self.view_tab_stats()
        except Exception as e:
            msg = "Unexpected error loading stats file"
            self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def load_spectrograms_file(self):
        """Load spectrograms spreadsheet."""

        spect_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption="Open Spectrogram File",
            filter="Spectrogram Files (*.h5 *.csv *.xlsx)",
        )

        if spect_file:
            # Get file extension
            ext = spect_file.split(".")[-1]

            # Read spreadsheet to data frame
            # TODO: Check that file read is valid
            if ext == "h5":
                logger, df = read_spectrograms_hdf5(spect_file)
            elif ext == "csv":
                logger, df = read_spectrograms_csv(spect_file)
            elif ext == "xlsx":
                logger, df = read_spectrograms_excel(spect_file)

            # Store spectrogram datasets and update plot tab
            self.spectrogramTab.datasets[logger] = df
            self.spectrogramTab.update_spect_datasets_list(logger)

            # Show dashboard
            self.view_tab_spectrogram()

    def load_wcfat_results_file(self):
        """Load 2HWCFAT .dmg file."""

        dmg_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption="Open 2HWCFAT Fatigue Damage File",
            filter="2HWCFAT Damage Files (*.dmg)",
        )

        if dmg_file:
            df_dam = read_wcfat_results(dmg_file)
            self.fatigueTab.process_fatigue_damage_file(df_dam)

    def open_logger_plot_settings(self):
        """Show raw data plot settings window."""

        # Set current parameters from time series plot widget class
        self.timeSeriesTab.plotSettings.get_params()
        self.timeSeriesTab.plotSettings.show()

    def open_spect_plot_settings(self):
        """Show spectrogram plot settings window."""

        # Set current parameters from spectrogram plot widget class
        self.spectrogramTab.plotSettings.get_params()
        self.spectrogramTab.plotSettings.show()

    def add_2h_icon(self):
        if self.add2HIcon.isChecked():
            title = {
                "title1": "21239 Total WoS",
                "title2": "Glendronach Well Monitoring Campaign",
                "title3": "Mean",
            }
            self.plot_2h.format_2h_style(**title)
            self.plot_2h.add_2H_icon()
        else:
            self.plot_2h.remove_2H_icon()

    def show_about(self):
        """Show program version info message box."""

        msg = f"Program: {__program__}\nVersion: {__version__}\nDate: {__date__}"
        self.message_information("About", msg)

    def show_help(self):
        """Show program overview and instructions message box."""

        msg = f"Instructions for using {__program__}:\n\n"
        self.message_information("Help", msg)

    def show_error_msg(self, msg):
        self.errorBar.setAutoFillBackground(True)
        self.errorBar.setStyleSheet("background:rgba(255,255,0,255)")
        self.errorLabel.setText(msg)
        self.errorBar.show()

    def clear_error_msg(self):
        self.errorLabel.setStyleSheet("background:rgba(0,0,0,0)")
        self.errorLabel.setText("")
        self.errorBar.hide()

    def view_proj_config_mod(self):
        self.update_tool_buttons("config")
        self.modulesWidget.setCurrentWidget(self.projConfigModule)

    def view_mod_raw_data(self):
        self.update_tool_buttons("raw")
        self.modulesWidget.setCurrentWidget(self.rawDataModule)

    def view_mod_data_quality(self):
        self.update_tool_buttons("quality")
        self.modulesWidget.setCurrentWidget(self.dataQualityModule)

    def view_mod_stats_screening(self):
        self.update_tool_buttons("stats")
        self.modulesWidget.setCurrentWidget(self.statsScreeningModule)

    def view_mod_spectral_screening(self):
        self.update_tool_buttons("spectral")
        self.modulesWidget.setCurrentWidget(self.spectralScreeningModule)

    def view_mod_seascatter(self):
        self.update_tool_buttons("seascatter")
        self.modulesWidget.setCurrentWidget(self.seascatterModule)

    def view_mod_transfer_funcs(self):
        self.update_tool_buttons("tf")
        self.modulesWidget.setCurrentWidget(self.transFuncsModule)

    def view_mod_fatigue(self):
        self.update_tool_buttons("fatigue")
        self.modulesWidget.setCurrentWidget(self.fatigueModule)

    def view_tab_stats(self):
        self.update_tool_buttons("stats")
        self.modulesWidget.setCurrentWidget(self.statsScreeningModule)
        self.statsScreeningModule.setCurrentWidget(self.statsTab)

    def view_tab_vessel_stats(self):
        self.update_tool_buttons("stats")
        self.modulesWidget.setCurrentWidget(self.statsScreeningModule)
        self.statsScreeningModule.setCurrentWidget(self.vesselStatsTab)

    def view_tab_spectrogram(self):
        self.update_tool_buttons("spectral")
        self.modulesWidget.setCurrentWidget(self.spectralScreeningModule)
        self.statsScreeningModule.setCurrentWidget(self.spectrogramTab)

    def view_tab_seascatter(self):
        self.update_tool_buttons("seascatter")
        self.modulesWidget.setCurrentWidget(self.seascatterModule)

    def update_tool_buttons(self, active_button):
        """Format selected module button."""

        # button_style = 'font-weight: bold'
        active_style = "background-color: blue; color: white"
        inactive_style = "background-color: none; color: none"

        # Reset all button colours
        self.projConfigButton.setStyleSheet(inactive_style)
        self.rawDataButton.setStyleSheet(inactive_style)
        self.dataQualityButton.setStyleSheet(inactive_style)
        self.statsScreeningButton.setStyleSheet(inactive_style)
        self.spectralScreeningButton.setStyleSheet(inactive_style)
        self.seascatterButton.setStyleSheet(inactive_style)
        self.transFuncsButton.setStyleSheet(inactive_style)
        self.fatigueButton.setStyleSheet(inactive_style)

        # Colour active dashboard button
        if active_button == "config":
            self.projConfigButton.setStyleSheet(active_style)
        if active_button == "raw":
            self.rawDataButton.setStyleSheet(active_style)
        if active_button == "quality":
            self.dataQualityButton.setStyleSheet(active_style)
        if active_button == "stats":
            self.statsScreeningButton.setStyleSheet(active_style)
        if active_button == "spectral":
            self.spectralScreeningButton.setStyleSheet(active_style)
        if active_button == "seascatter":
            self.seascatterButton.setStyleSheet(active_style)
        if active_button == "tf":
            self.transFuncsButton.setStyleSheet(active_style)
        if active_button == "fatigue":
            self.fatigueButton.setStyleSheet(active_style)

    def centre(self):
        """Centres window on screen (not sure if works correctly)."""

        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def analyse_config_setup(self, control):
        """Run statistical and spectral analysis in config setup."""

        # Check at least one logger exists
        if not control.loggers:
            self.warning("No loggers exist in setup")
            return

        # First get all raw data filenames for all loggers to be processed and perform some screening checks
        try:
            # Check all ids are unique
            control.check_logger_ids(control.logger_ids)

            # Create output folder if necessary
            control.ensure_dir_exists(control.output_folder)

            # Get raw filenames, check timestamps and select files in processing datetime range
            for logger in control.loggers:
                logger.process_filenames()
                logger.select_files_in_datetime_range(
                    logger.stats_start, logger.stats_end
                )
                logger.expected_data_points = logger.freq * logger.duration

                # Get all channel names and units if not already stored in logger object
                if (
                        len(logger.all_channel_names) == 0
                        and len(logger.all_channel_units) == 0
                ):
                    logger.get_all_channel_and_unit_names()

                # Check requested channels exist
                if logger.process_stats is True or logger.process_spectral is True:
                    channels, units = logger.check_requested_columns_exist()
                    logger.channel_names = channels
                    logger.channel_units = units

                # Make any user defined units and channels override any detected
                logger.user_header_override()

                # Check headers length match number of columns
                logger.check_headers()
        except InputError as e:
            return self.error(str(e))
        except LoggerError as e:
            return self.error(str(e))
        except Exception as e:
            msg = "Unexpected error on preparing config setup"
            self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            return logging.exception(msg)

        self.run_analysis(control)

    def run_analysis(self, control):
        """Run statistical and spectral analysis in config setup."""

        # Run processing on QThread worker - prevents GUI lock up
        try:
            # Create datalab object, map control data and process
            datalab = DataLab(no_dat=True)
            datalab.control = control

            # Create worker thread, connect signals to methods in this class and start, which this calls worker.run()
            self.worker = ControlFileWorker(datalab, parent=self)
            self.worker.signal_datalab.connect(self.set_datalab_output_to_gui)
            self.worker.signal_error.connect(self.error)
            self.worker.start()
        except Exception as e:
            msg = "Unexpected error on processing config setup"
            self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(msg)

    def set_datalab_output_to_gui(self, datalab):
        """Map results from statistical analysis to the GUI."""

        # Store datalab object and update data quality report module
        self.datalab = datalab
        self.dataQualityModule.datalab = datalab
        self.dataQualityModule.set_data_quality_results()

        # Clear any existing stats tab datasets
        self.statsTab.reset_dashboard()

        # For each logger create stats dataset object containing data, logger id, list of channels and
        # pri/sec plot flags and add to stats plot class
        for logger, df in datalab.dict_stats.items():
            dataset = StatsDataset(logger_id=logger, df=df)
            self.statsTab.datasets.append(dataset)

        # Store dataset/logger names from dictionary keys
        dataset_ids = list(datalab.dict_stats.keys())
        self.statsTab.update_datasets_list(dataset_ids)

        # Plot stats
        # self.parent.statsTab.set_plot_data(init=True)
        # self.parent.statsTab.filtered_ts = self.parent.statsTab.calc_filtered_data(self.df_plot)
        self.statsTab.update_plot()

        # TODO: Load and plot spectrograms data
        # Store spectrogram datasets and update plot tab
        # self.parent.spectrogramTab.datasets[logger] = df
        # self.parent.spectrogramTab.update_spect_datasets_list(logger)

    def gen_scatter_diag(self):
        """Create seascatter diagram if vessel stats data is loaded."""

        df_vessel = self.check_vessel_dataset_loaded(datasets=self.statsTab.datasets)

        if df_vessel is False:
            msg = (
                "No vessel statistics dataset found in memory.\n"
                "Load a statistics file containing vessel data and try again."
            )
            self.warning(msg)
        else:
            try:
                self.seascatterModule.get_seascatter_dataset(df_vessel)
            except Exception as e:
                msg = "Unexpected error generating seascatter diagram"
                self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
                logging.exception(msg)

        self.view_tab_seascatter()

    def check_vessel_dataset_loaded(self, datasets):
        """
        Check whether a vessel stats file has been loaded.
        This dataset will be titled "VESSEL".
        If found return dataset, otherwise false.
        """

        for dataset in datasets:
            if dataset.logger_id == "VESSEL":
                return dataset.df
        return False

    def save_scatter_diagram(self):
        """Export seascatter diagram to Excel."""

        if self.seascatterModule.df_scatter.empty:
            self.warning("No seascatter diagram generated. Nothing to export!")
        else:
            fname, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save Seascatter Diagram", filter="Excel Files (*.xlsx)"
            )
            if fname:
                self.seascatterModule.export_scatter_diagram(fname)


class ControlFileWorker(QtCore.QThread):
    """Worker class to process control file in separate thread."""

    # Note: Using the alternative method of creating a QObject and a standalone QThread worker and using moveToThread
    # does not work with GUIs. The QObject still stays on the QMainWindow thread. Therefore, while the processing works,
    # the GUI freezes up and doesn't show the progress bar updating.
    # Also, cannot pass parents to QObjects, which isn't ideal.
    signal_datalab = pyqtSignal(object)
    signal_error = pyqtSignal(str)
    signal_runtime = pyqtSignal(str)

    def __init__(self, datalab, parent=None):
        """Worker class to allow control file processing on a separate thread to the gui."""
        super(ControlFileWorker, self).__init__(parent)

        self.parent = parent

        # DataLab processing object
        self.datalab = datalab

        # Initialise progress bar
        self.pb = ControlFileProgressBar()
        self.connect_signals()

    def connect_signals(self):
        self.pb.signal_quit_worker.connect(self.quit_worker)
        self.datalab.signal_notify_progress.connect(self.pb.update_progress_bar)
        self.signal_runtime.connect(self.pb.report_runtime)

    def run(self):
        """Override of QThread's run method to process control file."""

        try:
            self.parent.setEnabled(False)
            t0 = time()

            # Run DataLab processing; compute and write requested logger statistics and spectrograms
            self.datalab.process_control_file()
            t = str(timedelta(seconds=round(time() - t0)))
            self.signal_runtime.emit(t)
            self.signal_datalab.emit(self.datalab)
        except ZeroDivisionError as e:
            self.signal_error.emit(str(e))
            logging.exception(e)
        except Exception as e:
            msg = "Unexpected error processing control file"
            self.signal_error.emit(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(msg)
        finally:
            self.parent.setEnabled(True)

    @pyqtSlot()
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

    signal_quit_worker = pyqtSignal()

    def __init__(self):
        super().__init__()

        # self.setFixedSize(400, 80)
        self.setFixedWidth(400)
        self.setWindowTitle("Processing Logger Statistics")
        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(self)
        self.progressBar = QtWidgets.QProgressBar(self)
        self.msgProcessingComplete = QtWidgets.QLabel(self)
        layout.addWidget(self.label)
        layout.addWidget(self.progressBar)
        layout.addWidget(self.msgProcessingComplete)

        self.buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.cancel)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        layout.addWidget(self.buttonBox)

        self.show()

    def cancel(self):
        """Cancel progress bar."""

        print("\nRun cancelled")
        self.signal_quit_worker.emit()

    @pyqtSlot(str, int, int, int, int, int)
    def update_progress_bar(
            self, logger, logger_i, file_i, n, file_num, total_num_files
    ):
        """Update progress bar window."""

        self.label.setText(
            f"Processing logger {logger}: file {file_i} of {total_num_files}"
        )

        perc = file_num / total_num_files * 100
        print(f"{file_num} {perc:.3f}%")
        self.progressBar.setValue(perc)
        if int(perc) == 100:
            self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)

    @pyqtSlot(str)
    def report_runtime(self, t):
        self.msgProcessingComplete.setText("Processing complete: elapsed time = " + t)


# class QtDesignerGui(QtWidgets.QMainWindow, datalab_gui_layout.Ui_MainWindow):
#     def __init__(self):
#         super().__init__()
#
#         self.setupUi(self)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # gui = QtDesignerGui()
    gui = DataLabApp()
    gui.show()
    sys.exit(app.exec_())
