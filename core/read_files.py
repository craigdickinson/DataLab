from datetime import timedelta
from time import time

import pandas as pd


def read_logger_csv(filename):
    """Load logger file into pandas dataframe."""

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
        df = pd.read_excel(xl, sheet_name=sh, header=[0, 1, 2])
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
    df = pd.read_csv(filename)
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


if __name__ == '__main__':
    df = read_logger_csv(r'dd10_2017_0310_0140.csv')
    print(df.head())
