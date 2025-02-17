from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QWidget,
    QHBoxLayout, QInputDialog
)
from PyQt6.QtCore import pyqtSignal
from datetime import datetime
from collections import defaultdict
import random

from UI.occupant_chip import OccupantChip
from UI.styles import LIGHT_QSS, FIRE_QSS

class ScheduleMatrixWidget(QTableWidget):
    """
    Tabela (QTableWidget) z occupant_chipami (OccupantChip) w komórkach.
    occupant_data[(r,c)] -> list[str].

    colorize_mode = True => losowe kolory occupantów (ignoruje overlimit, outside).
    colorize_mode = False => normalna walidacja (spoza participants => żółty, overlimit/noOverlap => czerwony,
                            normal => zależny od motywu).
    highlight_availability(person) => zielone tło komórki, jeśli overlap z availability.
    """

    scheduleChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.participants = []
        self.date_list = []
        self.time_slot_list = []
        self.max_hours = 0.0

        # occupant_data[(row,col)] -> list[str]
        self.occupant_data = {}

        self.current_highlight_person = None

        # Mapa occupant -> (bg_hex, text_hex) do colorize
        self.occupant_data_color_map = {}
        self.colorize_mode = False

        # Podstawowe rozmiary wierszy/kolumn
        self.verticalHeader().setDefaultSectionSize(30)
        self.horizontalHeader().setDefaultSectionSize(110)

        # minimalna szer
        self.horizontalHeader().setMinimumSectionSize(100)

    def setMaxHours(self, val):
        self.max_hours = val

    def load_schedule_matrix(self, schedule_data, participants, poll_dates, time_slot_list):
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
        Tworzy w komórce (row,col) QWidget z occupant_chipami.
        """
        cell_widget = QWidget()
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
        Buduje listę {Shift Start, Shift End, Assigned To} w oparciu o occupant_data.
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

        main_window = self.window()
        if hasattr(main_window, 'fire_mode') and main_window.fire_mode:
            dlg.setStyleSheet(FIRE_QSS)
        else:
            dlg.setStyleSheet(LIGHT_QSS)

        if dlg.exec():
            new_text = dlg.textValue()
            names = [n.strip() for n in new_text.split(",") if n.strip()]
            self.occupant_data[(row, col)] = names
            self._set_cell_widget(row, col, names)
            self.validate_all_cells()

        super().mouseDoubleClickEvent(event)

    # ------------------- highlight_availability -------------------
    def highlight_availability(self, person_name, enable=True):
        """
        Podświetla tło komórki (zielony) jeśli w overlapie z person_name.
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

    # ------------------- colorize_mode -------------------
    def setColorizeMode(self, enable: bool):
        self.colorize_mode = enable
        if enable:
            self._generate_color_map()
        self.validate_all_cells()

    def _generate_color_map(self):
        """
        occupant -> (bg_hex, text_hex) w oparciu o losowe barwy i kontrast.
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

    # ------------------- _refresh_cell_background (highlight) -------------------
    def _refresh_cell_background(self, row, col):
        """
        Ustawia tło w komórce, gdy jest highlight_availability włączony
        (self.current_highlight_person).
        """
        cell_w = self.cellWidget(row, col)
        if not cell_w:
            return
        # reset
        cell_w.setStyleSheet("QWidget { background-color: none; }")

        if not self.current_highlight_person:
            return

        person = next((p for p in self.participants if p['name'] == self.current_highlight_person), None)
        if not person:
            return

        # Slot start/end
        availability = person['availabilities']
        d_str = self.date_list[col]
        y, m, d = map(int, d_str.split('-'))
        t1, t2 = self.time_slot_list[row]
        sdt = datetime(y, m, d, t1.hour, t1.minute, 0)
        edt = datetime(y, m, d, t2.hour, t2.minute, 0)

        # Czy slot jest w ifNeeded?
        ifneeded_overlap = any(sdt >= ivs and edt <= ive for (ivs, ive) in person['ifNeeded'])
        # Czy slot jest w normal availability?
        normal_overlap = any(sdt >= avs and edt <= ave for (avs, ave) in person['availabilities'])

        if ifneeded_overlap and not normal_overlap:
            # Tylko w ifNeeded -> "mleczny żółty"
            cell_w.setStyleSheet("QWidget { background-color: rgba(255,255,153,150); }")
        elif normal_overlap:
            # Normal availability -> "pastelowy zielony"
            cell_w.setStyleSheet("QWidget { background-color: rgba(204,255,204,180); }")

    # ------------------- validate_all_cells -------------------
    def validate_all_cells(self):
        """
        Dla każdego occupant_chip w occupant_data ustala styl:
            - colorize -> occupant_data_color_map
            - normal -> (spoza participants => złoty, overlimit/noOverlap => czerwony,
                        w innym wypadku => zależny od motywu).
        """
        occupant_hours = defaultdict(float)

        rows = self.rowCount()
        cols = self.columnCount()

        # Policz łączny czas
        for c in range(cols):
            d_str = self.date_list[c]
            y, m, d = map(int, d_str.split('-'))
            for r in range(rows):
                occupant_list = self.occupant_data.get((r, c), [])
                if occupant_list:
                    (t1, t2) = self.time_slot_list[r]
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
        dark_mode = False
        if hasattr(main_window, 'fire_mode') and main_window.fire_mode:
            dark_mode = True

        if dark_mode:
            basic_bg = "#30363D"  # ciemnoszary > firemode
            basic_text = "#C9D1D9"
        else:
            basic_bg = "#E0E0E0"  # jasnoszary > lightmode
            basic_text = "#000000"

        for c in range(cols):
            d_str = self.date_list[c]
            y, m, d = map(int, d_str.split('-'))
            for r in range(rows):
                occupant_list = self.occupant_data.get((r, c), [])
                (t1, t2) = self.time_slot_list[r]
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
                    if not isinstance(chip, OccupantChip):
                        continue

                    nm = chip.occupant_name

                    # (1) Tryb colorize => occupant_data_color_map
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

                    # Gdy occupant w ogóle nie jest w occupant_data_color_map lub colorize wyłączony:
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
                        # Overlimit => #FF9999
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
                        # Sprawdzamy overlap
                        availability = person['availabilities']
                        overlap = any(sdt >= avs and edt <= ave for (avs, ave) in availability)
                        if not overlap:
                            # noOverlap => #FF9999
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

        # Odśwież highlight (osoba)
        if self.current_highlight_person:
            for r in range(rows):
                for c in range(cols):
                    self._refresh_cell_background(r, c)

        self.scheduleChanged.emit()

    # ------------------- DRAG & DROP -------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
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

        # Dodaj occupant_name do nowej komórki
        self.occupant_data[(row, col)].append(occupant_name)
        self._set_cell_widget(row, col, self.occupant_data[(row, col)])

        # Usuń occupant_name ze starej komórki
        if (old_r, old_c) in self.occupant_data:
            if occupant_name in self.occupant_data[(old_r, old_c)]:
                self.occupant_data[(old_r, old_c)].remove(occupant_name)
                self._set_cell_widget(old_r, old_c, self.occupant_data[(old_r, old_c)])

        self.validate_all_cells()
        event.acceptProposedAction()
