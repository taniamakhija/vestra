# Show that new safety information overrides agent agreement.

import copy
import json
from pathlib import Path

from .safety import check_stopping


# Find the project folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Read the saved before-and-after comparison.
INPUT_PATH = (
    PROJECT_ROOT
    / "results"
    / "new_information_comparison.json"
)

# Save this demonstration separately.
OUTPUT_PATH = (
    PROJECT_ROOT
    / "results"
    / "safety_injection.json"
)


def main():
    # Read the real agents' latest answers.
    comparison = json.loads(
        INPUT_PATH.read_text(encoding="utf-8")
    )

    # Copy the inputs so the original report stays unchanged.
    context = copy.deepcopy(comparison["after_context"])
    answers = copy.deepcopy(comparison["after_recommendations"])

    # Check the outcome before adding new information.
    before = check_stopping(context, answers, 0)

    # Add a simulated mandatory stop instruction.
    # This is a demo event, not a medical symptom detector.
    context["scenario"]["evidence"]["E9"] = (
        "Simulated safety event: the supervising reviewer has "
        "issued a mandatory stop-and-review instruction."
    )

    # Mark the scenario as requiring immediate escalation.
    context["scenario"]["mandatory_escalation"] = True

    # Check the rules immediately, before any new model calls.
    after = check_stopping(context, answers, 0)

    # Save the event and both outcomes.
    report = {
        "mode": "LIVE_RECOMMENDATIONS_WITH_SIMULATED_SAFETY_EVENT",
        "simulated": True,
        "previous_recommendations": answers,
        "updated_context": context,
        "before_safety_event": before,
        "after_safety_event": after,
        "new_llm_calls": 0,
        "note": (
            "The saved agent answers were made before the safety event. "
            "Python stops immediately without asking agents to reconsider."
        ),
        "clinically_validated": False,
    }

    # Save the demonstration.
    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    # Show how the safety event changed the outcome.
    print("Before safety event:", before["outcome"])
    print("After safety event:", after["outcome"])
    print("Reason:", after["reason"])
    print("Proposed action:", after["proposed_action"])
    print("New model calls: 0")
    print("Report saved:", OUTPUT_PATH)


# Run the program.
if __name__ == "__main__":
    main()