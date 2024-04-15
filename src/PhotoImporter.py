from PyQt5.QtCore import QObject, pyqtSignal
from os.path import join, exists


class PhotoImporter(QObject):

    sdCardRoot = ""
    editedDir = ""
    jpegDir = ""
    rawDir = ""
    projectName = ""
    projectDate = ""

    importing = pyqtSignal()

    def __init__(self):
        super().__init__()

    def validate(self, sdCardRoot: str, editedDir: str, jpegDir: str | None, rawDir: str | None) -> None:
        if not exists(join(sdCardRoot, "DCIM")):
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

    def importPhotos(self, date, projectName):
        self.projectName = projectName
        self.projectDate = date
        self._importPhotos()

    def _importPhotos(self):
        self.importing.emit()
