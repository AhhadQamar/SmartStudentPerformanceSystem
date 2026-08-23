import pickle
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "student_performance.csv"
MODEL_PATH = BASE_DIR / "app" / "static" / "model" / "model.pkl"


def main():
    data = pd.read_csv(DATA_PATH)

    feature_columns = ["attendance", "quiz", "assignment", "midterm"]

    X = data[feature_columns]
    y = data["final_grade"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
    )

    model = DecisionTreeClassifier(random_state=42)
    model.fit(X_train, y_train)

    accuracy = model.score(X_test, y_test)
    print(f"Model accuracy: {accuracy:.2f}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_PATH.open("wb") as file:
        pickle.dump(
            {
                "model": model,
                "feature_columns": feature_columns,
            },
            file,
        )
    print(f"Model saved to {MODEL_PATH}")
    print(f"training rows: {len(X_train)}, testing rows: {len(X_test)}")


if __name__ == "__main__":
    main()
