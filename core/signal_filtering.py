import numpy as np


def filter_signal(df, low_cutoff=None, high_cutoff=None, include_mean=True):
    """Apply bandpass filter to data frame of time series and return filtered time series."""

    # If no cut-off frequencies are set, return empty array
    if low_cutoff is None and high_cutoff is None:
        return np.array([])

    # Perform filtering on all channels
    fs = 1 / (df.index[1] - df.index[0])
    fft = np.fft.rfft(df, axis=0)
    f = np.fft.rfftfreq(len(df), 1 / fs)
    cut_fft = fft.copy()

    # Apply freq cut-offs (bandpass filter)
    if low_cutoff is not None:
        #  Ignore the 0 Hz (DC) frequency so as to not remove signal mean
        if include_mean is True:
            cut_fft[1:][f[1:] < low_cutoff] = 0
        else:
            cut_fft[f < low_cutoff] = 0

    if high_cutoff is not None:
        cut_fft[f > high_cutoff] = 0

    # ifft
    filtered = np.fft.irfft(cut_fft, axis=0)

    return filtered
