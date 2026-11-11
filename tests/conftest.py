# shared setup for all the tests, pytest finds this file on its own.
# a fixture is a function that gets something ready for a test. A test asks for it by writing its name as a parameter.

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.constants import ROLE_ADMIN, ROLE_TEACHER
from app.extensions import db
from app.models import Course, User
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    OTHER_TEACHER_EMAIL,
    OTHER_TEACHER_PASSWORD,
    TEACHER_EMAIL,
    TEACHER_PASSWORD,
    login,
)


@pytest.fixture
def app(tmp_path):
    # makes a new app with its own empty database for every test, so tests can't affect each other and the real database is never touched.
    # (tmp_path is a temporary folder that pytest makes and deletes)
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
            "WTF_CSRF_ENABLED": False,  # the tests don't send csrf tokens
            "SECRET_KEY": "test-secret-key",
        }
    )

    with app.app_context():
        admin = User(
            username="admin",
            email=ADMIN_EMAIL,
            password_hash=generate_password_hash(ADMIN_PASSWORD),
            role=ROLE_ADMIN,
        )
        teacher = User(
            username="teacher1",
            email=TEACHER_EMAIL,
            password_hash=generate_password_hash(TEACHER_PASSWORD),
            role=ROLE_TEACHER,
        )
        other_teacher = User(
            username="existing_teacher",
            email=OTHER_TEACHER_EMAIL,
            password_hash=generate_password_hash(OTHER_TEACHER_PASSWORD),
            role=ROLE_TEACHER,
        )
        db.session.add_all([admin, teacher, other_teacher])
        db.session.commit()

        # three courses, all taught by teacher1
        db.session.add_all(
            [
                Course(course_name="Data Structures", course_code="CS301", teacher_id=teacher.id),
                Course(course_name="Databases", course_code="CS302", teacher_id=teacher.id),
                Course(course_name="Software Engineering", course_code="CS303", teacher_id=teacher.id),
            ]
        )
        db.session.commit()

    yield app  # the test runs here

    with app.app_context():
        db.session.remove()
        db.engine.dispose()  # close the database file


@pytest.fixture
def client(app):
    # a browser that is not logged in
    return app.test_client()


@pytest.fixture
def admin_client(app):
    # a browser logged in as the admin
    client = app.test_client()
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    return client


@pytest.fixture
def teacher_client(app):
    # a browser logged in as teacher1 (teaches CS301, CS302, CS303)
    client = app.test_client()
    login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    return client


@pytest.fixture
def other_teacher_client(app):
    # a browser logged in as the other teacher, who has no courses
    client = app.test_client()
    login(client, OTHER_TEACHER_EMAIL, OTHER_TEACHER_PASSWORD)
    return client


# the prediction model, for the UC07 to UC10 tests


@pytest.fixture(scope="session")
def trained_model_path(tmp_path_factory):
    # trains a real model once for the whole run (takes a second or two) and saves it in a temp folder, not in app/ml_models
    import app.ml as ml

    folder = tmp_path_factory.mktemp("model")
    patch = pytest.MonkeyPatch()
    patch.setattr(ml, "MODEL_PATH", folder / "model.pkl")
    patch.setattr(ml, "LOG_PATH", folder / "training.log")
    try:
        ml.train_model()
    finally:
        patch.undo()
    return folder / "model.pkl"


@pytest.fixture
def model_ready(monkeypatch, trained_model_path, tmp_path):
    # makes the app use the temp model for one test
    import app.ml as ml

    monkeypatch.setattr(ml, "MODEL_PATH", trained_model_path)
    monkeypatch.setattr(ml, "LOG_PATH", tmp_path / "training.log")
