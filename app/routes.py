from functools import wraps
from pathlib import Path
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .extensions import db
from .models import Students, User

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
    if role == "Administrator":
        return render_template("admin_dashboard.html")
    if role == "teacher":
        return render_template("teacher_dashboard.html")
    flash("You do not have permission to access this page.", "danger")
    return redirect(url_for("main.index"))


@main.route("/admin/students", methods=["GET", "POST"])
@login_required
@role_required("Administrator")
def admin_students():

    if request.method == "POST":
        roll_number = request.form.get("roll_number", "").strip()
        name = request.form.get("name", "").strip()
        class_name = request.form.get("class_name", "").strip()

        if not roll_number or not name or not class_name:
            flash("All fields are required.", "danger")
            return redirect(url_for("main.admin_students"))
        existing_student = Students.query.filter_by(roll_number=roll_number).first()
        if existing_student:
            flash("Student with this roll number already exists.", "danger")
            return redirect(url_for("main.admin_students"))

        student = Students(roll_number=roll_number, name=name, class_name=class_name)
        db.session.add(student)
        db.session.commit()
        flash("Student added successfully.", "success")
        return redirect(url_for("main.admin_students"))

    students = Students.query.order_by(Students.id.desc()).all()
    return render_template("admin_students.html", students=students)


#
# @main.route('/teacher/predict',methods=["POST"])
# @login_required
# @role_required("Teacher")
# def teacher_predict():
#
#
#
#
