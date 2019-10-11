"""Signal processing functions."""

__author__ = "Craig Dickinson"

import numpy as np
import pandas as pd
from scipy import signal


def calc_psd(data, fs, window="boxcar", nperseg=None, noverlap=None):
    """
    Compute power spectral density amplitudes and frequencies of an array of time series.
    :param data: Array of time series ordered by column
    :param fs: Sampling frequency
    :param window: Window to apply; default "boxcar" equates to no window applied
    :param nperseg: Number of data points per segment; default None equates to 256 points
    :param noverlap: Proportion of segment overlap; default None equates to 50% overlap
    :return: Arrays of frequencies and PSD amplitudes
    """

    f, pxx = signal.welch(
        data, fs=fs, window=window, nperseg=nperseg, noverlap=noverlap
    )

    return f, pxx


def do_fft(df, col, n):
    """Calculate FFT - not currently used."""

    # Number of samples
    N = len(df)
    s = int(N / n)

    # Time resolution and sampling frequency
    d = (df.index - df.index[0]).total_seconds()[1]

    # Spectral frequencies
    freq = np.fft.rfftfreq(N, d)[1:]

    for i in range(int(n)):
        t1 = i * s
        t2 = t1 + s
        dfi = df[t1:t2]
        N = len(dfi)

        # FFT of sample
        fft_i = abs(np.fft.rfft(dfi[col])) / N
        fft_i = fft_i[1:]
        fft_i[:-1] *= 2

        # Cumulative PSD
        if i == 0:
            fft = fft_i
        else:
            fft += fft_i

    # Average FFT
    fft = fft / int(n)

    return freq, fft


def do_psd(df, col, n):
    """Calculate PSD - use for testing scipy."""

    # Number of samples
    N = len(df)
    s = int(N / n)

    # Time resolution and sampling frequency
    d = (df.index - df.index[0]).total_seconds()[1]
    fs = 1 / d

    # Spectral frequencies
    freq = np.fft.rfftfreq(N, d)[1:]

    for i in range(int(n)):
        t1 = i * s
        t2 = t1 + s
        dfi = df[t1:t2]
        N = len(dfi)

        # PSD of sample
        psd_i = abs(np.fft.rfft(dfi[col])) ** 2 / (fs * N)
        psd_i = psd_i[1:]
        psd_i[:-1] *= 2

        # Cumulative PSD
        if i == 0:
            psd = psd_i
        else:
            psd += psd_i

    # Average PSD
    psd = psd / int(n)

    return freq, psd


def filter_signal(df, low_cutoff=None, high_cutoff=None, retain_mean=True):
    """Apply bandpass filter to data frame of time series and return data frame of filtered time series."""

    # If no cut-off frequencies are set, return empty data frame
    if low_cutoff is None and high_cutoff is None:
        return pd.DataFrame()

    # Perform filtering on all channels
    fs = 1 / (df.index[1] - df.index[0])
    fft = np.fft.fft(df, axis=0)
    f = abs(np.fft.fftfreq(len(df), 1 / fs))
    cut_fft = fft.copy()

    # Apply freq cut-offs (bandpass filter)
    if low_cutoff:
        #  Ignore the 0 Hz (DC) frequency so as to not remove signal mean
        if retain_mean is True:
            cut_fft[1:][f[1:] < low_cutoff] = 0
        else:
            cut_fft[f < low_cutoff] = 0

    if high_cutoff:
        cut_fft[f > high_cutoff] = 0

    # ifft
    filtered = np.fft.ifft(cut_fft, axis=0).real
    df_filtered = pd.DataFrame(filtered, index=df.index, columns=df.columns)

    return df_filtered
