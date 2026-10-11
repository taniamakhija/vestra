# Find differences between the four agents' recommendations.

import json
from itertools import combinations
from pathlib import Path

from .agents import AGENT_ROLES
from .validation import validate_response


# Find the main project folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Read the initial answers and save the conflicts.
INPUT_PATH = PROJECT_ROOT / "results" / "initial_recommendations.json"
OUTPUT_PATH = PROJECT_ROOT / "results" / "disagreement_report.json"


def detect_disagreement(recommendations):
    # We need exactly four answers.
    if len(recommendations) != len(AGENT_ROLES):
        raise ValueError("We need one answer from each of the four agents.")

    # Check that each agent appears exactly once.
    agent_names = [
        response["agent_name"]
        for response in recommendations
    ]

    if set(agent_names) != set(AGENT_ROLES):
        raise ValueError("An agent is missing, duplicated, or unknown.")

    # Start an empty list of conflicts.
    conflicts = []

    # Compare every pair of agents.
    for first, second in combinations(recommendations, 2):
        # Compare both the action and the movement option.
        first_choice = (
            first["recommended_action"],
            first["approved_option_id"],
        )

        second_choice = (
            second["recommended_action"],
            second["approved_option_id"],
        )

        # Record the pair if their choices differ.
        if first_choice != second_choice:
            conflicts.append({
                "first_agent": first["agent_name"],
                "first_action": first["recommended_action"],
                "first_option": first["approved_option_id"],
                "second_agent": second["agent_name"],
                "second_action": second["recommended_action"],
                "second_option": second["approved_option_id"],
                "reason": "Different actions or movement options.",
            })

    # Return the conflicts without choosing a winner.
    return {
        "meaningful_disagreement": bool(conflicts),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "additional_information_requested": any(
            response["additional_information_required"]
            for response in recommendations
        ),
        "human_review_requested": any(
            response["recommended_action"] == "HUMAN_REVIEW"
            for response in recommendations
        ),
    }


def main():
    # Read the saved initial answers.
    report = json.loads(
        INPUT_PATH.read_text(encoding="utf-8")
    )

    context = report["context"]
    recommendations = report["recommendations"]

    # Check the saved answers before comparing them.
    for response in recommendations:
        validate_response(
            response,
            response["agent_name"],
            context,
        )

    # Find disagreements between the agents.
    result = detect_disagreement(recommendations)

    # Keep the demo label and scenario ID with the results.
    output = {
        "mode": report["mode"],
        "scenario_id": context["scenario"]["scenario_id"],
        **result,
        "final_decision": None,
    }

    # Save the conflict report.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )

    # Show the number of conflicting pairs.
    print("Mode:", report["mode"])
    print("Disagreement detected:", result["meaningful_disagreement"])
    print("Conflicting pairs:", result["conflict_count"])

    # Show which agents disagree.
    for conflict in result["conflicts"]:
        print()
        print(
            conflict["first_agent"],
            "→",
            conflict["first_action"],
        )
        print(
            conflict["second_agent"],
            "→",
            conflict["second_action"],
        )

    # Show whether an agent requested human review.
    print()
    print("Human review requested:", result["human_review_requested"])
    print("Report saved:", OUTPUT_PATH)
    print("No winner or approved intervention has been selected.")


# Run the program.
if __name__ == "__main__":
    main()