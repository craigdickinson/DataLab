__author__ = "Craig Dickinson"
__program__ = "DataLab"
__version__ = "1.1.0.5"
__date__ = "22 July 2019"

import logging
import os
import sys
from datetime import timedelta
from glob import glob
from time import time
import webbrowser

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal, pyqtSlot

# import datalab_gui_layout
from app.core.control import InputError
from app.core.screening import Screening
from app.core.logger_properties import LoggerError
from app.core.read_files import (
    read_spectrograms_csv,
    read_spectrograms_excel,
    read_spectrograms_hdf5,
    read_stats_csv,
    read_stats_excel,
    read_stats_hdf5,
)
from app.core.read_files import read_wcfat_results
from app.views.main_window_view import DataLabGui
from app.views.processing_progress_view import ProcessingProgressBar
from app.views.stats_view import StatsDataset


# if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
#     QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
#
# if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
#     QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


class DataLab(DataLabGui):
    """Main class for DataLab program. Subclasses the ui class."""

    def __init__(self):
        super().__init__()

        self.version = __version__
        self.setWindowTitle(f"DataLab {self.version}")

        self.set_active_tool_button("config")
        self._connect_signals()
        self._connect_child_signals()
        self.view_proj_config_mod()

        # Dummy placeholder for Screening class (main processor)
        self.screening = None

        # Map settings objects (control, seascatter, transfer functions)
        self.control = self.projConfigModule.control
        self.scatter = self.projConfigModule.scatter
        self.tf = self.projConfigModule.tf

    def _connect_signals(self):
        """Connect widget signals to methods/actions."""

        # File menu
        self.openConfigAction.triggered.connect(
            self.projConfigModule.on_open_config_clicked
        )
        self.saveConfigAction.triggered.connect(
            self.projConfigModule.on_save_config_clicked
        )
        self.openLoggerFileAction.triggered.connect(self.on_open_logger_file)
        self.openStatsAction.triggered.connect(self.on_open_stats_file_triggered)
        self.openSpectrogramsAction.triggered.connect(self.on_open_spectrograms_file)

        # View menu
        # self.showPlotScreen.triggered.connect(self.view_mod_stats_screening)

        # Process menu
        self.processScreeningAction.triggered.connect(self.process_screening)
        self.calcSeascatterAction.triggered.connect(self.calc_seascatter)
        self.calcTFAction.triggered.connect(self.calc_transfer_functions)
        self.calcFatigueAction.triggered.connect(self.calc_fatigue)

        # Plot settings menu
        # self.add2HIcon.triggered.connect(self.add_2h_icon)
        self.loggerPlotSettingsAction.triggered.connect(self.open_logger_plot_settings)
        self.spectPlotSettingsAction.triggered.connect(self.open_spect_plot_settings)

        # Export menu
        self.exportScatterDiag.triggered.connect(
            self.on_export_scatter_diagram_triggered
        )

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
        self.transFuncsButton.clicked.connect(self.view_mod_transfer_functions)
        self.fatigueButton.clicked.connect(self.view_mod_fatigue)

    def _connect_child_signals(self):
        self.rawDataModule.openRawButton.clicked.connect(self.on_open_logger_file)
        self.statsTab.openStatsButton.clicked.connect(self.on_open_stats_file)
        self.vesselStatsTab.openStatsButton.clicked.connect(self.on_open_stats_file)
        self.spectrogramTab.openSpectButton.clicked.connect(
            self.on_open_spectrograms_file
        )

    def _message_information(self, title, message, buttons=QtWidgets.QMessageBox.Ok):
        return QtWidgets.QMessageBox.information(self, title, message, buttons)

    def _message_warning(self, title, message, buttons=QtWidgets.QMessageBox.Ok):
        return QtWidgets.QMessageBox.warning(self, title, message, buttons)

    def _message_critical(self, title, message, buttons=QtWidgets.QMessageBox.Ok):
        return QtWidgets.QMessageBox.critical(self, title, message, buttons)

    @pyqtSlot(str)
    def error(self, message):
        print(f"Error: {message}")
        self._message_warning("Error", message)

    @pyqtSlot(str)
    def warning(self, message):
        print(f"Warning: {message}")
        self._message_information("Warning", message)

    def show_about(self):
        """Show program version info message box."""

        msg = f"Program: {__program__}\nVersion: {__version__}\nDate: {__date__}"
        self._message_information("About", msg)

    def show_help(self):
        """Open instructions documentation on sharepoint url."""

        url = (
            r"https://agcloud.sharepoint.com/:p:/r/sites/"
            r"O365-UG-2HEngineeringSoftware/Shared%20Documents/2H%20Datalab/"
            r"2019-07-12%20How%20to%20Use%20DataLab.pptx?d=wcabe347939784784b8d7270cdf7938e7&csf=1&e=G0SRms"
        )
        webbrowser.open(url)

    def on_open_logger_file(self):
        """Load raw logger time series file."""

        self.ts_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, caption="Open Logger File", filter="Logger Files (*.csv;*.acc;*.h5)"
        )

        if self.ts_file:
            root = os.path.dirname(self.ts_file)
            self.rawDataModule.root = root
            filename = os.path.basename(self.ts_file)
            ext = os.path.splitext(self.ts_file)[1]
            files_list = glob(root + "/*" + ext)
            files = [os.path.basename(f) for f in files_list]

            try:
                # Populate files list widget and read file
                self.rawDataModule.update_files_list(files, filename)
                self.rawDataModule.load_file(self.ts_file)
            except FileNotFoundError as e:
                self.error(str(e))
                logging.exception(e)
            except ValueError as e:
                self.error(str(e))
                logging.exception(e)
            except Exception as e:
                msg = "Unexpected error processing loggers"
                self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
                logging.exception(e)

            self.view_mod_raw_data()

    def on_open_stats_file_triggered(self):
        """Open stats file when actioned from file menu."""

        self.on_open_stats_file(src="logger_stats")

    def on_open_stats_file(self, src=None):
        """Open stats file."""

        try:
            # Prompt user to select file with open file dialog
            stats_file, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                caption="Open Logger Statistics File",
                filter="Logger Statistics Files (*.h5;*.csv;*.xlsx)",
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

                # For each logger create a stats dataset object
                for logger_id, df in dict_stats.items():
                    dataset = StatsDataset(logger_id, df)
                    self.statsTab.datasets.append(dataset)
                    self.vesselStatsTab.datasets.append(dataset)
                    self.pairplotTab.datasets.append(dataset)

                # Store dataset/logger names from dictionary keys
                logger_ids = list(dict_stats.keys())
                self.statsTab.update_datasets_list(logger_ids)
                self.vesselStatsTab.update_stats_datasets_list(logger_ids)

                # Plot stats
                if plot_flag is True:
                    # Select preset logger and channel index if no dataset previously exist and plot stats tabs
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

    def on_open_spectrograms_file(self):
        """Open spectrograms file."""

        spect_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption="Open Spectrogram File",
            filter="Spectrogram Files (*.h5;*.csv;*.xlsx)",
        )

        if spect_file:
            # Get file extension
            ext = spect_file.split(".")[-1]

            # Read spreadsheet to data frame
            # TODO: Check that file read is valid
            if ext == "h5":
                dataset_id, df = read_spectrograms_hdf5(spect_file)
            elif ext == "csv":
                dataset_id, df = read_spectrograms_csv(spect_file)
            elif ext == "xlsx":
                dataset_id, df = read_spectrograms_excel(spect_file)

            # Store spectrogram datasets and update plot tab
            self.spectrogramTab.datasets[dataset_id] = df
            self.spectrogramTab.append_spect_to_datasets_list(dataset_id)
            self.spectrogramTab.create_plots()

            # Show dashboard
            self.view_tab_spectrogram()

    def open_wcfat_damage_file(self):
        """Open 2HWCFAT .dmg file."""

        dmg_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            caption="Open 2HWCFAT Fatigue Damage File",
            filter="2HWCFAT Damage Files (*.dmg)",
        )

        if dmg_file:
            df_dam = read_wcfat_results(dmg_file)
            self.fatigueTab.process_fatigue_damage_file(df_dam)

    def open_fatlasa_damage_file(self):
        return QtWidgets.QMessageBox.information(
            self, "To Do", "Feature coming in a future update."
        )

    def open_logger_plot_settings(self):
        """Show raw data plot settings window."""

        # Set current parameters from time series plot widget class
        self.rawDataModule.plotSettings.get_params()
        self.rawDataModule.plotSettings.show()

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

    # def show_error_msg(self, msg):
    #     self.errorBar.setAutoFillBackground(True)
    #     self.errorBar.setStyleSheet("background:rgba(255,255,0,255)")
    #     self.errorLabel.setText(msg)
    #     self.errorBar.show()

    # def clear_error_msg(self):
    #     self.errorLabel.setStyleSheet("background:rgba(0,0,0,0)")
    #     self.errorLabel.setText("")
    #     self.errorBar.hide()

    def view_mod_raw_data(self):
        self.set_active_tool_button("raw")
        self.modulesWidget.setCurrentWidget(self.rawDataModule)

    def view_proj_config_mod(self):
        self.set_active_tool_button("config")
        self.modulesWidget.setCurrentWidget(self.projConfigModule)

    def view_mod_data_quality(self):
        self.set_active_tool_button("quality")
        self.modulesWidget.setCurrentWidget(self.dataQualityModule)

    def view_mod_stats_screening(self):
        self.set_active_tool_button("stats")
        self.modulesWidget.setCurrentWidget(self.statsScreeningModule)

    def view_mod_spectral_screening(self):
        self.set_active_tool_button("spectral")
        self.modulesWidget.setCurrentWidget(self.spectralScreeningModule)

    def view_mod_seascatter(self):
        self.set_active_tool_button("seascatter")
        self.modulesWidget.setCurrentWidget(self.seascatterModule)

    def view_mod_transfer_functions(self):
        self.set_active_tool_button("tf")
        self.modulesWidget.setCurrentWidget(self.transFuncsModule)

    def view_mod_fatigue(self):
        self.set_active_tool_button("fatigue")
        self.modulesWidget.setCurrentWidget(self.fatigueModule)

    def view_tab_stats(self):
        self.set_active_tool_button("stats")
        self.modulesWidget.setCurrentWidget(self.statsScreeningModule)
        self.statsScreeningModule.setCurrentWidget(self.statsTab)

    def view_tab_vessel_stats(self):
        self.set_active_tool_button("stats")
        self.modulesWidget.setCurrentWidget(self.statsScreeningModule)
        self.statsScreeningModule.setCurrentWidget(self.vesselStatsTab)

    def view_tab_spectrogram(self):
        self.set_active_tool_button("spectral")
        self.modulesWidget.setCurrentWidget(self.spectralScreeningModule)
        self.statsScreeningModule.setCurrentWidget(self.spectrogramTab)

    def view_tab_seascatter(self):
        self.set_active_tool_button("seascatter")
        self.modulesWidget.setCurrentWidget(self.seascatterModule)

    def set_active_tool_button(self, active_button):
        """Format selected module button."""

        # button_style = 'font-weight: bold'
        # active_style = "background-color: blue; color: white"
        # active_style = "background-color: rgb(0,49,80); color: white"
        active_style = "background-color: rgb(0,112,192); color: white"
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

    def set_window_title(self, filename=None):
        """Update main window title with config filename."""

        if filename:
            self.setWindowTitle(f"DataLab {self.version} - Loaded Project: {filename}")
        else:
            self.setWindowTitle(f"DataLab {self.version}")

    def centre(self):
        """Centres window on screen (not sure if works correctly)."""

        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def process_screening(self):
        """Screen loggers and process statistical and spectral analysis."""

        try:
            status = self.analyse_screening_setup()
            if status is True:
                self.run_screening()
        except InputError as e:
            self.error(str(e))
            return logging.exception(e)
        except LoggerError as e:
            self.error(str(e))
            return logging.exception(e)
        except FileNotFoundError as e:
            self.error(str(e))
            return logging.exception(e)
        except Exception as e:
            msg = "Unexpected error on preparing config setup"
            self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            return logging.exception(e)

    def analyse_screening_setup(self):
        """Prepare and check screening setup."""

        control = self.control

        # Check project path exists
        if control.project_path == "":
            self.warning("Cannot process: Project location not set")
            return False

        # Check at least one logger exists
        if not control.loggers:
            self.warning("Cannot process: No loggers exist in setup")
            return False

        # Get all raw data filenames for all loggers to be processed and perform some screening checks
        # Check all ids are unique
        control.check_logger_ids(control.logger_ids)

        # Set up output folders
        control.set_up_output_folders()

        # Get raw filenames, check timestamps and select files in processing datetime range
        for logger in control.loggers:
            # Store logger filenames and check file timestamps
            logger.process_filenames()

            # Select only files in date range to process on
            logger.select_files_in_datetime_range(
                logger.process_start, logger.process_end
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
                # Connect warning signal to warning message box in DataLab class
                try:
                    # Disconnect any existing connection to prevent repeated triggerings
                    logger.signal_warning.disconnect()
                except:
                    pass
                logger.signal_warning.connect(self.warning)

                # Set user-defined channel names and units if supplied
                logger.set_processed_columns_headers()

                # Check number of headers match number of columns to process
                logger.check_headers()

        return True

    def run_screening(self):
        """Run statistical and spectral analysis in config setup."""

        # Run processing on QThread worker - prevents GUI lock up
        try:
            # Create screening object, map control data and process
            screening = Screening(self)
            screening.control = self.control

            # Create worker thread, connect signals to methods in this class and start, which this calls worker.run()
            self.worker = ControlFileWorker(screening, parent=self)
            self.worker.signal_screening_output_to_gui.connect(
                self.set_screening_output_to_gui
            )
            self.worker.signal_error.connect(self.error)
            self.worker.start()
        except Exception as e:
            msg = "Unexpected error on processing config setup"
            self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    @pyqtSlot(object)
    def set_screening_output_to_gui(self, screening):
        """Map results from processing to the GUI."""

        # Store screening object and update data quality report module
        self.screening = screening
        self.dataQualityModule.screening = screening
        self.dataQualityModule.set_data_quality_results()

        # Reset stats and spectrograms dashboards
        self.statsTab.reset_dashboard()
        self.vesselStatsTab.reset_dashboard()
        self.spectrogramTab.reset_dashboard()

        # For each logger create a stats dataset object and append to stats and vessel stats objects
        if screening.dict_stats:
            for logger_id, df in screening.dict_stats.items():
                dataset = StatsDataset(logger_id, df)
                self.statsTab.datasets.append(dataset)
                self.vesselStatsTab.datasets.append(dataset)

            # Stats dataset ids
            dataset_ids = list(screening.dict_stats.keys())

            # Add dataset ids to stats tab and create initial plot
            self.statsTab.update_datasets_list(dataset_ids)
            self.statsTab.set_preset_logger_and_channel()
            self.statsTab.update_plot()

            # Add dataset ids to vessel stats tab and create initial plot
            self.vesselStatsTab.update_stats_datasets_list(dataset_ids)
            self.vesselStatsTab.set_plot_data(init=True)
            self.vesselStatsTab.update_plots()

        # Store spectrogram datasets to spectral dashboard and create an initial plot
        if screening.dict_spectrograms:
            self.spectrogramTab.datasets = screening.dict_spectrograms
            dataset_ids = list(screening.dict_spectrograms.keys())
            self.spectrogramTab.append_multiple_spect_to_datasets_list(dataset_ids)
            self.spectrogramTab.create_plots()

    def calc_seascatter(self):
        """Create seascatter diagram if vessel stats data is loaded."""

        logger = self.scatter.metocean_logger
        df_metocean = self.scatter.check_metocean_dataset_loaded(
            datasets=self.statsTab.datasets
        )

        # Warn if the stats dataset user has specified is not in memory
        if df_metocean is False:
            if logger == "":
                msg = (
                    "No logger set in sea scatter settings tab.\n\n"
                    "Input sea scatter settings and generate or load the required statistics dataset "
                    "containing Hs and Tp data and try again."
                )
            else:
                msg = (
                    f"Statistics dataset for logger '{logger}' (set to contain Hs and Tp data) not found in memory.\n\n"
                    "Generate or load the required statistics dataset "
                    "containing Hs and Tp data and try again."
                )
            return self.warning(msg)

        try:
            hs, tp = self.scatter.get_hs_tp_data(df_metocean)

            if hs.size == 0 and tp.size == 0:
                msg = (
                    f"The specified Hs and Tp columns in the '{logger}' stats data do not exist.\n\n"
                    "Check the correct columns have been input in the sea scatter settings."
                )
                return self.warning(msg)

            self.seascatterModule.df_ss = self.scatter.df_ss
            self.seascatterModule.calc_bins(hs, tp)
            self.seascatterModule.generate_scatter_diagram()
            self.view_tab_seascatter()
        except Exception as e:
            msg = "Unexpected error generating sea scatter diagram"
            self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def on_export_scatter_diagram_triggered(self):
        """Export sea scatter diagram to Excel."""

        if self.seascatterModule.df_scatter.empty:
            self.warning("No sea scatter diagram generated. Nothing to export!")
        else:
            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save Sea Scatter Diagram", filter="Excel Files (*.xlsx)"
            )
            if filename:
                self.seascatterModule.export_scatter_diagram(filename)

    def calc_transfer_functions(self):
        """Calculate frequency-dependent transfer functions."""

        try:
            self.transFuncsTab.tf = self.tf
            status = self.transFuncsTab.tf.process_transfer_functions()

            if status is True:
                self.transFuncsTab.plot_transfer_functions()
                self.view_mod_transfer_functions()
                msg = "Frequency-dependent transfer functions calculated successfully."
                self._message_information("Calculate Transfer Functions", msg)
        except Exception as e:
            msg = "Unexpected error processing loggers"
            self.error(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)

    def calc_fatigue(self):
        return QtWidgets.QMessageBox.information(
            self, "To Do", "Feature coming in a future update."
        )


class ControlFileWorker(QtCore.QThread):
    """Worker class to process control file in separate thread."""

    # Note: Using the alternative method of creating a QObject and a standalone QThread worker and using moveToThread
    # does not work with GUIs. The QObject still stays on the QMainWindow thread. Therefore, while the processing works,
    # the GUI freezes up and doesn't show the progress bar updating.
    # Also, cannot pass parents to QObjects, which isn't ideal.
    signal_screening_output_to_gui = pyqtSignal(object)
    signal_error = pyqtSignal(str)
    signal_complete = pyqtSignal(str, int)

    def __init__(self, screening, parent=None):
        """Worker class to allow control file processing on a separate thread to the gui."""
        super(ControlFileWorker, self).__init__(parent)

        self.parent = parent

        # Screening processing object
        self.screening = screening

        logger_ids = self.screening.control.logger_ids

        # Initialise progress bar
        self.pb = ProcessingProgressBar(logger_ids=logger_ids)
        self.connect_signals()

    def connect_signals(self):
        self.pb.signal_quit_worker.connect(self.quit_worker)
        self.screening.signal_notify_progress.connect(self.pb.update_progress_bar)
        self.signal_complete.connect(self.pb.on_processing_complete)

    def run(self):
        """Override of QThread's run method to process control file."""

        try:
            self.parent.setEnabled(False)
            t0 = time()

            # Run DataLab processing; compute and write requested logger statistics and spectrograms
            self.screening.process_control_file()
            t = str(timedelta(seconds=round(time() - t0)))
            self.signal_complete.emit(t, self.screening.total_files)
            self.signal_screening_output_to_gui.emit(self.screening)
        except ValueError as e:
            self.signal_error.emit(str(e))
            logging.exception(e)
        except ZeroDivisionError as e:
            self.signal_error.emit(str(e))
            logging.exception(e)
        except Exception as e:
            msg = "Unexpected error processing control file"
            self.signal_error.emit(f"{msg}:\n{e}\n{sys.exc_info()[0]}")
            logging.exception(e)
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


# class QtDesignerGui(QtWidgets.QMainWindow, datalab_gui_layout.Ui_MainWindow):
#     def __init__(self):
#         super().__init__()
#
#         self.setupUi(self)


if __name__ == "__main__":
    os.chdir(r"C:\Users\dickinsc\PycharmProjects\DataLab\demo_data\2. Project Configs")
    app = QtWidgets.QApplication(sys.argv)
    # win = QtDesignerGui()
    win = DataLab()
    win.show()
    sys.exit(app.exec_())
