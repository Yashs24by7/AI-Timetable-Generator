from faculty_expertise import (
    get_faculty_for_subject,
    get_subjects_for_faculty,
)


print("=" * 70)
print("FACULTY-SUBJECT MATCHING TEST")
print("=" * 70)

subjects = [
    "Microcontrollers & Applications",
    "Cellular Network",
    "VLSI Design",
    "Machine Learning",
    "Microcontrollers & VLSI Design Lab",
    "Cellular Network Lab",
    "Technical Seminar",
]

for subject in subjects:

    faculty = get_faculty_for_subject(subject)

    print()
    print(f"{subject}")
    print(f"Eligible Faculty: {faculty}")


print()
print("=" * 70)
print("FACULTY → SUBJECT TEST")
print("=" * 70)

for faculty in ["MD", "SP", "SJK", "PSG"]:

    subjects = get_subjects_for_faculty(faculty)

    print()
    print(f"{faculty} -> {subjects}")