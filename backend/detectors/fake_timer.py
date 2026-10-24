
import re


TIMER_PATTERNS = [
    r"\b\d+\s*(?:minutes?|mins?)\s*left\b",
    r"\b\d+\s*(?:hours?|hrs?)\s*left\b",
    r"\bcountdown\b",
    r"\boffer expires\b",
    r"\btime is running out\b",
    r"\blimited[- ]time offer\b",
    r"\bend of sale\b",
]


def detect_fake_timer(text):
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    findings = []

    for pattern in TIMER_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)

        for match in matches:
            findings.append(match.lower())

    return {
        "detector": "fake_timer",
        "possible_fake_timer_found": bool(findings),
        "findings": sorted(set(findings))
    }


if __name__ == "__main__":
    sample_text = """
    Special offer! Only 05 minutes left.
    Limited-time offer. Time is running out!
    """

    result = detect_fake_timer(sample_text)

    print("Fake Timer Detector Result:")
    print(result)
