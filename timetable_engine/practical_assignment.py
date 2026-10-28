from practical_activities import get_activities


BATCHES = ["T1", "T2", "T3"]


def flatten_activities(data):
    """
    Convert activity database output into a single list.
    Handles both normal lists and grouped activities.
    """

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        activities = []

        for group in data.values():
            if isinstance(group, list):
                activities.extend(group)

        return activities

    raise TypeError("Unsupported activity database format.")


def get_distinct_activities(subject, block_number=0):
    """
    Assign different practical activities to T1, T2 and T3.
    """

    raw_activities = get_activities(subject)
    activities = flatten_activities(raw_activities)

    if len(activities) < 3:
        raise ValueError(
            f"{subject} has only {len(activities)} activities. "
            f"At least 3 are required for parallel T1/T2/T3 assignment."
        )

    assignments = {}

    for index, batch in enumerate(BATCHES):

        activity_index = (
            block_number * 3 + index
        ) % len(activities)

        assignments[batch] = activities[activity_index]

    return assignments


def print_assignment(subject, number_of_blocks=1):

    print()
    print("=" * 70)
    print(f"PRACTICAL ACTIVITY ASSIGNMENT: {subject}")
    print("=" * 70)

    for block in range(number_of_blocks):

        assignments = get_distinct_activities(
            subject,
            block
        )

        print()
        print(f"Practical Block {block + 1}")
        print("-" * 70)

        for batch in BATCHES:
            print(f"{batch} -> {assignments[batch]}")


if __name__ == "__main__":

    # Microcontrollers & VLSI Design Lab
    print_assignment(
        "Microcontrollers & VLSI Design Lab",
        number_of_blocks=2
    )

    # Cellular Network Lab
    print_assignment(
        "Cellular Network Lab",
        number_of_blocks=1
    )

    # Machine Learning Lab
    print_assignment(
        "Machine Learning Lab",
        number_of_blocks=1
    )

    # Technical Seminar
    print_assignment(
        "Technical Seminar",
        number_of_blocks=1
    )