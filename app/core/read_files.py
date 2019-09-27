"""Routines to read time series files of various formats."""

__author__ = "Craig Dickinson"

import csv
import os
from datetime import datetime, timedelta

import pandas as pd

from app.core.logger_properties import LoggerProperties


class RawDataRead(object):
    def __init__(self, logger=LoggerProperties()):
        """
        Set the logger filenames to be assessed and required read file properties.
        :param logger: LoggerProperties instance
        """

        self.logger_id = ""
        self.path_to_files = ""
        self.filenames = []

        # File read properties
        self.file_format = ""
        self.delim = ""
        self.header_rows = 0
        self.skip_rows = []
        self.channel_names = []
        self.channel_units = []

        # Initialise with current logger settings
        self.set_logger(logger)

    def set_logger(self, logger):
        """Set the logger filenames and required read file properties."""

        self.logger_id = logger.logger_id
        self.path_to_files = logger.logger_path
        self.filenames = logger.get_filenames()
        self.channel_names = logger.all_channel_names
        self.channel_units = logger.all_channel_units

        # Set file read properties
        self.file_format = logger.file_format
        self.delim = logger.file_delimiter
        header_row = logger.channel_header_row - 1
        units_row = logger.units_header_row - 1

        # Additional header rows to skip - only using the first header row for data frame column names
        self.skip_rows = [
            i for i in range(logger.num_headers) if i > header_row and i != units_row
        ]

        # No header row specified
        if header_row < 0:
            self.header_rows = None
        elif units_row < 0:
            self.header_rows = header_row
        else:
            self.header_rows = [header_row, units_row]

    def read_file(self, filename):
        """Read time series file into data frame using logger file format settings."""

        df = pd.DataFrame()

        # Read data to data frame
        if self.file_format == "Fugro-csv" or self.file_format == "General-csv":
            df = pd.read_csv(
                filename,
                sep=self.delim,
                header=self.header_rows,
                skiprows=self.skip_rows,
                encoding="latin",
            )
            df = df.dropna(axis=1)
        elif self.file_format == "Pulse-acc":
            df = read_pulse_acc(filename, multi_header=True)
        elif self.file_format == "2HPS2-acc":
            df = read_2hps2_acc(filename, multi_header=True)

        return df


def read_fugro_csv(filename):
    """Raw data module: Read Fugro-csv file to data frame. Index is time steps."""

    try:
        df = pd.read_csv(filename, header=[1, 2], index_col=0, encoding="latin")
    except FileNotFoundError:
        raise FileNotFoundError(f"Could not load file {filename}. File not found.")

    try:
        df.index = pd.to_datetime(df.index, format="%d-%b-%Y %H:%M:%S.%f")
    except ValueError:
        raise ValueError(
            f"Could not load file {filename}.\n\nCSV files must be of Fugro format (for now...)."
        )

    # Calculate time delta from t0 and convert to seconds (float)
    t = (df.index - df.index[0]).total_seconds().values.round(3)
    df = df.reset_index()
    df.index = t
    df.index.name = "Time (s)"
    df = df.rename(columns={"index": "Timestamp"})
    df.columns.rename(["channels", "units"], inplace=True)

    return df


def read_pulse_acc(filename, multi_header=True):
    """
    Read Pulse-acc file to data frame.
    single-index header is used for screening module:
        Header is channel names only (units are omitted);
        Index is range index (note time steps column is replaced by timestamps).
    multi-header is used for raw data module:
        Header is channel names and units as a multi-index header;
        Timestamps columns added;
        Index is time steps.
    :param filename: *.acc file
    :param multi_header: If true header is a two-row multi-index, otherwise is a single row
    :return: df
    """

    num_headers = 20
    header_row = 18
    timestamp_row = 20

    with open(filename, "r") as f:
        accreader = csv.reader(f, delimiter=" ")

        # Skip file info headers but extract header row and timestamp row data
        for i in range(num_headers):
            # Read columns header
            if i == header_row - 1:
                header = next(accreader)
            # Read the start timestamp
            elif i == timestamp_row - 1:
                ts_start = next(accreader)
            else:
                next(accreader)

        # Read body - filter out blanks
        data = [list(filter(None, line)) for line in accreader]

    # Convert column names list so it is split by ":" not " "
    header = " ".join(header).split(":")

    # Drop "%Data," from the first column
    header[0] = header[0].split(",")[1]

    # Extract and convert start timestamp to datetime
    ts_start = list(map(int, ts_start[1:]))
    dt_start = datetime(
        ts_start[5],  # year
        ts_start[4],  # month
        ts_start[3],  # day
        ts_start[2],  # hour
        ts_start[1],  # minute
        ts_start[0],  # second
    )

    # Create data frame and timestamps using start timestamp marker and time steps column
    df = pd.DataFrame(data, dtype="float")
    ts = df.iloc[:, 0].values
    timestamps = [dt_start + timedelta(seconds=t) for t in ts]

    # For raw data module
    if multi_header is True:
        # Create multi-index header of channel names and units and time steps index
        channels = [col.split("(")[0].strip() for col in header]
        units = [col.split("(")[1][:-1] for col in header]
        header = list(zip(channels, units))
        header.insert(0, ("Timestamp", ""))
        header = pd.MultiIndex.from_tuples(header, names=["channels", "units"])
        df = df.set_index(df.columns[0])
        df.index.name = "Time (s)"
        df.insert(loc=0, column="Timestamp", value=timestamps)
    # For screening module
    else:
        # Create single row header of only channel names (i.e. strip out the units)
        # Replace time steps column with timestamps and use range index
        header = ["Timestamp"] + [col.split("(")[0].strip() for col in header]
        df.iloc[:, 0] = timestamps

    # Set desired header (single or multi-index)
    df.columns = header

    return df


def read_2hps2_acc(filename, multi_header=True):
    """
    Read old-school Pulse-acc file format generated by 2HPS2.
    text-based files that are space-delimited to data frame.
    single-index header is used for screening module:
        Header is channel names only (units are omitted);
        Index is range index (note time steps column is replaced by timestamps).
    multi-header is used for raw data module:
        Header is channel names and units as a multi-index header;
        Timestamps columns added;
        Index is time steps.
    :param filename: *.acc file
    :param multi_header: If true header is a two-row multi-index, otherwise is a single row
    :return: df
    """

    num_headers = 27
    header_row = 16
    units_row = 17
    timestamp_row = 20

    with open(filename, "r") as f:
        accreader = csv.reader(f, delimiter=" ")

        # Skip file info headers
        for i in range(num_headers):
            if i == header_row - 1:
                channels = next(accreader)
            elif i == units_row - 1:
                units = next(accreader)
            elif i == timestamp_row - 1:
                ts_start = next(accreader)
            else:
                next(accreader)

        # Read body - filter out blanks
        data = [list(filter(None, line)) for line in accreader]

    # Convert column names list it is split by "," not " " and drop "Time" item and trim
    channels = " ".join(channels).split(",")[1:]
    channels = [c.strip() for c in channels]

    # Read the start timestamp marker and get start datetime
    ts_start = list(map(int, ts_start[5:]))
    dt_start = datetime(
        ts_start[5],  # year
        ts_start[4],  # month
        ts_start[3],  # day
        ts_start[2],  # hour
        ts_start[1],  # minute
        ts_start[0],  # second
    )

    # Create data frame and timestamps using start timestamp marker and time steps column
    df = pd.DataFrame(data, dtype="float")
    ts = df.iloc[:, 0].values
    timestamps = [dt_start + timedelta(seconds=t) for t in ts]

    # For raw data module
    if multi_header is True:
        # Create multi-index header of channel names and units and time steps index
        units = " ".join(units).split(",")[1:]
        units = [i.strip().split("(")[1][:-1] for i in units]
        header = list(zip(channels, units))
        header.insert(0, ("Timestamp", ""))
        header = pd.MultiIndex.from_tuples(header, names=["channels", "units"])
        df = df.set_index(df.columns[0])
        df.index.name = "Time (s)"
        df.insert(loc=0, column="Timestamp", value=timestamps)
    # For screening module
    else:
        # Create single row header of only channel names (i.e. strip out the units)
        # Replace time steps column with timestamps and use range index
        header = ["Timestamp"] + channels
        df.iloc[:, 0] = timestamps

    # Set desired header (single or multi-index)
    df.columns = header

    return df


def read_logger_txt(filename):
    """Raw data module: Rermott txt file into pandas data frame. Index is time steps."""

    # TODO: McDermott-specifc. Need to generalise
    header1 = ["Timestamp", "Yaw", "Offset East", "Offset North"]
    header2 = ["", "deg", "m", "m"]
    cols = pd.MultiIndex.from_arrays([header1, header2], names=["channels", "units"])

    try:
        df = pd.read_csv(filename, header=None, skiprows=10, sep="\t")
        df = df.dropna(axis=1)
        df.index = df.iloc[:, 0]
        df.index.name = "Time (s)"
        df.columns = cols
    except FileNotFoundError:
        raise FileNotFoundError(f"Could not load file {filename}. File not found.")

    return df


def read_logger_hdf5(filename):
    """Load logger data stored in a .h5 file."""

    with pd.HDFStore(filename, mode="r") as store:
        datasets = store.keys()

    df = pd.read_hdf(filename, key=datasets[0], start=0, stop=36000)
    t = (df.index - df.index[0]).total_seconds().values.round(3)
    df = df.reset_index()
    df.index = t

    return df


def read_stats_hdf5(filename):
    """Read processed statistics HDF5 file for plotting."""

    df_dict = {}
    with pd.HDFStore(filename, mode="r") as store:
        datasets = store.keys()

    for key in datasets:
        df = pd.read_hdf(filename, key=key)

        # Use start date as index
        if df["End"].dtype == pd.Timestamp:
            # Drop redundant columns
            if "File Number" in df.columns:
                df = df.drop("File Number", axis=1, level=0)
            df = df.drop("End", axis=1, level=0)

            # Set index
            df = df.set_index(df.columns[0])
            df.index = pd.to_datetime(df.index, format="%Y-%m-%d %H:%M:%S")
            df.index.name = "Date"
        # Use file number as index
        else:
            df = df.drop(["Start", "End"], axis=1, level=0)
            df = df.set_index(df.columns[0])
            df.index.name = "File Number"

        # Remove preceding "/" from key
        key = key[1:]
        df_dict[key] = df

    return df_dict


def read_stats_csv(filename):
    """Read processed statistics csv file for plotting."""

    df_dict = {}
    df = pd.read_csv(filename, header=[0, 1, 2])

    # Check if End column data type is datetime - if so use start date as index, otherwise use file number;
    # Use start date as index - Note: df["End"] is interpreted as a dataframe here not a series as in hdf5
    if df["End"].dtypes.all() == pd.Timestamp:
        # Drop redundant columns
        if "File Number" in df.columns:
            df = df.drop("File Number", axis=1, level=0)
        df = df.drop("End", axis=1, level=0)
        df = df.set_index(df.columns[0])
        df.index.name = "Date"

        # Convert timestamps to datetime
        try:
            df.index = pd.to_datetime(df.index, format="%Y-%m-%d %H:%M:%S")
        except:
            try:
                # Timestamp will likely be in local (UK) format if csv file has been subsequently edited and saved
                df.index = pd.to_datetime(df.index, format="%d/%m/%Y %H:%M")
            except Exception as e:
                raise
    # Use file number as index
    else:
        df = df.drop(["Start", "End"], axis=1, level=0)
        df = df.set_index(df.columns[0])
        df.index.name = "File Number"

    df.columns.rename(["channels", "stats", "units"], inplace=True)
    logger = filename.split("Statistics_")[-1].split(".")[0]
    df_dict[logger] = df

    return df_dict


def read_stats_excel(filename):
    """Read processed statistics Excel file for plotting."""

    df_dict = {}
    xl = pd.ExcelFile(filename)

    for sh in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sh, header=[0, 1, 2])

        # Use start date as index
        if df["End"].dtypes.all() == pd.Timestamp:
            if "File Number" in df.columns:
                df = df.drop("File Number", axis=1, level=0)
            df = df.drop("End", axis=1, level=0)
            df = df.set_index(df.columns[0])
            df.index = pd.to_datetime(df.index, format="%Y-%m-%d %H:%M:%S")
            df.index.name = "Date"
        # Use file number as index
        else:
            df = df.drop(["Start", "End"], axis=1, level=0)
            df = df.set_index(df.columns[0])
            df.index.name = "File Number"

        df.columns.rename(["channels", "stats", "units"], inplace=True)
        df_dict[sh] = df

    return df_dict


def read_spectrograms_hdf5(filename):
    """Read spectrograms data HDF5 file."""

    with pd.HDFStore(filename, mode="r") as store:
        # info = store.info().split('\n')
        datasets = store.keys()

    key = datasets[0]
    df = pd.read_hdf(filename, key=key)
    key = key[1:]

    # Replace _ with " "
    key = " ".join(key.split("_"))

    return key, df


def read_spectrograms_csv(filename):
    """Read spectrograms data csv file."""

    key = filename.split("Spectrograms_Data_")[-1].split(".")[0]
    df = pd.read_csv(filename, index_col=0)

    if df.index.dtype == pd.Timestamp:
        df.index = pd.to_datetime(df.index, format="%Y-%m-%d %H:%M:%S")

    # Need to convert frequencies (header) from object/string to float
    df.columns = df.columns.astype(float)

    # Replace _ with " "
    key = " ".join(key.split("_"))

    return key, df


def read_spectrograms_excel(filename):
    """Read spectrograms data Excel file."""

    xl = pd.ExcelFile(filename)
    key = xl.sheet_names[0]
    df = pd.read_excel(xl, index_col=0)

    if df.index.dtype == pd.Timestamp:
        df.index = pd.to_datetime(df.index, format="%Y-%m-%d %H:%M:%S")

    # Replace _ with " "
    key = " ".join(key.split("_"))

    return key, df


def read_wcfat_results(filename, locations=["LPH Weld", "HPH Weld", "BOP Connector"]):
    """Read fatigue damage .dmg file output from 2HWCFAT."""

    df = pd.read_csv(filename, skiprows=8, header=None, sep="\t")

    # Drop the event length column and last column, which is just redundant ","
    df = df.drop([1, 5], axis=1)
    df.columns = ["Timestamp"] + locations
    df["Timestamp"] = df["Timestamp"].str.strip()
    df = df.set_index("Timestamp")
    df.index = pd.to_datetime(df.index, format="%Y_%m_%d_%H_%M")

    return df


def read_fatlasa_results(filename):
    """Read *_MAX_DAMAGE_history.csv file output from 2HFATLASA."""

    pass


if __name__ == "__main__":
    folder = r"C:\Users\dickinsc\PycharmProjects\DataLab\demo_data\1. Raw Data\21239 Pulse-acc\BOP"
    fname = "MPOD001_2018_06_07_16_20.ACC"

    folder = r"C:\Users\dickinsc\PycharmProjects\DataLab\demo_data\1. Raw Data\Mark H Pulse Volts"
    fname = "SMA0096_0000_2019_06_08_18_00.Acc"
    fpath = os.path.join(folder, fname)

    # df = read_pulse_acc(fpath)
    # df = read_pulse_acc(fpath, multi_header=False)
    df = read_2hps2_acc(fpath)
    df = read_2hps2_acc(fpath, multi_header=False)
    # df = read_logger_csv(r'dd10_2017_0310_0140.csv')
    # df = read_wcfat_results(r'C:\Users\dickinsc\PycharmProjects\DataLab\demo_data\Fatigue Test Data\damage_1.dmg')
    print(df.head())
