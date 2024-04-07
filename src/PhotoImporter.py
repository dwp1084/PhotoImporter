import sys

from PyQt5 import QtWidgets
from PyQt5.QtCore import QDateTime, QSize

from ui.ui_PhotoImporterMainWindow import Ui_PhotoImporterMainWindow


class PhotoImporterMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_PhotoImporterMainWindow()
        self.ui.setupUi(self)

        self.ui.separator.setVisible(False)
        self.ui.ProgressWidget.setVisible(False)

        self.ui.projectDateEdit.setDate(QDateTime.currentDateTime().date())

        newSize = QSize(self.width(), self.minimumHeight())
        self.resize(newSize)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = PhotoImporterMainWindow()
    window.show()
    sys.exit(app.exec())
