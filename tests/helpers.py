# small functions and constants that a lot of the tests use

import json
from datetime import date, timedelta

from app.extensions import db
from app.models import Attendance, Course, Enrollment, Marks, Prediction, Student

# the accounts that conftest.py makes for every test
ADMIN_EMAIL = "admin@school.com"
ADMIN_PASSWORD = "Admin@123"
TEACHER_EMAIL = "teacher1@school.com"
TEACHER_PASSWORD = "Valid@123"
OTHER_TEACHER_EMAIL = "existing.teacher@school.com"
OTHER_TEACHER_PASSWORD = "Valid@123"


def login(client, email, password):
    # fills in the login form like a user would
    return client.post(
        "/login",
        data={"username": email, "password": password},
        follow_redirects=True,
    )


def page_text(response):
    # returns the html of a response as text so we can search it for messages
    return response.get_data(as_text=True)


def make_student(
    app,
    name="Sara Khan",
    roll="SP24-BSCS-045",
    email="sara.khan@student.edu",
    contact="03001234567",
):
    # puts a student in the test database, returns the student id
    with app.app_context():
        student = Student(name=name, roll_number=roll, email=email, contact=contact)
        db.session.add(student)
        db.session.commit()
        return student.id


def enroll(app, student_id, course_code="CS301"):
    # enrolls a student in a course (CS301, CS302 or CS303)
    with app.app_context():
        course = Course.query.filter_by(course_code=course_code).first()
        db.session.add(Enrollment(student_id=student_id, course_id=course.id))
        db.session.commit()


def course_id(app, course_code="CS301"):
    # gets the id of a course from its code
    with app.app_context():
        return Course.query.filter_by(course_code=course_code).first().id


def make_marks(app, student_id, course_code="CS301", **marks):
    # puts marks in the database. Example: make_marks(app, student_id, quiz=8, assignment=18, midterm=25, final=35)
    # leave a mark out to keep it empty. The percentage and grade are worked out the same way the app does it.
    from app.utils import recalculate_marks

    with app.app_context():
        row = Marks(
            student_id=student_id,
            course_id=Course.query.filter_by(course_code=course_code).first().id,
            **marks,
        )
        recalculate_marks(row)
        db.session.add(row)
        db.session.commit()


def make_attendance(app, student_id, course_code="CS301", present=0, absent=0):
    # puts attendance records in the database, one per day going back from yesterday: the present days first, then the absent days
    with app.app_context():
        course = Course.query.filter_by(course_code=course_code).first()
        day = 1
        for status, how_many in (("Present", present), ("Absent", absent)):
            for _ in range(how_many):
                db.session.add(
                    Attendance(
                        student_id=student_id,
                        course_id=course.id,
                        record_date=date.today() - timedelta(days=day),
                        status=status,
                    )
                )
                day += 1
        db.session.commit()


def make_prediction(app, student_id, course_code="CS301", grade="B", risk="Low"):
    # puts a saved prediction in the database
    inputs = {"attendance": 90.0, "quiz": 80.0, "assignment": 85.0, "midterm": 75.0}
    with app.app_context():
        course = Course.query.filter_by(course_code=course_code).first()
        db.session.add(
            Prediction(
                student_id=student_id,
                course_id=course.id,
                predicted_grade=grade,
                risk_level=risk,
                input_snapshot=json.dumps(inputs),
            )
        )
        db.session.commit()
