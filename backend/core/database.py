import sqlite3
from pathlib import Path
import json


# core/database.py -> core -> backend -> CareerAI_Assistant -> database/
DB_PATH = Path(__file__).resolve().parent.parent.parent / "database" / "career_local.db"


def get_connection():
    """Opens a connection to the database, rows returned as dict-like objects."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates tables if they don't exist. Called on server startup."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT,
            university TEXT,
            program TEXT,
            scholarship_amount TEXT,
            tuition TEXT,
            gpa_requirement REAL,
            toefl_requirement REAL,
            deadline TEXT,
            visa_country TEXT,
            sub_role TEXT,
            acceptance_score REAL,
            status TEXT DEFAULT 'new',
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gpa REAL,
            courses TEXT,
            cv_summary TEXT
        )
    """)

    conn.commit()
    conn.close()


def add_application(data: dict) -> int:
    """Inserts a new application row, returns the new row's id.
    Any missing keys default to None. Any non-primitive values (dict/list,
    which can happen when the AI returns a nested structure for something
    like tuition) get converted to a JSON string so SQLite can store them.
    """
    expected_fields = [
        "country", "university", "program", "scholarship_amount", "tuition",
        "gpa_requirement", "toefl_requirement", "deadline", "visa_country",
        "sub_role", "acceptance_score", "notes",
    ]

    safe_data = {}
    for field in expected_fields:
        value = data.get(field)
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        safe_data[field] = value

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO applications
        (country, university, program, scholarship_amount, tuition, gpa_requirement,
         toefl_requirement, deadline, visa_country, sub_role, acceptance_score, notes)
        VALUES (:country, :university, :program, :scholarship_amount, :tuition, :gpa_requirement,
                :toefl_requirement, :deadline, :visa_country, :sub_role, :acceptance_score, :notes)
    """, safe_data)
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id
def save_profile(gpa: float | None, courses: list[str], cv_summary: str = "") -> int:
    """Inserts a new profile row, returns the new row's id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO profiles (gpa, courses, cv_summary)
        VALUES (:gpa, :courses, :cv_summary)
    """, {
        "gpa": gpa,
        "courses": ", ".join(courses),
        "cv_summary": cv_summary,
    })
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def get_all_applications() -> list[dict]:
    """Returns all applications as a list of dicts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
def get_latest_profile() -> dict | None:
    """Returns the most recently added profile, or None if none exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_application_by_id(app_id: int) -> dict | None:
    """Returns a single application row by id, or None if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_application_analysis(app_id: int, acceptance_score: float, notes: str) -> None:
    """Writes the analyst's score and reasoning back onto an existing application row."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE applications
        SET acceptance_score = :score, notes = :notes
        WHERE id = :id
    """, {"score": acceptance_score, "notes": notes, "id": app_id})
    conn.commit()
    conn.close()

def update_profile_cv_summary(profile_id: int, cv_summary: str) -> None:
    """Attaches a CV summary to an existing profile row."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE profiles SET cv_summary = :cv_summary WHERE id = :id
    """, {"cv_summary": cv_summary, "id": profile_id})
    conn.commit()
    conn.close()


def delete_application(app_id: int) -> None:
    """Deletes a single application row by id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()