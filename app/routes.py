from flask import Blueprint, render_template, url_for
from werkzeug.security import check_password_hash

from .extensions import db
from .models import Students, User

main = Blueprint("main", __name__)


@main.route("/")
@main.route("/home")
def index():
    return render_template("index.html")
