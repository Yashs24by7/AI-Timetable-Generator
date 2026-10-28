from ortools.sat.python import cp_model
import json
from datetime import datetime
from pathlib import Path

from data_loader import load_te_sem_v_data
from faculty_expertise import (
    get_faculty_for_theory,
    get_faculty_for_tutorial,
    get_faculty_for_practical,
)


# ============================================================
# TIMETABLE STRUCTURE
# ============================================================

DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
]

PERIODS = [
    ("P1", "08:45", "09:45"),
    ("P2", "09:45", "10:45"),
    ("P3", "11:00", "12:00"),
    ("P4", "12:00", "13:00"),
    ("P5", "13:45", "14:45"),
    ("P6", "14:45", "15:45"),
]

SLOTS = []

for day_index, day in enumerate(DAYS):
    for period_index, period in enumerate(PERIODS):
        SLOTS.append(
            {
                "index": day_index * 6 + period_index,
                "day": day,
                "period": period[0],
                "start": period[1],
                "end": period[2],
                "day_index": day_index,
                "period_index": period_index,
            }
        )


# ============================================================
# ROOMS
# ============================================================

CLASSROOMS = {
    "312": {"capacity": 80, "type": "classroom"},
    "319": {"capacity": 50, "type": "classroom"},
    "322": {"capacity": 80, "type": "classroom"},
}

LAB_ROOMS = {
    "A317": {"capacity": 48, "type": "lab"},
    "A318": {"capacity": 48, "type": "lab"},
    "A320": {"capacity": 48, "type": "lab"},
}

ROOMS = {**CLASSROOMS, **LAB_ROOMS}


# ============================================================
# BASIC HELPERS
# ============================================================

def get_batch_size(data, batch):
    if batch not in data["batches"]:
        return 0
    return int(data["batches"][batch]["students"])


def get_group_size(data, session):
    return sum(
        get_batch_size(data, batch)
        for batch in session.get("batch", [])
    )


def groups_overlap(session_a, session_b):
    batches_a = set(session_a.get("batch", []))
    batches_b = set(session_b.get("batch", []))
    return bool(batches_a.intersection(batches_b))


def valid_start_slots(duration):
    """Return valid slot indexes for 1-hour or 2-hour sessions."""
    result = []

    for slot in SLOTS:
        p = slot["period_index"]

        if duration == 1:
            result.append(slot["index"])

        elif duration == 2:
            # P1-P2, P3-P4, P5-P6
            if p in (0, 2, 4):
                result.append(slot["index"])

    return result


def get_faculty_candidates(session):
    subject = session["subject"]
    session_type = session["type"]

    # Programme Elective THEORY is actually one of two
    # electives: Cloud Computing or Advanced Java.
    if subject == "Programme Elective I":
        elective = session.get("elective", "")

        if elective == "Cloud Computing":
            return get_faculty_for_theory("Cloud Computing")

        if elective == "Advanced Java Programming":
            return get_faculty_for_theory("Advanced Java Programming")

        return []

    # Programme Elective LAB uses the faculty allocation
    # configured for the PE lab.
    if subject == "Programme Elective Lab":
        return get_faculty_for_practical("Programme Elective Lab")

    if session_type == "theory":
        return get_faculty_for_theory(subject)

    if session_type == "tutorial":
        candidates = get_faculty_for_tutorial(subject)

        # Current project data uses "Machine Learning Tutorial"
        # as the reference allocation.
        if not candidates:
            candidates = get_faculty_for_tutorial(
                "Machine Learning Tutorial"
            )

        return candidates

    if session_type == "practical":
        candidates = get_faculty_for_practical(subject)

        # Current project data uses "Machine Learning Practical"
        # as the reference allocation for the ML subject.
        if subject == "Machine Learning" and not candidates:
            candidates = get_faculty_for_practical(
                "Machine Learning Practical"
            )

        return candidates

    return []


def get_room_candidates(data, session):
    required_capacity = get_group_size(data, session)

    if session["type"] == "practical":
        return [
            room
            for room, info in LAB_ROOMS.items()
            if info["capacity"] >= required_capacity
        ]

    return [
        room
        for room, info in CLASSROOMS.items()
        if info["capacity"] >= required_capacity
    ]


def sessions_overlap(start_a, duration_a, start_b, duration_b):
    day_a = start_a // 6
    period_a = int(start_a) % 6

    day_b = start_b // 6
    period_b = int(start_b) % 6

    if day_a != day_b:
        return False

    end_a = period_a + duration_a
    end_b = period_b + duration_b

    return period_a < end_b and period_b < end_a


# ============================================================
# CONDITIONAL RESOURCE CONSTRAINT
# ============================================================

def add_conditional_no_overlap(
    model,
    start_a,
    duration_a,
    start_b,
    duration_b,
    both_use,
    name,
):
    """
    If both_use is true, sessions A and B must not overlap.
    If both_use is false, no ordering constraint is imposed.
    """

    before = model.NewBoolVar(f"{name}_before")
    after = model.NewBoolVar(f"{name}_after")

    # Exactly one ordering when both resources are used.
    model.Add(before + after == 1).OnlyEnforceIf(both_use)

    model.Add(
        start_a + duration_a <= start_b
    ).OnlyEnforceIf([both_use, before])

    model.Add(
        start_b + duration_b <= start_a
    ).OnlyEnforceIf([both_use, after])


def add_resource_conflict(
    model,
    start_a,
    duration_a,
    assignment_a,
    candidates_a,
    start_b,
    duration_b,
    assignment_b,
    candidates_b,
    name_prefix,
):
    """
    Prevent two sessions from using the same faculty/room
    at overlapping times.

    The constraint is conditional on both sessions selecting
    that exact resource.
    """

    common = set(candidates_a).intersection(candidates_b)

    for resource in common:
        index_a = candidates_a.index(resource)
        index_b = candidates_b.index(resource)

        a_uses = model.NewBoolVar(
            f"{name_prefix}_a_uses_{resource}"
        )
        b_uses = model.NewBoolVar(
            f"{name_prefix}_b_uses_{resource}"
        )

        model.Add(
            assignment_a == index_a
        ).OnlyEnforceIf(a_uses)

        model.Add(
            assignment_a != index_a
        ).OnlyEnforceIf(a_uses.Not())

        model.Add(
            assignment_b == index_b
        ).OnlyEnforceIf(b_uses)

        model.Add(
            assignment_b != index_b
        ).OnlyEnforceIf(b_uses.Not())

        both_use = model.NewBoolVar(
            f"{name_prefix}_both_{resource}"
        )

        # both_use <=> a_uses AND b_uses
        model.AddBoolAnd(
            [a_uses, b_uses]
        ).OnlyEnforceIf(both_use)

        model.AddBoolOr(
            [a_uses.Not(), b_uses.Not()]
        ).OnlyEnforceIf(both_use.Not())

        add_conditional_no_overlap(
            model,
            start_a,
            duration_a,
            start_b,
            duration_b,
            both_use,
            f"{name_prefix}_{resource}",
        )


# ============================================================
# PRACTICAL BLOCK IDENTIFICATION
# ============================================================

def get_practical_block(session):
    """
    Sessions belonging to the same practical rotation are
    grouped here.

    Parallelism is an objective, not an unconditional hard
    constraint. This prevents INFEASIBLE when the submitted
    faculty data has fewer than three practical instructors.
    """

    if session["type"] != "practical":
        return None

    subject = session["subject"]
    session_id = session["id"]

    if subject == "Microcontrollers & VLSI Design Lab":
        if "_1_" in session_id:
            return "MCA_VLSI_1"
        if "_2_" in session_id:
            return "MCA_VLSI_2"

    if subject == "Cellular Network Lab":
        return "CN_LAB"

    if subject == "Programme Elective Lab":
        return "PE_LAB"

    if subject == "Machine Learning":
        return "ML_LAB"

    if subject == "Technical Seminar":
        return "TECH_SEMINAR"

    return None


def build_practical_blocks(sessions):
    blocks = {}

    for session in sessions:
        block = get_practical_block(session)

        if block is not None:
            blocks.setdefault(block, []).append(session["id"])

    return blocks


# ============================================================
# RESOURCE CHECK
# ============================================================

def print_resource_check(data, sessions):
    print()
    print("RESOURCE CHECK")
    print("-" * 60)

    print("Classrooms:")
    for room, info in CLASSROOMS.items():
        print(
            f"  {room}: capacity {info['capacity']}"
        )

    print("Labs:")
    for room, info in LAB_ROOMS.items():
        print(
            f"  {room}: capacity {info['capacity']}"
        )

    print()
    print("Session resources:")

    for session in sessions:
        faculty = get_faculty_candidates(session)
        rooms = get_room_candidates(data, session)

        print(
            f"  {session['id']:<24} "
            f"{session['subject']:<38} "
            f"faculty={faculty} "
            f"rooms={rooms}"
        )

    print("-" * 60)


# ============================================================
# BUILD MODEL
# ============================================================

def build_model(data):
    model = cp_model.CpModel()
    sessions = data["sessions"]

    print_resource_check(data, sessions)

    session_start = {}
    room_assignment = {}
    faculty_assignment = {}

    faculty_lists = {}
    room_lists = {}

    # --------------------------------------------------------
    # VARIABLES
    # --------------------------------------------------------

    for index, session in enumerate(sessions):
        session_id = session["id"]

        valid_starts = valid_start_slots(
            session["duration"]
        )

        if not valid_starts:
            raise ValueError(
                f"No valid start time for {session_id}"
            )

        session_start[session_id] = (
            model.NewIntVarFromDomain(
                cp_model.Domain.FromValues(valid_starts),
                f"start_{index}",
            )
        )

        faculty_candidates = get_faculty_candidates(session)

        if not faculty_candidates:
            raise ValueError(
                f"No suitable faculty available for "
                f"{session_id} ({session['subject']})"
            )

        faculty_lists[session_id] = faculty_candidates

        faculty_assignment[session_id] = model.NewIntVar(
            0,
            len(faculty_candidates) - 1,
            f"faculty_{index}",
        )

        room_candidates = get_room_candidates(
            data,
            session,
        )

        if not room_candidates:
            raise ValueError(
                f"No suitable room available for "
                f"{session_id} "
                f"({get_group_size(data, session)} students)"
            )

        room_lists[session_id] = room_candidates

        room_assignment[session_id] = model.NewIntVar(
            0,
            len(room_candidates) - 1,
            f"room_{index}",
        )

    # --------------------------------------------------------
    # STUDENT, FACULTY AND ROOM CONFLICTS
    # --------------------------------------------------------

    for i in range(len(sessions)):
        session_a = sessions[i]
        id_a = session_a["id"]

        for j in range(i + 1, len(sessions)):
            session_b = sessions[j]
            id_b = session_b["id"]

            start_a = session_start[id_a]
            start_b = session_start[id_b]

            duration_a = session_a["duration"]
            duration_b = session_b["duration"]

            # STUDENT/BATCH CONFLICT
            if groups_overlap(session_a, session_b):
                before = model.NewBoolVar(
                    f"student_before_{i}_{j}"
                )
                after = model.NewBoolVar(
                    f"student_after_{i}_{j}"
                )

                model.Add(
                    before + after == 1
                )

                model.Add(
                    start_a + duration_a <= start_b
                ).OnlyEnforceIf(before)

                model.Add(
                    start_b + duration_b <= start_a
                ).OnlyEnforceIf(after)

            # FACULTY CONFLICT
            add_resource_conflict(
                model,
                start_a,
                duration_a,
                faculty_assignment[id_a],
                faculty_lists[id_a],
                start_b,
                duration_b,
                faculty_assignment[id_b],
                faculty_lists[id_b],
                f"faculty_{i}_{j}",
            )

            # ROOM CONFLICT
            add_resource_conflict(
                model,
                start_a,
                duration_a,
                room_assignment[id_a],
                room_lists[id_a],
                start_b,
                duration_b,
                room_assignment[id_b],
                room_lists[id_b],
                f"room_{i}_{j}",
            )

    # --------------------------------------------------------
    # PRACTICAL PARALLELISM
    # --------------------------------------------------------
    #
    # IMPORTANT:
    # This is intentionally a SOFT objective.
    #
    # If three different faculty members/labs are available,
    # the solver will normally put T1/T2/T3 together.
    #
    # If the submitted faculty data only has one or two
    # eligible faculty members, the timetable remains feasible
    # and the affected groups are separated automatically.
    # --------------------------------------------------------

    practical_blocks = build_practical_blocks(sessions)

    parallel_terms = []

    for block, session_ids in practical_blocks.items():

        if len(session_ids) <= 1:
            continue

        for i in range(len(session_ids)):
            for j in range(i + 1, len(session_ids)):

                id_a = session_ids[i]
                id_b = session_ids[j]

                parallel = model.NewBoolVar(
                    f"parallel_{block}_{i}_{j}"
                )

                model.Add(
                    session_start[id_a]
                    ==
                    session_start[id_b]
                ).OnlyEnforceIf(parallel)

                model.Add(
                    session_start[id_a]
                    !=
                    session_start[id_b]
                ).OnlyEnforceIf(parallel.Not())

                parallel_terms.append(parallel)

    # --------------------------------------------------------
    # SUBJECT SPREADING
    # --------------------------------------------------------

    same_day_terms = []

    for i in range(len(sessions)):
        for j in range(i + 1, len(sessions)):

            a = sessions[i]
            b = sessions[j]

            if a["subject"] != b["subject"]:
                continue

            start_a = session_start[a["id"]]
            start_b = session_start[b["id"]]

            day_a = model.NewIntVar(
                0,
                4,
                f"day_{i}_{j}_a",
            )

            day_b = model.NewIntVar(
                0,
                4,
                f"day_{i}_{j}_b",
            )

            model.AddDivisionEquality(
                day_a,
                start_a,
                6,
            )

            model.AddDivisionEquality(
                day_b,
                start_b,
                6,
            )

            same_day = model.NewBoolVar(
                f"same_day_{i}_{j}"
            )

            model.Add(
                day_a == day_b
            ).OnlyEnforceIf(same_day)

            model.Add(
                day_a != day_b
            ).OnlyEnforceIf(same_day.Not())

            same_day_terms.append(same_day)

    # --------------------------------------------------------
    # TIMETABLE QUALITY OBJECTIVES
    # --------------------------------------------------------
    # Hard constraints above guarantee a valid timetable.
    # These terms improve the human usability of that timetable.
    #
    # Priority order:
    #   1. Practical parallelism
    #   2. Spread repeated subjects across different days
    #   3. Avoid unnecessary P6 classes
    #   4. Avoid consecutive sessions of the same subject for
    #      the same batch where the model has a choice
    #
    # These are SOFT objectives: feasibility is never sacrificed.
    # --------------------------------------------------------

    parallel_score = sum(parallel_terms)
    repetition_penalty = sum(same_day_terms)

    # P6 penalty
    # Penalize one-hour sessions scheduled in the last period.
    # A two-hour practical occupying P5-P6 is not penalized here,
    # because P5 is a valid practical start and the block is required.
    p6_terms = []

    for session in sessions:
        if session["duration"] != 1:
            continue

        sid = session["id"]
        p6 = model.NewBoolVar(f"p6_{sid}")

        p6_period = model.NewIntVar(0, 5, f"p6_period_{sid}")
        model.AddModuloEquality(
            p6_period, session_start[sid], 6
        )
        model.Add(
            p6_period == 5
        ).OnlyEnforceIf(p6)
        model.Add(
            p6_period != 5
        ).OnlyEnforceIf(p6.Not())

        p6_terms.append(p6)

    # Consecutive same-subject penalty for the same batch.
    consecutive_terms = []

    def batches_of(session):
        raw_batches = session.get("batch", [])
        if isinstance(raw_batches, str):
            return {b.strip() for b in raw_batches.split(",") if b.strip()}
        return {str(b).strip() for b in raw_batches if str(b).strip()}

    for i in range(len(sessions)):
        for j in range(i + 1, len(sessions)):

            a = sessions[i]
            b = sessions[j]

            if a["subject"] != b["subject"]:
                continue

            if not (batches_of(a) & batches_of(b)):
                continue

            if a["duration"] != 1 or b["duration"] != 1:
                continue

            sid_a = a["id"]
            sid_b = b["id"]

            day_a = model.NewIntVar(0, 4, f"con_day_{i}_{j}_a")
            day_b = model.NewIntVar(0, 4, f"con_day_{i}_{j}_b")
            per_a = model.NewIntVar(0, 5, f"con_per_{i}_{j}_a")
            per_b = model.NewIntVar(0, 5, f"con_per_{i}_{j}_b")

            model.AddDivisionEquality(day_a, session_start[sid_a], 6)
            model.AddDivisionEquality(day_b, session_start[sid_b], 6)
            model.AddModuloEquality(per_a, session_start[sid_a], 6)
            model.AddModuloEquality(per_b, session_start[sid_b], 6)

            same_day = model.NewBoolVar(f"con_same_day_{i}_{j}")
            forward = model.NewBoolVar(f"con_forward_{i}_{j}")
            backward = model.NewBoolVar(f"con_backward_{i}_{j}")
            consecutive = model.NewBoolVar(f"consecutive_{i}_{j}")

            model.Add(day_a == day_b).OnlyEnforceIf(same_day)
            model.Add(day_a != day_b).OnlyEnforceIf(same_day.Not())

            model.Add(per_a + 1 == per_b).OnlyEnforceIf(forward)
            model.Add(per_a + 1 != per_b).OnlyEnforceIf(forward.Not())

            model.Add(per_b + 1 == per_a).OnlyEnforceIf(backward)
            model.Add(per_b + 1 != per_a).OnlyEnforceIf(backward.Not())

            # consecutive = same_day AND (forward OR backward)
            model.AddImplication(consecutive, same_day)
            model.AddBoolOr([forward, backward]).OnlyEnforceIf(consecutive)

            # If same_day and either direction is true, consecutive must be true.
            model.AddBoolOr([same_day.Not(), forward.Not(), consecutive])
            model.AddBoolOr([same_day.Not(), backward.Not(), consecutive])

            consecutive_terms.append(consecutive)

    p6_penalty = sum(p6_terms)
    consecutive_penalty = sum(consecutive_terms)

    model.Maximize(
        1000 * parallel_score
        - 20 * repetition_penalty
        - 5 * p6_penalty
        - 3 * consecutive_penalty
    )

    return (
        model,
        sessions,
        session_start,
        room_assignment,
        faculty_assignment,
        faculty_lists,
        room_lists,
        SLOTS,
        ROOMS,
        practical_blocks,
    )




# ============================================================
# INDEPENDENT POST-SOLVE VALIDATION
# ============================================================

def validate_schedule_records(records, sessions, faculty_lists, room_lists):
    """Return hard errors found in the final output-shaped records."""
    errors = []
    expected_by_id = {str(s["id"]): s for s in sessions}
    records_by_id = {}

    for row_no, record in enumerate(records, start=1):
        sid = str(record.get("session_id", ""))
        if not sid:
            errors.append(f"record {row_no}: missing session_id")
            continue
        if sid in records_by_id:
            errors.append(f"{sid}: duplicate output record")
            continue
        records_by_id[sid] = record
        if sid not in expected_by_id:
            errors.append(f"{sid}: output record has no matching input session")
            continue

        session = expected_by_id[sid]
        duration = int(session.get("duration", 0))
        kind = str(session.get("type", "")).strip().lower()
        if duration not in (1, 2):
            errors.append(f"{sid}: unsupported duration {duration}")
        if kind in {"theory", "tutorial"} and duration != 1:
            errors.append(f"{sid}: {kind} must be one hour, found {duration}")
        if kind == "practical" and duration != 2:
            errors.append(f"{sid}: practical must be two hours, found {duration}")

        day = record.get("day")
        if day not in DAYS:
            errors.append(f"{sid}: invalid day {day!r}")
            continue
        try:
            period_index = next(i for i, p in enumerate(PERIODS)
                                if p[0] == record.get("period"))
        except StopIteration:
            errors.append(f"{sid}: invalid start period {record.get('period')!r}")
            continue

        if duration == 2 and period_index not in (0, 2, 4):
            errors.append(f"{sid}: two-hour block must start at P1, P3, or P5")

        expected_start = PERIODS[period_index][1]
        expected_end = PERIODS[period_index + duration - 1][2] if period_index + duration <= 6 else None
        if record.get("start") != expected_start:
            errors.append(f"{sid}: start time {record.get('start')} disagrees with {record.get('period')} ({expected_start})")
        if expected_end is None or record.get("end") != expected_end:
            errors.append(f"{sid}: end time {record.get('end')} is inconsistent with duration {duration}")

        if record.get("faculty") not in faculty_lists.get(sid, []):
            errors.append(f"{sid}: assigned faculty is not eligible")
        if record.get("room") not in room_lists.get(sid, []):
            errors.append(f"{sid}: assigned room is not eligible")
        room_info = ROOMS.get(record.get("room"), {})
        if not room_info:
            errors.append(f"{sid}: unknown room {record.get('room')!r}")
        elif int(record.get("students", 0)) > int(room_info.get("capacity", 0)):
            errors.append(f"{sid}: student count exceeds room capacity")

    missing_ids = set(expected_by_id) - set(records_by_id)
    extra_ids = set(records_by_id) - set(expected_by_id)
    if missing_ids:
        errors.append("missing output sessions: " + ", ".join(sorted(missing_ids)))
    if extra_ids:
        errors.append("unexpected output sessions: " + ", ".join(sorted(extra_ids)))

    def get_interval(record):
        day_idx = DAYS.index(record["day"])
        p_idx = next(i for i, p in enumerate(PERIODS) if p[0] == record["period"])
        session = expected_by_id[str(record["session_id"])]
        return day_idx, p_idx, p_idx + int(session["duration"])

    def resource_names(record, key):
        value = record.get(key, "")
        if key == "batch":
            if isinstance(value, (list, tuple, set)):
                return [str(x).strip() for x in value if str(x).strip()]
            return [x.strip() for x in str(value or "").split(",") if x.strip()]
        return [str(value).strip()] if str(value or "").strip() else []

    for key in ("batch", "faculty", "room"):
        occupied = {}
        for record in records:
            if record.get("day") not in DAYS or record.get("period") not in [p[0] for p in PERIODS]:
                continue
            try:
                day_idx, start, end = get_interval(record)
            except (KeyError, StopIteration, ValueError, TypeError):
                continue
            for resource in resource_names(record, key):
                group_key = (day_idx, resource)
                for old_start, old_end, old_sid in occupied.get(group_key, []):
                    if max(start, old_start) < min(end, old_end):
                        errors.append(
                            f"{key} conflict for {resource!r} on {DAYS[day_idx]}: "
                            f"{old_sid} overlaps {record.get('session_id')}"
                        )
                occupied.setdefault(group_key, []).append(
                    (start, end, str(record.get("session_id")))
                )
    return sorted(set(errors))


# ============================================================
# SOLVE
# ============================================================

def solve_timetable():
    print()
    print("=" * 60)
    print("AI TIMETABLE SOLVER MODEL")
    print("=" * 60)

    data = load_te_sem_v_data()

    try:
        result = build_model(data)

    except Exception as exc:
        print()
        print("MODEL CREATION FAILED")
        print(type(exc).__name__, ":", exc)
        print("=" * 60)
        return None

    (
        model,
        sessions,
        session_start,
        room_assignment,
        faculty_assignment,
        faculty_lists,
        room_lists,
        SLOTS,
        ROOMS,
        practical_blocks,
    ) = result

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = 60
    solver.parameters.num_search_workers = 8

    print()
    print("Solving...")
    print()

    status = solver.Solve(model)

    print()
    print(
        "SOLVER STATUS:",
        solver.StatusName(status),
    )

    if status not in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    ):
        print()
        print("NO FEASIBLE TIMETABLE FOUND.")
        print()
        print(
            "The model could not satisfy the hard "
            "student, faculty, room and time constraints."
        )
        print("=" * 60)
        return None

    # --------------------------------------------------------
    # CREATE OUTPUT RECORDS
    # --------------------------------------------------------

    records = []

    for session in sessions:
        session_id = session["id"]

        start_index = solver.Value(
            session_start[session_id]
        )

        start_info = SLOTS[start_index]

        faculty_index = solver.Value(
            faculty_assignment[session_id]
        )

        faculty_code = faculty_lists[
            session_id
        ][faculty_index]

        room_index = solver.Value(
            room_assignment[session_id]
        )

        room_code = room_lists[
            session_id
        ][room_index]

        end_slot = (
            start_index
            + session["duration"]
            - 1
        )

        end_info = SLOTS[end_slot]

        records.append(
            {
                "session_id": session_id,
                "day": start_info["day"],
                "period": start_info["period"],
                "start": start_info["start"],
                "end": end_info["end"],
                "subject": session["subject"],
                "type": session["type"],
                "duration": session["duration"],
                "batch": ", ".join(
                    session.get("batch", [])
                ),
                "elective": session.get(
                    "elective",
                    "",
                ),
                "faculty": faculty_code,
                "room": room_code,
                "students": get_group_size(
                    data,
                    session,
                ),
            }
        )

    records.sort(
        key=lambda record: (
            DAYS.index(record["day"]),
            record["start"],
            record["room"],
        )
    )

    validation_errors = validate_schedule_records(
        records, sessions, faculty_lists, room_lists
    )
    if validation_errors:
        print("\\nPOST-SOLVE VALIDATION FAILED")
        for error in validation_errors:
            print("ERROR:", error)
        print("Timetable will not be reported as successful.")
        return None
    print(f"POST-SOLVE VALIDATION: PASS ({len(records)} sessions checked)")

    # Persist this exact successful schedule so Excel generation and
    # validation do not invoke the randomized solver a second time.
    project_root = Path(__file__).resolve().parent.parent
    schedule_dir = project_root / "output" / "schedule"
    schedule_dir.mkdir(parents=True, exist_ok=True)
    schedule_path = schedule_dir / "TE_SemV_AI_Schedule.json"
    payload = {
        "schema_version": 1,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "solver_status": solver.StatusName(status),
        "session_count": len(records),
        "records": records,
    }
    temp_path = schedule_path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_path.replace(schedule_path)
    print(f"SAVED SHARED SCHEDULE: {schedule_path}")

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("GENERATED TIMETABLE")
    print("=" * 60)

    for record in records:
        print(
            f"{record['day']:10} "
            f"{record['period']:>2} "
            f"{record['start']}-{record['end']} | "
            f"{record['subject']:<38} | "
            f"{record['batch']:<10} | "
            f"{record['faculty']:<5} | "
            f"{record['room']}"
        )

    # --------------------------------------------------------
    # PRACTICAL PARALLELISM REPORT
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("PRACTICAL PARALLELISM REPORT")
    print("=" * 60)

    for block, session_ids in practical_blocks.items():

        if len(session_ids) <= 1:
            print(f"{block}: single session")
            continue

        starts = []

        for session_id in session_ids:
            starts.append(
                solver.Value(
                    session_start[session_id]
                )
            )

        unique_starts = sorted(set(starts))

        if len(unique_starts) == 1:
            print(
                f"{block}: ALL BATCHES PARALLEL "
                f"at {SLOTS[unique_starts[0]]['day']} "
                f"{SLOTS[unique_starts[0]]['period']}"
            )
        else:
            print(
                f"{block}: split across "
                f"{len(unique_starts)} time blocks "
                f"(review faculty, room, and parallelism constraints)"
            )

    print()
    print("=" * 60)
    print(
        f"Scheduled sessions: {len(records)}"
    )
    print("=" * 60)

    return (
        model,
        sessions,
        records,
        session_start,
        room_assignment,
        faculty_assignment,
        SLOTS,
        ROOMS,
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    solve_timetable()
