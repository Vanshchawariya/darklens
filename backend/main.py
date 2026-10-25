
import json
import os
import uuid
from pathlib import Path
from typing import List
from tinyfish import TinyFish

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl

from backend.classifier import classify_finding, rank_websites
from backend.analyze_page import analyze_page


# --------------------------------------------------
# Configuration
# --------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
STORAGE_FILE = BACKEND_DIR / "audit_storage.json"

load_dotenv(BACKEND_DIR / ".env")

API_KEY = os.getenv("TINYFISH_API_KEY")
API_URL = "https://agent.tinyfish.ai/v1/automation/run-sse"


# --------------------------------------------------
# FastAPI application and CORS
# --------------------------------------------------

app = FastAPI(
    title="DarkLens API",
    description="Detect possible dark patterns on public product pages.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Request models
# --------------------------------------------------

class Finding(BaseModel):
    pattern: str
    detected: bool = True
    evidence_text: str = ""


class AuditRequest(BaseModel):
    url: str
    site: str
    findings: List[Finding]


class AnalyzeRequest(BaseModel):
    url: HttpUrl


# --------------------------------------------------
# Audit storage
# --------------------------------------------------

def load_audits():
    if not STORAGE_FILE.exists():
        return []

    try:
        with STORAGE_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        raise HTTPException(
            status_code=500,
            detail="Could not read the saved audit records.",
        )


def save_audits(audits):
    try:
        with STORAGE_FILE.open("w", encoding="utf-8") as file:
            json.dump(audits, file, indent=4, ensure_ascii=False)
    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Could not save the audit report.",
        )


def classify_findings(findings):
    results = []

    for finding in findings:
        result = classify_finding(finding)
        results.append(result)

    return results


def create_audit(url, site, findings, extra_data=None):
    results = classify_findings(findings)

    audit = {
        "audit_id": str(uuid.uuid4()),
        "url": url,
        "site": site,
        "status": "completed",
        "findings": results,
        "total_score": sum(
            finding["severity"] for finding in results
        ),
    }

    if extra_data:
        audit.update(extra_data)

    audits = load_audits()
    audits.append(audit)
    save_audits(audits)

    return audit


# --------------------------------------------------
# TinyFish response handling
# --------------------------------------------------

def extract_page_text(result):
    if isinstance(result, str):
        try:
            return extract_page_text(json.loads(result))
        except json.JSONDecodeError:
            return result

    if isinstance(result, dict):
        for key in ("page_text", "text", "content", "page_content"):
            value = result.get(key)

            if isinstance(value, str) and value.strip():
                return value

        for key in ("result", "data", "output"):
            if key in result:
                text = extract_page_text(result[key])

                if text:
                    return text

    return ""



def get_tinyfish_page_text(page_url):
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="TinyFish API key is not configured.",
        )

    goal = """
    Read the publicly visible webpage only.
    Do not log in, submit forms, purchase products, or enter payment details.

    Return a JSON object with a page_text field containing relevant
    visible page text about prices, fees, countdowns, offers, stock,
    and scarcity messages. Quote the page accurately.
    Do not invent missing information.
    """

    try:
        client = TinyFish(api_key=API_KEY)

        response = client.agent.run(
            url=page_url,
            goal=goal,
        )

        result = response.result

    except Exception as exc:
        print("TinyFish SDK error:", str(exc), flush=True)
        raise HTTPException(
            status_code=502,
            detail="TinyFish could not complete the page analysis. Check the backend terminal.",
        ) from exc

    page_text = extract_page_text(result)

    if not page_text.strip():
        raise HTTPException(
            status_code=502,
            detail="TinyFish returned no usable page text.",
        )

    error_markers = [
        "consistently unreachable",
        "connection errors",
        "err_timed_out",
        "err_tunnel_connection_failed",
        "impossible to extract",
        "page is currently unavailable",
    ]

    if any(marker in page_text.lower() for marker in error_markers):
        raise HTTPException(
            status_code=502,
            detail="TinyFish could not access the product page.",
        )

    return page_text

# --------------------------------------------------
# Convert detector results to classifier findings
# --------------------------------------------------

def make_classifier_findings(analysis):
    detector_settings = [
        (
            "hidden_fees",
            "possible_hidden_fees_found",
        ),
        (
            "fake_timer",
            "possible_fake_timer_found",
        ),
        (
            "false_scarcity",
            "possible_false_scarcity_found",
        ),
    ]

    findings = []

    for pattern, detection_key in detector_settings:
        detector_result = analysis.get(pattern, {})
        detected = bool(detector_result.get(detection_key, False))
        evidence_items = detector_result.get("findings", [])

        evidence_parts = []

        for item in evidence_items:
            if isinstance(item, dict):
                matches = item.get("matches", [])

                if matches:
                    evidence_parts.extend(str(match) for match in matches)
                else:
                    evidence_parts.append(str(item))
            else:
                evidence_parts.append(str(item))

        findings.append({
            "pattern": pattern,
            "detected": detected,
            "evidence_text": "; ".join(evidence_parts),
        })

    return findings


# --------------------------------------------------
# Home and health endpoints
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Welcome to DarkLens API!",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------------------------------------
# Automated URL analysis using TinyFish + detectors
# --------------------------------------------------

@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    page_url = str(request.url)
    host = request.url.host.lower()

    # Basic rejection of local and private-network hostnames.
    # A public deployment needs stronger network-level URL protection.
    if (
        host == "localhost"
        or host.endswith((".localhost", ".local", ".internal"))
        or host in {"127.0.0.1", "::1", "0.0.0.0"}
        or host.startswith(("10.", "192.168.", "169.254."))
    ):
        raise HTTPException(
            status_code=400,
            detail="Please provide a public website URL.",
        )

    page_text = get_tinyfish_page_text(page_url)

    # Run the three existing detectors.
    analysis = analyze_page(page_text)

    # Convert the detector output to the classifier's input format.
    findings = make_classifier_findings(analysis)

    # Save this automatically generated analysis in the audit history.
    site = request.url.host

    audit = create_audit(
        url=page_url,
        site=site,
        findings=findings,
        extra_data={
            "extracted_text": page_text,
            "analysis": analysis,
        },
    )

    report = {
        "audit_id": audit["audit_id"],
        "url": page_url,
        "site": site,
        "extracted_text": page_text,
        "analysis": analysis,
        "findings": audit["findings"],
        "total_score": audit["total_score"],
        "status": audit["status"],
    }

    samples_dir = PROJECT_DIR / "samples"
    samples_dir.mkdir(exist_ok=True)

    with (samples_dir / "darklens_api_analysis.json").open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    return report


# --------------------------------------------------
# Manually submitted audits
# --------------------------------------------------

@app.post("/audit")
def audit_website(request: AuditRequest):
    findings = [
        finding.model_dump()
        for finding in request.findings
    ]

    return create_audit(
        url=request.url,
        site=request.site,
        findings=findings,
    )


# --------------------------------------------------
# Retrieve a saved report
# --------------------------------------------------

@app.get("/report/{audit_id}")
def get_report(audit_id: str):
    audits = load_audits()

    for audit in audits:
        if audit["audit_id"] == audit_id:
            return audit

    raise HTTPException(
        status_code=404,
        detail="Audit report not found",
    )


# --------------------------------------------------
# Website leaderboard
# --------------------------------------------------

@app.get("/leaderboard")
def get_leaderboard():
    audits = load_audits()
    ranking = rank_websites(audits)

    return {"leaderboard": ranking}
