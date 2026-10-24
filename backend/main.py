
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from backend.classifier import classify_finding

app = FastAPI(title="DarkLens API")


class Finding(BaseModel):
    pattern: str
    detected: bool = True
    evidence_text: str = ""


class AuditRequest(BaseModel):
    url: str
    site: str
    findings: List[Finding]


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
        finding_data = finding.model_dump()
        result = classify_finding(finding_data)
        results.append(result)

    total_score = sum(
        finding["severity"] for finding in results
    )

    return {
        "url": request.url,
        "site": request.site,
        "status": "completed",
        "findings": results,
        "total_score": total_score
    }
