import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import asyncio


def fetch_page_text(url: str, timeout: int = 15) -> str:
    """
    Fetches a URL and returns cleaned, readable text (scripts/styles stripped).
    Returns an empty string on failure instead of raising, so the caller
    can skip broken pages without crashing a batch run.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout, verify=False)
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


def _fetch_page_text_js_sync(url: str, timeout: int = 20000) -> str:
    """
    Synchronous Playwright fetch — meant to be called from a worker thread
    (via asyncio.to_thread), never directly from an async function, since
    sync Playwright cannot run inside an active asyncio event loop.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=timeout, wait_until="networkidle")
            html = page.content()
            browser.close()
    except Exception as e:
        print(f"[scraper] Playwright fetch failed for {url}: {e}")
        return ""

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


async def fetch_page_text_smart(url: str) -> str:
    """
    Tries the fast, lightweight fetch first. If the result looks too thin
    (a strong signal of a JS-rendered page that returned mostly empty
    HTML), falls back to the slower but more capable browser-based fetch,
    run in a worker thread to avoid asyncio/Playwright conflicts on Windows.
    """
    text = fetch_page_text(url)
    if len(text) < 500:
        print(f"[scraper] Thin content ({len(text)} chars) from {url}, retrying with browser...")
        text = await asyncio.to_thread(_fetch_page_text_js_sync, url)
    return text