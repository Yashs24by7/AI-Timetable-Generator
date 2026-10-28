from data_loader import (
    load_te_workload,
    create_sessions,
    enrich_sessions
)


print("PRACTICAL SESSION TEST")
print("=" * 60)

workload = load_te_workload()

sessions = create_sessions(workload)

sessions = enrich_sessions(sessions)


print()

for session in sessions:

    if session["type"] != "PRACTICAL":
        continue

    print(
        f"Session {session['session_id']}: "
        f"{session['subject']}"
    )

    print(
        f"Duration: "
        f"{session['duration']} hours"
    )

    print(
        "Batch allocation:"
    )

    print(
        "  T1 → 32 students → Lab capacity required: 48"
    )

    print(
        "  T2 → 31 students → Lab capacity required: 48"
    )

    print(
        "  T3 → 17 students → Lab capacity required: 48"
    )

    print("-" * 60)