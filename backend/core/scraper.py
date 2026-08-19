import requests
from bs4 import BeautifulSoup


def fetch_page_text(url: str, timeout: int = 15) -> str:
    """
    Fetches a URL and returns cleaned, readable text (scripts/styles stripped).
    Returns an empty string on failure instead of raising, so the caller
    can skip broken pages without crashing a batch run.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CareerAI-Bot/1.0)"}
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[scraper] Failed to fetch {url}: {e}")
        return ""

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)