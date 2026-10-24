
import re


SCARCITY_PATTERNS = [
    r"\bonly\s+\d+\s+(?:items?|units?|pieces?|left|remaining)\b",
    r"\bonly\s+\d+\s+(?:left|remaining)\b",
    r"\blow stock\b",
    r"\blimited stock\b",
    r"\balmost sold out\b",
    r"\bonly a few left\b",
    r"\bgoing fast\b",
    r"\bwhile stocks last\b",
]


def detect_false_scarcity(text):
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    findings = []

    for pattern in SCARCITY_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)

        for match in matches:
            findings.append(match.lower())

    return {
        "detector": "false_scarcity",
        "possible_false_scarcity_found": bool(findings),
        "findings": sorted(set(findings))
    }


if __name__ == "__main__":
    sample_text = """
    Hurry! Only 2 items left.
    Almost sold out. Limited stock available!
    """

    result = detect_false_scarcity(sample_text)

    print("False Scarcity Detector Result:")
    print(result)
