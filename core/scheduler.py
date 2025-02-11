import multiprocessing
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from collections import defaultdict

def build_day_slots(participants, poll_dates, shift_duration):
    """
    Buduje listę slotów (start_dt, end_dt) dla wszystkich dni w poll_dates,
    opierając się na minimalnych i maksymalnych godzinach dostępności.
    
    Parametry:
      - participants: lista słowników, np. [{'name': 'A', 'availabilities': [(datetime, datetime), ...]}, ...]
      - poll_dates: lista dat w formacie "YYYY-MM-DD"
      - shift_duration: długość jednego slotu (w minutach)
    
    Zwraca:
      (day_slots_dict, unique_slots)
        - day_slots_dict: słownik { "YYYY-MM-DD" -> lista slotów (start, end) }
        - unique_slots: posortowana lista wszystkich slotów z wszystkich dni
    """
    day_slots_dict = {}
    for day_str in poll_dates:
        date_obj = datetime.strptime(day_str, "%Y-%m-%d").date()
        day_min = None
        day_max = None
        for p in participants:
            for av_start, av_end in p['availabilities']:
                if av_start.date() == date_obj:
                    if day_min is None or av_start < day_min:
                        day_min = av_start
                    if day_max is None or av_end > day_max:
                        day_max = av_end

        slots = []
        if day_min and day_max:
            current = day_min
            while current < day_max:
                slot_end = current + timedelta(minutes=shift_duration)
                if slot_end > day_max:
                    slot_end = day_max
                slots.append((current, slot_end))
                current = slot_end
        day_slots_dict[day_str] = slots

    all_slots = []
    for d in poll_dates:
        all_slots.extend(day_slots_dict[d])
    unique_slots = sorted(list(set(all_slots)), key=lambda x: x[0])
    return day_slots_dict, unique_slots


def assign_shifts(
    participants,
    slot_list,
    num_required,           # maksymalna liczba osób w slocie
    min_required,           # minimalna liczba osób w slocie
    max_hours,              # maks. godzin w całym okresie
    max_hours_per_day,      # maks. godzin dziennie
    gap_penalty=3,          # waga kary za "przerwy" (extra bloki) u pojedynczej osoby
    coverage_reward=2,      # waga nagrody za ciągłość slotów w ciągu dnia (z perspektywy biura)
    day_coverage_reward=2,  # waga nagrody za każdy dzień, w którym jest cokolwiek obsadzone
    time_limit=15.0,        # limit czasu (w sekundach)
    use_60_percent_cores=True
):
    """
    Rozpisuje dyżury, zwracając (schedule_data, total_hours), gdzie:
      - schedule_data to lista słowników o kluczach: 'Shift Start', 'Shift End', 'Assigned To'
      - total_hours to słownik { participant_name -> łączna liczba przepracowanych godzin }

    Idea modelu (funkcja celu):
      Maximize(
          SUM_of_assignments
          + coverage_reward * SUM_of_continuous_slots_in_a_day
          - gap_penalty * SUM_of_extra_blocks_per_person
          + day_coverage_reward * SUM_of_days_that_are_covered
      )

    Parametry:
      - participants: lista uczestników (każdy: {'name': str, 'availabilities': [(datetime_start, datetime_end), ...]})
      - slot_list: lista slotów (start_datetime, end_datetime), np. wynik z build_day_slots(...)
      - num_required: maksymalna liczba osób w slocie
      - min_required: minimalna liczba osób w slocie (jeśli nie osiągniemy minimum, slot się nie aktywuje)
      - max_hours: maks. liczba godzin łącznie dla jednej osoby
      - max_hours_per_day: maks. liczba godzin dziennie dla jednej osoby
      - gap_penalty: kara za „przerwy” u tej samej osoby w ciągu jednego dnia
      - coverage_reward: nagroda za ciągłe pokrycie slotów (j i j+1) w danym dniu
      - day_coverage_reward: nagroda za każdy dzień, w którym jest przynajmniej jeden obsadzony slot
      - time_limit: ile sekund solver może maksymalnie pracować (po tym czasie zwraca najlepsze znalezione rozwiązanie)
      - use_60_percent_cores: jeśli True, solver użyje ~60% rdzeni procesora w trybie równoległym

    Zwraca:
      (schedule_data, total_hours)
        - schedule_data: list(dict), np. [{'Shift Start': dt1, 'Shift End': dt2, 'Assigned To': 'Jan, Anna'}, ...]
        - total_hours: dict, np. {'Jan': 5.0, 'Anna': 3.5, ...}
                      (suma godzin w przypisanych slotach)
    """
    if not participants or not slot_list:
        return None, None

    model = cp_model.CpModel()

    # Długość slotu w minutach
    shift_minutes = int((slot_list[0][1] - slot_list[0][0]).total_seconds() // 60)

    # Limity godzinowe
    max_minutes = int(max_hours * 60)
    max_minutes_per_day = int(max_hours_per_day * 60)

    num_participants = len(participants)
    num_shifts = len(slot_list)

    # -------------------------------------------
    # Zmienne decyzyjne:
    #
    # assignments[(i, j)]: 1 jeśli uczestnik i pracuje w slocie j
    # shift_assigned[j]:   1 jeśli slot j jest w ogóle używany
    #
    # day_covered[d]:      1 jeśli w dniu d cokolwiek jest obsadzone
    # -------------------------------------------
    assignments = {}
    shift_assigned = {}
    for j in range(num_shifts):
        shift_assigned[j] = model.NewBoolVar(f'shift_assigned_{j}')

    for i in range(num_participants):
        for j in range(num_shifts):
            start_dt, end_dt = slot_list[j]
            if any(start_dt >= avs and end_dt <= ave for (avs, ave) in participants[i]['availabilities']):
                assignments[(i, j)] = model.NewBoolVar(f'assign_p{i}_s{j}')
            else:
                assignments[(i, j)] = None

    # -------------------------------------------
    # Ograniczenie: min_required i num_required
    # -------------------------------------------
    for j in range(num_shifts):
        vars_in_shift = [assignments[(i, j)] for i in range(num_participants)
                        if assignments[(i, j)] is not None]
        if vars_in_shift:
            num_assigned = sum(vars_in_shift)
            # 1) jeśli shift_assigned[j] == 1 => num_assigned >= min_required
            model.Add(num_assigned >= min_required).OnlyEnforceIf(shift_assigned[j])
            # 2) jeśli shift_assigned[j] == 0 => num_assigned == 0 (nikt nie pracuje)
            model.Add(num_assigned == 0).OnlyEnforceIf(shift_assigned[j].Not())
            # 3) jeśli slot użyty => num_assigned <= num_required
            model.Add(num_assigned <= num_required).OnlyEnforceIf(shift_assigned[j])
            # 4) assignment(i, j) może być 1 tylko wtedy, gdy shift_assigned[j] == 1
            for var in vars_in_shift:
                model.Add(var <= shift_assigned[j])
        else:
            # Jeśli nikt nie może pracować w tym slocie, to slot_assigned = 0
            model.Add(shift_assigned[j] == 0)

    # -------------------------------------------
    # Ograniczenia godzinowe per participant
    # -------------------------------------------
    for i in range(num_participants):
        # Wszystkie sloty, w których dana osoba i może pracować
        total_shifts_i = [assignments[(i, j)] for j in range(num_shifts)
                          if assignments[(i, j)] is not None]
        if total_shifts_i:
            # 1) Całkowity limit w całym okresie
            total_minutes = sum(total_shifts_i) * shift_minutes
            model.Add(total_minutes <= max_minutes)
            # 2) Ograniczenia dzienne
            shifts_per_day = defaultdict(list)
            for j in range(num_shifts):
                if assignments.get((i, j)) is not None:
                    day_of_shift = slot_list[j][0].date()
                    shifts_per_day[day_of_shift].append(assignments[(i, j)])
            for day, arr in shifts_per_day.items():
                day_minutes = sum(arr) * shift_minutes
                model.Add(day_minutes <= max_minutes_per_day)

    # -------------------------------------------
    # Przygotowanie struktur do:
    # 1) Kary za przerwy (gap_penalty)
    # 2) Nagradzanie ciągłości coverage_reward
    # 3) Nagradzanie "aktywnego" dnia (day_covered)
    # -------------------------------------------
    # day_to_slots_idx: {date -> list of slot indices in chronological order}
    day_to_slots_idx = defaultdict(list)
    for j, slot in enumerate(slot_list):
        day = slot[0].date()
        day_to_slots_idx[day].append(j)
    for d in day_to_slots_idx:
        day_to_slots_idx[d].sort(key=lambda idx: slot_list[idx][0])

    # (1) Kara za przerwy u pojedynczej osoby
    start_vars = {}
    for i in range(num_participants):
        for d, slots_idx in day_to_slots_idx.items():
            for idx_in_day, j in enumerate(slots_idx):
                if assignments[(i, j)] is not None:
                    start_vars[(i, j)] = model.NewBoolVar(f'start_i{i}_s{j}')
                    if idx_in_day == 0:
                        # Pierwszy slot w dniu => start = assignments
                        model.Add(start_vars[(i, j)] == assignments[(i, j)])
                    else:
                        j_prev = slots_idx[idx_in_day - 1]
                        if assignments[(i, j_prev)] is None:
                            model.Add(start_vars[(i, j)] == assignments[(i, j)])
                        else:
                            # start_i_j = 1 jeśli w tym slocie i jest, a w poprzednim nie
                            model.Add(start_vars[(i, j)] <= assignments[(i, j)])
                            model.Add(start_vars[(i, j)] <= 1 - assignments[(i, j_prev)])
                            model.Add(start_vars[(i, j)] >= assignments[(i, j)] - assignments[(i, j_prev)])
                else:
                    start_vars[(i, j)] = model.NewConstant(0)

    block_count = {}
    for i in range(num_participants):
        for d, slots_idx in day_to_slots_idx.items():
            start_list = [start_vars[(i, j)]
                          for j in slots_idx
                          if (i, j) in start_vars]
            if start_list:
                bc = model.NewIntVar(0, len(start_list), f'block_count_i{i}_d{d}')
                model.Add(bc == sum(start_list))
                block_count[(i, d)] = bc
            else:
                block_count[(i, d)] = model.NewConstant(0)

    # extra_blocks_i_d = max(block_count_i_d - 1, 0)
    extra_blocks = []
    for (i, d), bc in block_count.items():
        max_possible = len(day_to_slots_idx[d])
        ebd = model.NewIntVar(0, max_possible, f'extra_blocks_i{i}_d{d}')
        extra_blocks.append(ebd)
        model.Add(ebd >= bc - 1)
        model.Add(ebd <= bc)

    sum_of_extras = sum(extra_blocks)

    # (2) Nagradzanie ciągłości z perspektywy biura
    continuity_vars = []
    for d, slots_idx in day_to_slots_idx.items():
        for k in range(len(slots_idx) - 1):
            j1 = slots_idx[k]
            j2 = slots_idx[k + 1]
            cvar = model.NewBoolVar(f'cont_j{j1}_j{j2}')
            model.Add(cvar <= shift_assigned[j1])
            model.Add(cvar <= shift_assigned[j2])
            model.Add(cvar >= shift_assigned[j1] + shift_assigned[j2] - 1)
            continuity_vars.append(cvar)
    sum_of_continuity = sum(continuity_vars)

    # (3) Nagradzanie "aktywnego dnia" = czy w danym dniu jest cokolwiek obsadzone
    day_covered = {}
    for d, slots_idx in day_to_slots_idx.items():
        dc = model.NewBoolVar(f'day_covered_{d}')
        # sum_in_day = suma shift_assigned[j] dla slotów danego dnia
        sum_in_day = sum(shift_assigned[j] for j in slots_idx)
        # day_covered[d] == 1 <=> sum_in_day >= 1
        model.Add(sum_in_day == 0).OnlyEnforceIf(dc.Not())
        model.Add(sum_in_day >= 1).OnlyEnforceIf(dc)
        day_covered[d] = dc
    sum_of_covered_days = sum(day_covered.values())

    # -------------------------------------------
    # Suma przypisań (ile osób łącznie we wszystkich slotach)
    # -------------------------------------------
    all_assigns = []
    for i in range(num_participants):
        for j in range(num_shifts):
            if assignments[(i, j)] is not None:
                all_assigns.append(assignments[(i, j)])
    sum_of_assignments = sum(all_assigns)

    # -------------------------------------------
    # Funkcja celu
    #
    # Maximize(
    #   sum_of_assignments
    #   + coverage_reward * sum_of_continuity
    #   - gap_penalty * sum_of_extras
    #   + day_coverage_reward * sum_of_covered_days
    # )
    # -------------------------------------------
    objective_expr = (
        sum_of_assignments
        + coverage_reward * sum_of_continuity
        - gap_penalty * sum_of_extras
        + day_coverage_reward * sum_of_covered_days
    )
    model.Maximize(objective_expr)

    # -------------------------------------------
    # Konfiguracja solvera
    # -------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit

    if use_60_percent_cores:
        num_cores = multiprocessing.cpu_count()
        use_cores = max(1, int(num_cores * 0.60))
        solver.parameters.num_search_workers = use_cores
    else:
        solver.parameters.num_search_workers = 1
        # solver.parameters.num_search_workers = multiprocessing.cpu_count()

    # -------------------------------------------
    # Rozwiązywanie
    # -------------------------------------------
    status = solver.Solve(model)
    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return None, None

    # -------------------------------------------
    # Odczytanie rozwiązania
    # -------------------------------------------
    schedule_data = []
    total_hours = {p['name']: 0.0 for p in participants}
    for j in range(num_shifts):
        if solver.Value(shift_assigned[j]) == 1:
            assigned_names = []
            for i in range(num_participants):
                if assignments[(i, j)] is not None and solver.Value(assignments[(i, j)]) == 1:
                    assigned_names.append(participants[i]['name'])
            if assigned_names:
                start_dt, end_dt = slot_list[j]
                dur_hrs = (end_dt - start_dt).total_seconds() / 3600.0
                schedule_data.append({
                    'Shift Start': start_dt,
                    'Shift End': end_dt,
                    'Assigned To': ", ".join(assigned_names)
                })
                for nm in assigned_names:
                    total_hours[nm] += dur_hrs

    return schedule_data, total_hours
