"""Main class to perform signal processing on logger data."""

__author__ = "Craig Dickinson"

import argparse
import logging
import os
import sys
from datetime import timedelta
from time import time

import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal

from app.core.azure_cloud_storage import connect_to_azure_account, stream_blob
from app.core.calc_stats import LoggerStats
from app.core.control import Control
from app.core.data_screen import DataScreen
from app.core.data_screen_report import DataScreenReport
from app.core.spectrograms import Spectrogram
from app.core.write_stats import StatsOutput

prog_info = "Program to perform signal processing on logger data"


def parse_args(args):
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(prog="DataLab", description=prog_info)
    parser.add_argument(
        "-V", "--version", version="%(prog)s (version 0.1)", action="version"
    )
    parser.add_argument(
        "datfile",
        action="store",
        type=argparse.FileType("r"),
        help="specify the controlling *.dat file including extension",
    )

    return parser.parse_args(args)


class Screening(QThread):
    """Class for main DataLab program. Defined as a thread object for use with gui."""

    # Signal to report processing progress to progress bar class
    signal_notify_progress = pyqtSignal(dict)
    signal_update_output_info = pyqtSignal(list)

    def __init__(self, datfile="", no_dat=True):
        super().__init__()

        if no_dat is False:
            # Get dat file from command line if not already supplied
            if datfile == "":
                parser = parse_args(sys.argv[1:])
                datfile = parser.datfile.name

        self.datfile = datfile
        self.control = Control()

        # Lists of objects to hold data screening settings and logger stats
        self.data_screen_sets = []

        # Dictionaries to store all processed logger stats and spectrograms to load to gui after processing is complete
        self.dict_stats = {}
        self.dict_spectrograms = {}

    # def analyse_control_file(self):
    #     """
    #     DEPRECATED DAT ROUTINE - TO DELETE
    #     Read control file (*.dat) and extract and check input settings.
    #     """
    #
    #     # Read and process commands in control file
    #     print("Analysing control file")
    #
    #     # Create control file object
    #     self.control = Control()
    #     self.control.set_filename(self.datfile)
    #     self.control.analyse()

    def screen_loggers(self):
        """Process screening setup."""

        t0 = time()

        # Structure to amalgamate data screening results
        data_report = DataScreenReport(
            self.control.project_name,
            self.control.campaign_name,
            self.control.report_output_path,
        )

        # Create output stats to workbook object
        stats_out = StatsOutput(output_dir=self.control.stats_output_path)
        output_files = []

        # Create dictionary of True/False flags of spectrogram file formats to create
        dict_spect_export_formats = dict(
            h5=self.control.spect_to_h5,
            csv=self.control.spect_to_csv,
            xlsx=self.control.spect_to_xlsx,
        )

        # If writing stats HDF5 file, stats for all loggers are written to the same file
        # Set write mode to write new file for first logger then append for all others
        h5_write_mode = "w"
        file_suffix = ""

        # Scan loggers to get total # files, list of logger names, files source (local or Azure)
        # and flags for whether stats and spectrograms are to be processed
        total_files, logger_ids, any_data_on_azure, any_stats_expected, any_spect_expected = self._prepare_data_screening(
            data_report
        )

        # Connect to Azure account if to be used
        if any_data_on_azure:
            bloc_blob_service = connect_to_azure_account(
                self.control.azure_account_name, self.control.azure_account_key
            )

        # Process each logger file
        print("Processing loggers...")
        file_count = 0
        for i, data_screen in enumerate(self.data_screen_sets):
            logger = data_screen.logger

            # Initialise logger stats objects
            logger_stats_unfilt = LoggerStats()
            logger_stats_filt = LoggerStats()

            # Number of data points processed per sample
            stats_sample_length = int(logger.stats_interval * logger.freq)
            spect_sample_length = int(logger.spect_interval * logger.freq)

            # Initialise logger spectrograms objects
            spect_unfilt = Spectrogram(
                logger_id=logger.logger_id, output_dir=self.control.spect_output_path
            )
            spect_filt = Spectrogram(
                logger_id=logger.logger_id, output_dir=self.control.spect_output_path
            )

            # Initialise sample data frame for logger
            df_stats_sample = pd.DataFrame()
            df_spect_sample = pd.DataFrame()
            n = len(data_screen.files)

            # Get file number of first file to be processed (this is akin to load case number for no timestamp files)
            try:
                first_file_num = logger.file_indexes[0] + 1
            except IndexError:
                first_file_num = 1

            # Initialise file parameters in case there are no files to process
            j = 0
            filename = ""

            # Expose each sample here; that way it can be sent to different processing modules
            for j, file in enumerate(data_screen.files):
                # TODO: Consider adding multiprocessing pool here
                # TODO: If expected file in sequence is missing, store results as nan
                # Update console
                filename = os.path.basename(file)
                processed_file_num = first_file_num + j
                progress = (
                    f"Processing {logger.logger_id} file {j + 1} of {n} ({filename})"
                )
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

                # If streaming data from Azure Cloud read as a file stream
                if logger.data_on_azure:
                    file = stream_blob(
                        bloc_blob_service, logger.container_name, logger.blobs[j]
                    )

                # Read the file into a pandas data frame
                df = data_screen.read_logger_file(file)

                # Data munging/wrangling to prepare dataset for processing
                df = data_screen.munge_data(df, file_idx=j)

                # Data screening module
                # Perform basic screening checks on file - check file has expected number of data points
                data_screen.screen_data(file_num=j, df=df)

                # Ignore file if not of expected length
                # TODO: Allowing short sample length (revisit)
                # if data_screen[i].points_per_file[j] == logger.expected_data_points:
                if data_screen.points_per_file[j] <= logger.expected_data_points:
                    # Initialise with stats and spectral data frames both pointing to the same source data frame
                    # (note this does not create an actual copy of the data in memory)
                    df_stats = df.copy()
                    df_spect = df.copy()

                    # Stats processing module
                    if data_screen.stats_requested:
                        self.process_stats_module(
                            df_stats_sample,
                            df_stats,
                            data_screen,
                            processed_file_num,
                            stats_sample_length,
                            logger_stats_unfilt,
                            logger_stats_filt,
                        )

                    # Spectrograms processing module
                    if data_screen.spect_requested:
                        self.process_spect_module(
                            df_spect_sample,
                            df_spect,
                            data_screen,
                            processed_file_num,
                            spect_sample_length,
                            spect_unfilt,
                            spect_filt,
                        )

                file_count += 1

            # Operations for logger i after all logger i files have been processed
            if logger.files:
                coverage = data_screen.calc_data_completeness()
                print(
                    f"\nData coverage for {logger.logger_id} logger = {coverage.min():.1f}%\n"
                )

            # Add any files containing errors to screening report
            data_report.add_files_with_bad_data(
                logger.logger_id, data_screen.dict_bad_files
            )

            # Check logger stats requested and processed for current logger
            if data_screen.stats_requested and data_screen.stats_processed:
                # Create and store a data frame of logger stats
                df_stats = stats_out.compile_stats(
                    logger,
                    data_screen.stats_file_nums,
                    data_screen.stats_sample_start,
                    data_screen.stats_sample_end,
                    logger_stats_unfilt,
                    logger_stats_filt,
                )

                if not df_stats.empty:
                    # Store stats in dictionary for plotting in gui
                    self.dict_stats[logger.logger_id] = df_stats

                    # Export stats to requested file formats
                    if self.control.stats_to_h5 is True:
                        stats_filename = stats_out.write_to_hdf5(h5_write_mode)

                        # Add to output files list - and write to progress window
                        file_subpath = (
                            self.control.stats_output_folder + "/" + stats_filename
                        )
                        output_files.append(file_subpath + file_suffix)
                        self.signal_update_output_info.emit(output_files)

                        # Set write mode to append to file for additional loggers
                        if h5_write_mode == "w":
                            h5_write_mode = "a"
                            file_suffix = " (appended)"

                    if self.control.stats_to_csv is True:
                        stats_filename = stats_out.write_to_csv()

                        # Add to output files list - and write to progress window
                        file_subpath = (
                            self.control.stats_output_folder + "/" + stats_filename
                        )
                        output_files.append(file_subpath)
                        self.signal_update_output_info.emit(output_files)

                    if self.control.stats_to_xlsx is True:
                        stats_out.write_to_excel()

            # Check logger stats requested and processed for current logger
            if data_screen.spect_requested and data_screen.spect_processed:
                dates = data_screen.spect_sample_start
                file_nums = data_screen.spect_file_nums

                # Export spectrograms to requested file formats
                if spect_unfilt.spectrograms:
                    spect_unfilt.add_index(dates, file_nums)
                    df_dict = spect_unfilt.export_spectrograms_data(
                        dict_spect_export_formats
                    )
                    self.dict_spectrograms.update(df_dict)

                    # Add to output files list - and write to progress window
                    output_files.extend(spect_unfilt.output_files)
                    self.signal_update_output_info.emit(output_files)

                if spect_filt.spectrograms:
                    spect_filt.add_index(dates, file_nums)
                    df_dict = spect_filt.export_spectrograms_data(
                        dict_spect_export_formats, filtered=True
                    )
                    self.dict_spectrograms.update(df_dict)

                    # Add to output files list - and write to progress window
                    output_files.extend(spect_filt.output_files)
                    self.signal_update_output_info.emit(output_files)

        # Save data screen report workbook
        report_filename = "Data Screening Report.xlsx"
        data_report.write_bad_filenames()
        data_report.write_bad_files()
        data_report.save_workbook(report_filename)

        # Add to output files list - and write to progress window
        output_files.append(self.control.report_output_folder + "/" + report_filename)
        self.signal_update_output_info.emit(output_files)

        # Check if any stats or spectral processing was done for any logger
        any_stats_processed = False
        any_spect_processed = False

        for d in self.data_screen_sets:
            if d.stats_processed is True:
                any_stats_processed = True
            if d.spect_processed is True:
                any_spect_processed = True

        # Save stats workbook if requested
        if any_stats_processed and self.control.stats_to_xlsx is True:
            stats_filename = stats_out.save_workbook()

            # Add to output files list - and write to progress window
            file_subpath = self.control.stats_output_folder + "/" + stats_filename
            output_files.append(file_subpath)
            self.signal_update_output_info.emit(output_files)

        print("Processing complete")
        t = str(timedelta(seconds=round(time() - t0)))
        print(f"Screening runtime = {t}")

        # Check and inform user if stats/spectrograms were requested but not calculated (e.g. due to bad files)
        if any_stats_expected and not any_stats_processed:
            warning = "Warning: Statistics requested but none calculated. Check Data Screening Report."
            output_files.append(warning)
            self.signal_update_output_info.emit(output_files)

        if any_spect_expected and not any_spect_processed:
            warning = "Warning: Spectrograms requested but none calculated. Check Data Screening Report."
            output_files.append(warning)
            self.signal_update_output_info.emit(output_files)

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

    def _prepare_data_screening(self, data_report):
        """Review loggers and set properties for screening."""

        total_files = 0
        logger_ids = []
        any_data_on_azure = False
        any_stats_expected = False
        any_spect_expected = False
        global_process_stats = self.control.global_process_stats
        global_process_spect = self.control.global_process_spect

        for logger in self.control.loggers:
            # Add any bad filenames to screening report
            data_report.add_bad_filenames(logger.logger_id, logger.dict_bad_filenames)

            # Create data screen logger with logger and set screening properties
            data_screen = DataScreen(logger)

            # Create containers to store data screening results
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

            # Check whether logger data is to be streamed from Azure
            if logger.data_on_azure:
                any_data_on_azure = True

            if global_process_stats is True and logger.process_stats is True:
                any_stats_expected = True

            if global_process_spect is True and logger.process_spect is True:
                any_spect_expected = True

            self.data_screen_sets.append(data_screen)

        return (
            total_files,
            logger_ids,
            any_data_on_azure,
            any_stats_expected,
            any_spect_expected,
        )

    @staticmethod
    def process_stats_module(
        df_stats_sample,
        df_stats,
        data_screen,
        processed_file_num,
        stats_sample_length,
        logger_stats_unfilt,
        logger_stats_filt,
    ):
        """Stats processing module."""

        logger = data_screen.logger

        while len(df_stats) > 0:
            # Store the file number of processed sample (only of use for time step indexes)
            data_screen.stats_file_nums.append(processed_file_num)

            # Extract sample data frame from main dataset
            df_stats_sample, df_stats = data_screen.sample_data(
                df_stats_sample, df_stats, stats_sample_length, type="stats"
            )

            # Process sample if meets required length
            # TODO: Allowing short sample length (revisit)
            # if len(df_stats_sample) == stats_sample_length:
            if len(df_stats_sample) <= stats_sample_length:
                # Unfiltered data
                if logger.process_type != "Filtered only":
                    # Calculate sample stats
                    logger_stats_unfilt.calc_stats(df_stats_sample)
                    data_screen.stats_processed = True

                # Filtered data
                if logger.process_type != "Unfiltered only":
                    if data_screen.apply_filters is True:
                        # Apply low/high pass filtering
                        df_filt = data_screen.filter_data(df_stats_sample)

                        # Calculate sample stats
                        logger_stats_filt.calc_stats(df_filt)
                        data_screen.stats_processed = True

                # Clear sample data frame so as ready for next sample set
                df_stats_sample = pd.DataFrame()

        return data_screen.stats_processed

    @staticmethod
    def process_spect_module(
        df_spect_sample,
        df_spect,
        data_screen,
        processed_file_num,
        spect_sample_length,
        spect_unfilt,
        spect_filt,
    ):
        """Spectral processing module."""

        logger = data_screen.logger

        while len(df_spect) > 0:
            # Store the file number of processed sample (only of use for time step indexes)
            data_screen.spect_file_nums.append(processed_file_num)

            # Extract sample data frame from main dataset
            df_spect_sample, df_spect = data_screen.sample_data(
                df_spect_sample, df_spect, spect_sample_length, type="spectral"
            )

            # Process sample if meets required length
            if len(df_spect_sample) <= spect_sample_length:
                # Unfiltered data
                if logger.process_type != "Filtered only":
                    # Calculate sample PSD and add to spectrogram array
                    spect_unfilt.add_data(
                        df_spect_sample,
                        window=logger.psd_window,
                        nperseg=logger.psd_nperseg,
                        noverlap=logger.psd_overlap,
                    )
                    data_screen.spect_processed = True

                # Filtered data
                if logger.process_type != "Unfiltered only":
                    if data_screen.apply_filters is True:
                        # Apply low/high pass filtering
                        df_filt = data_screen.filter_data(df_spect_sample)

                        # Calculate sample PSD and add to spectrogram array
                        spect_filt.add_data(
                            df_filt,
                            window=logger.psd_window,
                            nperseg=logger.psd_nperseg,
                            noverlap=logger.psd_overlap,
                        )
                        data_screen.spect_processed = True

                # Clear sample data frame so as ready for next sample set
                df_spect_sample = pd.DataFrame()

        return data_screen.spect_processed


# if __name__ == "__main__":
#     direc = r"C:\Users\dickinsc\PycharmProjects\DataLab\demo_data\2. Project Configs\DAT Files (obsolete)"
#     f = "controlfile_21239_loggers.dat"
#     f = os.path.join(direc, f)
#     # f = ''
#     datalab = Screening(datfile=f, no_dat=False)
#
#     try:
#         datalab.analyse_control_file()
#         datalab.screen_loggers()
#     except Exception as e:
#         logging.exception(e)
