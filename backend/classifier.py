
#Map detected patterns to their categories and base scores

PATTERN_RULES = {
    "fake_timer": {
        "legal_category": "False urgency",
        "base_score": 6
    },
    "hidden_fees": {
        "legal_category": "Drip pricing",
        "base_score": 8
    },
    "false_scarcity": {
        "legal_category": "False urgency",
        "base_score": 5
    }
} 

def classify_pattern(pattern):
    if pattern in PATTERN_RULES:
        category = PATTERN_RULES[pattern]["legal_category"]
        score = PATTERN_RULES[pattern]["base_score"]

        return {
            "pattern": pattern,
            "legal_category": category,
            "severity": score
        }

    else:
        return {
            "pattern": pattern,
            "legal_category": "Unknown",
            "severity": 0
        }
    
def classify_finding(finding):
    pattern = finding.get("pattern", "unknown")
    evidence = finding.get("evidence_text", "")
    detected = finding.get("detected", False)

    result = classify_pattern(pattern)

    if not detected:
        result["severity"] = 0
        result["explanation"] = "No dark pattern was confirmed."
    elif pattern == "fake_timer":
        result["explanation"] = (
            "The countdown may create false urgency "
            "by pressuring users to act quickly."
        )
    elif pattern == "hidden_fees":
        result["explanation"] = (
            "Additional charges may be disclosed late "
            "in the purchase process."
        )
    elif pattern == "false_scarcity":
        result["explanation"] = (
            "The stock or demand message may pressure "
            "users into making a quick decision."
        )
    else:
        result["explanation"] = (
            "This pattern is not yet supported by our rules."
        )

    result["evidence_text"] = evidence
    result["detected"] = detected

    return result


def rank_websites(audits):
    website_scores = {}

    for audit in audits:
        site = audit.get("site", "unknown")
        findings = audit.get("findings", [])

        if site not in website_scores:
            website_scores[site] = 0

        for finding in findings:
            if finding.get("detected", False):
                result = classify_finding(finding)
                website_scores[site] += result["severity"]

    ranking = []

    for site, score in website_scores.items():
        ranking.append({
            "site": site,
            "total_score": score
        })

    ranking.sort(
        key=lambda item: item["total_score"],
        reverse=True
    )

    return ranking
