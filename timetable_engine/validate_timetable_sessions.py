"""
Session-level validator for the ENTC Semester V timetable.

Compares the expected sessions produced by data_loader.py with the
records returned by solver.solve_timetable(). It does not modify either
project file and does not infer expected sessions by multiplying workload
hours across batches.
"""

from collections import Counter, defaultdict

from data_loader import load_te_sem_v_data
from solver import solve_timetable


def norm(value):
    return " ".join(str(value or "").strip().split()).casefold()


def as_dict(record):
    if isinstance(record, dict):
        return record
    if hasattr(record, "_asdict"):
        return record._asdict()
    return None


def get_id(record):
    return str(record.get("session_id", record.get("id", "")) or "").strip()


def get_duration(record):
    value = record.get("duration", 1)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def main():
    print("\n" + "=" * 78)
    print("AI TIMETABLE SESSION-LEVEL VALIDATOR — SEMESTER V")
    print("=" * 78)

    print("\nLoading expected sessions from data_loader.py...")
    data = load_te_sem_v_data()

    if not isinstance(data, dict):
        raise SystemExit(
            f"FAIL: load_te_sem_v_data() returned {type(data).__name__}, not a dictionary."
        )

    expected_raw = data.get("sessions")
    if not isinstance(expected_raw, (list, tuple)) or not expected_raw:
        raise SystemExit(
            "FAIL: data_loader.py did not provide a non-empty 'sessions' list."
        )

    expected = []
    for index, item in enumerate(expected_raw, start=1):
        row = as_dict(item)
        if row is None:
            raise SystemExit(
                f"FAIL: Expected session #{index} is not a dictionary-like record: {item!r}"
            )
        expected.append(row)

    print(f"Expected sessions from data loader: {len(expected)}")
    print("\nGenerating timetable using the existing solver...")
    result = solve_timetable()

    if not isinstance(result, (tuple, list)) or len(result) < 3:
        raise SystemExit(
            "FAIL: solve_timetable() did not return the expected tuple/list with records at index 2."
        )

    generated_raw = result[2]
    if not isinstance(generated_raw, (list, tuple)) or not generated_raw:
        raise SystemExit("FAIL: Solver returned no timetable records at result[2].")

    generated = []
    for index, item in enumerate(generated_raw, start=1):
        row = as_dict(item)
        if row is None:
            raise SystemExit(
                f"FAIL: Generated record #{index} is not dictionary-like: {item!r}"
            )
        generated.append(row)

    print(f"Generated timetable records: {len(generated)}")

    expected_ids = [get_id(row) for row in expected]
    generated_ids = [get_id(row) for row in generated]

    missing_id_expected = [i + 1 for i, sid in enumerate(expected_ids) if not sid]
    missing_id_generated = [i + 1 for i, sid in enumerate(generated_ids) if not sid]
    duplicate_expected = [sid for sid, count in Counter(expected_ids).items() if sid and count > 1]
    duplicate_generated = [sid for sid, count in Counter(generated_ids).items() if sid and count > 1]

    expected_set = {sid for sid in expected_ids if sid}
    generated_set = {sid for sid in generated_ids if sid}
    missing = sorted(expected_set - generated_set)
    unexpected = sorted(generated_set - expected_set)

    errors = []

    print("\nSESSION ID COVERAGE")
    print("-" * 78)
    print(f"{'Expected unique IDs':32}: {len(expected_set)}")
    print(f"{'Generated unique IDs':32}: {len(generated_set)}")
    print(f"{'Missing expected sessions':32}: {len(missing)}")
    print(f"{'Unexpected generated sessions':32}: {len(unexpected)}")

    if missing_id_expected:
        errors.append("Expected records with missing session IDs")
        print(f"FAIL: Expected records missing IDs at positions: {missing_id_expected}")
    if missing_id_generated:
        errors.append("Generated records with missing session IDs")
        print(f"FAIL: Generated records missing IDs at positions: {missing_id_generated}")
    if duplicate_expected:
        errors.append("Duplicate expected session IDs")
        print("FAIL: Duplicate expected IDs:", ", ".join(duplicate_expected))
    if duplicate_generated:
        errors.append("Duplicate generated session IDs")
        print("FAIL: Duplicate generated IDs:", ", ".join(duplicate_generated))
    if missing:
        errors.append("Expected sessions missing from timetable")
        print("\nMissing sessions:")
        for sid in missing:
            print("  -", sid)
    if unexpected:
        errors.append("Unexpected sessions in timetable")
        print("\nUnexpected sessions:")
        for sid in unexpected:
            print("  -", sid)

    expected_by_id = {get_id(row): row for row in expected if get_id(row)}
    generated_by_id = {get_id(row): row for row in generated if get_id(row)}

    print("\nSESSION DETAIL CHECK")
    print("-" * 78)
    detail_mismatches = []
    for sid in sorted(expected_set & generated_set):
        exp = expected_by_id[sid]
        gen = generated_by_id[sid]

        exp_subject = norm(exp.get("subject"))
        gen_subject = norm(gen.get("subject"))
        exp_duration = get_duration(exp)
        gen_duration = get_duration(gen)

        exp_batches = exp.get("batches", exp.get("batch", exp.get("group", "")))
        gen_batches = gen.get("batches", gen.get("batch", gen.get("group", "")))

        problems = []
        if exp_subject != gen_subject:
            problems.append(f"subject expected={exp.get('subject')!r}, generated={gen.get('subject')!r}")
        if exp_duration is not None and gen_duration is not None and exp_duration != gen_duration:
            problems.append(f"duration expected={exp_duration}, generated={gen_duration}")
        if exp_duration is None or gen_duration is None:
            problems.append(f"duration unreadable (expected={exp_duration}, generated={gen_duration})")

        if problems:
            detail_mismatches.append((sid, problems))

    if detail_mismatches:
        errors.append("Session detail mismatches")
        for sid, problems in detail_mismatches:
            print(f"FAIL: {sid}")
            for problem in problems:
                print("  -", problem)
    else:
        print("PASS: Subject and duration match for every session ID found in both lists.")

    print("\nSCHEDULED RECORD SUMMARY")
    print("-" * 78)
    print(f"Generated timetable records: {len(generated)}")
    print(f"Records with a day value: {sum(bool(row.get('day')) for row in generated)}")
    print(f"Records with a room value: {sum(bool(row.get('room')) for row in generated)}")
    print(f"Records with a faculty value: {sum(bool(row.get('faculty')) for row in generated)}")

    # Batch/session counts are informative: they are not added together and
    # compared directly to subject workload hours.
    by_subject = defaultdict(Counter)
    for row in generated:
        subject = str(row.get("subject", "(missing subject)"))
        by_subject[subject]["records"] += 1
        duration = get_duration(row)
        if duration is not None:
            by_subject[subject]["record_duration_sum"] += duration

    print("\nGenerated records by subject (record durations are NOT shared workload totals):")
    for subject in sorted(by_subject):
        counts = by_subject[subject]
        print(
            f"  {subject}: {counts['records']} records; "
            f"sum of record durations={counts['record_duration_sum']} hours"
        )

    print("\n" + "=" * 78)
    if errors:
        print("SESSION VALIDATION NEEDS REVIEW")
        print("Issues:", "; ".join(errors))
    else:
        print("SESSION VALIDATION PASSED")
        print("Every expected session is present exactly once, with matching subject and duration.")
    print("=" * 78)


if __name__ == "__main__":
    main()
