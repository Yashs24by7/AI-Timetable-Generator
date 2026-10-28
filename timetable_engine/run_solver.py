from solver import solve_timetable

print("=" * 70)
print("AI TIMETABLE SOLVER - SEMESTER V")
print("=" * 70)

result = solve_timetable()

if result is None:
    raise SystemExit("FAILED: No timetable was generated. Check the solver output.")

if len(result) < 3 or not result[2]:
    raise SystemExit("FAILED: Solver returned no timetable records.")

records = result[2]

print("\nSUCCESS: Timetable generated.")
print(f"Scheduled sessions: {len(records)}")
print("\nTIMETABLE")
print("-" * 70)

for r in records:
    print(
        f"{r['day']:<10} {r['start']}-{r['end']} | "
        f"{r['subject']} | {r['batch']} | "
        f"Faculty: {r['faculty']} | Room: {r['room']}"
    )

print("\nSolver run completed.")
