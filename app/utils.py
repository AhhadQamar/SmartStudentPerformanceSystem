# Small helper functions that the routes can call.

from .config_grading import GRADE_SCALE, MAX_MARKS, RISK_BY_GRADE, WEIGHTS
from .constants import STATUS_PRESENT
from .models import Attendance, Marks


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
    check_weights()

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

    percentage = 0
    for name in WEIGHTS:
        percentage += (scores[name] / MAX_MARKS[name]) * WEIGHTS[name]
    percentage = round(percentage, 1)

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
    # we calculate the percentage and grade, and add them to object. If any of the marks are missing, we set percentage and grade to None
    result = calculate_grade(marks.quiz, marks.assignment, marks.midterm, marks.final)
    if result["status"] == "Complete":
        marks.percentage = result["percentage"]
        marks.grade = result["grade"]
    else:
        marks.percentage = None
        marks.grade = None


# returns the percentage of the days this student was present in this course.
def attendance_percentage(student_id, course_id):

    total = Attendance.query.filter_by(
        student_id=student_id, course_id=course_id
    ).count()
    if total == 0:
        return None
    present = Attendance.query.filter_by(
        student_id=student_id, course_id=course_id, status=STATUS_PRESENT
    ).count()
    return round(present / total * 100, 1)


def risk_from_grade(grade):
    # turms a predicted letter grade into a risk level, using the RISK_BY_GRADE dictionary.
    return RISK_BY_GRADE.get(grade, "Unknown")


def build_prediction_inputs(student_id, course_id):
    inputs = {}
    missing = []

    attendance = attendance_percentage(student_id, course_id)
    if attendance is None:
        missing.append("attendance")
    else:
        inputs["attendance"] = attendance

    marks = Marks.query.filter_by(student_id=student_id, course_id=course_id).first()
    for name in ["quiz", "assignment", "midterm"]:
        value = None
        if marks is not None:
            value = getattr(marks, name)
        if value is None:
            missing.append(name)
        else:
            inputs[name] = round(value / MAX_MARKS[name] * 100, 1)
    return inputs, missing
