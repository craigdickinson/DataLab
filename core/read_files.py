import csv
import os
from datetime import datetime, timedelta
from time import time

import pandas as pd


def read_fugro_csv(filename):
    """Read Fugro-csv file into pandas data frame. Index is time in seconds."""

    try:
        df = pd.read_csv(filename, header=[1, 2], index_col=0, encoding='latin')
    except:
        raise FileNotFoundError(f'Could not load file {filename}. File not found.')

    try:
        df.index = pd.to_datetime(df.index, format='%d-%b-%Y %H:%M:%S.%f')
    except:
        raise ValueError(f'Could not load file {filename}. File must be of Fugro logger format.')

    # Calculate time delta from t0 and convert to seconds (float)
    t = (df.index - df.index[0]).total_seconds().values.round(3)
    df = df.reset_index()
    df.index = t
    df.index.name = 'Time (s)'
    df = df.rename(columns={'index': 'Timestamp'})
    df.columns.rename(['channels', 'units'], inplace=True)

    return df


def read_pulse_acc(filename):
    """
    Read Pulse-acc file into pandas data in a format used for the raw data module.
    Header is channel names and units as a multi-index header.
    Index is time in seconds.
    """

    data = []
    with open(filename, 'r') as f:
        accreader = csv.reader(f, delimiter=' ')

        # Skip file info headers
        for i in range(17):
            next(accreader)

        # Read columns header
        header = next(accreader)
        next(accreader)

        # Read the start timestamp marker
        ts_marker = next(accreader)[1:]
        ts_marker = list(map(int, ts_marker))

        # Read main data
        for line in accreader:
            line = line[:-1]
            data.append(line)

    # Convert column names list to be split by ":" not space
    header = ' '.join(header).split(':')

    # Drop "%Data," from the first column
    header[0] = header[0].split(',')[1]

    # Create multi-index header of channel names and units
    channels = [col.split('(')[0].strip() for col in header]
    units = [col.split('(')[1][:-1] for col in header]
    header = list(zip(channels, units))
    header.insert(0, ('Timestamp', ''))
    header = pd.MultiIndex.from_tuples(header, names=['channels', 'units'])

    # Create data frame
    df = pd.DataFrame(data, dtype='float')
    df = df.set_index(df.columns[0])
    df.index.name = 'Time (s)'

    # Create timestamp column using start timestamp marker and time steps column
    ts = df.index.values
    dt_start = datetime(ts_marker[5],
                        ts_marker[4],
                        ts_marker[3],
                        ts_marker[2],
                        ts_marker[1],
                        ts_marker[0],
                        )
    timestamps = [dt_start + timedelta(seconds=t) for t in ts]
    df.insert(loc=0, column='Timestamp', value=timestamps)

    # Assign columns header
    df.columns = header

    return df


def read_pulse_acc_single_header_format(filename):
    """
    Read Pulse-acc file into pandas data in a format used for stats and spectral processing.
    Header is channel names and units combined.
    Index is standard integer indexing (note time steps columns is not included).
    """

    data = []
    with open(filename, 'r') as f:
        accreader = csv.reader(f, delimiter=' ')

        # Skip file info headers
        for i in range(17):
            next(accreader)

        # Read columns header
        header = next(accreader)
        next(accreader)

        # Read the start timestamp marker
        ts_marker = next(accreader)[1:]
        ts_marker = list(map(int, ts_marker))

        # Read main data
        for line in accreader:
            line = line[:-1]
            data.append(line)

    # Convert column names list to be split by ":" not space
    header = ' '.join(header).split(':')

    # Drop "%Data," from the first column and create columns header
    header[0] = header[0].split(',')[1]

    # Create header of only channel names (i.e. strip out the units)
    header = ['Timestamp'] + [col.split('(')[0].strip() for col in header]

    # Create data frame
    df = pd.DataFrame(data, columns=header, dtype='float')

    # Create timestamp column using start timestamp marker and time steps column
    ts = df.iloc[:, 0].values
    dt_start = datetime(ts_marker[5],
                        ts_marker[4],
                        ts_marker[3],
                        ts_marker[2],
                        ts_marker[1],
                        ts_marker[0],
                        )
    timestamps = [dt_start + timedelta(seconds=t) for t in ts]

    # Replace time steps column with timestamps
    df.iloc[:, 0] = timestamps

    return df


def read_logger_hdf5(filename):
    """Load logger data stored in a .h5 file."""

    with pd.HDFStore(filename, mode='r') as store:
        datasets = store.keys()

    df = pd.read_hdf(filename, key=datasets[0], start=0, stop=36000)
    t = (df.index - df.index[0]).total_seconds().values.round(3)
    df = df.reset_index()
    df.index = t

    return df


def read_stats_hdf5(filename):
    """Read processed statistics HDF5 file for plotting."""

    df_dict = {}
    with pd.HDFStore(filename, mode='r') as store:
        datasets = store.keys()

    for key in datasets:
        df = pd.read_hdf(filename, key=key)
        df = df.drop(df.columns[1], axis=1)
        df = df.set_index(df.columns[0])
        df.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
        df.index.name = 'Datetime'

        # Remove preceding "/" from key
        key = key[1:]
        df_dict[key] = df

    return df_dict


def read_stats_csv(filename):
    """Read processed statistics Excel file for plotting."""

    df_dict = {}
    df = pd.read_csv(filename, header=[0, 1, 2], index_col=0)
    df.drop(df.columns[0], axis=1, inplace=True)

    # TODO: This is ugly - revisit
    try:
        df.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
    except:
        try:
            # Timestamp will likely be in this format if csv file has been subsequently edited and saved
            df.index = pd.to_datetime(df.index, format='%d/%m/%Y %H:%M')
        except Exception as e:
            print('Error ' + str(e))
            raise

    df.index.name = 'Datetime'
    df.columns.rename(['channels', 'stats', 'units'], inplace=True)
    logger = filename.split('Statistics_')[-1].split('.')[0]
    df_dict[logger] = df

    return df_dict


def read_stats_excel(filename):
    """Read processed statistics Excel file for plotting."""

    df_dict = {}
    xl = pd.ExcelFile(filename)

    for sh in xl.sheet_names:
        df = pd.read_excel(xl, sheet_name=sh, header=[0, 1, 2], index_col=0)
        df.drop(df.columns[0], axis=1, inplace=True)
        df.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')
        df.index.name = 'Datetime'
        df.columns.rename(['channels', 'stats', 'units'], inplace=True)
        df_dict[sh] = df

    return df_dict


def read_spectrograms_hdf5(filename):
    """Read spectrograms data HDF5 file."""

    with pd.HDFStore(filename, mode='r') as store:
        # info = store.info().split('\n')
        datasets = store.keys()

    t0 = time()
    key = datasets[0]
    df = pd.read_hdf(filename, key=key)
    t1 = round(time() - t0)
    print('Read hdf5 file time = {}'.format(str(timedelta(seconds=t1))))
    key = key[1:]

    return key, df


def read_spectrograms_csv(filename):
    """Read spectrograms data csv file."""

    t0 = time()
    logger = filename.split('Spectrograms_Data_')[-1].split('.')[0]
    df = pd.read_csv(filename, index_col=0)
    df.index = pd.to_datetime(df.index, format='%Y-%m-%d %H:%M:%S')

    # Need to convert frequencies (the column headers) to float
    df.columns = df.columns.astype(float)

    t1 = round(time() - t0)
    print('Read csv file time = {}'.format(str(timedelta(seconds=t1))))

    return logger, df


def read_spectrograms_excel(filename):
    """Read spectrograms data Excel file."""

    t0 = time()
    xl = pd.ExcelFile(filename)
    logger = xl.sheet_names[0]
    df = pd.read_excel(xl)
    t1 = round(time() - t0)
    print('Read xlsx file time = {}'.format(str(timedelta(seconds=t1))))

    return logger, df


def read_wcfat_results(filename, locations=['LPH Weld', 'HPH Weld', 'BOP Connector']):
    """Read fatigue damage .dmg file output from 2HWCFAT."""

    df = pd.read_csv(filename, skiprows=8, header=None, sep='\t')

    # Drop the event length column and last column, which is just redundant ","
    df = df.drop([1, 5], axis=1)
    df.columns = ['Timestamp'] + locations
    df['Timestamp'] = df['Timestamp'].str.strip()
    df = df.set_index('Timestamp')
    df.index = pd.to_datetime(df.index, format='%Y_%m_%d_%H_%M')

    return df


def read_fatlasa_results(filename):
    """Read *_MAX_DAMAGE_history.csv file output from 2HFATLASA."""

    pass


if __name__ == '__main__':
    folder = r'C:\Users\dickinsc\PycharmProjects\_2. DataLab Analysis Files\21239\4. Dat2Acc\POD001'
    fname = 'MPOD001_2018_06_07_16_20.ACC'
    fpath = os.path.join(folder, fname)

    # df = read_pulse_acc(fpath)
    df = read_pulse_acc_single_header_format(fpath)
    # df = read_logger_csv(r'dd10_2017_0310_0140.csv')
    # df = read_wcfat_results(r'C:\Users\dickinsc\PycharmProjects\DataLab\Fatigue Test Data\damage_1.dmg')
    print(df.head())
