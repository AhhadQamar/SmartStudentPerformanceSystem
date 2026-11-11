# UC08: a teacher views the prediction history of a student. The docstring is the expected result.

from helpers import enroll, make_marks, make_prediction, make_student, page_text


def history_url(student_id):
    return f"/teacher/history/{student_id}"


def test_TC_UC08_01_view_history(teacher_client, app):
    """The history shows each prediction with its inputs, predicted grade and risk level."""
    student_id = make_student(app)
    enroll(app, student_id)
    make_prediction(app, student_id, grade="B", risk="Low")
    make_prediction(app, student_id, grade="D", risk="High")

    text = page_text(teacher_client.get(history_url(student_id)))

    assert "Sara Khan" in text
    assert text.count("Pending") == 2  # two rows, actual grade not known yet
    assert "90.0%" in text  # the saved attendance input
    assert "High" in text and "Low" in text


def test_TC_UC08_02_student_without_predictions(teacher_client, app):
    """A student with no predictions shows 'No prediction history available'."""
    student_id = make_student(app)
    enroll(app, student_id)

    text = page_text(teacher_client.get(history_url(student_id)))

    assert "No prediction history available" in text


def test_TC_UC08_03_actual_grade_not_known_yet(teacher_client, app):
    """While the real grade is not known the row shows 'Pending' and there is no error."""
    student_id = make_student(app)
    enroll(app, student_id)
    make_prediction(app, student_id)

    response = teacher_client.get(history_url(student_id))

    assert response.status_code == 200
    assert "Pending" in page_text(response)


def test_extra_history_shows_the_actual_grade_once_it_is_known(teacher_client, app):
    """When all four marks exist, the real grade replaces 'Pending'."""
    student_id = make_student(app)
    enroll(app, student_id)
    make_prediction(app, student_id, grade="A", risk="Low")
    make_marks(app, student_id, quiz=8, assignment=18, midterm=25, final=35)  # grade A

    text = page_text(teacher_client.get(history_url(student_id)))

    assert "Pending" not in text
