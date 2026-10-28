from flask import Flask, render_template, request, redirect, url_for, flash, Response
import sys
import html

from werkzeug.utils import secure_filename



from pathlib import Path

from datetime import datetime

import json

import uuid





# ============================================================

# APP CONFIGURATION

# ============================================================



app = Flask(__name__)



app.secret_key = "ai-timetable-project-secret-key"



BASE_DIR = Path(__file__).resolve().parent



SUBMISSIONS_DIR = BASE_DIR / "submissions"

SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)



ALLOWED_EXTENSIONS = {

          "pdf",

          "png",

          "jpg",

          "jpeg",

          "xlsx",

          "xls",

          "csv",

          "doc",

          "docx",

}





# ============================================================

# HELPERS

# ============================================================



def allowed_file(filename):

          return (

                    "." in filename

                    and filename.rsplit(".", 1)[1].lower()

                    in ALLOWED_EXTENSIONS

          )





def split_subjects(value):

          """

          Converts comma/newline/semicolon separated subjects

          into a clean list.

          """



          if not value:

                    return []



          value = value.replace(";", ",")

          value = value.replace("\n", ",")



          subjects = []



          for item in value.split(","):

                    item = item.strip()



                    if item:

                              subjects.append(item)



          return subjects





def save_uploaded_files(files, upload_dir):

          """

          Saves uploaded supporting documents.

          """



          saved_files = []



          upload_dir.mkdir(parents=True, exist_ok=True)



          for file in files:



                    if not file or not file.filename:

                              continue



                    filename = secure_filename(file.filename)



                    if not filename:

                              continue



                    if not allowed_file(filename):

                              continue



                    unique_name = (

                              f"{uuid.uuid4().hex[:8]}_{filename}"

                    )



                    destination = upload_dir / unique_name



                    file.save(destination)



                    saved_files.append({

                              "original_name": filename,

                              "saved_name": unique_name,

                    })



          return saved_files





def get_list_values(field_name):

          """

          Safely reads repeated HTML fields such as:

          faculty_code[]

          """



          return request.form.getlist(field_name)





# ============================================================

# HOME PAGE

# ============================================================



@app.route("/", methods=["GET"])

def index():

          """Render the semester-selection dashboard."""

          return render_template("dashboard.html")





@app.route("/data-form", methods=["GET"])

def data_form():

          """Keep the existing data-collection form available."""

          return render_template("index.html")





# ============================================================

# FORM SUBMISSION

# ============================================================




# ============================================================
# SEMESTER CONFIGURATION MANAGEMENT
# ============================================================

DATA_INPUT_DIR = BASE_DIR.parent / "data" / "input"
CONFIGURABLE_SEMESTERS = {3, 4, 5, 6}
CONFIG_FILES = {
    "batches": "batches.json",
    "faculty": "faculty.json",
    "rooms": "rooms.json",
    "configuration": "configuration.json",
}


def semester_data_dir(semester):
    return DATA_INPUT_DIR / f"sem_{semester}"


def read_json_file(path, default=None):
    if not path.exists():
        return {} if default is None else default
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {} if default is None else default


def semester_readiness(semester):
    folder = semester_data_dir(semester)
    batches = read_json_file(folder / "batches.json", {})
    faculty = read_json_file(folder / "faculty.json", {})
    rooms = read_json_file(folder / "rooms.json", {})
    config = read_json_file(folder / "configuration.json", {})
    subjects_path = folder / "subjects.json"
    subjects_exists = subjects_path.is_file()
    subjects = read_json_file(subjects_path, {}) if subjects_exists else {}

    missing = []

    # Validate batch records without assuming an unconfirmed structure.
    batch_list = batches.get("batches", []) if isinstance(batches, dict) else batches
    valid_batches = (
        isinstance(batch_list, list)
        and len(batch_list) > 0
        and all(
            isinstance(batch, dict)
            and str(batch.get("code", "")).strip()
            and isinstance(batch.get("students"), int)
            and not isinstance(batch.get("students"), bool)
            and batch["students"] > 0
            for batch in batch_list
        )
    )

    if not valid_batches:
        missing.append("student batches and student counts")

    if not isinstance(batches, dict) or batches.get("configured") is not True:
        missing.append("student batch structure confirmed for this semester")

    faculty_records = (
        faculty.get("faculty", faculty)
        if isinstance(faculty, dict)
        else {}
    )
    if not isinstance(faculty_records, dict) or not faculty_records:
        missing.append("faculty records")

    if not isinstance(config, dict):
        config = {}

    if config.get("faculty_expertise_verified") is not True:
        missing.append("faculty subject expertise verified for this semester")

    # Check included subjects with workload against saved faculty assignments.
    if subjects_exists and isinstance(subjects, dict):
        if isinstance(subjects.get("subjects"), dict):
            subjects = subjects["subjects"]

        assignments = config.get("faculty_assignments", {})
        if not isinstance(assignments, dict):
            assignments = {}

        unassigned = []
        if isinstance(subjects, dict):
            for code, info in subjects.items():
                if not isinstance(info, dict) or info.get("included", True) is False:
                    continue

                try:
                    has_workload = any(
                        int(info.get(field, 0) or 0) > 0
                        for field in (
                            "theory_hours",
                            "tutorial_hours",
                            "practical_hours",
                        )
                    )
                except (TypeError, ValueError):
                    has_workload = False

                if not has_workload:
                    continue

                name = str(info.get("subject", code)).strip()
                assigned = assignments.get(name, assignments.get(str(code), []))
                if isinstance(assigned, str):
                    assigned = [assigned]

                if not isinstance(assigned, list) or not any(
                    str(item).strip() for item in assigned
                ):
                    unassigned.append(name)

        if unassigned:
            missing.append(
                "faculty assignments missing for: " + ", ".join(unassigned)
            )

    if config.get("faculty_assignments_verified") is not True:
        missing.append("subject-to-faculty assignments verified for this semester")

    room_records = (
        rooms.get("rooms", rooms)
        if isinstance(rooms, dict)
        else {}
    )
    valid_rooms = (
        isinstance(room_records, dict)
        and bool(room_records)
        and all(
            isinstance(room, dict)
            and str(room.get("code", code)).strip()
            and isinstance(room.get("capacity"), int)
            and not isinstance(room.get("capacity"), bool)
            and room["capacity"] > 0
            for code, room in room_records.items()
        )
    )

    if not valid_rooms:
        missing.append("room and lab inventory")

    if config.get("rooms_verified") is not True:
        missing.append("room availability and suitability verified for this semester")

    if config.get("configured") is not True:
        missing.append("configuration marked complete")

    if not subjects_exists or not isinstance(subjects, dict) or not subjects:
        missing.append("curriculum/subjects file")

    return {
        "ready": not missing,
        "missing": missing,
        "subjects_exists": subjects_exists,
    }

@app.route("/semester/<int:semester>/configure", methods=["GET", "POST"])
def configure_semester(semester):
    """Edit semester-specific JSON inputs without touching Semester V or shared files."""
    if semester not in CONFIGURABLE_SEMESTERS:
        return Response("<h2>This semester is not available in the configuration editor.</h2><p><a href='/'>Back to dashboard</a></p>", status=404, mimetype="text/html")
    folder = semester_data_dir(semester)
    folder.mkdir(parents=True, exist_ok=True)
    errors = []
    saved = False
    if request.method == "POST":
        parsed = {}
        for key, filename in CONFIG_FILES.items():
            raw = request.form.get(key, "").strip()
            try:
                value = json.loads(raw) if raw else {}
                if not isinstance(value, (dict, list)):
                    raise ValueError("Top-level JSON must be an object or array.")
                parsed[key] = value
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append(f"{filename}: {exc}")

        # Validate subjects before writing any files.
        raw_subjects = request.form.get("subjects", "").strip()
        subject_value = None
        if raw_subjects:
            try:
                subject_value = json.loads(raw_subjects)
                if not isinstance(subject_value, dict):
                    raise ValueError("subjects.json must contain a JSON object.")
                for code, info in subject_value.items():
                    if not str(code).strip() or not isinstance(info, dict):
                        raise ValueError("Each subject needs a non-empty code and an object.")
                    if not str(info.get("subject", "")).strip():
                        raise ValueError(f"{code}: subject name cannot be empty.")
                    for field in ("theory_hours", "tutorial_hours", "practical_hours"):
                        hours = info.get(field, 0)
                        if isinstance(hours, bool) or not isinstance(hours, int) or hours < 0:
                            raise ValueError(f"{code}: {field} must be a non-negative whole number.")
            except (json.JSONDecodeError, ValueError) as exc:
                errors.append(f"subjects.json: {exc}")

        if not errors:
            documents_to_save = dict(parsed)
            if subject_value is not None:
                documents_to_save["subjects"] = subject_value

            # Write validated documents using temporary files.
            for key, value in documents_to_save.items():
                filename = "subjects.json" if key == "subjects" else CONFIG_FILES[key]
                target = folder / filename
                temp = target.with_suffix(target.suffix + ".tmp")
                with temp.open("w", encoding="utf-8") as handle:
                    json.dump(value, handle, indent=4, ensure_ascii=False)
                    handle.write("\n")
                temp.replace(target)
            saved = True

    # Preload shared faculty/room inventories for convenience when the semester files are empty.
    # They remain provisional until the user confirms semester-specific expertise and availability.
    documents_data = {key: read_json_file(folder / filename, {}) for key, filename in CONFIG_FILES.items()}
    shared_faculty = read_json_file(DATA_INPUT_DIR / "faculty.json", {})
    shared_rooms = read_json_file(DATA_INPUT_DIR / "rooms.json", {})
    if not documents_data.get("faculty") and isinstance(shared_faculty, dict) and shared_faculty:
        documents_data["faculty"] = shared_faculty
    if not documents_data.get("rooms") and isinstance(shared_rooms, dict) and shared_rooms:
        documents_data["rooms"] = shared_rooms
    documents = {key: json.dumps(documents_data.get(key, {}), indent=4, ensure_ascii=False) for key in CONFIG_FILES}
    subject_data = read_json_file(folder / "subjects.json", {})
    if isinstance(subject_data, dict) and isinstance(subject_data.get("subjects"), dict):
        subject_data = subject_data["subjects"]
    documents["subjects"] = json.dumps(subject_data if isinstance(subject_data, dict) else {}, indent=4, ensure_ascii=False)
    readiness = semester_readiness(semester)
    return render_template("semester_config.html", semester=semester, documents=documents,
                           errors=errors, saved=saved, readiness=readiness)

@app.route("/semester/<int:semester>/assignments", methods=["GET", "POST"])
def semester_faculty_assignments(semester):
    """Manage subject-level faculty assignments consumed by the generic solver."""
    if semester not in CONFIGURABLE_SEMESTERS:
        return Response("<h2>Semester not supported.</h2><p><a href='/'>Back to dashboard</a></p>", status=404, mimetype="text/html")

    folder = semester_data_dir(semester)
    subjects_doc = read_json_file(folder / "subjects.json", {})
    if isinstance(subjects_doc, dict) and isinstance(subjects_doc.get("subjects"), dict):
        subjects_doc = subjects_doc["subjects"]
    subjects = subjects_doc if isinstance(subjects_doc, dict) else {}

    faculty_doc = read_json_file(folder / "faculty.json", {})
    shared_faculty_doc = read_json_file(DATA_INPUT_DIR / "faculty.json", {})

    faculty_records = (
        faculty_doc.get("faculty", faculty_doc)
        if isinstance(faculty_doc, dict) else {}
    )
    shared_faculty_records = (
        shared_faculty_doc.get("faculty", shared_faculty_doc)
        if isinstance(shared_faculty_doc, dict) else {}
    )

    if not isinstance(faculty_records, dict):
        faculty_records = {}
    if not isinstance(shared_faculty_records, dict):
        shared_faculty_records = {}

    # Merge shared faculty into the semester pool without overwriting
    # semester-specific records. Newly added semester faculty appear in
    # the assignment dropdown after saving the Configuration Editor.
    faculty_records = {**shared_faculty_records, **faculty_records}

    # Semester V's legacy timetable data stores faculty in web_form/submissions/*/submission.json.
    # Use the latest submission as the selectable faculty pool only when JSON pools are empty.
    if not faculty_records:
        submission_files = list((BASE_DIR / "submissions").glob("*/submission.json"))
        if submission_files:
            latest_submission = max(submission_files, key=lambda item: item.stat().st_mtime)
            submission_doc = read_json_file(latest_submission, {})
            submitted_faculty = submission_doc.get("faculty", []) if isinstance(submission_doc, dict) else []
            if isinstance(submitted_faculty, list):
                faculty_records = {
                    str(item.get("code", "")).strip(): item
                    for item in submitted_faculty
                    if isinstance(item, dict) and str(item.get("code", "")).strip()
                }

    faculty = [{"code": str(code), "name": str(info.get("name", code))}
               for code, info in faculty_records.items()
               if isinstance(info, dict) and (info.get("name") or code)]

    config_path = folder / "configuration.json"
    config = read_json_file(config_path, {})
    if not isinstance(config, dict):
        config = {}
    assignments = config.get("faculty_assignments", {})
    if not isinstance(assignments, dict):
        assignments = {}
    errors, saved = [], False
    verified = config.get("faculty_assignments_verified") is True

    if request.method == "POST":
        submitted = {}
        valid_codes = {item["code"] for item in faculty}
        for key, info in subjects.items():
            if not isinstance(info, dict):
                continue
            name = str(info.get("subject", key))

            # Semester V's programme elective has two independent elective cohorts.
            if semester == 5 and name == "Programme Elective I":
                for suffix, elective_name in (
                    ("CC", "Cloud Computing"),
                    ("AJP", "Advanced Java Programming"),
                ):
                    chosen = request.form.get(f"faculty_{key}-{suffix}", "").strip()
                    if chosen:
                        if chosen not in valid_codes:
                            errors.append(f"{elective_name}: selected faculty code is not present in the faculty pool.")
                        else:
                            submitted[elective_name] = [chosen]
                continue

            chosen = request.form.get(f"faculty_{key}", "").strip()
            if chosen:
                if chosen not in valid_codes:
                    errors.append(f"{name}: selected faculty code is not present in the faculty pool.")
                else:
                    submitted[name] = [chosen]
        mark_verified = request.form.get("assignments_verified") == "on"
        schedulable = []
        for key, info in subjects.items():
            if not isinstance(info, dict):
                continue
            name = str(info.get("subject", key))
            if not any(int(info.get(field, 0) or 0) > 0
                       for field in ("theory_hours", "tutorial_hours", "practical_hours")):
                continue
            if semester == 5 and name == "Programme Elective I":
                schedulable.extend(["Cloud Computing", "Advanced Java Programming"])
            else:
                schedulable.append(name)
        if mark_verified:
            missing_subjects = [name for name in schedulable if name not in submitted]
            if missing_subjects:
                errors.append("Cannot verify yet. Assign a faculty member to every subject with scheduled workload: " + ", ".join(missing_subjects))
        if not errors:
            config["faculty_assignments"] = submitted
            config["faculty_assignments_verified"] = mark_verified
            config_path.parent.mkdir(parents=True, exist_ok=True)
            temp = config_path.with_suffix(".json.tmp")
            with temp.open("w", encoding="utf-8") as handle:
                json.dump(config, handle, indent=4, ensure_ascii=False)
                handle.write("\n")
            temp.replace(config_path)
            assignments, verified, saved = submitted, mark_verified, True

    rows = []
    for key, info in subjects.items():
        if not isinstance(info, dict):
            continue
        name = str(info.get("subject", key))
        workload = f"Theory {info.get('theory_hours', 0)}h Ã‚Â· Tutorial {info.get('tutorial_hours', 0)}h Ã‚Â· Practical {info.get('practical_hours', 0)}h"

        if semester == 5 and name == "Programme Elective I":
            for suffix, elective_name in (
                ("CC", "Cloud Computing"),
                ("AJP", "Advanced Java Programming"),
            ):
                current = assignments.get(elective_name, [])
                if isinstance(current, str):
                    current = [current]
                rows.append({
                    "code": f"{key}-{suffix}",
                    "name": elective_name,
                    "workload": "Theory 3h Ã‚Â· Elective cohort",
                    "current_code": str(current[0]) if current else "",
                })
            continue

        current = assignments.get(name, [])
        if isinstance(current, str):
            current = [current]
        rows.append({"code": str(key), "name": name, "workload": workload,
                     "current_code": str(current[0]) if current else ""})

    return render_template("faculty_assignments.html", semester=semester, rows=rows,
                           faculty=faculty, errors=errors, saved=saved, verified=verified)


@app.route("/semester/<int:semester>/readiness", methods=["GET"])
def semester_readiness_page(semester):
    if semester == 5:
        return redirect(url_for("index"))
    if semester not in CONFIGURABLE_SEMESTERS:
        return Response("<h2>Semester not supported in this readiness view.</h2><p><a href='/'>Back to dashboard</a></p>", status=404, mimetype="text/html")

    state = semester_readiness(semester)
    missing = set(state["missing"])
    checks = [
        ("Student batches and counts", "student batches and student counts", "batchesPanel", "Configure real batch codes and positive student counts."),
        ("Batch structure confirmation", "student batch structure confirmed for this semester", "batchesPanel", "Confirm the batch structure only after it is known."),
        ("Faculty records", "faculty records", "facultyPanel", "Review the faculty pool and add or edit records if needed."),
        ("Faculty subject expertise", "faculty subject expertise verified for this semester", "facultyPanel", "Verify which faculty can teach each subject in this semester."),
        ("Subject-to-faculty assignments", "subject-to-faculty assignments verified for this semester", "assignments", "Assign each curriculum subject to an eligible faculty member."),
        ("Room and lab inventory", "room and lab inventory", "roomsPanel", "Review room codes, types and capacities."),
        ("Room availability and suitability", "room availability and suitability verified for this semester", "roomsPanel", "Confirm actual semester availability and suitability."),
        ("Configuration completion", "configuration marked complete", "readinessPanel", "Mark complete only after all required data has been reviewed."),
        ("Curriculum file", "curriculum/subjects file", "readinessPanel", "Add or verify the official semester subject workload file."),
    ]
    cards = []
    for title, key, anchor, detail in checks:
        is_missing = key in missing
        status_label = "Pending" if is_missing else "Present"
        css = "pending" if is_missing else "complete"
        target = f"/semester/{semester}/assignments" if anchor == "assignments" else f"/semester/{semester}/configure#{anchor}"
        cards.append(
            f'<article class="check {css}"><div class="checktop"><h2>{html.escape(title)}</h2>'
            f'<span class="pill">{status_label}</span></div><p>{html.escape(detail)}</p>'
            f'<a href="{target}">Open relevant section Ã¢â€ â€™</a></article>'
        )
    pending_count = len(missing)
    headline = "Configuration incomplete" if pending_count else "Initial checks passed"
    summary = (f"{pending_count} requirement(s) still need attention. Timetable generation remains blocked until required data is configured and verified." if pending_count else "All configured readiness checks are present. Run the solver and full timetable validator before using any generated timetable.")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Semester {semester} readiness</title>
<style>
:root{{font-family:Inter,\"Segoe UI\",Arial,sans-serif;color:#172033;background:#f3f6fb}}*{{box-sizing:border-box}}body{{margin:0}}.top{{background:#172554;color:white;padding:26px 18px}}.wrap{{max-width:1050px;margin:auto;padding:24px 16px}}h1{{margin:0 0 8px;font-size:clamp(24px,4vw,32px)}}.top p{{margin:0;color:#dbeafe}}.actions{{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}}.btn{{display:inline-block;padding:10px 14px;border-radius:8px;text-decoration:none;background:#1d4ed8;color:#fff;font-weight:650}}.secondary{{background:#fff;color:#1e3a8a;border:1px solid #cbd5e1}}.summary{{background:#fff;border:1px solid #dbe3ef;border-left:5px solid {'#16a34a' if not pending_count else '#d97706'};border-radius:12px;padding:18px;margin:16px 0}}.summary strong{{display:block;font-size:18px;margin-bottom:6px}}.summary p{{margin:0;line-height:1.5;color:#475569}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}}.check{{background:#fff;border:1px solid #dbe3ef;border-radius:12px;padding:16px;min-width:0}}.check.pending{{border-top:4px solid #d97706}}.check.complete{{border-top:4px solid #16a34a}}.checktop{{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}}.check h2{{font-size:16px;margin:0}}.pill{{font-size:12px;border-radius:99px;padding:4px 8px;font-weight:700;white-space:nowrap;background:#fff7ed;color:#9a3412}}.complete .pill{{background:#dcfce7;color:#166534}}.check p{{font-size:13px;line-height:1.5;color:#64748b;min-height:40px}}.check a{{color:#1d4ed8;font-weight:650;text-decoration:none;font-size:13px}}.note{{margin-top:18px;color:#64748b;font-size:12px;line-height:1.5}}@media(max-width:600px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body><header class="top"><div class="wrap"><h1>Semester {semester} Ã¢â‚¬â€ Readiness</h1><p>ENTC AI-Based Timetable Generation System Ã‚Â· Check missing information before generation</p></div></header><main class="wrap"><div class="actions"><a class="btn secondary" href="/semester/{semester}/configure">Ã¢â€ Â Configuration editor</a><a class="btn secondary" href="/">Dashboard</a></div><section class="summary"><strong>{html.escape(headline)}</strong><p>{html.escape(summary)}</p></section><section class="grid">{''.join(cards)}</section><p class="note">A Ã¢â‚¬Å“PresentÃ¢â‚¬Â status means the current readiness check found the required field or file. It does not independently prove that faculty assignments, room availability or timetable feasibility are correct. Keep unknown information unverified.</p></main></body></html>"""
    return Response(page, mimetype="text/html")


# ============================================================
# TIMETABLE GENERATION
# ============================================================


@app.route("/semester/5/saved", methods=["GET"])
def view_saved_semester_v():
    """Display the existing Semester V JSON without running the solver."""
    schedule_path = (
        BASE_DIR.parent / "output" / "schedule" / "TE_SemV_AI_Schedule.json"
    )

    if not schedule_path.is_file():
        return Response(
            "<h2>Saved Semester V timetable not found.</h2>"
            "<p><a href='/'>Back to dashboard</a></p>",
            status=404,
            mimetype="text/html",
        )

    try:
        payload = json.loads(schedule_path.read_text(encoding="utf-8"))
        records = payload.get("records", [])
        if not isinstance(records, list):
            raise ValueError("The records field is not a list.")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return Response(
            "<h2>Could not read the saved timetable.</h2><pre>"
            + html.escape(str(exc))
            + "</pre><p><a href='/'>Back to dashboard</a></p>",
            status=500,
            mimetype="text/html",
        )

    columns = [
        ("day", "Day"), ("period", "Period"), ("start", "Start"),
        ("end", "End"), ("duration", "Duration"), ("batch", "Batch"),
        ("subject", "Subject"), ("type", "Type"),
        ("faculty", "Faculty"), ("room", "Room"),
    ]

    header = "".join(
        "<th>" + html.escape(label) + "</th>"
        for _, label in columns
    )

    rows = []
    for record in sorted(
        records,
        key=lambda item: (
            str(item.get("day", "")),
            str(item.get("period", "")),
            str(item.get("batch", "")),
        ),
    ):
        cells = "".join(
            "<td>" + html.escape(str(record.get(key, ""))) + "</td>"
            for key, _ in columns
        )
        rows.append("<tr>" + cells + "</tr>")

    page = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Saved Semester V Timetable</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#eef2f7;color:#1c2b3d;font-family:"Segoe UI",Arial,sans-serif}
header{background:#17365d;color:white;padding:24px 32px}
header h1{margin:0 0 8px;font-size:26px}
header p{margin:0;font-size:14px}
main{width:100%;max-width:1800px;margin:22px auto;padding:0 24px 32px}
.toolbar{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap}
.actions{display:flex;gap:8px;flex-wrap:wrap}
.btn{display:inline-block;padding:10px 15px;border:1px solid #b9c8d9;border-radius:6px;background:white;color:#17365d;text-decoration:none;cursor:pointer;font-size:14px}
.btn.primary{background:#17365d;color:white}
.table-wrap{width:100%;overflow-x:auto;background:white;border:1px solid #cbd6e2;border-radius:8px;margin-top:16px}
table{border-collapse:collapse;width:100%;min-width:1200px;font-size:13px}
th{background:#17365d;color:white;text-align:left}
th,td{padding:11px 10px;border-bottom:1px solid #d9e1ea;vertical-align:top}
tbody tr:nth-child(even){background:#f5f8fc}
.note{color:#5f6f82;font-size:13px}
@media(max-width:800px){header{padding:18px}main{padding:0 12px 20px}}
@media print{
@page{size:landscape;margin:8mm}
body{background:white}
header{background:white;color:#17365d;padding:8px 0;border-bottom:2px solid #17365d}
main{max-width:none;margin:8px 0;padding:0}
.no-print{display:none!important}
.table-wrap{overflow:visible;border:0}
table{min-width:0;width:100%;font-size:8px;table-layout:auto}
th,td{padding:4px;overflow-wrap:anywhere}
th{position:static;background:#17365d!important;color:white!important;print-color-adjust:exact;-webkit-print-color-adjust:exact}
tr{break-inside:avoid}
}
</style>
</head>
<body>
<header><h1>ENTC — Semester V Saved Timetable</h1>
<p>Existing saved schedule · Read-only view</p></header>
<main>
<div class="toolbar no-print">
<p class="note">Sessions: __COUNT__ · Solver status: __STATUS__</p>
<div class="actions">
<a class="btn" href="/">Back to Dashboard</a>
<button class="btn primary" onclick="window.print()">Print / Save PDF</button>
</div>
</div>
<div class="table-wrap"><table><thead><tr>__HEADERS__</tr></thead>
<tbody>__ROWS__</tbody></table></div>
<p class="note">Saved at: __CREATED__</p>
</main></body></html>"""

    page = (
        page.replace("__COUNT__", str(len(records)))
        .replace("__STATUS__", html.escape(str(payload.get("solver_status", "Unknown"))))
        .replace("__CREATED__", html.escape(str(payload.get("created_at", "Unknown"))))
        .replace("__HEADERS__", header)
        .replace("__ROWS__", "".join(rows))
    )
    return Response(page, mimetype="text/html")

@app.route("/generate/<int:semester>", methods=["GET", "POST"])
def generate_timetable(semester):
    """Generate a timetable using the appropriate semester solver."""
    
    if semester in (3, 4, 6):
        state = semester_readiness(semester)

        # Block generation until all readiness requirements are satisfied.
        if not state["ready"]:
            missing_items = "".join(
                f"<li>{html.escape(item)}</li>"
                for item in state["missing"]
            )
            page = (
                f"<h2>Semester {semester} configuration is incomplete</h2>"
                "<p>Timetable generation is blocked until required "
                "information is confirmed.</p>"
                f"<ul>{missing_items}</ul>"
                f"<p><a href='/semester/{semester}/readiness'>"
                "View readiness report</a></p>"
                "<p><a href='/'>Back to dashboard</a></p>"
            )
            return Response(
                page,
                status=400,
                mimetype="text/html",
            )

        engine_dir = BASE_DIR.parent / "timetable_engine"
        try:
            if str(engine_dir) not in sys.path:
                sys.path.insert(0, str(engine_dir))

            from generic_solver import solve_generic_timetable

            records, output_path, status = solve_generic_timetable(semester)

            return render_template(
                "generic_result.html",
                semester=semester,
                records=records,
                status=status,
                output_path=str(output_path),
            )
        except Exception as exc:
            return Response(
                "<h2>Timetable generation failed</h2><pre>"
                + html.escape(str(exc))
                + "</pre><p><a href='/'>Back to dashboard</a></p>",
                status=400,
                mimetype="text/html",
            )

    if semester != 5:
        return Response(
            f"<h2>Semester {semester} is not ready for generation.</h2>"
            '<p>Complete the semester resource and batch configuration first.</p>'
            '<p><a href="/">Back to dashboard</a></p>',
            status=400,
            mimetype="text/html",
        )

    # GET must only display confirmation; generation requires explicit POST.
    if request.method == "GET":
        page = """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Confirm Semester V Generation</title>
            <style>
                body { font-family: Segoe UI, Arial, sans-serif;
                       max-width: 680px; margin: 60px auto; padding: 24px;
                       color: #1c2b3d; background: #eef2f7; }
                section { background: white; padding: 28px;
                          border-radius: 10px; }
                button, a { display: inline-block; padding: 10px 16px;
                            margin: 8px 8px 0 0; border-radius: 5px;
                            text-decoration: none; cursor: pointer; }
                button { background: #17365d; color: white; border: 0; }
                a { color: #17365d; border: 1px solid #b9c8d9; }
            </style>
        </head>
        <body>
            <section>
                <h2>Generate Semester V Timetable?</h2>
                <p>Generation runs the existing Semester V solver and may
                   update the saved timetable output.</p>
                <p>Continue only when you intend to generate a new timetable.</p>
                <form method="post" action="/generate/5">
                    <button type="submit">Confirm and Generate</button>
                    <a href="/">Cancel and Return to Dashboard</a>
                </form>
            </section>
        </body>
        </html>
        """
        return Response(page, mimetype="text/html")
    engine_dir = BASE_DIR.parent / "timetable_engine"
    if not engine_dir.is_dir():
        return Response(
            "<h2>Timetable engine folder was not found.</h2>"
            "<p>Expected: timetable_engine beside web_form.</p>"
            '<p><a href="/">Back to dashboard</a></p>',
            status=500,
            mimetype="text/html",
        )

    try:
        if str(engine_dir) not in sys.path:
            sys.path.insert(0, str(engine_dir))

        from solver import solve_timetable
        result = solve_timetable()

        if not result or len(result) < 3 or not result[2]:
            raise RuntimeError(
                "The solver did not return a timetable. "
                "Check the Flask terminal for solver status."
            )

        records = result[2]
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        periods = ["P1", "P2", "P3", "P4", "P5", "P6"]
        time_labels = {
            "P1": "08:45-09:45", "P2": "09:45-10:45",
            "P3": "11:00-12:00", "P4": "12:00-13:00",
            "P5": "13:45-14:45", "P6": "14:45-15:45",
        }
        grid = {(day, period): [] for day in days for period in periods}
        for record in records:
            day = str(record.get("day", "")).strip()
            period = str(record.get("period", "")).strip()
            if (day, period) in grid:
                grid[(day, period)].append(record)

        header_html = "<th class=\"day-col\">Day</th>" + "".join(
            f"<th><span>{period}</span><small>{time_labels[period]}</small></th>"
            for period in periods
        )
        rows_html = []
        for day in days:
            cells = [f"<th class=\"day-name\">{day}</th>"]
            for period in periods:
                entries = grid[(day, period)]
                if not entries:
                    content = '<div class=\"free-slot\">Ã¢â‚¬â€</div>'
                else:
                    cards = []
                    for record in entries:
                        subject = html.escape(str(record.get("subject", "Untitled subject")))
                        batch = html.escape(str(record.get("batch", "")))
                        faculty = html.escape(str(record.get("faculty", "")))
                        room = html.escape(str(record.get("room", "")))
                        start_time = html.escape(str(record.get("start", "")))
                        end_time = html.escape(str(record.get("end", "")))
                        cards.append(
                            '<div class=\"session\">'
                            f'<div class=\"subject\">{subject}</div>'
                            f'<div class=\"meta\"><b>Batch</b> {batch}</div>'
                            f'<div class=\"meta\"><b>Faculty</b> {faculty}</div>'
                            f'<div class=\"meta\"><b>Room</b> {room}</div>'
                            f'<div class=\"time\">{start_time}Ã¢â‚¬â€œ{end_time}</div>'
                            '</div>'
                        )
                    content = "".join(cards)
                cells.append(f"<td>{content}</td>")
            rows_html.append("<tr>" + "".join(cells) + "</tr>")

        page = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Semester V Timetable | ENTC</title>
<style>
:root{--navy:#17365d;--blue:#245b9e;--ink:#1c2b3d;--muted:#5f6f82;--line:#cbd6e2;--bg:#eef2f7;--white:#fff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Segoe UI",Arial,sans-serif}
header{background:var(--navy);color:#fff;padding:22px 30px}
.header-inner{max-width:1800px;margin:auto;display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap}
h1{font-size:26px;margin:0 0 6px;font-weight:750;letter-spacing:.1px}
.subtitle{font-size:14px;margin:0;color:#dbe7f5}
.pattern{font-size:12px;border:1px solid #91aac8;border-radius:5px;padding:7px 10px;white-space:nowrap}
main{max-width:1800px;margin:22px auto;padding:0 24px 32px}
.toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:14px}
.toolbar p{margin:0;font-size:14px;color:var(--muted)}
.actions{display:flex;gap:8px;flex-wrap:wrap}
.btn{display:inline-block;text-decoration:none;border:1px solid #b9c8d9;border-radius:6px;padding:9px 13px;background:#fff;color:var(--navy);font-weight:650;font-size:13px;cursor:pointer}
.btn.primary{background:var(--navy);color:#fff;border-color:var(--navy)}
.heading{display:flex;justify-content:space-between;align-items:end;gap:12px;flex-wrap:wrap;margin:14px 0 12px}
h2{font-size:21px;margin:0;color:var(--navy)}
.heading p{margin:5px 0 0;color:var(--muted);font-size:13px}
.status{font-size:12px;font-weight:700;color:#17603c;background:#e2f4e9;border:1px solid #b7e0c6;border-radius:5px;padding:7px 10px}
.table-wrap{overflow:auto;background:#fff;border:1px solid #b8c7d8;border-radius:8px;box-shadow:0 3px 12px rgba(28,48,75,.06)}
table{width:100%;min-width:1450px;border-collapse:separate;border-spacing:0;table-layout:fixed}
th{background:#e4ebf4;color:var(--navy);padding:12px 10px;border-right:1px solid #cbd6e2;border-bottom:2px solid #b8c7d8;text-align:center;font-size:13px}
thead th{background:var(--navy);color:#fff;font-size:14px;padding:13px 8px}
thead th small{display:block;font-size:11px;font-weight:500;color:#d7e4f3;margin-top:5px;white-space:nowrap}
.day-col{width:105px}.day-name{width:105px;text-align:left;font-size:14px;background:#e8eef6;vertical-align:middle}
td{width:16.5%;vertical-align:top;padding:7px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);background:#fff}
tbody tr:nth-child(even) td{background:#f8fafc}
tbody tr:last-child td,tbody tr:last-child th{border-bottom:0}
th:last-child,td:last-child{border-right:0}
.session{background:#fff;border:1px solid #d4deea;border-left:4px solid var(--blue);border-radius:5px;padding:9px 9px 8px;margin:0 0 6px;box-shadow:0 1px 2px rgba(25,50,80,.04)}
.session:last-child{margin-bottom:0}.subject{font-size:13px;font-weight:750;line-height:1.35;color:#17365d;margin-bottom:7px;overflow-wrap:anywhere}
.meta{font-size:11.5px;line-height:1.55;color:#44556a;overflow-wrap:anywhere}.meta b{color:#263b53}
.time{font-size:10.5px;color:#718096;margin-top:5px;padding-top:4px;border-top:1px solid #edf1f5}
.free-slot{color:#a2adba;text-align:center;padding:16px 0;font-size:18px}
.footer{margin-top:12px;display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;color:var(--muted);font-size:12px}
@media(max-width:800px){header{padding:18px}main{padding:0 12px 20px}h1{font-size:22px}}
@media print{@page{size:landscape;margin:8mm}body{background:#fff}header{padding:10px 12px;background:#fff;color:#111;border-bottom:2px solid #17365d}.subtitle{color:#333}.pattern{color:#333;border-color:#888}.toolbar .actions,.footer{display:none}main{max-width:none;margin:10px 0;padding:0}.table-wrap{overflow:visible;box-shadow:none;border-radius:0}table{min-width:0;width:100%;table-layout:fixed}thead th{background:#17365d!important;color:#fff!important;-webkit-print-color-adjust:exact;print-color-adjust:exact;padding:7px 4px;font-size:10px}thead th small{font-size:8px;color:#fff!important}td{padding:3px;break-inside:avoid}.day-name{font-size:10px;padding:5px}.session{padding:4px;margin-bottom:3px;border-left-width:2px;box-shadow:none}.subject{font-size:8px;margin-bottom:3px}.meta{font-size:7px;line-height:1.3}.time{font-size:7px;margin-top:2px;padding-top:2px}.heading{margin:8px 0}h2{font-size:15px}.heading p{font-size:9px}.status{font-size:9px;padding:4px}}
</style>
</head>
<body>
<header><div class="header-inner"><div><h1>ENTC Ã¢â‚¬â€ Semester V Timetable</h1><p class="subtitle">KJ College of Engineering &amp; Management Research, Pune Ã‚Â· Academic timetable</p></div><span class="pattern">2024 Pattern / NEP 2020</span></div></header>
<main>
<div class="toolbar"><p><strong>__COUNT__ sessions</strong> scheduled Ã‚Â· Monday to Friday Ã‚Â· Six periods per day</p><div class="actions"><a class="btn" href="/">Ã¢â€ Â Dashboard</a><a class="btn" href="/data-form">Data collection</a><button class="btn primary" onclick="window.print()">Print / Save PDF</button></div></div>
<div class="heading"><div><h2>Weekly timetable</h2><p>Each cell shows the subject, batch, faculty, and assigned room.</p></div><span class="status">Ã¢Å“â€œ Generation completed</span></div>
<div class="table-wrap"><table><thead><tr>__HEADERS__</tr></thead><tbody>__ROWS__</tbody></table></div>
<div class="footer"><span>ENTC Ã‚Â· Semester V Ã‚Â· Timetable prototype</span><span>Break: 10:45Ã¢â‚¬â€œ11:00 Ã‚Â· Lunch: 13:00Ã¢â‚¬â€œ13:45</span></div>
</main>
</body></html>'''
        page = (page.replace("__COUNT__", str(len(records)))
                    .replace("__HEADERS__", header_html)
                    .replace("__ROWS__", "".join(rows_html)))
        return Response(page, mimetype="text/html")

    except Exception as error:
        app.logger.exception("Semester V timetable generation failed")
        message = html.escape(f"{type(error).__name__}: {error}")
        return Response(
            "<h2>Timetable generation failed</h2>"
            f"<pre>{message}</pre>"
            "<p>Check the Flask terminal for the full error details.</p>"
            '<p><a href="/">Back to dashboard</a></p>',
            status=500,
            mimetype="text/html",
        )


@app.route("/submit", methods=["POST"])

def submit():



          try:



                    # ----------------------------------------------------

                    # SUBMISSION ID

                    # ----------------------------------------------------



                    now = datetime.now()



                    submission_id = (

                              f"ENTC_"

                              f"{now.strftime('%Y%m%d_%H%M%S')}_"

                              f"{uuid.uuid4().hex[:6].upper()}"

                    )



                    submission_dir = SUBMISSIONS_DIR / submission_id



                    submission_dir.mkdir(

                              parents=True,

                              exist_ok=True

                    )



                    upload_dir = submission_dir / "uploads"



                    # ----------------------------------------------------

                    # ACADEMIC INFORMATION

                    # ----------------------------------------------------



                    academic = {

                              "college": request.form.get(

                                        "college_name", request.form.get("college", "")

                              ).strip(),



                              "department": request.form.get(

                                        "department", ""

                              ).strip(),



                              "academic_year": request.form.get(

                                        "academic_year", ""

                              ).strip(),



                              "pattern": request.form.get(

                                        "pattern", ""

                              ).strip(),



                              "semester": request.form.get(

                                        "semester", ""

                              ).strip(),



                              "working_days": request.form.get(

                                        "working_days", ""

                              ).strip(),



                              "start_time": request.form.get(

                                        "college_start", request.form.get("start_time", "")

                              ).strip(),



                              "end_time": request.form.get(

                                        "college_end", request.form.get("end_time", "")

                              ).strip(),



                              "break_time": request.form.get(

                                        "short_break", request.form.get("break_time", "")

                              ).strip(),



                              "lunch_time": request.form.get(

                                        "lunch_break", request.form.get("lunch_time", "")

                              ).strip(),

                    }



                    # ----------------------------------------------------

                    # BATCH INFORMATION

                    # ----------------------------------------------------



                    batch_codes = get_list_values(

                              "batch_code[]"

                    )



                    batch_students = get_list_values(

                              "batch_students[]"

                    )



                    batch_electives = get_list_values(

                              "batch_elective[]"

                    )



                    batches = []



                    batch_count = max(

                              len(batch_codes),

                              len(batch_students),

                              len(batch_electives),

                    )



                    for i in range(batch_count):



                              code = (

                                        batch_codes[i].strip()

                                        if i < len(batch_codes)

                                        else ""

                              )



                              students = (

                                        batch_students[i].strip()

                                        if i < len(batch_students)

                                        else ""

                              )



                              elective = (

                                        batch_electives[i].strip()

                                        if i < len(batch_electives)

                                        else ""

                              )



                              if not code:

                                        continue



                              try:

                                        students_value = int(students)

                              except (ValueError, TypeError):

                                        students_value = 0



                              batches.append({

                                        "code": code,

                                        "students": students_value,

                                        "elective": elective,

                              })



                    # ----------------------------------------------------

                    # FACULTY INFORMATION

                    # ----------------------------------------------------



                    faculty_codes = get_list_values(

                              "faculty_code[]"

                    )



                    faculty_names = get_list_values(

                              "faculty_name[]"

                    )



                    # Checkbox selections are collected per faculty card.
                    faculty = []

                    faculty_count = max(
                              len(faculty_codes),
                              len(faculty_names),
                              len(faculty_theory_status),
                              len(faculty_tutorial_status),
                              len(faculty_practical_status),
                    )

                    for i in range(faculty_count):

                              code = faculty_codes[i] if i < len(faculty_codes) else ""
                              name = faculty_names[i] if i < len(faculty_names) else ""

                              theory_status = (
                                        faculty_theory_status[i]
                                        if i < len(faculty_theory_status)
                                        else "not_specified"
                              )

                              tutorial_status = (
                                        faculty_tutorial_status[i]
                                        if i < len(faculty_tutorial_status)
                                        else "not_specified"
                              )

                              practical_status = (
                                        faculty_practical_status[i]
                                        if i < len(faculty_practical_status)
                                        else "not_specified"
                              )

                              theory_value = ", ".join(get_list_values(
                                        f"faculty_theory_by_card_{i}[]"
                              ))

                              tutorial_value = ", ".join(get_list_values(
                                        f"faculty_tutorial_by_card_{i}[]"
                              ))

                              practical_value = ", ".join(get_list_values(
                                        f"faculty_practical_by_card_{i}[]"
                              ))
                              faculty.append({



                                        "code": code,



                                        "name": name or code,



                                        "theory_status": theory_status,



                                        "tutorial_status": tutorial_status,



                                        "practical_status": practical_status,



                                        "theory": (

                                                  split_subjects(theory_value)

                                                  if theory_status == "known"

                                                  else []

                                        ),



                                        "tutorial": (

                                                  split_subjects(tutorial_value)

                                                  if tutorial_status == "known"

                                                  else []

                                        ),



                                        "practical": (

                                                  split_subjects(practical_value)

                                                  if practical_status == "known"

                                                  else []

                                        ),



                              })



                    # ----------------------------------------------------

                    # ROOM INFORMATION

                    # ----------------------------------------------------



                    room_codes = get_list_values(

                              "room_code[]"

                    )



                    room_capacities = get_list_values(

                              "room_capacity[]"

                    )



                    room_types = get_list_values(

                              "room_type[]"

                    )



                    rooms = []



                    room_count = max(

                              len(room_codes),

                              len(room_capacities),

                              len(room_types),

                    )



                    for i in range(room_count):



                              code = (

                                        room_codes[i].strip()

                                        if i < len(room_codes)

                                        else ""

                              )



                              capacity = (

                                        room_capacities[i].strip()

                                        if i < len(room_capacities)

                                        else ""

                              )



                              room_type = (

                                        room_types[i].strip()

                                        if i < len(room_types)

                                        else ""

                              )



                              if not code:

                                        continue



                              try:

                                        capacity_value = int(capacity)

                              except (ValueError, TypeError):

                                        capacity_value = 0



                              rooms.append({

                                        "code": code,

                                        "capacity": capacity_value,

                                        "type": room_type,

                              })



                    # ----------------------------------------------------

                    # RULES

                    # ----------------------------------------------------



                    rules = {

                              "practical_parallel": request.form.get(

                                        "practical_parallel", ""

                              ).strip(),



                              "same_faculty_conflict": request.form.get(

                                        "same_faculty_conflict", ""

                              ).strip(),



                              "room_capacity_rule": request.form.get(

                                        "room_capacity_rule", ""

                              ).strip(),



                              "additional_rules": request.form.get(

                                        "additional_rules", ""

                              ).strip(),

                    }



                    # ----------------------------------------------------

                    # NOTES

                    # ----------------------------------------------------



                    notes = request.form.get(

                              "notes", ""

                    ).strip()



                    # ----------------------------------------------------

                    # FILE UPLOADS

                    # ----------------------------------------------------



                    uploaded_files = request.files.getlist(

                              "supporting_files"

                    )



                    saved_files = save_uploaded_files(

                              uploaded_files,

                              upload_dir

                    )



                    # ----------------------------------------------------

                    # COMPLETE SUBMISSION

                    # ----------------------------------------------------



                    submission = {



                              "submission_id": submission_id,



                              "submitted_at": now.isoformat(

                                        timespec="seconds"

                              ),



                              "academic": academic,



                              "batches": batches,



                              "faculty": faculty,



                              "rooms": rooms,



                              "rules": rules,



                              "notes": notes,



                              "files": saved_files,



                    }



                    # ----------------------------------------------------

                    # SAVE JSON

                    # ----------------------------------------------------



                    submission_file = (

                              submission_dir / "submission.json"

                    )



                    with open(

                              submission_file,

                              "w",

                              encoding="utf-8"

                    ) as file:



                              json.dump(

                                        submission,

                                        file,

                                        indent=4,

                                        ensure_ascii=False

                              )



                    # ----------------------------------------------------

                    # SUCCESS

                    # ----------------------------------------------------



                    return f"""

                    <!DOCTYPE html>



                    <html>



                    <head>

                              <title>Submission Successful</title>



                              <style>



                                        body {{

                                                  font-family: Arial, sans-serif;

                                                  background: #f4f6f8;

                                                  padding: 50px;

                                        }}



                                        .box {{

                                                  max-width: 700px;

                                                  margin: auto;

                                                  background: white;

                                                  padding: 35px;

                                                  border-radius: 12px;

                                                  box-shadow: 0 4px 15px rgba(0,0,0,0.1);

                                        }}



                                        h1 {{

                                                  color: #1b7f3a;

                                        }}



                                        code {{

                                                  background: #f1f1f1;

                                                  padding: 8px;

                                                  border-radius: 5px;

                                        }}



                                        a {{

                                                  display: inline-block;

                                                  margin-top: 20px;

                                                  text-decoration: none;

                                                  background: #2563eb;

                                                  color: white;

                                                  padding: 10px 18px;

                                                  border-radius: 6px;

                                        }}



                              </style>



                    </head>



                    <body>



                              <div class="box">



                                        <h1>Ã¢Å“â€œ Submission Successful</h1>



                                        <p>

                                                  Your timetable input data has been saved.

                                        </p>



                                        <p>

                                                  <strong>Submission ID:</strong>

                                        </p>



                                        <p>

                                                  <code>{submission_id}</code>

                                        </p>



                                        <p>

                                                  Faculty expertise status is also stored

                                                  as <b>Known</b> or <b>Not specified</b>.

                                        </p>



                                        <a href="/">

                                                  Submit Another Form

                                        </a>



                              </div>



                    </body>



                    </html>

                    """



          except Exception as error:



                    print(

                              "FORM SUBMISSION ERROR:",

                              repr(error)

                    )



                    return f"""

                    <h2>Submission Error</h2>



                    <p>

                              Something went wrong while saving the form.

                    </p>



                    <pre>{error}</pre>



                    <a href="/">

                              Go Back

                    </a>

                    """, 500





# ============================================================
# FACULTY SELF-SERVICE PORTAL (additive; does not alter Semester V solver)
# ============================================================
import os
import secrets
import hashlib
import hmac
from functools import wraps
from flask import session, abort

# Use an environment-provided secret for sessions. Set AI_TIMETABLE_SECRET_KEY
# before deploying. The legacy key remains as a local-development fallback.
app.secret_key = os.environ.get("AI_TIMETABLE_SECRET_KEY") or app.secret_key

FACULTY_PORTAL_DIR = DATA_INPUT_DIR / "faculty_portal"
AUTH_FILE = FACULTY_PORTAL_DIR / "faculty_accounts.json"
PORTAL_SEMESTERS = {3, 4, 6}  # Semester V deliberately excluded.
PORTAL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PORTAL_PERIODS = [
    ("P1", "08:45-09:45"), ("P2", "09:45-10:45"),
    ("P3", "11:00-12:00"), ("P4", "12:00-13:00"),
    ("P5", "13:45-14:45"), ("P6", "14:45-15:45"),
]


def _portal_read(path, default):
    try:
        with path.open("r", encoding="utf-8") as fh:
            value = json.load(fh)
        return value
    except (OSError, json.JSONDecodeError):
        return default


def _portal_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(value, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(path)


def _portal_hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                 bytes.fromhex(salt), 240_000).hex()
    return {"salt": salt, "password_hash": digest}


def _portal_accounts():
    data = _portal_read(AUTH_FILE, {"accounts": {}})
    if not isinstance(data, dict) or not isinstance(data.get("accounts"), dict):
        return {"accounts": {}}
    return data


def _portal_csrf():
    token = session.get("_portal_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_portal_csrf"] = token
    return token


def _portal_check_csrf():
    sent = request.form.get("_csrf", "")
    expected = session.get("_portal_csrf", "")
    if not sent or not expected or not hmac.compare_digest(sent, expected):
        abort(400, description="Invalid form token. Refresh the page and try again.")


def _portal_logged_in(role=None):
    identity = session.get("portal_identity")
    return bool(identity and (role is None or identity.get("role") == role))


def _portal_login_required(role):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not _portal_logged_in(role):
                return redirect(url_for("portal_login", role=role, next=request.path))
            return fn(*args, **kwargs)
        return wrapped
    return decorate


def _portal_subjects(semester):
    folder = semester_data_dir(semester)
    raw = _portal_read(folder / "subjects.json", {})
    if isinstance(raw, dict) and isinstance(raw.get("subjects"), dict):
        raw = raw["subjects"]
    if not isinstance(raw, dict):
        return {}
    return {str(code): info for code, info in raw.items()
            if isinstance(info, dict) and info.get("included", True) is not False}


def _portal_request_file(semester):
    return FACULTY_PORTAL_DIR / f"sem_{semester}" / "requests.json"


def _portal_requests(semester):
    raw = _portal_read(_portal_request_file(semester), {"requests": []})
    if not isinstance(raw, dict) or not isinstance(raw.get("requests"), list):
        return {"requests": []}
    return raw


@app.route("/portal/login", methods=["GET", "POST"])
def portal_login():
    role = request.args.get("role", "faculty")
    if role not in {"faculty", "admin"}:
        role = "faculty"
    error = ""
    if request.method == "POST":
        _portal_check_csrf()
        posted_role = request.form.get("role", "faculty")
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if posted_role == "admin":
            admin_password = os.environ.get("AI_TIMETABLE_ADMIN_PASSWORD", "")
            if not admin_password:
                error = "Admin login is disabled until AI_TIMETABLE_ADMIN_PASSWORD is set in the environment."
            elif hmac.compare_digest(password, admin_password) and username == "admin":
                session.clear()
                session["portal_identity"] = {"role": "admin", "username": "admin", "name": "Administrator"}
                _portal_csrf()
                return redirect(url_for("portal_admin"))
            else:
                error = "Invalid administrator credentials."
        else:
            account = _portal_accounts()["accounts"].get(username)
            if account and account.get("active") is True:
                stored = account.get("password_hash", "")
                salt = account.get("salt", "")
                calculated = _portal_hash_password(password, salt).get("password_hash", "")
                if salt and hmac.compare_digest(calculated, stored):
                    session.clear()
                    session["portal_identity"] = {
                        "role": "faculty", "username": username,
                        "faculty_code": account.get("faculty_code", ""),
                        "name": account.get("name", username),
                    }
                    _portal_csrf()
                    return redirect(url_for("portal_faculty"))
            error = "Invalid credentials or account not active."
        role = posted_role if posted_role in {"faculty", "admin"} else "faculty"
    return render_template("portal_login.html", role=role, error=error, csrf=_portal_csrf())


@app.route("/portal/logout", methods=["POST"])
def portal_logout():
    _portal_check_csrf()
    session.clear()
    return redirect(url_for("index"))


@app.route("/portal/faculty", methods=["GET", "POST"])
@_portal_login_required("faculty")
def portal_faculty():
    identity = session["portal_identity"]
    semester = request.args.get("semester", "3")
    try:
        semester = int(semester)
    except (TypeError, ValueError):
        semester = 3
    if semester not in PORTAL_SEMESTERS:
        semester = 3
    subjects = _portal_subjects(semester)
    error = ""
    saved = False
    if request.method == "POST":
        _portal_check_csrf()
        try:
            semester = int(request.form.get("semester", "3"))
        except (TypeError, ValueError):
            semester = 0
        if semester not in PORTAL_SEMESTERS:
            abort(400, description="This semester is not available in the faculty portal.")
        subjects = _portal_subjects(semester)
        selected_codes = [code for code in request.form.getlist("subject_codes")
                          if code in subjects]
        proposed_name = request.form.get("proposed_subject_name", "").strip()
        proposed_code = request.form.get("proposed_subject_code", "").strip().upper()
        proposed_type = request.form.get("proposed_subject_type", "theory").strip().lower()
        try:
            th = int(request.form.get("proposed_theory_hours", "0") or 0)
            tu = int(request.form.get("proposed_tutorial_hours", "0") or 0)
            pr = int(request.form.get("proposed_practical_hours", "0") or 0)
        except ValueError:
            th = tu = pr = -1
        proposal = None
        if proposed_name or proposed_code:
            if not proposed_name or not proposed_code:
                error = "For a new-subject proposal, both subject code and subject name are required."
            elif proposed_code in subjects:
                error = "That subject code already exists. Select the existing subject instead."
            elif min(th, tu, pr) < 0 or max(th, tu, pr) > 20 or (th + tu + pr) <= 0:
                error = "Workload must be whole numbers from 0 to 20 hours, with at least one hour specified."
            elif proposed_type not in {"theory", "tutorial", "practical", "mixed"}:
                error = "Choose a valid subject type."
            else:
                proposal = {
                    "code": proposed_code, "subject": proposed_name,
                    "type": proposed_type, "theory_hours": th,
                    "tutorial_hours": tu, "practical_hours": pr,
                    "included": True,
                }
        if not error:
            periods = request.form.getlist("unavailable_slots")
            valid_slots = {f"{d}|{p[0]}" for d in PORTAL_DAYS for p in PORTAL_PERIODS}
            unavailable = [slot for slot in periods if slot in valid_slots]
            preferences = [slot for slot in request.form.getlist("preferred_slots") if slot in valid_slots]
            record = {
                "request_id": secrets.token_hex(8),
                "submitted_at": datetime.now().isoformat(timespec="seconds"),
                "semester": semester,
                "faculty_code": identity.get("faculty_code", ""),
                "faculty_username": identity["username"],
                "faculty_name": identity.get("name", identity["username"]),
                "selected_subject_codes": selected_codes,
                "selected_subject_names": [subjects[c].get("subject", c) for c in selected_codes],
                "proposed_subject": proposal,
                "unavailable_slots": unavailable,
                "preferred_slots": preferences,
                "status": "pending",
                "admin_note": "",
                "reviewed_at": None,
            }
            data = _portal_requests(semester)
            data["requests"].append(record)
            _portal_write(_portal_request_file(semester), data)
            saved = True
    # Refresh request history for this logged-in faculty identity.
    own = [r for r in _portal_requests(semester)["requests"]
           if r.get("faculty_username") == identity["username"]]
    return render_template(
        "portal_faculty.html", identity=identity, semester=semester,
        subjects=subjects, days=PORTAL_DAYS, periods=PORTAL_PERIODS,
        error=error, saved=saved, own_requests=own, csrf=_portal_csrf(),
        semesters=sorted(PORTAL_SEMESTERS),
    )


@app.route("/portal/admin", methods=["GET", "POST"])
@_portal_login_required("admin")
def portal_admin():
    error = ""
    notice = ""
    if request.method == "POST":
        _portal_check_csrf()
        action = request.form.get("action", "")
        if action == "create_account":
            username = request.form.get("username", "").strip().lower()
            name = request.form.get("name", "").strip()
            faculty_code = request.form.get("faculty_code", "").strip()
            password = request.form.get("password", "")
            if not all([username, name, faculty_code]) or len(password) < 12:
                error = "Provide username, name, faculty code, and a password of at least 12 characters."
            elif not username.replace(".", "").replace("_", "").replace("-", "").isalnum():
                error = "Username may contain letters, digits, dot, underscore, and hyphen only."
            else:
                data = _portal_accounts()
                if username in data["accounts"]:
                    error = "That username already exists."
                else:
                    hashed = _portal_hash_password(password)
                    data["accounts"][username] = {
                        **hashed, "name": name, "faculty_code": faculty_code,
                        "active": True, "created_at": datetime.now().isoformat(timespec="seconds"),
                    }
                    _portal_write(AUTH_FILE, data)
                    notice = f"Faculty account '{username}' created."
        elif action in {"approve", "reject", "changes"}:
            try:
                semester = int(request.form.get("semester", "0"))
            except ValueError:
                semester = 0
            request_id = request.form.get("request_id", "")
            note = request.form.get("admin_note", "").strip()[:1000]
            if semester not in PORTAL_SEMESTERS:
                error = "Unsupported semester."
            else:
                data = _portal_requests(semester)
                target = next((r for r in data["requests"] if r.get("request_id") == request_id), None)
                if not target:
                    error = "Request not found."
                else:
                    target["status"] = {"approve": "approved", "reject": "rejected", "changes": "changes_requested"}[action]
                    target["admin_note"] = note
                    target["reviewed_at"] = datetime.now().isoformat(timespec="seconds")
                    _portal_write(_portal_request_file(semester), data)
                    # Crucial: approval records the review only. It never edits
                    # subjects.json, faculty assignments, or readiness flags.
                    notice = f"Request {request_id} marked {target['status']}. Curriculum and readiness were not changed."
        else:
            error = "Unknown action."
    all_requests = []
    for sem in sorted(PORTAL_SEMESTERS):
        for item in _portal_requests(sem)["requests"]:
            all_requests.append(item)
    all_requests.sort(key=lambda item: item.get("submitted_at", ""), reverse=True)
    accounts = _portal_accounts()["accounts"]
    account_rows = [{"username": u, "name": a.get("name", ""),
                     "faculty_code": a.get("faculty_code", ""),
                     "active": a.get("active") is True}
                    for u, a in sorted(accounts.items())]
    return render_template("portal_admin.html", requests=all_requests,
                           accounts=account_rows, error=error, notice=notice,
                           csrf=_portal_csrf())


@app.route("/portal/health", methods=["GET"])
def portal_health():
    """Read-only portal status page."""
    semesters = ", ".join(str(s) for s in sorted(PORTAL_SEMESTERS))
    page = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Faculty Portal Health</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#eef2f7;color:#1c2b3d;font-family:Segoe UI,Arial,sans-serif}
header{background:#17365d;color:white;padding:28px 20px}
main{max-width:760px;margin:36px auto;padding:0 18px}
.card{background:white;border:1px solid #d9e1ea;border-radius:12px;padding:24px;margin-bottom:16px}
.status{display:inline-block;padding:6px 12px;border-radius:20px;background:#dcfce7;color:#166534;font-weight:700}
h1{margin:0 0 8px;font-size:26px}
h2{margin-top:0}
p{line-height:1.6}
.row{display:flex;justify-content:space-between;gap:15px;padding:12px 0;border-bottom:1px solid #e5eaf0}
.row:last-child{border-bottom:0}
.btn{display:inline-block;margin-top:12px;padding:10px 15px;border-radius:6px;background:#17365d;color:white;text-decoration:none}
.muted{color:#64748b;font-size:13px}
</style>
</head>
<body>
<header><h1>Faculty Portal Health</h1><div>ENTC AI-Based Timetable Generation System</div></header>
<main>
<section class="card">
<h2>Portal service status</h2>
<p><span class="status">Available</span></p>
<p>The health endpoint responded successfully. This page reports basic service status only; it does not verify every faculty workflow.</p>
<div class="row"><strong>Portal</strong><span>Available</span></div>
<div class="row"><strong>Faculty semesters</strong><span>__SEMESTERS__</span></div>
<div class="row"><strong>Semester V solver</strong><span>Existing legacy solver</span></div>
<a class="btn" href="/">Back to Dashboard</a>
<a class="btn" href="/portal/login">Faculty Login</a>
</section>
<p class="muted">Read-only status page. No timetable generation or data changes are performed here.</p>
</main>
</body>
</html>"""
    return Response(
        page.replace("__SEMESTERS__", html.escape(semesters)),
        status=200,
        mimetype="text/html",
    )


# ============================================================

# RUN APPLICATION

# ============================================================



if __name__ == "__main__":



          print("=" * 60)

          print("AI TIMETABLE WEB FORM")

          print("=" * 60)



          print(

                    f"Submissions directory:\n{SUBMISSIONS_DIR}"

          )



          print(

                    "\nOpen in browser:"

          )



          print(

                    "http://127.0.0.1:5000"

          )



          print("=" * 60)



          app.run(

                    host="127.0.0.1",

                    port=5000,

                    debug=True

          )

