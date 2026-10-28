from pathlib import Path
import ast

path = Path.cwd() / "data_loader_multisemester.py"
source = path.read_text(encoding="utf-8")
tree = ast.parse(source)

target = next(
    (n for n in tree.body
     if isinstance(n, ast.FunctionDef)
     and n.name == "create_generic_sessions"),
    None
)
if target is None:
    raise RuntimeError("create_generic_sessions() not found")

backup = path.with_name(path.name + ".before_practical_fix")
if not backup.exists():
    backup.write_text(source, encoding="utf-8")

replacement = '''def create_generic_sessions(subjects, batches):
    """Create workload-driven sessions for generic semesters."""
    sessions = []
    batch_codes = list(batches.keys()) or ["ALL"]

    for course_code, info in subjects.items():
        subject = str(info.get("subject", course_code)).strip()
        theory_hours = int(info.get("theory_hours", 0))
        tutorial_hours = int(info.get("tutorial_hours", 0))
        practical_hours = int(info.get("practical_hours", 0))

        for i in range(theory_hours):
            sessions.append({
                "id": f"{subject}_T{i + 1}",
                "subject": subject,
                "type": "theory",
                "duration": 1,
                "group": "ALL",
                "batch": batch_codes.copy()
            })

        for i in range(tutorial_hours):
            sessions.append({
                "id": f"{subject}_TUT_{i + 1}",
                "subject": subject,
                "type": "tutorial",
                "duration": 1,
                "group": "ALL",
                "batch": batch_codes.copy()
            })

        if practical_hours % 2:
            raise ValueError(
                f"Subject '{subject}' has {practical_hours} practical hours; "
                "practical sessions must be in 2-hour blocks."
            )

        for block in range(1, practical_hours // 2 + 1):
            for batch in batch_codes:
                sessions.append({
                    "id": f"{subject}_PRACTICAL_{block}_{batch}",
                    "subject": subject,
                    "type": "practical",
                    "duration": 2,
                    "group": batch,
                    "batch": [batch]
                })

    return sessions
'''

lines = source.splitlines(keepends=True)
updated = (
    "".join(lines[:target.lineno - 1])
    + replacement + "\n\n"
    + "".join(lines[target.end_lineno:])
)

ast.parse(updated)
path.write_text(updated, encoding="utf-8")
print("Patch applied successfully.")
print("Backup:", backup)
print("Syntax check: PASS")
