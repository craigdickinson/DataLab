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
from app.core.signal_processing import calc_psd


class Spectrogram(object):
    """Routines to read pandas data frames and construct spectrograms."""

    def __init__(self, logger_id, output_dir=""):
        self.logger_id = logger_id
        self.output_dir = output_dir
        self.output_folder = os.path.split(output_dir)[1]

        # Use a list to store output files in case multiple output file formats are selected
        self.output_files = []

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
        channels = df.columns[1:].astype(str)

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
        fs = 1 / ((df.iloc[1, 0] - df.iloc[0, 0]).total_seconds())
        # self.freq, psd = signal.welch(df.iloc[:, 1:], fs=fs, axis=0)
        # self.freq, psd = signal.welch(df.iloc[:, 1:].T, fs=fs)
        self.freq, psd = calc_psd(data=df.iloc[:, 1:].T.values, fs=fs, window="hann")

        # TODO: We are not using any user defined headers here - replace channel names with user header when create df?
        # Add 2d arrays to dictionary
        for i, channel in enumerate(channels):
            if channel not in self.spectrograms:
                self.spectrograms[channel] = psd[i]
            else:
                try:
                    self.spectrograms[channel] = np.row_stack(
                        [self.spectrograms[channel], psd[i]]
                    )
                except:
                    msg = (
                        f"Error during spectrograms processing:\n\n"
                        f"Length of sample is {df.shape[0]} which is less than the "
                        f"expected length of 256 used per PSD ensemble. "
                        f"Set a spectral sample length that does not result in such a "
                        f"short sample data length when processing the tail of a file."
                    )
                    raise ValueError(msg)

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
            filename = self.logger_id + "_" + channel + ".png"
            filename = os.path.join(self.output_dir, filename)
            plt.savefig(filename)

    def export_spectrograms_data(self, dict_formats_to_write, filtered=False):
        """Write spectrograms data to requested file formats (HDF5, csv, xlsx)."""

        t0 = time()
        dict_df = {}

        for channel, spect in self.spectrograms.items():
            logger_id = "_".join(self.logger_id.split(" "))
            channel = "_".join(channel.split(" "))

            key = f"{logger_id}_{channel}"
            if filtered is True:
                key += "_filtered"

            file_stem = f"Spectrograms_Data_{logger_id}_{channel}"
            if filtered is True:
                file_stem += "_(filtered)"

            # Create directory if does not exist
            if self.output_dir != "" and os.path.exists(self.output_dir) is False:
                os.makedirs(self.output_dir)

            # Check shape of spect data is valid - if contains only one event need to reshape
            try:
                # Check second dimension exists
                spect.shape[1]
            except:
                spect = spect.reshape(1, -1)

            # Create spectrogram data frame for channel and add to dictionary
            f = self.freq
            t = self.datetimes
            df = pd.DataFrame(data=spect, index=t, columns=f)

            # Replace _ in key with " "
            key2 = " ".join(key.split("_"))
            dict_df[key2] = df

            if dict_formats_to_write["h5"] is True:
                # Note HDF5 files should use a contiguous key name
                filename = file_stem + ".h5"
                file_path = os.path.join(self.output_dir, filename)
                df.to_hdf(file_path, key, mode="w")
                self.output_files.append(self.output_folder + "/" + filename)
            if dict_formats_to_write["csv"] is True:
                filename = file_stem + ".csv"
                file_path = os.path.join(self.output_dir, filename)
                df.to_csv(file_path)
                self.output_files.append(self.output_folder + "/" + filename)
            if dict_formats_to_write["xlsx"] is True:
                filename = file_stem + ".xlsx"
                file_path = os.path.join(self.output_dir, filename)
                writer = pd.ExcelWriter(file_path)

                # Worksheet name length limit is 31
                if len(key) > 31:
                    key = key[:31]

                df.to_excel(writer, sheet_name=key)
                writer.save()
                self.output_files.append(self.output_folder + "/" + filename)

        t1 = round(time() - t0)
        # print('Write hdf5 time = {}'.format(str(timedelta(seconds=t1))))

        return dict_df


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
