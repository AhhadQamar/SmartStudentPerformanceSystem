# UC02: the admin manages students. The docstring is the expected result from the design document.

from app.models import Student
from helpers import make_student, page_text


def test_TC_UC02_01_add_student(admin_client, app):
    """The administrator adds a student with valid details. The student is saved and a confirmation is shown."""
    response = admin_client.post(
        "/admin/students",
        data={
            "roll_number": "SP24-BSCS-045",
            "name": "Sara Khan",
            "email": "sara.khan@student.edu",
            "contact": "03001234567",
        },
        follow_redirects=True,
    )

    assert "Student added successfully" in page_text(response)
    with app.app_context():
        assert Student.query.filter_by(roll_number="SP24-BSCS-045").count() == 1


def test_TC_UC02_02_duplicate_roll_number(admin_client, app):
    """Adding a student whose roll number already exists shows an error and the student is not saved."""
    make_student(app)  # Sara Khan, SP24-BSCS-045

    response = admin_client.post(
        "/admin/students",
        data={
            "roll_number": "SP24-BSCS-045",
            "name": "Someone Else",
            "email": "someone.else@student.edu",
            "contact": "03111234567",
        },
        follow_redirects=True,
    )

    assert "roll number already exists" in page_text(response)
    with app.app_context():
        assert Student.query.filter_by(roll_number="SP24-BSCS-045").count() == 1
        assert Student.query.filter_by(name="Someone Else").count() == 0


def test_TC_UC02_03_required_field_empty(admin_client, app):
    """Leaving a required field empty shows a validation error and nothing is saved."""
    response = admin_client.post(
        "/admin/students",
        data={
            "roll_number": "SP24-BSCS-046",
            "name": "",
            "email": "ali@student.edu",
            "contact": "03001234567",
        },
        follow_redirects=True,
    )

    assert "All fields are required" in page_text(response)
    with app.app_context():
        assert Student.query.count() == 0


def test_TC_UC02_04_search_then_edit_contact(admin_client, app):
    """The administrator finds a student by search and changes the contact number. It is updated and a confirmation is shown."""
    student_id = make_student(app)

    # search with part of the name
    search = admin_client.get("/admin/students?q=sara")
    assert "Sara Khan" in page_text(search)

    # change the contact number
    response = admin_client.post(
        f"/admin/students/{student_id}/edit",
        data={
            "roll_number": "SP24-BSCS-045",
            "name": "Sara Khan",
            "email": "sara.khan@student.edu",
            "contact": "03211234567",
        },
        follow_redirects=True,
    )

    assert "updated successfully" in page_text(response)
    with app.app_context():
        assert Student.query.get(student_id).contact == "03211234567"


def test_TC_UC02_05_delete_student(admin_client, app):
    """The administrator deletes a student. The student is removed and a confirmation is shown."""
    student_id = make_student(app)

    response = admin_client.post(
        f"/admin/students/{student_id}/delete", follow_redirects=True
    )

    assert "deleted" in page_text(response)
    with app.app_context():
        assert Student.query.count() == 0


def test_TC_UC02_06_edit_or_delete_unknown_student(admin_client, app):
    """Editing or deleting a student that does not exist shows 'Student not found' and changes nothing."""
    make_student(app)  # a real student, must stay untouched

    edit = admin_client.post(
        "/admin/students/999/edit",
        data={"roll_number": "X", "name": "X", "email": "x@x.com", "contact": "1"},
        follow_redirects=True,
    )
    delete = admin_client.post("/admin/students/999/delete", follow_redirects=True)

    assert "Student not found" in page_text(edit)
    assert "Student not found" in page_text(delete)
    with app.app_context():
        assert Student.query.count() == 1


# extra test (not in the design document) for the permission rule


def test_extra_teacher_cannot_open_student_admin(teacher_client):
    """A teacher who opens the student administration page is turned away."""
    response = teacher_client.get("/admin/students", follow_redirects=True)

    assert "do not have permission" in page_text(response)
