import pandas as pd
from PyQt5 import QtWidgets


class Seascatter(object):
    def __init__(self):
        self.metocean_logger = ""
        self.hs_col = 0
        self.tp_col = 0

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

    # def save_scatter_diagram(self):
    #     """Export seascatter diagram to Excel."""
    #
    #     if self.seascatterModule.df_scatter.empty:
    #         self.warning("No seascatter diagram generated. Nothing to export!")
    #     else:
    #         filename, _ = QtWidgets.QFileDialog.getSaveFileName(
    #             self, "Save Seascatter Diagram", filter="Excel Files (*.xlsx)"
    #         )
    #         if filename:
    #             self.seascatterModule.export_scatter_diagram(filename)


def calc_seascatter_diagram(df, hs_bins, tp_bins):
    """Create seascatter diagram data frame."""

    # df = pd.DataFrame(np.vstack((hs, tp)).T, columns=['Hs', 'Tp'])
    df.columns = ["Hs", "Tp"]

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
