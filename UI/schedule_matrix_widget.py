from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QWidget,
    QHBoxLayout, QInputDialog
)
from PyQt6.QtCore import pyqtSignal
from datetime import datetime
from collections import defaultdict
import random

from UI.occupant_chip import OccupantChip

class ScheduleMatrixWidget(QTableWidget):
    """
    A QTableWidget displaying occupant chips (OccupantChip) in its cells.
    The occupant_data dict maps (row, col) to a list of occupant names (list[str]).

    When colorize_mode is True, occupant colors are assigned randomly.
    When colorize_mode is False, the basic chip colors are taken from the current theme
    (via main window attributes basic_chip_bg and basic_chip_text) while special states are overridden:
        - Participants not in the provided list are highlighted in yellow.
        - If a participant exceeds the max hours or has no availability overlap, highlighted in red.
        - Otherwise, styling depends on the current theme.
    The highlight_availability method sets a green (or yellow) background for cells overlapping a person's availability.
    """

    scheduleChanged = pyqtSignal()

    def __init__(self, parent=None):
        """
        Initializes the ScheduleMatrixWidget.
        """
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.participants = []
        self.date_list = []
        self.time_slot_list = []
        self.max_hours = 0.0

        self.occupant_data = {}

        self.current_highlight_person = None

        self.occupant_data_color_map = {}
        self.colorize_mode = False

        # Set default row and column sizes
        self.verticalHeader().setDefaultSectionSize(30)
        self.horizontalHeader().setDefaultSectionSize(110)
        self.horizontalHeader().setMinimumSectionSize(100)

    def setMaxHours(self, val):
        """
        Sets the maximum allowed hours.

        Args:
            val: Maximum hours value.
        """
        self.max_hours = val

    def load_schedule_matrix(self, schedule_data, participants, poll_dates, time_slot_list):
        """
        Loads the schedule matrix from the provided data.

        Args:
            schedule_data: List of dictionaries containing shift data.
            participants: List of participant dictionaries (each must contain a 'name' key).
            poll_dates: List of date strings.
            time_slot_list: List of time slot tuples (start, end) as time objects.
        """
        self.clear()
        self.participants = participants
        self.date_list = sorted(poll_dates)
        self.time_slot_list = time_slot_list

        rows = len(time_slot_list)
        cols = len(self.date_list)
        self.setRowCount(rows)
        self.setColumnCount(cols)

        for c, d_str in enumerate(self.date_list):
            self.setHorizontalHeaderItem(c, QTableWidgetItem(d_str))

        for r, (t1, t2) in enumerate(self.time_slot_list):
            label = f"{t1.strftime('%H:%M')} - {t2.strftime('%H:%M')}"
            self.setVerticalHeaderItem(r, QTableWidgetItem(label))

        cell_dict = defaultdict(list)
        for item in schedule_data:
            sdt = item['Shift Start']
            edt = item['Shift End']
            occupant_names = [n.strip() for n in item['Assigned To'].split(',') if n.strip()]

            day_str = sdt.strftime("%Y-%m-%d")
            t1 = sdt.time()
            t2 = edt.time()

            if day_str in self.date_list:
                col_idx = self.date_list.index(day_str)
                for row_idx, (slot_start, slot_end) in enumerate(self.time_slot_list):
                    if slot_start == t1 and slot_end == t2:
                        cell_dict[(row_idx, col_idx)].extend(occupant_names)

        self.occupant_data.clear()
        for r in range(rows):
            for c in range(cols):
                occupant_list = cell_dict.get((r, c), [])
                self.occupant_data[(r, c)] = occupant_list
                self._set_cell_widget(r, c, occupant_list)

        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.validate_all_cells()

    def _set_cell_widget(self, row, col, occupant_list):
        """
        Creates a QWidget with occupant chips for the cell at (row, col).

        Args:
            row: Row index.
            col: Column index.
            occupant_list: List of occupant names to display.
        """
        cell_widget = QWidget()
        cell_widget.setObjectName("CellWidget")
        layout = QHBoxLayout(cell_widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        for occupant_name in occupant_list:
            chip = OccupantChip(occupant_name, row=row, col=col)
            layout.addWidget(chip)

        layout.addStretch()
        self.setCellWidget(row, col, cell_widget)
        self._refresh_cell_background(row, col)

    def get_current_schedule_data(self):
        """
        Constructs a list of shift dictionaries from occupant_data.
        Each dictionary contains:
            - 'Shift Start': start datetime,
            - 'Shift End': end datetime,
            - 'Assigned To': comma-separated occupant names.
        
        Returns:
            List of shift dictionaries.
        """
        data = []
        for c, d_str in enumerate(self.date_list):
            y, m, d = map(int, d_str.split('-'))
            for r in range(self.rowCount()):
                occupant_list = self.occupant_data.get((r, c), [])
                if occupant_list:
                    t1, t2 = self.time_slot_list[r]
                    sdt = datetime(y, m, d, t1.hour, t1.minute, 0)
                    edt = datetime(y, m, d, t2.hour, t2.minute, 0)
                    data.append({
                        'Shift Start': sdt,
                        'Shift End': edt,
                        'Assigned To': ", ".join(occupant_list)
                    })
        return data

    def mouseDoubleClickEvent(self, event):
        """
        Handles double-click events to edit occupant names in a cell.
        Opens an input dialog for editing, updates occupant_data, and validates cells.
        """
        pos = event.position().toPoint()
        row = self.rowAt(pos.y())
        col = self.columnAt(pos.x())
        if row < 0 or col < 0:
            super().mouseDoubleClickEvent(event)
            return

        occupant_list = self.occupant_data.get((row, col), [])
        current_text = ", ".join(occupant_list)

        dlg = QInputDialog(self)
        dlg.setWindowTitle("Edycja osób w slocie")
        dlg.setLabelText("Wpisz osoby (rozdzielone przecinkiem):")
        dlg.setTextValue(current_text)
        dlg.setMinimumWidth(400)

        if dlg.exec():
            new_text = dlg.textValue()
            names = [n.strip() for n in new_text.split(",") if n.strip()]
            self.occupant_data[(row, col)] = names
            self._set_cell_widget(row, col, names)
            self.validate_all_cells()

        super().mouseDoubleClickEvent(event)

    def highlight_availability(self, person_name, enable=True):
        """
        Highlights cells with the availability of the specified person.
        
        Args:
            person_name: Name of the person.
            enable: True to enable highlighting; False to disable.
        """
        if not enable:
            self.current_highlight_person = None
            for r in range(self.rowCount()):
                for c in range(self.columnCount()):
                    self._refresh_cell_background(r, c)
            self.viewport().repaint()
            return

        self.current_highlight_person = person_name
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                self._refresh_cell_background(r, c)
        self.viewport().repaint()

    def setColorizeMode(self, enable: bool):
        """
        Enables or disables colorize mode.
        
        Args:
            enable: True to enable; False to disable.
        """
        self.colorize_mode = enable
        if enable:
            self._generate_color_map()
        self.validate_all_cells()

    def _generate_color_map(self):
        """
        Generates a mapping from occupant names to random background and text colors.
        """
        all_occupants = set()
        for occupant_list in self.occupant_data.values():
            for nm in occupant_list:
                all_occupants.add(nm)

        self.occupant_data_color_map.clear()
        for nm in sorted(all_occupants):
            r = random.randint(80, 255)
            g = random.randint(80, 255)
            b = random.randint(80, 255)
            bg_hex = f"#{r:02X}{g:02X}{b:02X}"
            text_hex = "#000000" if (r * 0.299 + g * 0.587 + b * 0.114) > 186 else "#FFFFFF"
            self.occupant_data_color_map[nm] = (bg_hex, text_hex)

    def _refresh_cell_background(self, row, col):
        """
        Refreshes the cell background. If a person is highlighted (current_highlight_person is set),
        applies a green background for normal availability or yellow for ifNeeded-only overlap.
        Otherwise, resets the background.
        """
        cell_w = self.cellWidget(row, col)
        if not cell_w:
            return
        # Reset background first
        cell_w.setStyleSheet("QWidget#CellWidget { background-color: none; }")

        if not self.current_highlight_person:
            return

        person = next((p for p in self.participants if p['name'] == self.current_highlight_person), None)
        if not person:
            return

        availability = person['availabilities']
        # info: Use ifNeeded availability if present; default to empty list if not
        ifneeded = person.get('ifNeeded', [])
        d_str = self.date_list[col]
        y, m, d = map(int, d_str.split('-'))
        t1, t2 = self.time_slot_list[row]
        sdt = datetime(y, m, d, t1.hour, t1.minute, 0)
        edt = datetime(y, m, d, t2.hour, t2.minute, 0)

        # Determine overlaps
        normal_overlap = any(sdt >= avs and edt <= ave for (avs, ave) in availability)
        ifneeded_overlap = any(sdt >= ivs and edt <= ive for (ivs, ive) in ifneeded)

        if ifneeded_overlap and not normal_overlap:
            cell_w.setStyleSheet("QWidget#CellWidget { background-color: rgba(255,255,153,150); }")
        elif normal_overlap:
            cell_w.setStyleSheet("QWidget#CellWidget { background-color: rgba(204,255,204,180); }")

    def validate_all_cells(self):
        """
        Validates and applies styles to each occupant chip based on:
            - Colorize mode (random assignment if enabled),
            - Missing participant (yellow),
            - Overlimit or no availability overlap (red),
            - Otherwise, basic chip colors from the current theme.
        """
        occupant_hours = defaultdict(float)
        rows = self.rowCount()
        cols = self.columnCount()

        # Compute total worked hours per occupant
        for c in range(cols):
            d_str = self.date_list[c]
            y, m, d = map(int, d_str.split('-'))
            for r in range(rows):
                occupant_list = self.occupant_data.get((r, c), [])
                if occupant_list:
                    t1, t2 = self.time_slot_list[r]
                    sdt = datetime(y, m, d, t1.hour, t1.minute, 0)
                    edt = datetime(y, m, d, t2.hour, t2.minute, 0)
                    dur_hrs = (edt - sdt).total_seconds() / 3600.0
                    for nm in occupant_list:
                        occupant_hours[nm] += dur_hrs

        occupant_over_limit = set()
        if self.max_hours > 0:
            for nm, hrs in occupant_hours.items():
                if hrs > self.max_hours:
                    occupant_over_limit.add(nm)

        main_window = self.window()
        if hasattr(main_window, 'basic_chip_bg') and hasattr(main_window, 'basic_chip_text'):
            basic_bg = main_window.basic_chip_bg
            basic_text = main_window.basic_chip_text
        else:
            basic_bg = "#E0E0E0"
            basic_text = "#000000"

        for c in range(cols):
            d_str = self.date_list[c]
            y, m, d = map(int, d_str.split('-'))
            for r in range(rows):
                occupant_list = self.occupant_data.get((r, c), [])
                t1, t2 = self.time_slot_list[r]
                sdt = datetime(y, m, d, t1.hour, t1.minute, 0)
                edt = datetime(y, m, d, t2.hour, t2.minute, 0)

                cell_widget = self.cellWidget(r, c)
                if not cell_widget:
                    continue

                for i in range(cell_widget.layout().count()):
                    item = cell_widget.layout().itemAt(i)
                    if not item or not item.widget():
                        continue
                    chip = item.widget()
                    if not hasattr(chip, "occupant_name"):
                        continue

                    nm = chip.occupant_name

                    if self.colorize_mode and nm in self.occupant_data_color_map:
                        bg_hex, text_hex = self.occupant_data_color_map[nm]
                        style_chip = f"""
                            QFrame#OccupantChip {{
                                background-color: {bg_hex};
                                border-radius: 10px;
                                padding: 3px;
                            }}
                            QFrame#OccupantChip QLabel {{
                                color: {text_hex};
                            }}
                        """
                        chip.setStyleSheet(style_chip)
                        continue

                    person = next((p for p in self.participants if p['name'] == nm), None)
                    if not person:
                        style_chip = f"""
                            QFrame#OccupantChip {{
                                background-color: #FFD700;
                                border-radius: 10px;
                                padding: 3px;
                            }}
                            QFrame#OccupantChip QLabel {{
                                color: #000000;
                            }}
                        """
                    elif nm in occupant_over_limit:
                        style_chip = f"""
                            QFrame#OccupantChip {{
                                background-color: #FF9999;
                                border-radius: 10px;
                                padding: 3px;
                            }}
                            QFrame#OccupantChip QLabel {{
                                color: #000000;
                            }}
                        """
                    else:
                        availability = person['availabilities']
                        overlap = any(sdt >= avs and edt <= ave for (avs, ave) in availability)
                        if not overlap:
                            style_chip = f"""
                                QFrame#OccupantChip {{
                                    background-color: #FF9999;
                                    border-radius: 10px;
                                    padding: 3px;
                                }}
                                QFrame#OccupantChip QLabel {{
                                    color: #000000;
                                }}
                            """
                        else:
                            style_chip = f"""
                                QFrame#OccupantChip {{
                                    background-color: {basic_bg};
                                    border-radius: 10px;
                                    padding: 3px;
                                }}
                                QFrame#OccupantChip QLabel {{
                                    color: {basic_text};
                                }}
                            """
                    chip.setStyleSheet(style_chip)

        if self.current_highlight_person:
            for r in range(rows):
                for c in range(cols):
                    self._refresh_cell_background(r, c)

        self.scheduleChanged.emit()

    def dragEnterEvent(self, event):
        """
        Accepts drag enter events if text data is present.
        """
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """
        Accepts drag move events if text data is present.
        """
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        """
        Handles drop events to move an occupant from one cell to another.
        """
        if not event.mimeData().hasText():
            super().dropEvent(event)
            return

        data_str = event.mimeData().text()
        try:
            occupant_name, old_r_str, old_c_str = data_str.split("|")
            old_r = int(old_r_str)
            old_c = int(old_c_str)
        except:
            event.ignore()
            return

        pos = event.position().toPoint()
        row = self.rowAt(pos.y())
        col = self.columnAt(pos.x())
        if row < 0 or col < 0:
            event.ignore()
            return

        self.occupant_data[(row, col)].append(occupant_name)
        self._set_cell_widget(row, col, self.occupant_data[(row, col)])

        if (old_r, old_c) in self.occupant_data:
            if occupant_name in self.occupant_data[(old_r, old_c)]:
                self.occupant_data[(old_r, old_c)].remove(occupant_name)
                self._set_cell_widget(old_r, old_c, self.occupant_data[(old_r, old_c)])

        self.validate_all_cells()
        event.acceptProposedAction()
