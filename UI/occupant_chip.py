from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout, QApplication
from PyQt6.QtGui import QDrag
from PyQt6.QtCore import Qt, QPoint, QMimeData
import weakref

class OccupantChip(QFrame):
    """
    Single chip in a table cell (for one person).
    Supports drag & drop (QDrag) for moving.
    """

    def __init__(self, occupant_name, row=None, col=None, parent=None):
        """
        Initializes the occupant chip.

            Args:
            occupant_name (str): The name of the occupant.
            row (int, optional): The source row.
            col (int, optional): The source column.
            parent (QWidget, optional): The parent widget.
        """
        super().__init__(parent)
        self.occupant_name = occupant_name
        self.source_row = row
        self.source_col = col
        self._drag_start_pos = QPoint()
        self._self_ref = weakref.ref(self)
        self._drag_in_progress = False
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
        if self._self_ref() is None:
            return
        
        if event.buttons() & Qt.MouseButton.LeftButton:
            distance = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
            if distance >= QApplication.startDragDistance():
                self._start_drag()
                return
        try:
            super().mouseMoveEvent(event)
        except RuntimeError:
            pass

    def _start_drag(self):
        """
        Initiates the drag operation.
        When the drag starts, it tries to find the summary widget from the main window.
        If found, it immediately shows the trash icon overlay (trash_overlay) to inform the user
        that dropping the chip on this area will remove it from the schedule.
        After the drag operation completes, the overlay is hidden.
        """
        if self._drag_in_progress:
            return
        chip = self._self_ref()
        if chip is None:
            return
        chip._drag_in_progress = True

        main_win = self.window()
        summary = getattr(main_win, "summary_widget", None)
        if summary:
            # info: Immediately show the trash icon overlay from summary widget
            summary.trash_overlay.show()
            summary.update()
        drag = QDrag(main_win)
        mime = QMimeData()
        # info: Prepare MIME text as "occupant_name|source_row|source_col"
        data_str = f"{self.occupant_name}|{self.source_row}|{self.source_col}"
        mime.setText(data_str)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

        if summary:
            # info: After drag completes, hide the trash overlay
            summary.trash_overlay.hide()
            summary.update()

        chip = self._self_ref()
        if chip is not None:
            chip._drag_in_progress = False
