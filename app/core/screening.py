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

    def __init__(self, datfile="", no_dat=True):
        super().__init__()

        if no_dat is False:
            # Get dat file from command line if not already supplied
            if datfile == "":
                parser = parse_args(sys.argv[1:])
                datfile = parser.datfile.name

        self.datfile = datfile
        self.control = Control()
        self.logger_path = ""
        self.data_screen = []
        self.total_files = 0

        # Dictionaries to store all processed logger stats and spectrograms to load to gui after processing is complete
        self.dict_stats = {}
        self.dict_spectrograms = {}

    def analyse_control_file(self):
        """Read control file (*.dat) and extract and check input settings."""

        # Read and process commands in control file
        print("Analysing control file")

        # Create control file object
        self.control = Control()
        self.control.set_filename(self.datfile)
        self.control.analyse()

    def process_control_file(self):
        """Process dat file."""

        t0 = time()

        # Loggers - later check campaign and compare with existing
        loggers = self.control.loggers

        # Lists of objects to hold data screening settings and logger stats
        data_screen = []
        logger_stats = []
        logger_stats_filtered = []
        stats_processed = False

        # Structure to amalgamate data screening results
        data_report = DataScreenReport(
            self.control.project_name, self.control.campaign_name
        )

        # Create output stats to workbook object
        stats_out = StatsOutput(output_dir=self.control.stats_output_path)

        # Get total number of files to process
        logger_ids = []
        for logger in loggers:
            self.total_files += len(logger.files)
            logger_ids.append(logger.logger_id)

        # Process each logger file
        print("Processing loggers...")
        file_count = 0
        for i, logger in enumerate(loggers):
            if logger.process_stats is True:
                stats_processed = True

            # Change directory to logger input files (useful for gui file tree)
            self.logger_path = logger.logger_path

            # Add any bad filenames to screening report
            data_report.add_bad_filenames(logger.logger_id, logger.dict_bad_filenames)

            # Create containers to store data screening results and stats
            data_screen.append(DataScreen())
            logger_stats.append(LoggerStats())
            logger_stats_filtered.append(LoggerStats())

            # Set logger to process - add all logger properties from the control object for the current logger
            data_screen[i].set_logger(logger)

            # Number of data points processed per sample
            stats_sample_length = int(logger.stats_interval * logger.freq)
            spect_sample_length = int(logger.spect_interval * logger.freq)

            # Spectrograms object
            if logger.process_spectral is True:
                spect_unfiltered = Spectrogram(
                    logger_id=logger.logger_id,
                    output_dir=self.control.spect_output_path,
                )
                spect_unfiltered.set_freq(
                    n=spect_sample_length, T=logger.spect_interval
                )

                spect_filtered = Spectrogram(
                    logger_id=logger.logger_id,
                    output_dir=self.control.spect_output_path,
                )
                spect_filtered.set_freq(n=spect_sample_length, T=logger.spect_interval)

            # Initialise sample pandas data frame for logger
            df_stats_sample = pd.DataFrame()
            df_spect_sample = pd.DataFrame()
            n = len(data_screen[i].files)

            # Expose each sample here; that way it can be sent to different processing modules
            for j, file in enumerate(data_screen[i].files):
                file_count += 1
                # TODO: Consider adding multiprocessing pool here
                # TODO: If expected file in sequence is missing, store results as nan

                # Update console
                filename = os.path.basename(file)
                progress = (
                    f"Processing {logger.logger_id} file {j + 1} of {n} ({filename})"
                )
                print(f"\r{progress}", end="")
                # print(f"{progress}")

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
                    if logger.process_stats is True:
                        while len(df_stats) > 0:
                            # Extract sample data frame from main dataset
                            df_stats_sample, df_stats = data_screen[i].sample_data(
                                df_stats_sample,
                                df_stats,
                                stats_sample_length,
                                type="stats",
                            )

                            # Processing sample if meets required length
                            # TODO: Allowing short sample length (revisit)
                            # if len(sample_df) == data_screen[i].sample_length:
                            if len(df_stats_sample) <= stats_sample_length:
                                # Calculate stats on unfiltered sample
                                if logger.process_type != "Filtered only":
                                    logger_stats[i].calc_stats(df_stats_sample)

                                # Apply low/high pass filtering and calculate stats
                                if logger.process_type != "Unfiltered only":
                                    # Check valid filters were set
                                    if data_screen[i].apply_filters is True:
                                        df_filtered = data_screen[i].filter_data(
                                            df_stats_sample
                                        )
                                        logger_stats_filtered[i].calc_stats(df_filtered)

                                # Clear sample data frame so as ready for next sample set
                                df_stats_sample = pd.DataFrame()

                    # Spectrograms processing module
                    if logger.process_spectral is True:
                        while len(df_spect) > 0:
                            # Extract sample data frame from main dataset
                            df_spect_sample, df_spect = data_screen[i].sample_data(
                                df_spect_sample,
                                df_spect,
                                spect_sample_length,
                                type="spectral",
                            )

                            # Calculate spectrograms
                            if len(df_spect_sample) <= spect_sample_length:
                                # Calculate stats on unfiltered sample
                                if logger.process_type != "Filtered only":
                                    spect_unfiltered.add_data(df_spect_sample)

                                # Apply low/high pass filtering and calculate stats
                                if logger.process_type != "Unfiltered only":
                                    # Check valid filters were set
                                    if data_screen[i].apply_filters is True:
                                        df_filtered = data_screen[i].filter_data(
                                            df_spect_sample
                                        )
                                        spect_filtered.add_data(df_filtered)

                                # Clear sample data frame so as ready for next sample set
                                df_spect_sample = pd.DataFrame()

                # Emit file number signal to gui
                dict_progress = dict(
                    logger_ids=logger_ids,
                    logger_i=i,
                    file_i=j,
                    filename=filename,
                    num_logger_files=n,
                    file_count=file_count,
                    total_files=self.total_files,
                )

                # Send data package to progress bar
                self.signal_notify_progress.emit(dict_progress)

            coverage = data_screen[i].calc_data_completeness()
            print(
                f"\nData coverage for {logger.logger_id} logger = {coverage.min():.1f}%\n"
            )

            # Add any files containing errors to screening report
            data_report.add_files_with_bad_data(
                logger.logger_id, data_screen[i].dict_bad_files
            )

            if logger.process_stats is True:
                # Create and store a data frame of logger stats
                stats_out.compile_stats(
                    logger,
                    data_screen[i].stats_sample_start,
                    data_screen[i].stats_sample_end,
                    logger_stats[i],
                    logger_stats_filtered[i],
                )

                # Export stats to requested file formats
                if self.control.stats_to_h5 is True:
                    stats_out.write_to_hdf5()
                if self.control.stats_to_csv is True:
                    stats_out.write_to_csv()
                if self.control.stats_to_xlsx is True:
                    stats_out.write_to_excel()

            if logger.process_spectral is True:
                # Create dictionary of True/False flags of file formats to write
                dict_formats_to_write = dict(
                    h5=self.control.spect_to_h5,
                    csv=self.control.spect_to_csv,
                    xlsx=self.control.spect_to_xlsx,
                )

                # Export spectrograms to requested file formats
                # TODO: Store data to dictionary to load to gui
                if spect_unfiltered.spectrograms:
                    spect_unfiltered.add_timestamps(
                        dates=data_screen[i].spect_sample_start
                    )
                    df_dict = spect_unfiltered.export_spectrograms_data(
                        dict_formats_to_write
                    )
                    self.dict_spectrograms.update(df_dict)
                if spect_filtered.spectrograms:
                    spect_filtered.add_timestamps(
                        dates=data_screen[i].spect_sample_start
                    )
                    df_dict = spect_filtered.export_spectrograms_data(
                        dict_formats_to_write, filtered=True
                    )
                    self.dict_spectrograms.update(df_dict)

        # Save data screen report workbook
        data_report.write_bad_filenames()
        data_report.write_bad_files()
        data_report.save_workbook(
            self.control.report_output_path, "Data Screening Report.xlsx"
        )

        # Store data screen objects list for gui
        # TODO: May revisit this since a lot of data is unnecessary so inefficient to store
        self.data_screen = data_screen

        # If stats for at least one logger was processed, store dictionary of logger stats data frames for gui
        if stats_processed is True:
            self.dict_stats = stats_out.dict_stats

            # Save stats workbook
            if self.control.stats_to_xlsx is True:
                stats_out.save_workbook()

        print("Processing complete")
        t1 = round(time() - t0)
        print("Screening runtime = {}".format(str(timedelta(seconds=t1))))


if __name__ == "__main__":
    direc = r"C:\Users\dickinsc\PycharmProjects\DataLab\Demo Data\21239 Project DAT"
    f = "controlfile_fugro_slim.dat"
    f = os.path.join(direc, f)
    # f = ''
    datalab = Screening(datfile=f, no_dat=False)

    try:
        datalab.analyse_control_file()
        datalab.process_control_file()
    except Exception as e:
        logging.exception(e)
