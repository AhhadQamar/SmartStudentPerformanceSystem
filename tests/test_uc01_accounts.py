# UC01: register, login and session timeout.
# one test for each test case in the design document, the docstring is the expected result.

import time
from datetime import timedelta

from app.constants import ROLE_TEACHER
from app.models import User
from helpers import (
    TEACHER_EMAIL,
    TEACHER_PASSWORD,
    OTHER_TEACHER_EMAIL,
    login,
    page_text,
)


def test_TC_UC01_01_register_new_teacher(client, app):
    """Register a new teacher. The account is created and the user is sent to the login page."""
    response = client.post(
        "/register",
        data={
            "username": "ali_raza",
            "email": "ali.raza@newuser.com",
            "password": "Pass@123",
            "confirm_password": "Pass@123",
        },
        follow_redirects=True,
    )

    assert "Registration successful" in page_text(response)
    with app.app_context():
        user = User.query.filter_by(email="ali.raza@newuser.com").first()
        assert user is not None
        assert user.role == ROLE_TEACHER


def test_TC_UC01_02_register_with_used_email(client, app):
    """Register with an email that is already used. An error is shown and no second account is made."""
    response = client.post(
        "/register",
        data={
            "username": "someone_else",
            "email": OTHER_TEACHER_EMAIL,
            "password": "Pass@123",
            "confirm_password": "Pass@123",
        },
        follow_redirects=True,
    )

    assert "already exists" in page_text(response)
    with app.app_context():
        assert User.query.filter_by(email=OTHER_TEACHER_EMAIL).count() == 1
        assert User.query.filter_by(username="someone_else").count() == 0


def test_TC_UC01_03_login_with_correct_details(client):
    """Log in with a correct email and password. A session is created and the teacher dashboard opens."""
    response = login(client, TEACHER_EMAIL, TEACHER_PASSWORD)

    assert "My Courses" in page_text(response)
    with client.session_transaction() as session:
        assert session["role"] == "teacher"
        assert "user_id" in session


def test_TC_UC01_04_login_with_wrong_password(client):
    """Log in with a wrong password. An error is shown and no session is created."""
    response = login(client, TEACHER_EMAIL, "WrongPassword1")

    assert "Invalid username or password" in page_text(response)
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_TC_UC01_05_session_expires_when_idle(app, client):
    """A logged-in user who does nothing for too long is logged out and must log in again."""
    # real limit is 30 minutes, for the test we make it 1 second
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=1)
    login(client, TEACHER_EMAIL, TEACHER_PASSWORD)

    # while the user is active the page opens
    assert client.get("/dashboard").status_code == 200

    time.sleep(2.2)  # user has now been idle longer than the limit

    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# extra tests (not in the design document) for security rules


def test_extra_registration_never_creates_an_admin(client, app):
    """Even if a browser sends role=admin, the new account is a teacher."""
    client.post(
        "/register",
        data={
            "username": "sneaky",
            "email": "sneaky@example.com",
            "password": "Pass@123",
            "confirm_password": "Pass@123",
            "role": "admin",
        },
    )

    with app.app_context():
        assert User.query.filter_by(username="sneaky").first().role == ROLE_TEACHER


def test_extra_weak_password_is_refused(client, app):
    """A password without an uppercase letter, a lowercase letter and a number is refused."""
    response = client.post(
        "/register",
        data={
            "username": "weakling",
            "email": "weak@example.com",
            "password": "abcdefgh",
            "confirm_password": "abcdefgh",
        },
        follow_redirects=True,
    )

    assert "uppercase" in page_text(response)
    with app.app_context():
        assert User.query.filter_by(username="weakling").count() == 0
