import json
from pathlib import Path
from data_loader import load_te_sem_v_data


# ============================================================
# TIMETABLE VALIDATOR
# ============================================================

DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
]

PERIODS = {
    "P1": ("08:45", "09:45"),
    "P2": ("09:45", "10:45"),
    "P3": ("11:00", "12:00"),
    "P4": ("12:00", "13:00"),
    "P5": ("13:45", "14:45"),
    "P6": ("14:45", "15:45"),
}

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

ROOMS = {
    **CLASSROOMS,
    **LAB_ROOMS,
}


# ============================================================
# HELPERS
# ============================================================

def slot_index(record):

    day_index = DAYS.index(
        record["day"]
    )

    period_index = (
        int(record["period"][1:]) - 1
    )

    return day_index * 6 + period_index


def overlaps(a, b):

    if a["day"] != b["day"]:
        return False

    start_a = slot_index(a) % 6
    start_b = slot_index(b) % 6

    end_a = start_a + int(a["duration"])
    end_b = start_b + int(b["duration"])

    return (
        start_a < end_b
        and start_b < end_a
    )


def get_batches(record):

    return {
        x.strip()
        for x in record["batch"].split(",")
        if x.strip()
    }


# ============================================================
# WORKLOAD CALCULATION
# ============================================================

def calculate_student_workload(records, batch):

    """
    Calculate workload for ONE student batch.

    Important:
    Batch-level practical rotations must NOT be added
    together as if T1 + T2 + T3 were the same students.

    Each batch receives its own 2-hour practical session,
    but a student in T1 only counts the T1 session.
    """

    total = 0

    for record in records:

        if batch not in get_batches(record):
            continue

        total += int(record["duration"])

    return total


def calculate_subject_workload_for_batch(
    records,
    batch,
):

    workload = {}

    for record in records:

        if batch not in get_batches(record):
            continue

        subject = record["subject"]

        workload.setdefault(
            subject,
            0
        )

        workload[subject] += int(
            record["duration"]
        )

    return workload


# ============================================================
# VALIDATION
# ============================================================

def validate_records(records, data):

    errors = []
    warnings = []

    print()
    print("=" * 70)
    print("AI TIMETABLE VALIDATION")
    print("=" * 70)

    # ========================================================
    # 1. BASIC COUNT
    # ========================================================

    print()
    print("1. BASIC SESSION CHECK")
    print("-" * 70)

    print(
        f"Generated sessions : {len(records)}"
    )

    if len(records) == 37:

        print(
            "PASS: 37 session records generated"
        )

    else:

        errors.append(
            f"Expected 37 sessions, "
            f"got {len(records)}"
        )

    # ========================================================
    # 2. PERIOD CHECK
    # ========================================================

    print()
    print("2. PERIOD CHECK")
    print("-" * 70)

    period_errors = 0

    for record in records:

        if record["period"] not in PERIODS:

            errors.append(
                f"Invalid period: "
                f"{record['session_id']}"
            )

            period_errors += 1

        if int(record["duration"]) not in (1, 2):

            errors.append(
                f"Invalid duration: "
                f"{record['session_id']}"
            )

            period_errors += 1

    if period_errors == 0:

        print(
            "PASS: All sessions use valid periods"
        )

    # ========================================================
    # 3. PRACTICAL DURATION
    # ========================================================

    print()
    print("3. PRACTICAL DURATION CHECK")
    print("-" * 70)

    practical_errors = 0

    for record in records:

        if record["type"] == "practical":

            if int(record["duration"]) != 2:

                errors.append(
                    f"Practical is not 2 hours: "
                    f"{record['session_id']}"
                )

                practical_errors += 1

    if practical_errors == 0:

        print(
            "PASS: All practical sessions are 2 hours"
        )

    # ========================================================
    # 4. ROOM CHECK
    # ========================================================

    print()
    print("4. ROOM CHECK")
    print("-" * 70)

    room_errors = 0

    for record in records:

        room = record["room"]

        if room not in ROOMS:

            errors.append(
                f"Unknown room: {room}"
            )

            room_errors += 1

            continue

        info = ROOMS[room]

        students = int(
            record["students"]
        )

        if students > info["capacity"]:

            errors.append(
                f"Capacity exceeded: "
                f"{record['session_id']} "
                f"{students}/"
                f"{info['capacity']}"
            )

            room_errors += 1

        if (
            record["type"] == "practical"
            and info["type"] != "lab"
        ):

            errors.append(
                f"Practical in non-lab room: "
                f"{record['session_id']} -> {room}"
            )

            room_errors += 1

        if (
            record["type"] != "practical"
            and info["type"] != "classroom"
        ):

            errors.append(
                f"Theory/tutorial in lab: "
                f"{record['session_id']} -> {room}"
            )

            room_errors += 1

    if room_errors == 0:

        print(
            "PASS: Room capacity and room types are valid"
        )

    # ========================================================
    # 5. STUDENT CONFLICT
    # ========================================================

    print()
    print("5. STUDENT/BATCH CONFLICT CHECK")
    print("-" * 70)

    student_conflicts = 0

    for i in range(len(records)):

        for j in range(i + 1, len(records)):

            a = records[i]
            b = records[j]

            if not overlaps(a, b):
                continue

            common = (
                get_batches(a)
                .intersection(
                    get_batches(b)
                )
            )

            if common:

                errors.append(
                    f"Student conflict: "
                    f"{a['session_id']} / "
                    f"{b['session_id']} "
                    f"{sorted(common)}"
                )

                student_conflicts += 1

    if student_conflicts == 0:

        print(
            "PASS: No student/batch conflicts"
        )

    # ========================================================
    # 6. FACULTY CONFLICT
    # ========================================================

    print()
    print("6. FACULTY CONFLICT CHECK")
    print("-" * 70)

    faculty_conflicts = 0

    for i in range(len(records)):

        for j in range(i + 1, len(records)):

            a = records[i]
            b = records[j]

            if a["faculty"] != b["faculty"]:
                continue

            if overlaps(a, b):

                errors.append(
                    f"Faculty conflict: "
                    f"{a['faculty']} -> "
                    f"{a['session_id']} / "
                    f"{b['session_id']}"
                )

                faculty_conflicts += 1

    if faculty_conflicts == 0:

        print(
            "PASS: No faculty conflicts"
        )

    # ========================================================
    # 7. ROOM CONFLICT
    # ========================================================

    print()
    print("7. ROOM CONFLICT CHECK")
    print("-" * 70)

    room_conflicts = 0

    for i in range(len(records)):

        for j in range(i + 1, len(records)):

            a = records[i]
            b = records[j]

            if a["room"] != b["room"]:
                continue

            if overlaps(a, b):

                errors.append(
                    f"Room conflict: "
                    f"{a['room']} -> "
                    f"{a['session_id']} / "
                    f"{b['session_id']}"
                )

                room_conflicts += 1

    if room_conflicts == 0:

        print(
            "PASS: No room conflicts"
        )

    # ========================================================
    # 8. STUDENT WORKLOAD
    # ========================================================

    print()
    print("8. STUDENT WORKLOAD CHECK")
    print("-" * 70)

    expected_total = 28

    for batch in ["T1", "T2", "T3"]:

        total = calculate_student_workload(
            records,
            batch,
        )

        print(
            f"{batch} workload : "
            f"{total} hours/week"
        )

        if total == expected_total:

            print(
                f"PASS: {batch} = "
                f"{expected_total} hours"
            )

        else:

            errors.append(
                f"{batch} workload is "
                f"{total}, expected "
                f"{expected_total}"
            )

    # ========================================================
    # 9. SUBJECT WORKLOAD PER BATCH
    # ========================================================

    print()
    print("9. SUBJECT WORKLOAD CHECK")
    print("-" * 70)

    expected = {
        "Microcontrollers & Applications": 3,
        "Cellular Network": 3,
        "VLSI Design": 3,
        "Microcontrollers & VLSI Design Lab": 4,
        "Cellular Network Lab": 2,
        "Programme Elective Lab": 2,
        "Machine Learning": 4,
        "Open Elective": 2,
        "Technical Seminar": 2,
    }

    for batch in ["T1", "T2", "T3"]:

        print()
        print(
            f"Batch {batch}"
        )

        print("-" * 50)

        workload = (
            calculate_subject_workload_for_batch(
                records,
                batch,
            )
        )

        for subject, required in expected.items():

            actual = workload.get(
                subject,
                0
            )

            if actual == required:

                print(
                    f"PASS: "
                    f"{subject:<38} "
                    f"{actual}/{required} h"
                )

            else:

                errors.append(
                    f"{batch}: "
                    f"{subject} "
                    f"{actual}/{required}"
                )

        # ----------------------------------------------------
        # Programme Elective
        # ----------------------------------------------------

        pe_hours = 0

        for record in records:

            if (
                record["subject"]
                == "Programme Elective I"
                and batch in get_batches(record)
            ):

                pe_hours += int(
                    record["duration"]
                )

        if pe_hours == 3:

            print(
                "PASS: Programme Elective I"
                f"{'':10} "
                f"{pe_hours}/3 h"
            )

        else:

            errors.append(
                f"{batch}: Programme Elective I "
                f"{pe_hours}/3"
            )

    # ========================================================
    # 10. PRACTICAL BATCH COVERAGE
    # ========================================================

    print()
    print("10. PRACTICAL BATCH COVERAGE")
    print("-" * 70)

    practical_subjects = [
        "Microcontrollers & VLSI Design Lab",
        "Cellular Network Lab",
        "Programme Elective Lab",
        "Machine Learning",
        "Technical Seminar",
    ]

    for subject in practical_subjects:

        batches = set()

        for record in records:

            if (
                record["subject"] == subject
                and record["type"] == "practical"
            ):

                batches.update(
                    get_batches(record)
                )

        expected_batches = {
            "T1",
            "T2",
            "T3",
        }

        if batches == expected_batches:

            print(
                f"PASS: {subject:<38}"
                "T1 + T2 + T3"
            )

        else:

            errors.append(
                f"Practical batch coverage error: "
                f"{subject} -> "
                f"{sorted(batches)}"
            )

    # ========================================================
    # 11. PRACTICAL PARALLELISM INFORMATION
    # ========================================================

    print()
    print("11. PRACTICAL PARALLELISM")
    print("-" * 70)

    practical_groups = {}

    for record in records:

        if record["type"] != "practical":
            continue

        subject = record["subject"]

        practical_groups.setdefault(
            subject,
            []
        ).append(record)

    for subject, group in practical_groups.items():

        start_times = sorted(
            set(
                (
                    record["day"],
                    record["period"]
                )
                for record in group
            )
        )

        if len(start_times) == 1:

            print(
                f"PASS: {subject:<38}"
                "T1/T2/T3 parallel"
            )

        else:

            print(
                f"INFO: {subject:<38}"
                f"split into {len(start_times)} blocks"
            )

            warnings.append(
                f"{subject} practical is split "
                f"because of available resources"
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    if errors:

        print(
            f"FAIL: {len(errors)} error(s)"
        )

        print()

        for error in errors:

            print(
                f"  ERROR: {error}"
            )

    else:

        print(
            "PASS: No hard validation errors found."
        )

    if warnings:

        print()

        for warning in warnings:

            print(
                f"  WARNING: {warning}"
            )

    print("=" * 70)

    return errors, warnings


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    project_root = Path(__file__).resolve().parent.parent
    schedule_path = project_root / "output" / "schedule" / "TE_SemV_AI_Schedule.json"

    if not schedule_path.exists():
        print("Validation stopped: saved schedule not found.")
        print("Run solver.py successfully first, then run validator.py.")
    else:
        try:
            payload = json.loads(schedule_path.read_text(encoding="utf-8"))
            records = payload["records"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            print(f"Validation stopped: could not read saved schedule: {exc}")
        else:
            print(f"Validating saved schedule: {schedule_path}")
            print(f"Schedule created: {payload.get('created_at', 'unknown')}")
            data = load_te_sem_v_data()
            validate_records(records, data)
