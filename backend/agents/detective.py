import json
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EXTRACTION_PROMPT = """You are extracting structured data about a graduate program, \
internship, or research lab listing from raw webpage text below.

Search the ENTIRE text carefully — details like tuition, GPA requirements, and \
visa/country info are often mentioned only once, in a single sentence, possibly \
far from where the program name appears.

Return ONLY a JSON object (no markdown, no explanation) with these exact keys:
- country
- university
- program
- scholarship_amount
- tuition
- gpa_requirement (number or null)
- toefl_requirement (number or null)
- deadline (format: YYYY-MM-DD if possible, else the raw text found)
- visa_country
- sub_role (e.g. "AI", "Embedded Software", or null if not specified)
- notes (any other relevant detail in 1-2 sentences)

If a field cannot be found in the text, use null for that field.

IMPORTANT: All values must be simple strings or numbers, never nested objects or arrays. \
If a field has multiple parts (e.g. different fees for EU/non-EU students), combine them \
into a single descriptive string, e.g. "EU: €0, Non-EU: €5000".

WEBPAGE TEXT:
{page_text}
"""


def extract_listing_data(page_text: str, model: str = "gpt-4o-mini") -> dict | None:
    """
    Sends scraped page text to GPT-4o mini and returns structured listing data.
    Returns None if the model output can't be parsed as JSON.
    """
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
        return json.loads(raw_output)
    except json.JSONDecodeError:
        print(f"[detective] Could not parse model output as JSON:\n{raw_output}")
        return None