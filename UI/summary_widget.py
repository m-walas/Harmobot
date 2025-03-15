from PyQt6.QtWidgets import (
    QWidget,
    QListWidget,
    QListWidgetItem,
    QToolButton,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QColor, QIcon, QDrag
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.resources import get_icon_path

class DraggableListWidget(QListWidget):
    """
    Custom QListWidget that initiates a drag event with custom MIME data.
    The MIME text is formatted as: occupant_name|-1|-1
    (using -1 as marker that the source is the summary list).
    """
    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return
        drag = QDrag(self)
        mime = QMimeData()
        text = item.text()
        bracket_idx = text.find(" [")
        name = text[:bracket_idx] if bracket_idx > 0 else text
        drag_data = f"{name}|-1|-1"
        mime.setText(drag_data)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)

class SummaryListWidget(QWidget):
    """
    Widget displaying a list of participants along with a summary of worked hours.
    Emits:
        - personSelected(str): when a participant is clicked.
        - personAddRequested(str): when a new participant is added via the add button.
    Additionally, this widget accepts drops from the schedule (OccupantChip)
    so that if a chip is dropped on it, it is interpreted as a removal request.
    """
    personSelected = pyqtSignal(str)
    personAddRequested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initializes the SummaryListWidget.
        """
        super().__init__(parent)
        self.setObjectName("SummaryWidget")
        self.name_to_hours: Dict[str, float] = {}
        self.setAcceptDrops(True)

        main_layout = QVBoxLayout(self)

        # note: Header layout: label on left, plus button on right.
        header_layout = QHBoxLayout()
        header_label = QLabel("Uczestnicy")
        header_label.setObjectName("SummaryHeaderLabel")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        self.add_button = QToolButton()
        self.add_button.setObjectName("PlusButton")
        plus_icon = QIcon(get_icon_path("plus"))
        if plus_icon.isNull():
            self.add_button.setText("+")
        else:
            self.add_button.setIcon(plus_icon)
        self.add_button.setToolTip("Dodaj nową osobę")
        self.add_button.clicked.connect(self.on_add_person)
        header_layout.addWidget(self.add_button)
        main_layout.addLayout(header_layout)

        self.list_widget = DraggableListWidget()
        self.list_widget.setDragEnabled(True)
        main_layout.addWidget(self.list_widget)
        self.list_widget.itemClicked.connect(self._on_item_clicked)

        self.instructions_label = QLabel(
            "Kliknij, aby zobaczyć dyspozycję.\nPrzeciągnij z listy, aby dodać do slota.\nUpuść tutaj, aby usunąć z grafiku."
        )
        self.instructions_label.setObjectName("SummaryInstructionsLabel")
        main_layout.addWidget(self.instructions_label)

        self.trash_overlay = QLabel(self)
        self.trash_overlay.setObjectName("TrashOverlay")
        self.trash_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.trash_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.trash_overlay.setText("🗑")
        self.trash_overlay.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.trash_overlay.setGeometry(0, 0, self.width(), self.height())

    def update_summary(
        self,
        participants: List[Dict[str, Any]],
        schedule_data: List[Dict[str, Any]],
        max_hours: Optional[float] = None
    ) -> None:
        """
        Updates the participant list with a summary of worked hours calculated from shift data.
        """
        self.name_to_hours.clear()
        for p in participants:
            if 'external' not in p:
                p['external'] = False
            self.name_to_hours[p['name']] = 0.0
        for item in schedule_data:
            shift_start: datetime = item['Shift Start']
            shift_end: datetime = item['Shift End']
            duration = (shift_end - shift_start).total_seconds() / 3600.0
            names = [n.strip() for n in item['Assigned To'].split(',') if n.strip()]
            for name in names:
                self.name_to_hours.setdefault(name, 0.0)
                self.name_to_hours[name] += duration

        self.list_widget.clear()
        for name, hours in self.name_to_hours.items():
            text = f"{name} [{hours:.2f}h]"
            list_item = QListWidgetItem(text)
            matching_participant = next((p for p in participants if p['name'] == name), None)
            if matching_participant is None or matching_participant.get("external", False):
                list_item.setBackground(QColor("#FFD700"))
            elif max_hours is not None and hours > max_hours:
                list_item.setBackground(QColor("#FF9999"))
            self.list_widget.addItem(list_item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """
        Emits the 'personSelected' signal using the participant's name.
        """
        text = item.text()
        bracket_idx = text.find(" [")
        name = text[:bracket_idx] if bracket_idx > 0 else text
        self.personSelected.emit(name)

    def on_add_person(self) -> None:
        """
        Opens input dialog to add a new participant; emits 'personAddRequested' on valid input.
        """
        new_person, ok = QInputDialog.getText(self, "Dodaj osobę", "Wpisz nową osobę:")
        if ok and new_person.strip():
            self.personAddRequested.emit(new_person.strip())

    def add_person(self, name: str) -> None:
        """
        Adds a new participant with 0 hours; avoids duplicate entries.
        """
        if name in self.name_to_hours:
            return
        self.name_to_hours[name] = 0.0
        text = f"{name} [0.00h]"
        list_item = QListWidgetItem(text)
        list_item.setBackground(QColor("#FFD700"))
        self.list_widget.addItem(list_item)

    def refresh_plus_button_icon(self) -> None:
        """
        Reloads the plus button icon so that it reflects updated theme colors.
        """
        plus_icon = QIcon(get_icon_path("plus"))
        if plus_icon.isNull():
            self.add_button.setText("+")
            self.add_button.setIcon(QIcon())
        else:
            self.add_button.setText("")
            self.add_button.setIcon(plus_icon)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        if not event.mimeData().hasText():
            event.ignore()
            return
        data_str = event.mimeData().text()
        try:
            occupant_name, old_r_str, old_c_str = data_str.split("|")
            old_r = int(old_r_str)
            old_c = int(old_c_str)
        except Exception:
            event.ignore()
            return
        if old_r != -1:
            main_win = self.window()
            if hasattr(main_win, "schedule_widget"):
                sch_widget = main_win.schedule_widget
                if (old_r, old_c) in sch_widget.occupant_data:
                    if occupant_name in sch_widget.occupant_data[(old_r, old_c)]:
                        sch_widget.occupant_data[(old_r, old_c)].remove(occupant_name)
                        sch_widget._set_cell_widget(old_r, old_c, sch_widget.occupant_data[(old_r, old_c)])
                sch_widget.validate_all_cells()
                main_win.update_summary()
        self.trash_overlay.hide()
        event.acceptProposedAction()
