# Run real agent recommendations and discussion rounds.

import copy
import json
from pathlib import Path

from .agents import AGENT_ROLES
from .build_context import read_json
from .codex_provider import ask_agent
from .disagreement import detect_disagreement
from .safety import check_stopping, MAX_ROUNDS


# Find our project folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Choose the settings and negotiation scenario.
CONFIG_PATH = PROJECT_ROOT / "config" / "vertigoai.json"
SCENARIO_PATH = PROJECT_ROOT / "data" / "negotiation_scenario.json"
MOVEMENT_PATH = PROJECT_ROOT / "results" / "movement_summary.json"

# Keep this live discussion separate from earlier results.
OUTPUT_PATH = (
    PROJECT_ROOT
    / "results"
    / "live_negotiation_history.json"
)


def build_negotiation_context():
    # Read the settings, scenario, and model prediction.
    domain = read_json(CONFIG_PATH)
    scenario = read_json(SCENARIO_PATH)
    movement = read_json(MOVEMENT_PATH)

    # This prototype uses simulated participant data.
    if scenario.get("simulated") is not True:
        raise ValueError("The scenario must be simulated.")

    if movement.get("simulated") is not True:
        raise ValueError("The movement summary must be simulated.")

    # Add the actual model output to the scenario.
    scenario["movement_summary"] = movement

    # Replace the placeholder movement evidence.
    scenario["evidence"]["E1"] = (
        f"The model classified a simulated five-second window as "
        f"{movement['predicted_pattern']}. "
        f"Its probability estimate was "
        f"{movement['model_probability']:.1%}. "
        "This does not establish danger or clinical benefit."
    )

    # Return the same input for every agent.
    return {
        "domain": domain,
        "scenario": scenario,
    }


def save_history(history):
    # Save progress after each completed stage.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(history, indent=2),
        encoding="utf-8",
    )


def choice_changed(old_answer, new_answer):
    # Compare actions and movement options.
    old_choice = (
        old_answer["recommended_action"],
        old_answer["approved_option_id"],
    )

    new_choice = (
        new_answer["recommended_action"],
        new_answer["approved_option_id"],
    )

    return old_choice != new_choice


def main():
    # Build the negotiation scenario.
    context = build_negotiation_context()

    # Start a clearly labeled live report.
    history = {
        "mode": "LIVE_CODEX",
        "simulated": True,
        "context": context,
        "initial_recommendations": [],
        "rounds": [],
        "final_recommendations": [],
        "stopping": None,
        "run_status": "IN_PROGRESS",
        "clinically_validated": False,
    }

    # Save a fresh report before making calls.
    save_history(history)

    try:
        # Stop before model calls if the scenario already requires review.
        scenario = context["scenario"]

        if scenario["mandatory_escalation"]:
            history["stopping"] = {
                "stop": True,
                "outcome": "ESCALATE_TO_EXPERT",
                "reason": "Mandatory escalation before agent calls.",
                "proposed_action": "HUMAN_REVIEW",
            }

        elif scenario["missing_critical_information"]:
            history["stopping"] = {
                "stop": True,
                "outcome": "NEEDS_INFORMATION",
                "reason": "Critical information is missing before agent calls.",
                "proposed_action": "HUMAN_REVIEW",
            }

        else:
            print("LIVE INITIAL RECOMMENDATIONS", flush=True)

            # Get independent initial answers.
            for agent_name in AGENT_ROLES:
                print(f"\nCalling {agent_name}...", flush=True)

                answer = ask_agent(
                    agent_name,
                    copy.deepcopy(context),
                )

                history["initial_recommendations"].append(answer)

                print("Action:", answer["recommended_action"])
                print("Reason:", answer["explanation"], flush=True)

                # Preserve each completed initial call.
                save_history(history)

            # Keep the initial answers separate from later revisions.
            current = copy.deepcopy(
                history["initial_recommendations"]
            )

            # Check whether discussion should begin.
            stopping = check_stopping(context, current, 0)

            history["initial_disagreement"] = detect_disagreement(
                current
            )
            history["initial_stopping"] = stopping
            history["final_recommendations"] = current
            history["stopping"] = stopping
            save_history(history)

            # Allow up to three discussion rounds.
            for round_number in range(1, MAX_ROUNDS + 1):
                if stopping["stop"]:
                    break

                print(f"\nDISCUSSION ROUND {round_number}", flush=True)

                # Freeze the previous answers for this round.
                previous = copy.deepcopy(current)
                previous_by_name = {
                    answer["agent_name"]: answer
                    for answer in previous
                }

                exchanges = []

                # All agents receive the same previous-round answers.
                # None sees another agent's new reply in this round.
                for agent_name in AGENT_ROLES:
                    print(f"\nCalling {agent_name}...", flush=True)

                    revised = ask_agent(
                        agent_name,
                        copy.deepcopy(context),
                        previous_answers=copy.deepcopy(previous),
                    )

                    changed = choice_changed(
                        previous_by_name[agent_name],
                        revised,
                    )

                    # Store the reply and checked recommendation.
                    exchanges.append({
                        "agent_name": agent_name,
                        "message": revised["explanation"],
                        "position_changed": changed,
                        "recommendation": revised,
                    })

                    print(revised["explanation"])
                    print("Action:", revised["recommended_action"])
                    print("Position changed:", changed, flush=True)

                # Update only after all four agents finish replying.
                current = [
                    exchange["recommendation"]
                    for exchange in exchanges
                ]

                # Apply the stopping rules after the round.
                stopping = check_stopping(
                    context,
                    current,
                    round_number,
                    previous=previous,
                )

                # Store the complete round.
                history["rounds"].append({
                    "round_number": round_number,
                    "previous_recommendations": previous,
                    "exchanges": exchanges,
                    "disagreement": detect_disagreement(current),
                    "stopping_check": stopping,
                })

                history["final_recommendations"] = current
                history["stopping"] = stopping
                save_history(history)

        # Mark the report complete.
        history["run_status"] = "COMPLETE"
        save_history(history)

    except Exception:
        # A failed run must not appear to be a completed decision.
        history["run_status"] = "FAILED"
        history["stopping"] = None
        save_history(history)
        print("\nRun failed. Saved progress is incomplete.")
        raise

    # Show the final outcome.
    print("\nOutcome:", history["stopping"]["outcome"])
    print("Reason:", history["stopping"]["reason"])
    print("Completed discussion rounds:", len(history["rounds"]))
    print("History saved:", OUTPUT_PATH)
    print("No intervention was clinically approved or performed.")


# Run the program.
if __name__ == "__main__":
    main()