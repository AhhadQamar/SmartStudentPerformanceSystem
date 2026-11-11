from datetime import date, datetime

from .extensions import db


# A user that can log in: an admin or a teacher.
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")


# A student, they do not log in, but they have grades.
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    enrollments = db.relationship(
        "Enrollment", backref="student", cascade="all, delete-orphan"
    )
    marks = db.relationship("Marks", backref="student", cascade="all, delete-orphan")
    attendance_records = db.relationship(
        "Attendance", backref="student", cascade="all, delete-orphan"
    )
    predictions = db.relationship(
        "Prediction", backref="student", cascade="all, delete-orphan"
    )


# A course, which is taught by a teacher and has many students enrolled.
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(100), nullable=False)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    teacher = db.relationship("User")
    enrollments = db.relationship(
        "Enrollment", backref="course", cascade="all, delete-orphan"
    )
    marks = db.relationship("Marks", backref="course", cascade="all, delete-orphan")
    attendance_records = db.relationship(
        "Attendance", backref="course", cascade="all, delete-orphan"
    )
    predictions = db.relationship(
        "Prediction", backref="course", cascade="all, delete-orphan"
    )


# Enrollment, Marks, Attendance and Prediction connect students to courses. They store who is enrolled, the marks, the attendance and the predictions.
# Enrollment, Marks and Attendance have a unique constraint so the same record can't be saved twice. Prediction doesn't, because a student can be predicted many times and we keep all of them as history.
class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    enrollment_date = db.Column(db.Date, default=date.today)
    # a student can only be enrolled in a course once, so we add a unique constraint on (student_id, course_id)
    __table_args__ = (db.UniqueConstraint("student_id", "course_id"),)


# Marks model stores the quiz, assignment, midterm and final marks of a student in a course, plus the percentage and grade that are worked out from them.
# the percentage and grade are filled in by recalculate_marks() in utils.py. The unique constraint means one set of marks per student per course.


class Marks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    quiz = db.Column(db.Float)
    assignment = db.Column(db.Float)
    midterm = db.Column(db.Float)
    final = db.Column(db.Float)

    percentage = db.Column(db.Float)
    grade = db.Column(db.String(2))

    __table_args__ = (db.UniqueConstraint("student_id", "course_id"),)


# Attendance model represents the attendance records of a student in a course, including the date of the record and whether the student was present or absent. The unique constraint ensures that a student can only have one attendance record per course per date.


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    record_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)  # "Present" or "Absent"

    __table_args__ = (db.UniqueConstraint("student_id", "course_id", "record_date"),)


# Prediction model stores one prediction: the predicted grade, the risk level, the input values that were used and the date.
# no unique constraint here on purpose, a student can be predicted many times and that is the prediction history.
class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    course_id = db.Column(
        db.Integer, db.ForeignKey("course.id"), nullable=False, index=True
    )
    predicted_grade = db.Column(db.String(2), nullable=False)
    risk_level = db.Column(db.String(20), nullable=False)  # "High", "Medium", "Low"

    input_snapshot = db.Column(db.Text)
    prediction_date = db.Column(db.DateTime, default=datetime.now)
