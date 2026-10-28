from faculty_expertise import get_faculty_for_practical


BATCHES_REQUIRED = 3


PRACTICAL_SUBJECTS = [
    "Microcontrollers & VLSI Design Lab",
    "Cellular Network Lab",
    "Machine Learning",
    "Programme Elective Lab",
    "Technical Seminar",
]


def check_practical_resources(subject):

    faculty = get_faculty_for_practical(subject)

    faculty_count = len(faculty)

    feasible = faculty_count >= BATCHES_REQUIRED

    return {
        "subject": subject,
        "faculty": faculty,
        "faculty_count": faculty_count,
        "required_faculty": BATCHES_REQUIRED,
        "parallel_feasible": feasible,
    }


def print_resource_report():

    print("=" * 70)
    print("PRACTICAL RESOURCE FEASIBILITY REPORT")
    print("=" * 70)

    for subject in PRACTICAL_SUBJECTS:

        result = check_practical_resources(subject)

        print()
        print(subject)
        print("-" * 70)

        print(
            f"Faculty available : "
            f"{result['faculty_count']}"
        )

        print(
            f"Faculty required  : "
            f"{result['required_faculty']}"
        )

        print(
            f"Faculty           : "
            f"{result['faculty']}"
        )

        if result["parallel_feasible"]:

            print(
                "STATUS            : FEASIBLE"
            )

        else:

            shortage = (
                result["required_faculty"]
                - result["faculty_count"]
            )

            print(
                "STATUS            : "
                "INSUFFICIENT FACULTY"
            )

            print(
                f"Shortage          : "
                f"{shortage}"
            )


if __name__ == "__main__":
    print_resource_report()