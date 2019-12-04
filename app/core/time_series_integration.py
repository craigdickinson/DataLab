"""Time series integration in frequency domain class."""

__author__ = "Craig Dickinson"

import numpy as np
import pandas as pd
import os.path


class IntegrateTimeSeries(object):
    def __init__(self):
        self.project_path = ""

    def process_file(self, file, df):
        idx = df.iloc[:, 0]
        cols = df.columns[1:]

        if isinstance(idx[0], pd.Timestamp):
            dt = (idx[1] - idx[0]).total_seconds()
        else:
            dt = idx[1] - idx[0]

        angle_data = []
        for col in cols:
            angle_ts = self.angular_rate_to_angle(df[col], dt)
            angle_data.append(angle_ts)

        df_int = pd.DataFrame(np.array(angle_data).T, index=idx, columns=cols)

        filename = os.path.basename(file)
        filename, ext = os.path.splitext(filename)

        # Extract logger folder
        folder = os.path.split(os.path.dirname(file))[-1]
        path_to_file = os.path.join(self.project_path, "Angle Conversion", folder)
        self._ensure_dir_exists(path_to_file)

        filename += "_Angle" + ext
        filepath = os.path.join(path_to_file, filename)
        df_int.to_csv(filepath)

    @staticmethod
    def _ensure_dir_exists(directory):
        """Create directory (and intermediate directories) if do not exist."""

        if directory != "" and os.path.exists(directory) is False:
            os.makedirs(directory)

    def angular_rate_to_angle(self, ang_rate_ts, dt):
        """Convert angular rate to angle through single integration in frequency domain."""

        # FFT signal
        fft = np.fft.fft(ang_rate_ts)
        f = np.fft.fftfreq(len(ang_rate_ts), dt)

        # Get integration transform
        int_transform = integration_transform(f)

        # Integrate in frequency domain
        fft = fft * int_transform

        # Inverse FFT to get angles
        angle_ts = np.fft.ifft(fft).real

        return angle_ts

    def acceleration_to_displacement(self, apply_g_correction=False):
        pass


def integration_transform(f):
    int_transform = 1 / (1j * 2 * np.pi * f[1:])
    int_transform = np.insert(int_transform, 0, 1)

    return int_transform
