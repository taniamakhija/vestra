# Decide whether negotiation should continue or stop.

from .disagreement import detect_disagreement
from .validation import validate_response


# Allow no more than three discussion rounds.
MAX_ROUNDS = 3


def decision_signature(recommendations):
    # Compare choices and information requests.
    # Changing only the wording does not count as a new position.
    positions = []

    for response in recommendations:
        position = (
            response["agent_name"],
            response["recommended_action"],
            response["approved_option_id"],
            response["additional_information_required"],
            tuple(sorted(response["information_needed"])),
        )

        positions.append(position)

    # Sort by agent so answer order does not affect the comparison.
    return tuple(sorted(positions))


def check_stopping(context, recommendations, rounds_completed, previous=None):
    # Check that the round count is valid.
    if type(rounds_completed) is not int or rounds_completed < 0:
        raise ValueError("The round count must be a nonnegative integer.")

    # Check every current answer.
    for response in recommendations:
        validate_response(
            response,
            response["agent_name"],
            context,
        )

    # Also check that all four agents are present.
    disagreement = detect_disagreement(recommendations)
    scenario = context["scenario"]

    # Mandatory escalation takes priority over agreement.
    if scenario["mandatory_escalation"]:
        return {
            "stop": True,
            "outcome": "ESCALATE_TO_EXPERT",
            "reason": "The scenario requires mandatory safety escalation.",
            "proposed_action": "HUMAN_REVIEW",
        }

    # Stop if critical scenario information is missing.
    if scenario["missing_critical_information"]:
        return {
            "stop": True,
            "outcome": "NEEDS_INFORMATION",
            "reason": "Critical scenario information is missing.",
            "proposed_action": "HUMAN_REVIEW",
        }

    # Stop if any agent says it needs more information.
    if disagreement["additional_information_requested"]:
        return {
            "stop": True,
            "outcome": "NEEDS_INFORMATION",
            "reason": "An agent needs more information before proceeding.",
            "proposed_action": "HUMAN_REVIEW",
        }

    # Agreement requires matching actions and movement options.
    if not disagreement["meaningful_disagreement"]:
        action = recommendations[0]["recommended_action"]

        # Agreement on human review goes to an expert.
        if action == "HUMAN_REVIEW":
            return {
                "stop": True,
                "outcome": "ESCALATE_TO_EXPERT",
                "reason": "All four agents recommend human review.",
                "proposed_action": "HUMAN_REVIEW",
            }

        # Other agreement is only a candidate for review.
        return {
            "stop": True,
            "outcome": "CANDIDATE_CONSENSUS",
            "reason": (
                "All four agents agree and the prototype checks pass. "
                "This is not clinical approval."
            ),
            "proposed_action": action,
        }

    # Stop after three discussion rounds.
    if rounds_completed >= MAX_ROUNDS:
        return {
            "stop": True,
            "outcome": "UNRESOLVED_DISAGREEMENT",
            "reason": "The three-round discussion limit was reached.",
            "proposed_action": "HUMAN_REVIEW",
        }

    # Compare with the previous round when one is available.
    if previous is not None:
        for response in previous:
            validate_response(
                response,
                response["agent_name"],
                context,
            )

        detect_disagreement(previous)

        # Stop if the agents' choices and questions have not changed.
        if decision_signature(recommendations) == decision_signature(previous):
            return {
                "stop": True,
                "outcome": "UNRESOLVED_DISAGREEMENT",
                "reason": "The agents' positions stopped changing.",
                "proposed_action": "HUMAN_REVIEW",
            }

    # Otherwise, allow another discussion round.
    return {
        "stop": False,
        "outcome": None,
        "reason": "The agents disagree and discussion can continue.",
        "proposed_action": None,
    }