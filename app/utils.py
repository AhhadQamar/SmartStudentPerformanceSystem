_MAXIMA = {"attendance": 100, "quiz": 50, "assignment": 25, "midterm": 100}

_WEIGHTS = {"attendance": 15, "quiz": 20, "assignment": 15, "midterm": 50}

_BOUNDARIES = [(80, "A"), (65, "B"), (50, "C"), (40, "D"), (0, "F")]


def calculate_percentage(
    attendance: float, quiz: float, assignment: float, midterm: float
) -> float:
    values = {
        "attendance": attendance,
        "quiz": quiz,
        "assignment": assignment,
        "midterm": midterm,
    }
    # Divide each score by its max to get 0–1, then multiply by its weight.
    return round(sum((values[k] / _MAXIMA[k]) * _WEIGHTS[k] for k in _WEIGHTS), 1)


def percentage_to_grade(percentage: float) -> str:
    for threshold, grade in _BOUNDARIES:
        if percentage >= threshold:
            return grade
    return "F"
