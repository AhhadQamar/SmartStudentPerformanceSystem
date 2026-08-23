from flask import Flask
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import User
from .routes import main


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///students.db"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "your_secret_key"

    db.init_app(app)
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()

        try:
            user_count = User.query.count()
        except Exception:
            db.session.rollback()
            db.drop_all()
            db.create_all()

    return app
