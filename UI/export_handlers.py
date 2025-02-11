import csv
from PyQt6.QtWidgets import QFileDialog
from datetime import datetime

def load_from_csv(main_window):
    filepath, _ = QFileDialog.getOpenFileName(
        main_window, "Wczytaj CSV", "", "CSV Files (*.csv)"
    )
    if not filepath:
        return

    schedule_data = []
    days_set = set()

    try:
        with open(filepath, "r", newline='', encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=';')
            header = next(reader, None)
            if not header or len(header) < 4:
                main_window.show_notification("Nieprawidłowy nagłówek CSV.", duration=3000, error=True)
                return

            for row in reader:
                if len(row) < 4:
                    continue
                day_str = row[0].strip()
                start_str = row[1].strip()
                end_str = row[2].strip()
                assigned_str = row[3].strip()
                try:
                    y, m, d = map(int, day_str.split('-'))
                    sh, sm = map(int, start_str.split(':'))
                    eh, em = map(int, end_str.split(':'))
                    sdt = datetime(y, m, d, sh, sm)
                    edt = datetime(y, m, d, eh, em)
                except:
                    continue

                schedule_data.append({
                    'Shift Start': sdt,
                    'Shift End': edt,
                    'Assigned To': assigned_str
                })
                days_set.add(day_str)

        main_window.poll_dates = sorted(days_set)
        main_window.full_slots = sorted(
            [(item['Shift Start'], item['Shift End']) for item in schedule_data],
            key=lambda x: x[0]
        )

        shift_duration = 30
        main_window.schedule_widget.load_schedule_matrix(
            schedule_data=schedule_data,
            participants=main_window.participants,
            poll_dates=main_window.poll_dates,
            time_slot_list=main_window._build_time_slot_list(shift_duration)
        )
        main_window.schedule_widget.setMaxHours(float(main_window.max_hours_spin.value()))
        main_window.update_summary()
        main_window.show_notification(f"Wczytano CSV z pliku: {filepath}", duration=3000)

    except Exception as e:
        main_window.show_notification(f"Błąd wczytywania CSV: {str(e)}", duration=3000, error=True)


def export_to_csv(main_window):
    filepath, _ = QFileDialog.getSaveFileName(main_window, "Eksport do CSV", "", "CSV Files (*.csv)")
    if not filepath:
        return

    schedule_data = main_window.schedule_widget.get_current_schedule_data()
    schedule_data.sort(key=lambda x: (x['Shift Start'], x['Shift End']))

    try:
        with open(filepath, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["Data", "Start", "Koniec", "Osoby"])
            for row in schedule_data:
                dt_str = row['Shift Start'].strftime("%Y-%m-%d")
                st_str = row['Shift Start'].strftime("%H:%M")
                en_str = row['Shift End'].strftime("%H:%M")
                assigned = row['Assigned To']
                writer.writerow([dt_str, st_str, en_str, assigned])

        main_window.show_notification(f"Zapisano plik: {filepath}", duration=3000)
    except Exception as e:
        main_window.show_notification(f"Błąd eksportu CSV: {str(e)}", duration=3000, error=True)


def export_to_png(main_window):
    filepath, _ = QFileDialog.getSaveFileName(main_window, "Eksport do PNG", "", "PNG Files (*.png)")
    if not filepath:
        return

    try:
        pixmap = main_window.schedule_widget.grab()
        pixmap.save(filepath, "PNG")
        main_window.show_notification(f"Zapisano plik: {filepath}", duration=3000)
    except Exception as e:
        main_window.show_notification(f"Błąd eksportu PNG: {str(e)}", duration=3000, error=True)


def export_to_html(main_window):
    filepath, _ = QFileDialog.getSaveFileName(main_window, "Eksport do HTML", "", "HTML Files (*.html)")
    if not filepath:
        return

    schedule_data = main_window.schedule_widget.get_current_schedule_data()
    schedule_data.sort(key=lambda x: (x['Shift Start'], x['Shift End']))

    try:
        lines = [
            "<html>",
            "<head><meta charset='utf-8'><title>Harmonogram</title></head>",
            "<body>",
            "<h1>Wygenerowany Harmonogram</h1>",
            "<table border='1' cellspacing='0' cellpadding='4'>",
            "<tr><th>Data</th><th>Godzina startu</th><th>Godzina końca</th><th>Osoby</th></tr>"
        ]
        for row in schedule_data:
            dt_str = row['Shift Start'].strftime("%Y-%m-%d")
            st_str = row['Shift Start'].strftime("%H:%M")
            en_str = row['Shift End'].strftime("%H:%M")
            assigned = row['Assigned To']
            lines.append(
                f"<tr>"
                f"<td>{dt_str}</td>"
                f"<td>{st_str}</td>"
                f"<td>{en_str}</td>"
                f"<td>{assigned}</td>"
                f"</tr>"
            )
        lines.append("</table></body></html>")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        main_window.show_notification(f"Zapisano plik: {filepath}", duration=3000)
    except Exception as e:
        main_window.show_notification(f"Błąd eksportu HTML: {str(e)}", duration=3000, error=True)
