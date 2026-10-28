SEMESTER III BATCH + LOADER FIX

This ZIP contains TWO replacements:
1. timetable_engine/data_loader_multisemester.py
2. data/input/sem_3/batches.json

Install both from the extracted ZIP into the matching folders under:
C:\AI_Timetable_Project_Updated\

Before replacing, back up both existing files.

After replacement, run PowerShell:

Set-Location "C:\AI_Timetable_Project_Updated\timetable_engine"
& "C:\AI_Timetable_Project\.venv\Scripts\python.exe" -m py_compile ".\data_loader_multisemester.py"
& "C:\AI_Timetable_Project\.venv\Scripts\python.exe" -c "from data_loader_multisemester import load_semester_data; d=load_semester_data(3); print('LOADER:', __import__('data_loader_multisemester').__file__); print('BATCHES:', d.get('batches')); print('BATCH DATA COMPLETE:', d.get('batch_data_complete')); print('READINESS:', d.get('readiness_status')); print('MESSAGE:', d.get('readiness_message'))"

Expected batch output includes S1 and S2 with 40 students each and BATCH DATA COMPLETE: True.
The semester may still report INPUT INCOMPLETE because faculty/resource configuration is not yet complete. Do not run generation until those are configured.
