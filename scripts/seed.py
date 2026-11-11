import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash

from app import create_app
from app.constants import ROLE_ADMIN, ROLE_TEACHER, STATUS_ABSENT, STATUS_PRESENT
from app.extensions import db
from app.ml import ModelNotAvailableError, predict_grade
from app.models import Attendance, Course, Enrollment, Marks, Prediction, Student, User
from app.utils import build_prediction_inputs, recalculate_marks, risk_from_grade

app = create_app()

with app.app_context():

    db.drop_all()
    db.create_all()

    admin = User(
        username="admin",
        email="admin@school.com",
        password_hash=generate_password_hash("Admin@123"),
        role=ROLE_ADMIN,
    )
    teacher1 = User(
        username="teacher1",
        email="teacher1@school.com",
        password_hash=generate_password_hash("Valid@123"),
        role=ROLE_TEACHER,
    )
    existing = User(
        username="existing_teacher",
        email="existing.teacher@school.com",
        password_hash=generate_password_hash("Valid@123"),
        role=ROLE_TEACHER,
    )
    db.session.add_all([admin, teacher1, existing])
    db.session.commit()  # commit now so these users get their ids

    cs301 = Course(
        course_name="Data Structures", course_code="CS301", teacher_id=teacher1.id
    )
    cs302 = Course(course_name="Databases", course_code="CS302", teacher_id=teacher1.id)
    cs303 = Course(
        course_name="Software Engineering", course_code="CS303", teacher_id=teacher1.id
    )
    db.session.add_all([cs301, cs302, cs303])

    student_data = [
        ("Sara Khan", "SP24-BSCS-045", "sara.khan@student.edu", "03001234567"),
        ("Ali Hassan", "SP24-BSCS-046", "ali.hassan@student.edu", "03011234567"),
        ("Ayesha Malik", "SP24-BSCS-047", "ayesha.malik@student.edu", "03021234567"),
        ("Usman Tariq", "SP24-BSCS-048", "usman.tariq@student.edu", "03031234567"),
        ("Fatima Noor", "SP24-BSCS-049", "fatima.noor@student.edu", "03041234567"),
        ("Hamza Ahmed", "SP24-BSCS-050", "hamza.ahmed@student.edu", "03051234567"),
        ("Zainab Iqbal", "SP24-BSCS-051", "zainab.iqbal@student.edu", "03061234567"),
        ("Bilal Raza", "SP24-BSCS-052", "bilal.raza@student.edu", "03071234567"),
        ("Hira Saeed", "SP24-BSCS-053", "hira.saeed@student.edu", "03081234567"),
        ("Danish Ali", "SP24-BSCS-054", "danish.ali@student.edu", "03091234567"),
        ("Maryam Aslam", "SP24-BSCS-055", "maryam.aslam@student.edu", "03101234567"),
        ("Talha Mehmood", "SP24-BSCS-056", "talha.mehmood@student.edu", "03111234567"),
    ]

    students = []
    for name, roll, email, contact in student_data:
        student = Student(name=name, roll_number=roll, email=email, contact=contact)
        db.session.add(student)
        students.append(student)  # keep them in a list so we can pick some below

    for student in students[0:10]:
        db.session.add(
            Enrollment(student=student, course=cs301)
        )  # CS301: students 1-10
    for student in students[0:5]:
        db.session.add(Enrollment(student=student, course=cs302))  # CS302: students 1-5
    for student in students[5:10]:
        db.session.add(
            Enrollment(student=student, course=cs303)
        )  # CS303: students 6-10

    marks_data = [
        (0, 9, 19, 27, 36),  # Sara Khan: everything entered, a strong student
        (1, 7, 15, 22, 28),
        (2, 8, 17, 24, None),  # no final exam mark yet
        (3, 5, 12, 16, 20),
        (4, 9, 18, 26, None),
        (5, 4, 9, 12, 15),
        (6, 3, 7, 10, 12),  # a weak student
        (7, 6, 13, 18, None),
        # position 8 (Hira Saeed) is left out on purpose: no marks at all
        (9, 7, None, None, None),  # Danish Ali: only the quiz so far
    ]

    for position, quiz, assignment, midterm, final in marks_data:
        marks = Marks(
            student=students[position],
            course=cs301,
            quiz=quiz,
            assignment=assignment,
            midterm=midterm,
            final=final,
        )
        recalculate_marks(
            marks
        )  # works out the percentage and grade (or leaves them empty)
        db.session.add(marks)

    class_days = []
    day = date.today()
    while len(class_days) < 10:
        day = day - timedelta(days=1)
        if day.weekday() < 5:
            class_days.append(day)

    # How many of the 10 days each student missed: {position: number of absences}.
    absences = {0: 0, 1: 1, 2: 1, 3: 3, 4: 0, 5: 4, 6: 5, 7: 2}

    for position, missed in absences.items():
        for number, class_day in enumerate(class_days):
            # The first "missed" days of the list count as absent, the rest as present.
            if number < missed:
                status = STATUS_ABSENT
            else:
                status = STATUS_PRESENT

            db.session.add(
                Attendance(
                    student=students[position],
                    course=cs301,
                    record_date=class_day,
                    status=status,
                )
            )
    db.session.commit()
    try:
        for position in range(8):
            student = students[position]
            inputs, missing = build_prediction_inputs(student.id, cs301.id)
            if missing:
                continue  # not enough data for this student, so skip them

            grade = predict_grade(
                inputs["attendance"],
                inputs["quiz"],
                inputs["assignment"],
                inputs["midterm"],
            )
            db.session.add(
                Prediction(
                    student_id=student.id,
                    course_id=cs301.id,
                    predicted_grade=grade,
                    risk_level=risk_from_grade(grade),
                    input_snapshot=json.dumps(inputs),
                )
            )
        db.session.commit()
    except ModelNotAvailableError:
        print("No trained model found, so no predictions were created.")
        print("Run: python scripts/train_model.py   then run this script again.")
    print("Done! Demo logins:")
    print("  admin     ->  admin@school.com    /  Admin@123")
    print("  teacher   ->  teacher1@school.com /  Valid@123")
