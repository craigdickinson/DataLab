"""
Class to compile and export logger stats.
"""
__author__ = "Craig Dickinson"

import os.path

import numpy as np
import pandas as pd
from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook


class StatsOutput(object):
    """
    Methods to write statistics from LoggerStats to Excel.
    """

    def __init__(self, output_dir):
        """Create workbook object and delete initial worksheet (called Sheet)."""

        # Path to save output
        self.output_dir = output_dir
        self.logger_id = ""

        # List to hold stats data for all logger channels
        self.stats = []

        # Dictionary to hold statistics data frames
        self.dict_stats = {}

        # Stats data frame for file export
        self.df_stats = pd.DataFrame()

        # Workbook object if writing stats to Excel
        self.wb = Workbook()
        sheet_name = self.wb.sheetnames[0]
        ws = self.wb[sheet_name]
        self.wb.remove(ws)

    def compile_stats(
        self, logger, sample_start, sample_end, logger_stats, logger_stats_filt
    ):
        """
        Compile statistics into data frame for exporting and for use by gui.
        :param logger: object
        :param sample_start
        :param sample_end
        :param logger_stats: object
        :param logger_stats_filt: object
        :return: None
        """

        # Store logger id
        self.logger_id = logger.logger_id

        # Reorder the unfiltered logger stats
        unfiltered_stats = self._reorder_stats(logger_stats)

        # Reorder the filtered logger stats (if processed)
        filtered_stats = self._reorder_stats(logger_stats_filt)

        # Create headers
        channels = logger.channel_names
        channels_header_unfilt = [x for chan in channels for x in [chan] * 4]
        stats_header = ["min", "max", "mean", "std"] * len(channels)
        units_header = [x for unit in logger.channel_units for x in [unit] * 4]

        # Join original and filtered stats columns
        if filtered_stats is not None:
            # Join unfiltered and filtered stats arrays
            self.stats = np.hstack((unfiltered_stats, filtered_stats))

            # Create headers containing unfiltered and filtered channels
            channel_header_filt = [
                x for chan in channels for x in [f"{chan} (filtered)"] * 4
            ]
            channels_header = channels_header_unfilt + channel_header_filt
            stats_header *= 2
            units_header *= 2
        # Use only unfiltered stats columns
        else:
            self.stats = unfiltered_stats
            channels_header = channels_header_unfilt

        # Create pandas multi-index header
        header = self._create_header(channels_header, stats_header, units_header)

        # Create stats data frame for internal use
        df = self._create_stats_dataframe(self.stats, sample_start, header)

        # Create an alternative stats data frame in a layout for writing to file (includes end timestamps column)
        self.df_stats = self._create_export_stats_dataframe(
            self.stats, sample_start, sample_end, header
        )

        # Reorder stats data frame columns to preferred order of (channel, channel (filtered)) pairs
        cols = self._reorder_columns(df)
        df = df[cols]
        self.df_stats = self.df_stats[["Start", "End"] + cols]

        # Add stats data frame to dictionary for internal use by the gui
        self.dict_stats[self.logger_id] = df

    @staticmethod
    def _reorder_stats(logger_stats):
        """
        Order stats as:
            [[chan_1: min max ave std [0],..., chan_M: min max ave std [0]],
             [chan_1: min max ave std [N],..., chan_M: min max ave std [N]]].
        """

        if len(logger_stats.min) == 0:
            return None

        num_pts = len(logger_stats.min)

        # These arrays are lists of channels, e.g.
        # mn = [[chan_1_min[0],..., chan_M_min[0]],
        #       [chan_1_min[N],..., chan_M_min[N]]]
        mn = logger_stats.min
        mx = logger_stats.max
        ave = logger_stats.mean
        std = logger_stats.std

        # Zip creates tuple of: ((ch1_min, ch1_max, ch1_ave, ch1_std),...,(chM_min, chM_max, chM_ave, chM_std))
        # Logic: Loop each data point, create list, loop each channel in zip, loop each stat in channel, add to list
        stats = [
            [stat for channel in zip(mn[k], mx[k], ave[k], std[k]) for stat in channel]
            for k in range(num_pts)
        ]

        return stats

    @staticmethod
    def _create_header(channel_header, stats_header, units_header):
        """Create multi-index header of channel names, stats, and units to use in stats data frame."""

        header = pd.MultiIndex.from_arrays(
            [channel_header, stats_header, units_header],
            names=["channels", "stats", "units"],
        )
        return header

    @staticmethod
    def _create_stats_dataframe(stats, sample_start, header):
        """Create statistics data frame."""

        df = pd.DataFrame(data=stats, index=sample_start, columns=header)

        return df

    @staticmethod
    def _create_export_stats_dataframe(stats, sample_start, sample_end, header):
        """
        Create an alternative statistics data frame layout for exporting to file (csv/xlsx/hdf5).
        The only difference is that the sample end timestamps column is include and a standard integer index is used.
        """

        # Add End time column, reset index and rename first column to Start
        df = pd.DataFrame(data=stats, columns=header)
        df.insert(loc=0, column="Start", value=sample_start)
        df.insert(loc=1, column="End", value=sample_end)

        # Convert start and end columns to strings
        df["Start"] = df["Start"].dt.strftime("%Y-%m-%d %H:%M:%S")
        df["End"] = df["End"].dt.strftime("%Y-%m-%d %H:%M:%S")

        return df

    @staticmethod
    def _reorder_columns(df):
        channels = df.columns.unique(0)
        n = len(channels)
        channels_unfilt = channels[: n // 2]
        channels_filt = channels[n // 2 :]
        new_cols = [col for pair in zip(channels_unfilt, channels_filt) for col in pair]

        return new_cols

    def write_to_hdf5(self):
        """Write stats to HDF5 file."""

        file_name = os.path.join(self.output_dir, "Statistics.h5")
        self.df_stats.to_hdf(file_name, self.logger_id)

    def write_to_csv(self):
        """Write stats to csv file."""

        file_name = os.path.join(
            self.output_dir, "Statistics_" + self.logger_id + ".csv"
        )
        self.df_stats.to_csv(file_name, index=False)

    def write_to_excel(self):
        """Write stats from a logger_stats object to Excel workbook."""

        # Convert headers and values as lists
        channels_header = self.df_stats.columns.unique(level=0).to_list()
        stats_header = self.df_stats.columns.get_level_values(level=1).to_list()
        units_header = self.df_stats.columns.get_level_values(level=2).to_list()
        data = self.df_stats.values.tolist()

        # Reformat channels header so as not to have repeating channels
        channels = channels_header[2:]
        channels = [x for chan in channels for x in [chan] + ["", "", ""]]
        channels_header = channels_header[:2] + channels

        # Create worksheet for logger
        ws = self.wb.create_sheet(title=self.logger_id)

        # Write headers
        ws.append(channels_header)
        ws.append(stats_header)
        ws.append(units_header)

        # Write data rows
        for row in data:
            ws.append(row)

        # Formatting
        # Apply scientific format to data
        max_col = ws.max_column
        max_row = ws.max_row
        for row in range(4, max_row + 1):
            for col in range(3, max_col + 1):
                ws.cell(row=row, column=col).number_format = "0.00E+00"

        # Set width of date columns
        for col in range(1, 3):
            ws.column_dimensions[get_column_letter(col)].width = 20

    def save_workbook(self):
        """Save workbook once all worksheets have been created."""

        try:
            fname = "Statistics.xlsx"
            self.wb.save(os.path.join(self.output_dir, fname))
        except:
            print("\n\nFailed to save " + fname)
