import json
import os
from openai import OpenAI
from tavily import TavilyClient
from core.database import check_budget, log_api_call


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


EXTRACTION_PROMPT = """You are extracting structured data about a graduate program, \
internship, or research lab listing from raw webpage text below.

Search the ENTIRE text carefully — details like tuition, GPA requirements, and \
visa/country info are often mentioned only once, in a single sentence, possibly \
far from where the program name appears.

Return ONLY a JSON object (no markdown, no explanation) with these exact keys:
- country
- university
- program
- scholarship_amount: search broadly — funding may be described as "scholarship", 
  "stipend", "grant", "fully funded", "tuition waiver", or "financial support", not 
  just the word "scholarship". If genuinely not mentioned anywhere in the text, use null.- tuition
- gpa_requirement (number or null)
- toefl_requirement (number or null)
- deadline (format: YYYY-MM-DD if possible, else the raw text found)
- visa_country
- sub_role (e.g. "AI", "Embedded Software", or null if not specified)
- notes (any other relevant detail in 1-2 sentences)
- application_type: either "masters" (for graduate degree programs) or "internship" 
  (for internships, traineeships, or entry-level job listings). Infer from context.

If a field cannot be found in the text, use null for that field.

IMPORTANT: All values must be simple strings or numbers, never nested objects or arrays. \
If a field has multiple parts (e.g. different fees for EU/non-EU students), combine them \
into a single descriptive string, e.g. "EU: €0, Non-EU: €5000".

WEBPAGE TEXT:
{page_text}
"""

def extract_listing_data(page_text: str, model: str = "gpt-4o-mini") -> dict | None:
    allowed, message = check_budget("openai")
    if not allowed:
        print(f"[detective] Budget check failed: {message}")
        return None

    if not page_text.strip():
        return None

    # Keep prompt cost/size sane — truncate very long pages
    truncated = page_text[:30000]

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": EXTRACTION_PROMPT.format(page_text=truncated)}
        ],
        temperature=0,
    )

    raw_output = response.choices[0].message.content.strip()

    # Strip accidental markdown fences if the model adds them
    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
        raw_output = raw_output.strip()

    try:
        log_api_call("openai", "extract_listing_data")
        return json.loads(raw_output)
    except json.JSONDecodeError:
        print(f"[detective] Could not parse model output as JSON:\n{raw_output}")
        return None

FACULTY_SUMMARY_PROMPT = """You are summarizing a professor's or research lab's recent \
academic work from the webpage text below (e.g. a Google Scholar page, lab website, or \
faculty profile).

Return ONLY a JSON object (no markdown, no explanation) with these exact keys:

- researcher_name: the professor's or lab's name, if identifiable
- recent_topics: a list of 3-6 short strings, each naming ONE specific research topic,
  method, or paper title found in the text (be specific — e.g. "Diffusion models for
  medical image reconstruction", not just "AI research")
- summary: 2-3 sentences summarizing the overall research focus/direction

If the text doesn't contain enough information to fill a field, use null or an empty list.

WEBPAGE TEXT:
{page_text}
"""

def search_faculty_pages(query: str, max_results: int = 3) -> list[dict]:
    """
    Searches the web for a professor/lab and returns a list of
    {title, url, content} dicts for the top results.
    """
    try:
        response = tavily_client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
        )
        return response.get("results", [])
    except Exception as e:
        print(f"[detective] Tavily search failed: {e}")
        return []

def find_and_summarize_faculty(search_query: str, model: str = "gpt-4o-mini") -> dict | None:
    """
    Searches the web for a professor/lab (via Tavily), combines the top
    results' content, and summarizes recent research topics via GPT-4o mini.
    """
    results = search_faculty_pages(search_query)
    if not results:
        return None

    combined_text = ""
    sources = []
    for r in results:
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "")
        combined_text += f"\n\n--- {title} ({url}) ---\n{content}"
        sources.append(url)

    truncated = combined_text[:15000]

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": FACULTY_SUMMARY_PROMPT.format(page_text=truncated)}
        ],
        temperature=0,
    )

    raw_output = response.choices[0].message.content.strip()
    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")
        if raw_output.startswith("json"):
            raw_output = raw_output[4:]
        raw_output = raw_output.strip()

    try:
        result = json.loads(raw_output)
        result["sources"] = sources
        return result
    except json.JSONDecodeError:
        print(f"[detective] Could not parse faculty summary output:\n{raw_output}")
        return None