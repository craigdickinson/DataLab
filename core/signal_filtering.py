import numpy as np


def filter_signal(df, low_cutoff=None, high_cutoff=None):
    """Apply bandpass filter to data frame of time series and return filtered time series."""

    mu = df.mean().values
    df0 = df

    # Perform filtering on all channels
    fs = 1 / (df0.index[1] - df0.index[0])
    fft = np.fft.rfft(df0, axis=0)
    f = np.fft.rfftfreq(len(df0), 1 / fs)
    cut_fft = fft.copy()

    # Apply freq cut-offs (bandpass filter)
    if low_cutoff is not None:
        cut_fft[f < low_cutoff] = 0

    if high_cutoff is not None:
        cut_fft[f > high_cutoff] = 0

    # ifft
    filtered = np.fft.irfft(cut_fft, axis=0)

    # Add mean back to filtered signal
    filtered += mu

    return filtered
