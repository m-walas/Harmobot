from PyQt6.QtWidgets import QWidget, QListWidget, QVBoxLayout, QListWidgetItem
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor

class SummaryListWidget(QWidget):
    """
    Widget wyświetlający listę uczestników i sumę przepracowanych godzin.
    Kliknięcie w pozycję listy emituje sygnał personSelected(nazwa).
    """
    personSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.list_widget = QListWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.name_to_hours = {}

    def update_summary(self, participants, schedule_data, max_hours=None):
        """
        Aktualizuje listę uczestników z podsumowaniem godzin na podstawie schedule_data.
        
        Parametry:
            - participants: lista słowników z kluczem 'name'
            - schedule_data: lista {Shift Start, Shift End, Assigned To}
            - max_hours: opcjonalny limit godzin
        """
        self.name_to_hours.clear()
        for p in participants:
            self.name_to_hours[p['name']] = 0.0

        for item in schedule_data:
            duration = (item['Shift End'] - item['Shift Start']).total_seconds() / 3600.0
            names = [n.strip() for n in item['Assigned To'].split(',') if n.strip()]
            for nm in names:
                self.name_to_hours.setdefault(nm, 0.0)
                self.name_to_hours[nm] += duration

        self.list_widget.clear()
        for nm, hrs in self.name_to_hours.items():
            text = f"{nm} [{hrs:.2f}h]"
            item = QListWidgetItem(text)
            in_participants = any(p['name'] == nm for p in participants)
            if not in_participants:
                item.setBackground(QColor("#FFD700"))
            elif max_hours and hrs > max_hours:
                item.setBackground(QColor("#FF9999"))
            self.list_widget.addItem(item)

    def _on_item_clicked(self, item):
        """
        Emituje sygnał z nazwą osoby po kliknięciu w listę.
        """
        text = item.text()
        bracket_idx = text.find(" [")
        name = text[:bracket_idx] if bracket_idx > 0 else text
        self.personSelected.emit(name)
