import sys
import traceback

from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox

from PhotoImporterMainWindow import PhotoImporterMainWindow

def qt_excepthook(exc_type, value, tb):
    """
    Custom exception hook. Initially written to print out uncaught exceptions
    to the terminal, even when QT hides the traceback. Now, it also shows an
    error dialog with the traceback on it as well.
    :param exc_type: Exception type
    :param value: Exception value
    :param tb: Exception traceback
    :return:
    """
    traceback.print_exception(exc_type, value, tb)

    tb_str = "".join(traceback.format_exception(exc_type, value, tb))

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setText(f"An uncaught exception occurred:\n{tb_str}")
    msg.setWindowTitle("Error")
    msg.exec()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = PhotoImporterMainWindow()

    sys.excepthook = qt_excepthook

    window.show()
    sys.exit(app.exec())
