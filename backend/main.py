
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

from .analyze_page import analyze_page


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent

load_dotenv(BACKEND_DIR / ".env")

API_KEY = os.getenv("TINYFISH_API_KEY")
API_URL = "https://agent.tinyfish.ai/v1/automation/run-sse"

app = FastAPI(
    title="Dark Lens API",
    description="Detect possible dark patterns on public product pages.",
    version="1.0.0",
)


class AnalyzeRequest(BaseModel):
    url: HttpUrl


@app.get("/")
def home():
    return {
        "message": "Dark Lens API is running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


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


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    if not API_KEY:
        raise HTTPException(
            status_code=500,
            detail="TinyFish API key is not configured.",
        )

    page_url = str(request.url)

    # Avoid sending local or private-network URLs to TinyFish.
    host = request.url.host.lower()

    if (
        host == "localhost"
        or host.endswith(".localhost")
        or host.endswith(".local")
        or host.endswith(".internal")
        or host in {"127.0.0.1", "::1", "0.0.0.0"}
        or host.startswith(("10.", "192.168.", "169.254."))
    ):
        raise HTTPException(
            status_code=400,
            detail="Please provide a public website URL.",
        )

    goal = """
    Read the publicly visible product page only.
    Do not log in, submit forms, purchase products, or enter payment details.

    Return a JSON object with a page_text field containing relevant
    visible page text about prices, fees, countdowns, offers, stock,
    and scarcity messages. Quote the page accurately.
    Do not invent missing information.
    """

    events = []
    final_result = None

    try:
        with requests.post(
            API_URL,
            headers={
                "X-API-Key": API_KEY,
                "Content-Type": "application/json",
            },
            json={"url": page_url, "goal": goal},
            stream=True,
            timeout=(20, 300),
        ) as response:
            response.raise_for_status()

            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue

                data = line[len("data:"):].strip()

                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue

                events.append(event)

                if event.get("type") == "COMPLETE":
                    if event.get("error"):
                        raise HTTPException(
                            status_code=502,
                            detail="TinyFish reported an analysis error.",
                        )

                    status = event.get("status")
                    if status not in (None, "COMPLETED", "SUCCESS"):
                        raise HTTPException(
                            status_code=502,
                            detail=f"TinyFish status: {status}",
                        )

                    final_result = event.get("result")

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Could not complete the TinyFish request.",
        )

    if final_result is None:
        raise HTTPException(
            status_code=502,
            detail="TinyFish did not return a final result.",
        )

    page_text = extract_page_text(final_result)

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

    analysis = analyze_page(page_text)

    report = {
        "url": page_url,
        "extracted_text": page_text,
        "analysis": analysis,
    }

    samples_dir = PROJECT_DIR / "samples"
    samples_dir.mkdir(exist_ok=True)

    with (samples_dir / "darklens_api_analysis.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    return report
