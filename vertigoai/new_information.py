# Compare real agent answers before and after new information.

import copy
import json
from pathlib import Path

from .agents import AGENT_ROLES
from .build_context import build_context
from .codex_provider import ask_agent
from .disagreement import detect_disagreement
from .safety import check_stopping
from .validation import validate_response


# Find the project folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Read the original answers without changing their file.
BEFORE_PATH = (
    PROJECT_ROOT
    / "results"
    / "live_initial_recommendations.json"
)

# Save the comparison in a separate file.
OUTPUT_PATH = (
    PROJECT_ROOT
    / "results"
    / "new_information_comparison.json"
)


def main():
    # Read the original live run.
    before = json.loads(
        BEFORE_PATH.read_text(encoding="utf-8")
    )

    # Check that this is a live result.
    if before["mode"] != "LIVE_CODEX":
        raise ValueError("The original report must contain live answers.")

    # Check that the original run did not already include E8.
    old_evidence = before["context"]["scenario"]["evidence"]

    if "E8" in old_evidence:
        raise ValueError(
            "The original report already includes the new information."
        )

    # Check the original answers.
    for answer in before["recommendations"]:
        validate_response(
            answer,
            answer["agent_name"],
            before["context"],
        )

    detect_disagreement(before["recommendations"])

    # Read the updated scenario and movement prediction.
    updated_context = build_context()

    # Check that the new evidence was saved.
    if "E8" not in updated_context["scenario"]["evidence"]:
        raise ValueError("Add E8 to the scenario before running this file.")

    # Keep the movement prediction unchanged for this comparison.
    old_movement = before["context"]["scenario"]["movement_summary"]
    new_movement = updated_context["scenario"]["movement_summary"]

    if old_movement != new_movement:
        raise ValueError("The movement prediction changed between runs.")

    # Store the new answers separately.
    after_answers = []

    print("LIVE COMPARISON — simulated new information")

    # Each agent independently evaluates the updated input.
    # They do not see the old answers or other agents' answers.
    for agent_name in AGENT_ROLES:
        print(f"\nCalling {agent_name}...", flush=True)

        answer = ask_agent(
            agent_name,
            copy.deepcopy(updated_context),
        )

        after_answers.append(answer)

    # Index the old answers by agent name.
    old_answers = {
        answer["agent_name"]: answer
        for answer in before["recommendations"]
    }

    # Compare each agent's old and new answers.
    changes = []

    for answer in after_answers:
        agent_name = answer["agent_name"]
        old_answer = old_answers[agent_name]

        # Compare the action and movement option.
        choice_changed = (
            old_answer["recommended_action"],
            old_answer["approved_option_id"],
        ) != (
            answer["recommended_action"],
            answer["approved_option_id"],
        )

        # Record whether the agent still needs information.
        change = {
            "agent_name": agent_name,
            "before_action": old_answer["recommended_action"],
            "after_action": answer["recommended_action"],
            "choice_changed": choice_changed,
            "before_needs_information": (
                old_answer["additional_information_required"]
            ),
            "after_needs_information": (
                answer["additional_information_required"]
            ),
            "after_explanation": answer["explanation"],
        }

        changes.append(change)

        # Show the before-and-after result.
        print(f"\n{agent_name}")
        print("Before:", change["before_action"])
        print("After:", change["after_action"])
        print("Choice changed:", choice_changed)
        print(
            "Still needs information:",
            change["after_needs_information"],
        )
        print("Reason:", answer["explanation"])

    # Check disagreement and stopping after the update.
    disagreement = detect_disagreement(after_answers)
    stopping = check_stopping(
        updated_context,
        after_answers,
        rounds_completed=0,
    )

    # Save both sets of inputs and answers.
    comparison = {
        "mode": "LIVE_CODEX",
        "simulated": True,
        "experiment": "Independent reevaluation after new evidence",
        "before": before,
        "after_context": updated_context,
        "after_recommendations": after_answers,
        "changes": changes,
        "after_disagreement": disagreement,
        "after_stopping": stopping,
        "limitation": (
            "One before-and-after run does not prove causation. "
            "Model responses can vary between calls."
        ),
        "clinically_validated": False,
    }

    # Save only after all four new answers succeed.
    OUTPUT_PATH.write_text(
        json.dumps(comparison, indent=2),
        encoding="utf-8",
    )

    # Show the final outcome.
    print("\nOutcome after new information:", stopping["outcome"])
    print("Reason:", stopping["reason"])
    print("Comparison saved:", OUTPUT_PATH)


# Run the program.
if __name__ == "__main__":
    main()