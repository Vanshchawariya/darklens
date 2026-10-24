
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

EXPLANATORY_PHRASES = [
    "no countdown timers",
    "no countdown timer",
    "countdown timers were not found",
    "countdown timers were not detected",
    "the actual page was unreachable",
    "the actual page was unreachable/timed out",
    "browser environment",
    "err_timed_out",
    "err_tunnel_connection_failed",
]


def detect_fake_timer(text):
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    cleaned_text = text.lower()

    # Remove explanatory text that can cause false positives.
    for phrase in EXPLANATORY_PHRASES:
        cleaned_text = cleaned_text.replace(phrase, "")

    findings = []

    for pattern in TIMER_PATTERNS:
        matches = re.findall(pattern, cleaned_text, re.IGNORECASE)

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

    test_text = """
    The actual page was unreachable/timed out from this browser environment.
    No countdown timers, sale offers, or scarcity messages were found.
    """

    print("\nTest with unreachable page:")
    print(detect_fake_timer(test_text))
