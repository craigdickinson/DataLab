"""Time series integration in frequency domain module."""

__author__ = "Craig Dickinson"

import os.path

import numpy as np
import pandas as pd
from scipy.constants import g

from core.control import Control
from core.logger_properties import LoggerProperties
from core.signal_processing import (
    add_signal_mean,
    apply_butterworth_filter,
    apply_rectangular_filter,
    create_butterworth_filter,
)


class IntegrateTimeSeries(object):
    def __init__(self, control=Control()):
        self.output_path = control.integration_output_path

        # Filter settings
        self.filter_type = control.filter_type
        self.butterworth_order = control.butterworth_order

        self.apply_g_correction = True
        self.gravity_correction_check = True
        self.xg_sign = -1
        self.yg_sign = -1

        # Column names to convert
        self.acc_x_col = "Not used"
        self.acc_y_col = "Not used"
        self.acc_z_col = "Not used"
        self.ang_rate_x_col = "Not used"
        self.ang_rate_y_col = "Not used"

        # Units conversions
        self.acc_x_units_conv = "-"
        self.acc_y_units_conv = "-"
        self.acc_z_units_conv = "-"
        self.ang_rate_x_units_conv = "-"
        self.ang_rate_y_units_conv = "-"

        # Low cut-off frequencies
        self.acc_x_low_cutoff = 0.25
        self.acc_y_low_cutoff = 0.25
        self.acc_z_low_cutoff = 0.25
        self.ang_rate_x_low_cutoff = 0.25
        self.ang_rate_y_low_cutoff = 0.25

        # High cut-off frequencies
        self.acc_x_high_cutoff = 2.0
        self.acc_y_high_cutoff = 2.0
        self.acc_z_high_cutoff = 2.0
        self.ang_rate_x_high_cutoff = 2.0
        self.ang_rate_y_high_cutoff = 2.0

        # RMS summary containers and settings
        self.output_rms_summary = True
        self.filenames = []
        self.columns = []
        self.all_rms = []

    def set_logger(self, logger: LoggerProperties):
        """Store conversion settings for logger."""

        self.apply_g_correction = logger.apply_gcorr
        self.gravity_correction_check = True
        self.xg_sign = -1
        self.yg_sign = -1
        self.output_rms_summary = logger.output_rms_summary

        # Column names
        self.acc_x_col = logger.acc_x_col
        self.acc_y_col = logger.acc_y_col
        self.acc_z_col = logger.acc_z_col
        self.ang_rate_x_col = logger.ang_rate_x_col
        self.ang_rate_y_col = logger.ang_rate_y_col

        # Units conversions
        self.acc_x_units_conv = logger.acc_x_units_conv
        self.acc_y_units_conv = logger.acc_y_units_conv
        self.acc_z_units_conv = logger.acc_z_units_conv
        self.ang_rate_x_units_conv = logger.ang_rate_x_units_conv
        self.ang_rate_y_units_conv = logger.ang_rate_y_units_conv

        # Low cut-off frequencies
        self.acc_x_low_cutoff = logger.acc_x_low_cutoff
        self.acc_y_low_cutoff = logger.acc_y_low_cutoff
        self.acc_z_low_cutoff = logger.acc_z_low_cutoff
        self.ang_rate_x_low_cutoff = logger.ang_rate_x_low_cutoff
        self.ang_rate_y_low_cutoff = logger.ang_rate_y_low_cutoff

        # High cut-off frequencies
        self.acc_x_high_cutoff = logger.acc_x_high_cutoff
        self.acc_y_high_cutoff = logger.acc_y_high_cutoff
        self.acc_z_high_cutoff = logger.acc_z_high_cutoff
        self.ang_rate_x_high_cutoff = logger.ang_rate_x_high_cutoff
        self.ang_rate_y_high_cutoff = logger.ang_rate_y_high_cutoff

    def process_file(self, file, df):
        """Convert dataframe accelerations to displacements and angular rates to angles on and export to csv."""

        angles_data = []
        angle_cols = []
        disps_data = []
        disp_cols = []
        angles_x = None
        angles_y = None
        idx = df.iloc[:, 0]
        mm_to_m = 0.001
        rad_to_deg = np.rad2deg(1)

        # Enforce a rectangular filter since a Butterworth filter does not set very low frequencies to exactly zero
        # and this causes low frequencies to explode and dominate leading to drift in integral signals
        # TODO: Notify user of this
        self.filter_type = "Rectangular"

        if isinstance(idx[0], pd.Timestamp):
            dt = (idx[1] - idx[0]).total_seconds()
        else:
            dt = idx[1] - idx[0]

        # Calculate integration transform to apply in frequency domain
        int_transform = integration_transform(len(df), dt)

        # Convert angular rates to angles
        # We calculate angles first as need angles for gravity correction of accelerations
        if self.ang_rate_x_col != "Not used":
            angle_cols.append("Angle X (deg)")
            ang_rates = df[self.ang_rate_x_col].values

            # Apply unit conversion if requested
            if self.ang_rate_x_units_conv == "rad to deg":
                ang_rates *= rad_to_deg

            # Apply filter
            ang_rates = self._filter_time_series(
                x=idx,
                y=ang_rates,
                low_cutoff=self.ang_rate_x_low_cutoff,
                high_cutoff=self.ang_rate_x_high_cutoff,
            )
            angles_x = angular_rate_to_angle(ang_rates, int_transform)
            angles_data.append(angles_x)

        if self.ang_rate_y_col != "Not used":
            angle_cols.append("Angle Y (deg)")
            ang_rates = df[self.ang_rate_y_col].values

            # Apply unit conversion if requested
            if self.ang_rate_y_units_conv == "rad to deg":
                ang_rates *= rad_to_deg

            # Apply filter
            ang_rates = self._filter_time_series(
                x=idx,
                y=ang_rates,
                low_cutoff=self.ang_rate_y_low_cutoff,
                high_cutoff=self.ang_rate_y_high_cutoff,
            )
            angles_y = angular_rate_to_angle(ang_rates, int_transform)
            angles_data.append(angles_y)

        # Convert accelerations to displacements (with optional gravity correction)
        if self.acc_x_col != "Not used":
            disp_cols.append("Disp X (m)")
            accels = df[self.acc_x_col].values

            # Apply unit conversion if requested
            if self.acc_x_units_conv == "mm to m":
                accels *= mm_to_m

            if self.apply_g_correction is True and angles_y is not None:
                # Test time series to determine correct gravity correction sign
                # (this is done only for the first logger file)
                if self.gravity_correction_check is True:
                    self.xg_sign = self.get_gravity_correction_sign(
                        accels, angles_y, self.acc_x_low_cutoff, self.acc_x_high_cutoff, idx
                    )

                accels = gravity_correction(accels, angles_y, g_sign=self.xg_sign)

            # Apply filter
            accels = self._filter_time_series(
                x=idx,
                y=accels,
                low_cutoff=self.acc_x_low_cutoff,
                high_cutoff=self.acc_x_high_cutoff,
            )
            disps = accel_to_disp(accels, int_transform)
            disps_data.append(disps)

        if self.acc_y_col != "Not used":
            disp_cols.append("Disp Y (m)")
            accels = df[self.acc_y_col].values

            # Apply unit conversion if requested
            if self.acc_y_units_conv == "mm to m":
                accels *= mm_to_m

            if self.apply_g_correction is True and angles_x is not None:
                # Test time series to determine correct gravity correction sign
                # (this is done only for the first logger file)
                if self.gravity_correction_check is True:
                    self.yg_sign = self.get_gravity_correction_sign(
                        accels, angles_x, self.acc_y_low_cutoff, self.acc_y_high_cutoff, idx
                    )

                accels = gravity_correction(accels, angles_x, g_sign=self.yg_sign)

            # Apply filter
            accels = self._filter_time_series(
                x=idx,
                y=accels,
                low_cutoff=self.acc_y_low_cutoff,
                high_cutoff=self.acc_y_high_cutoff,
            )
            disps = accel_to_disp(accels, int_transform)
            disps_data.append(disps)

        if self.acc_z_col != "Not used":
            disp_cols.append("Disp Z (m)")
            accels = df[self.acc_z_col].values

            # Apply unit conversion if requested
            if self.acc_z_units_conv == "mm to m":
                accels *= mm_to_m

            # Apply filter
            accels = self._filter_time_series(
                x=idx,
                y=accels,
                low_cutoff=self.acc_z_low_cutoff,
                high_cutoff=self.acc_z_high_cutoff,
            )

            # Note no gravity correction applied to z-accel; it's effectively constant anyway since would apply:
            # g*cos(theta_x)*cos(theta_y) => ~g*cos^2(theta) = g(1 - sin^2(theta)) ~ g
            disps = accel_to_disp(accels, int_transform)
            disps_data.append(disps)

        # Compile new dataframe if at least one column converted
        data = disps_data + angles_data
        self.columns = disp_cols + angle_cols
        if self.columns:
            df_int = pd.DataFrame(np.array(data).T, index=idx, columns=self.columns)

            # Append RMS displacements and/or angles to summary
            if self.output_rms_summary is True:
                filename = os.path.basename(file)
                self.add_to_rms_summary(df_int, filename)

            # Export to csv
            rel_filepath = export_integrated_time_series(df_int, file, self.output_path)
            return rel_filepath

    def _filter_time_series(self, x, y, low_cutoff, high_cutoff, detrend=True):
        """Calculate filtered signal of a single series."""

        # TODO: Simplify to remove dataframe and just use a single time series y with fs input
        # Apply bandpass filter (takes a dataframe as input)
        if len(y) > 0:
            df = pd.DataFrame(y, index=x)

            # Calculate sampling frequency
            try:
                # Datetime index
                fs = 1 / (df.index[1] - df.index[0]).total_seconds()
            except AttributeError:
                # Time steps index
                fs = 1 / (df.index[1] - df.index[0])

            if self.filter_type == "Butterworth":
                sos_filter = create_butterworth_filter(
                    fs, low_cutoff, high_cutoff, order=self.butterworth_order
                )
                df_filt = apply_butterworth_filter(df, sos_filter)

                if detrend is False and low_cutoff is not None:
                    df_filt = add_signal_mean(df, df_filt)
            else:
                df_filt = apply_rectangular_filter(df, fs, low_cutoff, high_cutoff, detrend=detrend)

            if df_filt.empty:
                df_filt = df

            return df_filt.values.flatten()

    def get_gravity_correction_sign(self, accels, angles, low_cutoff, high_cutoff, idx):
        """
        Calculate sign to use to remove gravity contamination from accelerations.
        To get the correct sign we calculate test g-corrected accelerations for +/- g*sign(theta).
        The sign of the signal that gives the lowest RMS filtered FFT is returned.
        """

        # Apply gravity correction with + and - signs
        accels_neg = gravity_correction(accels, angles, g_sign=-1)
        accels_pos = gravity_correction(accels, angles, g_sign=1)

        # Calculate filter signals (using filtered signal may not strictly be necessary to determine the correct sign
        # but gives a stronger signal for detection)
        accels_neg_filt = self._filter_time_series(
            x=idx, y=accels_neg, low_cutoff=low_cutoff, high_cutoff=high_cutoff,
        )
        accels_pos_filt = self._filter_time_series(
            x=idx, y=accels_pos, low_cutoff=low_cutoff, high_cutoff=high_cutoff,
        )

        # RMS of test g-corrected accelerations (correct one will have minimum RMS)
        rms_acc_neg = calc_rms(accels_neg_filt)
        rms_acc_pos = calc_rms(accels_pos_filt)

        # Index of min RMS
        g_sign = np.argmin([rms_acc_neg, rms_acc_pos])

        # Map index to required sign
        if g_sign == 0:
            g_sign = -1

        return g_sign

    def add_to_rms_summary(self, df, filename):
        """Calculate RMS of dataframe and append to store."""

        rms_data = calc_rms(df.values)
        self.all_rms.append(rms_data)
        self.filenames.append(filename)

    def export_rms_summary(self, logger_id):
        """Export displacements and/or angles RMS summary to csv."""

        df = pd.DataFrame(self.all_rms, index=self.filenames, columns=self.columns)
        df.index.name = "Filename"
        filename = f"{logger_id} RMS Summary.csv"
        filepath = os.path.join(self.output_path, filename)
        df.to_csv(filepath)

        # Relative file path to report in progress bar
        parent_folder = os.path.basename(self.output_path)
        rel_filepath = os.path.join(parent_folder, filename)

        return rel_filepath


def calc_rms(data):
    return np.sqrt(np.mean(data ** 2, axis=0))


def integration_transform(n, d):
    """
    Calculate the FFT integration transform: 1/(i*2pi*f).
    :param n: Number of data points
    :param d: Time step
    :return: Integration factor to apply to signal FFT
    """

    f = np.fft.fftfreq(n, d)
    int_transform = 1 / (1j * 2 * np.pi * f[1:])
    int_transform = np.insert(int_transform, 0, 0)

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


def accel_to_disp(accels, int_transform):
    """Convert accelerations to displacements through single integration in frequency domain."""

    # FFT signal
    fft = np.fft.fft(accels)

    # Double integrate in frequency domain
    fft = fft * int_transform ** 2

    # Inverse FFT to get displacements
    disps = np.fft.ifft(fft).real

    return disps


def gravity_correction(accels, angles, g_sign=-1):
    """Remove gravity contamination from accelerations."""

    return accels + g_sign * g * np.sin(np.radians(angles))


def export_integrated_time_series(df, src_filepath, output_path):
    """Export all integrated time series of a file to csv."""

    # New filename
    filename = os.path.basename(src_filepath)
    filename = os.path.splitext(filename)[0]
    filename += "_Converted.csv"

    # Extract logger folder
    folder = os.path.split(os.path.dirname(src_filepath))[-1]

    # Create file path for converted file using the folder name of the source file and export dataframe to csv
    filepath = os.path.join(output_path, folder, filename)
    df.to_csv(filepath)

    # Relative file path to report in progress bar
    parent_folder = os.path.basename(output_path)
    rel_filepath = os.path.join(parent_folder, folder, filename)

    return rel_filepath
