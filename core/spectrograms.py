"""
Class to create spectrograms.
"""
__author__ = "Craig Dickinson"

import os
from datetime import timedelta
from time import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import signal


class Spectrogram:
    """Routines to read pandas data frames and construct spectrograms."""

    def __init__(self, logger_id, num_chan, output_dir):
        self.logger_id = logger_id
        self.num_chan = num_chan
        self.output_dir = output_dir

        # Dictionary to hold spectrograms for each channel
        self.spectrograms = {}
        self.freq = np.array([])
        self.datetimes = np.array([])

    def set_freq(self, n, T):
        """
        Calculate frequency axis.
        :param n: Window length (number of sample points)
        :param T: Sample interval length (seconds)
        :return: Array of FFT sample frequencies, where d is the sample spacing.
        """

        if n == 0:
            raise ZeroDivisionError(
                "Error calculating spectrogram frequencies. Sample length is zero."
            )

        d = T / n
        self.freq = np.fft.rfftfreq(n, d)

    def add_data(self, df):
        """Calculate amplitude spectrum for each channel in sample data frame and store result in dictionary."""

        # Drop timestamp column
        channels = df.columns[1:]

        # Calculate amplitude spectrum
        # amps = [np.abs(np.fft.rfft(df[channel]) ** 2) for channel in channels]
        #
        # # Add 2d arrays to dictionary
        # for i, channel in enumerate(channels):
        #     if channel not in self.spectrograms:
        #         self.spectrograms[channel] = amps[i]
        #     else:
        #         self.spectrograms[channel] = np.column_stack([self.spectrograms[channel], amps[i]])

        # TODO: Create spectrograms with welch method with user settings
        self.freq, psd = signal.welch(df.iloc[:, 1:], fs=10, axis=0)

        # TODO: We are not using any user defined headers here - replace channel names with user header when create df?
        # Add 2d arrays to dictionary
        for i, channel in enumerate(channels):
            if channel not in self.spectrograms:
                self.spectrograms[channel] = psd[:, i]
            else:
                self.spectrograms[channel] = np.row_stack(
                    [self.spectrograms[channel], psd[:, i]]
                )

    def add_timestamps(self, dates):
        """Store all sample start dates."""

        self.datetimes = np.asarray(dates)

    def plot_spectrogram(self):
        """Plot and save spectrograms"""

        f = self.freq
        t = self.datetimes

        for channel, spect in self.spectrograms.items():
            # plt.pcolormesh(t, f, np.log10(spect))
            plt.pcolormesh(f, t, spect)
            # plt.yscale('log')

            # Limits - add controls for this
            plt.xlim(0, 1)
            # locs, labels = plt.xticks()
            # plt.setp(labels, rotation=90)
            plt.xlabel("Frequency (Hz)")
            plt.ylabel("Date")
            plt.tight_layout()
            fname = self.logger_id + "_" + channel + ".png"
            fname = os.path.join(self.output_dir, fname)
            plt.savefig(fname)

    def write_to_hdf5(self):
        """Write spectrogram data to HDF5 file."""

        t0 = time()

        for channel, spect in self.spectrograms.items():
            # print('Writing spectrogram file for ' + self.logger_id + ' ' + channel)
            filename = "_".join(("Spectrograms_Data", self.logger_id, channel + ".h5"))
            file_path = os.path.join(self.output_dir, filename)
            store_name = self.logger_id + "_" + channel
            f = self.freq
            t = self.datetimes

            df = pd.DataFrame(data=spect, index=t, columns=f)
            df.to_hdf(file_path, store_name)

        t1 = round(time() - t0)
        # print('Write hdf5 time = {}'.format(str(timedelta(seconds=t1))))

    def write_to_csv(self):
        """Write spectrogram data to csv file."""

        t0 = time()

        for channel, spect in self.spectrograms.items():
            # print('Writing spectrogram csv file for ' + self.logger_id + ' ' + channel)
            fname = "_".join(("Spectrograms_Data", self.logger_id, channel + ".csv"))
            fpath = os.path.join(self.output_dir, fname)
            f = self.freq
            t = self.datetimes

            df = pd.DataFrame(data=spect, index=t, columns=f)
            df.to_csv(fpath)

        t1 = round(time() - t0)
        # print('Write csv time = {}'.format(str(timedelta(seconds=t1))))

    def write_to_excel(self):
        """Write spectrogram data to Excel file."""

        t0 = time()

        for channel, spect in self.spectrograms.items():
            print(
                "Writing spectrogram excel file for " + self.logger_id + " " + channel
            )
            fname = "_".join(("Spectrograms_Data", self.logger_id, channel + ".xlsx"))
            fpath = os.path.join(self.output_dir, fname)
            store_name = self.logger_id + "_" + channel
            f = self.freq
            t = self.datetimes

            writer = pd.ExcelWriter(fpath)
            df = pd.DataFrame(data=spect, index=t, columns=f)
            df.to_excel(writer, sheet_name=store_name)
            writer.save()

        t1 = round(time() - t0)
        print("Write xlsx time = {}".format(str(timedelta(seconds=t1))))


# if __name__ == '__main__':
#     folder = r'C:\Users\dickinsc\PycharmProjects\_2. DataLab Analysis Files\Misc\Output 21239 Test 4'
#     filename = 'Spectrograms Data BOP AccelX.xlsx'
#     file_path = os.path.join(folder, filename)
#     df_dict = read_spectrograms(file_path)
#
#     filename = 'Spectrograms Data BOP AccelX.csv'
#     file_path = os.path.join(folder, filename)
#     df = read_spectrograms_csv(file_path)
#
#     filename = 'Spectrograms Data BOP AccelX.h5'
#     file_path = os.path.join(folder, filename)
#     df = read_spectrograms_hdf5(file_path)
#
#     sheet_names = list(df_dict.keys())
#     print(sheet_names)
#     print(df_dict[sheet_names[0]])
#
#     print(timeit.timeit('read_spectrograms()', setup='from __main__ import read_spectrograms', number=1))
