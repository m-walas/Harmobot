import json
from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from core.version import __app_version__

_instance = None

class UpdateChecker(QObject):
    """
    Klasa odpowiedzialna za sprawdzanie aktualizacji.
    Singleton – tylko jedna instancja w całej aplikacji.
    
    Sygnały:
      - updateAvailable(str): gdy jest dostępna nowsza wersja (parametr = numer wersji)
      - noUpdateAvailable: gdy wersja lokalna jest aktualna
      - errorOccurred(str): w razie błędu sieci/parsowania

    Atrybuty:
      - has_update (bool): flaga informująca, czy wykryto dostępną aktualizację;
        domyślnie False, ustawiana na True, gdy sygnał updateAvailable zostanie wyemitowany.
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
        Inicjuje sprawdzenie aktualizacji poprzez wysłanie żądania HTTP do zdalnego endpointu.
        Żądanie zostanie wykonane tylko raz na cykl życia aplikacji.
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
            import json
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
    Zwraca jedyną instancję UpdateChecker (singleton).
    Jeżeli instancja nie istnieje, tworzy ją (używając podanego parent,
    ale tylko przy pierwszej inicjalizacji).
    """
    global _instance
    if _instance is None:
        _instance = UpdateChecker(parent)
    return _instance
