from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QCheckBox, QLabel
from PyQt6.QtCore import pyqtSignal, Qt

class DaySelectionWidget(QWidget):
    dayToggled = pyqtSignal(int, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.checkboxes = []
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
    def setup_days(self, poll_dates):
        self.clear_checkboxes()
        for i, date_str in enumerate(poll_dates):
            day_widget = QWidget()
            day_layout = QVBoxLayout(day_widget)
            day_layout.setContentsMargins(2, 2, 2, 2)
            
            label = QLabel(date_str)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 10px; font-weight: bold;")
            
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox.toggled.connect(lambda checked, idx=i: self.dayToggled.emit(idx, checked))
            
            day_layout.addWidget(label)
            day_layout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
            
            self.checkboxes.append(checkbox)
            self.layout.addWidget(day_widget)
    
    def get_enabled_days(self):
        return [i for i, checkbox in enumerate(self.checkboxes) if checkbox.isChecked()]
