from PyQt6.QtWidgets import QWidget, QListWidget, QVBoxLayout, QListWidgetItem
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from typing import List, Dict, Any, Optional
from datetime import datetime

class SummaryListWidget(QWidget):
    """
    Widget displaying a list of participants along with a summary of worked hours.
    Emits the `personSelected` signal with the selected person's name when a list item is clicked.
    """
    personSelected = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initializes the widget.

        Args:
            parent (Optional[QWidget]): The parent widget, if any.
        """
        super().__init__(parent)
        self.list_widget = QListWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.name_to_hours: Dict[str, float] = {}

    def update_summary(
        self,
        participants: List[Dict[str, Any]],
        schedule_data: List[Dict[str, Any]],
        max_hours: Optional[float] = None
    ) -> None:
        """
        Updates the participant list with a summary of worked hours based on shift data.

        Args:
            participants (List[Dict[str, Any]]): List of dictionaries containing the key 'name'.
            schedule_data (List[Dict[str, Any]]): List of dictionaries with shift details, each containing:
                - 'Shift Start': a datetime object representing the start of the shift,
                - 'Shift End': a datetime object representing the end of the shift,
                - 'Assigned To': a string with comma-separated names assigned to the shift.
            max_hours (Optional[float]): Hour limit; if a participant exceeds this limit, the item is highlighted.
        """
        self.name_to_hours.clear()
        for p in participants:
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
            if not any(p['name'] == name for p in participants):
                list_item.setBackground(QColor("#FFD700"))
            elif max_hours is not None and hours > max_hours:
                list_item.setBackground(QColor("#FF9999"))
            self.list_widget.addItem(list_item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """
        Emits the 'personSelected' signal with the name of the person when a list item is clicked.

        Args:
            item (QListWidgetItem): The clicked list item.
        """
        text = item.text()
        bracket_idx = text.find(" [")
        name = text[:bracket_idx] if bracket_idx > 0 else text
        self.personSelected.emit(name)
