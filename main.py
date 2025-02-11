import sys
from PyQt6.QtWidgets import QApplication, QDialog
from UI.main_window import MainWindow
from UI.initial_setup_dialog import InitialSetupDialog

def main():
    app = QApplication(sys.argv)

    setup_dialog = InitialSetupDialog()
    if setup_dialog.exec() == QDialog.DialogCode.Accepted:
        schedule_data = setup_dialog.loaded_schedule_data
        participants = setup_dialog.loaded_participants
        poll_dates = setup_dialog.loaded_poll_dates
        time_slot_list = setup_dialog.loaded_time_slot_list
        day_slots_dict = setup_dialog.loaded_day_slots_dict
        full_slots = setup_dialog.loaded_full_slots
        fire_mode_enabled = setup_dialog.fire_mode

        main_window = MainWindow(fire_mode=fire_mode_enabled)
        main_window.show()

        main_window.schedule_widget.load_schedule_matrix(
            schedule_data=schedule_data,
            participants=participants,
            poll_dates=poll_dates,
            time_slot_list=time_slot_list
        )
        main_window.schedule_widget.setMaxHours(float(main_window.max_hours_spin.value()))

        main_window.participants = participants
        main_window.poll_dates = poll_dates
        main_window.day_slots_dict = day_slots_dict
        main_window.full_slots = full_slots

        sys.exit(app.exec())
    else:
        sys.exit()

if __name__ == "__main__":
    main()
