from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db.mongodb import db
from app.utils.auth import decode_token
from app.utils.scorer import compute_match_score
import re
from typing import List, Dict
from fastapi.responses import JSONResponse

router = APIRouter()
security = HTTPBearer()

def parse_boolean_query(query: str):
    query = query.lower()
    if ' or ' in query:
        keywords = [kw.strip() for kw in query.split(' or ')]
        mode = 'OR'
    else:
        keywords = [kw.strip() for kw in query.split(' and ')] if ' and ' in query else query.split()
        mode = 'AND'
    return keywords, mode

@router.get("/search-cvs")
def search_cvs(query: str = Query(..., description="Boolean query: e.g., 'python AND flask' or 'react OR nextjs'"), 
               credentials: HTTPAuthorizationCredentials = Depends(security)):

    token = credentials.credentials
    user_data = decode_token(token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    keywords, mode = parse_boolean_query(query)
    cvs = db.cvs.find()
    results = []

    for cv in cvs:
        text = cv.get("raw_text", "").lower()

        if mode == "AND":
            matched = all(kw in text for kw in keywords)
        else:  # OR
            matched = any(kw in text for kw in keywords)

        if matched:
            score = compute_match_score(text, query)
            if score > 0:
                results.append({
                    "user_email": cv.get("user_email"),
                    "original_filename": cv.get("original_filename"),
                    "stored_filename": cv.get("stored_filename"),
                    "match_score": score,
                    "upload_time": cv.get("upload_time"),
                    "name": cv.get("name"),
                    "email": cv.get("email"),
                    "skills": cv.get("skills", []),
                    "current_position": cv.get("current_position"),
                    "current_company": cv.get("current_company"),
                    "total_experience_years": cv.get("total_experience_years"),
                })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return JSONResponse(content={"results": results})


