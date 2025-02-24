import sys
from PyQt6.QtWidgets import QApplication, QDialog

from UI.initial_setup_dialog import InitialSetupDialog
from UI.main_window import MainWindow

def main():
    app = QApplication(sys.argv)

    setup_dialog = InitialSetupDialog()
    if setup_dialog.exec() == QDialog.DialogCode.Accepted:
        engine = setup_dialog.loaded_engine
        participants = setup_dialog.loaded_participants
        poll_dates = setup_dialog.loaded_poll_dates
        day_ranges = setup_dialog.loaded_day_ranges

        main_window = MainWindow()
        main_window.engine_name = engine
        main_window.participants = participants
        main_window.poll_dates = poll_dates
        main_window.day_ranges = day_ranges

        if main_window.engine_name == "Schej":
            main_window.sidebar.btn_schej.setChecked(True)
            main_window.sidebar.btn_cabbage.setChecked(False)
        else:
            main_window.sidebar.btn_cabbage.setChecked(True)
            main_window.sidebar.btn_schej.setChecked(False)

        main_window.initialize_schedule_table()
        main_window.show()
        sys.exit(app.exec())
    else:
        sys.exit()

if __name__ == "__main__":
    main()
