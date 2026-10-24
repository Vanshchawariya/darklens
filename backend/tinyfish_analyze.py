
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from backend.analyze_page import analyze_page


# Load the API key from backend/.env
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent

load_dotenv(BACKEND_DIR / ".env")

API_KEY = os.getenv("TINYFISH_API_KEY")

API_URL = "https://agent.tinyfish.ai/v1/automation/run-sse"


def extract_page_text(result):
    """Extract page text from TinyFish's final result."""

    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            return extract_page_text(parsed)
        except json.JSONDecodeError:
            return result

    if isinstance(result, dict):
        # Prefer the field specifically requested from TinyFish.
        for key in ("page_text", "text", "content", "page_content"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value

        # Handle a result nested inside another object.
        for key in ("result", "data", "output"):
            if key in result:
                text = extract_page_text(result[key])
                if text:
                    return text

    return ""


def main():
    if not API_KEY:
        raise ValueError(
            "TINYFISH_API_KEY not found. Check backend/.env"
        )

    page_url = input("Enter a public product page URL: ").strip()

    if not page_url.startswith(("https://", "http://")):
        raise ValueError("Enter a valid HTTP or HTTPS URL.")

    goal = """
    Read the publicly visible product page without purchasing anything,
    logging in, or submitting any forms.

    Extract relevant visible page text that could help detect:
    1. Additional fees, shipping charges, handling charges and service fees.
    2. Countdown timers, expiration claims and limited-time offers.
    3. Limited stock, low-stock claims and scarcity messages.

    Return a JSON object with this field:
    {
      "page_text": "Relevant visible text from the page"
    }

    Include the exact wording shown on the page when possible.
    Do not invent text or claim a pattern is deceptive without evidence.
    """

    print("\nConnecting to TinyFish...")

    events = []
    final_result = None

    try:
        with requests.post(
            API_URL,
            headers={
                "X-API-Key": API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "url": page_url,
                "goal": goal,
            },
            stream=True,
            timeout=(20, 300),
        ) as response:

            response.raise_for_status()

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue

                if line.startswith("data:"):
                    data = line[len("data:"):].strip()

                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    events.append(event)

                    event_type = event.get("type", "")
                    print("TinyFish event:", event_type or "received")

                    if event_type == "COMPLETE":
                        if event.get("error"):
                            raise RuntimeError(
                                f"TinyFish reported an error: "
                                f"{event['error']}"
                            )

                        if event.get("status") not in (
                            None, "COMPLETED", "SUCCESS"
                        ):
                            raise RuntimeError(
                                f"TinyFish status: {event.get('status')}"
                            )

                        final_result = event.get("result")

        # Save raw events for debugging and future demos.
        samples_dir = PROJECT_DIR / "samples"
        samples_dir.mkdir(exist_ok=True)

        raw_file = samples_dir / "tinyfish_page_events.json"
        with raw_file.open("w", encoding="utf-8") as file:
            json.dump(events, file, indent=2, ensure_ascii=False)

        if final_result is None:
            raise RuntimeError(
                "No final COMPLETE result received. "
                "Check the saved TinyFish events."
            )

        page_text = extract_page_text(final_result)

        if not page_text.strip():
            raise RuntimeError(
                "TinyFish completed but no page_text was found. "
                "Inspect samples/tinyfish_page_events.json "
                "to check the returned result structure."
            )

        print("\nPage text extracted successfully.")
        print("\nRunning Dark Lens detectors...")

        report = {
            "url": page_url,
            "extracted_text": page_text,
            "analysis": analyze_page(page_text),
        }

        report_file = samples_dir / "darklens_analysis.json"
        with report_file.open("w", encoding="utf-8") as file:
            json.dump(report, file, indent=2, ensure_ascii=False)

        print("\nDark Lens Analysis Report:")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"\nReport saved to: {report_file}")
        print(f"Raw TinyFish events saved to: {raw_file}")

    except requests.RequestException as error:
        print(f"\nTinyFish request failed: {error}")
        print("Check your internet connection and API access.")


if __name__ == "__main__":
    main()
