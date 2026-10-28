from data_loader import load_faculty_data
from pathlib import Path
import json


# ============================================================
# REFERENCE FACULTY-SUBJECT ALLOCATION
# ============================================================
# This is the existing project/reference allocation.
# It is NOT being presented as verified faculty expertise.
#
# If the web form later contains verified expertise,
# that information will take priority.


REFERENCE_FACULTY = {
    "Cloud Computing": ["PSG"],

    "Advanced Java Programming": ["RG"],

    "Microcontrollers & Applications": ["MD"],

    "Cellular Network": ["RGZ"],

    "VLSI Design": ["SP"],

    "Microcontrollers & VLSI Design Lab": [
        "MD",
        "SP",
    ],

    "Cellular Network Lab": ["PSG"],

    "Programme Elective Lab": ["RG"],

    "Machine Learning Tutorial": ["VDG"],

    "Machine Learning Practical": [
        "SJK",
        "VDG",
    ],

    "Technical Seminar": ["MD"],

    "Sustainability Development": ["GSK"],

    "Open Elective": ["GSK"],
}


# ============================================================
# HELPERS
# ============================================================

def _contains_subject(subject_list, subject):
    """
    Case-insensitive subject matching.
    """

    subject_lower = subject.strip().lower()

    return any(
        item.strip().lower() == subject_lower
        for item in subject_list
    )


def _get_saved_assignment(subject):
    """
    Read website-saved Semester V subject assignments.
    Saved website assignments override submitted expertise and reference defaults.
    """
    config_path = (
        Path(__file__).resolve().parent.parent
        / "data" / "input" / "sem_5" / "configuration.json"
    )
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []

    assignments = config.get("faculty_assignments", {})
    if not isinstance(assignments, dict):
        return []

    # Exact subject assignment first.
    value = assignments.get(subject)

    # Support the Open Elective/Sustainability Development naming used by the timetable data.
    if not value and subject == "Sustainability Development":
        value = assignments.get("Open Elective")
    if not value and subject == "Open Elective":
        value = assignments.get("Sustainability Development")

    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(code).strip() for code in value if str(code).strip()]


def _get_submitted_faculty(category, subject):
    """
    Returns faculty whose submitted form explicitly
    marks the subject as known expertise.
    """

    faculty_data = load_faculty_data()

    result = []

    for code, data in faculty_data.items():

        expertise = data.get(category, [])

        if _contains_subject(expertise, subject):
            result.append(code)

    return result


# ============================================================
# THEORY
# ============================================================

def get_faculty_for_theory(subject):
    """
    Priority:
        1. Submitted/known expertise
        2. Reference allocation if expertise is unspecified
    """

    saved = _get_saved_assignment(subject)
    if saved:
        return saved

    submitted = _get_submitted_faculty(
        "theory",
        subject
    )

    if submitted:
        return submitted

    return REFERENCE_FACULTY.get(
        subject,
        []
    )

# ============================================================
# TUTORIAL
# ============================================================

def get_faculty_for_tutorial(subject):
    """
    Priority:
        1. Submitted/known expertise
        2. Reference allocation
    """

    saved = _get_saved_assignment(subject)
    if saved:
        return saved

    submitted = _get_submitted_faculty(
        "tutorial",
        subject
    )

    if submitted:
        return submitted

    return REFERENCE_FACULTY.get(
        subject,
        []
    )

# ============================================================
# PRACTICAL
# ============================================================

def get_faculty_for_practical(subject):
    """
    Priority:
        1. Submitted/known expertise
        2. Reference allocation
    """

    saved = _get_saved_assignment(subject)
    if saved:
        return saved

    submitted = _get_submitted_faculty(
        "practical",
        subject
    )

    if submitted:
        return submitted

    return REFERENCE_FACULTY.get(
        subject,
        []
    )

# ============================================================
# GENERAL SUBJECT LOOKUP
# ============================================================

def get_faculty_for_subject(subject):
    """
    Returns faculty from theory, tutorial, or practical
    matching, depending on the subject.
    """

    result = set()

    result.update(
        get_faculty_for_theory(subject)
    )

    result.update(
        get_faculty_for_tutorial(subject)
    )

    result.update(
        get_faculty_for_practical(subject)
    )

    return sorted(result)


# ============================================================
# FACULTY → SUBJECTS
# ============================================================

def get_subjects_for_faculty(faculty_code):

    subjects = set()

    faculty_data = load_faculty_data()

    # --------------------------------------------------------
    # Submitted expertise
    # --------------------------------------------------------

    if faculty_code in faculty_data:

        data = faculty_data[faculty_code]

        for category in [
            "theory",
            "tutorial",
            "practical",
        ]:

            subjects.update(
                data.get(category, [])
            )

    # --------------------------------------------------------
    # Reference allocation
    # --------------------------------------------------------

    for subject, faculty_list in REFERENCE_FACULTY.items():

        if faculty_code in faculty_list:
            subjects.add(subject)

    return sorted(subjects)


# ============================================================
# DEBUG
# ============================================================

def print_faculty_expertise():

    print("=" * 60)
    print("FACULTY SUBJECT ALLOCATION")
    print("=" * 60)

    print(
        "\nNote:"
        "\nSubmitted expertise has priority."
        "\nReference allocation is used when expertise"
        "\nis not specified."
    )

    subjects = [
        "Cloud Computing",
        "Advanced Java Programming",
        "Microcontrollers & Applications",
        "Cellular Network",
        "VLSI Design",
        "Microcontrollers & VLSI Design Lab",
        "Cellular Network Lab",
        "Programme Elective Lab",
        "Machine Learning Tutorial",
        "Machine Learning Practical",
        "Technical Seminar",
        "Open Elective",
    ]

    print("\nSubject → Faculty\n")

    for subject in subjects:

        print(
            f"{subject}: "
            f"{get_faculty_for_subject(subject)}"
        )

    print("\nFaculty → Subjects\n")

    faculty_data = load_faculty_data()

    for code in faculty_data:

        print(
            f"{code}: "
            f"{get_subjects_for_faculty(code)}"
        )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":
    print_faculty_expertise()