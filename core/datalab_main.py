"""
Created on 4 Aug 2016

@author: bowdenc

Program to perform signal processing on logger data
"""
__author__ = 'Craig Dickinson'

import argparse
import os
import sys
from datetime import timedelta
from time import time

import pandas as pd
from PyQt5.QtCore import (QThread, pyqtSignal)

from core.calc_stats import LoggerStats
from core.control_file import ControlFile
from core.data_screen import DataScreen
from core.data_screen_report import DataScreenReport
from core.spectrograms import Spectrogram
from core.write_stats import StatsOutput

prog_info = 'Program to perform signal processing on logger data'


def parse_args(args):
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(prog='DSPLab', description=prog_info)
    parser.add_argument('-V', '--version',
                        version='%(prog)s (version 0.1)',
                        action='version'
                        )
    parser.add_argument('datfile',
                        action='store',
                        type=argparse.FileType('r'),
                        help=('specify the controlling *.dat file'
                              ' including extension'))

    return parser.parse_args(args)


class DataLab(QThread):
    """
    Class for main DataLab program. Defined as a thread object for use with gui.
    """

    # Signal to report logger file processing progress
    notify_progress = pyqtSignal(int, int)

    def __init__(self, datfile=''):
        super().__init__()

        # Get dat file from command line if not already supplied
        if not datfile:
            parser = parse_args(sys.argv[1:])
            datfile = parser.datfile.name

        self.datfile = datfile
        self.stats_dict = {}
        self.logger_path = None
        self.stats_file_type = 'csv'
        # self.stats_file_type = 'excel'
        # self.stats_file_type = 'hdf5'

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

        # Structure to amalgamate data screening results
        data_report = DataScreenReport(self.control.project_name,
                                       self.control.campaign_name)

        # Create output stats to workbook object
        stats_out = StatsOutput(output_dir=self.control.output_folder)

        print('Processing loggers...')

        # Process each logger file
        for i, logger in enumerate(loggers):
            print()

            # Change directory to logger input files (useful for gui file tree)
            self.logger_path = logger.logger_path

            # Add any bad filenames to screening report
            data_report.add_bad_filenames(logger, logger.bad_filenames)

            # Create object to store stats and data screening results
            data_screen.append(DataScreen())
            logger_stats.append(LoggerStats())

            # Set logger to process - add all logger properties from the control object for the current logger
            data_screen[i].set_logger(logger)

            # Set sample length
            data_screen[i].set_sample_length()

            # Spectrograms object
            if self.control.create_spectrograms[i]:
                spectrogram = Spectrogram(logger_id=logger.logger_id,
                                          num_chan=len(logger.stats_cols),
                                          output_dir=self.control.output_folder)
                spectrogram.set_freq(data_screen[i].sample_length, logger.stats_interval)

            n = len(data_screen[i].files)

            # Initialise sample pandas data frame for logger
            sample_df = pd.DataFrame()

            # Expose each sample here; that way it can be sent to different processing modules
            for j, f in enumerate(data_screen[i].files):
                # TODO: Consider adding multiprocessing pool here
                # TODO: If expected file in sequence is missing, store results as nan

                # Update console
                fname = os.path.basename(f)
                progress = 'Processing ' + logger.logger_id
                progress += ' file ' + str(j + 1) + ' of ' + str(n) + ' (' + fname + ')'
                print('\r%s' % progress, end='')

                # Read the file into a pandas dataframe and parse dates and floats
                df = data_screen[i].read_logger_file(f)

                # Perform basic screening checks on file - check file has expected number of data points
                data_screen[i].screen_data(file_num=j, data=df)

                # Ignore file if not of expected length
                # TODO: Allowing short sample length (revisit)
                # if data_screen[i].points_per_file[j] == logger.expected_data_points:
                if data_screen[i].points_per_file[j] <= logger.expected_data_points:
                    # Sample the data
                    while len(df) > 0:
                        # Extract sample data frame from main data
                        sample_df, df = data_screen[i].sample_dataframe(sample_df, df)

                        # Carry out processing of sample if of desired length
                        # TODO: Allowing short sample length (revisit)
                        # if len(sample_df) == data_screen[i].sample_length:
                        if len(sample_df) <= data_screen[i].sample_length:
                            # Calculate statistics
                            logger_stats[i].calc_stats(sample_df, logger.stats_unit_conv_factors)

                            # Calculate spectrograms
                            if self.control.create_spectrograms[i]:
                                spectrogram.add_data(sample_df)

                            # Clear the sample data
                            sample_df = pd.DataFrame()

                # Emit file number signal to gui
                self.notify_progress.emit(j + 1, n)

            # Add any files containing errors to screening report
            data_report.add_bad_files(logger, data_screen[i].bad_files)

            # Create dataframe of logger stats and store
            stats_out.compile_stats_dataframe(logger, data_screen[i], logger_stats[i])

            if self.stats_file_type == 'csv':
                stats_out.stats_to_csv()
                stats_out.stats_to_hdf5()
            elif self.stats_file_type == 'excel':
                stats_out.stats_to_excel(logger)
            else:
                stats_out.stats_to_hdf5()

            # Plot spectrograms
            if self.control.create_spectrograms[i]:
                spectrogram.add_timestamps(dates=data_screen[i].sample_start)
                # spectrogram.plot_spectrogram()
                spectrogram.write_spectrogram_to_hdf5()
                # spectrogram.write_spectrogram_to_csv()
                # spectrogram.write_spectrogram_to_excel()

        # Save data screen report workbook
        data_report.write_bad_filenames()
        data_report.write_bad_files()
        data_report.save_workbook(self.control.output_folder, 'Data Screening Report.xlsx')

        # Store logger stats dataframe for gui
        self.stats_dict = stats_out.stats_dict

        # Save stats workbook
        if self.stats_file_type == 'excel':
            stats_out.save_workbook()

        print('\n\nProcessing complete.')

        t1 = round(time() - t0)
        print('Screening runtime = {}'.format(str(timedelta(seconds=t1))))


if __name__ == '__main__':
    direc = r'C:\Users\dickinsc\PycharmProjects\_2. DataLab Analysis Files\21239\2. DAT Files'
    f = ''
    # f = 'controlfile.dat'
    # f = 'example_control_files/controlfile.dat'
    f = 'controlfile_21239_acc.dat'
    f = os.path.join(direc, f)
    datalab = DataLab(datfile=f)
    datalab.analyse_control_file()
    datalab.process_control_file()
