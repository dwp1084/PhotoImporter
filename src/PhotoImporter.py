import datetime as dt
from collections.abc import Callable

from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
from os import mkdir, listdir, walk, remove
from os.path import join, exists, isdir, basename
from shutil import copy2
from hashlib import sha256

from constants import CAMERA_FOLDER_NAME, DATE_FORMAT


class PhotoImporter(QObject):
    """
    Class that kicks off the photo import process and provides updates to the GUI about its status.
    """

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
        """
        The validate function checks that the given directories exist and are unique. It also ensures that the
        sdCardRoot is a valid camera removable storage device.

        :param sdCardRoot: Root directory of the SD card
        :param editedDir: Directory where edited photos are stored
        :param jpegDir: Directory where jpeg photos are stored, optional
        :param rawDir: Directory where raw photos are stored, optional
        :doc-author: Trelent
        """
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

    def importPhotos(self, date: dt.date, projectName: str) -> None:
        """
        The importPhotos function is the main function of this class. It takes a date and project name as arguments,
        and imports all photos from that day into a folder with the given project name.

        :param date: Specify the date of the project
        :param projectName: Set the project name
        :doc-author: Trelent
        """
        self.projectName = projectName
        self.projectDate = date
        self._importPhotos()

    @pyqtSlot()
    def jpegsFinished(self) -> None:
        """
        The jpegsFinished function is called when the jpegs have been imported. It creates a thread to import the raw
        files, and then calls rawsFinished when it's done.

        :doc-author: Trelent
        """
        self._createThread(self.rawFilesToImport, self.rawDir, self.rawsFinished)

    @pyqtSlot()
    def rawsFinished(self) -> None:
        """
        The rawsFinished function is called when the raw file import process has completed. It emits a signal to
        indicate that the import process has finished, and then resets the state of the importer.

        :doc-author: Trelent
        """
        self.importComplete.emit()
        self._reset()

    def _reset(self) -> None:
        """
        The _reset function is called after importing is complete. It sets all the class variables to their default
        values.

        :doc-author: Trelent
        """
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

    def _importPhotos(self) -> None:
        """
        The _importPhotos function is the main internal function of this class. It does the following:
            1. Emits a signal to indicate that importing has begun
            2. Creates directories for JPEG and RAW files if they don't already exist
            3. Gets file names from source directory, based on file extension (.jpg/.jpeg for JPEGs, .nef for RAWs) and
               stores them in lists

        :doc-author: Trelent
        """
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

    def _createThread(self, filesToImport: list, destination: str, finishedSlot: Callable[[], None]) -> None:
        """
        The _createThread function is a helper function that creates a QThread and a PhotoImporterWorker object,
        connects the worker's signals to slots in this class, and starts the thread. The finishedSlot parameter is used
        to connect the thread's finished signal to whatever slot you want called when the import is complete.

        :param filesToImport: List of files to import
        :param destination: Destination folder
        :param finishedSlot: Slot to be called once the thread has finished executing
        :doc-author: Trelent
        """
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

    def _mkdirs(self) -> None:
        """
        The _mkdirs function creates destination directories for the edited, jpeg, and raw photos. The directories are
        created in the following scheme: {root}/{type}/{year}/{date} {projectName}. This function checks if a project
        of the same name and date was already created so that photos are not imported to folders that already exist. If
        another project exists from the same date, the function adds a suffix to the date so projects are sorted in the
        correct order on your filesystem.
        """
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

    def _getFileNames(self, *extensions: str) -> list:
        """
        The _getFileNames function is a helper function that returns a list of all files in the camera folder
        that match any of the extensions passed to it. It does this by walking through each subdirectory and adding
        any matching file to its return list.

        :param *extensions: str: Pass a list of strings to the function
        :return: A list of all files in the sd card's DCIM folder that have one of the given file extensions
        :doc-author: Trelent
        """
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
    """
    Worker class for the importing threads, which handle the importing process to keep the GUI responsive.
    """

    completedOperation = pyqtSignal()
    statusMessage = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, filesToImport: list, destination: str) -> None:
        super().__init__()
        self.filesToImport = filesToImport
        self.destination = destination

    def run(self) -> None:
        """
        This function handles the thread execution. It imports each file from the file import list to the destination
        folder, compares the hashes of both files to ensure that the file was imported correctly, then deletes the file
        from the SD card if the hashes match. It also emits signals to update the GUI with the current status of the
        thread execution and update the progress bar.
        """
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
    def getFileHash(path: str) -> bytes:
        """
        The getFileHash function takes a path to a file and returns the SHA256 hash of that file.

        :param path: File path
        :return: The sha256 hash of the file
        :doc-author: Trelent
        """
        chunk_size = 1024 * 1024

        with open(path, "rb") as file:
            filehash = sha256()
            for chunk in iter(lambda: file.read(chunk_size), b""):
                filehash.update(chunk)
            return filehash.digest()
