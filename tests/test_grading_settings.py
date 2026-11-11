# the admin's grading page and the risk report csv download. These are extra tests, they are not in the Design Document.

import app.config_grading as config_grading
from app import create_app
from app.extensions import db
from app.models import Marks
from helpers import (
    course_id,
    enroll,
    make_marks,
    make_prediction,
    make_student,
    page_text,
)

# new weights that add up to 100 and a scale where A needs 90
NEW_FORM = {
    "weight_quiz": "20",
    "weight_assignment": "10",
    "weight_midterm": "30",
    "weight_final": "40",
    "min_A": "90",
    "min_B": "65",
    "min_C": "50",
    "min_D": "40",
}


def test_extra_admin_changes_weights_and_scale(admin_client, app):
    """Saved settings are used at once and every saved grade is recalculated."""
    student_id = make_student(app)
    enroll(app, student_id)
    make_marks(app, student_id, quiz=8, assignment=18, midterm=25, final=35)  # 86.0%, A

    response = admin_client.post("/admin/grading", data=NEW_FORM, follow_redirects=True)

    assert "Grading settings saved" in page_text(response)
    with app.app_context():
        marks = Marks.query.filter_by(student_id=student_id).first()
        assert marks.percentage == 85.0  # 16 + 9 + 25 + 35
        assert marks.grade == "B"  # A now needs 90
    assert config_grading.WEIGHTS["quiz"] == 20


def test_extra_weights_must_add_up_to_100(admin_client, app):
    """Weights adding up to 90 are refused and nothing changes."""
    form = dict(NEW_FORM, weight_final="30")

    response = admin_client.post("/admin/grading", data=form, follow_redirects=True)

    assert "must add up to 100" in page_text(response)
    assert config_grading.WEIGHTS["quiz"] == 10  # still the default


def test_extra_grade_minimums_must_go_down(admin_client, app):
    """A grade that needs more than the grade above it is refused."""
    form = dict(NEW_FORM, min_B="95")  # B needs more than A

    response = admin_client.post("/admin/grading", data=form, follow_redirects=True)

    assert "must be lower than the one above it" in page_text(response)
    assert config_grading.GRADE_SCALE[1] == (65, "B")  # still the default


def test_extra_text_instead_of_a_number_is_refused(admin_client, app):
    """Letters in a number field are refused and what was typed is shown again."""
    form = dict(NEW_FORM, weight_quiz="abc")

    response = admin_client.post("/admin/grading", data=form, follow_redirects=True)

    text = page_text(response)
    assert "whole number" in text
    assert 'value="abc"' in text
    assert config_grading.WEIGHTS["quiz"] == 10


def test_extra_teacher_cannot_open_the_grading_page(teacher_client):
    """Only the admin can change how grades are worked out."""
    response = teacher_client.post("/admin/grading", data=NEW_FORM, follow_redirects=True)

    assert "do not have permission" in page_text(response)
    assert config_grading.WEIGHTS["quiz"] == 10


def test_extra_saved_settings_survive_a_restart(admin_client, app):
    """A new app using the same database starts with the saved settings."""
    admin_client.post("/admin/grading", data=NEW_FORM)
    config_grading.WEIGHTS.update(config_grading.DEFAULT_WEIGHTS)  # forget them in memory, so the restart has to load them

    restarted = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": app.config["SQLALCHEMY_DATABASE_URI"],
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "test-secret-key",
        }
    )

    assert config_grading.WEIGHTS["quiz"] == 20
    assert config_grading.GRADE_SCALE[0] == [90, "A"]
    with restarted.app_context():
        db.session.remove()
        db.engine.dispose()


def test_extra_risk_report_csv_download(teacher_client, app):
    """The CSV has one row per student, with the risk level or 'No prediction yet'."""
    predicted = make_student(app, name="Sara Khan", roll="SP24-BSCS-045", email="s@student.edu")
    waiting = make_student(app, name="Ali Raza", roll="SP24-BSCS-046", email="a@student.edu")
    enroll(app, predicted)
    enroll(app, waiting)
    make_prediction(app, predicted, grade="F", risk="High")

    response = teacher_client.get(f"/teacher/risk-report/export?course={course_id(app)}")

    text = page_text(response)
    assert response.mimetype == "text/csv"
    assert "SP24-BSCS-045,Sara Khan,High,F" in text
    assert "SP24-BSCS-046,Ali Raza,No prediction yet" in text


def test_extra_csv_of_another_teachers_course_is_refused(other_teacher_client, app):
    """A teacher cannot download the report of a course that is not theirs."""
    response = other_teacher_client.get(
        f"/teacher/risk-report/export?course={course_id(app)}", follow_redirects=True
    )

    assert "Course not found" in page_text(response)
