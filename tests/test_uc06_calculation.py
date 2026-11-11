# UC06: the grade is worked out from the marks. The docstring is the expected result.

import pytest

import app.config_grading as config_grading
from app.models import Marks
from app.utils import GradeConfigError, calculate_grade
from helpers import course_id, enroll, make_marks, make_student, page_text


def test_TC_UC06_01_grade_from_complete_marks():
    """Quiz 8/10, assignment 18/20, midterm 25/30, final 35/40 give 86.0% and grade A."""
    result = calculate_grade(8, 18, 25, 35)

    assert result == {"status": "Complete", "percentage": 86.0, "grade": "A"}


def test_TC_UC06_02_missing_mark_gives_no_grade(teacher_client, app):
    """A missing midterm is reported and no grade is worked out or saved."""
    result = calculate_grade(8, 18, None, 35)
    assert result == {"status": "Incomplete", "missing": ["midterm"]}

    # same thing through the page: the marks get saved but there is no grade
    student_id = make_student(app)
    enroll(app, student_id)
    make_marks(app, student_id, quiz=8, assignment=18, final=35)
    with app.app_context():
        marks = Marks.query.filter_by(student_id=student_id).first()
        assert marks.percentage is None
        assert marks.grade is None


def test_TC_UC06_03_weights_that_do_not_add_up(teacher_client, app, monkeypatch):
    """Weights that add up to 90 give a configuration error and nothing is saved."""
    monkeypatch.setitem(config_grading.WEIGHTS, "quiz", 0)  # 0 + 20 + 30 + 40 = 90

    with pytest.raises(GradeConfigError):
        calculate_grade(8, 18, 25, 35)

    # same thing through the page: the teacher sees the error and no mark is saved
    student_id = make_student(app)
    enroll(app, student_id)
    response = teacher_client.post(
        f"/teacher/marks?course={course_id(app)}&assessment=quiz",
        data={f"mark_{student_id}": "8"},
        follow_redirects=True,
    )

    assert "configuration error" in page_text(response)
    with app.app_context():
        assert Marks.query.count() == 0
