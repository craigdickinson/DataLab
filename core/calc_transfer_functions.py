import pandas as pd
import numpy as np


class TransferFunctions:
    def __init__(self):
        pass

    def read_2httrace_csv(self, filename):
        """Read time series in 2HTTrace csv file output."""

        df = pd.read_csv(filename, header=3, index_col=0)

        # Drop wave elevation column
        df = df.drop(df.columns[0], axis=1)

        return df

    def calc_gravity_corrected_accelerations(self):
        pass

    def calc_tf(self):
        pass


if __name__ == '__main__':
    import os

    fpath = r'C:\Users\dickinsc\PycharmProjects\_2. DataLab Analysis Files\21239\Transfer Functions\Hot Spots BM Z'
    fname = '01_Glendronach_W1D_tt.csv'
    fpath = os.path.join(fpath, fname)

    tf = TransferFunctions()
    df = tf.read_2httrace_csv(fpath)
    print(df.head())
