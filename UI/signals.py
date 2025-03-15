from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from UI.settings_dialog import SettingsDialog

from core.export_handlers import export_to_csv, export_to_html, export_to_png, load_from_csv

def on_settings(self):
    """
    Open the settings dialog and apply the theme if accepted.
    """
    dialog = SettingsDialog(self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        self.apply_current_theme()


def on_show_doc(self):
    """
    Open the GitHub documentation link after confirmation.
    """
    msg = QMessageBox.question(
        self,
        "Otwieranie dokumentacji",
        "Aplikacja otworzy link GitHub w przeglądarce.\n\nCzy kontynuować?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    if msg == QMessageBox.StandardButton.Yes:
        QDesktopServices.openUrl(QUrl("https://github.com/m-walas/harmobot"))


def on_load_from_csv(self):
    """
    Load data from a CSV file.
    """
    load_from_csv(self)


def on_export_to_csv(self):
    """
    Export schedule data to CSV.
    """
    export_to_csv(self)


def on_export_to_html(self):
    """
    Export schedule data to HTML.
    """
    export_to_html(self)


def on_export_to_png(self):
    """
    Export schedule data to PNG.
    """
    export_to_png(self)