# UC03: a teacher enters marks. The docstring is the expected result.

from app.models import Marks
from helpers import course_id, enroll, make_marks, make_student, page_text


def marks_url(app, assessment="quiz"):
    return f"/teacher/marks?course={course_id(app)}&assessment={assessment}"


def test_TC_UC03_01_enter_valid_mark(teacher_client, app):
    """A valid mark (8 out of 10) is saved and the grade is worked out again."""
    student_id = make_student(app)
    enroll(app, student_id)
    # the other three marks already exist so the quiz mark completes the set
    make_marks(app, student_id, assignment=18, midterm=25, final=35)

    response = teacher_client.post(
        marks_url(app), data={f"mark_{student_id}": "8"}, follow_redirects=True
    )

    assert "Saved 1 mark" in page_text(response)
    with app.app_context():
        marks = Marks.query.filter_by(student_id=student_id).first()
        assert marks.quiz == 8
        assert marks.percentage == 86.0  # 8 + 18 + 25 + 35
        assert marks.grade == "A"


def test_TC_UC03_02_mark_above_the_maximum(teacher_client, app):
    """A mark of 15 on a quiz that is out of 10 shows an error and nothing is saved."""
    student_id = make_student(app)
    enroll(app, student_id)

    response = teacher_client.post(
        marks_url(app), data={f"mark_{student_id}": "15"}, follow_redirects=True
    )

    assert "between 0 and 10" in page_text(response)
    with app.app_context():
        assert Marks.query.count() == 0


def test_TC_UC03_03_student_not_enrolled(teacher_client, app):
    """A student who is not enrolled in the course cannot get a mark."""
    enrolled_id = make_student(app)
    enroll(app, enrolled_id)
    outsider_id = make_student(
        app, name="Ali Hassan", roll="SP24-BSCS-046", email="ali@student.edu"
    )  # not enrolled

    teacher_client.post(
        marks_url(app),
        data={f"mark_{enrolled_id}": "6", f"mark_{outsider_id}": "5"},
        follow_redirects=True,
    )

    with app.app_context():
        assert Marks.query.filter_by(student_id=enrolled_id).count() == 1
        assert Marks.query.filter_by(student_id=outsider_id).count() == 0


def test_TC_UC03_04_failure_while_saving(teacher_client, app, monkeypatch):
    """If something fails while saving, an error is shown and NOTHING is saved."""
    first = make_student(app)
    second = make_student(
        app, name="Ali Hassan", roll="SP24-BSCS-046", email="ali@student.edu"
    )
    enroll(app, first)
    enroll(app, second)

    # make the second student's save crash after the first one was already added
    import app.routes as routes

    calls = []
    real_function = routes.recalculate_marks

    def crash_on_second(marks):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("the database went away")
        real_function(marks)

    monkeypatch.setattr(routes, "recalculate_marks", crash_on_second)

    response = teacher_client.post(
        marks_url(app),
        data={f"mark_{first}": "7", f"mark_{second}": "8"},
        follow_redirects=True,
    )

    assert "could not be saved" in page_text(response)
    with app.app_context():
        assert Marks.query.count() == 0  # the first student's mark was undone too


# extra test (not in the design document) for the ownership rule


def test_extra_teacher_cannot_enter_marks_in_another_teachers_course(
    other_teacher_client, app
):
    """A teacher who does not teach the course is told it was not found."""
    response = other_teacher_client.get(marks_url(app), follow_redirects=True)

    assert "Course not found" in page_text(response)
