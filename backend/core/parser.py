import re
import pdfplumber

TURKISH_GRADES = {"AA", "BA", "BB", "CB", "CC", "DC", "DD", "FD", "FF"}
LETTER_GRADES = {"A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F"}


def extract_text_from_pdf(file_path: str) -> str:
    """Extracts all text from a PDF file."""
    text_chunks = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)
    return "\n".join(text_chunks)


def extract_gpa(text: str) -> float | None:
    """
    Looks for GPA in English and Turkish transcripts.
    Transcripts often list a GPA per semester — we take the LAST match,
    since the final/cumulative GPA typically appears last in the document.
    """
    patterns = [
        r"(?:C?GPA)[:\s]+([0-4][.,]\d{1,2})",
        r"(?:Grade Point Average)[:\s]+([0-4][.,]\d{1,2})",
        r"(?:AGNO|GANO)[:\s]+([0-4][.,]\d{1,2})",
        r"(?:Ağırlıklı\s+)?(?:Genel\s+Not\s+Ortalaması)[:\s]+([0-4][.,]\d{1,2})",
    ]

    matches = []
    for pattern in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            matches.append((m.start(), m.group(1)))

    if not matches:
        return None

    # sort by position in text, take the last one found
    matches.sort(key=lambda pair: pair[0])
    last_value = matches[-1][1].replace(",", ".")
    return float(last_value)

def extract_courses(text: str) -> list[str]:
    """
    Matches lines that END with a known grade token (Turkish or English).
    This avoids false positives like a stray 'C' inside '(C Programlama)'.
    """
    course_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        tokens = line.split()
        if not tokens:
            continue
        last_token = tokens[-1].upper()
        if last_token in TURKISH_GRADES or last_token in LETTER_GRADES:
            course_lines.append(line)
    return course_lines


def parse_transcript(file_path: str) -> dict:
    """Runs the full pipeline: extract text, then GPA and course list."""
    text = extract_text_from_pdf(file_path)
    return {
        "gpa": extract_gpa(text),
        "courses": extract_courses(text),
        "raw_text_length": len(text),
    }