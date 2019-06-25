import numpy as np
import pandas as pd
from PyQt5 import QtWidgets


class Seascatter(object):
    def __init__(self):
        self.metocean_logger = ""
        self.hs_col = 0
        self.tp_col = 0
        self.hs_col_idx = 0
        self.tp_col_idx = 0

    def check_metocean_dataset_loaded(self, datasets):
        """
        Check whether a vessel stats file has been loaded.
        This dataset will be titled "VESSEL".
        If found return dataset, otherwise false.
        """

        for dataset in datasets:
            if dataset.logger_id.upper() == self.metocean_logger.upper():
                return dataset.df
        return False

    def get_hs_tp_data(self, df):
        """Retrieve mean Hs and Tp columns from data frame."""

        try:
            # Select the mean stats
            df = df.xs("mean", axis=1, level=1)

            # TODO: This won't be correct if both unfiltered and filtered stats exist in data frame!
            hs = df.iloc[:, self.hs_col_idx].values
            tp = df.iloc[:, self.tp_col_idx].values
        except:
            hs = np.array([])
            tp = np.array([])

        return hs, tp


def calc_seascatter_diagram(hs, tp, hs_bins, tp_bins):
    """Create sea scatter diagram data frame."""

    df = pd.DataFrame(np.vstack((hs, tp)).T, columns=["Hs", "Tp"])

    # Drop events that are nan
    df_nan = df[df["Hs"].isnull() & df["Tp"].isnull()]
    df = df.drop(df_nan.index)

    a = pd.cut(df["Hs"], hs_bins)
    b = pd.cut(df["Tp"], tp_bins)

    # Need to convert bins to object type to prevent type error with crosstab
    a = a.astype("object")
    b = b.astype("object")

    scatter = pd.crosstab(index=a, columns=b, normalize=True) * 100
    scatter = scatter.apply(pd.to_numeric)

    # Need to convert index and column axes from categorical to object type to allow summation
    scatter.index = scatter.index.astype("object")
    scatter.columns = scatter.columns.astype("object")
    scatter["All"] = scatter.sum(axis=1)
    scatter.loc["All"] = scatter.sum()

    return scatter
