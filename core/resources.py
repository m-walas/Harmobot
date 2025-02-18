import sys
import os

def resource_path(relative_path):
    """
    Zwraca absolutną ścieżkę do zasobu.
    Dzięki temu zarówno podczas pracy z kodem (dev), jak i po spakowaniu (PyInstaller)
    aplikacja poprawnie znajdzie plik.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
