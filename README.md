

An AI-powered, autonomous academic and career application management platform. It scans 60+ international master's programs, internship listings, and research labs, scores your acceptance chances against your academic profile, drafts cover letter skeletons, and lets you track the whole process in an Excel-like matrix / Kanban board.

---

## Architecture

```
CareerAI_Assistant/
├── backend/          # Python / FastAPI
│   ├── agents/       # AI agents (detective.py, analyst.py)
│   ├── core/         # Scraper, PDF parser, database layer
│   ├── main.py       # FastAPI server and all endpoints
│   └── API_CONTRACT.md
├── frontend/         # C# / WPF desktop UI
│   ├── Models/       # DTO classes
│   ├── Services/     # ApiClient.cs (HTTP communication with backend)
│   └── MainWindow, DetailWindow, KanbanWindow
├── database/         # SQLite (career_local.db) — not committed to Git
└── scripts/
    └── launcher.bat  # One-click backend + frontend startup
```

**Data flow:** Frontend (WPF) → HTTP/JSON → Backend (FastAPI) → SQLite. AI calls go from the backend to OpenAI (GPT-4o mini), Anthropic (Claude), and Tavily (web search) APIs.

---

## Features

### 1. Autonomous Web Scraping (`scraper.py` + `detective.py`)
- Scrapes given URL(s), cleans the HTML into plain text.
- **Multi-layer fallback chain:**
  1. `requests` + `BeautifulSoup` for a fast, lightweight fetch (static sites)
  2. If the content comes back "thin" (short/empty) → **Playwright (Chromium)** does a real browser render (for JS-heavy career portals like Workday, SuccessFactors)
  3. If Playwright still hits a bot-protection page (e.g. Cloudflare's "Just a moment...") → **Tavily Extract** as a third attempt
  4. If related subpages (fees, admission requirements, etc.) can't be auto-discovered because Cloudflare hides the links → **Tavily Search** with a `site:domain.com ...` query to find relevant pages
- The resulting raw text is sent to **GPT-4o mini**, which converts it into a structured 23-column JSON (country, university, program, scholarship, tuition, GPA/TOEFL requirement, deadline, visa country, etc.)
- Past deadlines are automatically detected and flagged in the notes.
- The `application_type` field distinguishes **master's programs** from **internships**, filterable in the frontend.

### 2. PDF Transcript and CV Reading (`parser.py`)
- `pdfplumber` extracts GPA and the full course list from a transcript PDF (supports both Turkish and English grading systems — including letter grades like AA/BA/BB).
- For CVs, GPT/Claude generates a **free-text summary** (projects, technologies, experience).
- Single-profile assumption: each new transcript/CV upload updates the existing profile rather than creating a new row.

### 3. Deep Analysis Engine (`analyst.py`, Claude)
- **Acceptance score (0-10):** Instead of a fixed formula, it weighs criteria based on what each program's **own listing text** actually emphasizes.
- **Risk & Action Plan:** Identifies concrete gaps between the profile and the program (`risks`) and 2-4 week doable mini-projects that would close them (`action_plan`).
- **Visa routing:** For multi-country programs like Erasmus Mundus, determines which country's consulate to apply to based on the first-semester host institution.
- **Language requirement matching:** Compares the student's education language/TOEFL/IELTS against the program's stated requirement, returning `waived` / `met` / `not met` / `unclear`.
- **Sub-Role filter:** For broad listings (e.g. large company career pages), narrows the evaluation to the student's chosen specialization (e.g. "Computer Vision").
- **Cover Letter Draft:** Combines the CV summary, program details, and (if available) lab research info into opening/body/lab-fit/closing paragraphs plus "you should personally add" suggestions.
- All Claude calls use `temperature=0` for consistent, repeatable results on the same input.

### 4. Faculty & Lab Intelligence (Tavily + GPT-4o mini)
- Given a university/lab name, Tavily searches the web, finds the most relevant pages, and GPT-4o mini summarizes them (`researcher_name`, `recent_topics`, `summary`, source links).
- This info is automatically fed into the cover letter generator.

### 5. Excel-Like Matrix + Kanban (WPF Frontend)
- **DataGrid matrix:** All applications in a sortable table (country, university, program, scholarship, tuition, TOEFL, deadline, days left, visa, score, status).
- **Deadline color coding:** Rows are automatically colored based on days remaining (red ≤3 days, yellow ≤14 days, green further out, grey if passed).
- **Kanban board:** Drag-and-drop between New / Applied / Accepted / Rejected columns, auto-synced to the backend.
- **Master's / Internship filtering:** Two buttons to filter the view.
- **One-click Excel export:** Exports the full matrix to `.xlsx` via `ClosedXML`.
- **Detail window:** Double-clicking a row opens a persistent window with the analysis results, program details, sub-role editing, and a cover-letter-generation button.
- **Delete:** An application can be permanently removed (`DELETE /applications/{id}`).

### 6. Budget Safety
- Every AI/search provider (OpenAI, Anthropic, Tavily) has its daily call count logged in the `api_usage` table.
- `check_budget()` blocks a call if the configured daily limits (`DAILY_LIMITS`) are exceeded.
- The `/usage` endpoint returns today's usage summary.
- **Also recommended:** setting an additional "Hard Limit" (monthly hard spend cap) directly in the OpenAI and Anthropic dashboards.

### 7. One-Click Launch (`launcher.bat`)
- Starts the backend (`uvicorn`) and frontend (`dotnet build` + `.exe`) with a single double-click.
- Automatically rebuilds the frontend on every run, so it always reflects the latest code.
- Kills any leftover running `.exe` process first (avoids file-lock issues).

---

## Setup

### Requirements
- Python 3.11+ (virtual environment: `backend/.venv`)
- .NET SDK 10.0 (see `frontend/global.json`)
- OpenAI API key (for GPT-4o mini)
- Anthropic API key (for Claude)
- Tavily API key (for web search — [tavily.com](https://tavily.com), free tier: 1,000 credits/month)

### `.env` file (`backend/.env`)
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
```

### Backend setup
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### Frontend setup
Open `frontend/frontend.sln` in Rider and Build Solution.

### Running
Double-click:
```
scripts/launcher.bat
```
Backend and frontend start automatically.

---

## Database Schema

**`applications`**
| Column | Type | Description |
|---|---|---|
| id | INTEGER | |
| country, university, program | TEXT | |
| scholarship_amount, tuition | TEXT | Free text (may contain multiple rates) |
| gpa_requirement, toefl_requirement | REAL | |
| deadline | TEXT | `YYYY-MM-DD` |
| visa_country, sub_role | TEXT | |
| acceptance_score | REAL | 0-10, written by `/analyze` |
| status | TEXT | Kanban status (`new`, `applied`, `accepted`, `rejected`) |
| notes | TEXT | |
| application_type | TEXT | `masters` / `internship` |

**`profiles`** (single row, id=1)
| Column | Type |
|---|---|
| gpa | REAL |
| courses | TEXT (comma-separated) |
| cv_summary | TEXT |
| education_language | TEXT |
| toefl_score, ielts_score | REAL |

**`api_usage`** — provider/endpoint/timestamp log for budget tracking.

See `backend/API_CONTRACT.md` for the full API contract.

---

## Known Limitations

- **Single-user / single-profile assumption.** The profile table always has one row (id=1); supporting multiple people/candidates would require a separate architectural change.
- **SQLite isn't suited for concurrent writes.** Not an issue for local, single-user use.
- **No authentication.** The system is designed to run on `localhost` only; auth would need to be added before exposing it to a network.
- **A GitHub Actions cron job (cloud automation) was deliberately not added** — since a cloud runner can't reach the local SQLite file, it would significantly complicate the architecture (requiring sync or a move to a cloud database). Could be revisited as a separate phase later.
- **Some sites still can't be scraped** (aggressive bot protection, CAPTCHAs). Manual entry via `POST /applications` is recommended in that case.
- **The `sub_role` field is only meaningful for internship listings** (sub-department selection on broad corporate career pages); it's generally redundant for master's programs since the program name is already specific.

---

## Tech Stack

**Backend:** Python, FastAPI, SQLite, pdfplumber, BeautifulSoup, Playwright, OpenAI SDK, Anthropic SDK, Tavily SDK
**Frontend:** C#, WPF (.NET 10), ClosedXML
**Automation:** `.bat` launcher script
**Version control:** Git (monorepo — backend + frontend in one repo)
