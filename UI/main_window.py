from datetime import time

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QMessageBox,
    QPushButton, QFormLayout, QSpinBox, QDialog, QProgressDialog, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QSettings

from UI.initial_setup_dialog import InitialSetupDialog
from UI.schedule_matrix_widget import ScheduleMatrixWidget
from UI.summary_widget import SummaryListWidget
from UI.footer import FooterWidget
from UI.collapsible_sidebar import CollapsibleSidebar
from UI.signals import on_settings, on_show_doc, on_load_from_csv, on_export_to_csv, on_export_to_html, on_export_to_png

from core.scheduler import build_day_slots, assign_shifts
from core.update_checker import get_update_checker
from core.resources import resource_path, get_icon_path
from core.version import __app_version__


class SolverWorker(QObject):
    """
    Worker for solving shift assignments.
    Emits progress and finished signals.
    """
    finished = pyqtSignal(object, object)
    progress = pyqtSignal(str)

    def __init__(self, participants, slot_list, num_required, min_required,
                max_hours, max_hours_per_day, solver_time_limit, solver_num_threads, parent=None):
        """
        Initialize the worker.
        """
        super().__init__(parent)
        self.participants = participants
        self.slot_list = slot_list
        self.num_required = num_required
        self.min_required = min_required
        self.max_hours = max_hours
        self.max_hours_per_day = max_hours_per_day
        self.solver_time_limit = solver_time_limit
        self.solver_num_threads = solver_num_threads

    def run(self):
        """
        Execute the solver and emit the final result.
        """
        self.progress.emit("Liczenie...")
        schedule_data, total_hrs = assign_shifts(
            participants=self.participants,
            slot_list=self.slot_list,
            num_required=self.num_required,
            min_required=self.min_required,
            max_hours=self.max_hours,
            max_hours_per_day=self.max_hours_per_day,
            solver_time_limit=self.solver_time_limit,
            solver_num_threads=self.solver_num_threads
        )
        self.progress.emit("Zakończono liczenie.")
        self.finished.emit(schedule_data, total_hrs)


class MainWindow(QMainWindow):
    """
    Main application window.
    """
    def __init__(self):
        """
        Initialize the main window.
        """
        super().__init__()
        self.settings = QSettings("Harmobot", "Harmobot")
        self.engine_name = "Cabbage"

        self.setWindowTitle("Harmobot")
        self.resize(1300, 800)

        # Data – will be assigned from the initial setup dialog
        self.participants = []
        self.poll_dates = []
        self.day_ranges = None
        self.full_slots = []
        self.day_slots_dict = {}
        self.current_highlight_person = None

        # Set up central widget and layout
        central_widget = QWidget()
        central_vlayout = QVBoxLayout(central_widget)
        central_vlayout.setContentsMargins(0, 0, 0, 0)
        central_vlayout.setSpacing(0)
        self.setCentralWidget(central_widget)

        # Layout: sidebar + parameter panel + schedule/summary view
        top_widget = QWidget()
        top_hlayout = QHBoxLayout(top_widget)
        top_hlayout.setContentsMargins(0, 0, 0, 0)
        top_hlayout.setSpacing(0)

        self.sidebar = CollapsibleSidebar(initial_mode=False)
        self.sidebar.sig_select_cabbage.connect(self.on_select_cabbage)
        self.sidebar.sig_select_schej.connect(self.on_select_schej)
        self.sidebar.sig_load_csv.connect(self.on_load_from_csv)
        self.sidebar.sig_export_csv.connect(self.on_export_to_csv)
        self.sidebar.sig_export_html.connect(self.on_export_to_html)
        self.sidebar.sig_export_png.connect(self.on_export_to_png)
        self.sidebar.sig_colorize.connect(self.on_sidebar_colorize)
        self.sidebar.sig_toggle_params.connect(self.on_toggle_params_panel)
        self.sidebar.sig_settings.connect(self.on_settings)
        self.sidebar.sig_documentation.connect(self.on_show_doc)
        self.sidebar.sig_go_initial.connect(self.on_go_initial)
        top_hlayout.addWidget(self.sidebar, stretch=0)

        self.param_frame = self._create_param_frame()
        top_hlayout.addWidget(self.param_frame, stretch=0)

        # Schedule and summary
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
        self.summary_widget.personAddRequested.connect(self.on_person_add_requested)
        schedule_vlayout.addWidget(splitter)
        top_hlayout.addWidget(schedule_container, stretch=1)

        central_vlayout.addWidget(top_widget, stretch=1)

        # Footer
        self.footer = FooterWidget()
        self.footer.setFixedHeight(40)
        central_vlayout.addWidget(self.footer, stretch=0)

        # Update checker
        update_checker = get_update_checker()
        self.footer.setUpdateAvailable(update_checker.has_update)

        self.sidebar.disable_api_tabs(True)

        self.apply_current_theme()

        if self.participants and self.poll_dates:
            self.initialize_schedule_table()

    def initialize_schedule_table(self):
        """
        Initialize the schedule table using participants and poll dates.
        """
        shift_duration = 15 if self.engine_name == "Schej" else 30
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
        """
        Create and return the parameter panel widget.
        """
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
        self.num_required_spin.valueChanged.connect(self.validate_requireds)

        self.min_required_spin = QSpinBox()
        self.min_required_spin.setRange(1, 20)
        self.min_required_spin.setValue(1)
        self.min_required_spin.valueChanged.connect(self.validate_requireds)

        self.max_hours_spin = QSpinBox()
        self.max_hours_spin.setRange(0, 24)
        self.max_hours_spin.setValue(4)
        self.max_hours_spin.valueChanged.connect(self.validate_hours)

        self.max_hours_per_day_spin = QSpinBox()
        self.max_hours_per_day_spin.setRange(0, 12)
        self.max_hours_per_day_spin.setValue(2)
        self.max_hours_per_day_spin.valueChanged.connect(self.validate_hours)

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

    def validate_requireds(self):
        """
        Ensure the minimum required does not exceed the desired number.
        """
        num_required = self.num_required_spin.value()
        if self.min_required_spin.value() > num_required:
            self.min_required_spin.setValue(num_required)

    def validate_hours(self):
        """
        Ensure that max hours per day does not exceed total max hours.
        """
        max_hours = self.max_hours_spin.value()
        if self.max_hours_per_day_spin.value() > max_hours:
            self.max_hours_per_day_spin.setValue(max_hours)

    def on_generate_schedule(self):
        """
        Generate the schedule and update the schedule matrix.
        """
        if not self.participants or not self.poll_dates:
            QMessageBox.warning(self, "Brak danych", "Nie ma załadowanych uczestników/dostępności.")
            return

        shift_duration = 15 if self.engine_name == "Schej" else 30

        self.day_slots_dict, self.full_slots = build_day_slots(
            self.participants,
            self.poll_dates,
            shift_duration,
            day_ranges=self.day_ranges
        )
        if not self.full_slots:
            QMessageBox.information(self, "Grafik", "Brak wczytanej dyspozycji.")
            return

        solver_time_limit = int(self.settings.value("processing_time", 15))
        solver_num_threads = int(self.settings.value("max_threads", 4))
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
            num_required=self.num_required_spin.value(),
            min_required=self.min_required_spin.value(),
            max_hours=float(self.max_hours_spin.value()),
            max_hours_per_day=float(self.max_hours_per_day_spin.value()),
            solver_time_limit=solver_time_limit,
            solver_num_threads=solver_num_threads
        )
        self.solver_worker.moveToThread(self.solver_thread)
        self.solver_thread.started.connect(self.solver_worker.run)
        self.solver_worker.finished.connect(self.on_solver_finished)
        self.solver_worker.finished.connect(self.solver_thread.quit)
        self.solver_worker.finished.connect(self.solver_worker.deleteLater)
        self.solver_thread.finished.connect(self.solver_thread.deleteLater)
        self.solver_thread.start()

    def on_solver_finished(self, schedule_data, total_hrs):
        """
        Handle the solver result by updating the schedule matrix and summary.
        """
        self.generate_button.setEnabled(True)
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
        if schedule_data is None:
            QMessageBox.information(self, "Solver", "Nie znaleziono rozwiązania.")
            return

        shift_duration = 15 if self.engine_name == "Schej" else 30
        time_slot_list = self._build_time_slot_list(shift_duration)
        self.schedule_widget.load_schedule_matrix(
            schedule_data=schedule_data,
            participants=self.participants,
            poll_dates=self.poll_dates,
            time_slot_list=time_slot_list
        )
        self.update_summary()

    def _build_time_slot_list(self, shift_duration):
        """
        Build a list of time slots based on full_slots.

        Returns:
            List of tuples (start_time, end_time).
        """
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
        """
        Update the summary widget with current schedule data.
        """
        current_data = self.schedule_widget.get_current_schedule_data()
        self.summary_widget.update_summary(self.participants, current_data, float(self.max_hours_spin.value()))

    def on_select_cabbage(self):
        """
        Switch engine to Cabbage.
        """
        if self.engine_name == "Cabbage":
            return
        self.engine_name = "Cabbage"

    def on_select_schej(self):
        """
        Switch engine to Schej.
        """
        if self.engine_name == "Schej":
            return
        self.engine_name = "Schej"

    def on_person_selected(self, person_name):
        """
        Toggle highlighting for a selected person.
        """
        if self.current_highlight_person == person_name:
            self.schedule_widget.highlight_availability(person_name, enable=False)
            self.current_highlight_person = None
        else:
            if self.current_highlight_person:
                self.schedule_widget.highlight_availability(self.current_highlight_person, enable=False)
            self.schedule_widget.highlight_availability(person_name, enable=True)
            self.current_highlight_person = person_name

    def on_person_add_requested(self, name: str) -> None:
        """
        Slot to handle a new participant addition request.
        It adds the new person as an external participant (with empty availabilities)
        and updates the summary widget to display the new participant with 0 worked hours.
        Args:
            name (str): The name of the new participant.
        """
        new_person = {'name': name, 'availabilities': [], 'ifNeeded': [], 'external': True}
        if not any(p['name'] == name for p in self.participants):
            self.participants.append(new_person)
        self.summary_widget.add_person(name)

    def on_go_initial(self):
        """
        Open the initial setup dialog and reinitialize the schedule if accepted.
        """
        self.hide()
        dlg = InitialSetupDialog()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.engine_name = dlg.loaded_engine
            # note: check right button in sidebar
            if self.engine_name == "Schej":
                self.sidebar.btn_schej.setChecked(True)
                self.sidebar.btn_cabbage.setChecked(False)
            else:
                self.sidebar.btn_cabbage.setChecked(True)
                self.sidebar.btn_schej.setChecked(False)
            self.participants = dlg.loaded_participants
            self.poll_dates = dlg.loaded_poll_dates
            self.day_ranges = dlg.loaded_day_ranges
            self.initialize_schedule_table()
            self.apply_current_theme()
            self.show()
        else:
            self.close()

    def on_settings(self):
        """
        Emit the signal from signal.py
        """
        on_settings(self)

    def on_show_doc(self):
        """
        Emit the signal from signal.py
        """
        on_show_doc(self)

    def on_sidebar_colorize(self):
        """
        Toggle colorize mode in the schedule widget.
        """
        new_state = not self.schedule_widget.colorize_mode
        self.schedule_widget.setColorizeMode(new_state)

    def on_toggle_params_panel(self):
        """
        Toggle the visibility of the parameter panel.
        """
        if self.param_frame.isVisible():
            self.param_frame.hide()
        else:
            self.param_frame.show()

    def on_load_from_csv(self):
        """
        Emit the signal from signal.py
        """
        on_load_from_csv(self)

    def on_export_to_csv(self):
        """
        Emit the signal from signal.py
        """
        on_export_to_csv(self)

    def on_export_to_html(self):
        """
        Emit the signal from signal.py
        """
        on_export_to_html(self)

    def on_export_to_png(self):
        """
        Emit the signal from signal.py
        """
        on_export_to_png(self)

    def apply_current_theme(self):
        """
        Load the base stylesheet and corresponding theme file (e.g., light.qss, dark.qss, dracula.qss, 
        cafe.qss, ocean_light.qss, ocean_dark.qss, high_contrast.qss, firemode.qss),
        perform placeholder substitutions, and apply the resulting stylesheet.
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
            self.sidebar.update_icons(initial_mode=False)
            self.summary_widget.refresh_plus_button_icon()

            self.basic_chip_bg = theme_dict.get("%CHIP_BACKGROUND%", "#E0E0E0")
            self.basic_chip_text = theme_dict.get("%CHIP_TEXT%", "#000000")

            self.schedule_widget.validate_all_cells()
        except Exception as e:
            print("Error applying theme:", e)
