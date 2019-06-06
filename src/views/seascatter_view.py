import math
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from core import calc_seascatter_diagram


class SeascatterDiagram(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(SeascatterDiagram, self).__init__(parent)

        self.parent = parent

        # Hs/Tp and seascatter diagram data frames
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

        # Hs bins
        # self.hs_bins = np.arange(0, 20, 0.25)

        # Tp bins
        # self.tp_bins = np.arange(30)

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        # Bin controls
        self.hsBinSize = QtWidgets.QLineEdit("0.5")
        self.hsBinSize.setFixedWidth(30)
        self.tpBinSize = QtWidgets.QLineEdit("1.0")
        self.tpBinSize.setFixedWidth(30)

        # Apply float validation to input boxes
        dbl_validator = QtGui.QDoubleValidator()
        self.hsBinSize.setValidator(dbl_validator)
        self.tpBinSize.setValidator(dbl_validator)

        # Controls container
        self.container1 = QtWidgets.QWidget()
        self.controlsLayout = QtWidgets.QHBoxLayout(self.container1)
        self.controlsLayout.addWidget(QtWidgets.QLabel("Hs bin size (m):"))
        self.controlsLayout.addWidget(self.hsBinSize)
        self.controlsLayout.addWidget(QtWidgets.QLabel("Tp bin size (s):"))
        self.controlsLayout.addWidget(self.tpBinSize)

        # Seascatter table widget
        self.scatterTable = QtWidgets.QTableWidget(self)
        # fnt = self.scatterTable.font()
        # fnt.setPointSize(7)
        # self.scatterTable.setFont(fnt)

        # Hs, Tp plot widgets
        self.fig, (self.ax1, self.ax2) = plt.subplots(2)
        self.canvas = FigureCanvas(self.fig)

        # Table and plots container
        self.container2 = QtWidgets.QWidget()
        self.scatterLayout = QtWidgets.QHBoxLayout(self.container2)
        self.scatterLayout.addWidget(self.scatterTable, stretch=76)
        self.scatterLayout.addWidget(self.canvas, stretch=24)

        # Main layout
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.container1, alignment=QtCore.Qt.AlignLeft)
        self.layout.addWidget(self.container2)

    def connect_signals(self):
        self.hsBinSize.returnPressed.connect(self.update_hs_bins)
        self.tpBinSize.returnPressed.connect(self.update_tp_bins)

    def update_hs_bins(self):
        """Refresh seascatter diagram for change in Hs bin size."""

        if self.df_ss.empty:
            return

        self.hs_bin_size = float(self.hsBinSize.text())
        self.hs_bins = self.get_bins(self.hs_min, self.hs_max, self.hs_bin_size)
        self.generate_scatter_diagram()

    def update_tp_bins(self):
        """Refresh seascatter diagram for change in Tp bin size."""

        if self.df_ss.empty:
            return

        self.tp_bin_size = float(self.tpBinSize.text())
        self.tp_bins = self.get_bins(self.tp_min, self.tp_max, self.tp_bin_size)
        self.generate_scatter_diagram()

    def get_bins(self, bin_min, bin_max, bin_size):
        """create bins array. If bins size is an integer convert to integer bins."""

        bins = np.arange(bin_min, bin_max + bin_size, bin_size)
        if bin_size.is_integer():
            bins = bins.astype(int)
        return bins

    def get_seascatter_dataset(self, df_vessel):
        """Create Hs/Tp dataset from loaded stats dataset containing mean Hs and Tp values."""

        # Read hs and tp bin sizes in gui
        self.hs_bin_size = float(self.hsBinSize.text())
        self.tp_bin_size = float(self.tpBinSize.text())

        self.df_ss = df_vessel.xs("mean", axis=1, level=1)
        self.df_ss = self.df_ss[["SigWaveHeight", "SigWavePeriod"]]

        # Get Hs/Tp limits
        self.hs_min = math.floor(self.df_ss.min()[0])
        self.tp_min = math.floor(self.df_ss.min()[1])
        self.hs_max = math.ceil(self.df_ss.max()[0])
        self.tp_max = math.ceil(self.df_ss.max()[1])

        # Calculate bins and seascatter diagram
        self.hs_bins = self.get_bins(self.hs_min, self.hs_max, self.hs_bin_size)
        self.tp_bins = self.get_bins(self.tp_min, self.tp_max, self.tp_bin_size)
        self.generate_scatter_diagram()

    def generate_scatter_diagram(self):
        """Create and display seascatter diagram from Hs/Tp data."""

        # Generate seascatter diagram
        self.df_scatter = calc_seascatter_diagram(
            df=self.df_ss, hs_bins=self.hs_bins, tp_bins=self.tp_bins
        )

        # Apply seascatter to table and plot Hs/Tp distributions
        self.set_scatter_table(self.df_scatter)
        self.plot_hs_tp_distribution()

    def set_scatter_table(self, df_scatter):
        """Write seascatter diagram to table widget."""

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

                # Set scaled background colour to seastate values but not the totals
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
        """Plot distribution of Hs and Tp for generated seascatter diagram."""

        # Calculate Hs and Tp bin midpoints (the data frame indexes are interval types)
        hs = self.df_scatter.iloc[:-1, -1]
        hs_mids = []
        for i in hs.index:
            hs_mids.append(i.mid)
        hs.index = hs_mids

        tp = self.df_scatter.iloc[-1, :-1]
        tp_mids = []
        for i in tp.index:
            tp_mids.append(i.mid)
        tp.index = tp_mids

        # Plot Hs distribution
        self.ax1.cla()
        self.ax1.plot(hs)
        self.ax1.set_xlabel("Hs (m)")
        self.ax1.set_ylabel("Percentage Occurrence (%)")

        # Plot Tp distribution
        self.ax2.cla()
        self.ax2.plot(tp)
        self.ax2.set_xlabel("Tp (s)")
        self.ax2.set_ylabel("Percentage Occurrence (%)")

        self.fig.tight_layout()
        self.canvas.draw()

    def export_scatter_diagram(self, filename):
        """Export seastate scatter diagram to Export."""

        writer = pd.ExcelWriter(filename, engine="xlsxwriter")

        # Seastates sheet
        self.df_ss.to_excel(
            writer, sheet_name="Seastates", na_rep="N/A", float_format="%.2f"
        )
        ws = writer.sheets["Seastates"]
        ws.set_column("A:A", 11)
        # wb = writer.book
        # fmt = wb.add_format({'num_format': '0.00'})
        # ws.set_column('B:Y', None, fmt)

        # Seascatter sheet
        # Replace zeros with blanks
        df_scatter = self.df_scatter.replace({0: ""})
        df_scatter.to_excel(
            writer, sheet_name="Seascatter Diagram", float_format="%.2f"
        )
        ws.set_column("A:A", 18)
        writer.save()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = SeascatterDiagram()
    win.show()
    sys.exit(app.exec_())
