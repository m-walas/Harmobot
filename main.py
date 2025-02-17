import sys
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import Qt

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
        fire_mode_enabled = setup_dialog.fire_mode

        main_window = MainWindow(fire_mode=fire_mode_enabled)
        main_window.engine_name = engine
        main_window.participants = participants
        main_window.poll_dates = poll_dates
        main_window.day_ranges = day_ranges

        main_window.initialize_schedule_table()

        main_window.show()
        sys.exit(app.exec())
    else:
        sys.exit()

if __name__ == "__main__":
    main()
