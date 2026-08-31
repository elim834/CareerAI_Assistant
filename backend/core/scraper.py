import os
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from tavily import TavilyClient
import asyncio
from urllib.parse import urljoin, urlparse

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

REQUIREMENT_LINK_KEYWORDS = [
    "requirement", "admission", "eligib", "toefl", "ielts", "english",
    "apply", "application", "criteria", "prerequisite", "entry",
]

BOT_CHALLENGE_MARKERS = [
    "Just a moment",
    "cf-browser-verification",
    "Checking your browser",
    "Enable JavaScript and cookies to continue",
]

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def fetch_page_text(url: str, timeout: int = 15) -> str:
    """
    Fetches a URL and returns cleaned, readable text (scripts/styles stripped).
    Returns an empty string on failure instead of raising, so the caller
    can skip broken pages without crashing a batch run.
    """
    try:
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=timeout, verify=False)
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

    Uses "domcontentloaded" instead of "networkidle" because many sites
    (analytics beacons, chat widgets, ad trackers) never go fully idle,
    which caused hard timeouts on some real-world pages. Falls through to
    reading whatever HTML is available even if navigation raised a
    timeout, since the DOM is often usable by that point anyway.
    """
    html = ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=BROWSER_HEADERS["User-Agent"])
            try:
                page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            except Exception as e:
                print(f"[scraper] Playwright navigation warning for {url}: {e}")
            try:
                page.wait_for_timeout(2000)
            except Exception:
                pass
            html = page.content()
            browser.close()
    except Exception as e:
        print(f"[scraper] Playwright fetch failed for {url}: {e}")
        return ""

    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _fetch_raw_html_js_sync(url: str, timeout: int = 20000) -> str:
    """
    Like _fetch_page_text_js_sync, but returns raw HTML instead of cleaned
    text — used for link discovery when the lightweight requests fetch is
    blocked or returns too little to find navigation links in.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=BROWSER_HEADERS["User-Agent"])
            try:
                page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            except Exception as e:
                print(f"[scraper] Playwright navigation warning for {url}: {e}")
            try:
                page.wait_for_timeout(2000)
            except Exception:
                pass
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        print(f"[scraper] Playwright raw HTML fetch failed for {url}: {e}")
        return ""


def fetch_page_text_via_tavily(url: str) -> str:
    """
    Last-resort fetch using Tavily's Extract API. Tavily runs its own
    fetching infrastructure, so it can often retrieve content from pages
    protected by Cloudflare or similar bot-detection services that block
    both plain requests and headless Playwright from this machine.
    """
    try:
        result = tavily_client.extract(urls=[url])
    except Exception as e:
        print(f"[scraper] Tavily extract failed for {url}: {e}")
        return ""

    results = result.get("results", [])
    if not results:
        failed = result.get("failed_results", [])
        if failed:
            print(f"[scraper] Tavily could not extract {url}: {failed}")
        return ""

    raw_content = results[0].get("raw_content", "")
    return raw_content.strip() if raw_content else ""


def _looks_like_bot_challenge(html_or_text: str) -> bool:
    """Checks whether fetched content is actually a bot-verification page."""
    if not html_or_text:
        return False
    return any(marker in html_or_text for marker in BOT_CHALLENGE_MARKERS)


async def fetch_page_text_smart(url: str) -> str:
    """
    Tries the fast, lightweight fetch first, then a browser-rendered
    fetch, then — as a last resort — Tavily's Extract API, which runs
    from Tavily's own infrastructure and can often get past bot
    protection (e.g. Cloudflare challenges) that blocks direct requests
    from this machine.
    """
    text = fetch_page_text(url)
    if len(text) < 500 or _looks_like_bot_challenge(text):
        print(f"[scraper] Thin/blocked content ({len(text)} chars) from {url}, retrying with browser...")
        text = await asyncio.to_thread(_fetch_page_text_js_sync, url)

    if len(text) < 500 or _looks_like_bot_challenge(text):
        print(f"[scraper] Still thin/blocked content ({len(text)} chars) from {url}, trying Tavily extract...")
        tavily_text = await asyncio.to_thread(fetch_page_text_via_tavily, url)
        # Only accept the Tavily result if it's real content — otherwise
        # discard whatever we had (which may just be a stale bot-challenge
        # page) rather than passing it downstream as if it were real text.
        if tavily_text and len(tavily_text) >= 200 and not _looks_like_bot_challenge(tavily_text):
            text = tavily_text
        else:
            text = ""

    return text


def find_related_links(base_url: str, html: str, max_links: int = 3) -> list[str]:
    """
    Scans the anchor tags on a page for links whose href or visible text
    contains admission/requirement-related keywords (e.g. "Requirements",
    "Eligibility", "TOEFL"), and returns up to max_links absolute,
    same-domain URLs worth fetching as well.
    """
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc

    candidates: list[str] = []
    seen: set[str] = {base_url}

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(separator=" ").strip().lower()
        combined = f"{href.lower()} {text}"

        if not any(keyword in combined for keyword in REQUIREMENT_LINK_KEYWORDS):
            continue

        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)

        # Skip other domains, anchors, mailto/tel links
        if parsed.netloc != base_domain:
            continue
        if parsed.scheme not in ("http", "https"):
            continue
        if absolute_url in seen:
            continue

        seen.add(absolute_url)
        candidates.append(absolute_url)

        if len(candidates) >= max_links:
            break

    return candidates


def _extract_slug_keywords(url: str) -> str:
    """
    Pulls short, meaningful words out of a URL's path (e.g. "emai" and
    "admission" out of "/web/emai/access-admission") so a Tavily search
    fallback can stay scoped to the specific program instead of returning
    generic, unrelated pages from the same domain.
    """
    path = urlparse(url).path
    raw_tokens = [t for segment in path.split("/") for t in segment.replace("-", " ").replace("_", " ").split()]
    # Drop very short/common filler tokens that add noise to the query.
    stopwords = {"web", "en", "es", "ca", "index", "html", "php"}
    keywords = [t for t in raw_tokens if len(t) > 2 and t.lower() not in stopwords]
    return " ".join(keywords[:6])


def find_related_links_via_tavily(base_url: str, max_links: int = 3) -> list[str]:
    """
    Used when the page itself is behind a bot-challenge and we can't parse
    real HTML to find navigation links. Falls back to a Tavily web search
    scoped to the same domain, looking for requirement/eligibility pages
    for this specific program (using keywords pulled from the URL path,
    e.g. "emai", to avoid generic/unrelated results from the same domain).
    """
    domain = urlparse(base_url).netloc
    slug_keywords = _extract_slug_keywords(base_url)
    query = f"site:{domain} {slug_keywords} admission requirements TOEFL English score".strip()

    try:
        result = tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=max_links,
        )
    except Exception as e:
        print(f"[scraper] Tavily search fallback failed for {domain}: {e}")
        return []

    links = []
    for r in result.get("results", []):
        link_url = r.get("url")
        if not link_url or link_url == base_url:
            continue
        if urlparse(link_url).netloc != domain:
            continue
        # Skip binary documents (PDFs, docs) — they're rarely the right
        # requirements page and the extract step can't reliably read them.
        if link_url.lower().endswith((".pdf", ".doc", ".docx")):
            continue
        links.append(link_url)

    return links[:max_links]


async def fetch_page_text_deep(url: str, max_related: int = 3) -> str:
    """
    Fetches the given page, then automatically discovers and fetches a few
    on-domain sub-pages that look admission/requirement-related (based on
    link text and href keywords), and combines everything into one text
    blob. This helps when key details (like a TOEFL score threshold) live
    on a separate "Requirements" or "Eligibility" page rather than the
    page the user provided.

    Link discovery is attempted via the lightweight requests-based fetch
    first; if that's blocked (403, thin content, bot-challenge page) it
    falls back to a Playwright-rendered version of the page. If even that
    is just a bot-challenge page (e.g. Cloudflare), link discovery instead
    falls back to a Tavily web search scoped to the same domain.
    """
    raw_html = ""
    try:
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=15, verify=False)
        response.raise_for_status()
        raw_html = response.text
    except requests.RequestException as e:
        print(f"[scraper] Failed to fetch {url} for link discovery: {e}")

    if not raw_html or len(raw_html) < 500 or _looks_like_bot_challenge(raw_html):
        print(f"[scraper] Falling back to browser render for link discovery on {url}")
        try:
            raw_html = await asyncio.to_thread(_fetch_raw_html_js_sync, url)
        except Exception as e:
            print(f"[scraper] Browser-based link discovery failed for {url}: {e}")
            raw_html = ""

    main_text = await fetch_page_text_smart(url)
    combined = f"\n\n--- Content from {url} ---\n\n{main_text}" if main_text else ""

    if raw_html and not _looks_like_bot_challenge(raw_html):
        related_links = find_related_links(url, raw_html, max_links=max_related)
    else:
        print(f"[scraper] Page still blocked, using Tavily search to find related pages for {url}")
        related_links = find_related_links_via_tavily(url, max_links=max_related)

    for link in related_links:
        related_text = await fetch_page_text_smart(link)
        if related_text and len(related_text) >= 200 and not _looks_like_bot_challenge(related_text):
            combined += f"\n\n--- Content from {link} (auto-discovered) ---\n\n{related_text}"
            print(f"[scraper] Auto-discovered and included: {link}")
        else:
            print(f"[scraper] Skipped auto-discovered link (blocked/thin): {link}")

    return combined