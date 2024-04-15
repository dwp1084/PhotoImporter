from os import listdir
from os.path import exists, join, isdir
from pathlib import Path
from string import ascii_uppercase as drive_letters

from PyQt5 import QtWidgets
from PyQt5.QtCore import QDateTime, QSize, QSettings, pyqtSlot, QStandardPaths

from constants import ROOT_NAME, DRIVE_LETTER_NAME, EDITED_LOC_NAME, JPEG_LOC_NAME, RAW_LOC_NAME
from ui.ui_PhotoImporterMainWindow import Ui_PhotoImporterMainWindow


class PhotoImporterMainWindow(QtWidgets.QMainWindow):
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
    
    def comboBoxSetToSetting(self, comboBox: QtWidgets.QComboBox, settingsKey: str):
        comboBox.currentTextChanged.connect(
            lambda txt: self.settings.setValue(settingsKey, txt)
        )

    def loadSettings(self) -> None:
        if self.settings.value(ROOT_NAME):
            self.ui.rootDirectoryPathEdit.setText(self.settings.value(ROOT_NAME))
            self.updateSubdirectories()

        self.updateDriveLetters()

    def toggleImportWidgetVisibility(self, action: QtWidgets.QAction, widget: QtWidgets.QWidget) -> None:
        widget.setVisible(action.isChecked())

        # At least one value must always be checked
        if not (self.ui.actionRAW.isChecked() or self.ui.actionJPEG.isChecked()):
            if action == self.ui.actionRAW:
                self.ui.actionJPEG.toggle()
            else:
                self.ui.actionRAW.toggle()

    @pyqtSlot()
    def searchForFolder(self) -> None:
        startingDirectory = str(Path.home())
        if self.settings.value(ROOT_NAME):
            startingDirectory = self.settings.value(ROOT_NAME)
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Open Folder", startingDirectory)
        if path != "":
            self.ui.rootDirectoryPathEdit.setText(path)
            self.refresh(path)

    def refresh(self, pathName: str) -> None:
        if not (exists(pathName) or isdir(pathName)):
            self.error(f"Root path \"{pathName}\" could not be found.")
            return
        self.ui.errorLabel.setVisible(False)
        self.settings.setValue(ROOT_NAME, pathName.strip())
        self.updateSubdirectories()
        self.updateDriveLetters()

    def updateSubdirectories(self):
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

    def error(self, text):
        self.ui.errorLabel.setText(text)
        self.ui.errorLabel.setVisible(True)
        
    def updateDriveLetters(self):
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
    def setComboBoxFromSetting(comboBox: QtWidgets.QComboBox, setting: str):
        index = comboBox.findText(setting)
        if index > -1:
            comboBox.setCurrentIndex(index)
