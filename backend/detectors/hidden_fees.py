
import re


FEE_PATTERNS = {
    "shipping_fee": r"\bshipping fee\b|\bdelivery fee\b",
    "handling_fee": r"\bhandling fee\b|\bhandling charge\b",
    "service_fee": r"\bservice fee\b|\bservice charge\b",
    "convenience_fee": r"\bconvenience fee\b",
    "processing_fee": r"\bprocessing fee\b|\bprocessing charge\b",
}


def detect_hidden_fees(text):
    findings = []

    for fee_type, pattern in FEE_PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)

        if matches:
            findings.append({
                "type": fee_type,
                "matches": sorted(set(
                    match.lower() for match in matches
                ))
            })

    return {
        "detector": "hidden_fees",
        "possible_hidden_fees_found": bool(findings),
        "findings": findings
    }


if __name__ == "__main__":
    sample_text = """
    Product price: Rs. 999
    Shipping fee: Rs. 50
    Handling charge: Rs. 20
    """

    result = detect_hidden_fees(sample_text)

    print("Hidden Fees Detector Result:")
    print(result)
