from os import listdir
from os.path import exists, join, isdir
from pathlib import Path
from string import ascii_uppercase as drive_letters

from PyQt5 import QtWidgets
from PyQt5.QtCore import QDateTime, QSize, QSettings, pyqtSlot, QStandardPaths, Qt

from constants import ROOT_NAME, DRIVE_LETTER_NAME, EDITED_LOC_NAME, JPEG_LOC_NAME, RAW_LOC_NAME
from PhotoImporter import PhotoImporter
from ui.ui_PhotoImporterMainWindow import Ui_PhotoImporterMainWindow


class PhotoImporterMainWindow(QtWidgets.QMainWindow):
    """
    Main window GUI component of the Photo Importer tool.
    """

    photoImporter = PhotoImporter()
    operationsToPerform = 0
    operationsCompleted = 0

    def __init__(self) -> None:
        super().__init__()
        self.ui = Ui_PhotoImporterMainWindow()
        self.ui.setupUi(self)

        # Constants
        self.subdirectoryBoxes = {
            self.ui.editedLocationComboBox: EDITED_LOC_NAME,
            self.ui.jpegLocationComboBox: JPEG_LOC_NAME,
            self.ui.rawLocationComboBox: RAW_LOC_NAME
        }

        appConfig = (QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation) + "/PhotoImporter/config.ini")

        self.settings = QSettings(appConfig, QSettings.IniFormat)
        self.loadSettings()

        self.ui.menuSettings.setToolTipsVisible(True)
        self.ui.menuImport.setToolTipsVisible(True)

        # Hide panels on startup
        self.ui.CurrentFileProgressBarWidget.setVisible(False)
        self.ui.separator.setVisible(False)
        self.ui.ProgressWidget.setVisible(False)
        self.ui.errorLabel.setVisible(False)

        self.ui.projectDateEdit.setDate(QDateTime.currentDateTime().date())

        # Resize window to minimum height, but keep the same width
        newSize = QSize(self.width(), self.minimumHeight())
        self.resize(newSize)

        # Signals
        self.ui.actionJPEG.changed.connect(
            lambda: self.toggleImportWidgetVisibility(self.ui.actionJPEG, self.ui.JpegLocationWidget)
        )
        self.ui.actionRAW.changed.connect(
            lambda: self.toggleImportWidgetVisibility(self.ui.actionRAW, self.ui.RawLocationWidget)
        )
        self.ui.selectRootDirectoryButton.clicked.connect(self.searchForFolder)
        self.ui.actionRefresh.triggered.connect(lambda: self.refresh(self.ui.rootDirectoryPathEdit.text()))
        self.comboBoxSetToSetting(self.ui.jpegLocationComboBox, JPEG_LOC_NAME)
        self.comboBoxSetToSetting(self.ui.rawLocationComboBox, RAW_LOC_NAME)
        self.comboBoxSetToSetting(self.ui.editedLocationComboBox, EDITED_LOC_NAME)
        self.comboBoxSetToSetting(self.ui.sdCardRootComboBox, DRIVE_LETTER_NAME)
        self.ui.importButton.clicked.connect(self.importPhotos)
        self.photoImporter.importing.connect(self.importing)
        self.photoImporter.updateNumberOfOperations.connect(self.setNumberOfOperations)
        self.photoImporter.completedOperation.connect(self.updateProgress)
        self.photoImporter.statusMessage.connect(self.setStatusMessage)
        self.photoImporter.importComplete.connect(self.importComplete)

    @pyqtSlot()
    def searchForFolder(self) -> None:
        """
        The searchForFolder function is a function that allows the user to search for a folder. It opens up a file
        dialog box and allows the user to select any folder they want. The starting directory of this file dialog box is
        set by default as the home directory, but if there was already an existing root path saved in settings, then it
        will start at that location instead.

        :doc-author: Trelent
        """
        startingDirectory = str(Path.home())
        if self.settings.value(ROOT_NAME):
            startingDirectory = self.settings.value(ROOT_NAME)
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Open Folder", startingDirectory)
        if path != "":
            self.ui.rootDirectoryPathEdit.setText(path)
            self.refresh(path)

    @pyqtSlot()
    def importing(self) -> None:
        """
        The importing function is called when the user clicks on the Import button. It sets up a progress bar and
        disables all other widgets in order to prevent the user from changing any settings while importing is taking
        place. It also sets up a busy cursor so that the user knows that something is happening.

        :doc-author: Trelent
        """
        self.ui.separator.setVisible(True)
        self.ui.ProgressWidget.setVisible(True)
        self.ui.OptionsWidget.setEnabled(False)
        self.ui.menubar.setEnabled(False)
        self.ui.errorLabel.setVisible(False)
        QtWidgets.QApplication.setOverrideCursor(Qt.BusyCursor)

    @pyqtSlot()
    def importComplete(self) -> None:
        """
        The importComplete function is called when the import process has completed. It resets the program to its
        default state after an import is complete.

        :doc-author: Trelent
        """
        self.ui.OptionsWidget.setEnabled(True)
        self.ui.menubar.setEnabled(True)
        QtWidgets.QApplication.restoreOverrideCursor()
        self.operationsToPerform = 0
        self.operationsCompleted = 0

    @pyqtSlot()
    def importPhotos(self) -> None:
        """
        The importPhotos function is called when the user clicks on the "Import" button. It first checks to see if a
        project name has been entered, and if not, displays an error message. If a project name has been entered, it
        then gets all the information from the GUI that is needed for importing photos.

        :doc-author: Trelent
        """
        if self.ui.projectNameEdit.text() == "":
            self.error("Please enter a project name.")
            return

        sdCardRoot = self.ui.sdCardRootComboBox.currentText()
        currentRootDir = self.ui.rootDirectoryPathEdit.text()
        editedPhotosDir = join(currentRootDir, self.ui.editedLocationComboBox.currentText())
        jpegPhotosDir = None
        rawPhotosDir = None
        if self.ui.actionJPEG.isChecked():
            jpegPhotosDir = join(currentRootDir, self.ui.jpegLocationComboBox.currentText())
        if self.ui.actionRAW.isChecked():
            rawPhotosDir = join(currentRootDir, self.ui.rawLocationComboBox.currentText())

        try:
            self.photoImporter.validate(sdCardRoot, editedPhotosDir, jpegPhotosDir, rawPhotosDir)
        except OSError as ose:
            self.error(str(ose))
        else:
            self.photoImporter.importPhotos(
                self.ui.projectDateEdit.date().toPyDate(),
                self.ui.projectNameEdit.text()
            )

    @pyqtSlot(int)
    def setNumberOfOperations(self, numberOfOperations: int) -> None:
        """
        The setNumberOfOperations function sets the number of operations to perform, which is used to calculate the
        percentage shown in the progress bar.

        :param numberOfOperations: Number of operations to perform
        :doc-author: Trelent
        """
        self.operationsToPerform = numberOfOperations

    @pyqtSlot()
    def updateProgress(self) -> None:
        """
        The updateProgress function is called every time an operation in the PhotoImporter is completed. It increments
        the operationsCompleted variable by 1, and then sets the totalProgressBar's value to be equal to the percentage
        of operations that have been completed (operationsCompleted / operationsToPerform * 100). This allows for a
        progress bar to be displayed.

        :doc-author: Trelent
        """
        self.operationsCompleted += 1
        self.ui.totalProgressBar.setValue(int(self.operationsCompleted / self.operationsToPerform * 100))

    @pyqtSlot(str)
    def setStatusMessage(self, message: str) -> None:
        """
        The setStatusMessage function is a function that sets the status message in the GUI.

        :param message: Text of the currentActionMessage label
        :doc-author: Trelent
        """
        self.ui.currentActionMessage.setText(message)
    
    def comboBoxSetToSetting(self, comboBox: QtWidgets.QComboBox, settingsKey: str) -> None:
        """
        The comboBoxSetToSetting function is a helper function that connects the currentTextChanged signal of a
        QComboBox to the setValue method of a QSettings object. This allows us to save the text in our combo box to our
        settings file, so that we can restore it later.

        :param comboBox: Combo box that is being connected
        :param settingsKey: Key that is used in the settings file
        :doc-author: Trelent
        """
        comboBox.currentTextChanged.connect(
            lambda txt: self.settings.setValue(settingsKey, txt)
        )

    def loadSettings(self) -> None:
        """
        The loadSettings function is called when the program starts. It loads the settings from the settings and sets
        them to their appropriate widgets. If there are no saved settings, it does nothing.

        :doc-author: Trelent
        """
        if self.settings.value(ROOT_NAME):
            self.ui.rootDirectoryPathEdit.setText(self.settings.value(ROOT_NAME))
            self.updateSubdirectories()

        self.updateDriveLetters()

    def toggleImportWidgetVisibility(self, action: QtWidgets.QAction, widget: QtWidgets.QWidget) -> None:
        """
        The toggleImportWidgetVisibility function is a function that toggles the visibility of the import widget. It
        also ensures that at least one value is always checked.

        :param action: Action from the menu bar
        :param widget: Widget connected to the action
        :doc-author: Trelent
        """
        widget.setVisible(action.isChecked())

        # At least one value must always be checked
        if not (self.ui.actionRAW.isChecked() or self.ui.actionJPEG.isChecked()):
            if action == self.ui.actionRAW:
                self.ui.actionJPEG.toggle()
            else:
                self.ui.actionRAW.toggle()

    def refresh(self, pathName: str) -> None:
        """
        The refresh function is called when the user clicks on the refresh menu action. It checks if the path exists and
        then updates all the subdirectories, drive letters, and progress bars.

        :param pathName: User-entered path
        :doc-author: Trelent
        """
        if not (exists(pathName) or isdir(pathName)):
            self.error(f"Root path \"{pathName}\" could not be found.")
            return
        self.ui.errorLabel.setVisible(False)
        self.settings.setValue(ROOT_NAME, pathName.strip())
        self.updateSubdirectories()
        self.updateDriveLetters()
        self.ui.ProgressWidget.setVisible(False)
        self.ui.separator.setVisible(False)
        self.ui.totalProgressBar.setValue(0)
        self.ui.currentActionMessage.setText("")

    def updateSubdirectories(self) -> None:
        """
        The updateSubdirectories function is called when settings are loaded or the program is refreshed. It updates all
        the subdirectory combo boxes to reflect the new directories in the root directory. It also sets each combo box
        to its corresponding setting, if it exists.

        :doc-author: Trelent
        """
        rootPath = self.settings.value(ROOT_NAME)
        paths = [x for x in listdir(rootPath) if isdir(join(rootPath, x))]
        for comboBox in self.subdirectoryBoxes:
            try:
                comboBox.disconnect()
            except TypeError:
                pass
            comboBox.clear()
            comboBox.addItems(paths)
            self.comboBoxSetToSetting(comboBox, self.subdirectoryBoxes[comboBox])

        if self.settings.value(EDITED_LOC_NAME):
            self.setComboBoxFromSetting(self.ui.editedLocationComboBox, self.settings.value(EDITED_LOC_NAME))

        if self.settings.value(JPEG_LOC_NAME):
            self.setComboBoxFromSetting(self.ui.jpegLocationComboBox, self.settings.value(JPEG_LOC_NAME))

        if self.settings.value(RAW_LOC_NAME):
            self.setComboBoxFromSetting(self.ui.rawLocationComboBox, self.settings.value(RAW_LOC_NAME))

    def error(self, text: str) -> None:
        """
        The error function takes a string as an argument and sets the errorLabel to that text. It then makes the
        errorLabel visible.

        :param text: Error label text.
        :doc-author: Trelent
        """
        self.ui.errorLabel.setText(text)
        self.ui.errorLabel.setVisible(True)
        
    def updateDriveLetters(self) -> None:
        """
        Gets a list of all drive letters that are available, then adds those values to the SD card root combo box.
        NOTE: This function currently only works on Windows systems. This also does not work for NTFS-mounted drives.
        """
        drives = [f"{d}:" for d in drive_letters if exists(f"{d}:")]
        try:
            self.ui.sdCardRootComboBox.disconnect()
        except TypeError:
            pass
        self.ui.sdCardRootComboBox.clear()
        self.ui.sdCardRootComboBox.addItems(drives)
        self.comboBoxSetToSetting(self.ui.sdCardRootComboBox, DRIVE_LETTER_NAME)

        if self.settings.value(DRIVE_LETTER_NAME):
            self.setComboBoxFromSetting(self.ui.sdCardRootComboBox, self.settings.value(DRIVE_LETTER_NAME))

    @staticmethod
    def setComboBoxFromSetting(comboBox: QtWidgets.QComboBox, setting: str) -> None:
        """
        The setComboBoxFromSetting function takes a QComboBox and a string as arguments. It then searches the combo box
        for the text of the string, and if it finds it, sets that item to be selected.

        :param comboBox: Combo box that's being modified
        :param setting: Text that is being searched for in the combo box
        :doc-author: Trelent
        """
        index = comboBox.findText(setting)
        if index > -1:
            comboBox.setCurrentIndex(index)
