from flask import Blueprint, flash, redirect, render_template, request, url_for, session
from werkzeug.security import check_password_hash

from .extensions import db
from .models import Students, User

main = Blueprint("main", __name__)


@main.route("/")
@main.route("/home")
def index():
    return render_template("index.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            return redirect(url_for("main.index"))

        flash("Invalid username or password", "danger")

    return render_template("login.html")


@main.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))
