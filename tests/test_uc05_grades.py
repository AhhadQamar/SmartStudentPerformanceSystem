# UC05: a teacher views the grades of a course. The docstring is the expected result.

from helpers import course_id, enroll, make_marks, make_student, page_text


def grades_url(app, course_code="CS301", sort="name"):
    return f"/teacher/grades?course={course_id(app, course_code)}&sort={sort}"


def test_TC_UC05_01_view_grades(teacher_client, app):
    """The page shows each student's marks, percentage and letter grade."""
    student_id = make_student(app)
    enroll(app, student_id)
    make_marks(app, student_id, quiz=8, assignment=18, midterm=25, final=35)

    text = page_text(teacher_client.get(grades_url(app)))

    assert "Sara Khan" in text
    assert "86%" in text  # the percentage
    assert ">A<" in text.replace(" ", "").replace("\n", "")  # the letter grade


def test_TC_UC05_02_course_without_marks(teacher_client, app):
    """A course with no marks shows 'No marks available'."""
    student_id = make_student(app)
    enroll(app, student_id, "CS302")

    text = page_text(teacher_client.get(grades_url(app, "CS302")))

    assert "No marks available" in text


def test_TC_UC05_03_sort_by_grade(teacher_client, app):
    """Sorting by grade puts the highest percentage first."""
    # the weak student is first alphabetically, so sorting by name and sorting by grade give opposite orders. That shows the grade sort works
    weak = make_student(app, name="Aamir Weak", roll="SP24-BSCS-050", email="a@student.edu")
    strong = make_student(app, name="Zara Strong", roll="SP24-BSCS-051", email="z@student.edu")
    enroll(app, weak)
    enroll(app, strong)
    make_marks(app, weak, quiz=3, assignment=7, midterm=12, final=15)  # 37%
    make_marks(app, strong, quiz=9, assignment=19, midterm=27, final=36)  # 91%

    by_name = page_text(teacher_client.get(grades_url(app, sort="name")))
    by_grade = page_text(teacher_client.get(grades_url(app, sort="grade")))

    assert by_name.index("Aamir Weak") < by_name.index("Zara Strong")
    assert by_grade.index("Zara Strong") < by_grade.index("Aamir Weak")


def test_TC_UC05_04_missing_mark_shows_a_warning(teacher_client, app):
    """A student with a missing midterm shows 'Incomplete', not a wrong grade."""
    student_id = make_student(app)
    enroll(app, student_id)
    make_marks(app, student_id, quiz=8, assignment=18, final=35)  # no midterm

    text = page_text(teacher_client.get(grades_url(app)))

    assert "Incomplete" in text
    assert "Missing: midterm" in text
