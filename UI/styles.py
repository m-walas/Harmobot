##============ LIGHT_QSS ============##

LIGHT_QSS = """
/* ---------------- Okno główne, dialogi ---------------- */
QMainWindow, QDialog, QProgressDialog {
    background-color: #F3F3F3;
    color: #000000;
}

/* ---------------- Splitter ---------------- */
QSplitter::handle {
    background-color: #DDDDDD;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}

/* ---------------- Sidebar & Stopka ---------------- */
QFrame#CollapsibleSidebar,
QWidget#FooterWidget {
    background-color: #009d4f;
    color: #000000;
}

/* Tytuł "Harmobot" w side-barze */
QLabel#SidebarAppLabel {
    font-size: 15px;
    font-weight: bold;
    color: #eef6ed;
    padding-left: 6px;
}

/* Górny przycisk "menu" w side-barze */
QPushButton#SidebarToggleBtn {
    background-color: transparent;
    border: none;
    padding: 6px;
}
QPushButton#SidebarToggleBtn:hover {
    background-color: rgba(0,0,0,0.07);
}

/* Przyciski w side-barze */
QPushButton#SidebarButton {
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 8px;
    color: #eef6ed; 
    font-weight: 500;
    border-radius: 0px;
    max-height: 30px;
    min-height: 30px;
}
QPushButton#SidebarButton:hover {
    background-color: rgba(0,0,0,0.07);
}
QPushButton#SidebarButton:checked {
    background-color: rgba(0,0,0,0.15);
    border-left: 4px solid #eef6ed;
}
QPushButton#SidebarButton:disabled {
    color: #999999;
}

/* Tekst w stopce */
QWidget#FooterWidget QLabel {
    color: #666666;
}

/* ---------------- Przyciski ogólne (poza sidebar) ---------------- */
QPushButton {
    background-color: #009d4f;
    color: #eef6ed;
    border: none;
    border-radius: 4px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: rgba(0,130,65,0.99);
}
QPushButton:disabled {
    background-color: #A9A9A9;
    color: #FFFFFF;
    border-radius: 4px;
}

/* ---------------- Tabela (Schedule) i Lista (Summary) ---------------- */
QTableWidget {
    background-color: #FFFFFF;
    color: #000000;
    gridline-color: #AAAAAA;
}
QHeaderView::section {
    background-color: #E0E0E0;
    color: #000000;
}
QListWidget {
    background-color: #FFFFFF;
    color: #000000;
}

/* ---------------- Etykiety ---------------- */
QLabel {
    color: #000000;
    font-weight: 400;
}

/* ---------------- Pola edycji + SpinBox ---------------- */
QLineEdit {
    background-color: #FFFFFF;
    color: #000000;
    border: 1px solid #CCCCCC;
    border-radius: 3px;
    padding: 4px;
    max-width: 80px;
}
QSpinBox {
    background-color: #FFFFFF;
    color: #000000;
    border: 1px solid #CCCCCC;
    border-radius: 3px;
    padding: 2px 6px;
    max-width: 70px;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 0;
    height: 0;
    border: none;
}
"""

##============ FIRE_QSS ============##

FIRE_QSS = """
QMainWindow, QDialog, QProgressDialog {
    background-color: #0D1117;
    color: #C9D1D9;
}

/* Splitter */
QSplitter::handle {
    background-color: #161B22;
}
QSplitter::handle:horizontal {
    width: 2px;
}
QSplitter::handle:vertical {
    height: 2px;
}

/* Sidebar & Footer */
QFrame#CollapsibleSidebar,
QWidget#FooterWidget {
    background-color: #161B22;
    color: #C9D1D9;
}
QLabel#SidebarAppLabel {
    font-size: 15px;
    font-weight: bold;
    color: #C9D1D9;
    padding-left: 6px;
}
QPushButton#SidebarToggleBtn {
    background-color: transparent;
    border: none;
    padding: 6px;
}
QPushButton#SidebarToggleBtn:hover {
    background-color: rgba(200,200,200,0.1);
}

QPushButton#SidebarButton {
    background-color: transparent;
    border: none;
    text-align: left;
    padding: 8px;
    color: #C9D1D9;
    font-weight: 500;
    border-radius: 0px;
    max-height: 30px;
    min-height: 30px;
}
QPushButton#SidebarButton:hover {
    background-color: rgba(200,200,200,0.07);
}
QPushButton#SidebarButton:checked {
    background-color: rgba(200,200,200,0.15);
    border-left: 4px solid #FF4500;
}
QPushButton#SidebarButton:disabled {
    color: #666666;
}

QWidget#FooterWidget QLabel {
    color: #999999;
}

/* Przyciski ogólne */
QPushButton {
    background-color: #FF4500;
    color: #1E1E1E;
    border: none;
    border-radius: 4px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: rgba(255,69,0,0.7);
}
QPushButton:disabled {
    background-color: #A9A9A9;
    color: #FFFFFF;
    border-radius: 4px;
}

/* Tabela, Lista */
QTableWidget {
    background-color: #21262D;
    color: #C9D1D9;
    gridline-color: #30363D;
}
QHeaderView::section {
    background-color: #30363D;
    color: #C9D1D9;
}
QListWidget {
    background-color: #21262D;
    color: #C9D1D9;
}

/* Etykiety */
QLabel {
    color: #C9D1D9;
    font-weight: 400;
}

/* Pola edycji + SpinBox */
QLineEdit {
    background-color: #30363D;
    color: #C9D1D9;
    border: 1px solid #FF4500;
    border-radius: 3px;
    padding: 4px;
    max-width: 80px;
}
QSpinBox {
    background-color: #30363D;
    color: #C9D1D9;
    border: 1px solid #FF4500;
    border-radius: 3px;
    padding: 2px 6px;
    max-width: 70px;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 0;
    height: 0;
    border: none;
}
"""
