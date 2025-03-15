from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QPushButton,
    QMessageBox
)
from PyQt6.QtGui import QMovie, QPixmap, QDesktopServices
from PyQt6.QtCore import Qt, QUrl, QSettings

from UI.collapsible_sidebar import CollapsibleSidebar
from UI.footer import FooterWidget
from UI.signals import on_settings, on_show_doc

from core.resources import resource_path, get_icon_path, get_logo_path
from core.update_checker import get_update_checker
from core.version import __app_version__
from core.cabbage_service import fetch_event_data as cabbage_fetch_event_data
from core.cabbage_service import process_data as cabbage_process_data
from core.schej_service import fetch_event_data as schej_fetch_event_data
from core.schej_service import process_data as schej_process_data

def parse_cabbage_link(raw_input: str) -> str:
    """
    Parse the Cabbage event URL.
    
    Raises:
        ValueError: if the URL is invalid for Cabbage.
    """
    raw_input = raw_input.strip()
    if not raw_input.lower().startswith("http"):
        raise ValueError("Link musi zaczynać się od http/https.")
    if "/e/" in raw_input:
        raise ValueError("Wygląda na link do Schej, a aktualnie wybrano Cabbage.")
    if "/m/" not in raw_input:
        raise ValueError("Wygląda na niepoprawny URL z serwisu cabbage.")
    return raw_input


def parse_schej_link(raw_input: str) -> str:
    """
    Parse the Schej event URL.
    
    Raises:
        ValueError: if the URL is invalid for Schej.
    """
    raw_input = raw_input.strip()
    if not raw_input.lower().startswith("http"):
        raise ValueError("Link musi zaczynać się od http/https.")
    if "/m/" in raw_input:
        raise ValueError("Wygląda na link do Cabbage, a aktualnie wybrano Schej.")
    if "/e/" not in raw_input:
        raise ValueError("Wygląda na niepoprawny URL z serwisu schej.")
    return raw_input


class InitialSetupDialog(QDialog):
    """
    Dialog for the initial setup of Harmobot.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Harmobot")
        self.setModal(True)
        self.resize(900, 600)

        self.settings = QSettings("Harmobot", "Harmobot")
        # Default engine is Cabbage
        self.current_engine = "Cabbage"
        self.loaded_engine = "Cabbage"
        self.loaded_participants = []
        self.loaded_poll_dates = []
        self.loaded_day_ranges = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top area: sidebar and central content
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        # Sidebar widget
        self.sidebar = CollapsibleSidebar(initial_mode=True)
        self.sidebar.sig_select_cabbage.connect(lambda: self._set_engine("Cabbage", clear_input=True))
        self.sidebar.sig_select_schej.connect(lambda: self._set_engine("Schej", clear_input=True))
        self.sidebar.sig_settings.connect(self.on_settings)
        self.sidebar.sig_documentation.connect(self.on_show_doc)
        top_layout.addWidget(self.sidebar, stretch=0)

        # Central widget
        center_widget = QWidget()
        self.center_layout = QVBoxLayout(center_widget)
        self.center_layout.setContentsMargins(20, 20, 10, 10)
        self.center_layout.setSpacing(10)

        # Logo label
        self.logo_label = QLabel()
        self.default_pixmap = QPixmap(get_logo_path())
        self.fire_pixmap = QMovie(resource_path("assets/harmobot_fire.gif"))
        self.center_layout.addWidget(self.logo_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Spacer widget (height depends on theme)
        self.spacer_widget = QWidget()
        self.spacer_widget.setFixedHeight(5)
        self.center_layout.addWidget(self.spacer_widget)

        # URL input label
        self.event_id_label = QLabel("Pełny URL wydarzenia:")
        self.event_id_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.center_layout.addWidget(self.event_id_label)

        # URL input field
        self.event_id_edit = QLineEdit()
        placeholder = "https://***/m/*****" if self.current_engine == "Cabbage" else "https://***/e/*****"
        self.event_id_edit.setPlaceholderText(placeholder)
        self.event_id_edit.setMinimumWidth(400)
        self.event_id_edit.textChanged.connect(self.toggle_fetch_button)
        self.center_layout.addWidget(self.event_id_edit, alignment=Qt.AlignmentFlag.AlignCenter)

        # Fetch button
        self.fetch_button = QPushButton("Pobierz dane")
        self.fetch_button.setFixedWidth(120)
        self.fetch_button.setEnabled(False)
        self.fetch_button.clicked.connect(self.on_fetch_data)
        self.center_layout.addWidget(self.fetch_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; font-size: 10px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.center_layout.addWidget(self.error_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.center_layout.addStretch()
        top_layout.addWidget(center_widget, stretch=1)
        main_layout.addWidget(top_widget, stretch=1)

        # "Working with" row
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

        # Footer widget
        self.footer = FooterWidget()
        main_layout.addWidget(self.footer, stretch=0)

        self.update_checker = get_update_checker(self)
        self.update_checker.updateAvailable.connect(self.on_update_available)
        self.update_checker.noUpdateAvailable.connect(self.on_no_update)
        self.update_checker.errorOccurred.connect(self.on_update_error)
        self.update_checker.check_for_update()

        # Apply theme at startup
        self.apply_current_theme()
        self._set_engine("Cabbage", clear_input=True)

    def _set_engine(self, engine: str, clear_input: bool = False):
        """
        Set the current engine and update labels.
        
        Args:
            engine (str): "Cabbage" or "Schej".
            clear_input (bool): Clear the URL input if True.
        """
        self.current_engine = engine
        self.error_label.setText("")
        if engine == "Cabbage":
            self.event_id_label.setText("Pełny URL wydarzenia (Cabbage):")
            self.event_id_edit.setPlaceholderText("https://***/m/*****")
            fallback_html = (
                '<span id=cabbage_1>cabbage</span>'
                '<span id=cabbage_2>meet</span>'
            )
        elif engine == "Schej":
            self.event_id_label.setText("Pełny URL wydarzenia (Schej):")
            self.event_id_edit.setPlaceholderText("https://***/e/*****")
            fallback_html = '<span id=schej>schej</span>'
        else:
            return

        if clear_input:
            self.event_id_edit.clear()
        self.engine_logo_label.setText(fallback_html)

    def on_settings(self):
        """
        Emit the signal from UI/signal.py
        """
        on_settings(self)

    def on_engine_logo_clicked(self, event):
        """
        Open the engine website when the logo is clicked.
        """
        if self.current_engine == "Cabbage":
            QDesktopServices.openUrl(QUrl("https://cabbagemeet.com"))
        elif self.current_engine == "Schej":
            QDesktopServices.openUrl(QUrl("https://schej.it"))

    def toggle_fetch_button(self, text: str):
        """
        Enable or disable the fetch button based on the URL input.
        """
        self.fetch_button.setEnabled(bool(text.strip()))

    def on_fetch_data(self):
        """
        Fetch event data using the selected engine.
        """
        raw_input = self.event_id_edit.text().strip()
        if not raw_input:
            self.show_error("Proszę wpisać pełny URL wydarzenia.")
            return

        self.error_label.setText("")
        try:
            if self.current_engine == "Cabbage":
                event_url = parse_cabbage_link(raw_input)
                json_resp = cabbage_fetch_event_data(event_url)
                timezone_offset = int(self.settings.value("timezone_cabbage", 1))
                participants, dates, day_ranges = cabbage_process_data(json_resp, time_offset_hours=timezone_offset)
                self.loaded_engine = "Cabbage"
            else:
                event_url = parse_schej_link(raw_input)
                json_resp = schej_fetch_event_data(event_url)
                timezone_offset = int(self.settings.value("timezone_schej", 1))
                participants, dates, day_ranges = schej_process_data(json_resp, time_offset_hours=timezone_offset)
                self.loaded_engine = "Schej"
            self.loaded_participants = participants
            self.loaded_poll_dates = dates
            self.loaded_day_ranges = day_ranges
            self.accept()
        except Exception as e:
            self.show_error(str(e))

    def show_error(self, message: str):
        """
        Display an error message.
        """
        self.error_label.setText(message)

    def on_show_doc(self):
        """
        Emit the signal from signal.py
        """
        on_show_doc(self)

    def on_update_available(self, remote_version: str):
        """
        Inform that an update is available.
        """
        self.footer.setUpdateAvailable(True)
        QMessageBox.information(
            self,
            "Aktualizacja dostępna",
            f"Nowa wersja {remote_version} jest dostępna!"
        )

    def on_no_update(self):
        """
        Inform that no update is available.
        """
        self.footer.setUpdateAvailable(False)

    def on_update_error(self, error_msg: str):
        """
        Handle update check errors.
        """
        QMessageBox.warning(self, "Błąd sprawdzania aktualizacji", error_msg)
        self.footer.setUpdateAvailable(False)

    def update_spacer(self, height: int):
        """
        Update the spacer widget height.
        """
        self.spacer_widget.setFixedHeight(height)

    def update_logo(self):
        """
        Update the logo label based on the current theme.
        """
        self.default_pixmap = QPixmap(get_logo_path())

    def apply_current_theme(self):
        """
        Load the base stylesheet and the corresponding theme file (e.g., light.qss, dark.qss, dracula.qss, cafe.qss, ocean_light.qss, ocean_dark.qss, high_contrast.qss, firemode.qss),
        perform placeholder substitutions, and apply the resulting stylesheet.
        For the "firemode" theme, use a GIF logo and a larger spacer.
        """
        theme = self.settings.value("theme", "Light")
        theme_file_name = theme.lower().replace(" ", "_") + ".qss"
        base_path = resource_path("styles/base.qss")
        theme_path = resource_path(f"styles/{theme_file_name}")
        try:
            with open(base_path, "r", encoding="utf-8") as f:
                base_style = f.read()
            with open(theme_path, "r", encoding="utf-8") as f:
                theme_style = f.read()
            theme_dict = {}
            for line in theme_style.splitlines():
                line = line.strip()
                if line and not line.startswith("/*") and ":" in line:
                    parts = line.split(":", 1)
                    key = parts[0].strip()
                    value = parts[1].strip().rstrip(";")
                    theme_dict[key] = value
            combined_style = base_style
            for key, value in theme_dict.items():
                combined_style = combined_style.replace(key, value)
            arrow_path = get_icon_path("arrow_down").replace("\\", "/")
            combined_style = combined_style.replace("%ARROW_DOWN%", arrow_path)
            self.setStyleSheet(combined_style)
            self.sidebar.update_icons(initial_mode=True)
            self.update_logo()
        except Exception as e:
            print("Error applying theme:", e)

        # info: Special handling for "firemode" theme
        if theme.lower() == "firemode":
            if self.fire_pixmap.isValid():
                self.logo_label.setMovie(self.fire_pixmap)
                self.fire_pixmap.start()
            else:
                self.logo_label.setPixmap(self.default_pixmap)
            self.update_spacer(158)
        else:
            self.fire_pixmap.stop()
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
            self.update_spacer(5)
