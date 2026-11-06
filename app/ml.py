import pickle
from datetime import datetime
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler

# Where the files live. Path(__file__) is this file, .parent is its folder.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "student_performance.csv"
MODEL_PATH = BASE_DIR / "app" / "ml_models" / "model.pkl"
LOG_PATH = BASE_DIR / "logs" / "training.log"

# What the model looks at (the inputs) and what it predicts (the output).
FEATURE_COLUMNS = ["attendance", "quiz", "assignment", "midterm"]
TARGET_COLUMN = "final_grade"

MINIMUM_ROWS = 10  # fewer students than this is not enough to learn from
MINIMUM_ACCURACY = 0.60  # a model below this is flagged for review


class TrainingError(Exception):
    """Raised when the model cannot be trained (missing or bad data)."""

    pass


class ModelNotAvailableError(Exception):
    """Raised when the saved model file is missing or cannot be read."""

    pass


def load_training_data():
    # Read the CSV file and check it is usable. Any problem raises a
    # TrainingError with a clear message, BEFORE anything is trained or saved.
    if not DATA_PATH.exists():
        raise TrainingError(f"The training data file was not found: {DATA_PATH.name}")

    try:
        data = pd.read_csv(DATA_PATH)
    except Exception:
        raise TrainingError("The training data file could not be read.")

    for column in FEATURE_COLUMNS + [TARGET_COLUMN]:
        if column not in data.columns:
            raise TrainingError(f"The training data has no '{column}' column.")

    # Turn each input column into numbers. An empty cell becomes NaN
    # ("not a number") and is allowed: the pipeline fills it in later.
    # A cell with text in it, like "abc", is a real problem.
    for column in FEATURE_COLUMNS:
        as_numbers = pd.to_numeric(data[column], errors="coerce")
        text_cells = as_numbers.isna() & data[column].notna()
        if text_cells.any():
            raise TrainingError(
                f"The '{column}' column has values that are not numbers."
            )
        data[column] = as_numbers

    # A row with no grade is no use for learning.
    data = data.dropna(subset=[TARGET_COLUMN])

    if len(data) < MINIMUM_ROWS:
        raise TrainingError(
            f"The training data has only {len(data)} rows. At least {MINIMUM_ROWS} are needed."
        )
    if data[TARGET_COLUMN].nunique() < 2:
        raise TrainingError("The training data needs at least two different grades.")

    return data


def train_model():
    # Trains a new model, saves it, and returns a dictionary with the results.
    data = load_training_data()
    inputs = data[FEATURE_COLUMNS]
    grades = data[TARGET_COLUMN]

    # Keep 20% of the students back. The model never sees them while learning,
    # so testing on them shows how it does on students it has not met.
    try:
        # stratify keeps the same mix of grades in both parts
        inputs_train, inputs_test, grades_train, grades_test = train_test_split(
            inputs, grades, test_size=0.2, random_state=42, stratify=grades
        )
    except ValueError:
        # stratify fails when a grade has only one or two students
        inputs_train, inputs_test, grades_train, grades_test = train_test_split(
            inputs, grades, test_size=0.2, random_state=42
        )

    # A pipeline is a list of steps that always run in this order:
    #  1. fill empty cells with the middle (median) value of that column
    #  2. scale every column to 0-1, so no column counts more just because its numbers are bigger
    #  3. the Random Forest: many small decision trees that vote on the grade
    model = Pipeline(
        [
            ("fill_empty", SimpleImputer(strategy="median")),
            ("scale", MinMaxScaler()),
            ("classifier", RandomForestClassifier(random_state=42)),
        ]
    )
    model.fit(inputs_train, grades_train)  # this is the "learning" step

    # Test on the students that were kept back.
    predictions = model.predict(inputs_test)
    metrics = {
        # accuracy: out of all predictions, how many were right?
        "accuracy": round(accuracy_score(grades_test, predictions), 3),
        # precision: when it says "B", how often is it really B? (average over the grades)
        "precision": round(
            precision_score(grades_test, predictions, average="macro", zero_division=0),
            3,
        ),
        # recall: of the students who really are B, how many did it find? (average)
        "recall": round(
            recall_score(grades_test, predictions, average="macro", zero_division=0), 3
        ),
        "training_rows": len(inputs_train),
        "test_rows": len(inputs_test),
    }

    result = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "metrics": metrics,
        "flagged_for_review": metrics["accuracy"] < MINIMUM_ACCURACY,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = MODEL_PATH.with_suffix(".tmp")
    with temp_path.open("wb") as file:
        pickle.dump(result, file)
    temp_path.replace(MODEL_PATH)

    write_log(result)
    return result


def write_log(result):
    # Add one line about this training run to logs/training.log.
    metrics = result["metrics"]
    line = (
        f"{result['trained_at']}  accuracy={metrics['accuracy']}  "
        f"precision={metrics['precision']}  recall={metrics['recall']}  "
        f"train_rows={metrics['training_rows']}  test_rows={metrics['test_rows']}"
    )
    if result["flagged_for_review"]:
        line += (
            f"  WARNING: accuracy is below {MINIMUM_ACCURACY}, model flagged for review"
        )

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as file:  # "a" = add to the end of the file
        file.write(line + "\n")


def load_model():
    # Reads the saved model from disk and returns the dictionary saved by train_model().
    if not MODEL_PATH.exists():
        raise ModelNotAvailableError("The prediction model has not been trained yet.")

    try:
        with MODEL_PATH.open("rb") as file:
            return pickle.load(file)
    except Exception:
        raise ModelNotAvailableError("The prediction model file could not be read.")


def predict_grade(attendance, quiz, assignment, midterm):
    # All four inputs are percentages (0-100). Returns a letter like "B".
    saved = load_model()

    # The model expects a table, so we make a table with one row: this student.
    student = pd.DataFrame(
        [[attendance, quiz, assignment, midterm]], columns=saved["feature_columns"]
    )
    return str(saved["model"].predict(student)[0])
