import json
from datetime import date
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .config_grading import ATTENDANCE_THRESHOLD, MAX_MARKS
from .constants import ROLE_ADMIN, ROLE_TEACHER, STATUS_ABSENT, STATUS_PRESENT
from .extensions import db
from .ml import ModelNotAvailableError, predict_grade
from .models import Attendance, Course, Enrollment, Marks, Prediction, Student, User
from .utils import (
    GradeConfigError,
    attendance_percentage,
    build_prediction_inputs,
    check_password_rules,
    recalculate_marks,
    risk_from_grade,
)

# setting up the main blueprint for the app.
main = Blueprint("main", __name__)


# function to check is the user is logged in or not. If not logged in, redirect to login page. If logged in, allow access to the view function.
def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)

    return wrapped_view


# fucntion to check if the user has the required role to access the view . If not, redirect to the index page. If yes, allow access to the the view
def role_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "role" not in session or session["role"] not in allowed_roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("main.index"))
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


# setting up main route
@main.route("/")
@main.route("/home")
def index():
    return render_template("index.html")


# setting up the log in route making sure user is logged in and is saved in session and has the correct role
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            return redirect(url_for("main.dashboard"))
        flash("Invalid username or password", "danger")
    return render_template("login.html")


# route for the registration page. This will allow the user to register as an admin or teacher. If the user is already logged in, they will be redirected to the dashboard.
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        if not username or not email or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return redirect(url_for("main.register"))
        # Admin accounts are created by the seed script instead.
        role = ROLE_TEACHER
        # Check the password rules (the function lives in utils.py).
        password_problem = check_password_rules(password)
        if password_problem:
            flash(password_problem, "danger")
            return redirect(url_for("main.register"))
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("main.register"))
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash("Username or email already exists.", "danger")
            return redirect(url_for("main.register"))
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
        )
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")


# route for the loggin out of the app. This will clear the session and redirect to the login page
@main.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))


# route for the dashboard. This will check the role of the user and render the appropriate dashboard template. If the user does not have permission, they will be redirected to the index page with a flash message.
@main.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role")
    if role == ROLE_ADMIN:
        # .count() asks the database for just the number, not all the rows.
        student_count = Student.query.count()
        course_count = Course.query.count()
        teacher_count = User.query.filter_by(role=ROLE_TEACHER).count()
        return render_template(
            "admin_dashboard.html",
            student_count=student_count,
            course_count=course_count,
            teacher_count=teacher_count,
        )
        return render_template(
            "teacher_dashboard.html",
            my_courses=my_courses,
        )
    flash("You do not have permission to access this page.", "danger")
    return redirect(url_for("main.index"))


@main.route("/teacher/courses/<int:course_id>")
@login_required
@role_required(ROLE_TEACHER)
def teacher_course(course_id):
    course = Course.query.get(course_id)
    if course is None or course.teacher_id != session["user_id"]:
        flash("Course not found.", "danger")
        return redirect(url_for("main.dashboard"))
    return render_template("teacher_course.html", course=course)


# route for the page where a teacher can type in the marks for one assesment of one course. This will allow the teacher to enter the marks for each student in the course
@main.route("/teacher/marks", methods=["GET", "POST"])
@login_required
@role_required(ROLE_TEACHER)
def teacher_marks():
    # The courses for the dropdown: only this teacher's own.
    my_courses = (
        Course.query.filter_by(teacher_id=session["user_id"])
        .order_by(Course.course_code)
        .all()
    )

    course_id = request.args.get("course", "")
    assessment = request.args.get("assessment", "")

    # Find the chosen course and check it belongs to this teacher.
    course = None
    if course_id.isdigit():
        course = Course.query.get(int(course_id))
        if course is None or course.teacher_id != session["user_id"]:
            flash("Course not found.", "danger")
            return redirect(url_for("main.teacher_marks"))

    # The assessment must be one of the names in config_grading.py.
    if assessment and assessment not in MAX_MARKS:
        flash("Unknown assessment.", "danger")
        return redirect(url_for("main.teacher_marks"))

    # Only when BOTH are chosen do we show the list of students.
    show_students = course is not None and assessment != ""
    max_mark = MAX_MARKS.get(assessment)
    typed = {}  # what the teacher typed, so we can put it back if there is an error

    if request.method == "POST":
        if not show_students:
            flash("Choose a course and an assessment first.", "danger")
            return redirect(url_for("main.teacher_marks"))

        typed = request.form
        new_marks = {}
        problems = []  # error messages

        for enrollment in course.enrollments:
            student = enrollment.student
            text = request.form.get(f"mark_{student.id}", "").strip()

            if text == "":
                continue  # nothing typed, so leave this student as they are

            try:
                value = float(text)
            except ValueError:
                problems.append(f"{student.name}: '{text}' is not a number.")
                continue

            if value < 0 or value > max_mark:
                problems.append(
                    f"{student.name}: the mark must be between 0 and {max_mark}."
                )
                continue

            new_marks[student.id] = value

        if problems:
            for problem in problems:
                flash(problem, "danger")
        elif not new_marks:
            flash("No marks were entered.", "warning")
        else:
            try:
                for student_id, value in new_marks.items():
                    marks = Marks.query.filter_by(
                        student_id=student_id, course_id=course.id
                    ).first()
                    if marks is None:
                        marks = Marks(student_id=student_id, course_id=course.id)
                        db.session.add(marks)

                    setattr(marks, assessment, value)
                    recalculate_marks(marks)

                db.session.commit()
            except GradeConfigError as error:
                db.session.rollback()
                flash(
                    f"Grading configuration error: {error}. Please fix the grading settings.",
                    "danger",
                )
            except Exception:
                db.session.rollback()
                flash(
                    "The marks could not be saved. Nothing was changed, please try again.",
                    "danger",
                )
            else:
                flash(f"Saved {len(new_marks)} mark(s).", "success")
                return redirect(
                    url_for(
                        "main.teacher_marks", course=course.id, assessment=assessment
                    )
                )

    existing = {}
    if show_students:
        for marks in Marks.query.filter_by(course_id=course.id).all():
            value = getattr(marks, assessment)
            if value is not None:
                existing[marks.student_id] = f"{value:g}"

    return render_template(
        "teacher_marks.html",
        my_courses=my_courses,
        course=course,
        assessment=assessment,
        assessments=MAX_MARKS,
        max_mark=max_mark,
        show_students=show_students,
        existing=existing,
        typed=typed,
    )


# route for the page where a teacher can type in the attendance for one course. This will allow the teacher to enter the attendance for each student in the course
@main.route("/teacher/attendance", methods=["GET", "POST"])
@login_required
@role_required(ROLE_TEACHER)
def teacher_attendance():
    my_courses = (
        Course.query.filter_by(teacher_id=session["user_id"])
        .order_by(Course.course_code)
        .all()
    )
    course_id = request.args.get("course", "")
    date_text = request.args.get("date", "")

    course = None
    if course_id.isdigit():
        course = Course.query.get(int(course_id))
        if course is None or course.teacher_id != session["user_id"]:
            flash("Course not found.", "danger")
            return redirect(url_for("main.teacher_attendance"))

    chosen_date = None
    if date_text:
        try:
            chosen_date = date.fromisoformat(date_text)
        except ValueError:
            flash("Please choose a valid date.", "danger")
            return redirect(url_for("main.teacher_attendance"))
        if chosen_date > date.today():
            flash("You cannot choose a future date.", "danger")
            return redirect(url_for("main.teacher_attendance"))

    show_students = course is not None and chosen_date is not None

    saved_records = {}
    if show_students:
        records = Attendance.query.filter_by(
            course_id=course.id, record_date=chosen_date
        ).all()
        for record in records:
            saved_records[record.student_id] = record.status
    already_recorded = len(saved_records) > 0

    typed = {}
    if request.method == "POST":
        if not show_students:
            flash("Choose a course and a date first.", "danger")
            return redirect(url_for("main.teacher_attendance"))

        if already_recorded:
            flash(
                "Attendance for this date has already been recorded. You cannot change it.",
                "danger",
            )
        elif len(course.enrollments) == 0:
            flash("There are no students enrolled in this course.", "danger")
        else:
            statuses = {}
            for enrollment in course.enrollments:
                status = request.form.get(f"status_{enrollment.student_id}", "").strip()
                if status == STATUS_PRESENT or status == STATUS_ABSENT:
                    statuses[enrollment.student_id] = status
            if len(statuses) < len(course.enrollments):
                flash("You must mark all students as present or absent.", "danger")
            else:
                try:
                    for student_id, status in statuses.items():
                        db.session.add(
                            Attendance(
                                student_id=student_id,
                                course_id=course.id,
                                record_date=chosen_date,
                                status=status,
                            )
                        )
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    flash(
                        "The attendance could not be saved. Nothing was changed, please try again.",
                        "danger",
                    )
                else:
                    flash(
                        f"Saved attendance for {len(statuses)} student(s).", "success"
                    )

                    low_attendance = []
                    for enrollment in course.enrollments:
                        percent = attendance_percentage(
                            enrollment.student_id, course.id
                        )
                        if percent is not None and percent < ATTENDANCE_THRESHOLD:
                            low_attendance.append(enrollment.student.name)
                    if low_attendance:
                        flash(
                            "Warning: The following students have low attendance: "
                            + ", ".join(low_attendance),
                            "warning",
                        )
                    return redirect(
                        url_for(
                            "main.teacher_attendance",
                            course=course.id,
                            date=chosen_date,
                        )
                    )
    summary = []
    if course is not None:
        for enrollment in course.enrollments:
            student = enrollment.student
            percent = attendance_percentage(student.id, course.id)
            summary.append(
                {
                    "student": student,
                    "percent": percent,
                }
            )
    return render_template(
        "teacher_attendance.html",
        my_courses=my_courses,
        course=course,
        date_value=date_text or date.today().isoformat(),
        chosen_date=chosen_date,
        show_students=show_students,
        already_recorded=already_recorded,
        saved_records=saved_records,
        summary=summary,
        typed=typed,
        threshold=ATTENDANCE_THRESHOLD,
    )


# Page where a teacher sees the marks, percentage and grade of every student in a course.
# The URL carries the choice: /teacher/grades?course=1&sort=grade
@main.route("/teacher/grades")
@login_required
@role_required(ROLE_TEACHER)
def teacher_grades():
    # The courses for the dropdown: only this teacher's own.
    my_courses = (
        Course.query.filter_by(teacher_id=session["user_id"])
        .order_by(Course.course_code)
        .all()
    )

    course_id = request.args.get("course", "")
    sort = request.args.get("sort", "name")

    # Find the chosen course and check it belongs to this teacher.
    course = None
    if course_id.isdigit():
        course = Course.query.get(int(course_id))
        if course is None or course.teacher_id != session["user_id"]:
            flash("Course not found.", "danger")
            return redirect(url_for("main.teacher_grades"))

    rows = []  # one dictionary per enrolled student, for the table
    has_marks = False  # becomes True if at least one mark exists in this course

    if course is not None:
        # All the Marks rows of this course, looked up by student id.
        marks_by_student = {}
        for marks in Marks.query.filter_by(course_id=course.id).all():
            marks_by_student[marks.student_id] = marks

        for enrollment in course.enrollments:
            student = enrollment.student
            marks = marks_by_student.get(student.id)  # None if no marks at all yet

            row = {"student": student, "percentage": None, "grade": None, "missing": []}

            # Copy each of the four marks into the row, and note the missing ones.
            for name in MAX_MARKS:
                value = None
                if marks is not None:
                    value = getattr(marks, name)
                row[name] = value

                if value is None:
                    row["missing"].append(name)
                else:
                    has_marks = True

            if marks is not None:
                row["percentage"] = marks.percentage
                row["grade"] = marks.grade
            rows.append(row)

        # Put the rows in the order the teacher asked for.
        if sort == "roll":
            rows.sort(key=lambda row: row["student"].roll_number)
        elif sort == "grade":
            # Highest percentage first. Students without a grade go at the end.
            graded = []
            not_graded = []
            for row in rows:
                if row["percentage"] is None:
                    not_graded.append(row)
                else:
                    graded.append(row)
            graded.sort(key=lambda row: row["percentage"], reverse=True)
            rows = graded + not_graded
        else:
            sort = "name"
            rows.sort(key=lambda row: row["student"].name.lower())

    return render_template(
        "teacher_grades.html",
        my_courses=my_courses,
        course=course,
        sort=sort,
        rows=rows,
        has_marks=has_marks,
        max_marks=MAX_MARKS,
    )


# route for the admin to manage students. This will allow the admin to add new students and view the list of existing students. If the user does not have permission, they will be redirected to the index page with a flash message.
@main.route("/admin/students", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def admin_students():
    # POST = the admin submitted the "Add Student" form.
    if request.method == "POST":
        roll_number = request.form.get("roll_number", "").strip()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        contact = request.form.get("contact", "").strip()

        # Reject the form if any field is empty.
        if not roll_number or not name or not email or not contact:
            flash("All fields are required.", "danger")
            return redirect(url_for("main.admin_students"))

        # The database refuses duplicates, so we check first and show a friendly message.
        if Student.query.filter_by(roll_number=roll_number).first():
            flash("Student with this roll number already exists.", "danger")
            return redirect(url_for("main.admin_students"))
        if Student.query.filter_by(email=email).first():
            flash("Student with this email already exists.", "danger")
            return redirect(url_for("main.admin_students"))

        student = Student(
            roll_number=roll_number, name=name, email=email, contact=contact
        )
        db.session.add(student)  # stage the new row
        db.session.commit()  # actually save it to the database
        flash("Student added successfully.", "success")
        return redirect(url_for("main.admin_students"))

    # GET = show the list. If the URL has ?q=something, only show matches.
    # request.args holds whatever comes after the "?" in the URL.
    search_text = request.args.get("q", "").strip()

    query = Student.query
    if search_text:
        # % means "anything". ilike is a case-insensitive "contains" match.
        pattern = f"%{search_text}%"
        query = query.filter(
            db.or_(Student.name.ilike(pattern), Student.roll_number.ilike(pattern))
        )
    students = query.order_by(Student.id.desc()).all()
    return render_template(
        "admin_students.html", students=students, search_text=search_text
    )


# route for the admin to edit a student. This will allow the admin to edit the student's details. If the user does not have permission, they will be redirected to the index page with a flash message.
@main.route("/admin/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def admin_edit_student(student_id):
    student = Student.query.get(student_id)
    # Look the student up in the database. If they don't exist, show an error and redirect to the student list.
    if student is None:
        flash("Student not found.", "danger")
        return redirect(url_for("main.admin_students"))
    # POST = the admin submitted the "Edit Student" form.
    if request.method == "POST":
        roll_number = request.form.get("roll_number", "").strip()
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        contact = request.form.get("contact", "").strip()
        # Reject the form if any field is empty.
        if not roll_number or not name or not email or not contact:
            flash("All fields are required.", "danger")
            return redirect(url_for("main.admin_edit_student", student_id=student_id))

        same_roll = Student.query.filter_by(roll_number=roll_number).first()
        if same_roll and same_roll.id != student.id:
            flash("Student with this roll number already exists.", "danger")
            return redirect(url_for("main.admin_edit_student", student_id=student_id))
        same_email = Student.query.filter_by(email=email).first()
        if same_email and same_email.id != student.id:
            flash("Student with this email already exists.", "danger")
            return redirect(url_for("main.admin_edit_student", student_id=student_id))
        student.roll_number = roll_number
        student.name = name
        student.email = email
        student.contact = contact
        db.session.commit()  # save the changes to the database
        flash("Student updated successfully.", "success")
        return redirect(url_for("main.admin_students"))
    return render_template("admin_edit_student.html", student=student)


# route for the admin to delete a student. This will delete the student and all their marks, attendance and predictions. If the user does not have permission, they will be redirected to the index page with a flash message.
@main.route("/admin/students/<int:student_id>/delete", methods=["POST"])
@login_required
@role_required(ROLE_ADMIN)
def admin_delete_student(student_id):
    student = Student.query.get(student_id)
    if student is None:
        flash("Student not found.", "danger")
        return redirect(url_for("main.admin_students"))
    name = student.name
    db.session.delete(student)
    db.session.commit()
    flash(f"Student '{name}' deleted successfully.", "success")
    return redirect(url_for("main.admin_students"))


# route for the admin to manage courses. This will allow the admin to add new courses and view the list of existing courses. If the user does not have permission, they will be redirected to the index page with a flash message.
@main.route("/admin/courses", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def admin_courses():
    if request.method == "POST":
        course_name = request.form.get("course_name", "").strip()
        course_code = request.form.get("course_code", "").strip().upper()
        teacher_id = request.form.get("teacher_id", "").strip()

        if not course_name or not course_code or not teacher_id:
            flash("All fields are required.", "danger")
            return redirect(url_for("main.admin_courses"))

        teacher = None
        if teacher_id.isdigit():
            teacher = User.query.get(int(teacher_id))

        if teacher is None or teacher.role != ROLE_TEACHER:
            flash("Invalid teacher ID.", "danger")
            return redirect(url_for("main.admin_courses"))
        if Course.query.filter_by(course_code=course_code).first():
            flash("Course with this code already exists.", "danger")
            return redirect(url_for("main.admin_courses"))
        course = Course(
            course_name=course_name, course_code=course_code, teacher_id=teacher.id
        )
        db.session.add(course)
        db.session.commit()
        flash("Course added successfully.", "success")
        return redirect(url_for("main.admin_courses"))

    courses = Course.query.order_by(Course.course_code).all()
    teachers = User.query.filter_by(role=ROLE_TEACHER).order_by(User.username).all()
    return render_template("admin_courses.html", courses=courses, teachers=teachers)


# Route for the admin to mangane who is enrolled in which courses. GET shows the page. POST adds the chosen student to the course.
@main.route("/admin/courses/<int:course_id>/enroll", methods=["GET", "POST"])
@login_required
@role_required(ROLE_ADMIN)
def admin_enroll(course_id):
    course = Course.query.get(course_id)
    if course is None:
        flash("Course not found.", "danger")
        return redirect(url_for("main.admin_courses"))

    # post = the admin submitted the "Enroll Student" form.
    if request.method == "POST":
        student_id = request.form.get("student_id", "")

        student = None
        if student_id.isdigit():
            student = Student.query.get(int(student_id))
        if student is None:
            flash("Invalid student ID.", "danger")
            return redirect(url_for("main.admin_enroll", course_id=course_id))
        # Check if the student is already enrolled in the course.

        already_enrolled = Enrollment.query.filter_by(
            student_id=student_id, course_id=course_id
        ).first()
        if already_enrolled:
            flash("Student is already enrolled in this course.", "danger")
            return redirect(url_for("main.admin_enroll", course_id=course_id))

        enrollment = Enrollment(student_id=student.id, course_id=course.id)
        db.session.add(enrollment)
        db.session.commit()
        flash(
            f"Student '{student.name}' enrolled in course '{course.course_name}'.",
            "success",
        )
        return redirect(url_for("main.admin_enroll", course_id=course_id))
        # Get work out which students are not enrolled yet for the dropdown list.
    enrolled_ids = [enrollment.student_id for enrollment in course.enrollments]
    available_students = (
        Student.query.filter(Student.id.notin_(enrolled_ids))
        .order_by(Student.name)
        .all()
    )

    return render_template(
        "admin_enroll.html", course=course, available_students=available_students
    )


# route to remove one student form a course post request only.
@main.route(
    "/admin/courses/<int:course_id>/unenroll/<int:student_id>", methods=["POST"]
)
@login_required
@role_required(ROLE_ADMIN)
def admin_unenroll(course_id, student_id):
    enrollment = Enrollment.query.filter_by(
        student_id=student_id, course_id=course_id
    ).first()
    if enrollment is None:
        flash("Enrollment not found.", "danger")
    else:
        db.session.delete(enrollment)
        db.session.commit()
        flash("Student removed from the course.", "success")
    return redirect(url_for("main.admin_enroll", course_id=course_id))


@main.route("/teacher/predict", methods=["GET", "POST"])
@login_required
@role_required(ROLE_TEACHER)
def teacher_predict():
    my_courses = (
        Course.query.filter_by(teacher_id=session["user_id"])
        .order_by(Course.course_code)
        .all()
    )

    course_id = request.args.get("course", "")

    course = None
    if course_id.isdigit():
        course = Course.query.get(int(course_id))
        if course is None or course.teacher_id != session["user_id"]:
            flash("Course not found.", "danger")
            return redirect(url_for("main.teacher_predict"))

    selected_student_id = ""  # keeps the chosen student in the dropdown after an error

    if request.method == "POST":
        if course is None:
            flash("Choose a course first.", "danger")
            return redirect(url_for("main.teacher_predict"))

        selected_student_id = request.form.get("student_id", "")

        enrollment = None
        if selected_student_id.isdigit():
            enrollment = Enrollment.query.filter_by(
                student_id=int(selected_student_id), course_id=course.id
            ).first()

        if enrollment is None:
            flash("Please choose a student who is enrolled in this course.", "danger")
        else:
            student = enrollment.student

            inputs, missing = build_prediction_inputs(student.id, course.id)

            if missing:
                flash(
                    f"There is not enough data to predict for {student.name}. "
                    f"Missing: {', '.join(missing)}.",
                    "danger",
                )
            else:
                try:
                    grade = predict_grade(
                        inputs["attendance"],
                        inputs["quiz"],
                        inputs["assignment"],
                        inputs["midterm"],
                    )
                    prediction = Prediction(
                        student_id=student.id,
                        course_id=course.id,
                        predicted_grade=grade,
                        risk_level=risk_from_grade(grade),
                        # json.dumps turns the dictionary into text, so it fits in one column
                        input_snapshot=json.dumps(inputs),
                    )
                    db.session.add(prediction)
                    db.session.commit()
                except ModelNotAvailableError as error:
                    db.session.rollback()
                    flash(f"The prediction model is unavailable. {error}", "danger")
                except Exception:
                    db.session.rollback()
                    flash(
                        "The prediction failed. Nothing was saved, please try again.",
                        "danger",
                    )
                else:
                    flash("Prediction saved.", "success")
                    return redirect(
                        url_for(
                            "main.teacher_predict",
                            course=course.id,
                            prediction=prediction.id,
                        )
                    )

    result = None
    result_inputs = {}
    prediction_id = request.args.get("prediction", "")
    if course is not None and prediction_id.isdigit():
        result = Prediction.query.filter_by(
            id=int(prediction_id), course_id=course.id
        ).first()
        if result is not None:
            result_inputs = json.loads(
                result.input_snapshot
            )  # text back to a dictionary

    return render_template(
        "teacher_predict.html",
        my_courses=my_courses,
        course=course,
        selected_student_id=selected_student_id,
        result=result,
        result_inputs=result_inputs,
    )
