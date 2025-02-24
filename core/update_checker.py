import json
from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from core.version import __app_version__

_instance = None

class UpdateChecker(QObject):
    """
    Class responsible for checking for updates.
    Singleton – only one instance exists for the entire application.
    
    Signals:
        - updateAvailable(str): Emitted when a newer version is available (parameter = version number).
        - noUpdateAvailable: Emitted when the local version is up-to-date.
        - errorOccurred(str): Emitted in case of a network or parsing error.

    Attributes:
        - has_update (bool): Flag indicating whether an update is available; initially False, set to True when the updateAvailable signal is emitted.
    """
    updateAvailable = pyqtSignal(str)
    noUpdateAvailable = pyqtSignal()
    errorOccurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)
        self._manager.finished.connect(self._handle_response)
        self.remote_url = QUrl("https://harmobot.matwal777.workers.dev/version")
        self._update_checked = False
        self.has_update = False

    def check_for_update(self):
        """
        Initiates the update check by sending an HTTP request to the remote endpoint.
        The request is executed only once during the application's lifetime.
        """
        if self._update_checked:
            return
        self._update_checked = True

        request = QNetworkRequest(self.remote_url)
        self._manager.get(request)

    def _handle_response(self, reply: QNetworkReply):
        if reply.error() != QNetworkReply.NetworkError.NoError:
            error_msg = f"Network error: {reply.errorString()}"
            self.errorOccurred.emit(error_msg)
            reply.deleteLater()
            return

        data = reply.readAll().data()
        reply.deleteLater()

        try:
            json_data = json.loads(data.decode("utf-8"))
            remote_version = json_data.get("version", "")
            local_version = __app_version__.lstrip("vV")
            remote_version_clean = remote_version.lstrip("vV")

            def version_tuple(v):
                return tuple(map(int, v.split(".")))

            if version_tuple(remote_version_clean) > version_tuple(local_version):
                self.has_update = True
                self.updateAvailable.emit(remote_version)
            else:
                self.noUpdateAvailable.emit()
        except Exception as e:
            self.errorOccurred.emit(f"Parse error: {str(e)}")

def get_update_checker(parent=None):
    """
    Returns the sole instance of UpdateChecker (singleton).
    If an instance does not exist, creates one using the provided parent (only on first initialization).
    """
    global _instance
    if _instance is None:
        _instance = UpdateChecker(parent)
    return _instance
