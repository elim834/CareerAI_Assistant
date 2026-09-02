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
                   CREATE TABLE IF NOT EXISTS applications
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       country
                       TEXT,
                       university
                       TEXT,
                       program
                       TEXT,
                       scholarship_amount
                       TEXT,
                       tuition
                       TEXT,
                       gpa_requirement
                       REAL,
                       toefl_requirement
                       REAL,
                       deadline
                       TEXT,
                       visa_country
                       TEXT,
                       sub_role
                       TEXT,
                       acceptance_score
                       REAL,
                       status
                       TEXT
                       DEFAULT
                       'new',
                       notes
                       TEXT,
                       application_type
                       TEXT,
                       source_url
                       TEXT
                   )
                   """)

    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS api_usage
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       provider
                       TEXT,
                       endpoint
                       TEXT,
                       timestamp
                       DATETIME
                       DEFAULT
                       CURRENT_TIMESTAMP
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
        "sub_role", "acceptance_score", "notes", "application_type", "source_url",
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
                    toefl_requirement, deadline, visa_country, sub_role, acceptance_score, notes,
                    application_type, source_url)
                   VALUES (:country, :university, :program, :scholarship_amount, :tuition, :gpa_requirement,
                           :toefl_requirement, :deadline, :visa_country, :sub_role, :acceptance_score, :notes,
                           :application_type, :source_url)
                   """, safe_data)
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def save_profile(gpa: float | None, courses: list[str], cv_summary: str = "",
                  education_language: str | None = None, toefl_score: float | None = None,
                  ielts_score: float | None = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM profiles WHERE id = 1")
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE profiles SET gpa = :gpa, courses = :courses
            WHERE id = 1
        """, {"gpa": gpa, "courses": ", ".join(courses)})
        profile_id = 1
    else:
        cursor.execute("""
            INSERT INTO profiles (id, gpa, courses, cv_summary)
            VALUES (1, :gpa, :courses, :cv_summary)
        """, {"gpa": gpa, "courses": ", ".join(courses), "cv_summary": cv_summary})
        profile_id = 1

    conn.commit()
    conn.close()
    return profile_id

def update_profile_language_info(profile_id: int, education_language: str | None = None,
                                   toefl_score: float | None = None,
                                   ielts_score: float | None = None) -> None:
    """Updates language-related fields on the profile."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE profiles
        SET education_language = COALESCE(:education_language, education_language),
            toefl_score = COALESCE(:toefl_score, toefl_score),
            ielts_score = COALESCE(:ielts_score, ielts_score)
        WHERE id = :id
    """, {
        "education_language": education_language,
        "toefl_score": toefl_score,
        "ielts_score": ielts_score,
        "id": profile_id,
    })
    conn.commit()
    conn.close()

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

def update_application_status(app_id: int, status: str) -> None:
    """Updates just the status field of an application."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE applications SET status = :status WHERE id = :id",
                    {"status": status, "id": app_id})
    conn.commit()
    conn.close()

def update_application_sub_role(app_id: int, sub_role: str) -> None:
    """Updates just the sub_role field of an application."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE applications SET sub_role = :sub_role WHERE id = :id",
                    {"sub_role": sub_role, "id": app_id})
    conn.commit()
    conn.close()

def log_api_call(provider: str, endpoint: str) -> None:
    """Records one API call for budget tracking purposes."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO api_usage (provider, endpoint) VALUES (:provider, :endpoint)",
                    {"provider": provider, "endpoint": endpoint})
    conn.commit()
    conn.close()

def get_today_call_count(provider: str) -> int:
    """Returns how many calls to a given provider happened today (local date)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as count FROM api_usage
        WHERE provider = :provider AND date(timestamp) = date('now', 'localtime')
    """, {"provider": provider})
    row = cursor.fetchone()
    conn.close()
    return row["count"] if row else 0

def get_usage_summary() -> dict:
    """Returns today's call counts broken down by provider."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT provider, COUNT(*) as count FROM api_usage
        WHERE date(timestamp) = date('now', 'localtime')
        GROUP BY provider
    """)
    rows = cursor.fetchall()
    conn.close()
    return {row["provider"]: row["count"] for row in rows}

def find_application_by_source_url(url: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE source_url = ?", (url,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

DAILY_LIMITS = {
    "openai": 100,
    "anthropic": 50,
    "tavily": 100,
}

def check_budget(provider: str) -> tuple[bool, str]:
    """
    Returns (allowed, message). If the daily limit for this provider is
    exceeded, allowed=False and message explains why.
    """
    limit = DAILY_LIMITS.get(provider)
    if limit is None:
        return True, ""

    current = get_today_call_count(provider)
    if current >= limit:
        return False, f"Daily limit reached for {provider} ({current}/{limit}). Try again tomorrow."
    return True, ""