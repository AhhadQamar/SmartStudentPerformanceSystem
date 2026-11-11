# UC04: a teacher records attendance. The docstring is the expected result.

from datetime import date, timedelta

from app.models import Attendance
from app.utils import attendance_percentage
from helpers import course_id, enroll, make_attendance, make_student, page_text


def yesterday():
    return (date.today() - timedelta(days=1)).isoformat()


def attendance_url(app, day=None):
    return f"/teacher/attendance?course={course_id(app)}&date={day or yesterday()}"


def test_TC_UC04_01_record_attendance(teacher_client, app):
    """Attendance is saved for the day and the student's percentage is updated."""
    student_id = make_student(app)
    enroll(app, student_id)

    response = teacher_client.post(
        attendance_url(app), data={f"status_{student_id}": "Present"}, follow_redirects=True
    )

    assert "Saved attendance" in page_text(response)
    with app.app_context():
        assert Attendance.query.count() == 1
        assert attendance_percentage(student_id, course_id(app)) == 100.0


def test_TC_UC04_02_record_the_same_day_twice(teacher_client, app):
    """A second record for the same course and date is refused: it already exists."""
    student_id = make_student(app)
    enroll(app, student_id)
    data = {f"status_{student_id}": "Present"}
    teacher_client.post(attendance_url(app), data=data)

    response = teacher_client.post(attendance_url(app), data=data, follow_redirects=True)

    assert "already been recorded" in page_text(response)
    with app.app_context():
        assert Attendance.query.count() == 1


def test_TC_UC04_03_attendance_below_the_limit_is_flagged(teacher_client, app):
    """A student who drops to 70% (limit 75%) is flagged as low attendance."""
    student_id = make_student(app)
    enroll(app, student_id)
    # 9 days already recorded, 6 present and 3 absent. Today's "Present" makes it 7 out of 10
    make_attendance(app, student_id, present=6, absent=3)

    response = teacher_client.post(
        attendance_url(app, date.today().isoformat()),
        data={f"status_{student_id}": "Present"},
        follow_redirects=True,
    )

    text = page_text(response)
    assert "low attendance" in text
    assert "Sara Khan" in text
    with app.app_context():
        assert attendance_percentage(student_id, course_id(app)) == 70.0


def test_TC_UC04_04_nobody_marked(teacher_client, app):
    """Sending the form without marking any student shows an error and saves nothing."""
    student_id = make_student(app)
    enroll(app, student_id)

    response = teacher_client.post(attendance_url(app), data={}, follow_redirects=True)

    assert "mark all students" in page_text(response)
    with app.app_context():
        assert Attendance.query.count() == 0
