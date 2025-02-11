from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QFileDialog, QHBoxLayout, QSpacerItem, QSizePolicy, QWidget
)
from PyQt6.QtGui import QPixmap, QMovie, QCursor, QFont
from PyQt6.QtCore import Qt, QSize

from datetime import datetime
import sys
import os

from core.lettuce_service import fetch_event_data, process_data
from core.scheduler import build_day_slots
from core.version import __app_version__

from UI.styles import LIGHT_QSS, FIRE_QSS


class InitialSetupDialog(QDialog):
    """
    Dialog startowy dla aplikacji HarmoBot.
    Pozwala wprowadzić Event ID (i pobrać dane),
    wczytać harmonogram z pliku CSV oraz włączyć tryb FireMode.
    
    Po załadowaniu danych ustawia atrybuty loaded_* i wywołuje accept().
    """

    def resource_path(self, relative_path):
        """
        Zwraca ścieżkę absolutną do zasobu (np. pliku graficznego).
        Obsługuje zarówno środowisko developerskie, jak i PyInstaller.
        
        Parametr:
            relative_path (str): ścieżka względna do zasobu

        Zwraca:
            str: ścieżka absolutna w systemie plików
        """
        try:
            base_path = sys._MEIPASS  # PyInstaller
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def __init__(self, parent=None):
        """
        Inicjalizuje dialog, ustawia layout, logo, pola tekstowe, przyciski
        i stopkę z informacjami.
        """
        super().__init__(parent)
        self.setWindowTitle("HarmoBot")
        self.setModal(True)
        self.resize(600, 500)

        self.fire_mode = False

        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 40, 40, 20)

        # Logo
        self.logo_label = QLabel()
        self.default_pixmap = QPixmap(self.resource_path("assets/harmobot_logo_big.png"))
        self.fire_pixmap = QMovie(self.resource_path("assets/harmobot_fire.gif"))
        if self.default_pixmap.isNull():
            self.logo_label.setText("Logo Here")
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self.logo_label.setPixmap(
                self.default_pixmap.scaled(
                    250, 250,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.logo_label, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Sekcja wprowadzania Event ID
        event_section = QWidget()
        event_layout = QVBoxLayout()
        event_layout.setSpacing(15)

        event_id_layout = QHBoxLayout()
        event_id_label = QLabel("Event ID:")
        event_id_label.setFont(QFont("Segoe UI", 10))

        self.event_id_edit = QLineEdit()
        self.event_id_edit.setPlaceholderText("Wprowadź Event ID")
        self.event_id_edit.textChanged.connect(self.toggle_fetch_button)

        event_id_layout.addWidget(event_id_label)
        event_id_layout.addWidget(self.event_id_edit)
        event_layout.addLayout(event_id_layout)

        self.fetch_button = QPushButton("Pobierz dane")
        self.fetch_button.setFixedHeight(35)
        self.fetch_button.setEnabled(False)
        self.fetch_button.setFont(QFont("Segoe UI", 10))
        fetch_icon_path = "assets/icons/download.png"
        fetch_icon = QPixmap(fetch_icon_path)
        if not fetch_icon.isNull():
            self.fetch_button.setIcon(
                fetch_icon.scaled(
                    20, 20,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
            self.fetch_button.setIconSize(QSize(20, 20))
        self.fetch_button.clicked.connect(self.on_fetch_data)
        event_layout.addWidget(self.fetch_button)

        event_section.setLayout(event_layout)
        main_layout.addWidget(event_section, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Etykieta błędów
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red; font-size: 10px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.error_label)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Separator
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #E0E0E0; border: none;")
        main_layout.addWidget(separator)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Stopka (FireMode, CSV, prawa autorskie)
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(20)

        self.fire_mode_button = QPushButton("FireMode")
        self.fire_mode_button.setToolTip("Tylko dla prawdziwych samorządowiczów")
        self.fire_mode_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.fire_mode_button.setFixedSize(QSize(100, 35))
        self.fire_mode_button.setFont(QFont("Segoe UI", 9))

        fire_mode_icon_path = "assets/icons/firemode.png"
        fire_mode_icon = QPixmap(fire_mode_icon_path)
        if not fire_mode_icon.isNull():
            self.fire_mode_button.setIcon(
                fire_mode_icon.scaled(
                    20, 20,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
            self.fire_mode_button.setIconSize(QSize(20, 20))
        self.fire_mode_button.clicked.connect(self.toggle_fire_mode)
        footer_layout.addWidget(self.fire_mode_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.load_csv_button = QPushButton("Wczytaj CSV")
        self.load_csv_button.setToolTip("Dodaj istniejący harmonogram z pliku CSV")
        self.load_csv_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.load_csv_button.setFixedSize(QSize(120, 35))
        self.load_csv_button.setFont(QFont("Segoe UI", 9))

        csv_icon_path = "assets/icons/csv.png"
        csv_icon = QPixmap(csv_icon_path)
        if not csv_icon.isNull():
            self.load_csv_button.setIcon(
                csv_icon.scaled(
                    20, 20,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
            self.load_csv_button.setIconSize(QSize(20, 20))
        self.load_csv_button.clicked.connect(self.on_load_csv)
        footer_layout.addWidget(self.load_csv_button, alignment=Qt.AlignmentFlag.AlignLeft)

        footer_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        copyright_label = QLabel(f"© 2025 mwalas | v{__app_version__}")
        copyright_label.setStyleSheet("font-size: 9px; color: #666666;")
        footer_layout.addWidget(
            copyright_label,
            alignment=Qt.AlignmentFlag.AlignRight
        )

        main_layout.addLayout(footer_layout)
        self.setLayout(main_layout)

        # Pola do przechowania załadowanych danych
        self.loaded_schedule_data = None
        self.loaded_participants = None
        self.loaded_poll_dates = None
        self.loaded_time_slot_list = None
        self.loaded_day_slots_dict = None
        self.loaded_full_slots = None

    def toggle_fire_mode(self):
        """
        Przełącza styl okna (FireMode) i zmienia wyświetlane logo
        (statyczne -> animowane) w zależności od stanu self.fire_mode.
        """
        if not self.fire_mode:
            self.fire_mode = True
            self.setStyleSheet(FIRE_QSS)

            if not self.fire_pixmap.isValid():
                self.show_error("Nie można załadować animowanego logo FireMode.")
                return
            self.logo_label.clear()
            self.logo_label.setMovie(self.fire_pixmap)
            self.fire_pixmap.start()
        else:
            self.fire_mode = False
            self.setStyleSheet(LIGHT_QSS)

            if self.fire_pixmap.isValid():
                self.fire_pixmap.stop()
            self.logo_label.setMovie(None)
            self.logo_label.setPixmap(
                self.default_pixmap.scaled(
                    250, 250,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )

    def toggle_fetch_button(self, text: str):
        self.fetch_button.setEnabled(bool(text.strip()))

    def on_fetch_data(self):
        """
        Pobiera dane eventu z zewn. źródła i tworzy sloty czasowe.
        Uzupełnia wewnętrzne atrybuty loaded_* i wywołuje accept().
        """
        event_id = self.event_id_edit.text().strip()
        token = ""
        offset_hours = 0

        if not event_id:
            self.show_error("Proszę wpisać Event ID.")
            return

        try:
            json_resp = fetch_event_data(event_id, token)
            participants, dates = process_data(json_resp, offset_hours)
            if not participants:
                self.show_error("Brak uczestników w danych.")
                return

            shift_duration = 30
            day_slots_dict, full_slots = build_day_slots(participants, dates, shift_duration)
            schedule_data = []
            for (start_dt, end_dt) in full_slots:
                schedule_data.append({
                    'Shift Start': start_dt,
                    'Shift End': end_dt,
                    'Assigned To': ""
                })

            self.loaded_schedule_data = schedule_data
            self.loaded_participants = participants
            self.loaded_poll_dates = dates
            self.loaded_time_slot_list = self._build_time_slot_list(full_slots, shift_duration)
            self.loaded_day_slots_dict = day_slots_dict
            self.loaded_full_slots = full_slots

            self.accept()

        except Exception as e:
            self.show_error(str(e))

    def on_load_csv(self):
        """
        Wczytuje dane harmonogramu z pliku CSV w formacie:
        Data;Start;Koniec;Osoby
        Zapisuje je w polach loaded_* i wywołuje accept() po pomyślnym odczycie.
        """
        filepath, _ = QFileDialog.getOpenFileName(self, "Wczytaj CSV", "", "CSV Files (*.csv)")
        if not filepath:
            return

        try:
            import csv
            schedule_data = []
            days_set = set()
            times_set = set()

            with open(filepath, "r", newline='', encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=';')
                header = next(reader, None)
                if not header or len(header) < 4:
                    self.show_error("Nieprawidłowy nagłówek CSV.")
                    return

                for row in reader:
                    if len(row) < 4:
                        continue
                    day_str = row[0].strip()
                    start_str = row[1].strip()
                    end_str = row[2].strip()
                    assigned_str = row[3].strip()

                    try:
                        y, m, d = map(int, day_str.split('-'))
                        sh, sm = map(int, start_str.split(':'))
                        eh, em = map(int, end_str.split(':'))
                        sdt = datetime(y, m, d, sh, sm)
                        edt = datetime(y, m, d, eh, em)
                    except:
                        continue

                    schedule_data.append({
                        'Shift Start': sdt,
                        'Shift End': edt,
                        'Assigned To': assigned_str
                    })
                    days_set.add(day_str)
                    times_set.add((start_str, end_str))

            participants = set()
            for item in schedule_data:
                assigned = item['Assigned To']
                names = [n.strip() for n in assigned.split(',') if n.strip()]
                for name in names:
                    participants.add(name)

            participants = [{'name': name, 'availabilities': []} for name in sorted(participants)]
            poll_dates = sorted(days_set)

            full_slots = sorted(
                [(item['Shift Start'], item['Shift End']) for item in schedule_data],
                key=lambda x: x[0]
            )

            shift_duration = 30
            time_slot_list = self._build_time_slot_list(full_slots, shift_duration)
            day_slots_dict, built_full_slots = build_day_slots(participants, poll_dates, shift_duration)

            self.loaded_schedule_data = schedule_data
            self.loaded_participants = participants
            self.loaded_poll_dates = poll_dates
            self.loaded_time_slot_list = time_slot_list
            self.loaded_day_slots_dict = day_slots_dict
            self.loaded_full_slots = built_full_slots

            self.accept()

        except Exception as e:
            self.show_error(str(e))

    def show_error(self, message: str):
        self.error_label.setText(message)

    def _build_time_slot_list(self, full_slots, shift_duration):
        """
        Tworzy listę krotek (start_time, end_time) na podstawie
        listy slotów (start_datetime, end_datetime).
        
        Parametry:
            - full_slots: lista par (datetime, datetime)
            - shift_duration: długość slotu w minutach
        
        Zwraca:
            list[tuple(time, time)]
        """
        if not full_slots:
            return []
        times = sorted(set((slot[0].time(), slot[1].time()) for slot in full_slots))
        return list(times)
