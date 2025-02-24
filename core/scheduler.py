import multiprocessing
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from collections import defaultdict

def build_day_slots(participants, poll_dates, shift_duration, day_ranges=None):
    """
    Builds a list of time slots (start_dt, end_dt) for all days in poll_dates based on the available time ranges.

    Args:
        participants (list): List of dictionaries with keys:
            - 'name': str,
            - 'availabilities': list of tuples (datetime, datetime),
            - 'ifNeeded': list of tuples (datetime, datetime)
        poll_dates (list): List of date strings in "YYYY-MM-DD" format.
        shift_duration (int): Duration of each slot in minutes.
        day_ranges (dict, optional): Dictionary mapping each date string to a tuple (start_dt, end_dt).

    Returns:
        tuple: (day_slots_dict, unique_slots) where:
            - day_slots_dict is a dict mapping each date string to a list of slots (start, end).
            - unique_slots is a sorted list of unique slots across all days.
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
    num_required,           # maximum number of participants per slot
    min_required,           # minimum number of participants per slot
    max_hours,              # maximum hours over the entire period
    max_hours_per_day,      # maximum hours per day
    solver_time_limit,      # time limit for the solver from settings dialog
    solver_num_threads,     # number of threads for the solver from settings dialog
    gap_penalty=3,          # penalty for breaks
    coverage_reward=2,      # reward for continuity within a day
    day_coverage_reward=2,  # reward for each covered day
    ifNeeded_penalty=2      # penalty for 'ifNeeded' slots
):
    """
    Assigns shifts and returns (schedule_data, total_hours).

    The 'ifNeeded_penalty' is applied as a negative component in the objective function:
        - ifNeeded_penalty * sum(assignments[i,j]) for assignments marked as 'ifNeeded'.

    Args:
        participants (list): List of participant dictionaries.
        slot_list (list): List of time slots as tuples (start_dt, end_dt).
        num_required (int): Maximum number of participants per slot.
        min_required (int): Minimum number of participants per slot.
        max_hours (float): Maximum total hours per participant.
        max_hours_per_day (float): Maximum hours per participant per day.
        solver_time_limit (int): Time limit for the solver in seconds.
        solver_num_threads (int): Number of threads for the solver.
        gap_penalty (int, optional): Penalty for breaks.
        coverage_reward (int, optional): Reward for continuity in a day.
        day_coverage_reward (int, optional): Reward for each day that is covered.
        ifNeeded_penalty (int, optional): Penalty for assignments in 'ifNeeded' slots.

    Returns:
        tuple: (schedule_data, total_hours) where:
            - schedule_data is a list of dictionaries with keys 'Shift Start', 'Shift End', and 'Assigned To'.
            - total_hours is a dict mapping participant names to their total assigned hours.
        If no feasible solution is found, returns (None, None).
    """
    if not participants or not slot_list:
        return None, None

    model = cp_model.CpModel()

    # Duration of a slot in minutes
    shift_minutes = int((slot_list[0][1] - slot_list[0][0]).total_seconds() // 60)

    # Convert hour limits to minutes
    max_minutes = int(max_hours * 60)
    max_minutes_per_day = int(max_hours_per_day * 60)

    num_participants = len(participants)
    num_shifts = len(slot_list)

    # Decision variables: assignments[i,j], shift_assigned[j], and ifNeeded flag
    assignments = {}
    shift_assigned = {}
    if_needed_flag = {}

    for j in range(num_shifts):
        shift_assigned[j] = model.NewBoolVar(f'shift_assigned_{j}')

    for i in range(num_participants):
        for j in range(num_shifts):
            start_dt, end_dt = slot_list[j]

            # Check if the slot is within normal availability
            normal_ok = any(
                start_dt >= avs and end_dt <= ave
                for (avs, ave) in participants[i]['availabilities']
            )
            # Check if the slot is within 'ifNeeded'
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

    # Constraints: enforce min_required and num_required per shift
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

    # Hourly constraints for each participant
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

    # Structures for gap_penalty, coverage_reward, etc.
    day_to_slots_idx = defaultdict(list)
    for j, slot in enumerate(slot_list):
        d = slot[0].date()
        day_to_slots_idx[d].append(j)
    for d in day_to_slots_idx:
        day_to_slots_idx[d].sort(key=lambda idx: slot_list[idx][0])

    # (1) gap_penalty: penalty for extra blocks (gaps)
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

    # (2) coverage_reward: reward for continuity
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

    # (3) Day coverage: reward for each day that is covered
    day_covered = {}
    for d, slots_idx in day_to_slots_idx.items():
        dc = model.NewBoolVar(f'day_covered_{d}')
        sum_in_day = sum(shift_assigned[j] for j in slots_idx)
        model.Add(sum_in_day == 0).OnlyEnforceIf(dc.Not())
        model.Add(sum_in_day >= 1).OnlyEnforceIf(dc)
        day_covered[d] = dc
    sum_of_covered_days = sum(day_covered.values())

    # Total assignments across all slots
    all_assigns = []
    for i in range(num_participants):
        for j in range(num_shifts):
            if assignments[(i, j)] is not None:
                all_assigns.append(assignments[(i, j)])
    sum_of_assignments = sum(all_assigns)

    # Sum of ifNeeded assignments
    ifNeeded_assigns = []
    for (i, j), var in assignments.items():
        if var is not None and if_needed_flag.get((i, j), 0) == 1:
            ifNeeded_assigns.append(var)
    sum_of_ifNeeded = sum(ifNeeded_assigns)

    # Objective function
    objective_expr = (
        sum_of_assignments
        + coverage_reward * sum_of_continuity
        - gap_penalty * sum_of_extras
        + day_coverage_reward * sum_of_covered_days
        - ifNeeded_penalty * sum_of_ifNeeded
    )
    model.Maximize(objective_expr)

    # Solver configuration
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = solver_time_limit
    solver.parameters.num_search_workers = solver_num_threads

    # Solve the model
    status = solver.Solve(model)
    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return None, None

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
