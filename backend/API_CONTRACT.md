# CareerAI Assistant — API Contract

Base URL (local dev): `http://127.0.0.1:8000`

All request/response bodies are JSON unless noted otherwise.

---

## Health check

### `GET /`
Returns a simple status message to confirm the server is running.

**Response**
```json
{ "message": "CareerAI Assistant API is running" }
```

---

## Applications

### `GET /applications`
Returns all tracked applications.

**Response**: array of application objects (see shape below).

### `GET /applications/{application_id}`
Returns a single application by id.

**Response** (success):
```json
{
  "id": 8,
  "country": "Italy",
  "university": "Politecnico di Milano",
  "program": "Erasmus Mundus Joint Master in Imaging",
  "scholarship_amount": "€1400/month for a maximum of 24 months",
  "tuition": "€2000/year for EU citizens, €8000/year for non-EU citizens",
  "gpa_requirement": null,
  "toefl_requirement": 78,
  "deadline": "2026-01-09",
  "visa_country": "Italy",
  "sub_role": null,
  "acceptance_score": 7.2,
  "status": "new",
  "notes": "..."
}
```

**Response** (not found):
```json
{ "error": "No application found with id 99" }
```

### `POST /applications`
Manually creates an application row. Any field can be omitted (defaults to `null`).

**Request body**
```json
{
  "country": "Germany",
  "university": "TU Munich",
  "program": "MSc Computer Science",
  "scholarship_amount": "1000 EUR/month",
  "tuition": "0",
  "gpa_requirement": 3.0,
  "toefl_requirement": 90,
  "deadline": "2026-12-15",
  "visa_country": "Germany",
  "sub_role": "AI",
  "acceptance_score": null,
  "notes": "Strong fit based on coursework"
}
```

**Response**
```json
{ "id": 9, "status": "created" }
```

### `DELETE /applications/{application_id}`
Deletes a single application row.

**Response**
```json
{ "status": "deleted", "id": 9 }
```

---

## Profile

### `POST /profile/upload-pdf`
Uploads a transcript PDF, extracts GPA and course list, saves as a new profile row.

**Request**: `multipart/form-data` with a `file` field (PDF).

**Response**
```json
{
  "profile_id": 1,
  "gpa": 3.47,
  "courses_found": 47,
  "courses": ["CENG 105 ... AA", "..."]
}
```

### `POST /profile/upload-cv`
Uploads a CV PDF, summarizes it with AI, attaches the summary to the **most recently
created profile row** (so upload the transcript first).

**Request**: `multipart/form-data` with a `file` field (PDF).

**Response** (success):
```json
{
  "profile_id": 1,
  "cv_summary": "Elif Imil is a Software Engineering student..."
}
```

**Response** (no profile yet):
```json
{ "error": "No profile found. Upload a transcript first." }
```

> **Note on profile handling**: the system currently assumes a single active
> profile (the latest one created). There is no profile-switching endpoint yet —
> if this is needed later (e.g. multiple family members using the same install),
> a `GET /profiles` + profile selector will need to be added.

---

## Scraping (Detective agent)

### `POST /scan-url`
Fetches one or more URLs, extracts structured program data via GPT-4o mini,
saves it as a new application row.

**Request body** (single URL):
```json
{ "url": "https://example.edu/program-page" }
```

**Request body** (multiple related pages, e.g. admissions + fees):
```json
{
  "urls": [
    "https://example.edu/admissions",
    "https://example.edu/fees-and-funding"
  ]
}
```

**Response** (success):
```json
{
  "id": 8,
  "extracted": {
    "country": "Italy",
    "university": "Politecnico di Milano",
    "program": "Erasmus Mundus Joint Master in Imaging",
    "scholarship_amount": "€1400/month for a maximum of 24 months",
    "tuition": "€2000/year for EU citizens, €8000/year for non-EU citizens",
    "gpa_requirement": null,
    "toefl_requirement": 78,
    "deadline": "2026-01-09",
    "visa_country": "Italy",
    "sub_role": null,
    "notes": "..."
  }
}
```

**Response** (failure cases):
```json
{ "error": "Could not fetch or extract text from any of the provided pages" }
```
```json
{ "error": "Model could not extract structured data" }
```

---

## Analysis (Analyst agent)

### `POST /analyze/{application_id}`
Compares the current profile (GPA + courses + CV summary) against a given
application's listing data using Claude. Writes `acceptance_score` and a
combined notes string back onto the application row.

**Response** (success):
```json
{
  "application_id": 8,
  "analysis": {
    "acceptance_score": 7.2,
    "reasoning": "Elif's profile strongly aligns with...",
    "visa_summary": "As a Turkish national applying to a program hosted in Italy...",
    "suggested_focus": "Elif should prominently feature her face recognition system project..."
  }
}
```

**Response** (failure cases):
```json
{ "error": "No application found with id 99" }
```
```json
{ "error": "No profile found. Upload a transcript first." }
```
```json
{ "error": "Model could not produce a valid analysis" }
```

---

## Application object — full field reference

| Field                | Type            | Notes                                                |
|-----------------------|-----------------|-------------------------------------------------------|
| id                    | int             | auto-increment                                         |
| country               | string \| null  |                                                         |
| university            | string \| null  |                                                         |
| program               | string \| null  |                                                         |
| scholarship_amount    | string \| null  | free text, may include amount + duration               |
| tuition               | string \| null  | free text, may include multiple rates (EU/non-EU)      |
| gpa_requirement       | number \| null  |                                                         |
| toefl_requirement     | number \| null  |                                                         |
| deadline              | string \| null  | `YYYY-MM-DD` when parseable, else raw text              |
| visa_country          | string \| null  |                                                         |
| sub_role              | string \| null  | e.g. "AI", "Embedded Software" — set manually for now  |
| acceptance_score      | number \| null  | 0–10, set by `/analyze/{id}`                            |
| status                | string          | defaults to `"new"`                                     |
| notes                 | string \| null  | free text, populated by `/analyze/{id}`                 |

## Profile object — full field reference

| Field       | Type            | Notes                                     |
|-------------|-----------------|--------------------------------------------|
| id          | int             | auto-increment                              |
| gpa         | number \| null  | from `/profile/upload-pdf`                  |
| courses     | string \| null  | comma-separated list                        |
| cv_summary  | string \| null  | from `/profile/upload-cv`                   |

---

## Known limitations / things to revisit

- Single-profile assumption (see note under `/profile/upload-cv`).
- `sub_role` is not auto-filled by scraping; needs manual input or a future
  prompt update.
- No auth — fine for local single-user use, would need adding before any
  network exposure.
- SQLite is not safe for concurrent writes from multiple processes; fine for
  this project's local single-user scope.
