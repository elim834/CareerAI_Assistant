from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from pathlib import Path
import shutil
from core.scraper import fetch_page_text_smart, fetch_page_text_deep
from agents.detective import extract_listing_data, find_and_summarize_faculty
from core import database as db
from agents.analyst import analyze_fit, summarize_cv, draft_cover_letter
from fastapi import FastAPI, UploadFile, File
from core.parser import parse_transcript, extract_text_from_pdf
from datetime import date



@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="CareerAI Assistant API", lifespan=lifespan)

UPLOAD_DIR = Path(__file__).resolve().parent / "temp_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@app.get("/")
async def root():
    return {"message": "CareerAI Assistant API is running"}

@app.post("/applications")
async def create_application(data: dict):
    new_id = db.add_application(data)
    return {"id": new_id, "status": "created"}

@app.get("/applications")
async def list_applications():
    return db.get_all_applications()

@app.get("/profile")
async def get_profile():
    profile = db.get_latest_profile()
    if not profile:
        return {"error": "No profile found."}
    return profile

@app.post("/profile/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    # Save the uploaded file temporarily
    temp_path = UPLOAD_DIR / file.filename
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Parse it
    result = parse_transcript(str(temp_path))

    # Save to profiles table
    profile_id = db.save_profile(gpa=result["gpa"], courses=result["courses"])

    # Clean up the temp file
    temp_path.unlink()

    return {
        "profile_id": profile_id,
        "gpa": result["gpa"],
        "courses_found": len(result["courses"]),
        "courses": result["courses"],
    }

@app.post("/analyze/{application_id}")
async def analyze_application(application_id: int):
    application = db.get_application_by_id(application_id)
    if not application:
        return {"error": f"No application found with id {application_id}"}

    profile = db.get_latest_profile()
    if not profile:
        return {"error": "No profile found. Upload a transcript first."}

    courses = profile["courses"].split(", ") if profile["courses"] else []

    analysis = analyze_fit(
        student_gpa=profile["gpa"],
        student_courses=courses,
        program_data=application,
        cv_summary=profile.get("cv_summary"),
        sub_role=application.get("sub_role"),
        education_language=profile.get("education_language"),
        toefl_score=profile.get("toefl_score"),
        ielts_score=profile.get("ielts_score"),
    )
    if analysis is None:
        return {"error": "Model could not produce a valid analysis"}

    db.update_application_analysis(app_id=application_id, analysis=analysis)

    return {"application_id": application_id, "analysis": analysis}


@app.get("/applications/{application_id}/last-analysis")
async def get_cached_analysis(application_id: int):
    """Returns the cached analysis result without calling the model again."""
    analysis = db.get_last_analysis(application_id)
    if analysis is None:
        return {"analyzed": False}
    return {"analyzed": True, "analysis": analysis}

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

    profile = db.get_latest_profile()
    if not profile:
        return {"error": "No profile found. Upload a transcript first."}

    db.update_profile_cv_summary(profile["id"], summary)
    return {"profile_id": profile["id"], "cv_summary": summary}

@app.delete("/applications/{application_id}")
async def delete_application(application_id: int):
    db.db_delete(application_id)
    return {"status": "deleted", "id": application_id}

@app.get("/applications/{application_id}")
async def get_single_application(application_id: int):
    application = db.get_application_by_id(application_id)
    if not application:
        return {"error": f"No application found with id {application_id}"}
    return application

@app.patch("/applications/{application_id}/status")
async def change_status(application_id: int, payload: dict):
    new_status = payload.get("status")
    if not new_status:
        return {"error": "status field is required"}
    db.update_application_status(application_id, new_status)
    return {"id": application_id, "status": new_status}

@app.patch("/applications/{application_id}/sub-role")
async def change_sub_role(application_id: int, payload: dict):
    new_sub_role = payload.get("sub_role")
    if not new_sub_role:
        return {"error": "sub_role field is required"}
    db.update_application_sub_role(application_id, new_sub_role)
    return {"id": application_id, "sub_role": new_sub_role}

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
        page_text = await fetch_page_text_deep(url)
        if page_text:
            combined_text += page_text

    if not combined_text.strip():
        return {"error": "Could not fetch or extract text from any of the provided pages"}

    listing_data = extract_listing_data(combined_text)
    if listing_data is None:
        return {"error": "Model could not extract structured data"}

    # Flag if the deadline appears to have already passed
    deadline_str = listing_data.get("deadline")
    if deadline_str:
        try:
            deadline_date = date.fromisoformat(deadline_str)
            if deadline_date < date.today():
                existing_notes = listing_data.get("notes") or ""
                listing_data["notes"] = (
                    f"⚠️ This deadline ({deadline_str}) appears to have already passed. "
                    f"Check the site for the next intake cycle. {existing_notes}"
                ).strip()
        except ValueError:
            pass

    primary_url = urls[0]
    listing_data["source_url"] = primary_url

    existing = db.find_application_by_source_url(primary_url)
    if existing:
        return {
            "id": existing["id"],
            "extracted": listing_data,
            "note": "Bu URL zaten takip listesinde, yeni satır oluşturulmadı.",
            "duplicate": True,
        }

    new_id = db.add_application(listing_data)
    return {
        "id": new_id,
        "extracted": listing_data,
        "debug_text_length": len(combined_text),
    }

@app.post("/cover-letter/{application_id}")
async def generate_cover_letter(application_id: int, payload: dict = None):
    application = db.get_application_by_id(application_id)
    if not application:
        return {"error": f"No application found with id {application_id}"}

    profile = db.get_latest_profile()
    if not profile:
        return {"error": "No profile found. Upload a transcript first."}

    courses = profile["courses"].split(", ") if profile["courses"] else []

    # Optional: if the caller provides a faculty search query, fetch lab research first
    lab_research = None
    if payload and payload.get("faculty_query"):
        lab_research = find_and_summarize_faculty(payload["faculty_query"])

    letter = draft_cover_letter(
        student_gpa=profile["gpa"],
        student_courses=courses,
        program_data=application,
        cv_summary=profile.get("cv_summary"),
        sub_role=application.get("sub_role"),
        lab_research=lab_research,
    )
    if letter is None:
        return {"error": "Model could not produce a valid cover letter draft"}

    return {"application_id": application_id, "letter": letter}

@app.post("/faculty-research/search")
async def search_faculty_research(payload: dict):
    query = payload.get("query")
    if not query:
        return {"error": "query field is required (e.g. 'Prof. Jane Doe MIT computer vision lab')"}

    result = find_and_summarize_faculty(query)
    if result is None:
        return {"error": "Could not find or summarize research for this query"}

    return result

@app.get("/usage")
async def usage_summary():
    return db.get_usage_summary()

@app.patch("/profile/language")
async def update_language_info(payload: dict):
    profile = db.get_latest_profile()
    if not profile:
        return {"error": "No profile found. Upload a transcript first."}

    db.update_profile_language_info(
        profile_id=profile["id"],
        education_language=payload.get("education_language"),
        toefl_score=payload.get("toefl_score"),
        ielts_score=payload.get("ielts_score"),
    )
    return {"status": "updated"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)