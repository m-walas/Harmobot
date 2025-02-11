LIGHT_QSS = """
QMainWindow {
    background-color: #F2F2F2;
    color: #000000;
}

QSplitter::handle {
    background-color: #DDDDDD;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}

/* Dock */
QDockWidget {
    background-color: #F7F7F7;
    color: #000000;
    max-width: 250px;
}
QDockWidget QWidget {
    background-color: #F7F7F7;
    color: #000000;
}

/* Dialogi / Progress */
QDialog, QProgressDialog {
    background-color: #F2F2F2;
    color: #000000;
}
QDialog QPushButton, QProgressDialog QPushButton {
    background-color: #2E86C1;
    color: #FFFFFF;
    border-radius: 4px;
    padding: 6px 12px;
}
QDialog QPushButton:hover, QProgressDialog QPushButton:hover {
    background-color: #1B4F72;
}

/* Główne przyciski */
QPushButton {
    background-color: #2E86C1;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1B4F72;
}

/* Tabela + Lista */
QTableWidget {
    background-color: #FFFFFF;
    color: #000000;
    gridline-color: #AAAAAA;
}
QHeaderView::section {
    background-color: #DDDDDD;
    color: #000000;
}
QListWidget {
    background-color: #FFFFFF;
    color: #000000;
}

/* Etykiety */
QLabel {
    color: #000000;
}

/* Pola edycji */
QLineEdit {
    background-color: #FFFFFF;
    color: #000000;
    border: 1px solid #CCCCCC;
    max-width: 65px;
}

/* Menu */
QMenuBar {
    background-color: #E4E4E4;
    color: #000000;
}
QMenuBar::item {
    background-color: transparent;
    color: #000000;
}
QMenuBar::item:selected {
    background-color: #D0D0D0;
}
QMenu {
    background-color: #F8F8F8;
    color: #000000;
}
QMenu::item:selected {
    background-color: #CCCCCC;
}

/* SpinBox – usunięcie strzałek */
QSpinBox {
    border: 1px solid #666666;
    background-color: #FFFFFF;
    color: #000000;
    border-radius: 4px;
    padding: 2px;
    min-height: 15px;
    max-width: 60px;
    padding-right: 16px;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 0;
    height: 0;
    border: none;
}
"""

FIRE_QSS = """
QMainWindow {
    background-color: #0D1117;
    color: #C9D1D9;
}

QSplitter::handle {
    background-color: #161B22;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}

/* Dock */
QDockWidget {
    background-color: #161B22;
    color: #C9D1D9;
    max-width: 250px;
}
QDockWidget QWidget {
    background-color: #161B22;
    color: #C9D1D9;
}

/* Dialogi / Progress */
QDialog, QProgressDialog {
    background-color: #161B22;
    color: #C9D1D9;
}
QDialog QPushButton, QProgressDialog QPushButton {
    background-color: #FF4500;
    color: #1E1E1E;
    border-radius: 4px;
    padding: 6px 12px;
}
QDialog QPushButton:hover, QProgressDialog QPushButton:hover {
    background-color: #e03e00;
}

/* Główne przyciski */
QPushButton {
    background-color: #FF4500;
    color: #1E1E1E;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #e03e00;
}

/* Tabela + Lista */
QTableWidget {
    background-color: #21262D;
    color: #C9D1D9;
    gridline-color: #30363D;
}
QTableWidget::viewport {
    background-color: #21262D;
}
QTableCornerButton::section {
    background-color: #21262D;
}
QHeaderView::section {
    background-color: #30363D;
    color: #C9D1D9;
}
QListWidget {
    background-color: #21262D;
    color: #C9D1D9;
}
QTableCornerButton::section {
    background-color: #21262D;
}

/* Etykiety */
QLabel {
    color: #C9D1D9;
}

/* Pola edycji */
QLineEdit {
    background-color: #30363D;
    color: #C9D1D9;
    border: 1px solid #FF4500;
    max-width: 65px;
}

/* Menu */
QMenuBar {
    background-color: #161B22;
    color: #C9D1D9;
}
QMenuBar::item {
    background-color: transparent;
    color: #C9D1D9;
}
QMenuBar::item:selected {
    background-color: #30363D;
}
QMenu {
    background-color: #161B22;
    color: #C9D1D9;
}
QMenu::item:selected {
    background-color: #30363D;
}

/* SpinBox */
QSpinBox {
    border: 1px solid #FF4500;
    background-color: #30363D;
    color: #C9D1D9;
    border-radius: 4px;
    padding: 2px;
    min-height: 15px;
    max-width: 60px;
    padding-right: 16px;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 0;
    height: 0;
    border: none;
}
"""
