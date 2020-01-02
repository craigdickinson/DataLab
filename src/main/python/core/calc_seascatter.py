import numpy as np
import pandas as pd


class Seascatter(object):
    def __init__(self):
        self.metocean_logger = ""
        self.hs_col = 0
        self.tp_col = 0
        self.hs_col_idx = 0
        self.tp_col_idx = 0
        self.df_ss = pd.DataFrame()

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

            # Check if need to remap Hs and Tp columns
            hs_i, tp_i = self._check_column_indexes(df)

            # Select mean Hs and Tp data
            hs = df.iloc[:, hs_i].values
            tp = df.iloc[:, tp_i].values

            # Store seastates as data frame
            self.df_ss = df.iloc[:, [hs_i, tp_i]]
            self.df_ss.columns = ["Hs (m)", "Tp (s)"]
        except IndexError:
            hs = np.array([])
            tp = np.array([])

        return hs, tp

    def _check_column_indexes(self, df):
        """Correct hs-tp column indexes if stats data frame contains both unfiltered and filtered columns."""

        hs_i = self.hs_col_idx
        tp_i = self.tp_col_idx
        cols = df.columns.get_level_values(0)

        # If both unfiltered and filtered stats columns exist, remap to the associated filtered Hs and Tp columns
        if (
            cols[0].endswith("(filtered)") is False
            and cols[1].endswith("(filtered)") is True
        ):
            hs_i = 2 * hs_i + 1
            tp_i = 2 * tp_i + 1

        return hs_i, tp_i


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
