# Check that each agent's answer follows our rules.

from .agents import AGENT_ROLES


def validate_response(response, agent_name, context):
    # List the fields every answer must contain.
    required_fields = {
        "agent_name",
        "recommended_action",
        "explanation",
        "supporting_evidence",
        "confidence",
        "concerns",
        "additional_information_required",
        "information_needed",
        "approved_option_id",
    }

    # The answer must be a JSON object.
    if not isinstance(response, dict):
        raise ValueError("The agent answer must be a JSON object.")

    # Check that all required fields are present.
    if set(response) != required_fields:
        raise ValueError("The agent answer has missing or extra fields.")

    # Check that we are using a known agent.
    if agent_name not in AGENT_ROLES:
        raise ValueError("Unknown agent name.")

    # The answer must belong to the correct agent.
    if response["agent_name"] != agent_name:
        raise ValueError("The answer has the wrong agent name.")

    # Read the shared settings and scenario.
    domain = context["domain"]
    scenario = context["scenario"]

    # Check that the action is permitted.
    action = response["recommended_action"]

    if action not in domain["actions"]:
        raise ValueError("The agent suggested an unsupported action.")

    # Require a short explanation.
    explanation = response["explanation"]

    if not isinstance(explanation, str) or not explanation.strip():
        raise ValueError("The agent must explain its recommendation.")

    # These fields must contain lists of text.
    list_fields = [
        "supporting_evidence",
        "concerns",
        "information_needed",
    ]

    for field in list_fields:
        values = response[field]

        if not isinstance(values, list):
            raise ValueError(f"{field} must be a list.")

        for value in values:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must contain nonempty text.")

    # Evidence IDs must exist in the shared scenario.
    for evidence_id in response["supporting_evidence"]:
        if evidence_id not in scenario["evidence"]:
            raise ValueError("The agent cited unsupported evidence.")

    # Confidence must be a number between zero and one.
    confidence = response["confidence"]

    if type(confidence) not in (int, float):
        raise ValueError("Confidence must be a number.")

    if not 0 <= confidence <= 1:
        raise ValueError("Confidence must be between zero and one.")

    # The information flag must be true or false.
    needs_information = response["additional_information_required"]

    if type(needs_information) is not bool:
        raise ValueError("The information flag must be true or false.")

    # The flag must match the list of questions.
    questions = response["information_needed"]

    if needs_information != bool(questions):
        raise ValueError("The information flag and questions do not match.")

    # Read the chosen movement option, if any.
    option = response["approved_option_id"]

    if action == "APPROVED_MOVEMENT_MODIFICATION":
        # A modification must name an approved option.
        if not isinstance(option, str):
            raise ValueError("A modification must include an option ID.")

        if option not in domain["approved_options"]:
            raise ValueError("The movement option is not approved.")

        # The option must also be available to this participant.
        available_options = scenario["patient_context"].get(
            "available_approved_options",
            [],
        )

        if option not in available_options:
            raise ValueError("The option is not available in this scenario.")

    else:
        # Other actions must not include a movement option.
        if option is not None:
            raise ValueError("Only modifications can include an option ID.")

    # Return the answer after it passes all checks.
    return response