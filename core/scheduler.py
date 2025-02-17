import multiprocessing
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from collections import defaultdict

def build_day_slots(participants, poll_dates, shift_duration, day_ranges=None):
    """
    Buduje listę slotów (start_dt, end_dt) dla wszystkich dni w poll_dates,
    opierając się na minimalnych i maksymalnych godzinach dostępności.
    
    Parametry:
        - participants: [{'name': 'A', 'availabilities': [(dt1, dt2), ...], 'ifNeeded': [...]}, ...]
        - poll_dates: lista dat w formacie "YYYY-MM-DD"
        - shift_duration: długość jednego slotu (w minutach)
        - day_ranges: opcjonalnie, słownik z minimalnymi i maksymalnymi godzinami dla każdego dnia
            { "YYYY-MM-DD": (start_dt, end_dt), ... }
    Zwraca:
        (day_slots_dict, unique_slots)
        - day_slots_dict: { "YYYY-MM-DD": [(start, end), ...], ... }
        - unique_slots: posortowana lista unikalnych slotów ze wszystkich dni
    """
    day_slots_dict = {}
    for day_str in poll_dates:
        date_obj = datetime.strptime(day_str, "%Y-%m-%d").date()

        if day_ranges and day_str in day_ranges:
            day_min, day_max = day_ranges[day_str]
        else:
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
    num_required,           # maks. liczba osób w slocie
    min_required,           # min. liczba osób w slocie
    max_hours,              # maks. godzin w całym okresie
    max_hours_per_day,      # maks. godzin dziennie
    gap_penalty=3,          # kara za przerwy
    coverage_reward=2,      # nagroda za ciągłość w ciągu dnia
    day_coverage_reward=2,  # nagroda za każdy dzień obsadzony
    ifNeeded_penalty=2,     # kara za sloty ifNeeded
    time_limit=15.0,
    use_60_percent_cores=True
):
    """
    Rozpisuje dyżury i zwraca (schedule_data, total_hours).

    ifNeeded_penalty => minusowy składnik w funkcji celu:
        - ifNeeded_penalty * SUM( assignments[i,j] ) 
        dla tych (i,j), które są 'ifNeeded'.
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
    # Zmienne decyzyjne: assignments[i,j], shift_assigned[j]
    # + flaga ifNeeded
    # -------------------------------------------
    assignments = {}
    shift_assigned = {}
    if_needed_flag = {}

    for j in range(num_shifts):
        shift_assigned[j] = model.NewBoolVar(f'shift_assigned_{j}')

    for i in range(num_participants):
        for j in range(num_shifts):
            start_dt, end_dt = slot_list[j]

            # czy dany slot (start_dt, end_dt) jest w normalnej avail...
            normal_ok = any(
                start_dt >= avs and end_dt <= ave
                for (avs, ave) in participants[i]['availabilities']
            )
            # ...albo w ifNeeded
            ifneeded_ok = any(
                start_dt >= ivs and end_dt <= ive
                for (ivs, ive) in participants[i]['ifNeeded']
            )

            if normal_ok or ifneeded_ok:
                assignments[(i, j)] = model.NewBoolVar(f'assign_p{i}_s{j}')

                if ifneeded_ok and not normal_ok:
                    if_needed_flag[(i, j)] = 1
                else:
                    if_needed_flag[(i, j)] = 0
            else:
                assignments[(i, j)] = None

    # -------------------------------------------
    # Ograniczenie: min_required i num_required
    # -------------------------------------------
    for j in range(num_shifts):
        vars_in_shift = [
            assignments[(i, j)] 
            for i in range(num_participants)
            if assignments[(i, j)] is not None
        ]
        if vars_in_shift:
            num_assigned = sum(vars_in_shift)
            model.Add(num_assigned >= min_required).OnlyEnforceIf(shift_assigned[j])
            model.Add(num_assigned == 0).OnlyEnforceIf(shift_assigned[j].Not())
            model.Add(num_assigned <= num_required).OnlyEnforceIf(shift_assigned[j])
            for var in vars_in_shift:
                model.Add(var <= shift_assigned[j])
        else:
            model.Add(shift_assigned[j] == 0)

    # -------------------------------------------
    # Ograniczenia godzinowe
    # -------------------------------------------
    for i in range(num_participants):
        total_shifts_i = [
            assignments[(i, j)] 
            for j in range(num_shifts) 
            if assignments[(i, j)] is not None
        ]
        if total_shifts_i:
            total_minutes = sum(total_shifts_i) * shift_minutes
            model.Add(total_minutes <= max_minutes)

            shifts_per_day = defaultdict(list)
            for j in range(num_shifts):
                if assignments.get((i, j)) is not None:
                    day_of_shift = slot_list[j][0].date()
                    shifts_per_day[day_of_shift].append(assignments[(i, j)])
            for day, arr in shifts_per_day.items():
                day_minutes = sum(arr) * shift_minutes
                model.Add(day_minutes <= max_minutes_per_day)

    # -------------------------------------------
    # Struktury do gap_penalty, coverage_reward itd.
    # -------------------------------------------
    day_to_slots_idx = defaultdict(list)
    for j, slot in enumerate(slot_list):
        d = slot[0].date()
        day_to_slots_idx[d].append(j)
    for d in day_to_slots_idx:
        day_to_slots_idx[d].sort(key=lambda idx: slot_list[idx][0])

    # (1) gap_penalty = kara za dodatkowe "bloki"
    start_vars = {}
    for i in range(num_participants):
        for d, slots_idx in day_to_slots_idx.items():
            for idx_in_day, j in enumerate(slots_idx):
                if assignments[(i, j)] is not None:
                    start_vars[(i, j)] = model.NewBoolVar(f'start_i{i}_s{j}')
                    if idx_in_day == 0:
                        model.Add(start_vars[(i, j)] == assignments[(i, j)])
                    else:
                        j_prev = slots_idx[idx_in_day - 1]
                        if assignments[(i, j_prev)] is None:
                            model.Add(start_vars[(i, j)] == assignments[(i, j)])
                        else:
                            model.Add(start_vars[(i, j)] <= assignments[(i, j)])
                            model.Add(start_vars[(i, j)] <= 1 - assignments[(i, j_prev)])
                            model.Add(start_vars[(i, j)] >= assignments[(i, j)] - assignments[(i, j_prev)])
                else:
                    start_vars[(i, j)] = model.NewConstant(0)

    block_count = {}
    for i in range(num_participants):
        for d, slots_idx in day_to_slots_idx.items():
            start_list = [start_vars[(i, j)] for j in slots_idx if (i, j) in start_vars]
            if start_list:
                bc = model.NewIntVar(0, len(start_list), f'block_count_i{i}_d{d}')
                model.Add(bc == sum(start_list))
                block_count[(i, d)] = bc
            else:
                block_count[(i, d)] = model.NewConstant(0)

    extra_blocks = []
    for (i, d), bc in block_count.items():
        max_possible = len(day_to_slots_idx[d])
        ebd = model.NewIntVar(0, max_possible, f'extra_blocks_i{i}_d{d}')
        extra_blocks.append(ebd)
        model.Add(ebd >= bc - 1)
        model.Add(ebd <= bc)

    sum_of_extras = sum(extra_blocks)

    # (2) coverage_reward = nagroda za ciągłość
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

    # (3) day_covered
    day_covered = {}
    for d, slots_idx in day_to_slots_idx.items():
        dc = model.NewBoolVar(f'day_covered_{d}')
        sum_in_day = sum(shift_assigned[j] for j in slots_idx)
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
    # Liczymy sumę ifNeeded
    # -------------------------------------------
    ifNeeded_assigns = []
    for (i, j), var in assignments.items():
        if var is not None and if_needed_flag.get((i, j), 0) == 1:
            ifNeeded_assigns.append(var)
    sum_of_ifNeeded = sum(ifNeeded_assigns)

    # -------------------------------------------
    # Funkcja celu
    # -------------------------------------------
    objective_expr = (
        sum_of_assignments
        + coverage_reward * sum_of_continuity
        - gap_penalty * sum_of_extras
        + day_coverage_reward * sum_of_covered_days
        - ifNeeded_penalty * sum_of_ifNeeded
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
