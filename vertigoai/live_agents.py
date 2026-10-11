# Get independent answers from four real Codex agents.

import copy
import json
from pathlib import Path

from .agents import AGENT_ROLES
from .build_context import build_context
from .codex_provider import ask_agent
from .disagreement import detect_disagreement
from .safety import check_stopping


# Find the main project folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Keep live results separate from the scripted demo.
OUTPUT_PATH = (
    PROJECT_ROOT
    / "results"
    / "live_initial_recommendations.json"
)


def main():
    # Build one shared input for all four agents.
    context = build_context()

    # Start an empty list of recommendations.
    recommendations = []

    # Each call starts a fresh session.
    # Agents do not receive the other agents' answers.
    for agent_name in AGENT_ROLES:
        print(f"\nCalling {agent_name}...", flush=True)

        # Give this agent a copy of the same shared input.
        response = ask_agent(
            agent_name,
            copy.deepcopy(context),
        )

        # Keep its checked answer.
        recommendations.append(response)

        # Show its recommendation and reason.
        print("Action:", response["recommended_action"])
        print("Reason:", response["explanation"])
        print("Confidence:", response["confidence"], flush=True)

    # Compare the four recommendations.
    disagreement = detect_disagreement(recommendations)

    # Check whether discussion should begin or stop.
    stopping = check_stopping(
        context,
        recommendations,
        rounds_completed=0,
    )

    # Save the inputs and answers from this live run.
    report = {
        "mode": "LIVE_CODEX",
        "simulated": True,
        "context": context,
        "recommendations": recommendations,
        "disagreement": disagreement,
        "stopping": stopping,
        "clinically_validated": False,
    }

    # Save only after all four calls succeed.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    # Show the disagreement result.
    print("\nLIVE CODEX RESULTS")
    print(
        "Disagreement detected:",
        disagreement["meaningful_disagreement"],
    )
    print("Conflicting pairs:", disagreement["conflict_count"])

    # Show whether negotiation can continue.
    print("Stop:", stopping["stop"])
    print("Outcome:", stopping["outcome"])
    print("Reason:", stopping["reason"])

    # Show where the live report was saved.
    print("Results saved:", OUTPUT_PATH)
    print("Real model responses using simulated participant data.")


# Run the program.
if __name__ == "__main__":
    main()