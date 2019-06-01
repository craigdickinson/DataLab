import sys

import numpy as np
from PyQt5.QtWidgets import QApplication, QGridLayout, QWidget
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from scipy import signal


class FFTWidget(QWidget):
    """FFT plot widget class."""

    def __init__(self):
        super().__init__()

        plt.style.use("seaborn")

        # Grid layout
        grid = QGridLayout(self)

        # Figure and axes
        self.fig, self.ax = plt.subplots(1)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.draw()

        grid.addWidget(self.canvas)

    def plot_fft(self, df):
        """Plot FFT."""

        # Calculate frequency
        N = len(df.index)
        d = 0.1
        freq = np.fft.rfftfreq(N, d)

        # Calculate FFT amplitudes for 4 channels
        # amps = [np.abs(np.fft.rfft(df[col])) / N for col in df.columns[1:5]]
        # amps = [np.concatenate([[A[0]], 2 * A[1:-1], [A[-1]]]) for A in amps]

        amps = np.abs(np.fft.rfft(df[df.columns[1]])) / N
        amps[1:-1] *= 2

        # Do not plot 0 Hz which is the mean amplitude
        ax = self.ax[0]
        ax.clear()
        ax.plot(freq[1:], amps[1:], color="b", linewidth=0.2)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Amplitude ($\mathregular{m^2}$)")
        ax.set_title("FFT")
        ax.set_xlim(0, 1)

        self.fig.tight_layout()
        self.canvas.draw()

    def plot_psd(self, df):
        """Plot PSD."""

        # Calculate frequency
        N = len(df.index)
        d = 0.1
        fs = 10
        freq = np.fft.rfftfreq(N, d)[1:]

        # Calculate FFT amplitudes for 4 channels
        # amps = [np.abs(np.fft.rfft(df[col])) ** 2 / (fs * N) for col in df.columns[1:5]]
        # amps = [np.concatenate([[A[0]], 2 * A[1:-1], [A[-1]]]) for A in amps]

        amps = abs(np.fft.rfft(df[df.columns[1]])) ** 2 / (fs * N)
        amps = amps[1:]
        amps[:-1] *= 2

        # Do not plot 0 Hz which is the mean amplitude
        # ax = self.ax[0]
        ax = self.ax
        ax.clear()
        ax.plot(freq, amps, color="r")  # , linewidth=0.2)
        # ax.plot(freq[1:], np.log10(amps[1:]), color='b')  # , linewidth=0.2)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("PSD ($\mathregular{(m/s^2)^2/Hz}$)")
        ax.set_title("Power Spectral Density")
        # ax.set_xlim(0, 1)
        self.ax.margins(x=0, y=0)
        self.ax.set_yscale("log")

        # self.fig.tight_layout()
        self.canvas.draw()

    def calc_psd(df, col, n):
        """Calculate PSD."""

        # Number of samples
        N = len(df)
        s = int(N / n)

        # Time resolution and sampling frequency
        d = (df.index - df.index[0]).total_seconds()[1]
        fs = 1 / d

        for i in range(int(n)):
            t1 = i * s
            t2 = t1 + s
            dfi = df[t1:t2]
            N = len(dfi)

            # PSD of sample
            psdi = abs(np.fft.rfft(dfi[col])) ** 2 / (fs * N)
            psdi = psdi[1:]
            psdi[:-1] *= 2

            # Cumulative PSD
            if i == 0:
                psd = psdi
            else:
                psd += psdi

        # Average PSD
        psd = psd / int(n)

        # Spectral frequencies
        freq = np.fft.rfftfreq(N, d)[1:]

        return freq, psd

    def plot_periodogram(self, df, fs):
        """Plot FFT."""

        x = df[df.columns[1]]
        f, pxx = signal.welch(x, fs)

        ax = self.ax
        ax.clear()
        ax.plot(f, pxx, color="y", linewidth=0.2)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("PSD ($\mathregular{(m^2)^2/Hz}$)")
        ax.set_title("Periodogram")
        ax.set_xlim(0, 1)

        self.fig.tight_layout()
        self.canvas.draw()


# For testing layout
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = FFTWidget()
    w.show()
    sys.exit(app.exec_())
