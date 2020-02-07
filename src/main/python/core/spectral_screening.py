"""Spectral screening module."""

__author__ = "Craig Dickinson"

import os

import numpy as np
import pandas as pd

from core.control import Control
from core.signal_processing import calc_psd


class SpectralScreening(object):
    """Class to perform spectral screening of loggers."""

    def __init__(self, control=Control()):
        self.control = control

        # Initialise logger stats objects
        self.spect_unfilt = Spectrogram()
        self.spect_filt = Spectrogram()

        # To store spectrograms for all datasets to load to gui
        self.dict_spectrograms = {}

        # Dictionary of True/False flags of spectrogram output file formats to create
        self.dict_spect_export_formats = dict(
            csv=control.spect_to_csv, xlsx=control.spect_to_xlsx, h5=control.spect_to_h5,
        )

    def init_logger_spect(self, logger_id):
        """Set new spectral objects for processing a new logger."""

        # Initialise logger spectrogram objects
        self.spect_unfilt = Spectrogram(logger_id, self.control.spect_output_path)
        self.spect_filt = Spectrogram(logger_id, self.control.spect_output_path)

    def file_spect_processing(self, df_file, data_screen, processed_file_num):
        """Spectral processing module."""

        logger = data_screen.logger
        sample_length = data_screen.spect_sample_length
        df_spect = df_file.copy()
        df_spect_sample = pd.DataFrame()

        while len(df_spect) > 0:
            # Store the file number of processed sample (only of use for time step indexes)
            data_screen.spect_file_nums.append(processed_file_num)

            # Extract sample data frame from main dataset
            df_spect_sample, df_spect = data_screen.sample_data(
                df_spect_sample, df_spect, sample_length, type="spectral"
            )

            # Process sample if meets required length
            # if len(df_spect_sample) <= sample_length:
            # Unfiltered data
            if logger.process_type != "Filtered only":
                # Calculate sample PSD and add to spectrogram array
                self.spect_unfilt.add_data(
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
                    self.spect_filt.add_data(
                        df_filt,
                        window=logger.psd_window,
                        nperseg=logger.psd_nperseg,
                        noverlap=logger.psd_overlap,
                    )
                    data_screen.spect_processed = True

            # Clear sample data frame ready for next sample set
            df_spect_sample = pd.DataFrame()

        return data_screen.spect_processed

    def logger_spect_post(self, data_screen):
        """Spectral post-processing of all files for a given logger."""

        output_files = []
        dates = data_screen.spect_sample_start
        file_nums = data_screen.spect_file_nums

        # Export spectrograms to requested file formats
        if self.spect_unfilt.spectrograms:
            # Set index as dates if used, otherwise file numbers
            self.spect_unfilt.set_spectrogram_index(dates, file_nums)
            df_dict = self.spect_unfilt.export_spectrograms_data(self.dict_spect_export_formats)
            self.dict_spectrograms.update(df_dict)

            # Add to output files list
            output_files.extend(self.spect_unfilt.output_files)

        if self.spect_filt.spectrograms:
            # Set index as dates if used, otherwise file numbers
            self.spect_filt.set_spectrogram_index(dates, file_nums)

            # Export
            df_dict = self.spect_filt.export_spectrograms_data(
                self.dict_spect_export_formats, filtered=True
            )
            self.dict_spectrograms.update(df_dict)

            # Add to output files list
            output_files.extend(self.spect_filt.output_files)

        return output_files


class Spectrogram(object):
    """Routines to read pandas dataframes and construct spectrograms."""

    def __init__(self, logger_id="", output_dir=""):
        self.logger_id = logger_id
        self.output_dir = output_dir
        self.output_folder = os.path.basename(output_dir)

        # Use a list to store output files in case multiple output file formats are selected
        self.output_files = []

        # Dictionary to hold spectrograms for each channel
        self.spectrograms = {}
        self.freq = np.array([])
        self.index = np.array([])
        self.expected_length = 0

    # def set_freq(self, n, T):
    #     """
    #     Calculate frequency axis.
    #     :param n: Window length (number of sample points)
    #     :param T: Sample interval length (seconds)
    #     :return: Array of FFT sample frequencies, where d is the sample spacing.
    #     """
    #
    #     if n == 0:
    #         raise ZeroDivisionError(
    #             "Error calculating spectrogram frequencies. Sample length is zero."
    #         )
    #
    #     d = T / n
    #     self.freq = np.fft.rfftfreq(n, d)

    def add_data(self, df, window="none", nperseg=None, noverlap=None):
        """Calculate amplitude spectrum for each channel in sample data frame and store result in dictionary."""

        # Column names - omit column 1 (timestamp/time)
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

        if isinstance(df.iloc[0, 0], pd.Timestamp):
            fs = 1 / ((df.iloc[1, 0] - df.iloc[0, 0]).total_seconds())
        else:
            fs = 1 / (df.iloc[1, 0] - df.iloc[0, 0])

        window = window.lower()
        if window == "none":
            window = "boxcar"

        # Calculate number of segment overlap points - set nperseg to length of sample if not provided
        n = len(df)
        if nperseg:
            noverlap = nperseg * noverlap // 100
        else:
            nperseg = n

        if nperseg <= n:
            # Calculate PSD using Welch method
            try:
                self.freq, psd = calc_psd(
                    data=df.iloc[:, 1:].T.values,
                    fs=fs,
                    window=window,
                    nperseg=nperseg,
                    noverlap=noverlap,
                )
            except Exception:
                raise Exception
        # Sample is too short, can't compute PSD
        else:
            # Just in case the first file happens to be too short,
            # calculate the expected number of zero points to create
            if self.expected_length == 0:
                if n % 2 == 0:
                    self.expected_length = nperseg // 2 + 1
                else:
                    self.expected_length = int(nperseg / 2 + 1)

            # Create a dummy row of zeros for the no PSD event
            dummy_row = np.zeros(self.expected_length)

        # Add 2d arrays to dictionary
        for i, channel in enumerate(channels):
            if channel not in self.spectrograms:
                self.spectrograms[channel] = psd[i]
                self.expected_length = len(self.freq)
            else:
                try:
                    self.spectrograms[channel] = np.row_stack([self.spectrograms[channel], psd[i]])
                except:
                    self.spectrograms[channel] = np.row_stack(
                        [self.spectrograms[channel], dummy_row]
                    )
                    msg = (
                        f"Error during spectrograms processing:\n\n"
                        f"Length of sample is {len(df)} which is less than the "
                        f"expected length of {nperseg} used per PSD ensemble. "
                        f"Set a spectral sample length that does not result in such a "
                        f"short sample data length when processing the tail of a file."
                    )
                    print(f"Spectral screening warning: {msg}")
                    # TODO: Compile warnings to control object to report to GUI at the end and write to Screening Report
                    # raise ValueError(msg)

    def set_spectrogram_index(self, dates, file_nums):
        """Store all sample start dates if timestamps used, or file numbers if not."""

        if isinstance(dates[0], pd.Timestamp):
            self.index = dates
        else:
            self.index = file_nums

    # def plot_spectrogram(self):
    #     """Plot and save spectrograms."""
    #
    #     f = self.freq
    #     t = self.index
    #
    #     for channel, spect in self.spectrograms.items():
    #         # plt.pcolormesh(t, f, np.log10(spect))
    #         plt.pcolormesh(f, t, spect)
    #         # plt.yscale('log')
    #
    #         # Limits - add controls for this
    #         plt.xlim(0, 1)
    #         # locs, labels = plt.xticks()
    #         # plt.setp(labels, rotation=90)
    #         plt.xlabel("Frequency (Hz)")
    #         plt.ylabel("Date")
    #         plt.tight_layout()
    #         filename = self.logger_id + "_" + channel + ".png"
    #         filename = os.path.join(self.output_dir, filename)
    #         plt.savefig(filename)

    def export_spectrograms_data(self, dict_formats_to_write, filtered=False):
        """Write spectrograms data to requested file formats (HDF5, csv, xlsx)."""

        dict_df = {}

        for channel, spect in self.spectrograms.items():
            # Check for possible units in column name and remove
            if "(" in channel:
                p = channel.index("(")
                channel = channel[:p].strip()
            if "[" in channel:
                p = channel.index("[")
                channel = channel[:p].strip()

            logger_id = "_".join(self.logger_id.split(" "))
            channel = "_".join(channel.split(" "))

            key = f"{logger_id}_{channel}"
            if filtered is True:
                key += "_Filtered"

            # Create file name stem
            filestem = f"Spectrograms_Data_{logger_id}_{channel}"
            if filtered is True:
                filestem += "_(Filtered)"

            # Remove disallowed characters from filename and replace spaces
            filestem = filestem.replace("/", "")
            filestem = filestem.replace("^", "")
            filestem = filestem.replace(" ", "_")

            # Check shape of spect data is valid - if contains only one event need to reshape
            try:
                # Check second dimension exists
                spect.shape[1]
            except:
                # TODO: Simpler to use flatten?
                spect = spect.reshape(1, -1)

            # Create spectrogram data frame for channel and add to dictionary
            df = pd.DataFrame(data=spect, index=self.index, columns=self.freq)

            # Replace _ in key with " "
            key2 = key.replace("_", " ")

            # Store channel spectrogram in dictionary
            dict_df[key2] = df

            # Export channel spectrogram data to file
            # CSV
            if dict_formats_to_write["csv"] is True:
                filename = filestem + ".csv"
                filepath = os.path.join(self.output_dir, filename)
                df.to_csv(filepath)
                self.output_files.append(self.output_folder + "/" + filename)

            # Excel
            if dict_formats_to_write["xlsx"] is True:
                filename = filestem + ".xlsx"
                filepath = os.path.join(self.output_dir, filename)
                writer = pd.ExcelWriter(filepath)

                # Worksheet name length limit is 31
                if len(key) > 31:
                    key = key[:31]

                df.to_excel(writer, sheet_name=key)
                writer.save()
                self.output_files.append(self.output_folder + "/" + filename)

            # HDF5
            if dict_formats_to_write["h5"] is True:
                # Note HDF5 files should use a contiguous key name
                filename = filestem + ".h5"
                filepath = os.path.join(self.output_dir, filename)
                df.to_hdf(filepath, key, mode="w")
                self.output_files.append(self.output_folder + "/" + filename)

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
