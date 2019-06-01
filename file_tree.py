import os
import sys

from PyQt5.QtCore import QDir, Qt
from PyQt5.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileSystemModel,
    QMainWindow,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)


class FileTree(QWidget):
    def __init__(self, file_type="*.csv"):
        super().__init__()

        # File system model
        pathRoot = QDir.rootPath()
        self.model = QFileSystemModel()
        self.model.setRootPath(pathRoot)
        self.model.setNameFilterDisables(False)

        # Top level of file system
        indexRoot = self.model.index(str(self.model.myComputer()))

        # Tree view widget
        self.treeView = QTreeView()
        self.treeView.setModel(self.model)
        self.treeView.setRootIndex(indexRoot)
        self.treeView.scrollToBottom()

        # Only show the file column
        for i in range(1, 5):
            self.treeView.hideColumn(i)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.treeView)
        self.expand_path(os.getcwd())
        self.setFilters(file_type)
        self.setMinimumWidth(350)

    def expand_path(self, path):
        path_var = path
        folders = [path]
        while 1:
            path_var, folder = os.path.split(path_var)
            if folder != "":
                folders.append(path_var)
            else:
                break

        folders.reverse()
        for item in folders:
            self.treeView.scrollTo(self.model.index(item))

    def setFilters(self, file_type):
        self.model.setNameFilters([file_type])


class FileTreeWidget(QMainWindow):
    def __init__(self, parent=None):
        super(FileTreeWidget, self).__init__(parent)

        button1 = QPushButton()
        button1.setText("Show/Hide Tree")
        self.setCentralWidget(button1)
        self.tree = FileTree()

        self.dock1 = QDockWidget("Docked File Tree")
        self.dock1.setWidget(self.tree)
        self.dock1.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock1)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    gui = FileTreeWidget()
    gui.resize(600, 300)

    gui.show()
    sys.exit(app.exec_())
