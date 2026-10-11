# Run VESTRA's agents and show a clear ending.

import copy
import json
import time
import uuid
from html import escape
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from vertigoai.agents import AGENT_ROLES
from vertigoai.codex_provider import ask_agent
from vertigoai.disagreement import detect_disagreement
from vertigoai.safety import check_stopping, MAX_ROUNDS


# Find the project folders.
ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
DATA = ROOT / "data"

# Give agents readable names.
NAMES = {
    "risk_prevention": "Risk Prevention",
    "long_term_optimization": "Long-Term Optimization",
    "alternative_strategies": "Alternative Strategies",
    "practicality_human_impact": "Practicality and Human Impact",
}

# Give each stopping outcome a clear title.
ENDING_TITLES = {
    "CANDIDATE_CONSENSUS": "Consensus reached",
    "UNRESOLVED_DISAGREEMENT": (
        "Discussion stopped - disagreement remains"
    ),
    "NEEDS_INFORMATION": "Paused - more information needed",
    "ESCALATE_TO_EXPERT": "Stopped - human review required",
}


def readable(value):
    # Make saved action names easier to read.
    if value is None:
        return "Discussion can continue"

    return value.replace("_", " ").title()


def save_run(run):
    # Save each conversation separately.
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"vestra_chat_{run['id']}.json"

    path.write_text(
        json.dumps(run, indent=2),
        encoding="utf-8",
    )


def add_event(run, title, answers=None, message=None):
    # Keep a snapshot of this step.
    run["events"].append({
        "title": title,
        "answers": copy.deepcopy(answers or []),
        "message": message,
        "context": copy.deepcopy(run["context"]),
        "stopping": copy.deepcopy(run["stopping"]),
    })

    save_run(run)


def predict_pattern(pattern):
    # Load the model we trained ourselves.
    saved = joblib.load(RESULTS / "motion_model.joblib")
    model = saved["model"]
    columns = saved["feature_columns"]

    # Read the features and test recording IDs.
    features = pd.read_csv(DATA / "motion_features.csv")
    evaluation = json.loads(
        (RESULTS / "motion_evaluation.json").read_text(
            encoding="utf-8"
        )
    )

    # Choose a held-out recording of the selected pattern.
    candidates = features[
        features["recording_id"].isin(
            evaluation["test_recording_ids"]
        )
        & (features["pattern_label"] == pattern)
    ].sort_values(["recording_id", "window_id"])

    if candidates.empty:
        raise ValueError("No matching held-out recording was found.")

    selected = candidates.iloc[[0]]
    row = selected.iloc[0]

    # Run the trained movement classifier.
    prediction = str(model.predict(selected[columns])[0])
    probabilities = model.predict_proba(selected[columns])[0]

    estimates = {
        str(label): float(probability)
        for label, probability in zip(
            model.classes_,
            probabilities,
        )
    }

    return {
        "simulated": True,
        "selected_dataset_pattern": pattern,
        "predicted_pattern": prediction,
        "model_probability": estimates[prediction],
        "recording_id": str(row["recording_id"]),
        "window_id": int(row["window_id"]),
        "window_seconds": 5,
        "selection": "Held-out simulated recording selected by pattern.",
    }


def create_context(pattern, situation, preferences):
    # Read the permitted actions and fictional approved options.
    domain = json.loads(
        (ROOT / "config" / "vertigoai.json").read_text(
            encoding="utf-8"
        )
    )

    movement = predict_pattern(pattern)

    # Use only the context entered for this conversation.
    scenario = {
        "scenario_id": "user-entered-simulation",
        "simulated": True,
        "movement_summary": movement,
        "patient_context": {
            "situation": situation,
            "preferences": preferences,
            "available_approved_options": list(
                domain["approved_options"]
            ),
        },
        "evidence": {
            "E1": (
                f"The classifier predicts "
                f"{movement['predicted_pattern']} for a simulated "
                "five-second recording. This does not establish danger."
            ),
            "E2": "User-entered simulated situation: " + situation,
            "E3": "User-entered simulated preferences: " + preferences,
            "E4": (
                "The domain configuration supplies fictional approved "
                "movement options. Availability does not establish "
                "that an option is best for this situation."
            ),
        },
        "mandatory_escalation": False,
        "missing_critical_information": [],
    }

    return {"domain": domain, "scenario": scenario}


def show_answers(answers):
    # Show each agent's response as a chat bubble.
    for answer in answers:
        with st.chat_message("assistant", avatar="🌿"):
            st.markdown(f"**{NAMES[answer['agent_name']]}**")
            st.markdown(
                "**Proposal: "
                + readable(answer["recommended_action"])
                + "**"
            )

            st.write(answer["explanation"])
            st.caption(
                "Evidence: "
                + ", ".join(answer["supporting_evidence"])
            )

            # Show questions when information is missing.
            for question in answer["information_needed"]:
                st.write("Question:", question)


def evaluate(run, discussion=False, new_evidence=False):
    # Freeze previous answers for all agents in this round.
    previous = copy.deepcopy(run["answers"])
    answers = []

    title = (
        f"Discussion round {run['rounds'] + 1}"
        if discussion
        else "Independent perspectives"
    )

    with st.status(title, expanded=True) as status:
        for name in AGENT_ROLES:
            st.write(f"Waiting for {NAMES[name]}...")
            run["calls"] += 1
            save_run(run)
            started = time.perf_counter()

            try:
                answer = ask_agent(
                    name,
                    copy.deepcopy(run["context"]),
                    previous_answers=(
                        copy.deepcopy(previous) if discussion else None
                    ),
                )
            except Exception:
                # Never turn a partial round into a final decision.
                run["failed"] = True
                run["stopping"] = None

                add_event(
                    run,
                    "Incomplete stage",
                    answers=answers,
                    message=f"The call for {NAMES[name]} failed.",
                )

                status.update(
                    state="error",
                    label="Run incomplete",
                )
                raise

            run["seconds"] += time.perf_counter() - started
            answers.append(answer)

            # Display each real answer when it arrives.
            show_answers([answer])

        status.update(
            state="complete",
            label="Stage completed",
        )

    # Update only after all four agents finish.
    run["answers"] = answers

    if discussion:
        run["rounds"] += 1

    # Apply the same safety and stopping checks.
    run["stopping"] = check_stopping(
        run["context"],
        answers,
        run["rounds"],
        previous=(
            previous if discussion and not new_evidence else None
        ),
    )

    add_event(run, title, answers=answers)


def show_ending(run):
    # Show one clear card for the ending.
    stopping = run["stopping"]
    conflicts = detect_disagreement(run["answers"])

    title = ENDING_TITLES.get(
        stopping["outcome"],
        "Evaluation completed",
    )

    action = stopping.get("proposed_action")
    action_text = (
        readable(action)
        if action is not None
        else "No final action selected"
    )

    # Escape saved text before placing it in HTML.
    st.markdown(
        f"""
        <div class="ending-card">
            <div class="ending-label">EVALUATION ENDED</div>
            <h2>{escape(title)}</h2>
            <p>
                <strong>Proposed next action:</strong>
                {escape(action_text)}
            </p>
            <p>{escape(stopping["reason"])}</p>
            <p>
                Completed discussion rounds: {run["rounds"]}
                &nbsp; | &nbsp;
                Remaining conflicting pairs: {conflicts["conflict_count"]}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_timeline(run):
    # Compare proposals across completed stages.
    rows = []

    for event in run["events"]:
        for answer in event["answers"]:
            rows.append({
                "Stage": event["title"],
                "Agent": NAMES[answer["agent_name"]],
                "Proposal": readable(answer["recommended_action"]),
                "Needs information": (
                    answer["additional_information_required"]
                ),
            })

    if rows:
        # Use a table with the same font and colors.
        table = pd.DataFrame(rows).to_html(
            index=False,
            escape=True,
            border=0,
        )

        st.markdown(
            '<div class="timeline">' + table + "</div>",
            unsafe_allow_html=True,
        )


# Set up the page.
st.set_page_config(page_title="VESTRA", layout="wide")

# Keep all controls light with dark green text.
st.markdown(
    """
    <style>
    .stApp, [data-testid="stHeader"] {
        background: #F7F4EC !important;
        color: #234638 !important;
    }

    .stApp h1, .stApp h2, .stApp h3,
    .stApp p, .stApp label, .stApp li,
    .stApp button, .stApp summary,
    [data-testid="stCaptionContainer"] {
        font-family: Georgia, "Times New Roman", serif !important;
        color: #234638 !important;
    }

    .stApp p, .stApp label {
        font-size: 20px;
        line-height: 1.6;
    }

    [data-testid="stChatMessage"],
    [data-testid="stChatMessageContent"],
    [data-testid="stExpander"] {
        background: #FBF9F3 !important;
        color: #234638 !important;
        border-radius: 12px;
    }

    [data-testid="stChatMessage"] {
        border: 1px solid #D2DDCA;
        margin-bottom: 14px;
    }

    [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessageContent"] span {
        color: #234638 !important;
    }

    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary:hover,
    [data-testid="stStatusWidget"] summary,
    [data-testid="stStatusWidget"] summary:hover {
        background: #E5EBDD !important;
        color: #234638 !important;
    }

    [data-testid="stExpander"] summary *,
    [data-testid="stStatusWidget"] summary * {
        background: transparent !important;
        color: #234638 !important;
    }

    textarea, input,
    [data-baseweb="textarea"],
    [data-baseweb="input"],
    [data-baseweb="select"] > div,
    [data-baseweb="select"] > div > div {
        background: #FBF9F3 !important;
        color: #234638 !important;
        border-color: #8FA98B !important;
    }

    textarea, input {
        -webkit-text-fill-color: #234638 !important;
    }

    [data-baseweb="select"] svg {
        color: #234638 !important;
        fill: #234638 !important;
    }

    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    [data-baseweb="menu"],
    [role="listbox"],
    [role="option"] {
        background: #FBF9F3 !important;
        color: #234638 !important;
    }

    [role="option"] *,
    [data-baseweb="menu"] li * {
        color: #234638 !important;
    }

    [role="option"]:hover,
    [role="option"][aria-selected="true"],
    [data-baseweb="menu"] li:hover {
        background: #E5EBDD !important;
    }

    .stButton button,
    .stDownloadButton button,
    [data-testid="stFormSubmitButton"] button {
        background: #E5EBDD !important;
        color: #234638 !important;
        border: 1px solid #8FA98B !important;
        box-shadow: none !important;
    }

    .stButton button *,
    .stDownloadButton button *,
    [data-testid="stFormSubmitButton"] button * {
        color: #234638 !important;
    }

    .stButton button:hover,
    [data-testid="stFormSubmitButton"] button:hover {
        background: #D2DDCA !important;
    }

    [data-testid="stChatInput"],
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] textarea {
        background: #FBF9F3 !important;
        color: #234638 !important;
        border-color: #8FA98B !important;
    }

    [data-testid="stChatInput"] button {
        background: #E5EBDD !important;
        color: #234638 !important;
    }

    [data-testid="stChatInput"] button svg {
        fill: #234638 !important;
        color: #234638 !important;
    }

    .stTabs [data-baseweb="tab"] * {
        color: #234638 !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background: #234638 !important;
    }

    .ending-card {
        background: #E5EBDD;
        border: 1px solid #8FA98B;
        border-radius: 16px;
        padding: 24px;
        margin: 24px 0 16px;
        color: #234638;
        font-family: Georgia, "Times New Roman", serif;
    }

    .ending-card h2 {
        margin-top: 8px;
        color: #234638;
    }

    .ending-label {
        color: #234638;
        font-size: 14px;
        letter-spacing: 0.12em;
    }

    .timeline {
        overflow-x: auto;
    }

    .timeline table {
        width: 100%;
        border-collapse: collapse;
        background: #FBF9F3;
        color: #234638;
        font-family: Georgia, "Times New Roman", serif;
    }

    .timeline th {
        background: #E5EBDD;
        text-align: left;
    }

    .timeline th, .timeline td {
        padding: 0.8rem;
        border-bottom: 1px solid #D2DDCA;
    }

    [data-testid="stMetric"] {
        background: #E5EBDD;
        padding: 1rem;
        border-radius: 12px;
    }

    .stApp code {
        background: #E5EBDD !important;
        color: #234638 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("VESTRA")
st.subheader("Live agent conversation")
st.caption("Simulated situations | Real model-generated responses")

# Keep the conversation between page refreshes.
if "vestra_chat" not in st.session_state:
    st.session_state["vestra_chat"] = None

conversation_tab, reflection_tab = st.tabs([
    "Conversation",
    "Run reflection",
])


with conversation_tab:
    # Collect the three inputs before calling agents.
    with st.form("demo_input"):
        st.markdown("### Enter your situation")

        pattern = st.selectbox(
            "1. Which simulated movement pattern?",
            ["VARIABLE", "STEADY", "TRANSITION"],
        )

        situation = st.text_area(
            "2. What is happening?",
            value=(
                "The participant is performing a standing balance "
                "exercise in a fictional prescribed plan. Continuing "
                "without feedback, one gentle cue, and the supplied "
                "seated alternative are permitted proposals. "
                "No mandatory stop instruction is present. "
                "One cue helped awareness in an earlier simulated session, "
                "but no option is established as best."
            ),
            height=160,
        )

        preferences = st.text_area(
            "3. What does the participant prefer?",
            value=(
                "Prefers standing practice for independence. "
                "Accepts one brief vibration cue but finds repeated "
                "cues distracting. Accepts the seated alternative "
                "but finds it less engaging."
            ),
            height=120,
        )

        submitted = st.form_submit_button(
            "Start new conversation"
        )

    if submitted:
        if not situation.strip() or not preferences.strip():
            st.error("Enter the situation and preferences first.")
        else:
            try:
                context = create_context(
                    pattern,
                    situation.strip(),
                    preferences.strip(),
                )
            except Exception as error:
                st.error(str(error))
            else:
                # Start a new saved conversation.
                run = {
                    "id": uuid.uuid4().hex[:12],
                    "mode": "LIVE_MODEL_RESPONSES",
                    "context": context,
                    "answers": [],
                    "events": [],
                    "rounds": 0,
                    "calls": 0,
                    "seconds": 0.0,
                    "stopping": None,
                    "failed": False,
                }

                st.session_state["vestra_chat"] = run

                add_event(
                    run,
                    "Input submitted",
                    message=(
                        f"Selected pattern: {pattern}\n\n"
                        f"Situation: {situation}\n\n"
                        f"Preferences: {preferences}"
                    ),
                )

                try:
                    evaluate(run)
                except Exception as error:
                    st.error(str(error))
                else:
                    st.rerun()

    run = st.session_state["vestra_chat"]

    if run is not None:
        # Show the selected recording's actual model prediction.
        movement = run["context"]["scenario"]["movement_summary"]

        st.caption(
            "Model prediction: "
            + movement["predicted_pattern"]
            + " | Recording: "
            + movement["recording_id"]
        )

        # Show the completed conversation in order.
        for event in run["events"]:
            st.markdown(f"### {event['title']}")

            if event["message"]:
                with st.chat_message("user", avatar="📝"):
                    st.write(event["message"])

            show_answers(event["answers"])

        if run["failed"]:
            st.error(
                "This run is incomplete. "
                "Start a new conversation to retry."
            )

        elif run["answers"]:
            stopping = run["stopping"]
            conflicts = detect_disagreement(run["answers"])

            if stopping["stop"]:
                # End with one clear result card.
                show_ending(run)

                st.write(
                    "This evaluation has ended. Open Run reflection "
                    "to review its timeline or download the conversation."
                )

            else:
                # Show conflicts only while discussion remains open.
                st.subheader("The agents are weighing different choices")
                st.write(
                    "Conflicting pairs:",
                    str(conflicts["conflict_count"]),
                )

                for conflict in conflicts["conflicts"]:
                    st.write(
                        NAMES[conflict["first_agent"]],
                        "proposes",
                        readable(conflict["first_action"]),
                        "while",
                        NAMES[conflict["second_agent"]],
                        "proposes",
                        readable(conflict["second_action"]),
                    )

                if st.button("Run the next discussion round"):
                    try:
                        evaluate(run, discussion=True)
                    except Exception as error:
                        st.error(str(error))
                    else:
                        st.rerun()

            # Hide extra controls beneath the ending.
            mandatory = run["context"]["scenario"]["mandatory_escalation"]

            if not mandatory:
                update_title = (
                    "Reopen with new information - optional"
                    if stopping["stop"]
                    else "Add new information before the next round"
                )

                with st.expander(update_title, expanded=False):
                    st.write(
                        "New evidence can trigger reevaluation within "
                        "the three-round limit. Previous outcomes remain "
                        "in the saved history."
                    )

                    event_type = st.selectbox(
                        "Update type",
                        [
                            "New context or preference",
                            "Mandatory safety stop",
                        ],
                    )

                    # Allow safety escalation even at the round limit.
                    can_update = (
                        run["rounds"] < MAX_ROUNDS
                        or event_type == "Mandatory safety stop"
                    )

                    if not can_update:
                        st.write(
                            "The discussion limit has been reached. "
                            "Start a new conversation for further evaluation."
                        )

                    update = st.chat_input(
                        "Enter new evidence...",
                        disabled=not can_update,
                        key="new_context_message",
                    )

                    if update:
                        scenario = run["context"]["scenario"]

                        # Add the update without deleting history.
                        number = len(scenario["evidence"]) + 1
                        evidence_id = f"E{number}"

                        scenario["evidence"][evidence_id] = (
                            "New user-entered simulated information: "
                            + update
                            + " This supersedes earlier context where "
                            "it explicitly changes it."
                        )

                        scenario["patient_context"].setdefault(
                            "updates",
                            [],
                        ).append(update)

                        if event_type == "Mandatory safety stop":
                            # Stop immediately without another model call.
                            scenario["mandatory_escalation"] = True

                            run["stopping"] = check_stopping(
                                run["context"],
                                run["answers"],
                                run["rounds"],
                            )

                            add_event(
                                run,
                                "Mandatory safety information",
                                message=update,
                            )
                            st.rerun()

                        else:
                            add_event(
                                run,
                                "New information",
                                message=update,
                            )

                            try:
                                evaluate(
                                    run,
                                    discussion=True,
                                    new_evidence=True,
                                )
                            except Exception as error:
                                st.error(str(error))
                            else:
                                st.rerun()


with reflection_tab:
    run = st.session_state["vestra_chat"]

    if run is None:
        st.write("Start a conversation to create its reflection.")

    else:
        st.subheader("Reflection on this conversation")

        # Show measured usage for this run.
        columns = st.columns(3)
        columns[0].metric("Model calls attempted", run["calls"])
        columns[1].metric("Completed rounds", run["rounds"])
        columns[2].metric(
            "Successful processing time",
            f"{run['seconds']:.1f} seconds",
        )

        if run["failed"]:
            st.error("Incomplete run - no final decision.")

        elif run["stopping"] is not None:
            if run["stopping"]["stop"]:
                show_ending(run)
            else:
                st.write("Discussion remains open.")

        # Show the sequence of recommendations.
        st.subheader("Recommendation timeline")
        show_timeline(run)

        # Keep the complete stage history available.
        st.subheader("Stage history")

        for event in run["events"]:
            with st.expander(event["title"]):
                if event["message"]:
                    st.write(event["message"])

                show_answers(event["answers"])

                if event["stopping"] is not None:
                    st.write(
                        "Outcome at this stage:",
                        readable(event["stopping"]["outcome"]),
                    )

        st.download_button(
            "Download complete conversation",
            data=json.dumps(run, indent=2),
            file_name=f"vestra_conversation_{run['id']}.json",
            mime="application/json",
        )