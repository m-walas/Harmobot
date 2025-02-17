from datetime import time

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QMessageBox,
    QPushButton, QFormLayout, QSpinBox, QDialog, QProgressDialog, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QUrl
from PyQt6.QtGui import QDesktopServices

from UI.initial_setup_dialog import InitialSetupDialog
from UI.schedule_matrix_widget import ScheduleMatrixWidget
from UI.summary_widget import SummaryListWidget
from UI.footer import FooterWidget
from UI.collapsible_sidebar import CollapsibleSidebar
from UI.styles import LIGHT_QSS, FIRE_QSS

from core.export_handlers import load_from_csv, export_to_csv, export_to_html, export_to_png
from core.scheduler import build_day_slots, assign_shifts
from core.update_checker import get_update_checker
from core.version import __app_version__

class SolverWorker(QObject):
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

class MainWindow(QMainWindow):
    """
    Główne okno aplikacji.
    """
    def __init__(self, fire_mode=False):
        super().__init__()
        self.fire_mode = fire_mode
        self.engine_name = "Lettuce"

        self.setWindowTitle("Harmobot")
        self.resize(1300, 800)

        # Dane – zostaną przypisane z initial_setup_dialog
        self.participants = []
        self.poll_dates = []
        self.day_ranges = None
        self.full_slots = []
        self.day_slots_dict = {}
        self.current_highlight_person = None

        # Ustawienie głównego widgetu i layoutu
        central_widget = QWidget()
        central_vlayout = QVBoxLayout(central_widget)
        central_vlayout.setContentsMargins(0, 0, 0, 0)
        central_vlayout.setSpacing(0)
        self.setCentralWidget(central_widget)

        # Layout: sidebar + panel parametrów + schedule/sumaryczny widok
        top_widget = QWidget()
        top_hlayout = QHBoxLayout(top_widget)
        top_hlayout.setContentsMargins(0, 0, 0, 0)
        top_hlayout.setSpacing(0)

        self.sidebar = CollapsibleSidebar(initial_mode=False)
        self.sidebar.sig_select_lettuce.connect(self.on_select_lettuce)
        self.sidebar.sig_select_schej.connect(self.on_select_schej)
        self.sidebar.sig_load_csv.connect(self.load_from_csv)
        self.sidebar.sig_export_csv.connect(self.export_to_csv)
        self.sidebar.sig_export_html.connect(self.export_to_html)
        self.sidebar.sig_export_png.connect(self.export_to_png)
        self.sidebar.sig_fire_mode.connect(self.on_sidebar_fire_mode)
        self.sidebar.sig_colorize.connect(self.on_sidebar_colorize)
        self.sidebar.sig_toggle_params.connect(self.on_toggle_params_panel)
        self.sidebar.sig_documentation.connect(self.on_show_doc_main)
        self.sidebar.sig_go_initial.connect(self.on_go_initial)
        top_hlayout.addWidget(self.sidebar, stretch=0)

        self.param_frame = self._create_param_frame()
        top_hlayout.addWidget(self.param_frame, stretch=0)

        # schedule + summary
        schedule_container = QWidget()
        schedule_vlayout = QVBoxLayout(schedule_container)
        schedule_vlayout.setContentsMargins(0, 0, 0, 0)
        schedule_vlayout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.schedule_widget = ScheduleMatrixWidget()
        splitter.addWidget(self.schedule_widget)
        self.summary_widget = SummaryListWidget()
        splitter.addWidget(self.summary_widget)
        splitter.setSizes([800, 180])
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        self.schedule_widget.scheduleChanged.connect(self.update_summary)
        self.summary_widget.personSelected.connect(self.on_person_selected)
        schedule_vlayout.addWidget(splitter)
        top_hlayout.addWidget(schedule_container, stretch=1)

        central_vlayout.addWidget(top_widget, stretch=1)

        # Stopka
        self.footer = FooterWidget()
        self.footer.setFixedHeight(40)
        central_vlayout.addWidget(self.footer, stretch=0)

        # Update checker
        update_checker = get_update_checker()
        if update_checker.has_update:
            self.footer.setUpdateAvailable(True)
        else:
            self.footer.setUpdateAvailable(False)

        self.sidebar.disable_api_tabs(True)

        if self.fire_mode:
            self.apply_fire_mode_theme()
            self.sidebar.set_dark_mode_icon(dark=True)
        else:
            self.apply_light_theme()
            self.sidebar.set_dark_mode_icon(dark=False)

        if self.participants and self.poll_dates:
            self.initialize_schedule_table()

    def initialize_schedule_table(self):
        """Generuje pustą tabelę harmonogramu – sloty obliczane według engine."""
        if self.engine_name == "Schej":
            shift_duration = 15
        else:
            shift_duration = 30
        self.day_slots_dict, self.full_slots = build_day_slots(
            self.participants,
            self.poll_dates,
            shift_duration,
            day_ranges=self.day_ranges
        )
        schedule_data = []
        for sdt, edt in self.full_slots:
            schedule_data.append({
                'Shift Start': sdt,
                'Shift End': edt,
                'Assigned To': ""
            })
        time_slot_list = self._build_time_slot_list(shift_duration)
        self.schedule_widget.load_schedule_matrix(
            schedule_data=schedule_data,
            participants=self.participants,
            poll_dates=self.poll_dates,
            time_slot_list=time_slot_list
        )

    def _create_param_frame(self):
        param_frame = QFrame()
        param_vlayout = QVBoxLayout(param_frame)
        param_vlayout.setContentsMargins(8, 8, 8, 8)
        param_vlayout.setSpacing(8)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self.num_required_spin = QSpinBox()
        self.num_required_spin.setRange(1, 20)
        self.num_required_spin.setValue(2)
        self.num_required_spin.valueChanged.connect(self.validate_num_required)

        self.min_required_spin = QSpinBox()
        self.min_required_spin.setRange(1, 20)
        self.min_required_spin.setValue(1)
        self.min_required_spin.valueChanged.connect(self.validate_min_required)

        self.max_hours_spin = QSpinBox()
        self.max_hours_spin.setRange(0, 24)
        self.max_hours_spin.setValue(4)
        self.max_hours_spin.valueChanged.connect(self.validate_max_hours)

        self.max_hours_per_day_spin = QSpinBox()
        self.max_hours_per_day_spin.setRange(0, 12)
        self.max_hours_per_day_spin.setValue(2)
        self.max_hours_per_day_spin.valueChanged.connect(self.validate_max_hours_per_day)

        form_layout.addRow("Pożądana liczba osób:", self.num_required_spin)
        form_layout.addRow("Minimalna liczba:", self.min_required_spin)
        form_layout.addRow("Max godzin/osoba:", self.max_hours_spin)
        form_layout.addRow("Max godz/os/dzień:", self.max_hours_per_day_spin)

        self.generate_button = QPushButton("Generuj grafik")
        self.generate_button.setFixedHeight(40)
        self.generate_button.clicked.connect(self.on_generate_schedule)
        form_layout.addRow(self.generate_button)
        param_vlayout.addLayout(form_layout)
        return param_frame

    def validate_num_required(self):
        num_required = self.num_required_spin.value()
        if self.min_required_spin.value() > num_required:
            self.min_required_spin.setValue(num_required)

    def validate_min_required(self):
        num_required = self.num_required_spin.value()
        if self.min_required_spin.value() > num_required:
            self.min_required_spin.setValue(num_required)

    def validate_max_hours(self):
        max_hours = self.max_hours_spin.value()
        if self.max_hours_per_day_spin.value() > max_hours:
            self.max_hours_per_day_spin.setValue(max_hours)

    def validate_max_hours_per_day(self):
        max_hours = self.max_hours_spin.value()
        if self.max_hours_per_day_spin.value() > max_hours:
            self.max_hours_per_day_spin.setValue(max_hours)

    def on_generate_schedule(self):
        if not self.participants or not self.poll_dates:
            QMessageBox.warning(self, "Brak danych", "Nie ma załadowanych uczestników/daty.")
            return

        num_required = self.num_required_spin.value()
        min_required = self.min_required_spin.value()
        max_hours = float(self.max_hours_spin.value())
        max_hours_per_day = float(self.max_hours_per_day_spin.value())

        if self.engine_name == "Schej":
            shift_duration = 15
        else:
            shift_duration = 30

        self.day_slots_dict, self.full_slots = build_day_slots(
            self.participants,
            self.poll_dates,
            shift_duration,
            day_ranges=self.day_ranges
        )
        if not self.full_slots:
            QMessageBox.information(self, "Grafik", "Brak slotów do generowania.")
            return

        self.generate_button.setEnabled(False)
        self.progress_dialog = QProgressDialog("Liczenie...", None, 0, 0, self)
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
        self.solver_thread.start()

    def on_solver_finished(self, schedule_data, total_hrs):
        self.generate_button.setEnabled(True)
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        if schedule_data is None:
            QMessageBox.information(self, "Solver", "Nie znaleziono rozwiązania.")
            return

        if self.engine_name == "Schej":
            shift_duration = 15
        else:
            shift_duration = 30

        time_slot_list = self._build_time_slot_list(shift_duration)
        self.schedule_widget.load_schedule_matrix(
            schedule_data=schedule_data,
            participants=self.participants,
            poll_dates=self.poll_dates,
            time_slot_list=time_slot_list
        )
        self.update_summary()

    def _build_time_slot_list(self, shift_duration):
        if not self.full_slots:
            return []
        def t2m(dt):
            return dt.hour * 60 + dt.minute
        all_starts = [slot[0] for slot in self.full_slots]
        all_ends = [slot[1] for slot in self.full_slots]
        start_min = min(t2m(s) for s in all_starts)
        end_min = max(t2m(e) for e in all_ends)
        slots_list = []
        cur = start_min
        while cur < end_min:
            nxt = cur + shift_duration
            if nxt > end_min:
                nxt = end_min
            sh, sm = divmod(cur, 60)
            eh, em = divmod(nxt, 60)
            slots_list.append((time(sh, sm), time(eh, em)))
            cur = nxt
        return slots_list

    def update_summary(self):
        current_data = self.schedule_widget.get_current_schedule_data()
        self.summary_widget.update_summary(self.participants, current_data, float(self.max_hours_spin.value()))

    def on_select_lettuce(self):
        if self.engine_name == "Lettuce":
            return
        self.engine_name = "Lettuce"

    def on_select_schej(self):
        if self.engine_name == "Schej":
            return
        self.engine_name = "Schej"

    def on_person_selected(self, person_name):
        if self.current_highlight_person == person_name:
            self.schedule_widget.highlight_availability(person_name, enable=False)
            self.current_highlight_person = None
        else:
            if self.current_highlight_person:
                self.schedule_widget.highlight_availability(self.current_highlight_person, enable=False)
            self.schedule_widget.highlight_availability(person_name, enable=True)
            self.current_highlight_person = person_name

    def on_go_initial(self):
        self.hide()
        dlg = InitialSetupDialog()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.engine_name = dlg.loaded_engine
            self.participants = dlg.loaded_participants
            self.poll_dates = dlg.loaded_poll_dates
            self.day_ranges = dlg.loaded_day_ranges
            self.initialize_schedule_table()
            self.show()
        else:
            self.close()

    def on_show_doc_main(self):
        reply = QMessageBox.question(
            self,
            "Otwieranie dokumentacji",
            "Aplikacja otworzy link GitHub. Kontynuować?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl("https://github.com/m-walas/harmobot"))

    def on_sidebar_fire_mode(self):
        new_state = not self.fire_mode
        self.on_toggle_fire_mode(new_state)

    def on_toggle_fire_mode(self, checked: bool):
        self.fire_mode = checked
        if self.fire_mode:
            self.apply_fire_mode_theme()
        else:
            self.apply_light_theme()
        self.schedule_widget.validate_all_cells()

    def on_sidebar_colorize(self):
        new_state = not self.schedule_widget.colorize_mode
        self.schedule_widget.setColorizeMode(new_state)

    def on_toggle_params_panel(self):
        if self.param_frame.isVisible():
            self.param_frame.hide()
        else:
            self.param_frame.show()

    def load_from_csv(self):
        load_from_csv(self)

    def export_to_csv(self):
        export_to_csv(self)

    def export_to_html(self):
        export_to_html(self)

    def export_to_png(self):
        export_to_png(self)

    def apply_light_theme(self):
        self.setStyleSheet(LIGHT_QSS)

    def apply_fire_mode_theme(self):
        self.setStyleSheet(FIRE_QSS)
