# UC10: training the prediction model. The docstring is the expected result.

import hashlib
import shutil
from pathlib import Path

import pytest

import app.ml as ml

REAL_CSV = Path(ml.__file__).resolve().parent.parent / "data" / "student_performance.csv"


@pytest.fixture
def workspace(monkeypatch, tmp_path):
    # a temp folder with its own copy of the data, model and log so these tests never touch the real files
    data_file = tmp_path / "data.csv"
    shutil.copy(REAL_CSV, data_file)
    monkeypatch.setattr(ml, "DATA_PATH", data_file)
    monkeypatch.setattr(ml, "MODEL_PATH", tmp_path / "model.pkl")
    monkeypatch.setattr(ml, "LOG_PATH", tmp_path / "training.log")
    return tmp_path


def fingerprint(path):
    # a short code that changes if the file changes
    return hashlib.md5(path.read_bytes()).hexdigest()


def test_TC_UC10_01_train_on_valid_data(workspace):
    """Training works: the metrics are logged and the model is saved."""
    result = ml.train_model()

    assert (workspace / "model.pkl").exists()
    assert 0 < result["metrics"]["accuracy"] <= 1
    assert result["flagged_for_review"] is False
    log = (workspace / "training.log").read_text()
    assert "accuracy=" in log and "precision=" in log and "recall=" in log


def test_TC_UC10_02_data_file_missing(workspace):
    """A missing data file stops the training and the old model is kept."""
    ml.train_model()
    before = fingerprint(workspace / "model.pkl")
    (workspace / "data.csv").unlink()

    with pytest.raises(ml.TrainingError, match="not found"):
        ml.train_model()

    assert fingerprint(workspace / "model.pkl") == before


def test_TC_UC10_03_too_few_rows_or_text_in_numbers(workspace):
    """Too few rows, or text where numbers should be, stops the training safely."""
    ml.train_model()
    before = fingerprint(workspace / "model.pkl")
    lines = REAL_CSV.read_text().splitlines()

    # only 5 students
    (workspace / "data.csv").write_text("\n".join(lines[:6]) + "\n")
    with pytest.raises(ml.TrainingError, match="only 5 rows"):
        ml.train_model()

    # the word "abc" in a number column
    lines[3] = "abc,50,50,50,B"
    (workspace / "data.csv").write_text("\n".join(lines) + "\n")
    with pytest.raises(ml.TrainingError, match="not numbers"):
        ml.train_model()

    assert fingerprint(workspace / "model.pkl") == before


def test_TC_UC10_04_accuracy_below_the_limit(workspace, monkeypatch):
    """A model below the accuracy limit is flagged for review and a warning is logged."""
    monkeypatch.setattr(ml, "MINIMUM_ACCURACY", 0.99)  # no real model reaches this

    result = ml.train_model()

    assert result["flagged_for_review"] is True
    assert "WARNING" in (workspace / "training.log").read_text()


def test_extra_admin_can_train_from_the_page(admin_client, workspace):
    """The admin's Train button trains a model and shows a confirmation."""
    response = admin_client.post("/admin/train", follow_redirects=True)

    assert "Model trained" in response.get_data(as_text=True)
    assert (workspace / "model.pkl").exists()


def test_extra_teacher_cannot_train_the_model(teacher_client, workspace):
    """A teacher who tries to train the model is turned away."""
    response = teacher_client.post("/admin/train", follow_redirects=True)

    assert "do not have permission" in response.get_data(as_text=True)
    assert not (workspace / "model.pkl").exists()
