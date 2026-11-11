# UC09: the risk report of a course. The docstring is the expected result.

from helpers import course_id, enroll, make_prediction, make_student, page_text


def report_url(app, course_code="CS301"):
    return f"/teacher/risk-report?course={course_id(app, course_code)}"


def add_student(app, number, course_code="CS301"):
    student_id = make_student(
        app,
        name=f"Student {number:02d}",
        roll=f"SP24-BSCS-{100 + number}",
        email=f"student{number}@student.edu",
    )
    enroll(app, student_id, course_code)
    return student_id


def test_TC_UC09_01_students_grouped_by_risk(teacher_client, app):
    """Students are listed in the High, Medium and Low groups."""
    high = add_student(app, 1)
    medium = add_student(app, 2)
    low = add_student(app, 3)
    make_prediction(app, high, grade="F", risk="High")
    make_prediction(app, medium, grade="C", risk="Medium")
    make_prediction(app, low, grade="A", risk="Low")

    text = page_text(teacher_client.get(report_url(app)))

    # the groups show up in the order High, Medium, Low, each followed by its student
    high_part = text[text.index("High risk") : text.index("Medium risk")]
    medium_part = text[text.index("Medium risk") : text.index("Low risk")]
    low_part = text[text.index("Low risk") :]
    assert "Student 01" in high_part
    assert "Student 02" in medium_part
    assert "Student 03" in low_part


def test_TC_UC09_02_course_without_predictions(teacher_client, app):
    """A course with no predictions shows 'No prediction data available'."""
    add_student(app, 1, "CS303")

    text = page_text(teacher_client.get(report_url(app, "CS303")))

    assert "No prediction data available" in text


def test_TC_UC09_03_some_students_have_no_prediction(teacher_client, app):
    """With 8 of 10 students predicted, the report shows them and lists the 2 who are missing."""
    for number in range(1, 11):
        student_id = add_student(app, number)
        if number <= 8:
            make_prediction(app, student_id, grade="B", risk="Low")

    text = page_text(teacher_client.get(report_url(app)))

    missing_part = text[text.index("No prediction yet") :]
    assert "Student 09" in missing_part
    assert "Student 10" in missing_part
    assert "Student 01" not in missing_part  # a predicted student is not in the missing list


def test_TC_UC09_04_report_can_be_printed(teacher_client, app):
    """The report has a Print button that opens the browser's print window."""
    student_id = add_student(app, 1)
    make_prediction(app, student_id)

    html = teacher_client.get(report_url(app)).get_data(as_text=True)

    assert "Print report" in html
    assert "window.print()" in html


def test_extra_report_uses_only_the_latest_prediction(teacher_client, app):
    """A student who was High and is now Low appears only under Low."""
    student_id = add_student(app, 1)
    make_prediction(app, student_id, grade="F", risk="High")
    make_prediction(app, student_id, grade="A", risk="Low")  # newer

    text = page_text(teacher_client.get(report_url(app)))

    assert "Student 01" not in text[text.index("High risk") : text.index("Medium risk")]
    assert "Student 01" in text[text.index("Low risk") :]
