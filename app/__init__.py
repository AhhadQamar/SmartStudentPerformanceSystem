import os
from datetime import timedelta

from flask import Flask

from .constants import SESSION_TIMEOUT_MINUTES
from .extensions import csrf, db
from .routes import main


# test_config is optional, the tests use it to give the app a temporary database and turn csrf off. The normal app is started without it
def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///students.db"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    # so only an idle user is logged out after SESSIONTIMEOUT_MINUTES, not a user who is actively using the app
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
        minutes=SESSION_TIMEOUT_MINUTES
    )

    # if the tests gave us settings, use them instead of the normal ones
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    csrf.init_app(app)
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()

    return app
