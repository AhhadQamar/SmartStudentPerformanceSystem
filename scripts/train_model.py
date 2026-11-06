import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ml import MINIMUM_ACCURACY, TrainingError, train_model

try:
    result = train_model()
except TrainingError as error:
    print(f"Training stopped: {error}")
    print("The existing model, if there is one, was not changed.")
    sys.exit(1)

metrics = result["metrics"]
print("Model trained and saved.")
print(f"  accuracy:  {metrics['accuracy']}")
print(f"  precision: {metrics['precision']}")
print(f"  recall:    {metrics['recall']}")
print(
    f"  trained on {metrics['training_rows']} students, tested on {metrics['test_rows']}"
)

if result["flagged_for_review"]:
    print(
        f"WARNING: accuracy is below {MINIMUM_ACCURACY}. The model is flagged for review."
    )
