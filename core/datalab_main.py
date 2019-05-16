"""
Main class to perform signal processing on logger data.
"""
__author__ = 'Craig Dickinson'

import argparse
import logging
import os
import sys
from datetime import timedelta
from time import time

import pandas as pd
from PyQt5.QtCore import (QThread, pyqtSignal)

from calc_stats import LoggerStats
from control_file import ControlFile
from data_screen import DataScreen
from data_screen_report import DataScreenReport
from spectrograms import Spectrogram
from write_stats import StatsOutput

prog_info = 'Program to perform signal processing on logger data'


def parse_args(args):
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(prog='DataLab', description=prog_info)
    parser.add_argument('-V', '--version',
                        version='%(prog)s (version 0.1)',
                        action='version'
                        )
    parser.add_argument('datfile',
                        action='store',
                        type=argparse.FileType('r'),
                        help='specify the controlling *.dat file including extension')

    return parser.parse_args(args)


class DataLab(QThread):
    """Class for main DataLab program. Defined as a thread object for use with gui."""

    # Signal to report logger file processing progress
    signal_notify_progress = pyqtSignal(str, int, int, int, int, int)

    def __init__(self, datfile='', no_dat=False):
        super().__init__()

        if no_dat is False:
            # Get dat file from command line if not already supplied
            if datfile == '':
                parser = parse_args(sys.argv[1:])
                datfile = parser.datfile.name

        self.datfile = datfile
        self.control = ControlFile()
        self.logger_path = ''
        self.data_screen = []
        self.stats_file_type = 'csv'
        # self.stats_file_type = 'excel'
        # self.stats_file_type = 'hdf5'
        self.dict_stats = {}

    def analyse_control_file(self):
        """Read control file (*.dat) and extract and check input settings."""

        # Read and process commands in control file
        print('Analysing control file')

        # Create control file object
        self.control = ControlFile()
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
        stats_processed = False

        # Structure to amalgamate data screening results
        data_report = DataScreenReport(self.control.project_name,
                                       self.control.campaign_name)

        # Create output stats to workbook object
        stats_out = StatsOutput(output_dir=self.control.output_folder)

        # Get total number of files to process
        total_files = 0
        for logger in loggers:
            total_files += len(logger.files)

        # Process each logger file
        print('Processing loggers...')
        file_count = 0
        for i, logger in enumerate(loggers):
            print()
            if logger.process_stats is True:
                stats_processed = True

            # Change directory to logger input files (useful for gui file tree)
            self.logger_path = logger.logger_path

            # Add any bad filenames to screening report
            data_report.add_bad_filenames(logger.logger_id, logger.dict_bad_filenames)

            # Create object to store stats and data screening results
            data_screen.append(DataScreen())
            logger_stats.append(LoggerStats())

            # Set logger to process - add all logger properties from the control object for the current logger
            data_screen[i].set_logger(logger)
            stats_sample_length = int(logger.stats_interval * logger.freq)
            spectral_sample_length = int(logger.spectral_interval * logger.freq)

            # Spectrograms object
            if logger.process_spectral is True:
                spectrogram = Spectrogram(logger_id=logger.logger_id,
                                          num_chan=len(logger.spectral_cols),
                                          output_dir=self.control.output_folder,
                                          )
                spectrogram.set_freq(n=spectral_sample_length, T=logger.spectral_interval)

            # Initialise sample pandas data frame for logger
            df_stats_sample = pd.DataFrame()
            df_spectral_sample = pd.DataFrame()
            n = len(data_screen[i].files)

            # Expose each sample here; that way it can be sent to different processing modules
            for j, file in enumerate(data_screen[i].files):
                file_count += 1
                # TODO: Consider adding multiprocessing pool here
                # TODO: If expected file in sequence is missing, store results as nan

                # Update console
                filename = os.path.basename(file)
                progress = f'Processing {logger.logger_id} file {j + 1} of {n} ({filename})'
                # print(f'\r{progress}', end='')

                # Read the file into a pandas data frame
                df = data_screen[i].read_logger_file(file)

                # Data munging/wrangling to prepare dataset for processing
                df = data_screen[i].munge_data(df)

                # Data Screening module
                # Perform basic screening checks on file - check file has expected number of data points
                data_screen[i].screen_data(file_num=j, df=df)

                # Ignore file if not of expected length
                # TODO: Allowing short sample length (revisit)
                # if data_screen[i].points_per_file[j] == logger.expected_data_points:
                if data_screen[i].points_per_file[j] <= logger.expected_data_points:
                    # Initialise with stats and spectral data frames both pointing to the same source data frame
                    # (note this does not create an actual copy of the data in memory)
                    df_stats = df.copy()
                    df_spectral = df.copy()

                    # Stats processing module
                    if logger.process_stats is True:
                        while len(df_stats) > 0:
                            # Extract sample data frame from main dataset
                            df_stats_sample, df_stats = data_screen[i].sample_data(df_stats_sample,
                                                                                   df_stats,
                                                                                   stats_sample_length,
                                                                                   type='stats',
                                                                                   )

                            # Carry out processing of sample if of desired length
                            # TODO: Allowing short sample length (revisit)
                            # if len(sample_df) == data_screen[i].sample_length:
                            if len(df_stats_sample) <= stats_sample_length:
                                # Calculate statistics if logger is to be processed
                                logger_stats[i].calc_stats(df_stats_sample, logger.unit_conv_factors)
                                df_stats_sample = pd.DataFrame()

                    # Spectrograms processing module
                    if logger.process_spectral is True:
                        while len(df_spectral) > 0:
                            # Extract sample data frame from main dataset
                            df_spectral_sample, df_spectral = data_screen[i].sample_data(df_spectral_sample,
                                                                                         df_spectral,
                                                                                         spectral_sample_length,
                                                                                         type='spectral',
                                                                                         )

                            if len(df_spectral_sample) <= spectral_sample_length:
                                # Calculate spectrograms
                                spectrogram.add_data(df_spectral_sample)
                                df_spectral_sample = pd.DataFrame()

                # Emit file number signal to gui
                self.signal_notify_progress.emit(logger.logger_id, i + 1, j + 1, n, file_count, total_files)

            coverage = data_screen[i].calc_data_completeness()
            print(f'\nData coverage for {logger.logger_id} logger = {coverage.min():.1f}%')

            # Add any files containing errors to screening report
            data_report.add_files_with_bad_data(logger.logger_id, data_screen[i].dict_bad_files)

            # If processing selected logger stats
            if logger.process_stats is True:
                # Create and store a data frame of logger stats
                stats_out.compile_stats_dataframe(logger,
                                                  data_screen[i].stats_sample_start,
                                                  data_screen[i].stats_sample_end,
                                                  logger_stats[i],
                                                  )

                # Export stats in selected file format
                if self.stats_file_type == 'csv':
                    stats_out.stats_to_csv()
                    # stats_out.stats_to_hdf5()
                elif self.stats_file_type == 'excel':
                    stats_out.stats_to_excel(logger)
                else:
                    stats_out.stats_to_hdf5()

            # Plot spectrograms
            if logger.process_spectral is True:
                spectrogram.add_timestamps(dates=data_screen[i].spectral_sample_start)
                # spectrogram.plot_spectrogram()
                # spectrogram.write_spectrogram_to_hdf5()
                spectrogram.write_spectrogram_to_csv()
                # spectrogram.write_spectrogram_to_excel()

        # Save data screen report workbook
        data_report.write_bad_filenames()
        data_report.write_bad_files()
        data_report.save_workbook(self.control.output_folder, 'Data Screening Report.xlsx')

        # Store data screen objects list for gui
        # TODO: May revisit this since a lot of data is unnecessary so inefficient to store
        self.data_screen = data_screen

        # If stats for at least one logger was processed, store dictionary of logger stats data frames for gui
        if stats_processed is True:
            self.dict_stats = stats_out.dict_stats

            # Save stats workbook
            if self.stats_file_type == 'excel':
                stats_out.save_workbook()

        print('\nProcessing complete')

        t1 = round(time() - t0)
        print('Screening runtime = {}'.format(str(timedelta(seconds=t1))))


if __name__ == '__main__':
    direc = r'C:\Users\dickinsc\PycharmProjects\DataLab\Demo Data\21239 Project DAT'
    f = 'controlfile_fugro_slim.dat'
    f = os.path.join(direc, f)
    # f = ''
    datalab = DataLab(datfile=f)

    try:
        datalab.analyse_control_file()
        datalab.process_control_file()
    except Exception as e:
        print(str(e))
        logging.exception(e)
