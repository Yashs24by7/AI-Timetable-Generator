# ENTC AI Timetable — Data Collection Web Form V1

A simple Flask web form for collecting timetable inputs from the project guide/faculty.

## What V1 does
- Collects academic details
- Uploads curriculum/workload documents
- Collects batch/elective information
- Collects faculty codes and subjects
- Collects rooms/labs and capacities
- Collects timetable constraints/rules
- Accepts supporting documents
- Saves every submission in `submissions/<submission_id>/`
  - `submission.json`
  - `uploads/`

## What V1 does NOT do yet
- OCR/AI extraction
- OR-Tools timetable generation
- Automatic conflict resolution
- Public hosting/login
- Database dashboard

Those are the next stages.

## Run on Windows
1. Install Python 3.10+.
2. Open Command Prompt in this folder.
3. Install Flask:
   `py -m pip install flask werkzeug`
4. Start:
   `py app.py`
5. Open:
   `http://127.0.0.1:5000`

## Important
Change `app.secret_key` before deploying publicly.

## Current TE Sem V defaults
- 2024 Pattern / NEP 2020
- Monday–Friday
- 08:45–15:45
- Break 10:45–11:00
- Lunch 13:00–13:45
- T1 1–32, Cloud Computing
- T2 33–63, Cloud Computing
- T3 64–80, Advanced Java Programming
- Rooms 312=80, 322=80, 319=50
- Labs A317/A318/A320 modeled at effective capacity 48 (24 PCs × 2 students/PC)
- T1+T2 Cloud combined lecture
- Practical rotation across T1/T2/T3
- 3:45–4:30 excluded by default
