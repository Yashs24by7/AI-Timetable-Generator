# ============================================================
# FACULTY SUBJECT SELECTION DATABASE
# ============================================================
#
# Faculty will select subjects according to their expertise.
# This file defines the subjects available for selection.
#
# Faculty names/codes are NOT hard-coded here.
# ============================================================


AVAILABLE_SUBJECTS = {

    "Theory": [
        "Microcontrollers & Applications",
        "Cellular Network",
        "VLSI Design",
        "Programme Elective I",
        "Machine Learning",
        "Open Elective",
    ],

    "Tutorial": [
        "Machine Learning",
    ],

    "Practical": [
        "Microcontrollers & VLSI Design Lab",
        "Cellular Network Lab",
        "Programme Elective Lab",
        "Machine Learning",
        "Technical Seminar",
    ],
}


def get_all_subjects():
    """Return all unique subjects available for faculty selection."""

    subjects = []

    for category in AVAILABLE_SUBJECTS.values():
        for subject in category:
            if subject not in subjects:
                subjects.append(subject)

    return subjects


def get_subjects_by_type(subject_type):
    """Return subjects belonging to a specific category."""

    return AVAILABLE_SUBJECTS.get(subject_type, [])


def print_subjects():

    print("=" * 70)
    print("FACULTY SUBJECT SELECTION DATABASE")
    print("=" * 70)

    for subject_type, subjects in AVAILABLE_SUBJECTS.items():

        print()
        print(subject_type)
        print("-" * 70)

        for number, subject in enumerate(subjects, start=1):
            print(f"{number}. {subject}")


if __name__ == "__main__":
    print_subjects()