"""Time series integration in frequency domain module."""

__author__ = "Craig Dickinson"

import numpy as np
import pandas as pd
import os.path


class IntegrateTimeSeries(object):
    def __init__(self, output_path=""):
        self.output_path = output_path
        self.acc_x_col = "-"
        self.acc_y_col = "-"
        self.acc_z_col = "-"
        self.ang_rate_x_col = "-"
        self.ang_rate_y_col = "-"
        self.ang_rate_z_col = "-"
        self.apply_g_correction = True

    def set_logger(self, logger):
        """Store conversion settings for logger."""

        self.acc_x_col = logger.acc_x_col
        self.acc_y_col = logger.acc_y_col
        self.acc_z_col = logger.acc_z_col
        self.ang_rate_x_col = logger.ang_rate_x_col
        self.ang_rate_y_col = logger.ang_rate_y_col
        self.ang_rate_z_col = logger.ang_rate_z_col
        self.apply_g_correction = logger.apply_gcorr

    def process_file(self, file, df):
        """Convert dataframe accelerations to displacements and angular rates to angles on and export to csv."""

        angles_data = []
        angle_cols = []
        disps_data = []
        disp_cols = []
        angles_x = None
        angles_y = None
        angles_z = None
        idx = df.iloc[:, 0]

        if isinstance(idx[0], pd.Timestamp):
            dt = (idx[1] - idx[0]).total_seconds()
        else:
            dt = idx[1] - idx[0]

        int_transform = integration_transform(len(df), dt)

        # Convert angular rate columns to angles
        # (We calculate angles first as need angles for gravity decontamination of displacements)
        if self.ang_rate_x_col != "Not used":
            angle_cols.append("Angle X (deg)")
            ang_rates = df[self.ang_rate_x_col].values
            angles_x = angular_rate_to_angle(ang_rates, int_transform)
            angles_data.append(angles_x)

        if self.ang_rate_y_col != "Not used":
            angle_cols.append("Angle Y (deg)")
            ang_rates = df[self.ang_rate_y_col].values
            angles_y = angular_rate_to_angle(ang_rates, int_transform)
            angles_data.append(angles_y)

        # Convert acceleration columns to displacements (with optional gravity decontamination)
        if self.acc_x_col != "Not used":
            disp_cols.append("Disp X (m)")
            accels = df[self.acc_x_col].values
            disps = accel_to_disp(accels, int_transform, self.apply_g_correction, angles_x)
            disps_data.append(disps)

        if self.acc_y_col != "Not used":
            disp_cols.append("Disp Y (m)")
            accels = df[self.acc_y_col].values
            disps = accel_to_disp(accels, int_transform, self.apply_g_correction, angles_y)
            disps_data.append(disps)

        if self.acc_z_col != "Not used":
            disp_cols.append("Disp Z (m)")
            accels = df[self.acc_z_col].values
            disps = accel_to_disp(
                accels, int_transform, self.apply_g_correction, angles_z, z_comp=True
            )
            disps_data.append(disps)

        # Compile new dataframe if at least one column converted
        data = disps_data + angles_data
        cols = disp_cols + angle_cols
        if cols:
            df_int = pd.DataFrame(np.array(data).T, index=idx, columns=cols)

            # New filename
            filename = os.path.basename(file)
            filename = os.path.splitext(filename)[0]
            filename += "_Converted.csv"

            # Extract logger folder
            folder = os.path.split(os.path.dirname(file))[-1]

            # Create directory path, check exists and export file
            path_to_file = os.path.join(self.output_path, folder)
            filepath = os.path.join(path_to_file, filename)
            df_int.to_csv(filepath)

            # Relative file path to report in progress bar
            rel_filepath = os.path.join("Displacements and Angles", folder, filename)

            return rel_filepath


def integration_transform(n, d):
    """Calculate the integration transform: 1/(i*2pi*f)."""

    f = np.fft.fftfreq(n, d)
    int_transform = 1 / (1j * 2 * np.pi * f[1:])
    int_transform = np.insert(int_transform, 0, 1)

    return int_transform


def angular_rate_to_angle(ang_rates, int_transform):
    """Convert angular rates to angles through single integration in frequency domain."""

    # FFT signal
    fft = np.fft.fft(ang_rates)

    # Integrate in frequency domain
    fft = fft * int_transform

    # Inverse FFT to get angles
    angles = np.fft.ifft(fft).real

    return angles


def accel_to_disp(accels, int_transform, apply_g_correction=False, angles=None, z_comp=False):
    """Convert accelerations to displacements through single integration in frequency domain."""

    # FFT signal
    fft = np.fft.fft(accels)

    # Double integrate in frequency domain
    fft = fft * int_transform ** 2

    # Inverse FFT to get displacements
    disps = np.fft.ifft(fft).real

    # Remove gravity contamination if requested
    if apply_g_correction:
        g = 9.807

        if z_comp:
            disps -= g * np.sin(np.radians(angles))
        else:
            disps -= g * np.cos(np.radians(angles))

    return disps
