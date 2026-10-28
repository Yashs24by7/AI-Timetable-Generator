DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday"
]


PERIODS = {
    1: ("08:45", "09:45"),
    2: ("09:45", "10:45"),
    3: ("11:00", "12:00"),
    4: ("12:00", "13:00"),
    5: ("13:45", "14:45"),
    6: ("14:45", "15:45"),
}

BATCHES = {
    "T1": {
        "students": 32,
        "elective": "Cloud Computing"
    },
    "T2": {
        "students": 31,
        "elective": "Cloud Computing"
    },
    "T3": {
        "students": 17,
        "elective": "Advanced Java Programming"
    }
}

SUBJECT_BATCHES = {
    "Microcontrollers & Applications": ["T1", "T2", "T3"],
    "Cellular Network": ["T1", "T2", "T3"],
    "VLSI Design": ["T1", "T2", "T3"],

    "Microcontrollers & VLSI Design Lab": ["T1", "T2", "T3"],
    "Cellular Network Lab": ["T1", "T2", "T3"],

    "Programme Elective I": ["T1", "T2", "T3"],
    "Programme Elective Lab": ["T1", "T2", "T3"],

    "Machine Learning": ["T1", "T2", "T3"],

    "Open Elective": ["T1", "T2", "T3"],
    "Technical Seminar": ["T1", "T2", "T3"],
}

TEACHING_GROUPS = {
    "COMMON_TE": ["T1", "T2", "T3"],

    "CLOUD": ["T1", "T2"],

    "AJP": ["T3"],

    "T1": ["T1"],
    "T2": ["T2"],
    "T3": ["T3"],
}

ELECTIVE_GROUPS = {
    "Programme Elective I": {
        "CLOUD": ["T1", "T2"],
        "AJP": ["T3"],
    },

    "Programme Elective Lab": {
        "CLOUD": ["T1", "T2"],
        "AJP": ["T3"],
    },
}
PRACTICAL_PARALLEL_RULE = {
    "enabled": True,
    "batches": ["T1", "T2", "T3"],
    "duration": 2,
    "same_time_block": True,
    "different_activity": True,
}
LAB_ROOMS = {
    "A317": {
        "capacity": 48,
        "computers": 24,
        "students_per_pc": 2
    },

    "A318": {
        "capacity": 48,
        "computers": 24,
        "students_per_pc": 2
    },

    "A320": {
        "capacity": 48,
        "computers": 24,
        "students_per_pc": 2
    }
}


CLASSROOMS = {
    "312": {
        "capacity": 80
    },

    "319": {
        "capacity": 50
    },

    "322": {
        "capacity": 80
    }
}
def room_can_fit(room, student_count, room_type):
    """Check whether a room can accommodate a group."""

    if room_type == "LAB":
        if room not in LAB_ROOMS:
            return False

        return student_count <= LAB_ROOMS[room]["capacity"]

    if room_type == "CLASSROOM":
        if room not in CLASSROOMS:
            return False

        return student_count <= CLASSROOMS[room]["capacity"]

    return False


COMBINED_BATCHES = {
    "CLOUD": ["T1", "T2"]
}
FACULTY = {
    "PSG": {
        "name": "PSG",
        "subjects": [
            "Cloud Computing",
            "Cellular Network Lab"
        ]
    },

    "RG": {
        "name": "RG",
        "subjects": [
            "Advanced Java Programming",
            "Programme Elective Lab"
        ]
    },

    "RGZ": {
        "name": "RGZ",
        "subjects": [
            "Cellular Network"
        ]
    },

    "MD": {
        "name": "MD",
        "subjects": [
            "Microcontrollers & Applications",
            "Microcontrollers & VLSI Design Lab",
            "Technical Seminar"
        ]
    },

    "GSK": {
        "name": "GSK",
        "subjects": [
            "Sustainability Development"
        ]
    },

    "VDG": {
        "name": "VDG",
        "subjects": [
            "Machine Learning Tutorial"
        ]
    },

    "SJK": {
        "name": "SJK",
        "subjects": [
            "Machine Learning Practical"
        ]
    },

    "SP": {
        "name": "SP",
        "subjects": [
            "VLSI Design"
        ]
    }
}

# Two-hour practicals can only occupy
# two consecutive teaching periods.
PRACTICAL_START_PERIODS = [
    1,   # P1 + P2
    3,   # P3 + P4
    5    # P5 + P6
]


def get_all_slots():
    """Return all available 1-hour timetable slots."""

    slots = []

    for day in DAYS:
        for period in PERIODS:
            slots.append((day, period))

    return slots


def get_practical_slots():
    """Return valid starting slots for 2-hour practicals."""

    slots = []

    for day in DAYS:
        for start_period in PRACTICAL_START_PERIODS:
            slots.append(
                (day, start_period, start_period + 1)
            )

    return slots

def faculty_can_teach(faculty_code, subject):
    """Check whether a faculty member is assigned to a subject."""

    if faculty_code not in FACULTY:
        return False

    return subject in FACULTY[faculty_code]["subjects"]


if __name__ == "__main__":

    print("Working days:", len(DAYS))
    print("Periods per day:", len(PERIODS))
    print("Total weekly slots:", len(get_all_slots()))
    print("Valid 2-hour practical blocks:", len(get_practical_slots()))