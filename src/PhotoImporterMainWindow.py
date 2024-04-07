from PyQt5 import QtWidgets
from PyQt5.QtCore import QDateTime, QSize, QSettings

from ui.ui_PhotoImporterMainWindow import Ui_PhotoImporterMainWindow


class PhotoImporterMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_PhotoImporterMainWindow()
        self.ui.setupUi(self)

        self.settings = QSettings()
        self.loadSettings()

        # Hide panels on startup
        self.ui.separator.setVisible(False)
        self.ui.ProgressWidget.setVisible(False)

        if not self.ui.jpegCheckBox.isChecked():
            self.ui.JpegLocationWidget.setVisible(False)

        if not self.ui.rawCheckBox.isChecked():
            self.ui.RawLocationWidget.setVisible(False)

        self.ui.projectDateEdit.setDate(QDateTime.currentDateTime().date())

        # Resize window to minimum height, but keep the same width
        newSize = QSize(self.width(), self.minimumHeight())
        self.resize(newSize)

    def loadSettings(self):
        pass
