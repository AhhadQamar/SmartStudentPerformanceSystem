# The maximum raw marks for each part of a course.
MAX_MARKS = {"quiz": 10, "assignment": 20, "midterm": 30, "final": 40}

# How much each part counts towards the final percentage.
WEIGHTS = {"quiz": 10, "assignment": 20, "midterm": 30, "final": 40}

# Letter grades. Python checks from the top: the first line where
# the percentage is high enough wins. 85% -> "A", 70% -> "B", etc.
GRADE_SCALE = [(80, "A"), (65, "B"), (50, "C"), (40, "D"), (0, "F")]


# How risky each predicted grade is. A student predicted to get a D or F
# needs help the most.
RISK_BY_GRADE = {"A": "Low", "B": "Low", "C": "Medium", "D": "High", "F": "High"}

# A student whose attendance % is below this gets flagged.
ATTENDANCE_THRESHOLD = 75
