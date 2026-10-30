# Small helper functions that the routes can call.

from .config_grading import GRADE_SCALE, MAX_MARKS, WEIGHTS


# an exception class for invalid grading configuration
class GradeConfigError(Exception):
    """Raised when the grading configuration is invalid."""

    pass


# Check that the weights sum to 100. If not, raise an exception.
def check_weights():
    total = sum(WEIGHTS.values())
    if total != 100:
        raise GradeConfigError(f"Grading weights sum to {total}, not 100.")


# Convert a percentage to a letter grade, using the GRADE_SCALE.
def percentage_to_grade(percentage):
    for minimum, letter in GRADE_SCALE:
        if percentage >= minimum:
            return letter
    return "F"  # Should never get here if GRADE_SCALE is valid.


def calculate_grade(quiz, assignment, midterm, final):
    scores = {
        "quiz": quiz,
        "assignment": assignment,
        "midterm": midterm,
        "final": final,
    }
    missing = []
    for name, value in scores.items():
        if value is None:
            missing.append(name)

    if len(missing) > 0:
        return {"status": "Incomplete", "missing": missing}

    check_weights()

    percentage = 0
    for name in WEIGHTS:
        percentage += (scores[name] / MAX_MARKS[name]) * WEIGHTS[name]

    return {
        "status": "Complete",
        "percentage": percentage,
        "grade": percentage_to_grade(percentage),
    }


# OLD PROTOTYPE Code
_MAXIMA = {"attendance": 100, "quiz": 50, "assignment": 25, "midterm": 100}

_WEIGHTS = {"attendance": 15, "quiz": 20, "assignment": 15, "midterm": 50}


def calculate_percentage(attendance, quiz, assignment, midterm):
    values = {
        "attendance": attendance,
        "quiz": quiz,
        "assignment": assignment,
        "midterm": midterm,
    }
    return round(sum((values[k] / _MAXIMA[k]) * _WEIGHTS[k] for k in _WEIGHTS), 1)
    # Divide each score by its max to get 0–1, then multiply by its weight.
