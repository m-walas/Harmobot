from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenuBar

def create_menu_bar(main_window):
    """
    Tworzy i wypełnia menu bar dla main_window.
    Zwraca obiekt menubar (lub nic, jeśli używamy main_window.menuBar()).
    """
    menubar = main_window.menuBar()
    
    # Menu File
    file_menu = menubar.addMenu("Plik")

    load_csv_action = QAction("Wczytaj CSV", main_window)
    load_csv_action.triggered.connect(main_window.load_from_csv)
    file_menu.addAction(load_csv_action)

    export_csv_action = QAction("Eksportuj do CSV", main_window)
    export_csv_action.triggered.connect(main_window.export_to_csv)
    file_menu.addAction(export_csv_action)

    export_html_action = QAction("Eksportuj do HTML", main_window)
    export_html_action.triggered.connect(main_window.export_to_html)
    file_menu.addAction(export_html_action)

    export_png_action = QAction("Eksportuj do PNG", main_window)
    export_png_action.triggered.connect(main_window.export_to_png)
    file_menu.addAction(export_png_action)

    file_menu.addSeparator()
    exit_action = file_menu.addAction("Zamknij")
    exit_action.triggered.connect(main_window.close)

    # Menu View
    view_menu = menubar.addMenu("Widok")

    toggle_fire_mode_action = QAction("FireMode", main_window)
    toggle_fire_mode_action.setCheckable(True)
    toggle_fire_mode_action.setChecked(main_window.fire_mode)
    toggle_fire_mode_action.triggered.connect(main_window.on_toggle_fire_mode)
    view_menu.addAction(toggle_fire_mode_action)

    toggle_colorize_action = QAction("Kolorowanie czipów", main_window)
    toggle_colorize_action.setCheckable(True)
    toggle_colorize_action.setChecked(False)
    toggle_colorize_action.triggered.connect(main_window.on_toggle_colorize_chips)
    view_menu.addAction(toggle_colorize_action)

    # Dock toggle
    view_menu.addAction(main_window.param_dock.toggleViewAction())

    return menubar
