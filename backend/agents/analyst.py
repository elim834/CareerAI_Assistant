import json
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

ANALYSIS_PROMPT = """You are an academic admissions advisor. Compare the student's \
profile against the program listing below, and return ONLY a JSON object (no markdown, \
no explanation) with these exact keys:

- acceptance_score: a number from 0 to 10 representing the estimated chance of admission
- reasoning: 2-3 sentences explaining the score, referencing specific overlaps or gaps
  between the student's background and the program's requirements
- visa_summary: 1-2 sentences on which country's consulate the student would need to
  apply to for a visa, based on the program's visa_country field
- suggested_focus: 1 sentence on what the student could highlight or improve in their
  application (e.g. a specific project, skill, or test score)

STUDENT PROFILE:
GPA: {gpa}
Courses/background: {courses}
CV summary (projects, skills, experience): {cv_summary}

PROGRAM LISTING:
{program_json}
"""


def analyze_fit(student_gpa: float | None, student_courses: list[str], program_data: dict,
                 cv_summary: str | None = None, model: str = "claude-sonnet-4-6") -> dict | None:
    prompt = ANALYSIS_PROMPT.format(
        gpa=student_gpa if student_gpa is not None else "Not provided",
        courses=", ".join(student_courses[:30]) if student_courses else "Not provided",
        cv_summary=cv_summary if cv_summary else "Not provided",
        program_json=json.dumps(program_data, ensure_ascii=False, indent=2),
    )

    response = client.messages.create(
        model=model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_output = response.content[0].text.strip()

    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
        raw_output = raw_output.strip()

    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        print(f"[analyst] Could not parse model output as JSON:\n{raw_output}")
        return None


CV_SUMMARY_PROMPT = """You are summarizing a student's CV for use in academic program \
matching. Read the CV text below and return ONLY a JSON object (no markdown, no \
explanation) with this exact key:

- cv_summary: a 3-5 sentence summary covering the student's key technical skills, \
notable projects (with technologies used), and any relevant experience. Be specific \
about technologies and domains (e.g. "built a face recognition system using OpenCV \
and ONNX") since this will be matched against academic program requirements.

CV TEXT:
{cv_text}
"""


def summarize_cv(cv_text: str, model: str = "claude-sonnet-4-6") -> str | None:
    """Summarizes raw CV text into a few sentences focused on skills/projects."""
    prompt = CV_SUMMARY_PROMPT.format(cv_text=cv_text[:12000])

    response = client.messages.create(
        model=model,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_output = response.content[0].text.strip()
    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
        raw_output = raw_output.strip()

    try:
        parsed = json.loads(raw_output)
        return parsed.get("cv_summary")
    except json.JSONDecodeError:
        print(f"[analyst] Could not parse CV summary output:\n{raw_output}")
        return None