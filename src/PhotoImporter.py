import datetime as dt

from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
from os import mkdir, listdir, walk, remove
from os.path import join, exists, isdir, basename
from shutil import copy2
from hashlib import sha256

from constants import CAMERA_FOLDER_NAME, DATE_FORMAT


class PhotoImporter(QObject):

    sdCardRoot = ""
    editedDir = ""
    jpegDir = ""
    rawDir = ""
    projectName = ""
    projectDate = dt.date.today()
    baseProjectFolderName = ""

    editedPathExists = False
    jpegPathAlreadyExists = False
    rawPathAlreadyExists = False

    jpegFilesToImport = []
    rawFilesToImport = []

    importing = pyqtSignal()
    updateNumberOfOperations = pyqtSignal(int)
    completedOperation = pyqtSignal()
    statusMessage = pyqtSignal(str)
    importComplete = pyqtSignal()

    def __init__(self):
        super().__init__()

    def validate(self, sdCardRoot: str, editedDir: str, jpegDir: str | None, rawDir: str | None) -> None:
        if not exists(join(sdCardRoot, CAMERA_FOLDER_NAME)):
            raise IOError(f"Drive \"{sdCardRoot}\" not a valid camera removable storage device.")

        if not exists(editedDir):
            raise IOError(f"Directory \"{editedDir}\" does not exist.")

        if jpegDir is not None and not exists(jpegDir):
            raise IOError(f"Directory \"{jpegDir}\" does not exist.")

        if rawDir is not None and not exists(rawDir):
            raise IOError(f"Directory \"{rawDir}\" does not exist.")

        if jpegDir is None and editedDir == rawDir:
            raise IOError("Edited photos directory and raw photos directory cannot be the same.")

        if rawDir is None and editedDir == jpegDir:
            raise IOError("Edited photos directory and jpeg photos directory cannot be the same.")

        if len({editedDir, jpegDir, rawDir}) < 3:
            raise IOError("Edited, jpeg, and raw photo directories must be unique.")

        self.sdCardRoot = sdCardRoot
        self.editedDir = editedDir
        if jpegDir is not None:
            self.jpegDir = jpegDir
        if rawDir is not None:
            self.rawDir = rawDir

    def importPhotos(self, date: dt.date, projectName: str):
        self.projectName = projectName
        self.projectDate = date
        self._importPhotos()

    def _reset(self):
        self.sdCardRoot = ""
        self.editedDir = ""
        self.jpegDir = ""
        self.rawDir = ""
        self.projectName = ""
        self.projectDate = dt.date.today()
        self.baseProjectFolderName = ""

        self.editedPathExists = False
        self.jpegPathAlreadyExists = False
        self.rawPathAlreadyExists = False

        self.jpegFilesToImport = []
        self.rawFilesToImport = []

    def _importPhotos(self):
        self.importing.emit()
        self._mkdirs()
        if self.jpegDir != "" and not self.jpegPathAlreadyExists:
            self.jpegFilesToImport = self._getFileNames(".jpg", ".jpeg")
        if self.rawDir != "" and not self.rawPathAlreadyExists:
            self.rawFilesToImport = self._getFileNames(".nef")

        # Update total number of operations for progress bar (copy each file, compare hash of each file,
        # and delete original.)
        numberOfOperations = (len(self.jpegFilesToImport) + len(self.rawFilesToImport)) * 3
        self.updateNumberOfOperations.emit(numberOfOperations)

        self._createThread(self.jpegFilesToImport, self.jpegDir, self.jpegsFinished)

    @pyqtSlot()
    def jpegsFinished(self):
        self._createThread(self.rawFilesToImport, self.rawDir, self.rawsFinished)

    @pyqtSlot()
    def rawsFinished(self):
        self.importComplete.emit()
        self._reset()

    def _createThread(self, filesToImport, destination, finishedSlot):
        self.thread = QThread()
        self.worker = PhotoImporterWorker(filesToImport, destination)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.completedOperation.connect(self.completedOperation)
        self.worker.statusMessage.connect(self.statusMessage)
        self.thread.finished.connect(finishedSlot)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _mkdirs(self):
        # Determine if there's a directory for the year
        year = self.projectDate.strftime("%Y")
        yearPath = join(self.editedDir, year)
        if not isdir(yearPath):
            mkdir(yearPath)

        # Determine if there's another project(s) from the same date
        dateStr = self.projectDate.strftime(DATE_FORMAT)
        matches = [project for project in listdir(yearPath) if dateStr in project]

        if len(matches) > 0:
            # If there is, check if the name is the same, a folder might already exist
            if any(self.projectName in match for match in matches):
                self.editedPathExists = True
            # If it's not the same, add a suffix to the date
            else:
                index = 1
                while True:
                    updatedDateStr = f"{dateStr}-{index:02d}"
                    if any(updatedDateStr in match for match in matches):
                        index += 1
                    else:
                        dateStr = updatedDateStr
                        break
        # Otherwise, create folders in each directory
        baseDirectory = f"{dateStr} {self.projectName}"
        if not self.editedPathExists:
            editedPath = join(yearPath, baseDirectory)
            mkdir(editedPath)

        if self.jpegDir != "":
            yearPath = join(self.jpegDir, year)
            jpegPath = join(yearPath, baseDirectory)
            if not isdir(jpegPath):
                mkdir(jpegPath)
                self.jpegDir = jpegPath
            else:
                self.jpegPathAlreadyExists = True

        if self.rawDir != "":
            yearPath = join(self.rawDir, f"R{year}")
            rawPath = join(yearPath, f"R{baseDirectory}")
            if not isdir(rawPath):
                mkdir(rawPath)
                self.rawDir = rawPath
            else:
                self.rawPathAlreadyExists = True

    def _getFileNames(self, *extensions):
        sdPath = join(self.sdCardRoot, CAMERA_FOLDER_NAME)

        # Get all files and subdirectories
        results = walk(sdPath)
        filesToImport = []
        for result in results:
            matchingFiles = [join(result[0], file)
                             for file in result[2]
                             if any(extension.lower() in file.lower() for extension in extensions)
                             ]
            filesToImport += matchingFiles

        return filesToImport


class PhotoImporterWorker(QObject):
    completedOperation = pyqtSignal()
    statusMessage = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, filesToImport, destination):
        super().__init__()
        self.filesToImport = filesToImport
        self.destination = destination

    def changeSettings(self, filesToImport, destination):
        self.filesToImport = filesToImport
        self.destination = destination

    def run(self):
        for file in self.filesToImport:
            self.statusMessage.emit(f"Copying {basename(file)} to {self.destination}.")
            copy2(file, self.destination)
            self.completedOperation.emit()

            self.statusMessage.emit(f"Checking hash of {basename(file)}.")
            originalHash = self.getFileHash(file)
            newHash = self.getFileHash(join(self.destination, basename(file)))
            self.completedOperation.emit()
            if originalHash != newHash:
                print(f"File {file} not copied correctly")
            else:
                # Remove original file only if it was copied over correctly.
                self.statusMessage.emit(f"Deleting {file}.")
                remove(file)
            self.completedOperation.emit()
        self.finished.emit()

    @staticmethod
    def getFileHash(path):
        chunk_size = 1024 * 1024

        with open(path, "rb") as file:
            filehash = sha256()
            for chunk in iter(lambda: file.read(chunk_size), b""):
                filehash.update(chunk)
            return filehash.digest()
