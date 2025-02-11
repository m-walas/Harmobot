from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout, QApplication
from PyQt6.QtGui import QDrag
from PyQt6.QtCore import Qt, QPoint, QMimeData

class OccupantChip(QFrame):
    """
    Pojedynczy 'chip' w komórce tabeli (dla jednej osoby).
    Obsługuje drag & drop (QDrag) przy przesuwaniu.
    """

    def __init__(self, occupant_name, row=None, col=None, parent=None):
        super().__init__(parent)
        self.occupant_name = occupant_name
        self.source_row = row
        self.source_col = col
        self._drag_start_pos = QPoint()

        self.setObjectName("OccupantChip")
        self.setStyleSheet("""
            QFrame#OccupantChip {
                border-radius: 10px;
                padding: 3px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(0)

        self.label = QLabel(occupant_name, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            distance = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
            if distance > QApplication.startDragDistance():
                self._start_drag()
        super().mouseMoveEvent(event)

    def _start_drag(self):
        drag = QDrag(self)
        mime = QMimeData()

        data_str = f"{self.occupant_name}|{self.source_row}|{self.source_col}"
        mime.setText(data_str)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)
