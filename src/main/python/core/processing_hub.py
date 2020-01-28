"""Main class to perform signal processing on logger data."""

__author__ = "Craig Dickinson"

import argparse
import os
from datetime import timedelta
from pathlib import Path
from time import time

from PyQt5.QtCore import QObject, pyqtSignal

from core.azure_cloud_storage import connect_to_azure_account, stream_blob
from core.control import Control
from core.data_screen import DataScreen
from core.data_screen_report import DataScreenReport
from core.histograms import Histograms
from core.spectral_screening import SpectralScreening
from core.stats_screening import StatsScreening
from core.time_series_integration import IntegrateTimeSeries

prog_info = "Program to perform signal processing on logger data"


def parse_args(args):
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(prog="DataLab", description=prog_info)
    parser.add_argument("-V", "--version", version="%(prog)s (version 0.1)", action="version")
    parser.add_argument(
        "datfile",
        action="store",
        type=argparse.FileType("r"),
        help="specify the controlling *.dat file including extension",
    )

    return parser.parse_args(args)


def create_output_folder(path_to_folder):
    """Create requested output folder if doesn't exist."""

    path = Path(path_to_folder)
    path.mkdir(parents=True, exist_ok=True)


class ProcessingHub(QObject):
    """Class for main DataLab program. Defined as a QObject for use with gui."""

    # Signal to report processing progress to progress bar class
    signal_notify_progress = pyqtSignal(dict)
    signal_update_output_info = pyqtSignal(list)

    def __init__(self, control=Control()):
        super().__init__()

        self.control = control

        # Lists of objects to hold data screening settings and logger stats
        self.data_screen_sets = []

        # Expected data/processing to be done flags
        self.any_data_on_azure = False
        self.any_stats_requested = False
        self.any_spect_requested = False
        self.any_histograms_requested = False

        # Dictionaries to store all processed logger stats and spectrograms to load to gui after processing is complete
        self.dict_stats = {}
        self.dict_spectrograms = {}
        self.dict_histograms = {}

    def _prepare_screening(self, data_report):
        """Review loggers and set properties for screening."""

        total_files = 0
        logger_ids = []

        global_process_stats = self.control.global_process_stats
        global_process_spect = self.control.global_process_spect
        global_process_histograms = self.control.global_process_histograms

        # Select only enabled loggers
        enabled_loggers = (logger for logger in self.control.loggers if logger.enabled)
        for logger in enabled_loggers:
            # Add any bad filenames to screening report
            data_report.add_bad_filenames(logger.logger_id, logger.dict_bad_filenames)

            # Create data screen logger with logger and set screening properties
            data_screen = DataScreen(logger)
            total_files += len(logger.files)
            logger_ids.append(logger.logger_id)

            # Check and update process flags
            if global_process_stats is False:
                data_screen.stats_requested = False
            else:
                data_screen.stats_requested = logger.process_stats

            if global_process_spect is False:
                data_screen.spect_requested = False
            else:
                data_screen.spect_requested = logger.process_spect

            if global_process_histograms is False:
                data_screen.histograms_requested = False
            else:
                data_screen.histograms_requested = logger.process_hists

            # Check whether logger data is to be streamed from Azure
            if logger.data_on_azure:
                self.any_data_on_azure = True

            # Set flags for if analysis of a particular type is expected to be run for any dataset
            if global_process_stats is True and logger.process_stats is True:
                self.any_stats_requested = True

            if global_process_spect is True and logger.process_spect is True:
                self.any_spect_requested = True

            if global_process_histograms is True and logger.process_hists is True:
                self.any_histograms_requested = True

            self.data_screen_sets.append(data_screen)

        return total_files, logger_ids

    def _prepare_ts_int_screening(self):
        """Review loggers and set properties for screening."""

        total_files = 0
        logger_ids = []

        # Select only enabled loggers
        enabled_loggers = (logger for logger in self.control.loggers if logger.enabled)
        for logger in enabled_loggers:
            # Create data screen logger with logger and set screening properties
            data_screen = DataScreen(logger)
            total_files += len(logger.files)
            logger_ids.append(logger.logger_id)

            # Check whether logger data is to be streamed from Azure
            if logger.data_on_azure:
                self.any_data_on_azure = True

            self.data_screen_sets.append(data_screen)

        return total_files, logger_ids

    def run_screening(self):
        """Process screening setup."""

        # SETUP
        bloc_blob_service = None
        t0 = time()

        # Structure to amalgamate data screening results
        data_report = DataScreenReport(
            self.control.project_name, self.control.campaign_name, self.control.report_output_path
        )

        # Scan loggers to get total # files, list of logger names, files source (local or Azure)
        # and flags for whether stats and spectrograms are to be processed
        total_files, logger_ids = self._prepare_screening(data_report)

        # Create processing object for requested analysis and create output folders if don't exist
        if self.any_stats_requested:
            stats_screening = StatsScreening(self.control)
            create_output_folder(self.control.stats_output_path)
        if self.any_spect_requested:
            spect_screening = SpectralScreening(self.control)
            create_output_folder(self.control.spect_output_path)
        if self.any_histograms_requested:
            histograms = Histograms(self.control)
            create_output_folder(self.control.hist_output_path)

        # Screening report output folder
        create_output_folder(self.control.report_output_path)

        # List of output files created
        output_files = []

        # Connect to Azure account if to be used
        if self.any_data_on_azure:
            bloc_blob_service = connect_to_azure_account(
                self.control.azure_account_name, self.control.azure_account_key
            )

        # PROCESSING
        # Process each dataset
        print("Processing loggers...")
        file_count = 0
        for i, data_screen in enumerate(self.data_screen_sets):
            logger = data_screen.logger
            logger_id = logger.logger_id

            # Initialise logger screening objects
            if data_screen.stats_requested:
                stats_screening.init_logger_stats()
            if data_screen.spect_requested:
                spect_screening.init_logger_spect(logger_id)
            if data_screen.histograms_requested:
                histograms.init_dataset(data_screen)

            # Get file number of first file to be processed (this is akin to load case number for no timestamp files)
            try:
                first_file_num = logger.file_indices[0] + 1
            except IndexError:
                first_file_num = 1

            # Initialise file parameters in case there are no files to process
            j = 0
            filename = ""
            n = len(data_screen.files)

            # Process each file
            # Expose each sample here; that way it can be sent to different processing modules
            for j, file in enumerate(data_screen.files):
                # TODO: If expected file in sequence is missing, store results as nan
                # Update console
                filename = os.path.basename(file)
                processed_file_num = first_file_num + j
                progress = f"Processing {logger_id} file {j + 1} of {n} ({filename})"
                print(f"\r{progress}", end="")
                t = str(timedelta(seconds=round(time() - t0)))

                # Progress info package to emit to progress bar
                dict_progress = dict(
                    logger_ids=logger_ids,
                    logger_i=i,
                    file_i=j,
                    filename=filename,
                    num_logger_files=n,
                    file_count=file_count,
                    total_files=total_files,
                    elapsed_time=t,
                )

                # Send data package to progress bar
                self.signal_notify_progress.emit(dict_progress)

                # READ FILE TO DATA FRAME
                # If streaming data from Azure Cloud read as a file stream
                if logger.data_on_azure:
                    file = stream_blob(bloc_blob_service, logger.container_name, logger.blobs[j])

                # Read the file into a pandas dataframe
                df = data_screen.read_logger_file(file)

                # Wrangle data to prepare for processing
                df = data_screen.wrangle_data(df, file_idx=j)

                # Select columns for screening
                df = data_screen.select_columns_to_process(df)
                df = data_screen.set_column_names(df)
                df = data_screen.apply_unit_conversions(df)

                # # Filter data if requested
                # df_filt=pd.DataFrame()
                # if logger.process_type != "Unfiltered only":
                #     if data_screen.apply_filters is True:
                #         df_filt = data_screen.filter_data(df_stats_sample)

                # =========================================================
                # AT THIS POINT WE SPLIT INTO DIFFERENT PROCESSING MODULES
                # =========================================================
                # Data screening module
                # Perform basic screening checks on file - check file has expected number of data points
                data_screen.screen_data(file_num=j, df=df)

                # Ignore file if not of expected length
                # TODO: Allowing short sample length (revisit)
                # if data_screen.points_per_file[j] == logger.expected_data_points:
                if data_screen.points_per_file[j] <= logger.expected_data_points:
                    # STATS SCREENING
                    if data_screen.stats_requested:
                        stats_screening.file_stats_processing(df, data_screen, processed_file_num)

                    # SPECTRAL SCREENING
                    if data_screen.spect_requested:
                        spect_screening.file_spect_processing(df, data_screen, processed_file_num)

                    # CALCULATE HISTOGRAMS
                    if data_screen.histograms_requested:
                        # Compute histograms for each channel in dataframe
                        histograms.calc_histograms(df, data_screen, processed_file_num)

                file_count += 1

            # Operations for logger i after all logger i files have been processed
            if logger.files:
                coverage = data_screen.calc_data_completeness()
                print(f"\nData coverage for {logger_id} logger = {coverage.min():.1f}%\n")

            # Add any files containing errors to screening report
            data_report.add_files_with_bad_data(logger_id, data_screen.dict_bad_files)

            # Check logger stats requested and processed for current logger
            if data_screen.stats_requested and data_screen.stats_processed:
                stats_screening.logger_stats_post(logger, data_screen, output_files)
                self.signal_update_output_info.emit(output_files)

            # Check logger stats requested and processed for current logger
            if data_screen.spect_requested and data_screen.spect_processed:
                spect_screening.logger_spect_post(data_screen, output_files)
                self.signal_update_output_info.emit(output_files)

            # Calculate aggregate histogram for each column
            histograms.calc_aggregate_histograms()

            # Append column histograms dictionary to dataset dictionary
            self.dict_histograms[logger_id] = histograms.dict_df_col_hists

            # Export dataset histograms
            histograms.export_histograms()

        # Publish data screening report
        self._publish_screening_report(data_report, output_files)

        # Update progress dialog
        self.signal_update_output_info.emit(output_files)

        # Check if screening modules were run for any logger
        any_stats_processed = False
        any_spect_processed = False
        any_histograms_processed = False
        for d in self.data_screen_sets:
            if d.stats_processed is True:
                any_stats_processed = True
            if d.spect_processed is True:
                any_spect_processed = True
            if d.histograms_processed is True:
                any_histograms_processed = True

        # Save stats workbook if requested
        if any_stats_processed and self.control.stats_to_xlsx is True:
            stats_screening.save_stats_excel(output_files)
            self.signal_update_output_info.emit(output_files)

        print("Processing complete")
        t = str(timedelta(seconds=round(time() - t0)))
        print(f"Screening runtime = {t}")

        # Check and inform user if stats/spectrograms were requested but not calculated (e.g. due to bad files)
        if self.any_stats_requested and not any_stats_processed:
            warning = (
                "Warning: Statistics requested but none calculated. Check Data Screening Report."
            )
            output_files.append(warning)
            self.signal_update_output_info.emit(output_files)

        if self.any_spect_requested and not any_spect_processed:
            warning = (
                "Warning: Spectrograms requested but none calculated. Check Data Screening Report."
            )
            output_files.append(warning)
            self.signal_update_output_info.emit(output_files)

        if self.any_histograms_requested and not any_histograms_processed:
            warning = (
                "Warning: Histograms requested but none calculated. Check Data Screening Report."
            )
            output_files.append(warning)
            self.signal_update_output_info.emit(output_files)

        # Store processing results dictionaries
        if self.any_stats_requested:
            self.dict_stats = stats_screening.dict_stats
        if self.any_spect_requested:
            self.dict_spectrograms = spect_screening.dict_spectrograms

        # Final progress info package to emit to progress bar
        dict_progress = dict(
            logger_ids=logger_ids,
            logger_i=i,
            file_i=j,
            filename=filename,
            num_logger_files=n,
            file_count=file_count,
            total_files=total_files,
            elapsed_time=t,
        )

        # Send data package to progress bar
        self.signal_notify_progress.emit(dict_progress)

    def run_ts_integration(self):
        """Run time series integration setup."""

        # SETUP
        bloc_blob_service = None
        t0 = time()
        data_integration = IntegrateTimeSeries(output_path=self.control.integration_output_path)

        # List of output files created
        output_files = []

        # Scan loggers to get total # files, list of logger names, files source (local or Azure)
        # and flags for whether stats and spectrograms are to be processed
        total_files, logger_ids = self._prepare_ts_int_screening()

        # Connect to Azure account if to be used
        if self.any_data_on_azure:
            bloc_blob_service = connect_to_azure_account(
                self.control.azure_account_name, self.control.azure_account_key
            )

        # PROCESSING
        # Process each dataset
        print("Processing loggers...")
        file_count = 0
        for i, data_screen in enumerate(self.data_screen_sets):
            logger = data_screen.logger
            logger_id = logger.logger_id

            # Initialise integrations object
            data_integration.set_logger(logger)

            # Get file number of first file to be processed (this is akin to load case number for no timestamp files)
            try:
                first_file_num = logger.file_indices[0] + 1
            except IndexError:
                first_file_num = 1

            # Initialise file parameters in case there are no files to process
            j = 0
            filename = ""
            n = len(data_screen.files)

            # Process each file
            # Expose each sample here; that way it can be sent to different processing modules
            for j, file in enumerate(data_screen.files):
                # For first file, create logger output folder
                if j == 0:
                    folder = os.path.basename(os.path.dirname(data_screen.files[0]))
                    output_path = os.path.join(self.control.integration_output_path, folder)
                    create_output_folder(output_path)

                # TODO: If expected file in sequence is missing, store results as nan
                # Update console
                filename = os.path.basename(file)
                processed_file_num = first_file_num + j
                progress = f"Processing {logger_id} file {j + 1} of {n} ({filename})"
                print(f"\r{progress}", end="")
                t = str(timedelta(seconds=round(time() - t0)))

                # Update progress info dict and emit to progress bar
                dict_progress = dict(
                    logger_ids=logger_ids,
                    logger_i=i,
                    file_i=j,
                    filename=filename,
                    num_logger_files=n,
                    file_count=file_count,
                    total_files=total_files,
                    elapsed_time=t,
                )
                self.signal_notify_progress.emit(dict_progress)

                # READ FILE TO DATA FRAME
                # If streaming data from Azure Cloud read as a file stream
                if logger.data_on_azure:
                    file = stream_blob(bloc_blob_service, logger.container_name, logger.blobs[j])

                # Read the file into a pandas dataframe
                df = data_screen.read_logger_file(file)

                # Wrangle data to prepare for processing
                df = data_screen.wrangle_data(df, file_idx=j)

                # TIME SERIES INTEGRATION
                # Acceleration and/or angular rate conversion
                if logger.process_integration:
                    out_filename = data_integration.process_file(file, df)
                    output_files.append(out_filename)

                file_count += 1

                # Update progress dialog
                self.signal_update_output_info.emit(output_files)

        print("Processing complete")
        t = str(timedelta(seconds=round(time() - t0)))
        print(f"Screening runtime = {t}")

        # Final progress info dict to emit to progress bar
        dict_progress = dict(
            logger_ids=logger_ids,
            logger_i=i,
            file_i=j,
            filename=filename,
            num_logger_files=n,
            file_count=file_count,
            total_files=total_files,
            elapsed_time=t,
        )
        self.signal_notify_progress.emit(dict_progress)

    def _publish_screening_report(self, data_report, output_files):
        """Compile and export Excel data screening report."""

        # Save data screen report workbook
        report_filename = "Data Screening Report.xlsx"
        data_report.write_bad_filenames()
        data_report.write_bad_files()
        data_report.save_workbook(report_filename)

        # Add to output files list - and write to progress window
        output_files.append(self.control.report_output_folder + "/" + report_filename)
