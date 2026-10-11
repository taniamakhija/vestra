# Show four different perspectives using scripted responses.
# This is a demonstration, not a live LLM experiment.

import copy
import json
from pathlib import Path

from .agents import AGENT_ROLES
from .build_context import build_context
from .validation import validate_response


# Find the project folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Choose where to save the initial answers.
OUTPUT_PATH = PROJECT_ROOT / "results" / "initial_recommendations.json"


def scripted_response(agent_name, context):
    # These answers are written for our sample scenario.
    scenario_id = context["scenario"]["scenario_id"]

    if scenario_id != "simulated-conflicting-priorities-001":
        raise ValueError("These scripted answers need the sample scenario.")

    # Give each agent a different recommendation and reason.
    examples = {
        "risk_prevention": {
            "action": "GENTLE_HAPTIC_FEEDBACK",
            "explanation": (
                "I propose a gentle cue for review because the model "
                "identified variable movement. This does not prove danger "
                "or show that a cue would help."
            ),
            "evidence": ["E1"],
            "concerns": [
                "Continuing without feedback may overlook a useful cue.",
                "A cue may distract the participant.",
            ],
            "option": None,
        },

        "long_term_optimization": {
            "action": "NO_FEEDBACK",
            "explanation": (
                "I favor continuing without feedback because the standing "
                "exercise is prescribed in this simulated plan. "
                "Movement variability alone does not justify interruption."
            ),
            "evidence": ["E1", "E2"],
            "concerns": [
                "Unnecessary feedback may interrupt practice.",
                "The exercise plan does not resolve every situation.",
            ],
            "option": None,
        },

        "alternative_strategies": {
            "action": "APPROVED_MOVEMENT_MODIFICATION",
            "explanation": (
                "I propose considering the supplied seated option. "
                "It offers another permitted way to perform the activity, "
                "but the data does not prove it is better."
            ),
            "evidence": ["E3"],
            "concerns": [
                "The participant dislikes the seated alternative.",
                "An available option may still be unsuitable in practice.",
            ],
            "option": "SIM_SEATED_VERSION",
        },

        "practicality_human_impact": {
            "action": "HUMAN_REVIEW",
            "explanation": (
                "I recommend human review because vibration is distracting "
                "and the participant dislikes the seated option. "
                "The plan does not resolve these competing preferences."
            ),
            "evidence": ["E4", "E5", "E7"],
            "concerns": [
                "Feedback may reduce comfort or participation.",
                "Human review may interrupt the activity.",
            ],
            "option": None,
        },
    }

    # Get the example for this agent only.
    example = examples[agent_name]

    # Return the same answer format we will use for live LLMs.
    return {
        "agent_name": agent_name,
        "recommended_action": example["action"],
        "explanation": example["explanation"],
        "supporting_evidence": example["evidence"],
        "confidence": 0.5,
        "concerns": example["concerns"],
        "additional_information_required": False,
        "information_needed": [],
        "approved_option_id": example["option"],
    }


def main():
    # Build one shared input for all four agents.
    context = build_context()

    # Start an empty list of answers.
    recommendations = []

    # Each agent gets its own copy of the same input.
    # No agent receives the other agents' answers here.
    for agent_name in AGENT_ROLES:
        agent_input = copy.deepcopy(context)

        # Get this agent's scripted answer.
        response = scripted_response(agent_name, agent_input)

        # Check the answer before saving it.
        checked_response = validate_response(
            response,
            agent_name,
            agent_input,
        )

        recommendations.append(checked_response)

    # Label the report clearly as a scripted demonstration.
    report = {
        "mode": "SCRIPTED_DEMO",
        "simulated": True,
        "context": context,
        "recommendations": recommendations,
        "final_decision": None,
        "note": "Scripted initial perspectives; no approved intervention.",
    }

    # Save the complete initial answers.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    # Show each agent's recommendation and explanation.
    print("SCRIPTED DEMO — no live LLM calls")

    for response in recommendations:
        print()
        print("Agent:", response["agent_name"])
        print("Action:", response["recommended_action"])
        print("Reason:", response["explanation"])

    # Show where the report was saved.
    print()
    print("Answers saved:", OUTPUT_PATH)
    print("These are proposals, not an approved final decision.")


# Run the program.
if __name__ == "__main__":
    main()