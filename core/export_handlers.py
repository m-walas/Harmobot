from datetime import datetime
import csv, re
from PyQt6.QtWidgets import QFileDialog, QMessageBox


def load_from_csv(main_window):
    """
    Loads schedule data from a CSV file in matrix format and updates the main window's schedule widget.
    Expected CSV format:
        - The first row (header) should have "Godzina" in the first cell and dates (YYYY-MM-DD) in subsequent cells.
        - Each subsequent row represents a time slot, with the first cell as a time range "HH:MM - HH:MM",
            and subsequent cells containing occupant names (separated by newline if multiple).
    important: The shift duration is computed dynamically based on the first valid time slot.
    """

    filepath, _ = QFileDialog.getOpenFileName(main_window, "Wczytaj CSV", "", "CSV Files (*.csv)")
    if not filepath:
        return

    try:
        with open(filepath, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=";")
            rows = list(reader)
        if not rows:
            QMessageBox.warning(main_window, "Błąd", "Plik CSV jest pusty.")
            return

        header = rows[0]
        if len(header) < 2:
            QMessageBox.warning(main_window, "Błąd", "Niepoprawny format CSV.")
            return

        if header[0].strip().lower() != "godzina":
            QMessageBox.information(main_window, "Import CSV",
                                    "Niepoprawny format CSV.\nUpewnij się, że eksport jest w formacie macierzowym.")
            return

        date_list = [d.strip() for d in header[1:] if d.strip()]
        schedule_entries = []
        first_duration = None
        for row in rows[1:]:
            if len(row) == 0 or all(cell.strip() == "" for cell in row):
                continue
            time_range = row[0].strip()
            m = re.match(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", time_range)
            if not m:
                continue
            start_str, end_str = m.group(1), m.group(2)
            try:
                start_time = datetime.strptime(start_str, "%H:%M").time()
                end_time = datetime.strptime(end_str, "%H:%M").time()
            except Exception:
                continue
            if first_duration is None:
                dt_start = datetime.combine(datetime.today(), start_time)
                dt_end = datetime.combine(datetime.today(), end_time)
                first_duration = (dt_end - dt_start).seconds // 60
                if first_duration <= 0:
                    first_duration = 30
            for i, cell in enumerate(row[1:], start=0):
                date_str = date_list[i]
                if not cell.strip():
                    continue
                occupants = [name.strip() for name in cell.split("\n") if name.strip()]
                try:
                    y, m_val, d = map(int, date_str.split("-"))
                    sdt = datetime(y, m_val, d, start_time.hour, start_time.minute)
                    edt = datetime(y, m_val, d, end_time.hour, end_time.minute)
                except Exception:
                    continue
                schedule_entries.append({
                    "Shift Start": sdt,
                    "Shift End": edt,
                    "Assigned To": ", ".join(occupants)
                })
        if not schedule_entries:
            QMessageBox.warning(main_window, "Błąd", "Nie znaleziono danych w CSV.")
            return

        sorted_dates = sorted(date_list)
        main_window.poll_dates = sorted_dates
        full_slots = sorted(
            [(entry["Shift Start"], entry["Shift End"]) for entry in schedule_entries],
            key=lambda x: x[0]
        )
        main_window.full_slots = full_slots

        if not main_window.participants:
            names = set()
            for entry in schedule_entries:
                for name in entry["Assigned To"].split(","):
                    if name.strip():
                        names.add(name.strip())
            main_window.participants = [{"name": n, "availabilities": [], "ifNeeded": []} for n in names]

        if hasattr(main_window, "schedule_widget"):
            shift_duration = first_duration if first_duration else 30
            main_window.schedule_widget.load_schedule_matrix(
                schedule_data=schedule_entries,
                participants=main_window.participants,
                poll_dates=main_window.poll_dates,
                time_slot_list=main_window._build_time_slot_list(shift_duration)
            )
            main_window.schedule_widget.setMaxHours(float(main_window.max_hours_spin.value()))
            main_window.update_summary()
    except Exception as e:
        QMessageBox.warning(main_window, "Błąd importu CSV", str(e))


def export_to_csv(main_window):
    """
    Exports the current schedule data to a CSV file in matrix format.
    Columns correspond to dates and rows represent time slots (with time range labels).
    """

    filepath, _ = QFileDialog.getSaveFileName(
        main_window, "Eksport do CSV", "", "CSV Files (*.csv)"
    )
    if not filepath:
        return

    schedule_widget = main_window.schedule_widget
    date_list = schedule_widget.date_list            # Columns: list of date strings
    time_slot_list = schedule_widget.time_slot_list    # Rows: list of (start, end) time tuples
    occupant_data = schedule_widget.occupant_data       # Mapping (row, col) -> list of occupant names

    try:
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            header = ["Godzina"] + date_list
            writer.writerow(header)
            for r, (t1, t2) in enumerate(time_slot_list):
                time_label = f"{t1.strftime('%H:%M')} - {t2.strftime('%H:%M')}"
                row = [time_label]
                for c, _ in enumerate(date_list):
                    occupants = occupant_data.get((r, c), [])
                    cell_text = "\n".join(occupants) if occupants else ""
                    row.append(cell_text)
                writer.writerow(row)
            writer.writerow([])
            writer.writerow(["Wygenerowano z użyciem Harmobot"])
    except Exception as e:
        return


def export_to_png(main_window):
    """
    Exports the schedule widget as a PNG image.
    """
    filepath, _ = QFileDialog.getSaveFileName(main_window, "Eksport do PNG", "", "PNG Files (*.png)")
    if not filepath:
        return

    try:
        pixmap = main_window.schedule_widget.grab()
        pixmap.save(filepath, "PNG")
    except Exception as e:
        return


def export_to_html(main_window):
    """
    Exports the current schedule data to an HTML file presented in a matrix format.
    Columns correspond to dates and rows represent time slots.
    """

    filepath, _ = QFileDialog.getSaveFileName(
        main_window, "Eksport do HTML", "", "HTML Files (*.html)"
    )
    if not filepath:
        return

    schedule_widget = main_window.schedule_widget
    date_list = schedule_widget.date_list
    time_slot_list = schedule_widget.time_slot_list
    occupant_data = schedule_widget.occupant_data

    header_html = "<tr><th>Godzina</th>"
    for d in date_list:
        header_html += f"<th>{d}</th>"
    header_html += "</tr>\n"

    rows_html = ""
    for r, (t1, t2) in enumerate(time_slot_list):
        time_label = f"{t1.strftime('%H:%M')} - {t2.strftime('%H:%M')}"
        row_html = f"<tr><th>{time_label}</th>"
        for c, d in enumerate(date_list):
            occupants = occupant_data.get((r, c), [])
            cell_text = "<br>".join(occupants) if occupants else ""
            row_html += f"<td>{cell_text}</td>"
        row_html += "</tr>\n"
        rows_html += row_html

    html_content = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<title>Grafik</title>
<style>
    body {{
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        background-color: #ffffff;
        margin: 20px;
    }}
    h2 {{
        text-align: center;
    }}
    table {{
        width: 100%;
        margin: 0 auto;
        border-collapse: collapse;
    }}
    th, td {{
        border: 1px solid #cccccc;
        padding: 8px;
        text-align: center;
        vertical-align: middle;
    }}
    th {{
        background-color: #f2f2f2;
    }}
    tr:nth-child(even) {{
        background-color: #fafafa;
    }}
    p.footer {{
        text-align: center;
        font-size: 0.8em;
        color: #666;
        margin-top: 10px;
    }}
</style>
</head>
<body>
<h2>Grafik</h2>
<table>
{header_html}
{rows_html}
</table>
<p class="footer">Wygenerowano z użyciem Harmobot</p>
</body>
</html>
"""
    try:
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(html_content)
    except Exception as e:
        return
