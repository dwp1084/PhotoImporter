import sys
from PyQt5 import QtWidgets
from PhotoImporterMainWindow import PhotoImporterMainWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = PhotoImporterMainWindow()
    window.show()
    sys.exit(app.exec())
