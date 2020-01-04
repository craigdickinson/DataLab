"""Sea scatter dashboard gui view."""

__author__ = "Craig Dickinson"

import math
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from core.calc_seascatter import calc_seascatter_diagram


class SeascatterDiagram(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(SeascatterDiagram, self).__init__(parent)

        self.parent = parent

        # Hs and Tp arrays
        self.hs = np.array([])
        self.tp = np.array([])

        # Seastate and seascatter diagram data frames
        self.df_ss = pd.DataFrame()
        self.df_scatter = pd.DataFrame()

        # Hs/Tp bins limits
        self.hs_min = 0
        self.tp_min = 0
        self.hs_max = 0
        self.tp_max = 0

        # Hs/Tp bin sizes
        self.hs_bin_size = 0
        self.tp_bin_size = 0

        # Hs/Tp bins
        self.hs_bins = np.array([])
        self.tp_bins = np.array([])

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        # Define input box validator
        dbl_validator = QtGui.QDoubleValidator()

        # WIDGETS
        # Bin controls
        self.hsBinSize = QtWidgets.QLineEdit("0.5")
        self.hsBinSize.setFixedWidth(30)
        self.hsBinSize.setValidator(dbl_validator)
        self.tpBinSize = QtWidgets.QLineEdit("1.0")
        self.tpBinSize.setFixedWidth(30)
        self.tpBinSize.setValidator(dbl_validator)

        # Seascatter table widget
        self.scatterTable = QtWidgets.QTableWidget(self)
        # fnt = self.scatterTable.font()
        # fnt.setPointSize(7)
        # self.scatterTable.setFont(fnt)

        # Hs, Tp plot widgets
        self.fig, (self.ax1, self.ax2) = plt.subplots(2)
        self.canvas = FigureCanvas(self.fig)

        # CONTAINERS
        # Controls container
        self.controlsLayout = QtWidgets.QHBoxLayout()
        self.controlsLayout.addWidget(QtWidgets.QLabel("Hs bin size (m):"))
        self.controlsLayout.addWidget(self.hsBinSize)
        self.controlsLayout.addWidget(QtWidgets.QLabel("Tp bin size (s):"))
        self.controlsLayout.addWidget(self.tpBinSize)
        self.controlsLayout.addStretch()

        # Splitter to allow resizing of widget containers
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self.scatterTable)
        splitter.addWidget(self.canvas)
        splitter.setSizes([1000, 350])

        # LAYOUT
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addLayout(self.controlsLayout)
        self.layout.addWidget(splitter)

    def connect_signals(self):
        self.hsBinSize.returnPressed.connect(self.on_hs_bins_updated)
        self.tpBinSize.returnPressed.connect(self.on_tp_bins_updated)

    def on_hs_bins_updated(self):
        """Refresh seascatter diagram for change in Hs bin size."""

        if self.hs_bins.size == 0:
            return

        self.hs_bin_size = float(self.hsBinSize.text())
        self.hs_bins = self.get_bins(self.hs_min, self.hs_max, self.hs_bin_size)
        self.generate_scatter_diagram()

    def on_tp_bins_updated(self):
        """Refresh seascatter diagram for change in Tp bin size."""

        if self.tp_bins.size == 0:
            return

        self.tp_bin_size = float(self.tpBinSize.text())
        self.tp_bins = self.get_bins(self.tp_min, self.tp_max, self.tp_bin_size)
        self.generate_scatter_diagram()

    @staticmethod
    def get_bins(bin_min, bin_max, bin_size):
        """create bins array. If bins size is an integer convert to integer bins."""

        bins = np.arange(bin_min, bin_max + bin_size, bin_size)
        if bin_size.is_integer():
            bins = bins.astype(int)
        return bins

    def calc_bins(self, hs, tp):
        """Calculate Hs/Tp bins from loaded stats dataset containing mean Hs and Tp values."""

        self.hs = hs
        self.tp = tp

        # Read hs and tp bin sizes in gui
        self.hs_bin_size = float(self.hsBinSize.text())
        self.tp_bin_size = float(self.tpBinSize.text())

        # Get Hs/Tp limits
        self.hs_min = math.floor(np.nanmin(hs))
        self.hs_max = math.ceil(np.nanmax(hs))
        self.tp_min = math.floor(np.nanmin(tp))
        self.tp_max = math.ceil(np.nanmax(tp))

        # Calculate hs/tp bins
        self.hs_bins = self.get_bins(self.hs_min, self.hs_max, self.hs_bin_size)
        self.tp_bins = self.get_bins(self.tp_min, self.tp_max, self.tp_bin_size)

    def generate_scatter_diagram(self):
        """Create and display seascatter diagram from Hs/Tp data."""

        # Generate seascatter diagram
        self.df_scatter = calc_seascatter_diagram(
            self.hs, self.tp, self.hs_bins, self.tp_bins
        )

        # Apply sea scatter to table and plot Hs/Tp distributions
        self.set_scatter_table(self.df_scatter)
        self.plot_hs_tp_distribution()

    def set_scatter_table(self, df_scatter):
        """Write sea scatter diagram to table widget."""

        self.scatterTable.setRowCount(df_scatter.shape[0])
        self.scatterTable.setColumnCount(df_scatter.shape[1])

        # Get maximum percentage occurrence to scale colours
        max_val = df_scatter.iloc[:-1, :-1].values.max()

        # Write percentage occurrence values to table
        for i in range(len(df_scatter.index)):
            for j in range(len(df_scatter.columns)):
                val = df_scatter.iat[i, j]
                frac = val / max_val
                if val == 0:
                    val = ""
                else:
                    val = f"{val:.2f}"

                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(QtCore.Qt.AlignCenter)

                # Apply scaled background colour to sea state values but not the totals
                if (i < len(df_scatter.index) - 1) & (j < len(df_scatter.columns) - 1):
                    item.setBackground(QtGui.QColor(0, 0, 255, 255 * frac))

                self.scatterTable.setItem(i, j, item)

        # Convert index and header to strings to be able to write table
        tp_intervals = [str(col) for col in df_scatter.columns.tolist()]
        hs_intervals = [str(idx) for idx in df_scatter.index.tolist()]
        self.scatterTable.setHorizontalHeaderLabels(tp_intervals)
        self.scatterTable.setVerticalHeaderLabels(hs_intervals)
        self.scatterTable.resizeColumnsToContents()
        self.scatterTable.resizeRowsToContents()
        self.scatterTable.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)

    def plot_hs_tp_distribution(self):
        """Plot distribution of Hs and Tp for generated sea scatter diagram."""

        # Calculate Hs and Tp bin midpoints (the data frame indexes are interval types)
        hs = self.df_scatter.iloc[:-1, -1]
        hs.index = [i.mid for i in hs.index]
        tp = self.df_scatter.iloc[-1, :-1]
        tp.index = [i.mid for i in tp.index]

        # Plot Hs distribution
        self.ax1.cla()
        self.ax1.bar(hs.index, hs.values, width=self.hs_bin_size)
        self.ax1.plot(hs, "r")
        self.ax1.set_xlabel("Hs (m)")
        self.ax1.set_ylabel("Percentage Occurrence (%)")

        # Plot Tp distribution
        self.ax2.cla()
        self.ax2.bar(tp.index, tp.values, width=self.tp_bin_size)
        self.ax2.plot(tp, "r", marker="x")
        self.ax2.set_xlabel("Tp (s)")
        self.ax2.set_ylabel("Percentage Occurrence (%)")

        # For some reason need to do tight layout and draw twice to make sure plot is sized correctly
        self.fig.tight_layout()
        self.canvas.draw()
        self.fig.tight_layout()
        self.canvas.draw()

    def export_scatter_diagram(self, filename):
        """Export sea state scatter diagram to Excel."""

        writer = pd.ExcelWriter(filename, engine="xlsxwriter")

        # Seastates sheet
        self.df_ss.to_excel(
            writer, sheet_name="Sea States", na_rep="N/A", float_format="%.2f"
        )
        ws = writer.sheets["Sea States"]
        ws.set_column("A:A", 11)
        # wb = writer.book
        # fmt = wb.add_format({'num_format': '0.00'})
        # ws.set_column('B:Y', None, fmt)

        # Seascatter sheet
        # Replace zeros with blanks
        df_scatter = self.df_scatter.replace({0: ""})
        df_scatter.to_excel(
            writer, sheet_name="Sea Scatter Diagram", float_format="%.2f"
        )
        ws.set_column("A:A", 18)
        writer.save()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = SeascatterDiagram()
    win.show()
    sys.exit(app.exec_())
