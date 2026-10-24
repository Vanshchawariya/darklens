
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from pathlib import Path
import json
import uuid


from backend.classifier import classify_finding, rank_websites

app = FastAPI(title="DarkLens API")

STORAGE_FILE = Path(__file__).parent / "audit_storage.json"


class Finding(BaseModel):
    pattern: str
    detected: bool = True
    evidence_text: str = ""


class AuditRequest(BaseModel):
    url: str
    site: str
    findings: List[Finding]


def load_audits():
    if not STORAGE_FILE.exists():
        return []

    with open(STORAGE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_audits(audits):
    with open(STORAGE_FILE, "w", encoding="utf-8") as file:
        json.dump(audits, file, indent=4)


@app.get("/")
def home():
    return {
        "message": "Welcome to DarkLens API!",
        "status": "running"
    }


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



@app.get("/leaderboard")
def get_leaderboard():
    audits = load_audits()
    ranking = rank_websites(audits)

    return {
        "leaderboard": ranking
    }
