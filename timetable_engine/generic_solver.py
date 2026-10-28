"""Generic CP-SAT timetable solver for configured ENTC semesters 3, 4 and 6-8.

Semester V intentionally continues to use the existing solver.py implementation.
This module refuses to generate a timetable if semester resources are incomplete.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import defaultdict

from ortools.sat.python import cp_model

from data_loader_multisemester import (
    INPUT_ROOT,
    SUPPORTED_SEMESTERS,
    SCHEDULING_RULES,
    load_semester_data,
)


def _unwrap(raw, key):
    """Support either a direct mapping or the documented template wrapper."""
    if not isinstance(raw, dict):
        return {}
    wrapped = raw.get(key)
    if isinstance(wrapped, dict):
        raw = wrapped
    return {str(k): v for k, v in raw.items() if k != "_schema" and isinstance(v, dict)}


def _read_configuration(semester: int) -> dict:
    path = INPUT_ROOT / f"sem_{semester}" / "configuration.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def _normalize_batches(raw) -> dict:
    """Normalize either T1:{...} or configured:{..., batches:[...]} input."""
    if not isinstance(raw, dict):
        return {}
    if raw.get("configured") is False:
        return {}
    if isinstance(raw.get("batches"), list):
        result = {}
        for item in raw["batches"]:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code", "")).strip()
            if code:
                result[code] = {
                    **item,
                    "students": int(item.get("students", 0) or 0),
                    "elective": str(item.get("elective", "") or "").strip(),
                }
        return result
    if "batches" in raw and isinstance(raw["batches"], dict):
        raw = raw["batches"]
    result = {}
    for code, info in raw.items():
        if not isinstance(info, dict) or code in {"configured", "notes", "total_students", "number_of_batches"}:
            continue
        try:
            count = int(info.get("students", 0) or 0)
        except (TypeError, ValueError):
            count = 0
        result[str(code)] = {**info, "students": count, "elective": str(info.get("elective", "") or "").strip()}
    return result


def _faculty_candidates(session, faculty, configuration):
    subject = str(session.get("subject", "")).strip()
    session_type = str(session.get("type", "theory")).lower()
    assigned = configuration.get("faculty_assignments", {}) or {}
    override = assigned.get(session.get("id"), assigned.get(subject)) if isinstance(assigned, dict) else None
    if override:
        choices = override if isinstance(override, list) else [override]
        return [str(x).strip() for x in choices if str(x).strip() in faculty]

    field = {"theory": "theory", "tutorial": "tutorial", "practical": "practical"}.get(session_type, "theory")
    matches = []
    for code, info in faculty.items():
        subjects = info.get(field, []) or []
        if isinstance(subjects, str):
            subjects = [subjects]
        normalized = {str(x).strip().casefold() for x in subjects}
        if subject.casefold() in normalized:
            matches.append(code)
    return matches


def _room_candidates(session, rooms, group_size, configuration):
    subject = str(session.get("subject", "")).strip()
    assigned = configuration.get("room_assignments", {}) or {}
    override = assigned.get(session.get("id"), assigned.get(subject)) if isinstance(assigned, dict) else None
    choices = override if isinstance(override, list) else ([override] if override else list(rooms))
    required_type = "lab" if str(session.get("type", "")).lower() == "practical" else "classroom"
    candidates = []
    for name in choices:
        info = rooms.get(str(name))
        if not isinstance(info, dict):
            continue
        room_type = str(info.get("type", "classroom")).strip().lower()
        capacity = int(info.get("capacity", 0) or 0)
        if room_type in {required_type, "laboratory" if required_type == "lab" else required_type} and capacity >= group_size:
            candidates.append(str(name))
    return candidates


def _slots(periods_per_day=6):
    days = list(SCHEDULING_RULES.get("working_days", []))
    periods = SCHEDULING_RULES.get("periods", {})
    result = []
    for day_index, day in enumerate(days):
        for p in range(1, periods_per_day + 1):
            period = periods.get(p, periods.get(str(p), {}))
            result.append({
                "index": len(result), "day": day, "day_index": day_index,
                "period": p, "start": str(period.get("start", "")),
                "end": str(period.get("end", "")),
            })
    return result


def _valid_starts(duration, slots, periods_per_day):
    starts = []
    for slot in slots:
        p0 = slot["period"] - 1
        if duration == 1:
            starts.append(slot["index"])
        elif duration == 2 and p0 in (0, 2, 4) and p0 + duration <= periods_per_day:
            starts.append(slot["index"])
    return starts


def _effective_batches(session, batches, configuration):
    """Preserve explicit practical batches; apply mappings to theory/tutorial sessions."""
    existing = session.get("batch", []) or []
    existing = [str(x) for x in existing if str(x) in batches]

    if str(session.get("type", "")).strip().lower() == "practical":
        return existing

    mapping = configuration.get("batch_mapping", {}) or {}
    subject = str(session.get("subject", "")).strip()
    session_id = str(session.get("id", ""))
    mapped = mapping.get(session_id, mapping.get(subject)) if isinstance(mapping, dict) else None

    if mapped:
        values = mapped if isinstance(mapped, list) else [mapped]
        return [str(x) for x in values if str(x) in batches]

    return existing


def prepare_generic_data(semester: int):
    if semester not in SUPPORTED_SEMESTERS:
        raise ValueError(f"Unsupported semester {semester}. Supported: {SUPPORTED_SEMESTERS}")
    if semester == 5:
        raise ValueError("Semester V must use the existing timetable_engine/solver.py pipeline.")

    data = load_semester_data(semester)
    if data.get("mode") == "data_pending" or not data.get("subjects"):
        raise ValueError(f"Semester {semester} is DATA PENDING. Add its curriculum before scheduling.")

    configuration = _read_configuration(semester)
    faculty = _unwrap(data.get("faculty", {}), "faculty")
    rooms = _unwrap(data.get("rooms", {}), "rooms")
    batches = _normalize_batches(data.get("batches", {}))

    missing = []
    if not batches:
        missing.append("configured student batches")
    if not faculty:
        missing.append("faculty expertise/assignments")
    if not rooms:
        missing.append("room and lab resources")
    if configuration.get("configured") is not True:
        missing.append("configuration.json with configured=true")
    if missing:
        raise ValueError("Semester input incomplete: " + "; ".join(missing) + ".")

    # Generic loader's temporary ALL group is not a real student batch.
    if set(batches) == {"ALL"} or any(not int(v.get("students", 0) or 0) for v in batches.values()):
        raise ValueError("Batch configuration must contain real batches with positive student counts.")

    # Elective subjects must be selected/mapped explicitly; otherwise the
    # generic session builder would incorrectly assign one elective to every batch.
    subjects = data.get("subjects", {}) or {}
    elective_codes = [
        code for code, info in subjects.items()
        if isinstance(info, dict) and info.get("elective_options")
    ]
    elective_selections = configuration.get("elective_selections", {}) or {}
    batch_mapping = configuration.get("batch_mapping", {}) or {}
    for code in elective_codes:
        info = subjects[code]
        subject_name = str(info.get("subject", code)).strip()
        has_selection = bool(
            elective_selections.get(code)
            or elective_selections.get(subject_name)
            or batch_mapping.get(code)
            or batch_mapping.get(subject_name)
        )
        if not has_selection:
            raise ValueError(
                f"Elective '{subject_name}' has options but no selection/batch mapping. "
                "Configure elective_selections and batch_mapping first."
            )

    sessions = []
    for source in data.get("sessions", []):
        session = dict(source)
        session["batch"] = _effective_batches(session, batches, configuration)
        if not session["batch"]:
            raise ValueError(f"No student batches assigned to session '{session.get('id', '?')}'. Configure batch_mapping.")
        if int(session.get("duration", 1)) not in (1, 2):
            raise ValueError(f"Unsupported session duration for {session.get('id')}: {session.get('duration')}")
        if session.get("type") == "practical" and int(session.get("duration", 0)) != 2:
            raise ValueError(f"Practical '{session.get('id')}' must be configured as a 2-hour block.")
        sessions.append(session)

    if not sessions:
        raise ValueError(f"Semester {semester} has no schedulable sessions.")

    periods_per_day = int(SCHEDULING_RULES.get("periods_per_day", 6))
    slots = _slots(periods_per_day)
    capacity = len(slots)
    # A single batch cannot attend more than the available weekly hours.
    for batch_code in batches:
        required = sum(int(s["duration"]) for s in sessions if batch_code in s["batch"])
        if required > capacity:
            raise ValueError(
                f"Batch {batch_code} requires {required} scheduled hours, but only {capacity} weekly periods exist. "
                "Review internship/OJT, parallel electives, or the academic timetable before generating."
            )

    # Resolve viable resource candidates before creating CP-SAT variables.
    candidate_map = {}
    room_map = {}
    for s in sessions:
        size = sum(int(batches[b].get("students", 0)) for b in s["batch"])
        candidate_map[s["id"]] = _faculty_candidates(s, faculty, configuration)
        room_map[s["id"]] = _room_candidates(s, rooms, size, configuration)
        if not candidate_map[s["id"]]:
            raise ValueError(f"No eligible faculty found for '{s['subject']}' ({s['type']}). Check faculty.json/faculty_assignments.")
        if not room_map[s["id"]]:
            raise ValueError(f"No eligible room with sufficient capacity found for '{s['subject']}' ({s['type']}, {size} students). Check rooms.json/room_assignments.")
    return data, configuration, batches, faculty, rooms, sessions, slots, candidate_map, room_map


def build_generic_model(semester: int):
    (data, configuration, batches, faculty, rooms, sessions, slots,
     faculty_candidates, room_candidates) = prepare_generic_data(semester)

    model = cp_model.CpModel()
    periods_per_day = int(SCHEDULING_RULES.get("periods_per_day", 6))
    starts, ends = {}, {}
    intervals_by_batch = defaultdict(list)
    intervals_by_faculty = defaultdict(list)
    intervals_by_room = defaultdict(list)
    faculty_presence, room_presence = {}, {}
    all_valid_starts = {}

    for session in sessions:
        sid = session["id"]
        duration = int(session["duration"])
        valid = _valid_starts(duration, slots, periods_per_day)
        if not valid:
            raise ValueError(f"No valid start periods for {sid}.")
        all_valid_starts[sid] = valid
        starts[sid] = model.NewIntVarFromDomain(cp_model.Domain.FromValues(valid), f"start_{sid}")
        ends[sid] = model.NewIntVar(0, len(slots) + duration, f"end_{sid}")
        model.Add(ends[sid] == starts[sid] + duration)

        for batch in session["batch"]:
            intervals_by_batch[batch].append(
                model.NewIntervalVar(starts[sid], duration, ends[sid], f"batch_{batch}_{sid}")
            )

        # Optional intervals ensure a faculty/room is occupied only when selected.
        faculty_presence[sid] = {}
        for code in faculty_candidates[sid]:
            present = model.NewBoolVar(f"faculty_selected_{sid}_{code}")
            faculty_presence[sid][code] = present
            intervals_by_faculty[code].append(
                model.NewOptionalIntervalVar(starts[sid], duration, ends[sid], present, f"faculty_{code}_{sid}")
            )
        model.AddExactlyOne(list(faculty_presence[sid].values()))

        room_presence[sid] = {}
        for room in room_candidates[sid]:
            present = model.NewBoolVar(f"room_selected_{sid}_{room}")
            room_presence[sid][room] = present
            intervals_by_room[room].append(
                model.NewOptionalIntervalVar(starts[sid], duration, ends[sid], present, f"room_{room}_{sid}")
            )
        model.AddExactlyOne(list(room_presence[sid].values()))

    for group, intervals in intervals_by_batch.items():
        model.AddNoOverlap(intervals)
    for code, intervals in intervals_by_faculty.items():
        model.AddNoOverlap(intervals)
    for room, intervals in intervals_by_room.items():
        model.AddNoOverlap(intervals)

    # Soft preference: reduce period-6 sessions where feasible.
    late_penalties = []
    for session in sessions:
        sid = session["id"]
        is_period6 = model.NewBoolVar(f"period6_{sid}")
        period6_starts = [slot["index"] for slot in slots if slot["period"] == periods_per_day]
        # Channel the start variable to the period-6 indicator.
        period_values = [x for x in all_valid_starts[sid] if x in period6_starts]
        non_period_values = [x for x in all_valid_starts[sid] if x not in period6_starts]
        if period_values and non_period_values:
            model.AddAllowedAssignments([starts[sid], is_period6], [[x, 1] for x in period_values] + [[x, 0] for x in non_period_values])
        elif period_values:
            model.Add(is_period6 == 1)
        else:
            model.Add(is_period6 == 0)
        late_penalties.append(is_period6)
    if late_penalties:
        model.Minimize(sum(late_penalties))

    return {
        "model": model, "data": data, "configuration": configuration,
        "batches": batches, "faculty": faculty, "rooms": rooms,
        "sessions": sessions, "slots": slots, "starts": starts,
        "ends": ends, "faculty_presence": faculty_presence,
        "room_presence": room_presence,
    }


def solve_generic_timetable(semester: int, max_seconds: int = 60):
    built = build_generic_model(semester)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_seconds
    solver.parameters.num_search_workers = 8
    status = solver.Solve(built["model"])
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"No feasible timetable found for Semester {semester}. Solver status={solver.StatusName(status)}")

    slots = built["slots"]
    records = []
    for session in built["sessions"]:
        sid = session["id"]
        start_index = solver.Value(built["starts"][sid])
        slot = slots[start_index]
        faculty_code = next(code for code, var in built["faculty_presence"][sid].items() if solver.Value(var))
        room_code = next(code for code, var in built["room_presence"][sid].items() if solver.Value(var))
        duration = int(session["duration"])
        end_slot = slots[start_index + duration - 1]
        students = sum(int(built["batches"][b].get("students", 0)) for b in session["batch"])
        records.append({
            "semester": semester,
            "session_id": sid,
            "day": slot["day"],
            "period": f"P{slot['period']}",
            "period_index": slot["period"],
            "start": slot["start"],
            "end": end_slot["end"],
            "subject": session["subject"],
            "type": session["type"],
            "duration": duration,
            "batch": ", ".join(session["batch"]),
            "elective": session.get("elective", ""),
            "faculty": faculty_code,
            "room": room_code,
            "students": students,
        })
    records.sort(key=lambda row: (slots.index(next(s for s in slots if s["day"] == row["day"] and s["period"] == row["period_index"])), row["room"], row["subject"]))

    output_dir = Path(__file__).resolve().parent.parent / "output" / "generic"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"semester_{semester}_timetable.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump({
            "semester": semester,
            "label": built["data"]["semester"].get("label", f"Semester {semester}"),
            "status": solver.StatusName(status),
            "solver_seconds": solver.WallTime(),
            "session_count": len(records),
            "records": records,
        }, handle, indent=2, ensure_ascii=False)
    return records, output_path, solver.StatusName(status)


def main():
    parser = argparse.ArgumentParser(description="Generic multi-semester ENTC timetable solver")
    parser.add_argument("--semester", type=int, required=True, choices=SUPPORTED_SEMESTERS)
    parser.add_argument("--max-seconds", type=int, default=60)
    args = parser.parse_args()
    try:
        records, output_path, status = solve_generic_timetable(args.semester, args.max_seconds)
    except Exception as exc:
        parser.exit(1, f"GENERATION BLOCKED/FAILED: {exc}\n")
    print(f"Semester {args.semester}: {status}")
    print(f"Scheduled sessions: {len(records)}")
    print(f"Output: {output_path}")
    print("\n".join(f"{r['day']} {r['period']} | {r['subject']} | {r['batch']} | {r['faculty']} | {r['room']}" for r in records))


if __name__ == "__main__":
    main()
