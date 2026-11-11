# UC07: a teacher predicts a student's final grade. The docstring is the expected result.

import app.ml as ml
from app.models import Prediction
from helpers import course_id, enroll, make_attendance, make_marks, make_student, page_text


def predict_url(app):
    return f"/teacher/predict?course={course_id(app)}"


def student_with_data(app):
    # a student who has everything the model needs
    student_id = make_student(app)
    enroll(app, student_id)
    make_marks(app, student_id, quiz=9, assignment=19, midterm=27)
    make_attendance(app, student_id, present=5)
    return student_id


def test_TC_UC07_01_predict_a_grade(teacher_client, app, model_ready):
    """A grade and a risk level are predicted, shown, and saved."""
    student_id = student_with_data(app)

    response = teacher_client.post(
        predict_url(app), data={"student_id": student_id}, follow_redirects=True
    )

    text = page_text(response)
    assert "Prediction saved" in text
    assert "Predicted grade" in text
    with app.app_context():
        prediction = Prediction.query.one()
        assert prediction.predicted_grade in ["A", "B", "C", "D", "F"]
        assert prediction.risk_level in ["Low", "Medium", "High"]
        assert prediction.student_id == student_id


def test_TC_UC07_02_model_file_missing(teacher_client, app, monkeypatch, tmp_path):
    """If the model file is missing the teacher is told, and nothing is saved."""
    monkeypatch.setattr(ml, "MODEL_PATH", tmp_path / "does_not_exist.pkl")
    student_id = student_with_data(app)

    response = teacher_client.post(
        predict_url(app), data={"student_id": student_id}, follow_redirects=True
    )

    assert "model is unavailable" in page_text(response)
    with app.app_context():
        assert Prediction.query.count() == 0


def test_TC_UC07_03_not_enough_data(teacher_client, app, model_ready):
    """A student with no quiz or assignment data gets 'not enough data' and nothing is saved."""
    student_id = make_student(app)
    enroll(app, student_id)  # no marks, no attendance

    response = teacher_client.post(
        predict_url(app), data={"student_id": student_id}, follow_redirects=True
    )

    text = page_text(response)
    assert "not enough data" in text
    assert "quiz" in text
    with app.app_context():
        assert Prediction.query.count() == 0


def test_TC_UC07_04_prediction_takes_too_long(teacher_client, app, model_ready, monkeypatch):
    """If the prediction fails or times out, an error is shown, nothing is saved, and the teacher can retry."""
    import app.routes as routes

    def too_slow(*arguments):
        raise TimeoutError("the model did not answer")

    monkeypatch.setattr(routes, "predict_grade", too_slow)
    student_id = student_with_data(app)

    response = teacher_client.post(
        predict_url(app), data={"student_id": student_id}, follow_redirects=True
    )

    text = page_text(response)
    assert "prediction failed" in text
    assert "Predict grade" in text  # the form is still there, so the teacher can try again
    with app.app_context():
        assert Prediction.query.count() == 0


def test_extra_risk_level_follows_the_predicted_grade():
    """A and B are Low risk, C is Medium risk, D and F are High risk."""
    from app.utils import risk_from_grade

    assert risk_from_grade("A") == "Low"
    assert risk_from_grade("B") == "Low"
    assert risk_from_grade("C") == "Medium"
    assert risk_from_grade("D") == "High"
    assert risk_from_grade("F") == "High"
