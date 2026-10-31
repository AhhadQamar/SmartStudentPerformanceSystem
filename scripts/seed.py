# Fills the database with demo data so we don't have to type it by hand.
# WARNING: it erases everything first, then creates fresh data.

import os
import sys

# This script lives in the "scripts" folder, but it needs to import from
# the "app" folder. This line tells Python to also look in the main folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash

from app import create_app
from app.constants import ROLE_ADMIN, ROLE_TEACHER
from app.extensions import db
from app.models import Course, Enrollment, Student, User

app = create_app()

# Database commands only work inside an "app context". Think of it as
# "the app is switched on, so db knows which database to talk to".
with app.app_context():

    # ---- 1. Start fresh: delete all tables, then create them again ----
    db.drop_all()
    db.create_all()

    # ---- 2. Users (passwords are stored hashed, just like in register) ----
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

    # ---- 3. Courses, all taught by teacher1 ----
    cs301 = Course(
        course_name="Data Structures", course_code="CS301", teacher_id=teacher1.id
    )
    cs302 = Course(course_name="Databases", course_code="CS302", teacher_id=teacher1.id)
    cs303 = Course(
        course_name="Software Engineering", course_code="CS303", teacher_id=teacher1.id
    )
    db.session.add_all([cs301, cs302, cs303])

    # ---- 4. Students: (name, roll number, email, contact) ----
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

    # ---- 5. Enrollments: who takes which course ----
    # students[0:10] means "the first 10 students" (positions 0 to 9).
    # Because of the "backref" in models.py, we can write student=... and
    # course=... directly instead of looking up ids ourselves.
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
    # Students 11 and 12 are not enrolled anywhere yet. That is on purpose:
    # later we use them to test "student not enrolled in this course".

    db.session.commit()

    print("Done! Demo logins:")
    print("  admin     ->  admin@school.com    /  Admin@123")
    print("  teacher   ->  teacher1@school.com /  Valid@123")
