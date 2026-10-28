"""
Semester V workload validator for the current ENTC timetable project.
Uses load_workload()'s dictionary schema and solve_timetable().
Does not modify solver.py or data_loader.py.
"""
from collections import defaultdict

from solver import solve_timetable
from data_loader import load_workload


def norm(value):
    return " ".join(str(value or "").strip().split()).casefold()


def normalize_type(value):
    text = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    if any(token in text for token in ("practical", "laboratory", "lab", "prac")):
        return "practical"
    if any(token in text for token in ("tutorial", "tut")):
        return "tutorial"
    if any(token in text for token in ("theory", "lecture", "class")):
        return "theory"
    return None


def main():
    print("\n" + "=" * 76)
    print("AI TIMETABLE WORKLOAD VALIDATOR — SEMESTER V")
    print("=" * 76)

    workload_data = load_workload()
    if not isinstance(workload_data, dict) or "records" not in workload_data:
        raise SystemExit(
            "FAIL: Unexpected load_workload() return format. "
            f"Actual type: {type(workload_data).__name__}; "
            f"keys: {list(workload_data.keys()) if isinstance(workload_data, dict) else 'not a dictionary'}"
        )

    workload_rows = workload_data["records"]
    if not isinstance(workload_rows, (list, tuple)) or not workload_rows:
        raise SystemExit("FAIL: Workload data contains no subject records.")

    required = {}
    for row in workload_rows:
        subject = str(row.get("subject", "")).strip()
        if not subject:
            continue
        key = norm(subject)
        if key in required:
            raise SystemExit(f"FAIL: Duplicate workload subject: {subject}")
        theory = int(row.get("theory_hours", 0) or 0)
        tutorial = int(row.get("tutorial_hours", 0) or 0)
        practical = int(row.get("practical_hours", 0) or 0)
        required[key] = {
            "subject": subject,
            "theory": theory,
            "tutorial": tutorial,
            "practical": practical,
            "total": theory + tutorial + practical,
        }

    if not required:
        raise SystemExit("FAIL: No usable subject rows were found in workload data.")

    print("\nGenerating timetable through solve_timetable()...")
    result = solve_timetable()
    if not isinstance(result, (tuple, list)) or len(result) < 3 or not result[2]:
        raise SystemExit(
            "\nFAIL: solve_timetable() did not return timetable records at index 2. "
            "Check the solver output above."
        )

    records = result[2]
    generated = defaultdict(lambda: {"theory": 0, "tutorial": 0, "practical": 0, "total": 0})
    unmatched_subjects = set()
    malformed_records = []
    unclassified_records = []

    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            malformed_records.append((index, repr(record)))
            continue
        subject = str(record.get("subject", record.get("Subject", ""))).strip()
        if not subject:
            malformed_records.append((index, repr(record)))
            continue
        key = norm(subject)
        if key not in required:
            unmatched_subjects.add(subject)
            continue
        kind = normalize_type(record.get("type", record.get("session_type", "")))
        try:
            duration = int(record.get("duration", 1))
        except (ValueError, TypeError):
            malformed_records.append((index, repr(record)))
            continue
        if duration <= 0:
            malformed_records.append((index, repr(record)))
            continue
        generated[key]["total"] += duration
        if kind:
            generated[key][kind] += duration
        else:
            unclassified_records.append((index, subject, record))

    print(f"\nSolver returned {len(records)} timetable records.")
    print("\nSUBJECT WORKLOAD CHECK")
    print("-" * 76)
    print(f"{'Subject':42} {'Required':>10} {'Generated':>10} {'Status':>10}")
    print("-" * 76)

    total_errors = []
    for key, req in required.items():
        gen = generated[key]
        status = "PASS" if req["total"] == gen["total"] else "CHECK"
        print(f"{req['subject'][:42]:42} {req['total']:>10} {gen['total']:>10} {status:>10}")
        if status != "PASS":
            total_errors.append((req["subject"], req["total"], gen["total"]))

    print("\nDETAILED WORKLOAD CHECK")
    print("-" * 76)
    type_errors = []
    for key, req in required.items():
        gen = generated[key]
        print(req["subject"])
        for kind in ("theory", "tutorial", "practical"):
            print(f"  {kind.title():10} Required {req[kind]} | Generated {gen[kind]}")
            if not unclassified_records and req[kind] != gen[kind]:
                type_errors.append((req["subject"], kind, req[kind], gen[kind]))
        print(f"  {'Total':10} Required {req['total']} | Generated {gen['total']}")
        print("-" * 76)

    required_hours = sum(item["total"] for item in required.values())
    generated_hours = sum(item["total"] for item in generated.values())
    print(f"\nRequired weekly hours in workload sheet: {required_hours}")
    print(f"Generated hours counted from matched records: {generated_hours}")

    if unmatched_subjects:
        print("\nSubjects present in timetable records but absent from workload:")
        for subject in sorted(unmatched_subjects):
            print(f"  - {subject}")
    if malformed_records:
        print(f"\nWARNING: {len(malformed_records)} malformed/unreadable records:")
        for index, sample in malformed_records[:5]:
            print(f"  Record #{index}: {sample}")
    if unclassified_records:
        print(f"\nNOTE: {len(unclassified_records)} record(s) had no recognizable session type.")
        for index, subject, record in unclassified_records[:5]:
            print(f"  Record #{index}, subject={subject!r}, type={record.get('type')!r}")

    print("\n" + "=" * 76)
    if total_errors or unmatched_subjects or malformed_records:
        print("WORKLOAD VALIDATION NEEDS REVIEW")
    elif unclassified_records:
        print("TOTAL WORKLOAD COUNTS CHECKED; SESSION-TYPE VALIDATION INCOMPLETE")
    elif type_errors:
        print("TOTAL HOURS MATCH, BUT THEORY/TUTORIAL/PRACTICAL BREAKDOWN NEEDS REVIEW")
    else:
        print("WORKLOAD VALIDATION PASSED")
    print("=" * 76)


if __name__ == "__main__":
    main()
