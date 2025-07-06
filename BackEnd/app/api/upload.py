from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from uuid import uuid4
import os
from datetime import datetime
from bson import ObjectId
from typing import Optional
import json

from app.utils.auth import decode_token
from app.utils.parser import (
    extract_text_from_pdf,
    extract_text_from_docx,
    parse_cv_enhanced
)
from app.db.mongodb import db

router = APIRouter()
security = HTTPBearer()

UPLOAD_DIR = "uploaded_cvs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload-cv")
async def upload_cv(
    file: UploadFile = File(...),
    tags: str = Form(None),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    user_data = decode_token(token)
    user_email = user_data.get("sub")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename not provided in upload.")

    # Validate file type
    if file.content_type not in [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]:
        raise HTTPException(status_code=400, detail="Only PDF or DOCX files are allowed")

    # Validate file size (10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size too large. Maximum 10MB allowed")

    # Save with original filename, resolve conflicts
    original_name = file.filename
    filename = original_name
    path = os.path.join(UPLOAD_DIR, filename)

    counter = 1
    while os.path.exists(path):
        name_part, ext = os.path.splitext(original_name)
        filename = f"{name_part}_{counter}{ext}"
        path = os.path.join(UPLOAD_DIR, filename)
        counter += 1

    try:
        # Save uploaded file
        with open(path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Extract text
        ext = filename.split(".")[-1].lower()
        if ext == "pdf":
            extracted_text = extract_text_from_pdf(path)
        elif ext == "docx":
            extracted_text = extract_text_from_docx(path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        if not extracted_text or len(extracted_text.strip()) < 50:
            raise HTTPException(status_code=422, detail="Could not extract sufficient text from CV")

        parsed_data = parse_cv_enhanced(extracted_text, file_name=original_name)

        # Parse tags from JSON string if provided
        tags_list = []
        if tags:
            try:
                tags_list = json.loads(tags)
                if not isinstance(tags_list, list):
                    tags_list = []
            except Exception:
                tags_list = []

        # Prepare DB entry
        db_entry = parsed_data.copy()
        db_entry.update({
            "user_email": user_email,
            "original_filename": original_name,
            "stored_filename": filename,
            "file_size": file.size,
            "file_type": ext,
            "upload_time": datetime.utcnow(),
            "processing_status": "completed",
            "text_length": len(extracted_text),
            "tags": tags_list
        })

        result = db.cvs.insert_one(db_entry)
        cv_id = str(result.inserted_id)

        response_parsed_data = parsed_data.copy()
        response_parsed_data.pop("raw_text", None)

        return {
            "message": "CV uploaded and parsed successfully",
            "cv_id": cv_id,
            "parsed_data": response_parsed_data,
            "analysis": {
                "summary": {
                    "name": parsed_data.get("name"),
                    "total_experience_years": parsed_data.get("total_experience_years"),
                    "current_position": parsed_data.get("current_position"),
                    "current_company": parsed_data.get("current_company"),
                    "total_skills_found": len(parsed_data.get("skills", [])),
                    "skills_categories_found": len(parsed_data.get("skills_by_category", {})),
                    "education_entries": len(parsed_data.get("education", [])),
                    "job_entries": len(parsed_data.get("job_entries", [])),
                    "contact_info": {
                        "emails": len(parsed_data.get("emails", [])),
                        "phone_numbers": len(parsed_data.get("phone_numbers", []))
                    }
                }
            },
            "metadata": {
                "cv_id": cv_id,
                "original_filename": original_name,
                "file_size": file.size,
                "upload_time": db_entry["upload_time"].isoformat(),
                "text_length": len(extracted_text)
            }
        }

    except Exception as e:
        if os.path.exists(path):
            os.remove(path)
        raise HTTPException(status_code=500, detail=f"Error processing CV: {str(e)}")


@router.get("/list-cvs")
def list_user_cvs(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_data = decode_token(token)
    user_email = user_data.get("sub")

    user_cvs = db.cvs.find({"user_email": user_email})

    result = []
    for cv in user_cvs:
        result.append({
            "id": str(cv["_id"]),
            "filename": cv.get("original_filename"),
            "stored_filename": cv.get("stored_filename"),
            "uploaded_at": cv.get("upload_time").isoformat(),
            "status": cv.get("processing_status", "unknown"),
            "name": cv.get("name"),
            "tags": cv.get("tags", [])
        })

    return result


@router.get("/cv/download/{filename}")
def download_cv(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, media_type="application/octet-stream", filename=filename)


@router.delete("/cv/{cv_id}")
async def delete_cv(
    cv_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    user_data = decode_token(token)
    user_email = user_data.get("sub")

    try:
        cv_data = db.cvs.find_one({
            "_id": ObjectId(cv_id),
            "user_email": user_email
        })

        if not cv_data:
            raise HTTPException(status_code=404, detail="CV not found")

        result = db.cvs.delete_one({
            "_id": ObjectId(cv_id),
            "user_email": user_email
        })

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="CV not found")

        if cv_data.get("stored_filename"):
            file_path = os.path.join(UPLOAD_DIR, cv_data["stored_filename"])
            if os.path.exists(file_path):
                os.remove(file_path)

        return {
            "message": "CV deleted successfully",
            "deleted_cv": {
                "cv_id": cv_id,
                "original_filename": cv_data.get("original_filename"),
                "upload_time": cv_data.get("upload_time")
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting CV: {str(e)}")

@router.get("/cv/preview/{filename}")
def preview_cv(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path, media_type="application/pdf")