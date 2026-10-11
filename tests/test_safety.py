# Test the rules that stop negotiation.

import copy

import pytest

from vertigoai.agents import AGENT_ROLES
from vertigoai.build_context import build_context
from vertigoai.demo_agents import scripted_response
from vertigoai.disagreement import detect_disagreement
from vertigoai.safety import check_stopping
from vertigoai.validation import validate_response


@pytest.fixture
def sample():
    # Create fresh inputs for each test.
    context = build_context()

    # Get the four scripted initial answers.
    answers = [
        scripted_response(name, context)
        for name in AGENT_ROLES
    ]

    return context, answers


def make_agreement(answers, action):
    # Copy the answers so we do not change the originals.
    updated = copy.deepcopy(answers)

    # Give every agent the same action.
    for answer in updated:
        answer["recommended_action"] = action
        answer["approved_option_id"] = None

    return updated


def test_initial_disagreement(sample):
    # Four different choices should create six conflicting pairs.
    context, answers = sample
    result = detect_disagreement(answers)

    assert result["conflict_count"] == 6
    assert check_stopping(context, answers, 0)["stop"] is False


def test_candidate_agreement(sample):
    # Agreement is a candidate, not clinical approval.
    context, answers = sample
    answers = make_agreement(answers, "NO_FEEDBACK")

    result = check_stopping(context, answers, 1)

    assert result["stop"] is True
    assert result["outcome"] == "CANDIDATE_CONSENSUS"


def test_agreement_on_human_review(sample):
    # Agreement on human review must go to an expert.
    context, answers = sample
    answers = make_agreement(answers, "HUMAN_REVIEW")

    result = check_stopping(context, answers, 1)

    assert result["outcome"] == "ESCALATE_TO_EXPERT"


def test_safety_overrides_agreement(sample):
    # Mandatory escalation must override agreement.
    context, answers = sample
    answers = make_agreement(answers, "NO_FEEDBACK")

    context["scenario"]["mandatory_escalation"] = True
    context["scenario"]["missing_critical_information"] = ["Context"]

    result = check_stopping(context, answers, 0)

    assert result["outcome"] == "ESCALATE_TO_EXPERT"
    assert result["proposed_action"] == "HUMAN_REVIEW"


def test_missing_information(sample):
    # Missing critical information must stop discussion.
    context, answers = sample
    context["scenario"]["missing_critical_information"] = [
        "Exercise context"
    ]

    result = check_stopping(context, answers, 0)

    assert result["outcome"] == "NEEDS_INFORMATION"


def test_agent_requests_information(sample):
    # An agent's information request must also stop discussion.
    context, answers = sample
    answers[0]["additional_information_required"] = True
    answers[0]["information_needed"] = [
        "Does the plan permit vibration cues?"
    ]

    result = check_stopping(context, answers, 0)

    assert result["outcome"] == "NEEDS_INFORMATION"


def test_three_round_limit(sample):
    # Unresolved disagreement must stop after three rounds.
    context, answers = sample

    result = check_stopping(context, answers, 3)

    assert result["stop"] is True
    assert result["outcome"] == "UNRESOLVED_DISAGREEMENT"


def test_unchanged_positions(sample):
    # Stop if another round does not change any positions.
    context, answers = sample
    previous = copy.deepcopy(answers)

    # Different wording alone should not extend discussion.
    answers[0]["explanation"] = "I still recommend the same action."

    result = check_stopping(
        context,
        answers,
        1,
        previous=previous,
    )

    assert result["outcome"] == "UNRESOLVED_DISAGREEMENT"


def test_unsupported_action(sample):
    # Reject an action outside the permitted list.
    context, answers = sample
    answers[0]["recommended_action"] = "INVENTED_ACTION"

    with pytest.raises(ValueError):
        validate_response(
            answers[0],
            answers[0]["agent_name"],
            context,
        )


def test_unapproved_movement_option(sample):
    # Reject a movement option that is not approved.
    context, answers = sample
    answers[2]["approved_option_id"] = "INVENTED_OPTION"

    with pytest.raises(ValueError):
        validate_response(
            answers[2],
            answers[2]["agent_name"],
            context,
        )