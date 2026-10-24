
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from pathlib import Path
import json
import uuid

from backend.classifier import classify_finding, rank_websites


# Create the FastAPI application
app = FastAPI(title="DarkLens API")


# Allow our local frontend to communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Location of the audit storage file
STORAGE_FILE = Path(__file__).parent / "audit_storage.json"


# Structure of an individual finding
class Finding(BaseModel):
    pattern: str
    detected: bool = True
    evidence_text: str = ""


# Structure of an audit request
class AuditRequest(BaseModel):
    url: str
    site: str
    findings: List[Finding]


# Load previously saved audits
def load_audits():
    if not STORAGE_FILE.exists():
        return []

    with open(STORAGE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# Save audits to the JSON file
def save_audits(audits):
    with open(STORAGE_FILE, "w", encoding="utf-8") as file:
        json.dump(audits, file, indent=4)


# Home endpoint
@app.get("/")
def home():
    return {
        "message": "Welcome to DarkLens API!",
        "status": "running"
    }


# Create a new website audit
@app.post("/audit")
def audit_website(request: AuditRequest):
    results = []

    for finding in request.findings:
        result = classify_finding(finding.model_dump())
        results.append(result)

    total_score = sum(
        finding["severity"] for finding in results
    )

    audit = {
        "audit_id": str(uuid.uuid4()),
        "url": request.url,
        "site": request.site,
        "status": "completed",
        "findings": results,
        "total_score": total_score
    }

    audits = load_audits()
    audits.append(audit)
    save_audits(audits)

    return audit


# Retrieve a saved audit by its ID
@app.get("/report/{audit_id}")
def get_report(audit_id: str):
    audits = load_audits()

    for audit in audits:
        if audit["audit_id"] == audit_id:
            return audit

    raise HTTPException(
        status_code=404,
        detail="Audit report not found"
    )


# Display the website leaderboard
@app.get("/leaderboard")
def get_leaderboard():
    audits = load_audits()
    ranking = rank_websites(audits)

    return {
        "leaderboard": ranking
    }
