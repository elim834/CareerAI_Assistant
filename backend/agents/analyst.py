import json
import os
from anthropic import Anthropic
from core.database import check_budget, log_api_call

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

ANALYSIS_PROMPT = """You are an academic admissions advisor. Compare the student's \
profile against the program listing below, and return ONLY a JSON object (no markdown, \
no explanation) with these exact keys.

CRITICAL: Be concise. The "reasoning" and "visa_summary" fields must each be 1-2 \
sentences MAX. Each item in "risks" and "action_plan" must be ONE sentence, under 25 \
words. Do not write long paragraphs — short, direct phrasing only. This is required \
because the full response must fit within the token budget.

- acceptance_score: a number from 0 to 10. Base this on what THIS SPECIFIC program's
  listing actually emphasizes — read the program listing carefully and weigh the
  criteria it states or implies as important (e.g. if it explicitly requires a minimum
  GPA, weigh GPA heavily; if it emphasizes research experience or a specific technical
  skill, weigh that heavily; if it says nothing about a criterion, don't penalize the
  student for it). Do not apply a fixed generic formula — infer the program's own
  priorities from its listing text, then judge the student's fit against those specific
  priorities.
- language_requirement_status: one of "waived" (if the student's education language
  matches the program's medium of instruction or the program states a waiver for
  English-taught bachelor's degrees), "met" (if the student's TOEFL/IELTS score meets
  the stated requirement), "not met" (if a test is required and the score is below
  requirement or missing), or "unclear" (if the program doesn't specify or information
  is insufficient)
- reasoning: 1-2 sentences explaining the score, referencing specific overlaps or gaps
  between the student's background and the program's requirements
- visa_summary: 1 sentence on which country's consulate the student would need to
  apply to for a visa, based on the program's visa_country field
- suggested_focus: 1 sentence on what the student could highlight in their application
- risks: a list of 1-3 short strings (each under 25 words), each naming ONE specific gap
  between the program's requirements and the student's profile
- action_plan: a list of 1-3 short strings (each under 25 words), each a CONCRETE, small,
  doable-in-2-4-weeks project or action that would directly close one of the risks above

Each risk should have a corresponding action_plan item addressing it, in the same order.

{sub_role_instruction}

STUDENT PROFILE:
GPA: {gpa}
Courses/background: {courses}
CV summary (projects, skills, experience): {cv_summary}
Education language: {education_language}
TOEFL score: {toefl_score}
IELTS score: {ielts_score}

PROGRAM LISTING:
{program_json}
"""
def analyze_fit(student_gpa: float | None, student_courses: list[str], program_data: dict,
                 cv_summary: str | None = None, sub_role: str | None = None,
                 education_language: str | None = None, toefl_score: float | None = None,
                 ielts_score: float | None = None,
                 model: str = "claude-sonnet-4-6") -> dict | None:
    allowed, message = check_budget("anthropic")
    if not allowed:
        print(f"[analyst] Budget check failed: {message}")
        return None

    sub_role_instruction = ""
    if sub_role:
        sub_role_instruction = (
            f"IMPORTANT: The student is specifically applying for the \"{sub_role}\" track/role "
            f"within this program (not the program in general). Narrow your evaluation to focus "
            f"on the technical requirements typically expected for {sub_role} "
            f"(e.g. specific tools, frameworks, or theoretical background relevant to that field), "
            f"rather than evaluating general fit for the broader program."
        )

    prompt = ANALYSIS_PROMPT.format(
        sub_role_instruction=sub_role_instruction,
        gpa=student_gpa if student_gpa is not None else "Not provided",
        courses=", ".join(student_courses[:30]) if student_courses else "Not provided",
        cv_summary=cv_summary if cv_summary else "Not provided",
        education_language=education_language if education_language else "Not provided",
        toefl_score=toefl_score if toefl_score is not None else "Not provided",
        ielts_score=ielts_score if ielts_score is not None else "Not provided",
        program_json=json.dumps(program_data, ensure_ascii=False, indent=2),
    )
    response = client.messages.create(
        model=model,
        max_tokens=1500,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_output = response.content[0].text.strip()

    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
        raw_output = raw_output.strip()

    try:
        result = json.loads(raw_output)
        log_api_call("anthropic", "analyze_fit")
        return result
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
    allowed, message = check_budget("anthropic")
    if not allowed:
        print(f"[analyst] Budget check failed: {message}")
        return None

    prompt = CV_SUMMARY_PROMPT.format(cv_text=cv_text[:12000])

    response = client.messages.create(
        model=model,
        max_tokens=1000,
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
        log_api_call("anthropic", "summarize_cv")
        return parsed.get("cv_summary")
    except json.JSONDecodeError:
        print(f"[analyst] Could not parse CV summary output:\n{raw_output}")
        return None
COVER_LETTER_PROMPT = """You are helping a student draft a skeleton for a statement of \
purpose / motivation letter for a graduate program application. Using the student's \
profile and the program listing below, write a structured DRAFT (not a final polished \
letter) with clear placeholder guidance.

Return ONLY a JSON object (no markdown, no explanation) with these exact keys:

- opening_paragraph: a draft opening paragraph (3-4 sentences) that states the program
  name and connects the student's most relevant project/experience to why they're a fit.
  Write it in first person, as if the student is writing it, but keep it as a strong
  starting draft the student should personalize further.
- body_paragraph: a draft paragraph (4-5 sentences) that goes deeper into 1-2 of the
  student's specific projects (naming real technologies/skills from their profile) and
  explicitly ties them to the program's stated focus areas or requirements.
- lab_fit_paragraph: a draft paragraph (3-4 sentences) explaining specifically why this
  lab/department's research direction is a fit, referencing the actual research topics
  provided below if available. If no lab research info is provided, write a general
  paragraph about fit with the program's stated focus instead.
- closing_paragraph: a draft closing paragraph (2-3 sentences) expressing forward-looking
  motivation and fit with the program's goals.
- key_points_to_expand: a list of 2-4 short strings suggesting what the student should
  personally elaborate on or add (things the AI can't know, like personal motivation
  stories, specific faculty interest, or long-term career goals).

{sub_role_instruction}

STUDENT PROFILE:
GPA: {gpa}
Courses/background: {courses}
CV summary (projects, skills, experience): {cv_summary}

PROGRAM LISTING:
{program_json}

LAB/RESEARCH INFO (if available):
{lab_research}
"""


def draft_cover_letter(student_gpa: float | None, student_courses: list[str], program_data: dict,
                        cv_summary: str | None = None, sub_role: str | None = None,
                        lab_research: dict | None = None,
                        model: str = "claude-sonnet-4-6") -> dict | None:
    """Generates a structured cover letter draft skeleton."""
    allowed, message = check_budget("anthropic")
    if not allowed:
        print(f"[analyst] Budget check failed: {message}")
        return None

    sub_role_instruction = ""
    if sub_role:
        sub_role_instruction = (
            f"The student is applying specifically for the \"{sub_role}\" track. "
            f"Emphasize experience and framing relevant to that specific area."
        )

    lab_research_text = "Not provided"
    if lab_research:
        lab_research_text = json.dumps(lab_research, ensure_ascii=False, indent=2)

    prompt = COVER_LETTER_PROMPT.format(
        sub_role_instruction=sub_role_instruction,
        gpa=student_gpa if student_gpa is not None else "Not provided",
        courses=", ".join(student_courses[:30]) if student_courses else "Not provided",
        cv_summary=cv_summary if cv_summary else "Not provided",
        program_json=json.dumps(program_data, ensure_ascii=False, indent=2),
        lab_research=lab_research_text,
    )

    response = client.messages.create(
        model=model,
        max_tokens=1500,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_output = response.content[0].text.strip()
    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
        raw_output = raw_output.strip()

    try:
        result = json.loads(raw_output)
        log_api_call("anthropic", "draft_cover_letter")
        return result
    except json.JSONDecodeError:
        print(f"[analyst] Could not parse cover letter output:\n{raw_output}")
        return None