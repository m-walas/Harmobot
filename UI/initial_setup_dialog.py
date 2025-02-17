import sys
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QPushButton,
    QMessageBox, QFileDialog, QVBoxLayout
)
from PyQt6.QtGui import QMovie, QPixmap, QDesktopServices
from PyQt6.QtCore import Qt, QUrl

from UI.collapsible_sidebar import CollapsibleSidebar
from UI.footer import FooterWidget
from UI.styles import LIGHT_QSS, FIRE_QSS

from core.lettuce_service import fetch_event_data as lettuce_fetch_event_data
from core.lettuce_service import process_data as lettuce_process_data
from core.schej_service import fetch_event_data as schej_fetch_event_data
from core.schej_service import process_data as schej_process_data
from core.update_checker import get_update_checker
from core.version import __app_version__

class InitialSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Harmobot")
        self.setModal(True)
        self.resize(900, 600)

        # Domyślnie Lettuce
        self.current_engine = "Lettuce"
        self.fire_mode = False

        # Dane do przekazania do MainWindow
        self.loaded_engine = "Lettuce"
        self.loaded_participants = []
        self.loaded_poll_dates = []
        self.loaded_day_ranges = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Górny widget: sidebar + centrum
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        # Sidebar
        self.sidebar = CollapsibleSidebar(initial_mode=True)
        self.sidebar.sig_select_lettuce.connect(self.on_select_lettuce)
        self.sidebar.sig_select_schej.connect(self.on_select_schej)
        self.sidebar.sig_load_csv.connect(self.on_load_csv)
        self.sidebar.sig_fire_mode.connect(self.on_toggle_fire_mode)
        self.sidebar.sig_documentation.connect(self.on_show_doc)
        top_layout.addWidget(self.sidebar, stretch=0)

        # Central – główna część dialogu
        center_widget = QWidget()
        self.center_layout = QVBoxLayout(center_widget)
        self.center_layout.setContentsMargins(20, 20, 10, 10)
        self.center_layout.setSpacing(10)

        # main logo
        self.logo_label = QLabel()
        self.default_pixmap = QPixmap(self.resource_path("assets/harmobot_logo_big.png"))
        self.fire_pixmap = QMovie(self.resource_path("assets/harmobot_fire.gif"))
        if self.default_pixmap.isNull():
            self.logo_label.setText("Harmobot logo")
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self.default_pixmap.setDevicePixelRatio(2.0)
            self.logo_label.setPixmap(
                self.default_pixmap.scaled(
                    500, 500,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.center_layout.addWidget(self.logo_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # spacer widget
        self.spacer_widget = QWidget()
        # important: the same values as in function below (update_spacer) -> change in both places
        initial_space = 158 if self.fire_mode else 5
        self.spacer_widget.setFixedHeight(initial_space)
        self.center_layout.addWidget(self.spacer_widget)

        self.event_id_label = QLabel("URL lub Event ID (Lettuce):")
        self.event_id_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.center_layout.addWidget(self.event_id_label)

        self.event_id_edit = QLineEdit()
        self.event_id_edit.setPlaceholderText("https://lettucemeet.com/l/*****")
        self.event_id_edit.setMinimumWidth(400)
        self.event_id_edit.textChanged.connect(self.toggle_fetch_button)
        self.center_layout.addWidget(self.event_id_edit, alignment=Qt.AlignmentFlag.AlignCenter)

        self.fetch_button = QPushButton("Pobierz dane")
        self.fetch_button.setFixedWidth(120)
        self.fetch_button.setEnabled(False)
        self.fetch_button.clicked.connect(self.on_fetch_data)
        self.center_layout.addWidget(self.fetch_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; font-size: 10px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.center_layout.addWidget(self.error_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.center_layout.addStretch()
        top_layout.addWidget(center_widget, stretch=1)
        main_layout.addWidget(top_widget, stretch=1)

        # "Working with" & logo
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        row_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.working_with_label = QLabel("<i>Working with</i>")
        row_layout.addWidget(self.working_with_label)

        self.engine_logo_label = QLabel()
        self.engine_logo_label.setCursor(Qt.CursorShape.PointingHandCursor)
        row_layout.addWidget(self.engine_logo_label)

        self.center_layout.addStretch()
        self.center_layout.addWidget(row_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        self.engine_logo_label.mousePressEvent = self.on_engine_logo_clicked

        # footer
        self.footer = FooterWidget()
        main_layout.addWidget(self.footer, stretch=0)

        self.update_checker = get_update_checker(self)
        self.update_checker.updateAvailable.connect(self.on_update_available)
        self.update_checker.noUpdateAvailable.connect(self.on_no_update)
        self.update_checker.errorOccurred.connect(self.on_update_error)
        self.update_checker.check_for_update()

        self.apply_light_theme()

        self.on_select_lettuce()

    def on_engine_logo_clicked(self, event):
        """Kliknięcie w logo otwiera stronę właściwą dla wybranego "silnika"."""
        if self.current_engine == "Lettuce":
            QDesktopServices.openUrl(QUrl("https://lettucemeet.com"))
        elif self.current_engine == "Schej":
            QDesktopServices.openUrl(QUrl("https://schej.it"))
        else:
            pass

    def on_select_lettuce(self):
        self.current_engine = "Lettuce"
        self.error_label.setText("")
        self.event_id_label.setText("URL lub Event ID (Lettuce):")
        self.event_id_edit.setPlaceholderText("https://lettucemeet.com/l/*****")
        self.event_id_edit.clear()

        if self.fire_mode:
            logo_path = "assets/api/lettuce_logo_dark.png"
        else:
            logo_path = "assets/api/lettuce_logo_light.png"
        pixmap = QPixmap(self.resource_path(logo_path))
        if not pixmap.isNull():
            pixmap.setDevicePixelRatio(2.0)
            pixmap = pixmap.scaledToHeight(32, Qt.TransformationMode.SmoothTransformation)
            self.engine_logo_label.setPixmap(pixmap)
            self.engine_logo_label.setText("")
        else:
            if self.fire_mode:
                meet_color = "#eef6ed"
            else:
                meet_color = "#000000"
            fallback_html = (
                f'<span style="color:#009d50; font-weight:bold;">lettuce</span> '
                f'<span style="color:{meet_color}; font-weight:light;">meet</span>'
            )
            self.engine_logo_label.setText(fallback_html)

    def on_select_schej(self):
        self.current_engine = "Schej"
        self.error_label.setText("")
        self.event_id_label.setText("URL lub Event ID (Schej):")
        self.event_id_edit.setPlaceholderText("https://schej.it/e/*****")
        self.event_id_edit.clear()

        if self.fire_mode:
            logo_path = "assets/api/schej_logo_dark.png"
        else:
            logo_path = "assets/api/schej_logo_light.png"
        pixmap = QPixmap(self.resource_path(logo_path))
        if not pixmap.isNull():
            pixmap.setDevicePixelRatio(2.0)
            pixmap = pixmap.scaledToHeight(32, Qt.TransformationMode.SmoothTransformation)
            self.engine_logo_label.setPixmap(pixmap)
            self.engine_logo_label.setText("")
        else:
            fallback_html = '<span style="color:#009d50; font-weight:bold;">schej</span>'
            self.engine_logo_label.setText(fallback_html)

    def update_engine_logo(self):
        if self.current_engine == "Lettuce":
            self.on_select_lettuce()
        elif self.current_engine == "Schej":
            self.on_select_schej()
        else:
            pass

    def toggle_fetch_button(self, text: str):
        self.fetch_button.setEnabled(bool(text.strip()))

    def on_fetch_data(self):
        raw_input = self.event_id_edit.text().strip()
        if not raw_input:
            self.show_error("Proszę wpisać Event ID lub link.")
            return

        self.error_label.setText("")
        try:
            if self.current_engine == "Lettuce":
                event_id = self.parse_lettuce_id(raw_input)
                json_resp = lettuce_fetch_event_data(event_id)
                participants, dates = lettuce_process_data(json_resp, time_offset_hours=0)
                self.loaded_engine = "Lettuce"
                self.loaded_participants = participants
                self.loaded_poll_dates = dates
                self.loaded_day_ranges = None
            else:
                event_id = self.parse_schej_id(raw_input)
                json_resp = schej_fetch_event_data(event_id)
                participants, dates, day_ranges = schej_process_data(json_resp, time_offset_hours=1)
                self.loaded_engine = "Schej"
                self.loaded_participants = participants
                self.loaded_poll_dates = dates
                self.loaded_day_ranges = day_ranges
            self.accept()
        except Exception as e:
            self.show_error(str(e))

    def parse_lettuce_id(self, raw_input: str) -> str:
        if "schej.it" in raw_input.lower():
            raise ValueError("Wygląda na link do Schej, a aktualnie jest Lettuce.")
        if "lettucemeet.com" in raw_input.lower():
            parts = raw_input.rstrip("/").split("/")
            if parts:
                return parts[-1]
        return raw_input

    def parse_schej_id(self, raw_input: str) -> str:
        if "lettucemeet.com" in raw_input.lower():
            raise ValueError("Wygląda na link do Lettuce, a aktualnie jest Schej.")
        if "schej.it" in raw_input.lower():
            parts = raw_input.rstrip("/").split("/")
            if parts:
                return parts[-1]
        return raw_input

    def show_error(self, message: str):
        self.error_label.setText(message)

    def on_load_csv(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Wczytaj CSV", "", "CSV Files (*.csv)")
        if not filepath:
            return
        QMessageBox.information(self, "CSV", f"Załadowano CSV:\n{filepath}")

    def on_toggle_fire_mode(self):
        self.fire_mode = not self.fire_mode
        if self.fire_mode:
            self.apply_fire_mode_theme()
            if self.fire_pixmap.isValid():
                self.logo_label.clear()
                self.logo_label.setMovie(self.fire_pixmap)
                self.fire_pixmap.start()
        else:
            self.apply_light_theme()
            if self.fire_pixmap.isValid():
                self.fire_pixmap.stop()
            if not self.default_pixmap.isNull():
                self.logo_label.setMovie(None)
                self.logo_label.setPixmap(
                    self.default_pixmap.scaled(
                        500, 500,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )

    def on_show_doc(self):
        msg = QMessageBox.question(
            self,
            "Otwieranie dokumentacji",
            "Aplikacja otworzy link GitHub w przeglądarce.\n\nCzy kontynuować?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if msg == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl("https://github.com/m-walas/harmobot"))

    def on_update_available(self, remote_version: str):
        self.footer.setUpdateAvailable(True)
        QMessageBox.information(
            self,
            "Aktualizacja dostępna",
            f"Nowa wersja {remote_version} jest dostępna!"
        )

    def on_no_update(self):
        self.footer.setUpdateAvailable(False)

    def on_update_error(self, error_msg: str):
        QMessageBox.warning(self, "Update check error", error_msg)
        self.footer.setUpdateAvailable(False)

    def update_spacer(self):
        # important: the same values as in function above (InitialSetupDialog.__init__) -> change in both places
        new_space = 158 if self.fire_mode else 5
        self.spacer_widget.setFixedHeight(new_space)

    def apply_light_theme(self):
        self.setStyleSheet(LIGHT_QSS)
        self.sidebar.set_dark_mode_icon(dark=False)
        self.update_engine_logo()
        self.update_spacer()

    def apply_fire_mode_theme(self):
        self.setStyleSheet(FIRE_QSS)
        self.sidebar.set_dark_mode_icon(dark=True)
        self.update_engine_logo()
        self.update_spacer()

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)
