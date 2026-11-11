# Smart Student Performance & Prediction System

Final year project for CS619 (Virtual University of Pakistan).

A web application built with Flask. Administrators manage students and courses.
Teachers record marks and attendance for their own courses. A machine-learning
model predicts each student's final grade before the final exam and flags the
students who are at risk.

## What it does

**Administrator**

- Add, edit, search and delete students
- Create courses, assign a teacher, enroll and remove students
- See how accurate the prediction model is, and train a new one

**Teacher** (only for their own courses)

- Enter marks for the quiz, assignment, midterm and final exam
- Record daily attendance. Students below 75% are flagged
- View grades: marks, percentage and letter grade for every student
- Predict a student's final grade and risk level (Low, Medium, High)
- View a student's prediction history, next to the real grade once it is known
- Print a risk report that groups the students of a course by risk level

**Everyone**

- Passwords are stored hashed, logins expire after 30 minutes of inactivity,
  and every form is protected against CSRF
- The interface is responsive (Bootstrap), for desktop and mobile

## Quick start

```bash
bash setup.sh
```

This creates a virtual environment, installs the packages, trains the model,
creates the database with demo data and starts the app.

Then open `http://127.0.0.1:5000`.

## Manual setup

**1. Create and activate a virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

**2. Install the packages**

```bash
pip install -r requirements.txt
```

**3. Train the prediction model**

```bash
python scripts/train_model.py
```

**4. Create the database with demo data**

```bash
python scripts/seed.py
```

Warning: this deletes everything in the database and creates it again.

**5. Start the app**

```bash
flask run
```

The submitted zip already contains a database with demo data
(`instance/students.db`), so steps 3 and 4 are only needed to start fresh.

## Demo accounts

| Role                 | Email                       | Password  |
| -------------------- | --------------------------- | --------- |
| Administrator        | admin@school.com            | Admin@123 |
| Teacher              | teacher1@school.com         | Valid@123 |
| Teacher (no courses) | existing.teacher@school.com | Valid@123 |

Anyone can sign up from the Sign Up page, but that always creates a **teacher**.
Administrator accounts are only created by the seed script.

The demo data has three courses (CS301, CS302, CS303) taught by teacher1.
CS301 has 10 students with marks, attendance and predictions. CS302 and CS303
have students but no marks, so they show the empty states.

## How grades are worked out

All the grading rules are in `app/config_grading.py`.

| Part       | Out of | Weight |
| ---------- | ------ | ------ |
| Quiz       | 10     | 10%    |
| Assignment | 20     | 20%    |
| Midterm    | 30     | 30%    |
| Final exam | 40     | 40%    |

Grades: A from 80%, B from 65%, C from 50%, D from 40%, otherwise F.
A grade is only shown when all four marks have been entered.

## How the prediction works

The model gets four numbers for a student, all as percentages: attendance, quiz,
assignment and midterm. It never sees the final exam. A Random Forest
(scikit-learn) predicts the final grade, and the grade gives the risk level:
A or B is Low, C is Medium, D or F is High.

- The training data is **synthetic**. No real student records were available,
  so `scripts/generate_dataset.py` makes 300 students using the same grading
  rules as the app and a fixed random seed, so the file can be reproduced.
- The model is tested on 20% of the students that it never saw while learning.
  It reaches about 73% accuracy (precision about 70%, recall about 69%).
- Retrain it from the **Model** page (administrator) or with
  `python scripts/train_model.py`. Each run is added to `logs/training.log`.
  If the data file is bad, training stops and the existing model is kept.

## Project structure

```
app/
  __init__.py        creates the app (settings, CSRF, session timeout)
  routes.py          every page of the application
  models.py          the database tables
  config_grading.py  weights, maximum marks, grade scale, risk levels
  constants.py       role names, attendance statuses, timeout
  utils.py           grade, attendance and prediction-input calculations
  ml.py              training and using the prediction model
  extensions.py      database and CSRF objects
  ml_models/         the trained model (model.pkl)
  templates/         the HTML pages
  static/CSS/        the stylesheet
data/                training data (student_performance.csv)
scripts/
  seed.py            creates the database with demo data
  generate_dataset.py  makes the training data
  train_model.py     trains the model
instance/            the SQLite database (students.db)
logs/                training.log
```

## Notes

- **HTTPS:** the development server uses plain HTTP. For a real deployment run
  the app behind an HTTPS reverse proxy (for example Nginx with a TLS
  certificate) and set the `SECRET_KEY` environment variable to a long random
  value.
- **Browsers:** designed for current versions of Chrome, Firefox and Edge.
- **Security:** database access goes through SQLAlchemy only (no raw SQL), and
  Jinja escapes everything it prints, which protects against SQL injection and
  XSS.
