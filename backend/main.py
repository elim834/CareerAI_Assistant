from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager
from pathlib import Path
import shutil
from core.scraper import fetch_page_text
from agents.detective import extract_listing_data
from core.database import (
    init_db, add_application, get_all_applications,
    save_profile, get_latest_profile, get_application_by_id, update_application_analysis,
)
from agents.analyst import analyze_fit, summarize_cv
from fastapi import FastAPI, UploadFile, File
from core.database import init_db, add_application, get_all_applications, save_profile, update_profile_cv_summary
from core.parser import parse_transcript, extract_text_from_pdf


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="CareerAI Assistant API", lifespan=lifespan)

UPLOAD_DIR = Path(__file__).resolve().parent / "temp_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@app.get("/")
async def root():
    return {"message": "CareerAI Assistant API is running"}


@app.post("/applications")
async def create_application(data: dict):
    new_id = add_application(data)
    return {"id": new_id, "status": "created"}


@app.get("/applications")
async def list_applications():
    return get_all_applications()


@app.post("/profile/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    # Save the uploaded file temporarily
    temp_path = UPLOAD_DIR / file.filename
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Parse it
    result = parse_transcript(str(temp_path))

    # Save to profiles table
    profile_id = save_profile(gpa=result["gpa"], courses=result["courses"])

    # Clean up the temp file
    temp_path.unlink()

    return {
        "profile_id": profile_id,
        "gpa": result["gpa"],
        "courses_found": len(result["courses"]),
        "courses": result["courses"],
    }

@app.post("/scan-url")
async def scan_url(payload: dict):
    urls = payload.get("urls")
    if not urls:
        single_url = payload.get("url")
        urls = [single_url] if single_url else None

    if not urls:
        return {"error": "Provide either 'url' (string) or 'urls' (list of strings)"}

    combined_text = ""
    for url in urls:
        page_text = fetch_page_text(url)
        if page_text:
            combined_text += f"\n\n--- Content from {url} ---\n\n{page_text}"

    if not combined_text.strip():
        return {"error": "Could not fetch or extract text from any of the provided pages"}

    listing_data = extract_listing_data(combined_text)
    if listing_data is None:
        return {"error": "Model could not extract structured data"}

    new_id = add_application(listing_data)
    return {
        "id": new_id,
        "extracted": listing_data,
        "debug_text_length": len(combined_text),
    }

@app.post("/analyze/{application_id}")
async def analyze_application(application_id: int):
    application = get_application_by_id(application_id)
    if not application:
        return {"error": f"No application found with id {application_id}"}

    profile = get_latest_profile()
    if not profile:
        return {"error": "No profile found. Upload a transcript first."}

    courses = profile["courses"].split(", ") if profile["courses"] else []

    analysis = analyze_fit(
        student_gpa=profile["gpa"],
        student_courses=courses,
        program_data=application,
        cv_summary=profile.get("cv_summary"),
    )
    if analysis is None:
        return {"error": "Model could not produce a valid analysis"}

    combined_notes = f"{analysis.get('reasoning', '')} | Visa: {analysis.get('visa_summary', '')} | Focus: {analysis.get('suggested_focus', '')}"
    update_application_analysis(
        app_id=application_id,
        acceptance_score=analysis.get("acceptance_score"),
        notes=combined_notes,
    )

    return {"application_id": application_id, "analysis": analysis}

@app.post("/profile/upload-cv")
async def upload_cv(file: UploadFile = File(...)):
    temp_path = UPLOAD_DIR / file.filename
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    cv_text = extract_text_from_pdf(str(temp_path))
    temp_path.unlink()

    if not cv_text.strip():
        return {"error": "Could not extract text from the CV"}

    summary = summarize_cv(cv_text)
    if summary is None:
        return {"error": "Could not summarize CV"}

    profile = get_latest_profile()
    if not profile:
        return {"error": "No profile found. Upload a transcript first."}

    update_profile_cv_summary(profile["id"], summary)
    return {"profile_id": profile["id"], "cv_summary": summary}

@app.delete("/applications/{application_id}")
async def delete_application(application_id: int):
    from core.database import delete_application as db_delete
    db_delete(application_id)
    return {"status": "deleted", "id": application_id}


@app.get("/applications/{application_id}")
async def get_single_application(application_id: int):
    application = get_application_by_id(application_id)
    if not application:
        return {"error": f"No application found with id {application_id}"}
    return application

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)