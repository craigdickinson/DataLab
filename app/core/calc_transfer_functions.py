import pandas as pd
import numpy as np
import os
from glob import glob
from app.core.signal_processing import calc_psd


class TransferFunctions(object):
    def __init__(self):
        self.num_loggers = 0
        self.num_locs = 0
        self.num_ss = 0

        # Lists to store logger, location and transfer function names
        self.logger_names = []
        self.loc_names = []
        self.tf_names = []
        # self.logger_names = ["BOP", "LMRP"]
        # self.loc_names = ["LPH Weld", "HPH Weld", "BOP Connector"]

        self.perc_occ = [
            19.040,
            10.134,
            20.049,
            17.022,
            14.644,
            10.374,
            5.448,
            3.289,
        ]

        self.disp_dir = ""
        self.rot_dir = ""
        self.bm_dir = ""
        self.disp_files = []
        self.rot_files = []
        self.bm_files = []
        self.df_disp = pd.DataFrame()
        self.df_rot = pd.DataFrame()
        self.df_bm = pd.DataFrame()
        self.df_acc = pd.DataFrame()

        self.logger_acc_psds = []
        self.loc_bm_psds = []
        self.trans_funcs = []
        self.ave_tfs = []

        self.root_dir = ""
        self.output_folder1 = "Seastate TFs"
        self.output_folder2 = "Weighted Average TFs"

    def get_files(self):
        self.bm_files = glob(self.bm_dir + "/*.csv")
        self.disp_files = glob(self.disp_dir + "/*.csv")
        self.rot_files = glob(self.rot_dir + "/*.csv")

        self.get_number_of_windows()

    def get_number_of_windows(self):
        n1 = len(self.bm_files)
        n2 = len(self.disp_files)
        n3 = len(self.rot_files)

        if n1 == n2 == n3:
            self.num_ss = n1
        else:
            self.num_ss = 0
            print('Warning: Unequal number of window files in each folder')

    def read_fea_time_traces(self):

        self.df_bm = read_seastate_time_traces(self.bm_files)
        self.df_disp = read_seastate_time_traces(self.disp_files)
        self.df_rot = read_seastate_time_traces(self.rot_files)

        self.get_number_of_loggers()
        self.get_number_of_locations()

    def get_number_of_loggers(self):
        n = self.df_disp.shape[1]
        m = self.df_rot.shape[1]

        if n == m:
            if self.num_ss > 0:
                self.num_loggers = n // self.num_ss
            else:
                self.num_loggers = 0
                print('Warning: Number of windows is zero.')
        else:
            print('Warning: Unequal number of columns in logger displacements and logger rotations time traces.')

    def get_number_of_locations(self):
        n = self.df_bm.shape[1]

        if self.num_ss > 0:
            self.num_locs = n // self.num_ss
        else:
            self.num_locs = 0
            print('Warning: Number of windows is zero.')

    def calc_g_cont_accs(self):
        """
        Compute gravity-contaminated acceleration from displacement.
        Use second order central finite difference method to compute acceleration from displacement.
        Then add gravity-contamination contribution.
        acc_g = -[x(i-1) + 2 * x(i) - x(i+1)] / h^2 + g * sin(theta)
        Note: Negative sign added to ensure that a positive displacement and inclination results in a positive
        gravity-contaminated acceleration (sense the logger "feels" force in the oppositve direction to motion).
        """

        # Step size
        h = self.df_disp.index[1] - self.df_disp.index[0]

        # Double differentiate node displacement to acceleration
        acc = -(self.df_disp.shift(1) - 2 * self.df_disp + self.df_disp.shift(-1)) / h ** 2

        # Gravity component from node rotation time series
        g = 9.807
        g_cont = g * np.sin(np.radians(self.df_rot))

        # Acc and g_cont data frames need to have the same column names in order to add data frames together
        cols = []
        for i in range(self.num_ss):
            for j in range(self.num_loggers):
                c = f"Logger {j + 1} Acc-g W{i + 1}"
                cols.append(c)

        acc.columns = cols
        g_cont.columns = cols

        # Combine to get gravity-contaminated acceleration time series
        self.df_acc = acc + g_cont

    def clean_acc_and_bm_dataframes(self):
        """
        Remove nan rows from g-cont accelerations data frame and equivalent rows in BM data frame
        and rebase time index to 0.
        """

        # Store index of nan rows (this will actually be the first and last rows) and remove from df_bm so shape is same
        nan_idx = self.df_acc.index[self.df_acc.isna().any(axis=1)]

        # Drop nan rows from bending moment and acceleration data frames and rescale time index to zero
        self.df_bm.drop(nan_idx, inplace=True)
        self.df_acc.dropna(inplace=True)
        self.df_bm.index = self.df_bm.index - self.df_bm.index[0]
        self.df_acc.index = self.df_acc.index - self.df_acc.index[0]

    def calc_logger_acc_psds(self):
        df = self.df_acc
        fs = 1 / (df.index[1] - df.index[0])
        freq, psds = calc_psd(data=df.T.values, fs=fs, nperseg=1000, noverlap=0)
        freq = np.round(freq, 3)

        # Create list of logger acceleration PSD data frames
        n = self.num_loggers
        self.loc_bm_psds = []

        for i in range(n):
            # Select every logger i row, transpose and construct data frame
            data = psds[i::n].T
            cols = [f"Logger {i + 1} SS{j + 1}" for j in range(self.num_ss)]
            df = pd.DataFrame(data, index=freq, columns=cols)
            self.logger_acc_psds.append(df)

    def calc_location_bm_psds(self):
        df = self.df_bm
        fs = 1 / (df.index[1] - df.index[0])
        freq, psds = calc_psd(data=df.T.values, fs=fs, nperseg=1000, noverlap=0)
        freq = np.round(freq, 3)

        # Create list of locations bending moment PSD data frames
        n = self.num_locs
        self.loc_bm_psds = []

        for i in range(n):
            # Select every location i row, transpose and construct data frame
            data = psds[i::n].T
            cols = [f"Loc {i + 1} SS{j + 1}" for j in range(self.num_ss)]
            df = pd.DataFrame(data, index=freq, columns=cols)
            self.loc_bm_psds.append(df)

    def calc_trans_funcs(self):
        """
        Compute frequency dependent transfer functions.
        TF = [Location BM PSD] / [Logger Acc PSD]
        Transfer functions are stored in 2D lists of form: TF[logger i][location j].
        """

        self.logger_names = []
        self.tf_names = []
        self.trans_funcs = []
        freq = self.loc_bm_psds[0].index

        # Store location names
        self.loc_names = [f"Loc {i + 1}" for i in range(self.num_locs)]

        # Create new TFs list for each logger
        for i in range(self.num_loggers):
            self.trans_funcs.append([])

            # Store logger name
            logger_name = f"Logger {i + 1}"
            self.logger_names.append(logger_name)

            # Append logger i derived TF for each location
            for j in range(self.num_locs):
                data = self.loc_bm_psds[j].values / self.logger_acc_psds[i].values
                cols = [f"{logger_name} {self.loc_names[j]} SS{k + 1}" for k in range(self.num_ss)]
                df = pd.DataFrame(data, index=freq, columns=cols)
                df.index.name = "Freq (Hz)"
                self.trans_funcs[i].append(df)

                # Store full transfer function names
                self.tf_names.extend(cols)

    def calc_weighted_ave_trans_funcs(self):
        """Compute percentage occurrence weighted average transfer functions for all seastates."""

        perc_occ = np.asarray(self.perc_occ)
        n = perc_occ.sum()

        self.ave_tfs = []
        for i in range(self.num_loggers):
            df_ave = pd.DataFrame()

            for j in range(self.num_locs):
                df = self.trans_funcs[i][j].apply(lambda x: perc_occ * x, axis=1).sum(axis=1) / n
                df_ave = pd.concat((df_ave, df), axis=1)

            df_ave.index.name = "Freq (Hz)"
            df_ave.columns = self.loc_names
            self.ave_tfs.append(df_ave)

    def export_seastate_transfer_functions(self, root_dir=""):
        """
        Export transfer functions. Export separate file for all locations per logger, per seastate.
        File columns: Freq, Loc 1, Loc, 2, etc.
        """

        exported = False
        path = os.path.join(root_dir, self.output_folder1)

        # Ensure folder exists
        if os.path.exists(path) is False:
            os.makedirs(path)

        # Export transfer functions files for each location and seastate, for all locations
        for i, logger in enumerate(self.logger_names):
            for j in range(self.num_ss):
                df_ss = pd.DataFrame()

                for k, loc in enumerate(self.loc_names):
                    df_ss = pd.concat((df_ss, self.trans_funcs[i][k].iloc[:, j]), axis=1)

                df_ss.columns = self.loc_names
                df_ss.index.name = "Freq (Hz)"
                filename = f"TF_{'_'.join(logger.split(' '))}_SS{j + 1}.csv"
                df_ss.to_csv(os.path.join(path, filename))
                exported = True

        return exported

    def export_weighted_ave_trans_funcs(self, root_dir=""):
        """
        Export weighted average transfer functions.
        File columns: Freq, Loc 1, Loc, 2, etc.
        """

        exported = False
        path = os.path.join(root_dir, self.output_folder2)

        # Ensure folder exists
        if os.path.exists(path) is False:
            os.makedirs(path)

        for i, logger in enumerate(self.logger_names):
            filename = f"TF_Weighted_Ave_{'_'.join(logger.split(' '))}.csv"
            self.ave_tfs[i].to_csv(os.path.join(path, filename))
            exported = True

        return exported


def read_seastate_time_traces(files):
    df_all = pd.DataFrame()

    for i, f in enumerate(files):
        df = read_2httrace_csv(f)

        # Format and append window number to column names
        df.columns = format_column_names(df.columns, ss_num=i + 1)

        # Join frames
        df_all = pd.concat((df_all, df), axis=1)

    return df_all


def format_column_names(cols, ss_num):
    cols_new = []
    for c in cols:
        # Remove the element _After or _Before suffix if present
        pos = c.find("_After")
        if pos > -1:
            c = c[:pos]
        pos = c.find("_Before")
        if pos > -1:
            c = c[:pos]

        cols_new.append(f"{c.strip()}_W{ss_num}")

    return cols_new


def read_2httrace_csv(filename):
    """Read time series in 2HTTrace csv file output."""

    # Determine header row (row with "TIME" in column 1)
    header_row = get_header_row(filename)

    # Read file and drop wave elevation column
    df = pd.read_csv(filename, header=header_row, index_col=0, skip_blank_lines=False)
    df = df.drop(df.columns[0], axis=1)

    return df


def get_header_row(filename):
    """
    Determine header row of 2HTTrace.csv file.
    Will differ depending on whether user labels are included in 2HTTrace dat file.
    """

    with open(filename, "r") as f:
        for i, line in enumerate(f):
            test_str = line.split(",")[0].strip()

            if test_str.upper() == "TIME":
                return i

    return 0


def find_nearest_window(windows, hs_list, tp_list, hs_i, tp_i):
    """Find the nearest seastate window from the linearised seastates for a given (Hs, Tp) pair."""

    # Ensure working with arrays
    windows = np.asarray(windows)
    hs_list = np.asarray(hs_list)
    tp_list = np.asarray(tp_list)

    # Make window seastate data frame
    df = pd.DataFrame(np.vstack((windows, hs_list, tp_list)).T, columns=["Windows", "Hs", "Tp"])

    # Find nearest Tp
    i = np.abs(df["Tp"] - tp_i).idxmin()
    nearest_tp = df.loc[i, "Tp"]

    # Slice data frame on nearest Tp and find nearest Hs in subset and return window number
    df = df[df["Tp"] == nearest_tp]
    i = np.abs(df["Hs"] - hs_i).idxmin()
    win = df.loc[i, "Windows"]

    return int(win)


if __name__ == "__main__":
    tf = TransferFunctions()
    root = r"C:\Users\dickinsc\PycharmProjects\DataLab\demo_data\3. Transfer Functions"
    tf.bm_dir = os.path.join(root, "Hot Spots BM Z")
    tf.disp_dir = os.path.join(root, "Loggers Disp Y")
    tf.rot_dir = os.path.join(root, "Loggers Rot Z")
    tf.get_files()
    tf.read_fea_time_traces()
    tf.calc_g_cont_accs()
    tf.clean_acc_and_bm_dataframes()
    tf.calc_logger_acc_psds()
    tf.calc_location_bm_psds()
    tf.calc_trans_funcs()
    tf.calc_weighted_ave_trans_funcs()
    tf.export_seastate_transfer_functions()
    tf.export_weighted_ave_trans_funcs()

    # # Test find nearest window
    # windows = [1, 2, 3, 4, 5, 6, 7, 8]
    # hs = [
    #     0.875,
    #     2.625,
    #     1.125,
    #     1.375,
    #     2.625,
    #     1.375,
    #     1.125,
    #     2.125,
    # ]
    # tp = [
    #     6.5,
    #     7.5,
    #     7.5,
    #     8.5,
    #     9.5,
    #     9.5,
    #     11.5,
    #     14.5,
    # ]
    # perc_occ = [
    #     19.040,
    #     10.134,
    #     20.049,
    #     17.022,
    #     14.644,
    #     10.374,
    #     5.448,
    #     3.289,
    # ]
    #
    # hs_i = 2
    # tp_i = 9.5
    # print(f"hs_i = {hs_i} m")
    # print(f"tp_i = {tp_i} s")
    # win = find_nearest_window(windows, hs, tp, hs_i, tp_i)
    # print(f"Window = {win}")
