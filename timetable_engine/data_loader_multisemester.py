from pathlib import Path
import json
import pandas as pd
import argparse


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SUBMISSIONS_DIR = (
    PROJECT_ROOT
    / "web_form"
    / "submissions"
)

WORKLOAD_FILE = (
    PROJECT_ROOT
    / "data"
    / "TE_SemV_Reconstructed_Workload.xlsx"
)


# ============================================================
# SCHEDULING CONFIGURATION
# ============================================================

SCHEDULING_RULES = {

    "working_days": [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
    ],

    "periods_per_day": 6,

    "periods": {

        1: {
            "start": "08:45",
            "end": "09:45",
        },

        2: {
            "start": "09:45",
            "end": "10:45",
        },

        3: {
            "start": "11:00",
            "end": "12:00",
        },

        4: {
            "start": "12:00",
            "end": "13:00",
        },

        5: {
            "start": "13:45",
            "end": "14:45",
        },

        6: {
            "start": "14:45",
            "end": "15:45",
        },
    },

    "short_break": {
        "start": "10:45",
        "end": "11:00",
    },

    "lunch_break": {
        "start": "13:00",
        "end": "13:45",
    },

    "theory_duration": 1,

    "tutorial_duration": 1,

    "practical_duration": 2,
}


# ============================================================
# FIND LATEST SUBMISSION
# ============================================================

def find_latest_submission():

    if not SUBMISSIONS_DIR.exists():

        raise FileNotFoundError(
            f"Submission directory not found:\n"
            f"{SUBMISSIONS_DIR}"
        )

    submissions = [

        folder

        for folder in SUBMISSIONS_DIR.iterdir()

        if (
            folder.is_dir()
            and
            (folder / "submission.json").exists()
        )
    ]

    if not submissions:

        raise FileNotFoundError(
            "No submitted timetable form was found."
        )

    return max(
        submissions,
        key=lambda folder: (
            folder / "submission.json"
        ).stat().st_mtime
    )


# ============================================================
# LOAD SUBMISSION
# ============================================================

def load_submission():

    submission_folder = find_latest_submission()

    submission_file = (
        submission_folder
        / "submission.json"
    )

    with open(
        submission_file,
        "r",
        encoding="utf-8-sig"
    ) as file:

        return json.load(file)


# ============================================================
# FACULTY DATA
# ============================================================

def load_faculty_data():

    submission = load_submission()

    faculty_data = {}

    for faculty in submission.get(
        "faculty",
        []
    ):

        code = str(
            faculty.get(
                "code",
                ""
            )
        ).strip()

        name = str(
            faculty.get(
                "name",
                ""
            )
        ).strip()

        if not code:
            continue

        faculty_data[code] = {

            "name":
                name or code,

            "theory":
                faculty.get(
                    "theory",
                    []
                ) or [],

            "tutorial":
                faculty.get(
                    "tutorial",
                    []
                ) or [],

            "practical":
                faculty.get(
                    "practical",
                    []
                ) or [],
        }

    return faculty_data


# ============================================================
# FACULTY HELPERS
# ============================================================

def get_faculty_for_theory(subject):

    result = []

    for code, data in load_faculty_data().items():

        if subject in data["theory"]:

            result.append(code)

    return result


def get_faculty_for_tutorial(subject):

    result = []

    for code, data in load_faculty_data().items():

        if subject in data["tutorial"]:

            result.append(code)

    return result


def get_faculty_for_practical(subject):

    result = []

    for code, data in load_faculty_data().items():

        if subject in data["practical"]:

            result.append(code)

    return result


def get_faculty_for_subject(subject):

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


def get_subjects_for_faculty(faculty_code):

    faculty = load_faculty_data()

    if faculty_code not in faculty:

        return []

    data = faculty[faculty_code]

    return sorted(
        set(
            data["theory"]
            +
            data["tutorial"]
            +
            data["practical"]
        )
    )


# ============================================================
# BATCH DATA
# ============================================================

def load_batch_data():

    submission = load_submission()

    batches = {}

    for batch in submission.get(
        "batches",
        []
    ):

        code = str(
            batch.get(
                "code",
                ""
            )
        ).strip()

        if not code:
            continue

        try:

            students = int(
                batch.get(
                    "students",
                    0
                )
            )

        except (
            ValueError,
            TypeError
        ):

            students = 0

        batches[code] = {

            "students":
                students,

            "elective":
                str(
                    batch.get(
                        "elective",
                        ""
                    )
                ).strip(),
        }

    return batches


# ============================================================
# ACADEMIC DATA
# ============================================================

def load_academic_data():

    submission = load_submission()

    return submission.get(
        "academic",
        {}
    )


# ============================================================
# ROOM DATA
# ============================================================

def load_room_data():

    submission = load_submission()

    return submission.get(
        "rooms",
        []
    )


# ============================================================
# WORKLOAD DATA
#
# Excel is the source of workload information.
# ============================================================

def load_workload():

    if not WORKLOAD_FILE.exists():

        raise FileNotFoundError(
            f"Workload file not found:\n"
            f"{WORKLOAD_FILE}"
        )

    df = pd.read_excel(
        WORKLOAD_FILE
    )

    if df.empty:

        raise ValueError(
            "Workload Excel file is empty."
        )

    # --------------------------------------------------------
    # Normalize column names
    # --------------------------------------------------------

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    required_columns = [

        "Course Code",

        "Subject",

        "Theory (hrs)",

        "Tutorial (hrs)",

        "Practical (hrs)",

        "Credits",

        "Session Packaging",
    ]

    missing_columns = [

        column

        for column in required_columns

        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            "Workload file is missing required "
            "columns:\n"
            +
            "\n".join(
                f"- {column}"
                for column in missing_columns
            )
        )

    # --------------------------------------------------------
    # Remove TOTAL row
    # --------------------------------------------------------

    df = df[
        df["Course Code"].notna()
    ].copy()

    df = df[
        df["Course Code"].astype(str).str.upper()
        != "TOTAL"
    ].copy()

    # --------------------------------------------------------
    # Normalize text columns
    # --------------------------------------------------------

    df["Course Code"] = (
        df["Course Code"]
        .astype(str)
        .str.strip()
    )

    df["Subject"] = (
        df["Subject"]
        .astype(str)
        .str.strip()
    )

    df["Session Packaging"] = (
        df["Session Packaging"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # Normalize numeric columns
    # --------------------------------------------------------

    numeric_columns = [

        "Theory (hrs)",

        "Tutorial (hrs)",

        "Practical (hrs)",

        "Credits",
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        ).fillna(0)

    # --------------------------------------------------------
    # Build clean workload records
    # --------------------------------------------------------

    workload_records = []

    for _, row in df.iterrows():

        workload_records.append({

            "course_code":
                row["Course Code"],

            "subject":
                row["Subject"],

            "theory_hours":
                int(row["Theory (hrs)"]),

            "tutorial_hours":
                int(row["Tutorial (hrs)"]),

            "practical_hours":
                int(row["Practical (hrs)"]),

            "credits":
                float(row["Credits"]),

            "session_packaging":
                row["Session Packaging"],
        })

    # --------------------------------------------------------
    # Validate workload
    # --------------------------------------------------------

    for record in workload_records:

        total_hours = (

            record["theory_hours"]

            +

            record["tutorial_hours"]

            +

            record["practical_hours"]
        )

        if total_hours <= 0:

            raise ValueError(
                f"Subject has zero workload: "
                f"{record['subject']}"
            )

    return {

        "dataframe":
            df,

        "records":
            workload_records,

        "total_theory_hours":
            sum(
                record["theory_hours"]
                for record in workload_records
            ),

        "total_tutorial_hours":
            sum(
                record["tutorial_hours"]
                for record in workload_records
            ),

        "total_practical_hours":
            sum(
                record["practical_hours"]
                for record in workload_records
            ),

        "total_weekly_hours":
            sum(
                record["theory_hours"]
                +
                record["tutorial_hours"]
                +
                record["practical_hours"]

                for record in workload_records
            ),
    }


# ============================================================
# SUBJECT DEFINITIONS
#
# IMPORTANT:
# Workload values now come from Excel.
#
# These definitions currently contain only scheduling
# structure that is NOT present in the workload Excel:
#
# - batch groups
# - elective groups
# - practical groups
#
# We will make these dynamic in the next phase.
# ============================================================

SUBJECT_DEFINITIONS = {

    "Microcontrollers & Applications": {

        "code": "PCC-301-ETC",

        "theory_group": "COMMON_TE",

        "batch_groups": [
            "T1",
            "T2",
            "T3",
        ],
    },

    "Cellular Network": {

        "code": "PCC-302-ETC",

        "theory_group": "COMMON_TE",

        "batch_groups": [
            "T1",
            "T2",
            "T3",
        ],
    },

    "VLSI Design": {

        "code": "PCC-303-ETC",

        "theory_group": "COMMON_TE",

        "batch_groups": [
            "T1",
            "T2",
            "T3",
        ],
    },

    "Microcontrollers & VLSI Design Lab": {

        "code": "PCC-304-ETC",

        "practical_groups": [
            "T1",
            "T2",
            "T3",
        ],

        "practical_blocks": 2,
    },

    "Cellular Network Lab": {

        "code": "PCC-305-ETC",

        "practical_groups": [
            "T1",
            "T2",
            "T3",
        ],

        "practical_blocks": 1,
    },

    "Programme Elective I": {

        "code": "PEC-321-ETC",

        "elective_groups": {

            "Cloud Computing": [
                "T1",
                "T2",
            ],

            "Advanced Java Programming": [
                "T3",
            ],
        },
    },

    "Programme Elective Lab": {

        "code": "PEC-322-ETC",

        "elective_groups": {

            "Cloud Computing": [
                "T1",
                "T2",
            ],

            "Advanced Java Programming": [
                "T3",
            ],
        },

        "practical_blocks": 1,
    },

    "Machine Learning": {

        "code": "MDM-331-ETC",

        "tutorial_group":
            "COMMON_TE",

        "practical_groups": [
            "T1",
            "T2",
            "T3",
        ],

        "practical_blocks": 1,
    },

    "Open Elective": {

        "code": "OLE-341-ETC",

        "theory_group":
            "COMMON_TE",

        "batch_groups": [
            "T1",
            "T2",
            "T3",
        ],

        "elective_name":
            "Sustainability Development",
    },

    "Technical Seminar": {

        "code": "ELC-342-ETC",

        "practical_groups": [
            "T1",
            "T2",
            "T3",
        ],

        "practical_blocks": 1,
    },
}


# ============================================================
# TEACHING GROUPS
# ============================================================

TEACHING_GROUPS = {

    "COMMON_TE":
        [
            "T1",
            "T2",
            "T3",
        ],

    "CLOUD":
        [
            "T1",
            "T2",
        ],

    "AJP":
        [
            "T3",
        ],

    "T1":
        [
            "T1",
        ],

    "T2":
        [
            "T2",
        ],

    "T3":
        [
            "T3",
        ],
}


# ============================================================
# SUBJECT BATCH STRUCTURE
# ============================================================

def build_subject_batches():

    subject_batches = {}

    for subject, definition in SUBJECT_DEFINITIONS.items():

        batches = []

        if "batch_groups" in definition:

            batches.extend(
                definition[
                    "batch_groups"
                ]
            )

        if "practical_groups" in definition:

            batches.extend(
                definition[
                    "practical_groups"
                ]
            )

        if "theory_group" in definition:

            batches.extend(
                TEACHING_GROUPS[
                    definition[
                        "theory_group"
                    ]
                ]
            )

        if "tutorial_group" in definition:

            batches.extend(
                TEACHING_GROUPS[
                    definition[
                        "tutorial_group"
                    ]
                ]
            )

        if "elective_groups" in definition:

            for group_batches in definition[
                "elective_groups"
            ].values():

                batches.extend(
                    group_batches
                )

        subject_batches[subject] = sorted(
            set(batches)
        )

    return subject_batches


SUBJECT_BATCHES = (
    build_subject_batches()
)


# ============================================================
# ELECTIVE GROUPS
# ============================================================

ELECTIVE_GROUPS = {

    "Programme Elective I": {

        "CLOUD":
            [
                "T1",
                "T2",
            ],

        "AJP":
            [
                "T3",
            ],
    },

    "Programme Elective Lab": {

        "T1":
            [
                "T1",
            ],

        "T2":
            [
                "T2",
            ],

        "T3":
            [
                "T3",
            ],
    },
}


# ============================================================
# WORKLOAD LOOKUP
# ============================================================

def get_workload_record(
    subject,
    workload,
):

    for record in workload["records"]:

        if record["subject"] == subject:

            return record

    return None


# ============================================================
# SESSION CREATION HELPER
# ============================================================

def make_session(
    session_id,
    subject,
    session_type,
    duration,
    group,
    batches,
    elective=None,
):

    session = {

        "id":
            session_id,

        "subject":
            subject,

        "type":
            session_type,

        "duration":
            duration,

        "group":
            group,

        "batch":
            batches,
    }

    if elective:

        session["elective"] = elective

    return session


# ============================================================
# COMMON THEORY SESSION CREATOR
# ============================================================

def create_common_theory_sessions(
    subject,
    hours,
    group="COMMON_TE",
):

    sessions = []

    batches = (
        TEACHING_GROUPS[group]
    )

    for index in range(
        1,
        hours + 1
    ):

        sessions.append(
            make_session(

                session_id=(
                    f"{subject}_T{index}"
                ),

                subject=subject,

                session_type="theory",

                duration=
                    SCHEDULING_RULES[
                        "theory_duration"
                    ],

                group=group,

                batches=batches.copy(),
            )
        )

    return sessions


# ============================================================
# TUTORIAL SESSION CREATOR
# ============================================================

def create_common_tutorial_sessions(
    subject,
    hours,
    group="COMMON_TE",
):

    sessions = []

    batches = (
        TEACHING_GROUPS[group]
    )

    for index in range(
        1,
        hours + 1
    ):

        sessions.append(
            make_session(

                session_id=(
                    f"{subject}_TUT_{index}"
                ),

                subject=subject,

                session_type="tutorial",

                duration=
                    SCHEDULING_RULES[
                        "tutorial_duration"
                    ],

                group=group,

                batches=batches.copy(),
            )
        )

    return sessions


# ============================================================
# ELECTIVE THEORY SESSION CREATOR
# ============================================================

def create_elective_theory_sessions(
    subject,
    hours,
    elective_groups,
):

    sessions = []

    for elective, batches in (
        elective_groups.items()
    ):

        if batches == [
            "T1",
            "T2",
        ]:

            group_name = "CLOUD"

        else:

            group_name = "AJP"

        for index in range(
            1,
            hours + 1
        ):

            sessions.append(
                make_session(

                    session_id=(
                        f"{subject}_"
                        f"{elective.replace(' ', '_')}_"
                        f"{index}"
                    ),

                    subject=subject,

                    session_type="theory",

                    duration=
                        SCHEDULING_RULES[
                            "theory_duration"
                        ],

                    group=group_name,

                    batches=batches.copy(),

                    elective=elective,
                )
            )

    return sessions


# ============================================================
# PRACTICAL SESSION CREATOR
# ============================================================

def create_practical_sessions(
    subject,
    blocks,
    groups,
):

    sessions = []

    for block in range(
        1,
        blocks + 1
    ):

        for batch in groups:

            elective = None

            if subject == (
                "Programme Elective Lab"
            ):

                if batch in [
                    "T1",
                    "T2",
                ]:

                    elective = (
                        "Cloud Computing"
                    )

                elif batch == "T3":

                    elective = (
                        "Advanced Java Programming"
                    )

            sessions.append(
                make_session(

                    session_id=(
                        f"{subject}_"
                        f"{block}_"
                        f"{batch}"
                    ),

                    subject=subject,

                    session_type="practical",

                    duration=
                        SCHEDULING_RULES[
                            "practical_duration"
                        ],

                    group=batch,

                    batches=[
                        batch
                    ],

                    elective=elective,
                )
            )

    return sessions


# ============================================================
# MASTER SESSION GENERATOR
# ============================================================

def create_sessions(
    workload,
):

    sessions = []

    # --------------------------------------------------------
    # Process subjects using workload Excel.
    # --------------------------------------------------------

    for subject, definition in (
        SUBJECT_DEFINITIONS.items()
    ):

        workload_record = (
            get_workload_record(
                subject,
                workload
            )
        )

        if workload_record is None:

            raise ValueError(
                f"Subject '{subject}' "
                f"was not found in workload Excel."
            )

        theory_hours = (
            workload_record[
                "theory_hours"
            ]
        )

        tutorial_hours = (
            workload_record[
                "tutorial_hours"
            ]
        )

        practical_hours = (
            workload_record[
                "practical_hours"
            ]
        )

        # ----------------------------------------------------
        # COMMON THEORY
        # ----------------------------------------------------

        if theory_hours > 0:

            if (
                "theory_group"
                in definition
            ):

                sessions.extend(
                    create_common_theory_sessions(
                        subject,
                        theory_hours,
                        definition[
                            "theory_group"
                        ],
                    )
                )

        # ----------------------------------------------------
        # ELECTIVE THEORY
        # ----------------------------------------------------

        if theory_hours > 0:

            if (
                "elective_groups"
                in definition
            ):

                sessions.extend(
                    create_elective_theory_sessions(
                        subject,
                        theory_hours,
                        definition[
                            "elective_groups"
                        ],
                    )
                )

        # ----------------------------------------------------
        # COMMON TUTORIAL
        # ----------------------------------------------------

        if tutorial_hours > 0:

            if (
                "tutorial_group"
                in definition
            ):

                sessions.extend(
                    create_common_tutorial_sessions(
                        subject,
                        tutorial_hours,
                        definition[
                            "tutorial_group"
                        ],
                    )
                )

        # ----------------------------------------------------
        # PRACTICAL
        # ----------------------------------------------------

        if practical_hours > 0:

            # Programme Elective Lab uses elective groups
            # rather than the generic practical_groups key.
            # Each batch gets one 2-hour lab session.
            if (
                subject == "Programme Elective Lab"
                and "elective_groups" in definition
            ):

                for elective, groups in definition[
                    "elective_groups"
                ].items():

                    for batch in groups:

                        sessions.append(
                            make_session(
                                session_id=(
                                    f"{subject}_"
                                    f"1_{batch}"
                                ),
                                subject=subject,
                                session_type="practical",
                                duration=SCHEDULING_RULES[
                                    "practical_duration"
                                ],
                                group=batch,
                                batches=[batch],
                                elective=elective,
                            )
                        )

            elif "practical_groups" in definition:

                practical_blocks = int(
                    definition.get(
                        "practical_blocks",
                        practical_hours // 2
                    )
                )

                sessions.extend(
                    create_practical_sessions(
                        subject,
                        practical_blocks,
                        definition[
                            "practical_groups"
                        ],
                    )
                )

    return sessions


# ============================================================
# VALIDATE GENERATED SESSIONS
# ============================================================

def validate_sessions(
    sessions,
    batches,
    workload,
):

    errors = []

    # --------------------------------------------------------
    # SESSION COUNT
    # --------------------------------------------------------

    if len(sessions) != 37:

        errors.append(
            f"Expected 37 sessions, "
            f"but generated {len(sessions)}."
        )

    # --------------------------------------------------------
    # WORKLOAD TOTAL
    # --------------------------------------------------------

    if workload[
        "total_weekly_hours"
    ] != 28:

        errors.append(
            "Expected 28 weekly workload hours, "
            f"but found "
            f"{workload['total_weekly_hours']}."
        )

    # --------------------------------------------------------
    # REQUIRED BATCHES
    # --------------------------------------------------------

    required_batches = {
        "T1",
        "T2",
        "T3",
    }

    available_batches = set(
        batches.keys()
    )

    missing_batches = (
        required_batches
        -
        available_batches
    )

    if missing_batches:

        errors.append(
            "Missing required batches: "
            +
            ", ".join(
                sorted(
                    missing_batches
                )
            )
        )

    # --------------------------------------------------------
    # SESSION STRUCTURE
    # --------------------------------------------------------

    for session in sessions:

        required_keys = [

            "id",

            "subject",

            "type",

            "duration",

            "group",

            "batch",
        ]

        for key in required_keys:

            if key not in session:

                errors.append(
                    f"Session "
                    f"{session.get('id', 'UNKNOWN')} "
                    f"is missing '{key}'."
                )

        if session.get(
            "duration"
        ) not in [
            1,
            2,
        ]:

            errors.append(
                f"Invalid duration in "
                f"{session.get('id', 'UNKNOWN')}: "
                f"{session.get('duration')}"
            )

        if session.get(
            "type"
        ) == "practical":

            if session.get(
                "duration"
            ) != 2:

                errors.append(
                    f"Practical session "
                    f"{session.get('id')} "
                    f"must be 2 hours."
                )

        for batch in session.get(
            "batch",
            []
        ):

            if batch not in batches:

                errors.append(
                    f"Session "
                    f"{session.get('id')} "
                    f"references unknown "
                    f"batch {batch}."
                )

    return errors


# ============================================================
# MULTI-SEMESTER INPUT LAYER
# ============================================================

INPUT_ROOT = PROJECT_ROOT / "data" / "input"
SUPPORTED_SEMESTERS = [3, 4, 5, 6, 7, 8]


def get_semester_input_dir(semester):
    semester = int(semester)

    if semester not in SUPPORTED_SEMESTERS:
        raise ValueError(
            f"Unsupported semester: {semester}. "
            f"Supported semesters: {SUPPORTED_SEMESTERS}"
        )

    semester_dir = INPUT_ROOT / f"sem_{semester}"

    if not semester_dir.exists():
        raise FileNotFoundError(
            f"Semester input directory not found:\n{semester_dir}"
        )

    return semester_dir


def load_json_file(path, default=None, required=False):
    if not path.exists():
        if required:
            raise FileNotFoundError(
                f"Required input file not found:\n{path}"
            )
        return default

    with open(path, "r", encoding="utf-8-sig") as file:
        return json.load(file)


def load_semester_subjects(semester):
    semester_dir = get_semester_input_dir(semester)

    return load_json_file(
        semester_dir / "subjects.json",
        required=True
    )


def workload_from_subjects_json(semester):
    """
    Convert the semester subjects.json format into the same workload
    structure used by the existing Sem-V session engine.
    """

    subjects = load_semester_subjects(semester)

    records = []

    for course_code, info in subjects.items():

        record = {
            "course_code": str(course_code).strip(),
            "subject": str(
                info.get("subject", course_code)
            ).strip(),
            "theory_hours": int(
                info.get("theory_hours", 0)
            ),
            "tutorial_hours": int(
                info.get("tutorial_hours", 0)
            ),
            "practical_hours": int(
                info.get("practical_hours", 0)
            ),
            "credits": float(
                info.get("credits", 0)
            ),
            "session_packaging": str(
                info.get("session_packaging", "")
            ).strip(),
        }

        if (
            record["theory_hours"]
            + record["tutorial_hours"]
            + record["practical_hours"]
            <= 0
        ):
            raise ValueError(
                f"Subject has zero workload: "
                f"{record['subject']}"
            )

        records.append(record)

    if not records:
        raise ValueError(
            f"No subjects found for Semester {semester}."
        )

    df = pd.DataFrame(records)

    return {
        "dataframe": df,
        "records": records,
        "total_theory_hours": sum(
            r["theory_hours"] for r in records
        ),
        "total_tutorial_hours": sum(
            r["tutorial_hours"] for r in records
        ),
        "total_practical_hours": sum(
            r["practical_hours"] for r in records
        ),
        "total_weekly_hours": sum(
            r["theory_hours"]
            + r["tutorial_hours"]
            + r["practical_hours"]
            for r in records
        ),
    }


def load_optional_semester_resource(
    semester,
    filename,
    default
):
    semester_dir = get_semester_input_dir(semester)

    return load_json_file(
        semester_dir / filename,
        default=default
    )


# ============================================================
# GENERIC DATA FOR SEMESTERS WITHOUT RESOURCE INFORMATION
# ============================================================

def build_generic_batches(semester, subjects):
    """
    Load explicitly configured semester batches.

    Supports both a dictionary keyed by batch code and the nested
    schema {"configured": true, "batches": [{"code": "S1", ...}]}.
    Returns (normalized_batches, batch_data_complete).
    """
    raw = load_optional_semester_resource(
        semester,
        "batches.json",
        {}
    )

    fallback = {
        "ALL": {
            "students": 0,
            "elective": ""
        }
    }

    if not raw or not isinstance(raw, (dict, list)):
        return fallback, False

    if isinstance(raw, dict):
        if raw.get("configured") is False:
            return fallback, False

        # New/standard nested schema: metadata plus a list of batches.
        if "batches" in raw:
            if raw.get("configured") is not True:
                return fallback, False
            raw_batches = raw.get("batches")
        else:
            # Legacy schema keyed directly by batch code.
            raw_batches = [
                {"code": code, **details}
                for code, details in raw.items()
                if isinstance(details, dict)
                and code not in {
                    "configured", "total_students",
                    "number_of_batches", "notes"
                }
            ]
    else:
        raw_batches = raw

    if not isinstance(raw_batches, list) or not raw_batches:
        return fallback, False

    normalized = {}
    try:
        for item in raw_batches:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code", "")).strip()
            students = int(item.get("students", 0))
            if not code or code.upper() == "ALL" or students <= 0:
                continue
            normalized[code] = {
                "students": students,
                "elective": str(item.get("elective", "")).strip()
            }
    except (TypeError, ValueError):
        return fallback, False

    if not normalized:
        return fallback, False

    # Avoid silently accepting duplicate codes or inconsistent metadata.
    codes = [str(item.get("code", "")).strip()
             for item in raw_batches if isinstance(item, dict)]
    if len([c for c in codes if c]) != len(set(c for c in codes if c)):
        return normalized, False

    if isinstance(raw, dict):
        declared_count = raw.get("number_of_batches")
        declared_total = raw.get("total_students")
        if declared_count is not None and int(declared_count) != len(normalized):
            return normalized, False
        if declared_total is not None and int(declared_total) != sum(
            item["students"] for item in normalized.values()
        ):
            return normalized, False

    return normalized, True

def create_generic_sessions(subjects, batches):
    """Create workload-driven sessions for generic semesters."""
    sessions = []
    batch_codes = list(batches.keys()) or ["ALL"]

    for course_code, info in subjects.items():
        # Excluded subjects remain in subjects.json but create no sessions.
        # Missing "included" means True for backward compatibility.
        if info.get("included", True) is False:
            continue

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




def validate_generic_sessions(
    sessions,
    workload
):
    errors = []

    for session in sessions:

        required_keys = [
            "id",
            "subject",
            "type",
            "duration",
            "group",
            "batch"
        ]

        for key in required_keys:
            if key not in session:
                errors.append(
                    f"Session "
                    f"{session.get('id', 'UNKNOWN')} "
                    f"is missing '{key}'."
                )

        if session.get("duration") not in [1, 2]:
            errors.append(
                f"Invalid duration in "
                f"{session.get('id', 'UNKNOWN')}: "
                f"{session.get('duration')}"
            )

        if session.get("type") == "practical":
            if session.get("duration") != 2:
                errors.append(
                    f"Practical session "
                    f"{session.get('id')} "
                    f"has duration "
                    f"{session.get('duration')}h."
                )

    return errors


# ============================================================
# SEM-V RESOURCE LOADING
# ============================================================

def load_sem_v_resources():
    """
    Preserve the existing proven Sem-V web-form resource logic.
    """

    submission = load_submission()

    faculty = load_faculty_data()
    batches = load_batch_data()
    academic = load_academic_data()
    rooms = load_room_data()

    return submission, faculty, batches, academic, rooms


# ============================================================
# MULTI-SEMESTER DATA LOADER
# ============================================================

def determine_readiness_status(
    semester_info,
    subjects,
    batch_data_complete,
    faculty_data_complete,
    room_data_complete,
    configuration_data_complete
):
    """
    Determine whether a semester has enough information
    to proceed toward timetable generation.
    """

    semester_status = str(
        semester_info.get("status", "")
    ).strip().lower()

    # No curriculum data has been supplied yet.
    if semester_status == "data_pending":
        return {
            "status": "DATA PENDING",
            "ready_for_generation": False,
            "message": "Curriculum data is not available yet."
        }

    # Curriculum exists, but one or more required resources
    # are still missing.
    if not subjects:
        return {
            "status": "DATA PENDING",
            "ready_for_generation": False,
            "message": "Curriculum data is incomplete."
        }

    missing = []

    if not batch_data_complete:
        missing.append("Batches")

    if not faculty_data_complete:
        missing.append("Faculty")

    if not room_data_complete:
        missing.append("Rooms")

    if not configuration_data_complete:
        missing.append("Configuration")

    if missing:
        return {
            "status": "INPUT INCOMPLETE",
            "ready_for_generation": False,
            "message": "Missing: " + ", ".join(missing)
        }

    return {
        "status": "READY FOR GENERATION",
        "ready_for_generation": True,
        "message": "All required semester inputs are available."
    }

def load_semester_data(semester):
    semester = int(semester)

    semester_dir = get_semester_input_dir(semester)

    semester_info = load_json_file(
        semester_dir / "semester.json",
        required=True
    )

    # Semesters marked as data_pending do not yet have
    # curriculum input files.
    if semester_info.get("status") == "data_pending":
        return {
            "semester": semester_info,
            "semester_number": semester,
            "submission": {},
            "faculty": {},
            "batches": {},
            "academic": {},
            "rooms": {},
            "subjects": {},
            "workload": {
                "total_theory_hours": 0,
                "total_tutorial_hours": 0,
                "total_practical_hours": 0,
                "total_weekly_hours": 0,
                "total_hours": 0
            },
            "sessions": [],
            "subject_definitions": {},
            "subject_batches": {},
            "teaching_groups": {},
            "elective_groups": {},
            "scheduling_rules": SCHEDULING_RULES,
            "resource_data_complete": False,
            "mode": "data_pending"
        }

    subjects = load_semester_subjects(semester)

    # --------------------------------------------------------
    # SEM-V
    #
    # Keep the existing detailed real-data behavior.
    # --------------------------------------------------------

    if semester == 5:

        (
            submission,
            faculty,
            batches,
            academic,
            rooms
        ) = load_sem_v_resources()

        workload = workload_from_subjects_json(5)

        # Use the existing Sem-V definitions/session engine.
        sessions = create_sessions(workload)

        validation_errors = validate_sessions(
            sessions,
            batches,
            workload
        )

        if validation_errors:
            raise ValueError(
                "SEMESTER 5 DATA LOADER VALIDATION FAILED:\n"
                + "\n".join(
                    f"- {error}"
                    for error in validation_errors
                )
            )

        return {
            "semester": semester_info,
            "semester_number": semester,
            "submission": submission,
            "faculty": faculty,
            "batches": batches,
            "academic": academic,
            "rooms": rooms,
            "subjects": subjects,
            "workload": workload,
            "sessions": sessions,
            "subject_definitions": SUBJECT_DEFINITIONS,
            "subject_batches": SUBJECT_BATCHES,
            "teaching_groups": TEACHING_GROUPS,
            "elective_groups": ELECTIVE_GROUPS,
            "scheduling_rules": SCHEDULING_RULES,

            # Sem-V has complete real resource information.
            "batch_data_complete": True,
            "faculty_data_complete": True,
            "room_data_complete": True,
            "configuration_data_complete": True,
            "resource_data_complete": True,
            "ready_for_generation": True,
            "readiness_status": "READY FOR GENERATION",
            "readiness_message": (
                "All required semester inputs are available."
            ),

            "mode": "detailed_sem_v"
        }

    # --------------------------------------------------------
    # OTHER SEMESTERS
    #
    # Use only information actually supplied in their
    # semester folders. Missing resources remain missing.
    # --------------------------------------------------------

    workload = workload_from_subjects_json(
        semester
    )

    faculty = load_optional_semester_resource(
        semester,
        "faculty.json",
        {}
    )

    academic = load_optional_semester_resource(
        semester,
        "academic.json",
        {}
    )

    rooms = load_optional_semester_resource(
        semester,
        "rooms.json",
        {}
    )

    batches, batch_data_complete = build_generic_batches(
        semester,
        subjects
    )

    sessions = create_generic_sessions(
        subjects,
        batches
    )

    validation_errors = validate_generic_sessions(
        sessions,
        workload
    )

    if validation_errors:
        raise ValueError(
            f"SEMESTER {semester} DATA LOADER "
            f"VALIDATION FAILED:\n"
            + "\n".join(
                f"- {error}"
                for error in validation_errors
            )
        )

    # --------------------------------------------------------
    # READINESS STATUS
    # --------------------------------------------------------

    configuration_data = load_optional_semester_resource(
        semester,
        "configuration.json",
        {}
    )

    configuration_data_complete = bool(
        configuration_data
        and configuration_data.get("configured") is True
    )

    readiness = determine_readiness_status(
        semester_info,
        subjects,
        batch_data_complete,
        bool(faculty),
        bool(rooms),
        configuration_data_complete
    )

    return {
        "semester": semester_info,
        "semester_number": semester,
        "submission": {},
        "faculty": faculty,
        "batches": batches,
        "academic": academic,
        "rooms": rooms,
        "subjects": subjects,
        "workload": workload,
        "sessions": sessions,
        "subject_definitions": {},
        "subject_batches": {},
        "teaching_groups": {},
        "elective_groups": {},
        "scheduling_rules": SCHEDULING_RULES,
        "batch_data_complete": batch_data_complete,
        "faculty_data_complete": bool(faculty),
        "room_data_complete": bool(rooms),
        "configuration_data_complete": configuration_data_complete,
        "resource_data_complete": bool(
            batch_data_complete
            and faculty
            and rooms
            and configuration_data_complete
        ),
        "ready_for_generation": readiness["ready_for_generation"],
        "readiness_status": readiness["status"],
        "readiness_message": readiness["message"],
        "mode": "workload_only"
    }


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def load_te_sem_v_data():
    """
    Existing Sem-V entry point.
    """

    return load_semester_data(5)


def load_data(semester=5):
    """
    General entry point for the timetable system.

    Examples:
        load_data(3)
        load_data(4)
        load_data(5)
        load_data(6)
    """

    return load_semester_data(
        semester
    )


# ============================================================
# DEBUG / TEST
# ============================================================

def print_loader_summary(data):

    semester_info = data["semester"]
    workload = data["workload"]

    semester_number = data[
        "semester_number"
    ]

    print()
    print("=" * 70)
    print("AI TIMETABLE MULTI-SEMESTER DATA LOADER")
    print("=" * 70)

    print(
        f"Semester       : {semester_number}"
    )

    print(
        f"Label          : "
        f"{semester_info.get('label', '')}"
    )

    print(
        f"Mode           : {data['mode']}"
    )

    print()
    print(
        f"Subjects       : "
        f"{len(data['subjects'])}"
    )

    print()
    print("Workload:")
    print(
        "Theory         :",
        workload["total_theory_hours"]
    )
    print(
        "Tutorial       :",
        workload["total_tutorial_hours"]
    )
    print(
        "Practical      :",
        workload["total_practical_hours"]
    )
    print(
        "Total          :",
        workload["total_weekly_hours"]
    )

    print()
    print(
        f"Sessions       : "
        f"{len(data['sessions'])}"
    )

    print()
    print("Resources:")
    print(
        "Faculty        :",
        "Available"
        if data["faculty"]
        else "Not provided"
    )
    print(
        "Batches        :",
        "Available"
        if data.get("batch_data_complete", False)
        else "Not provided"
    )
    print(
        "Rooms          :",
        "Available"
        if data["rooms"]
        else "Not provided"
    )

    print()
    print("=" * 70)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "ENTC AI Timetable "
            "Multi-Semester Data Loader"
        )
    )

    parser.add_argument(
        "--semester",
        type=int,
        default=5,
        choices=[3, 4, 5, 6, 7, 8],
        help="Semester to load. Default: 5"
    )

    args = parser.parse_args()

    data = load_semester_data(
        args.semester
    )

    print_loader_summary(data)

    print()
    print("=" * 70)

    if args.semester == 5:
        print(
            "SEMESTER 5 VALIDATION PASSED"
        )
    else:
        print(
            f"SEMESTER {args.semester} "
            "INPUT VALIDATION PASSED"
        )

    print(
        f"Total sessions: "
        f"{len(data['sessions'])}"
    )

    print(
        f"Total workload: "
        f"{data['workload']['total_weekly_hours']} "
        f"hours/week"
    )

    print("=" * 70)




