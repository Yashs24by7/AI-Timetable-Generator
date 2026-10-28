ENTC AI Timetable Generation System - V5 Faculty Assignment Module

CONTENTS
- app.py: updated Flask routes, subject-to-faculty assignment page, readiness status integration
- templates/semester_config.html: adds a navigation link to assignments
- templates/faculty_assignments.html: subject-to-faculty assignment form
- templates/dashboard.html: preserved from V4

INSTALL
1. Stop Flask with Ctrl+C.
2. Back up web_form\app.py and web_form\templates\semester_config.html.
3. Extract this ZIP into C:\AI_Timetable_Project_Updated\web_form, preserving folders and allowing replacement.
4. Restart:
   Set-Location "C:\AI_Timetable_Project_Updated\web_form"
   & "C:\AI_Timetable_Project\.venv\Scripts\python.exe" app.py
5. Open http://127.0.0.1:5000/semester/3/assignments
   or open the Semester III configuration page and click "Subject-to-faculty assignments".

BEHAVIOR
- Reads semester curriculum from data\input\sem_N\subjects.json.
- Uses semester faculty records; if empty, displays shared faculty as a provisional pool.
- Saves faculty_assignments and faculty_assignments_verified in that semester's configuration.json.
- Assignment keys are curriculum subject names and values are lists of faculty codes, compatible with the generic solver's subject-level assignment lookup.
- It does not alter Semester V files or solver.
- Verification remains pending unless the user explicitly checks the confirmation box. If checked, all subjects with scheduled workload must have a faculty selection.

IMPORTANT LIMITATION
This version supports one faculty member per subject across its session types. If a subject has different faculty for theory/tutorial/practical, use exact session-level assignments in advanced configuration. Do not use provisional assignments as real allocations.

VALIDATION
Python syntax compilation passed. This patch was not executed inside the user's Windows virtual environment, so test the route and save behavior locally before relying on it.
