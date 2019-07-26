"""
Main class to perform signal processing on logger data.
"""
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
        self.data_screen = []

        # Dictionaries to store all processed logger stats and spectrograms to load to gui after processing is complete
        self.dict_stats = {}
        self.dict_spectrograms = {}

    def analyse_control_file(self):
        """
        DEPRECATED DAT ROUTINE - TO DELETE
        Read control file (*.dat) and extract and check input settings.
        """

        # Read and process commands in control file
        print("Analysing control file")

        # Create control file object
        self.control = Control()
        self.control.set_filename(self.datfile)
        self.control.analyse()

    def screen_loggers(self):
        """Process screening setup."""

        t0 = time()

        # Loggers - later check campaign and compare with existing
        loggers = self.control.loggers

        # Lists of objects to hold data screening settings and logger stats
        data_screen = []

        # Structure to amalgamate data screening results
        data_report = DataScreenReport(
            self.control.project_name,
            self.control.campaign_name,
            self.control.report_output_path,
        )

        # Create output stats to workbook object
        stats_out = StatsOutput(output_dir=self.control.stats_output_path)

        # List of output files
        output_files = []

        logger_ids = []
        total_files = 0
        global_process_stats = self.control.global_process_stats
        global_process_spect = self.control.global_process_spect
        any_data_on_azure = False
        stats_expected = False
        stats_processed = False
        spect_expected = False
        spect_processed = False

        # If writing stats HDF5 file, stats for all loggers are written to the same file
        # Set write mode to write new file for first logger then append for all others
        h5_write_mode = "w"
        file_suffix = ""

        # Scan loggers to get total # files, list of loggers anmes, files source (local or Azure)
        # and flags for whether stats and spectrograms are to be processed
        for logger in loggers:
            total_files += len(logger.files)
            logger_ids.append(logger.logger_id)

            # Check whether logger data is to be streamed from Azure
            if logger.data_on_azure is True:
                any_data_on_azure = True

            if global_process_stats is True and logger.process_stats is True:
                stats_expected = True

            if global_process_spect is True and logger.process_spect is True:
                spect_expected = True

        # Connect to Azure account if to be used
        if any_data_on_azure:
            bloc_blob_service = connect_to_azure_account(
                self.control.azure_account_name, self.control.azure_account_key
            )

        # Process each logger file
        print("Processing loggers...")
        file_count = 0
        for i, logger in enumerate(loggers):
            # Add any bad filenames to screening report
            data_report.add_bad_filenames(logger.logger_id, logger.dict_bad_filenames)

            # Create containers to store data screening results and stats
            data_screen.append(DataScreen())
            logger_stats = LoggerStats()
            logger_stats_filtered = LoggerStats()

            # Set logger to process - add all logger properties from the control object for the current logger
            data_screen[i].set_logger(logger)

            # Number of data points processed per sample
            stats_sample_length = int(logger.stats_interval * logger.freq)
            spect_sample_length = int(logger.spect_interval * logger.freq)

            # Spectrograms object
            if logger.process_spect is True:
                spect_unfilt = Spectrogram(
                    logger_id=logger.logger_id,
                    output_dir=self.control.spect_output_path,
                )
                spect_unfilt.set_freq(n=spect_sample_length, T=logger.spect_interval)

                spect_filt = Spectrogram(
                    logger_id=logger.logger_id,
                    output_dir=self.control.spect_output_path,
                )
                spect_filt.set_freq(n=spect_sample_length, T=logger.spect_interval)

            # Initialise sample pandas data frame for logger
            df_stats_sample = pd.DataFrame()
            df_spect_sample = pd.DataFrame()
            n = len(data_screen[i].files)

            # Expose each sample here; that way it can be sent to different processing modules
            for j, file in enumerate(data_screen[i].files):
                # TODO: Consider adding multiprocessing pool here
                # TODO: If expected file in sequence is missing, store results as nan

                # Update console
                filename = os.path.basename(file)
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
                if logger.data_on_azure is True:
                    file = stream_blob(
                        bloc_blob_service, logger.container_name, logger.blobs[j]
                    )

                # Read the file into a pandas data frame
                df = data_screen[i].read_logger_file(file)

                # Data munging/wrangling to prepare dataset for processing
                df = data_screen[i].munge_data(df)

                # Data screening module
                # Perform basic screening checks on file - check file has expected number of data points
                data_screen[i].screen_data(file_num=j, df=df)

                # Ignore file if not of expected length
                # TODO: Allowing short sample length (revisit)
                # if data_screen[i].points_per_file[j] == logger.expected_data_points:
                if data_screen[i].points_per_file[j] <= logger.expected_data_points:
                    # Initialise with stats and spectral data frames both pointing to the same source data frame
                    # (note this does not create an actual copy of the data in memory)
                    df_stats = df.copy()
                    df_spect = df.copy()

                    # Stats processing module
                    if global_process_stats is True and logger.process_stats is True:
                        while len(df_stats) > 0:
                            # Extract sample data frame from main dataset
                            df_stats_sample, df_stats = data_screen[i].sample_data(
                                df_stats_sample,
                                df_stats,
                                stats_sample_length,
                                type="stats",
                            )

                            # Process sample if meets required length
                            # TODO: Allowing short sample length (revisit)
                            # if len(df_stats_sample) == stats_sample_length:
                            if len(df_stats_sample) <= stats_sample_length:
                                # Unfiltered data
                                if logger.process_type != "Filtered only":
                                    # Calculate sample stats
                                    logger_stats.calc_stats(df_stats_sample)
                                    stats_processed = True

                                # Filtered data
                                if logger.process_type != "Unfiltered only":
                                    if data_screen[i].apply_filters is True:
                                        # Apply low/high pass filtering
                                        df_filt = data_screen[i].filter_data(
                                            df_stats_sample
                                        )

                                        # Calculate sample stats
                                        logger_stats_filtered.calc_stats(df_filt)
                                        stats_processed = True

                                # Clear sample data frame so as ready for next sample set
                                df_stats_sample = pd.DataFrame()

                    # Spectrograms processing module
                    if global_process_spect is True and logger.process_spect is True:
                        while len(df_spect) > 0:
                            # Extract sample data frame from main dataset
                            df_spect_sample, df_spect = data_screen[i].sample_data(
                                df_spect_sample,
                                df_spect,
                                spect_sample_length,
                                type="spectral",
                            )

                            # Process sample if meets required length
                            if len(df_spect_sample) <= spect_sample_length:
                                # Unfiltered data
                                if logger.process_type != "Filtered only":
                                    # Calculate sample PSD and add to spectrogram array
                                    spect_unfilt.add_data(df_spect_sample)
                                    spect_processed = True

                                # Filtered data
                                if logger.process_type != "Unfiltered only":
                                    if data_screen[i].apply_filters is True:
                                        # Apply low/high pass filtering
                                        df_filt = data_screen[i].filter_data(
                                            df_spect_sample
                                        )

                                        # Calculate sample PSD and add to spectrogram array
                                        spect_filt.add_data(df_filt)
                                        spect_processed = True

                                # Clear sample data frame so as ready for next sample set
                                df_spect_sample = pd.DataFrame()

                file_count += 1

            # Operations for logger i after all logger i files have been processed
            coverage = data_screen[i].calc_data_completeness()
            print(
                f"\nData coverage for {logger.logger_id} logger = {coverage.min():.1f}%\n"
            )

            # Add any files containing errors to screening report
            data_report.add_files_with_bad_data(
                logger.logger_id, data_screen[i].dict_bad_files
            )

            if stats_processed:
                # Create and store a data frame of logger stats
                df_stats = stats_out.compile_stats(
                    logger,
                    data_screen[i].stats_sample_start,
                    data_screen[i].stats_sample_end,
                    logger_stats,
                    logger_stats_filtered,
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

            if spect_processed:
                # Create dictionary of True/False flags of file formats to write
                dict_formats_to_write = dict(
                    h5=self.control.spect_to_h5,
                    csv=self.control.spect_to_csv,
                    xlsx=self.control.spect_to_xlsx,
                )

                # Export spectrograms to requested file formats
                if spect_unfilt.spectrograms:
                    spect_unfilt.add_timestamps(dates=data_screen[i].spect_sample_start)
                    df_dict = spect_unfilt.export_spectrograms_data(
                        dict_formats_to_write
                    )
                    self.dict_spectrograms.update(df_dict)

                    # Add to output files list - and write to progress window
                    output_files.extend(spect_unfilt.output_files)
                    self.signal_update_output_info.emit(output_files)

                if spect_filt.spectrograms:
                    spect_filt.add_timestamps(dates=data_screen[i].spect_sample_start)
                    df_dict = spect_filt.export_spectrograms_data(
                        dict_formats_to_write, filtered=True
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

        # Store data screen objects list for gui
        # TODO: May revisit this since a lot of data is unnecessary so inefficient to store
        self.data_screen = data_screen

        # Save stats workbook if requested
        if stats_processed and self.control.stats_to_xlsx is True:
            stats_filename = stats_out.save_workbook()

            # Add to output files list - and write to progress window
            file_subpath = self.control.stats_output_folder + "/" + stats_filename
            output_files.append(file_subpath)
            self.signal_update_output_info.emit(output_files)

        print("Processing complete")
        t = str(timedelta(seconds=round(time() - t0)))
        print(f"Screening runtime = {t}")

        # Check and inform user if stats/spectrograms were requested but not calculated (e.g. due to bad files)
        if stats_expected and not stats_processed:
            warning = "Warning: Statistics requested but none calculated. Check Data Screening Report."
            output_files.append(warning)
            self.signal_update_output_info.emit(output_files)

        if spect_expected and not spect_processed:
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


if __name__ == "__main__":
    direc = r"C:\Users\dickinsc\PycharmProjects\DataLab\Demo Data\21239 Project DAT"
    f = "controlfile_fugro_slim.dat"
    f = os.path.join(direc, f)
    # f = ''
    datalab = Screening(datfile=f, no_dat=False)

    try:
        datalab.analyse_control_file()
        datalab.screen_loggers()
    except Exception as e:
        logging.exception(e)
