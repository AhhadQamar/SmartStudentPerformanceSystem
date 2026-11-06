import csv
import os
import random
import sys

# This script lives in the "scripts" folder, but it needs to import from
# the "app" folder. This line tells Python to also look in the main folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config_grading import GRADE_SCALE, WEIGHTS

NUMBER_OF_STUDENTS = 300
OUTPUT_FILE = "data/student_performance.csv"

# A fixed seed means we get the SAME "random" numbers every time we run the
# script, so anyone who runs it gets the same file.
random.seed(42)


def keep_between_0_and_100(number):
    # A percentage can't be below 0 or above 100.
    return max(0, min(100, number))


def grade_from_percentage(percentage):
    # Same idea as percentage_to_grade in utils.py: go down the scale and
    # take the first letter whose minimum the student reached.
    for minimum, letter in GRADE_SCALE:
        if percentage >= minimum:
            return letter
    return "F"


rows = []
for _ in range(NUMBER_OF_STUDENTS):
    # Each student gets one "ability" number. A strong student does well
    # everywhere, a weak one does badly everywhere.
    ability = keep_between_0_and_100(random.gauss(62, 20))

    # Every result is the ability plus some random luck (good or bad day).
    # Bigger luck numbers mean that result is a weaker hint about ability.
    attendance = keep_between_0_and_100(ability + random.gauss(8, 12))
    quiz = keep_between_0_and_100(ability + random.gauss(0, 10))
    assignment = keep_between_0_and_100(ability + random.gauss(3, 8))
    midterm = keep_between_0_and_100(ability + random.gauss(0, 9))

    # The final exam happens AFTER the other results, so the model never sees
    # it. It is what makes the real grade hard to predict perfectly.
    final = keep_between_0_and_100(ability + random.gauss(0, 10))

    # Work out the final percentage with the app's own weights.
    # Example: quiz 80% with weight 10 -> 80 / 100 * 10 = 8 points.
    percentage = (
        quiz / 100 * WEIGHTS["quiz"]
        + assignment / 100 * WEIGHTS["assignment"]
        + midterm / 100 * WEIGHTS["midterm"]
        + final / 100 * WEIGHTS["final"]
    )

    rows.append(
        {
            "attendance": round(attendance, 1),
            "quiz": round(quiz, 1),
            "assignment": round(assignment, 1),
            "midterm": round(midterm, 1),
            "final_grade": grade_from_percentage(percentage),
        }
    )

with open(OUTPUT_FILE, "w", newline="") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=["attendance", "quiz", "assignment", "midterm", "final_grade"],
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)

# Show how many students got each grade.
counts = {}
for row in rows:
    grade = row["final_grade"]
    counts[grade] = counts.get(grade, 0) + 1
print(f"Wrote {len(rows)} rows to {OUTPUT_FILE}")
for letter in ["A", "B", "C", "D", "F"]:
    print(f"  {letter}: {counts.get(letter, 0)}")
