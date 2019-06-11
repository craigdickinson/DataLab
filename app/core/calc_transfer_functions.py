import csv
import pandas as pd
import numpy as np
import os
from glob import glob


class TransferFunctions(object):
    def __init__(self):
        self.num_loggers = 2
        self.num_locs = 3
        self.num_win = 8
        self.logger_names = ["BOP", "LMRP"]
        self.loc_names = ["LPH Weld", "HPH Weld", "BOP Connector"]
        self.bm_dir = ""
        self.disp_dir = ""
        self.rot_dir = ""
        self.bm_files = []
        self.disp_files = []
        self.rot_files = []
        self.df_bm = pd.DataFrame()
        self.df_disp = pd.DataFrame()
        self.df_rot = pd.DataFrame()
        self.df_acc = pd.DataFrame()

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
            self.num_win = n1
        else:
            self.num_win = 0
            print('Warning: Unequal number of window files in each folder')

    def read_fea_time_traces(self):

        self.df_bm = read_all_windows(self.bm_files)
        self.df_disp = read_all_windows(self.disp_files)
        self.df_rot = read_all_windows(self.rot_files)

        self.get_number_of_loggers()
        self.get_number_of_locations()

    def get_number_of_loggers(self):
        n = self.df_disp.shape[1]
        m = self.df_rot.shape[1]

        if n == m:
            if self.num_win > 0:
                self.num_loggers = n // self.num_win
            else:
                self.num_loggers = 0
                print('Warning: Number of windows is zero.')
        else:
            print('Warning: Unequal number of columns in logger displacements and logger rotations time traces.')

    def get_number_of_locations(self):
        n = self.df_bm.shape[1]

        if self.num_win > 0:
            self.num_locs = n // self.num_win
        else:
            self.num_locs = 0
            print('Warning: Number of windows is zero.')

    def calc_g_cont_accs(self, df_disp, df_rot):
        """
        Compute gravity-contaminated acceleration from displacement.
        Use second order central finite difference method to compute acceleration from displacement.
        Then add gravity-contamination contribution.
        acc_g = -[x(i-1) + 2 * x(i) - x(i+1)] / h^2 + g * sin(theta)
        Note: Negative sign added to ensure that a positive displacement and inclination results in a positive
        gravity-contaminated acceleration (sense the logger "feels" force in the oppositve direction to motion).
        """

        # Step size
        h = df_disp.index[1] - df_disp.index[0]

        # Double differentiate node displacement to acceleration
        acc = -(df_disp.shift(1) - 2 * df_disp + df_disp.shift(-1)) / h ** 2

        # Gravity component from node rotation time series
        g = 9.807
        g_cont = g * np.sin(np.radians(df_rot))

        # Need to rename columns so identical in order to add data frames
        n = self.num_loggers * self.num_win

        cols = []
        for i in range(self.num_win):
            for j in range(self.num_loggers):
                c = f"Logger {j + 1} Acc-g W{i + 1}"
                cols.append(c)

        acc.columns = cols
        g_cont.columns = cols

        # Combine to get gravity-contaminated acceleration time series
        self.df_acc = acc + g_cont

        # Finally drop NAN rows and rescale time index to zero
        self.df_acc = self.df_acc.dropna()
        self.df_acc.index = self.df_acc.index - self.df_acc.index[0]

    def calc_acc_psd(self):
        pass

    def calc_bm_psd(self):
        pass

    def calc_tf(self):
        pass


def read_all_windows(files):
    df_all = pd.DataFrame()

    for i, f in enumerate(files):
        df = read_2httrace_csv(f)

        # Format column names
        cols = df.columns

        # Format and append window number to column names
        df.columns = format_column_names(cols, win_num=i + 1)

        # Join frames
        df_all = pd.concat((df_all, df), axis=1)

    return df_all


def format_column_names(cols, win_num):
    cols_new = []
    for c in cols:
        # Remove the element _After or _Before suffix if present
        pos = c.find("_After")
        if pos > -1:
            c = c[:pos]
        pos = c.find("_Before")
        if pos > -1:
            c = c[:pos]

        cols_new.append(f"{c.strip()}_W{win_num}")

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
    Will differ depending on whetehr user labels included in DAT file.
    """

    with open(filename, "r") as f:
        for i, line in enumerate(f):
            test_str = line.split(",")[0].strip()

            if test_str.upper() == "TIME":
                return i

    return 0

    #     reader = csv.reader(f)
    #     data = [r for r in reader]
    #
    # for i, r in enumerate(data):


if __name__ == "__main__":
    tf = TransferFunctions()

    root = r"C:\Users\dickinsc\PycharmProjects\DataLab\demo_data\3. Transfer Functions"
    tf.bm_dir = os.path.join(root, "Hot Spots BM Z")
    tf.disp_dir = os.path.join(root, "Loggers Disp Y")
    tf.rot_dir = os.path.join(root, "Loggers Rot Z")
    tf.get_files()

    tf.read_fea_time_traces()

    tf.calc_g_cont_accs(tf.df_disp, tf.df_rot)
    print(tf.df_acc)
