import multiprocessing
from PyQt6.QtWidgets import (
    QDialog, QGridLayout, QLabel, QSpinBox, QComboBox, QHBoxLayout, QWidget,
    QDialogButtonBox, QToolButton
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSettings

from core.resources import get_icon_path

def pluralize_cores(n: int) -> str:
    """
    Returns the Polish plural form of the word "rdzeń" (core) based on the given number.

    Args:
        n (int): The number of cores.

    Returns:
        str: The plural form of the word "rdzeń".
    """
    if n == 0 or 5 <= n <= 20 or n % 10 == 0:
        return "rdzeni"
    elif n == 1:
        return "rdzeń"
    elif 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return "rdzenie"
    else:
        return "rdzeni"

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("SettingsDialog")

        self.setWindowTitle("Ustawienia")
        self.setMaximumWidth(420)

        self.settings = QSettings("Harmobot", "Harmobot")

        layout = QGridLayout()
        layout.setHorizontalSpacing(15)
        layout.setVerticalSpacing(8)
        self.setLayout(layout)

        self.themeCombo = QComboBox()
        self.themeCombo.addItems([
            "Light", "Dark", "Cafe", "Dracula",
            "Ocean Light", "Ocean Dark", "High Contrast", "Firemode"
        ])
        self.themeCombo.setCurrentText(self.settings.value("theme", "Light"))

        label_theme = QLabel("Motyw:")
        layout.addWidget(label_theme, 0, 0)
        layout.addWidget(self.themeCombo, 0, 1)

        self.processingTimeSpin = QSpinBox()
        self.processingTimeSpin.setRange(1, 60)
        self.processingTimeSpin.setValue(int(self.settings.value("processing_time", 15)))

        self.processingInfoBtn = QToolButton()
        self.processingInfoBtn.setIcon(QIcon(get_icon_path("info")))
        self.processingInfoBtn.setToolTip(
            "Maksymalny czas (w sekundach), przez jaki solver będzie szukał rozwiązania.\n"
            "Większa wartość = większa szansa na lepsze rozwiązanie, ale dłuższy czas obliczeń."
        )

        timeWidget = QWidget()
        timeHLayout = QHBoxLayout(timeWidget)
        timeHLayout.setContentsMargins(0, 0, 0, 0)
        timeHLayout.setSpacing(6)
        timeHLayout.addWidget(self.processingTimeSpin)
        timeHLayout.addWidget(self.processingInfoBtn)

        label_time = QLabel("Czas (s):")
        layout.addWidget(label_time, 1, 0)
        layout.addWidget(timeWidget, 1, 1)

        self.maxThreadsSpin = QSpinBox()
        self.maxThreadsSpin.setObjectName("MaxThreadsSpin")
        self.maxThreadsSpin.setRange(1, 64)
        self.maxThreadsSpin.setValue(int(self.settings.value("max_threads", 4)))

        threadsInfoBtn = QToolButton()
        threadsInfoBtn.setIcon(QIcon(get_icon_path("info")))
        threadsInfoBtn.setToolTip(
            "Maksymalna liczba wątków (workerów) używanych przez solver.\n"
            "Więcej wątków może przyspieszyć obliczenia, ale obciąża CPU.\n"
            "Zbyt wysoka wartość spowolni inne procesy w systemie."
        )

        threadsWidget = QWidget()
        threadsHLayout = QHBoxLayout(threadsWidget)
        threadsHLayout.setContentsMargins(0, 0, 0, 0)
        threadsHLayout.setSpacing(6)
        threadsHLayout.addWidget(self.maxThreadsSpin)
        threadsHLayout.addWidget(threadsInfoBtn)

        label_threads = QLabel("Maks. wątków:")
        layout.addWidget(label_threads, 2, 0)
        layout.addWidget(threadsWidget, 2, 1)

        self.threadsStatusLabel = QLabel()
        self.threadsStatusLabel.setObjectName("ThreadStatusLabel")
        self.threadsStatusLabel.setWordWrap(True)
        layout.addWidget(self.threadsStatusLabel, 3, 0, 1, 2)

        self.maxThreadsSpin.valueChanged.connect(self.updateThreadsStatus)
        self.updateThreadsStatus(self.maxThreadsSpin.value())

        self.timezoneCabbageSpin = QSpinBox()
        self.timezoneCabbageSpin.setRange(-12, 14)
        self.timezoneCabbageSpin.setValue(int(self.settings.value("timezone_cabbage", 1)))

        tzCabbageBtn = QToolButton()
        tzCabbageBtn.setIcon(QIcon(get_icon_path("info")))
        tzCabbageBtn.setToolTip(
            "Przesunięcie strefy czasowej (w godzinach) dla serwisu Cabbage.\n"
            "Dodawane do czasów wydarzeń pobranych z Cabbage."
        )

        cabbageWidget = QWidget()
        cabbageHLayout = QHBoxLayout(cabbageWidget)
        cabbageHLayout.setContentsMargins(0, 0, 0, 0)
        cabbageHLayout.setSpacing(6)
        cabbageHLayout.addWidget(self.timezoneCabbageSpin)
        cabbageHLayout.addWidget(tzCabbageBtn)

        layout.addWidget(QLabel("Cabbage TimeZone:"), 4, 0)
        layout.addWidget(cabbageWidget, 4, 1)

        self.timezoneSchejSpin = QSpinBox()
        self.timezoneSchejSpin.setRange(-12, 14)
        self.timezoneSchejSpin.setValue(int(self.settings.value("timezone_schej", 1)))

        tzSchejBtn = QToolButton()
        tzSchejBtn.setIcon(QIcon(get_icon_path("info")))
        tzSchejBtn.setToolTip(
            "Przesunięcie strefy czasowej (w godzinach) dla serwisu Schej.\n"
            "Dodawane do czasów wydarzeń pobranych z Schej."
        )

        schejWidget = QWidget()
        schejHLayout = QHBoxLayout(schejWidget)
        schejHLayout.setContentsMargins(0, 0, 0, 0)
        schejHLayout.setSpacing(6)
        schejHLayout.addWidget(self.timezoneSchejSpin)
        schejHLayout.addWidget(tzSchejBtn)

        layout.addWidget(QLabel("Schej TimeZone:"), 5, 0)
        layout.addWidget(schejWidget, 5, 1)

        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox.accepted.connect(self.validateAndAccept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox, 6, 0, 1, 2)

    def updateThreadsStatus(self, value: int):
        """
        Updates the status label with the current thread count and a recommendation.

        Args:
            value (int): The current thread count.
        """
        available_cores = multiprocessing.cpu_count()
        recommended = max(1, int(available_cores * 0.6))
        core_label = pluralize_cores(available_cores)

        status_text = f"{available_cores} {core_label}; maks zalecane: {recommended}"
        exceeded = False
        if value > recommended:
            exceeded = True
            status_text += " (>60%)"

        self.maxThreadsSpin.setProperty("exceeded", exceeded)
        self.threadsStatusLabel.setProperty("exceeded", exceeded)

        self.style().unpolish(self.maxThreadsSpin)
        self.style().polish(self.maxThreadsSpin)
        self.style().unpolish(self.threadsStatusLabel)
        self.style().polish(self.threadsStatusLabel)

        self.threadsStatusLabel.setText(status_text)

    def validateAndAccept(self):
        """
        Validates the settings and saves them to the settings file.
        """
        self.settings.setValue("theme", self.themeCombo.currentText())
        self.settings.setValue("processing_time", self.processingTimeSpin.value())
        self.settings.setValue("max_threads", self.maxThreadsSpin.value())
        self.settings.setValue("timezone_cabbage", self.timezoneCabbageSpin.value())
        self.settings.setValue("timezone_schej", self.timezoneSchejSpin.value())
        self.accept()
