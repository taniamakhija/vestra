# Demonstrate a scripted discussion between four agents.
# These are prepared responses, not live LLM conversations.

import copy
import json
from pathlib import Path

from .agents import AGENT_ROLES
from .disagreement import detect_disagreement
from .safety import check_stopping, MAX_ROUNDS
from .validation import validate_response


# Find our project folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Read the initial answers and save the full discussion.
INPUT_PATH = PROJECT_ROOT / "results" / "initial_recommendations.json"
OUTPUT_PATH = PROJECT_ROOT / "results" / "negotiation_history.json"


def scripted_reply(agent_name, round_number, previous, context):
    # Find this agent's previous answer.
    old_answer = next(
        answer
        for answer in previous
        if answer["agent_name"] == agent_name
    )

    # Start with a separate copy of the old answer.
    answer = copy.deepcopy(old_answer)

    # These messages describe the first discussion round.
    first_round = {
        "risk_prevention": (
            "Long-term optimization: I understand that the exercise is "
            "prescribed. I still propose considering a gentle cue, but "
            "I acknowledge practicality's concern about distraction."
        ),
        "long_term_optimization": (
            "Risk prevention: VARIABLE is a movement label, not evidence "
            "that feedback is needed. Alternatives: switching to seated "
            "may interrupt the standing practice the participant prefers."
        ),
        "alternative_strategies": (
            "Practicality: your preference evidence changes my position. "
            "An approved seated option is not automatically the best choice. "
            "I now favor NO_FEEDBACK rather than switching exercises."
        ),
        "practicality_human_impact": (
            "Risk prevention: the participant finds vibration distracting. "
            "Long-term optimization: continuing may respect their preference, "
            "but the plan does not settle this conflict. I favor HUMAN_REVIEW."
        ),
    }

    # These messages describe the second discussion round.
    second_round = {
        "risk_prevention": (
            "Long-term optimization: I accept that the model alone does not "
            "justify a cue. Practicality's evidence weakens my proposal. "
            "I now recommend HUMAN_REVIEW to resolve the competing needs."
        ),
        "long_term_optimization": (
            "Risk prevention: I agree that a cue is not established as useful. "
            "Practicality: the plan leaves this preference conflict unresolved. "
            "I now favor HUMAN_REVIEW rather than treating no feedback as settled."
        ),
        "alternative_strategies": (
            "Long-term optimization: staying with the standing exercise "
            "fits the participant's preference. Practicality: neither "
            "option resolves the full conflict. I now favor HUMAN_REVIEW."
        ),
        "practicality_human_impact": (
            "Risk prevention, long-term optimization, and alternatives: "
            "your replies recognize the limits of each proposal. "
            "I keep HUMAN_REVIEW as my recommendation."
        ),
    }

    if round_number == 1:
        # Most agents defend their initial choices.
        message = first_round[agent_name]

        # The alternatives agent changes its recommendation.
        if agent_name == "alternative_strategies":
            answer["recommended_action"] = "NO_FEEDBACK"
            answer["approved_option_id"] = None
            answer["supporting_evidence"] = ["E2", "E3", "E5"]

    else:
        # In the second round, all agents favor human review.
        message = second_round[agent_name]
        answer["recommended_action"] = "HUMAN_REVIEW"
        answer["approved_option_id"] = None
        answer["supporting_evidence"] = ["E1", "E4", "E5", "E7"]

    # Use the discussion message as the updated explanation.
    answer["explanation"] = message

    # Check the revised answer.
    validate_response(answer, agent_name, context)

    # Track whether the action or movement option changed.
    changed = (
        answer["recommended_action"],
        answer["approved_option_id"],
    ) != (
        old_answer["recommended_action"],
        old_answer["approved_option_id"],
    )

    # Save the message separately from the structured answer.
    return {
        "agent_name": agent_name,
        "message": message,
        "position_changed": changed,
        "recommendation": answer,
    }


def main():
    # Read the initial recommendations.
    initial = json.loads(
        INPUT_PATH.read_text(encoding="utf-8")
    )

    # This runner only supports the scripted sample.
    if initial["mode"] != "SCRIPTED_DEMO":
        raise ValueError("This runner requires scripted demo answers.")

    context = initial["context"]

    if context["scenario"]["scenario_id"] != (
        "simulated-conflicting-priorities-001"
    ):
        raise ValueError("These replies require the sample scenario.")

    # Keep a separate copy of the starting answers.
    current = copy.deepcopy(initial["recommendations"])
    rounds = []

    # Check safety and stopping rules before any discussion.
    stopping = check_stopping(context, current, 0)

    print("SCRIPTED NEGOTIATION — no live LLM calls")

    # Allow up to three discussion rounds.
    for round_number in range(1, MAX_ROUNDS + 1):
        if stopping["stop"]:
            break

        # Everyone sees the same previous-round answers.
        # Nobody sees replies being written in this round.
        previous = copy.deepcopy(current)
        exchanges = []

        print(f"\nROUND {round_number}")

        for agent_name in AGENT_ROLES:
            exchange = scripted_reply(
                agent_name,
                round_number,
                copy.deepcopy(previous),
                context,
            )

            exchanges.append(exchange)

            # Show the agent's reply and revised action.
            print(f"\n{agent_name}:")
            print(exchange["message"])
            print(
                "Action:",
                exchange["recommendation"]["recommended_action"],
            )
            print("Position changed:", exchange["position_changed"])

        # Update the answers only after everyone has replied.
        current = [
            exchange["recommendation"]
            for exchange in exchanges
        ]

        # Check whether another round is allowed.
        stopping = check_stopping(
            context,
            current,
            round_number,
            previous=previous,
        )

        # Save the full round for our future dashboard.
        rounds.append({
            "round_number": round_number,
            "previous_recommendations": previous,
            "exchanges": exchanges,
            "disagreement": detect_disagreement(current),
            "stopping_check": stopping,
        })

    # Save the complete discussion and final outcome.
    history = {
        "mode": "SCRIPTED_DEMO",
        "simulated": True,
        "context": context,
        "initial_recommendations": initial["recommendations"],
        "rounds": rounds,
        "final_recommendations": current,
        "stopping": stopping,
        "clinically_validated": False,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(history, indent=2),
        encoding="utf-8",
    )

    # Show why the discussion ended.
    print("\nOutcome:", stopping["outcome"])
    print("Stopping reason:", stopping["reason"])
    print("History saved:", OUTPUT_PATH)
    print("No intervention was clinically approved or performed.")


# Run the program.
if __name__ == "__main__":
    main()