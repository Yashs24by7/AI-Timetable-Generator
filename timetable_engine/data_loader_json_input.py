from pathlib import Path
import json
import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "data" / "input"

WORKLOAD_FILE = (
    PROJECT_ROOT
    / "data"
    / "TE_SemV_Reconstructed_Workload.xlsx"
)

SUBMISSIONS_DIR = (
    PROJECT_ROOT
    / "web_form"
    / "submissions"
)


# ============================================================
# INPUT FILE HELPERS
# ============================================================

def load_json(filename):
    path = INPUT_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Input file not found:\n{path}"
        )

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {path}:\n{exc}"
        ) from exc


def load_input_data():
    academic = load_json("academic.json")
    batches = load_json("batches.json")
    faculty = load_json("faculty.json")
    subjects = load_json("subjects.json")
    rooms = load_json("rooms.json")
    rules = load_json("rules.json")

    return {
        "academic": academic,
        "batches": batches,
        "faculty": faculty,
        "subjects": subjects,
        "rooms": rooms,
        "rules": rules,
    }


# ============================================================
# SCHEDULING CONFIGURATION
# ============================================================

def build_scheduling_rules(academic, rules):
    periods = {}

    for index, period in enumerate(
        academic.get("periods", []),
        start=1,
    ):
        periods[index] = {
            "start": str(period["start"]),
            "end": str(period["end"]),
        }

    if not periods:
        raise ValueError(
            "No academic periods found in academic.json."
        )

    return {
        "working_days": academic.get(
            "working_days",
            [],
        ),
        "periods_per_day": len(periods),
        "periods": periods,
        "short_break": academic.get(
            "short_break",
            {},
        ),
        "lunch_break": academic.get(
            "lunch_break",
            {},
        ),
        "theory_duration": 1,
        "tutorial_duration": 1,
        "practical_duration": int(
            rules.get(
                "practical_duration_hours",
                2,
            )
        ),
    }


# Loaded defaults are kept as module-level objects because the
# existing solver imports these names.
_default_input = load_input_data()

SCHEDULING_RULES = build_scheduling_rules(
    _default_input["academic"],
    _default_input["rules"],
)


# ============================================================
# OPTIONAL WEB-FORM COMPATIBILITY
# ============================================================

def find_latest_submission():
    if not SUBMISSIONS_DIR.exists():
        return None

    submissions = [
        folder
        for folder in SUBMISSIONS_DIR.iterdir()
        if (
            folder.is_dir()
            and (folder / "submission.json").exists()
        )
    ]

    if not submissions:
        return None

    return max(
        submissions,
        key=lambda folder: (
            folder / "submission.json"
        ).stat().st_mtime,
    )


def load_submission():
    """
    Compatibility layer.

    The new JSON files are now the primary input source.
    If a web-form submission exists, its raw record is returned
    only as supplemental metadata.
    """
    data = load_input_data()

    submission = {
        "academic": data["academic"],
        "batches": [
            {
                "code": code,
                **info,
            }
            for code, info in data["batches"].items()
        ],
        "faculty": [
            {
                "code": code,
                **info,
            }
            for code, info in data["faculty"].items()
        ],
        "rooms": [
            {
                "name": name,
                **info,
            }
            for name, info in data["rooms"].items()
        ],
        "subjects": data["subjects"],
        "rules": data["rules"],
        "input_source": str(INPUT_DIR),
    }

    latest = find_latest_submission()

    if latest is not None:
        submission["latest_web_form_submission"] = str(
            latest / "submission.json"
        )

    return submission


# ============================================================
# FACULTY DATA
# ============================================================

def load_faculty_data():
    raw = load_json("faculty.json")
    faculty_data = {}

    for code, info in raw.items():
        code = str(code).strip()

        if not code:
            continue

        faculty_data[code] = {
            "name": str(
                info.get("name", code)
            ).strip() or code,

            "theory": list(
                info.get("theory", [])
                or []
            ),

            "tutorial": list(
                info.get("tutorial", [])
                or []
            ),

            "practical": list(
                info.get("practical", [])
                or []
            ),
        }

    return faculty_data


def get_faculty_for_theory(subject):
    return [
        code
        for code, data in load_faculty_data().items()
        if subject in data["theory"]
    ]


def get_faculty_for_tutorial(subject):
    return [
        code
        for code, data in load_faculty_data().items()
        if subject in data["tutorial"]
    ]


def get_faculty_for_practical(subject):
    return [
        code
        for code, data in load_faculty_data().items()
        if subject in data["practical"]
    ]


def get_faculty_for_subject(subject):
    result = set()
    result.update(get_faculty_for_theory(subject))
    result.update(get_faculty_for_tutorial(subject))
    result.update(get_faculty_for_practical(subject))
    return sorted(result)


def get_subjects_for_faculty(faculty_code):
    faculty = load_faculty_data()

    if faculty_code not in faculty:
        return []

    data = faculty[faculty_code]

    return sorted(
        set(
            data["theory"]
            + data["tutorial"]
            + data["practical"]
        )
    )


# ============================================================
# BATCH DATA
# ============================================================

def load_batch_data():
    raw = load_json("batches.json")
    batches = {}

    for code, info in raw.items():
        code = str(code).strip()

        if not code:
            continue

        try:
            students = int(
                info.get("students", 0)
            )
        except (ValueError, TypeError):
            students = 0

        batches[code] = {
            "students": students,
            "elective": str(
                info.get("elective", "")
            ).strip(),
            "roll_range": str(
                info.get("roll_range", "")
            ).strip(),
        }

    return batches


# ============================================================
# ACADEMIC DATA
# ============================================================

def load_academic_data():
    return load_json("academic.json")


# ============================================================
# ROOM DATA
# ============================================================

def load_room_data():
    raw = load_json("rooms.json")
    rooms = []

    for name, info in raw.items():
        room = {
            "name": str(name).strip(),
            "type": str(
                info.get("type", "classroom")
            ).strip(),
            "capacity": int(
                info.get("capacity", 0)
            ),
        }

        if "computers" in info:
            room["computers"] = int(
                info["computers"]
            )

        if "students_per_pc" in info:
            room["students_per_pc"] = int(
                info["students_per_pc"]
            )

        rooms.append(room)

    return rooms


# ============================================================
# WORKLOAD DATA
#
# Workload Excel remains the authoritative workload/session
# packaging source for the current TE Semester V prototype.
# ============================================================

def load_workload():
    if not WORKLOAD_FILE.exists():
        raise FileNotFoundError(
            f"Workload file not found:\n"
            f"{WORKLOAD_FILE}"
        )

    df = pd.read_excel(WORKLOAD_FILE)

    if df.empty:
        raise ValueError(
            "Workload Excel file is empty."
        )

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

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Workload file is missing required columns:\n"
            + "\n".join(
                f"- {column}"
                for column in missing
            )
        )

    df = df[
        df["Course Code"].notna()
    ].copy()

    df = df[
        df["Course Code"].astype(str).str.upper()
        != "TOTAL"
    ].copy()

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

    for column in [
        "Theory (hrs)",
        "Tutorial (hrs)",
        "Practical (hrs)",
        "Credits",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).fillna(0)

    records = []

    for _, row in df.iterrows():
        record = {
            "course_code": row["Course Code"],
            "subject": row["Subject"],
            "theory_hours": int(
                row["Theory (hrs)"]
            ),
            "tutorial_hours": int(
                row["Tutorial (hrs)"]
            ),
            "practical_hours": int(
                row["Practical (hrs)"]
            ),
            "credits": float(
                row["Credits"]
            ),
            "session_packaging": row[
                "Session Packaging"
            ],
        }

        if (
            record["theory_hours"]
            + record["tutorial_hours"]
            + record["practical_hours"]
        ) <= 0:
            raise ValueError(
                f"Subject has zero workload: "
                f"{record['subject']}"
            )

        records.append(record)

    return {
        "dataframe": df,
        "records": records,
        "total_theory_hours": sum(
            r["theory_hours"]
            for r in records
        ),
        "total_tutorial_hours": sum(
            r["tutorial_hours"]
            for r in records
        ),
        "total_practical_hours": sum(
            r["practical_hours"]
            for r in records
        ),
        "total_weekly_hours": sum(
            r["theory_hours"]
            + r["tutorial_hours"]
            + r["practical_hours"]
            for r in records
        ),
    }


# ============================================================
# STATIC SCHEDULING STRUCTURE
#
# This preserves the currently validated TE Semester V
# teaching-group structure while faculty/batches/rooms/rules
# are now read from JSON input.
# ============================================================

SUBJECT_DEFINITIONS = {
    "Microcontrollers & Applications": {
        "code": "PCC-301-ETC",
        "theory_group": "COMMON_TE",
    },
    "Cellular Network": {
        "code": "PCC-302-ETC",
        "theory_group": "COMMON_TE",
    },
    "VLSI Design": {
        "code": "PCC-303-ETC",
        "theory_group": "COMMON_TE",
    },
    "Microcontrollers & VLSI Design Lab": {
        "code": "PCC-304-ETC",
        "practical_groups": ["T1", "T2", "T3"],
        "practical_blocks": 2,
    },
    "Cellular Network Lab": {
        "code": "PCC-305-ETC",
        "practical_groups": ["T1", "T2", "T3"],
        "practical_blocks": 1,
    },
    "Programme Elective I": {
        "code": "PEC-321-ETC",
        "elective_groups": {
            "Cloud Computing": ["T1", "T2"],
            "Advanced Java Programming": ["T3"],
        },
    },
    "Programme Elective Lab": {
        "code": "PEC-322-ETC",
        "elective_groups": {
            "Cloud Computing": ["T1", "T2"],
            "Advanced Java Programming": ["T3"],
        },
        "practical_blocks": 1,
    },
    "Machine Learning": {
        "code": "MDM-331-ETC",
        "tutorial_group": "COMMON_TE",
        "practical_groups": ["T1", "T2", "T3"],
        "practical_blocks": 1,
    },
    "Open Elective": {
        "code": "OLE-341-ETC",
        "theory_group": "COMMON_TE",
        "elective_name": "Sustainability Development",
    },
    "Technical Seminar": {
        "code": "ELC-342-ETC",
        "practical_groups": ["T1", "T2", "T3"],
        "practical_blocks": 1,
    },
}


def build_teaching_groups(batches):
    batch_codes = list(batches.keys())

    common = [
        code
        for code in ["T1", "T2", "T3"]
        if code in batches
    ]

    cloud = [
        code
        for code in common
        if batches[code].get("elective")
        == "Cloud Computing"
    ]

    ajp = [
        code
        for code in common
        if batches[code].get("elective")
        == "Advanced Java Programming"
    ]

    groups = {
        "COMMON_TE": common,
        "CLOUD": cloud,
        "AJP": ajp,
    }

    for code in batch_codes:
        groups[code] = [code]

    return groups


# Backward-compatible defaults for modules importing constants.
TEACHING_GROUPS = build_teaching_groups(
    _default_input["batches"]
)


def build_subject_batches():
    result = {}

    for subject, definition in SUBJECT_DEFINITIONS.items():
        batches = []

        if "theory_group" in definition:
            batches.extend(
                TEACHING_GROUPS.get(
                    definition["theory_group"],
                    [],
                )
            )

        if "tutorial_group" in definition:
            batches.extend(
                TEACHING_GROUPS.get(
                    definition["tutorial_group"],
                    [],
                )
            )

        if "practical_groups" in definition:
            batches.extend(
                definition["practical_groups"]
            )

        if "elective_groups" in definition:
            for group_batches in definition[
                "elective_groups"
            ].values():
                batches.extend(group_batches)

        result[subject] = sorted(
            set(batches)
        )

    return result


SUBJECT_BATCHES = build_subject_batches()

ELECTIVE_GROUPS = {
    "Programme Elective I": {
        "CLOUD": TEACHING_GROUPS.get(
            "CLOUD", []
        ),
        "AJP": TEACHING_GROUPS.get(
            "AJP", []
        ),
    },
    "Programme Elective Lab": {
        "T1": ["T1"],
        "T2": ["T2"],
        "T3": ["T3"],
    },
}


# ============================================================
# SESSION CREATION
# ============================================================

def get_workload_record(subject, workload):
    for record in workload["records"]:
        if record["subject"] == subject:
            return record

    return None


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
        "id": session_id,
        "subject": subject,
        "type": session_type,
        "duration": duration,
        "group": group,
        "batch": list(batches),
    }

    if elective:
        session["elective"] = elective

    return session


def create_common_theory_sessions(
    subject,
    hours,
    group="COMMON_TE",
):
    sessions = []

    batches = TEACHING_GROUPS.get(
        group,
        [],
    )

    for index in range(1, hours + 1):
        sessions.append(
            make_session(
                f"{subject}_T{index}",
                subject,
                "theory",
                SCHEDULING_RULES[
                    "theory_duration"
                ],
                group,
                batches,
            )
        )

    return sessions


def create_common_tutorial_sessions(
    subject,
    hours,
    group="COMMON_TE",
):
    sessions = []

    batches = TEACHING_GROUPS.get(
        group,
        [],
    )

    for index in range(1, hours + 1):
        sessions.append(
            make_session(
                f"{subject}_TUT_{index}",
                subject,
                "tutorial",
                SCHEDULING_RULES[
                    "tutorial_duration"
                ],
                group,
                batches,
            )
        )

    return sessions


def create_elective_theory_sessions(
    subject,
    hours,
    elective_groups,
):
    sessions = []

    for elective, batches in elective_groups.items():
        if set(batches) == set(
            TEACHING_GROUPS.get("CLOUD", [])
        ):
            group_name = "CLOUD"
        else:
            group_name = "AJP"

        for index in range(1, hours + 1):
            sessions.append(
                make_session(
                    (
                        f"{subject}_"
                        f"{elective.replace(' ', '_')}_"
                        f"{index}"
                    ),
                    subject,
                    "theory",
                    SCHEDULING_RULES[
                        "theory_duration"
                    ],
                    group_name,
                    batches,
                    elective,
                )
            )

    return sessions


def create_practical_sessions(
    subject,
    blocks,
    groups,
):
    sessions = []

    for block in range(1, blocks + 1):
        for batch in groups:
            elective = None

            if subject == "Programme Elective Lab":
                if batch in ["T1", "T2"]:
                    elective = "Cloud Computing"
                elif batch == "T3":
                    elective = (
                        "Advanced Java Programming"
                    )

            sessions.append(
                make_session(
                    (
                        f"{subject}_"
                        f"{block}_"
                        f"{batch}"
                    ),
                    subject,
                    "practical",
                    SCHEDULING_RULES[
                        "practical_duration"
                    ],
                    batch,
                    [batch],
                    elective,
                )
            )

    return sessions


def create_sessions(workload):
    sessions = []

    for subject, definition in (
        SUBJECT_DEFINITIONS.items()
    ):
        record = get_workload_record(
            subject,
            workload,
        )

        if record is None:
            raise ValueError(
                f"Subject '{subject}' "
                "was not found in workload Excel."
            )

        theory_hours = record["theory_hours"]
        tutorial_hours = record["tutorial_hours"]
        practical_hours = record["practical_hours"]

        if theory_hours > 0:
            if "theory_group" in definition:
                sessions.extend(
                    create_common_theory_sessions(
                        subject,
                        theory_hours,
                        definition[
                            "theory_group"
                        ],
                    )
                )

            if "elective_groups" in definition:
                sessions.extend(
                    create_elective_theory_sessions(
                        subject,
                        theory_hours,
                        definition[
                            "elective_groups"
                        ],
                    )
                )

        if tutorial_hours > 0:
            if "tutorial_group" in definition:
                sessions.extend(
                    create_common_tutorial_sessions(
                        subject,
                        tutorial_hours,
                        definition[
                            "tutorial_group"
                        ],
                    )
                )

        if practical_hours > 0:
            if "practical_groups" in definition:
                blocks = int(
                    definition.get(
                        "practical_blocks",
                        practical_hours // 2,
                    )
                )

                sessions.extend(
                    create_practical_sessions(
                        subject,
                        blocks,
                        definition[
                            "practical_groups"
                        ],
                    )
                )

    return sessions


# ============================================================
# VALIDATION
# ============================================================

def validate_sessions(
    sessions,
    batches,
    workload,
):
    errors = []

    if len(sessions) != 37:
        errors.append(
            f"Expected 37 sessions, "
            f"but generated {len(sessions)}."
        )

    if workload[
        "total_weekly_hours"
    ] != 28:
        errors.append(
            "Expected 28 weekly workload hours, "
            f"but found "
            f"{workload['total_weekly_hours']}."
        )

    required_batches = {"T1", "T2", "T3"}
    missing = required_batches - set(
        batches.keys()
    )

    if missing:
        errors.append(
            "Missing required batches: "
            + ", ".join(sorted(missing))
        )

    for session in sessions:
        for key in [
            "id",
            "subject",
            "type",
            "duration",
            "group",
            "batch",
        ]:
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

        if (
            session.get("type") == "practical"
            and session.get("duration") != 2
        ):
            errors.append(
                f"Practical session "
                f"{session.get('id')} "
                "must be 2 hours."
            )

        for batch in session.get("batch", []):
            if batch not in batches:
                errors.append(
                    f"Session "
                    f"{session.get('id')} "
                    f"references unknown batch "
                    f"{batch}."
                )

    return errors


# ============================================================
# MAIN DATA LOADER
# ============================================================

def load_te_sem_v_data():
    input_data = load_input_data()

    # Refresh module-level scheduling groups from the current
    # JSON batch file on every engine run.
    global TEACHING_GROUPS
    global SUBJECT_BATCHES
    global ELECTIVE_GROUPS
    global SCHEDULING_RULES

    TEACHING_GROUPS = build_teaching_groups(
        input_data["batches"]
    )

    SCHEDULING_RULES = build_scheduling_rules(
        input_data["academic"],
        input_data["rules"],
    )

    SUBJECT_BATCHES = build_subject_batches()

    ELECTIVE_GROUPS = {
        "Programme Elective I": {
            "CLOUD": TEACHING_GROUPS.get(
                "CLOUD", []
            ),
            "AJP": TEACHING_GROUPS.get(
                "AJP", []
            ),
        },
        "Programme Elective Lab": {
            "T1": ["T1"],
            "T2": ["T2"],
            "T3": ["T3"],
        },
    }

    faculty = load_faculty_data()
    batches = load_batch_data()
    academic = load_academic_data()
    rooms = load_room_data()
    workload = load_workload()

    sessions = create_sessions(
        workload
    )

    validation_errors = validate_sessions(
        sessions,
        batches,
        workload,
    )

    if validation_errors:
        raise ValueError(
            "DATA LOADER VALIDATION FAILED:\n"
            + "\n".join(
                f"- {error}"
                for error in validation_errors
            )
        )

    return {
        "submission": load_submission(),
        "faculty": faculty,
        "batches": batches,
        "academic": academic,
        "rooms": rooms,
        "workload": workload,
        "sessions": sessions,
        "subject_definitions": SUBJECT_DEFINITIONS,
        "subject_batches": SUBJECT_BATCHES,
        "teaching_groups": TEACHING_GROUPS,
        "elective_groups": ELECTIVE_GROUPS,
        "scheduling_rules": SCHEDULING_RULES,
        "input_data": input_data,
    }


def load_data():
    return load_te_sem_v_data()


# ============================================================
# DEBUG / TEST
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("AI TIMETABLE DATA LOADER")
    print("=" * 70)

    data = load_te_sem_v_data()

    print("\nINPUT SOURCE:")
    print(INPUT_DIR)

    print("\nWorkload totals:")
    print(
        "Theory    :",
        data["workload"]["total_theory_hours"],
    )
    print(
        "Tutorial  :",
        data["workload"]["total_tutorial_hours"],
    )
    print(
        "Practical :",
        data["workload"]["total_practical_hours"],
    )
    print(
        "Total     :",
        data["workload"]["total_weekly_hours"],
    )

    print("\nFaculty:")
    for code, info in data["faculty"].items():
        print(
            f"{code} - {info['name']}"
        )

    print("\nBatches:")
    for code, info in data["batches"].items():
        print(
            f"{code}: "
            f"{info['students']} students | "
            f"{info['elective']}"
        )

    print("\nRooms:")
    for room in data["rooms"]:
        print(
            f"{room['name']}: "
            f"{room['type']} | "
            f"capacity {room['capacity']}"
        )

    print("\nSessions:", len(data["sessions"]))

    print("\n" + "=" * 70)
    print("DATA LOADER VALIDATION PASSED")
    print(
        f"Total sessions: {len(data['sessions'])}"
    )
    print(
        "Total workload: "
        f"{data['workload']['total_weekly_hours']} hours/week"
    )
    print("=" * 70)
