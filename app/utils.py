# Small helper functions that the routes can call.

from sqlalchemy.sql.roles import TruncatedLabelRole

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


def check_password_rules(password):
    # returns none is the password if fine or a message saying what is wrong with it.
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    #  walk through evey character and check if it has at least one uppercase, one lowercase and one digit
    has_upper = False
    has_lower = False
    has_digit = False
    has_special = False
    for char in password:
        if char.isupper():
            has_upper = True
        elif char.islower():
            has_lower = True
        elif char.isdigit():
            has_digit = True

    if not has_upper:
        return "Password must contain at least one uppercase letter."
    if not has_lower:
        return "Password must contain at least one lowercase letter."
    if not has_digit:
        return "Password must contain at least one digit."
    return None  # password is fine


def recalculate_marks(marks):
    # marks is one row of the marks table, as a dictionary. It has keys: quiz, assignment, midterm, final.
    # we calculate the percentage and grade, and add them to the dictionary. If any of the marks are missing, we set percentage and grade to None
    result = calculate_grade(marks.quiz, marks.assignment, marks.midterm, marks.final)
    if result["status"] == "Complete":
        marks.percentage = result["percentage"]
        marks.grade = result["grade"]
    else:
        marks.percentage = None
        marks.grade = None


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
