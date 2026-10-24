
import json

from .detectors.hidden_fees import detect_hidden_fees
from .detectors.fake_timer import detect_fake_timer
from .detectors.false_scarcity import detect_false_scarcity

def analyze_page(text):
    fee_result = detect_hidden_fees(text)
    timer_result = detect_fake_timer(text)
    scarcity_result = detect_false_scarcity(text)

    results = {
        "hidden_fees": fee_result,
        "fake_timer": timer_result,
        "false_scarcity": scarcity_result
    }

    triggered = sum([
        fee_result["possible_hidden_fees_found"],
        timer_result["possible_fake_timer_found"],
        scarcity_result["possible_false_scarcity_found"]
    ])

    results["summary"] = {
        "detectors_triggered": triggered,
        "total_detectors": 3,
        "risk_score": round((triggered / 3) * 100),
        "risk_level": (
            "High" if triggered == 3
            else "Medium" if triggered == 2
            else "Low" if triggered == 1
            else "No patterns detected"
        )
    }

    return results


if __name__ == "__main__":
    sample_text = """
    Product price: Rs. 999
    Shipping fee: Rs. 50
    Handling charge: Rs. 20
    Special offer! Only 05 minutes left.
    Limited-time offer. Time is running out!
    Hurry! Only 2 items left.
    Almost sold out. Limited stock available!
    """

    result = analyze_page(sample_text)

    print(json.dumps(result, indent=4))
