import pickle
from functools import wraps
from pathlib import Path

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .constants import ROLE_ADMIN, ROLE_TEACHER
from .extensions import db
from .models import Student, User
from .utils import calculate_percentage, check_password_rules

# setting up the main blueprint for the app.
main = Blueprint("main", __name__)

MODEL_PATH = Path(__file__).resolve().parent / "static" / "model" / "model.pkl"


# theme switching route. This will set the theme in the session and redirect to the previous page. If the theme is not valid, it will default to dark theme.
@main.route("/set-theme/<theme>")
def set_theme(theme):
    if theme not in ("dark", "light"):
        theme = "dark"
    session["theme"] = theme
    return redirect(request.referrer or url_for("main.index"))


# makeing theme available in all templates. This will get the theme from the session and pass it to the template. If the theme is not set, it will default to dark theme.
@main.context_processor
def inject_theme():
    return {"theme": session.get("theme", "dark")}


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


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
    with MODEL_PATH.open("rb") as file:
        return pickle.load(file)


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
        else:
            flash("Invalid role selected.", "danger")
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
        return render_template("admin_dashboard.html")
    if role == ROLE_TEACHER:
        students = Student.query.order_by(Student.id.desc()).all()
        return render_template("teacher_dashboard.html", students=students)
    flash("You do not have permission to access this page.", "danger")
    return redirect(url_for("main.index"))


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

    # GET = just show the page with the list of students.
    students = Student.query.order_by(Student.id.desc()).all()
    return render_template("admin_students.html", students=students)


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


@main.route("/teacher/predict", methods=["POST"])
@login_required
@role_required(ROLE_TEACHER)
def teacher_predict():
    student_id = request.form.get("student_id", "").strip()
    attendance = request.form.get("attendance", "").strip()
    quiz = request.form.get("quiz", "").strip()
    assignment = request.form.get("assignment", "").strip()
    midterm = request.form.get("midterm", "").strip()
    if not student_id or not attendance or not quiz or not assignment or not midterm:
        flash("All fields are required.", "danger")
        return redirect(url_for("main.dashboard"))
    student = Student.query.get(student_id)
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("main.dashboard"))
    try:
        attendance = float(attendance)
        quiz = float(quiz)
        assignment = float(assignment)
        midterm = float(midterm)
    except ValueError:
        flash(
            "Attendance, quiz, assignment, and midterm must be numeric values.",
            "danger",
        )
        return redirect(url_for("main.dashboard"))
    try:
        model_bundle = load_model()
        model = model_bundle["model"]
    except FileNotFoundError:
        flash("Model file not found. Please train the model first.", "danger")
        return redirect(url_for("main.dashboard"))
    input_data = [[attendance, quiz, assignment, midterm]]
    prediction = model.predict(input_data)[0]
    percentage = calculate_percentage(attendance, quiz, assignment, midterm)
    grade = str(prediction)
    return render_template(
        "prediction.html",
        student=student,
        percentage=percentage,
        grade=grade,
    )
