import os
import random
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QDockWidget, QFormLayout, QSpinBox, QPushButton,
    QSplitter, QLabel, QVBoxLayout, QHBoxLayout, QStyle, QProgressDialog
)
from PyQt6.QtCore import (
    Qt, QTimer, QUrl, QThread, pyqtSignal, QObject, QCoreApplication
)
from PyQt6.QtGui import QFont, QDesktopServices

from datetime import time

from core.scheduler import build_day_slots, assign_shifts
from core.version import __app_version__

from UI.schedule_matrix_widget import ScheduleMatrixWidget
from UI.summary_widget import SummaryListWidget
from UI.menu_bar import create_menu_bar
from UI.styles import LIGHT_QSS, FIRE_QSS
from UI.export_handlers import (
    load_from_csv, export_to_csv, export_to_html, export_to_png
)

class SolverWorker(QObject):
    """
    Uruchamia 'assign_shifts' w osobnym wątku.
    Po zakończeniu emituje sygnał 'finished(schedule_data, total_hours)'.
    Sygnał 'progress' służy do komunikatów w trakcie (opcjonalnie).
    """
    finished = pyqtSignal(object, object)
    progress = pyqtSignal(str)

    def __init__(self, participants, slot_list, num_required, min_required,
                max_hours, max_hours_per_day, parent=None):
        super().__init__(parent)
        self.participants = participants
        self.slot_list = slot_list
        self.num_required = num_required
        self.min_required = min_required
        self.max_hours = max_hours
        self.max_hours_per_day = max_hours_per_day
        self._stop_requested = False

    def request_stop(self):
        """
        Zmieniamy flagę `_stop_requested`. 
        (Tu nie jest wykorzystywana do przerwania solvera,
        ale mogłaby być użyta z solver.StopSearch().)
        """
        self._stop_requested = True

    def run(self):
        self.progress.emit("Liczenie...")
        schedule_data, total_hrs = assign_shifts(
            self.participants,
            self.slot_list,
            self.num_required,
            self.min_required,
            self.max_hours,
            self.max_hours_per_day
        )
        self.progress.emit("Zakończono liczenie.")
        self.finished.emit(schedule_data, total_hrs)


class CustomStatusBar(QWidget):
    """
    Dwuwierszowy status bar:
    - dynamic_label (góra) -> komunikaty
    - static_layout (dół) -> info i przycisk pomocy
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fire_mode = False

        self.dynamic_label = QLabel("")
        self.dynamic_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.dynamic_label.setFont(QFont("Segoe UI", 12))
        self.dynamic_label.setStyleSheet("background-color: transparent;")

        self.static_left = QLabel(f"HarmoBot | v{__app_version__} | © 2025")
        self.static_left.setStyleSheet("color: gray; background-color: transparent;")
        self.static_left.setFont(QFont("Segoe UI", 8))

        self.static_right = QLabel("mwalas777@gmail.com")
        self.static_right.setStyleSheet("color: gray; background-color: transparent;")
        self.static_right.setFont(QFont("Segoe UI", 8))

        self.help_button = QPushButton()
        self.help_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion))
        self.help_button.setToolTip("Pomoc")
        self.help_button.setFlat(True)
        self.help_button.setStyleSheet("background: transparent;")
        self.help_button.clicked.connect(self.open_help)

        self.static_layout = QHBoxLayout()
        self.static_layout.setContentsMargins(5, 2, 5, 2)
        self.static_layout.setSpacing(10)
        self.static_layout.addWidget(self.static_left)
        self.static_layout.addStretch()
        self.static_layout.addWidget(self.help_button)
        self.static_layout.addWidget(self.static_right)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.dynamic_label)
        main_layout.addLayout(self.static_layout)

        self.setFixedHeight(60)
        self.setStyleSheet("background-color: #F6F6F6;")

    def set_fire_mode(self, fire_mode):
        self.fire_mode = fire_mode
        if self.fire_mode:
            self.setStyleSheet("background-color: #1e1e1e;")
        else:
            self.setStyleSheet("background-color: #F6F6F6;")

    def show_message(self, message, error=False):
        if error:
            self.dynamic_label.setStyleSheet("color: red; background-color: transparent;")
        elif self.fire_mode:
            self.dynamic_label.setStyleSheet("color: white; background-color: transparent;")
        else:
            self.dynamic_label.setStyleSheet("color: black; background-color: transparent;")
        self.dynamic_label.setText(message)

    def clear_message(self):
        self.dynamic_label.setText("")

    def open_help(self):
        pdf_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "instruction.pdf")
        if os.path.exists(pdf_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
        else:
            self.show_message("Instrukcja? Jeszcze czego... Tu są 4 przyciski na krzyż c:", error=True)


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji HarmoBot.
    Zawiera panel z parametrami (dock), menu, główny obszar (Schedule + Summary)
    i niestandardowy status bar.
    """
    def __init__(self, fire_mode=False):
        super().__init__()
        self.setWindowTitle("HarmoBot")
        self.resize(1300, 800)

        self.fire_mode = fire_mode
        self.participants = []
        self.poll_dates = []
        self.day_slots_dict = {}
        self.full_slots = []
        self.current_highlight_person = None

        self.param_dock = self._create_left_dock()
        self._create_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.schedule_widget = ScheduleMatrixWidget()
        splitter.addWidget(self.schedule_widget)

        self.summary_widget = SummaryListWidget()
        splitter.addWidget(self.summary_widget)

        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([800, 180])
        main_layout.addWidget(splitter)

        self.custom_status_bar = CustomStatusBar()
        main_layout.addWidget(self.custom_status_bar)

        self.schedule_widget.scheduleChanged.connect(self.update_summary)
        self.summary_widget.personSelected.connect(self.on_person_selected)

        self.custom_status_bar.set_fire_mode(self.fire_mode)
        if self.fire_mode:
            self.show_notification(random.choice([
                "🔥 FireMode 🔥",
                "TEMPERATURA 🔥",
                "Harmo<s>BOT</s>HOT.",
                "Ale hotówa. 🔥",
                "HOT HOT HOT 🔥",
            ]), duration=3000)
            self.apply_fire_mode_theme()
        else:
            self.show_notification(random.choice([
                "Bang bang!",
                "Jasność",
                "Tryb hot wyłączony",
            ]), duration=3000)
            self.apply_light_theme()

    def _create_menu_bar(self):
        create_menu_bar(self)

    def on_toggle_colorize_chips(self, checked: bool):
        self.schedule_widget.setColorizeMode(checked)
        msg = "Kolorowanie chipów aktywne." if checked else "Kolorowanie chipów wyłączone."
        self.show_notification(msg, duration=3000)

    def _create_left_dock(self):
        dock = QDockWidget("Parametry", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        param_widget = QWidget()
        form = QFormLayout(param_widget)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self.num_required_spin = QSpinBox()
        self.num_required_spin.setRange(1, 20)
        self.num_required_spin.setValue(2)
        self.num_required_spin.valueChanged.connect(self.validate_num_required)

        self.min_required_spin = QSpinBox()
        self.min_required_spin.setRange(1, 20)
        self.min_required_spin.setValue(1)
        self.min_required_spin.valueChanged.connect(self.validate_min_required)

        # self.shift_duration_spin = QSpinBox()

        self.max_hours_spin = QSpinBox()
        self.max_hours_spin.setRange(0, 24)
        self.max_hours_spin.setValue(4)
        self.max_hours_spin.valueChanged.connect(self.validate_max_hours)

        self.max_hours_per_day_spin = QSpinBox()
        self.max_hours_per_day_spin.setRange(0, 12)
        self.max_hours_per_day_spin.setValue(2)
        self.max_hours_per_day_spin.valueChanged.connect(self.validate_max_hours_per_day)

        form.addRow("Pożądana liczba osób/slot:", self.num_required_spin)
        form.addRow("Minimalna liczba osób/slot:", self.min_required_spin)
        # form.addRow("Długość slotu (min):", self.shift_duration_spin)
        form.addRow("Max godzin/osoba (łącznie):", self.max_hours_spin)
        form.addRow("Max godzin/osoba/dzień:", self.max_hours_per_day_spin)

        self.generate_button = QPushButton("Generuj grafik")
        self.generate_button.setFixedHeight(40)
        self.generate_button.clicked.connect(self.on_generate_schedule)
        form.addRow(self.generate_button)

        dock.setWidget(param_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        return dock

    def validate_num_required(self):
        num_required = self.num_required_spin.value()
        if self.min_required_spin.value() > num_required:
            self.min_required_spin.setValue(num_required)
            self.show_notification(
                "Pożądana liczba osób/slot nie może być mniejsza niż minimalna liczba osób/slot.",
                error=True
            )

    def validate_min_required(self):
        num_required = self.num_required_spin.value()
        if self.min_required_spin.value() > num_required:
            self.min_required_spin.setValue(num_required)
            self.show_notification(
                "Pożądana liczba osób/slot nie może być mniejsza niż minimalna liczba osób/slot.",
                error=True
            )

    def validate_max_hours(self):
        max_hours = self.max_hours_spin.value()
        if self.max_hours_per_day_spin.value() > max_hours:
            self.max_hours_per_day_spin.setValue(max_hours)
            self.show_notification(
                "Max godzin/osoba/dzień nie może przekraczać Max godzin/osoba (łącznie).",
                error=True
            )

    def validate_max_hours_per_day(self):
        max_hours = self.max_hours_spin.value()
        if self.max_hours_per_day_spin.value() > max_hours:
            self.max_hours_per_day_spin.setValue(max_hours)
            self.show_notification(
                "Max godzin/osoba/dzień nie może przekraczać Max godzin/osoba (łącznie).",
                error=True
            )

    def on_toggle_fire_mode(self, checked: bool):
        self.fire_mode = checked
        self.custom_status_bar.set_fire_mode(self.fire_mode)

        fire_msgs = [
            "🔥 FireMode 🔥",
            "TEMPERATURA 🔥",
            "Harmo<s>BOT</s>HOT.",
            "Ale hotówa. 🔥",
        ]
        light_msgs = [
            "Bang bang!",
            "Jasność",
            "Tryb hot wyłączony",
            "Nie jesteś już hot :c",
        ]
        if self.fire_mode:
            self.apply_fire_mode_theme()
            msg = random.choice(fire_msgs)
        else:
            self.apply_light_theme()
            msg = random.choice(light_msgs)

        self.schedule_widget.validate_all_cells()
        self.show_notification(msg, duration=3000)

    def apply_light_theme(self):
        self.setStyleSheet(LIGHT_QSS)

    def apply_fire_mode_theme(self):
        self.setStyleSheet(FIRE_QSS)

    def show_notification(self, message, duration=3000, error=False):
        self.custom_status_bar.show_message(message, error)
        QTimer.singleShot(duration, self.custom_status_bar.clear_message)

    def hide_notification(self):
        self.custom_status_bar.clear_message()

    def on_generate_schedule(self):
        """
        Uruchamia solver w wątku (SolverWorker) z QProgressDialog informującym,
        że trwa generowanie grafiku.
        """
        if not self.participants or not self.poll_dates:
            self.show_notification("Brak uczestników lub dat.", duration=3000, error=True)
            return

        num_required = self.num_required_spin.value()
        min_required = self.min_required_spin.value()
        shift_duration = 30
        max_hours = float(self.max_hours_spin.value())
        max_hours_per_day = float(self.max_hours_per_day_spin.value())

        if not self.full_slots:
            self.day_slots_dict, self.full_slots = build_day_slots(
                self.participants, self.poll_dates, shift_duration
            )
            if not self.full_slots:
                self.show_notification("Brak slotów do obsadzenia.", duration=3000, error=True)
                return

        self.generate_button.setEnabled(False)
        self.show_notification("Trwa generowanie grafiku...", duration=15000)

        self.progress_dialog = QProgressDialog("Generowanie grafiku w toku...", None, 0, 0, self)
        self.progress_dialog.setCancelButtonText(None)
        self.progress_dialog.setWindowTitle("Generowanie grafiku")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        self.progress_dialog.show()

        self.solver_thread = QThread(self)
        self.solver_worker = SolverWorker(
            participants=self.participants,
            slot_list=self.full_slots,
            num_required=num_required,
            min_required=min_required,
            max_hours=max_hours,
            max_hours_per_day=max_hours_per_day
        )
        self.solver_worker.moveToThread(self.solver_thread)

        self.solver_thread.started.connect(self.solver_worker.run)
        self.solver_worker.finished.connect(self.on_solver_finished)
        self.solver_worker.finished.connect(self.solver_thread.quit)
        self.solver_worker.finished.connect(self.solver_worker.deleteLater)
        self.solver_thread.finished.connect(self.solver_thread.deleteLater)
        self.solver_worker.progress.connect(self.on_solver_progress)

        self.solver_thread.start()

    def on_solver_progress(self, message: str):
        self.progress_dialog.setLabelText(message)
        QCoreApplication.processEvents()

    def on_solver_finished(self, schedule_data, total_hrs):
        self.generate_button.setEnabled(True)
        self.hide_notification()

        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()

        if schedule_data is None:
            self.show_notification("Solver nie znalazł rozwiązania.", duration=4000, error=True)
            return

        shift_duration = 30
        self.schedule_widget.load_schedule_matrix(
            schedule_data=schedule_data,
            participants=self.participants,
            poll_dates=self.poll_dates,
            time_slot_list=self._build_time_slot_list(shift_duration)
        )
        self.schedule_widget.setMaxHours(float(self.max_hours_spin.value()))
        self.update_summary()
        self.show_notification("Wygenerowano grafik.", duration=3000)

    def _build_time_slot_list(self, shift_duration):
        if not self.full_slots:
            return []

        def t2m(tt):
            return tt.hour * 60 + tt.minute

        all_starts = [slot[0] for slot in self.full_slots]
        all_ends = [slot[1] for slot in self.full_slots]
        start_min = min(t2m(dt.time()) for dt in all_starts)
        end_min = max(t2m(dt.time()) for dt in all_ends)

        time_slot_list = []
        cur = start_min
        while cur < end_min:
            nxt = cur + shift_duration
            if nxt > end_min:
                nxt = end_min
            sh, sm = divmod(cur, 60)
            eh, em = divmod(nxt, 60)
            t1 = time(sh, sm)
            t2 = time(eh, em)
            time_slot_list.append((t1, t2))
            cur = nxt
        return time_slot_list

    def update_summary(self):
        current_data = self.schedule_widget.get_current_schedule_data()
        max_hours = float(self.max_hours_spin.value())
        self.summary_widget.update_summary(self.participants, current_data, max_hours)

    def on_person_selected(self, name):
        if self.current_highlight_person == name:
            self.schedule_widget.highlight_availability(name, enable=False)
            self.current_highlight_person = None
        else:
            if self.current_highlight_person:
                self.schedule_widget.highlight_availability(self.current_highlight_person, enable=False)
            self.schedule_widget.highlight_availability(name, enable=True)
            self.current_highlight_person = name

    def load_from_csv(self):
        load_from_csv(self)

    def export_to_csv(self):
        export_to_csv(self)

    def export_to_html(self):
        export_to_html(self)

    def export_to_png(self):
        export_to_png(self)
