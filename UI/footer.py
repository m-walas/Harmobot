from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont
from core.version import __app_version__


class FooterWidget(QWidget):
    """
    Wspólny widget stopki dla całej aplikacji.
        - nazwa aplikacji, autor, rok,
        - numer wersji,
        - ikonka informująca o dostępnej aktualizacji.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(10)

        self.appLabel = QLabel("Harmobot © 2025 | mwalas")
        self.appLabel.setFont(QFont("Segoe UI", 9))
        self._layout.addWidget(self.appLabel)

        self._layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.versionLabel = QLabel(f"v{__app_version__}")
        self.versionLabel.setFont(QFont("Segoe UI", 9))
        self._layout.addWidget(self.versionLabel)

        self.updateIcon = QLabel()
        update_pixmap = QPixmap("assets/icons/update.png")
        if not update_pixmap.isNull():
            self.updateIcon.setPixmap(update_pixmap.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio))
        self.updateIcon.setToolTip("Nowa wersja jest dostępna.")
        self.updateIcon.setVisible(False)
        self._layout.addWidget(self.updateIcon)

    def setUpdateAvailable(self, is_available: bool):
        """
        Pokazuje lub ukrywa ikonę aktualizacji w zależności od wartości is_available.
        """
        self.updateIcon.setVisible(is_available)
