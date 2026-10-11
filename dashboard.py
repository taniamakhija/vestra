# Display VESTRA's movement analysis and agent discussions.

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# Find our project folders.
ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
DATA = ROOT / "data"

# Choose the chart colors.
CHART_COLORS = ["#234638", "#627D59", "#916C43"]

# Give agents readable names.
AGENT_NAMES = {
    "risk_prevention": "Risk Prevention",
    "long_term_optimization": "Long-Term Optimization",
    "alternative_strategies": "Alternative Strategies",
    "practicality_human_impact": "Practicality and Human Impact",
}

# Give actions readable names.
ACTION_NAMES = {
    "NO_FEEDBACK": "No feedback",
    "GENTLE_HAPTIC_FEEDBACK": "Gentle haptic feedback",
    "APPROVED_MOVEMENT_MODIFICATION": "Approved movement modification",
    "HUMAN_REVIEW": "Human review",
}


def agent_name(value):
    # Show a readable agent name.
    return AGENT_NAMES.get(value, value)


def action_name(value):
    # Show a readable action name.
    return ACTION_NAMES.get(value, value)


def outcome_name(value):
    # Show a readable outcome.
    if value is None:
        return "Discussion can continue"

    return value.replace("_", " ").title()


def read_report(filename):
    # Read a saved result.
    path = RESULTS / filename

    if not path.exists():
        st.info("No saved results available for this section.")
        return None

    # Show a message if the report cannot be read.
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st.error(f"Could not read {filename}.")
        return None


def style_chart(chart):
    # Match chart text and backgrounds to the page.
    chart.update_layout(
        paper_bgcolor="#F7F4EC",
        plot_bgcolor="#F7F4EC",
        font={
            "family": "Georgia, Times New Roman, serif",
            "color": "#234638",
        },
        title_font={
            "family": "Georgia, Times New Roman, serif",
            "color": "#234638",
        },
        legend={
            "font": {
                "family": "Georgia, Times New Roman, serif",
                "color": "#234638",
            },
        },
        hoverlabel={
            "bgcolor": "#E5EBDD",
            "bordercolor": "#8FA98B",
            "font": {
                "family": "Georgia, Times New Roman, serif",
                "color": "#234638",
            },
        },
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
    )

    # Keep axes and grid lines readable.
    chart.update_xaxes(
        gridcolor="#DFE5D8",
        zerolinecolor="#DFE5D8",
        tickfont={"color": "#234638"},
    )
    chart.update_yaxes(
        gridcolor="#DFE5D8",
        zerolinecolor="#DFE5D8",
        tickfont={"color": "#234638"},
    )

    return chart


def show_table(table, include_index=False):
    # Use an HTML table so its font and colors match the page.
    # Escape cell text before displaying it.
    html = table.to_html(
        index=include_index,
        escape=True,
        border=0,
        classes="vestra-table",
    )

    st.markdown(
        '<div class="vestra-table-wrap">' + html + "</div>",
        unsafe_allow_html=True,
    )


def show_answers(answers):
    # Show each agent's recommendation.
    for answer in answers:
        title = (
            agent_name(answer["agent_name"])
            + " — "
            + action_name(answer["recommended_action"])
        )

        with st.expander(title, expanded=True):
            st.write(answer["explanation"])

            # Show evidence and the agent's own confidence.
            st.caption(
                "Evidence: "
                + ", ".join(answer["supporting_evidence"])
            )
            st.write(
                "Self-reported confidence:",
                f"{answer['confidence']:.0%}",
            )

            # Show concerns about the available choices.
            for concern in answer["concerns"]:
                st.write("Concern:", concern)

            # Show questions when more information is needed.
            if answer["additional_information_required"]:
                st.write("Additional information requested:")

                for question in answer["information_needed"]:
                    st.write("-", question)

            # Show the approved option when one is selected.
            if answer["approved_option_id"]:
                st.write("Option:", answer["approved_option_id"])


# Set up the page.
st.set_page_config(
    page_title="VESTRA",
    page_icon="🌿",
    layout="wide",
)

# Style the page with cream, forest green, and sage.
# The text inside the triple quotes is CSS.
st.markdown(
    """
    <style>
    :root {
        color-scheme: light;
    }

    .stApp {
        background-color: #F7F4EC;
        color: #234638;
        font-family: Georgia, "Times New Roman", serif;
    }

    [data-testid="stHeader"] {
        background-color: #F7F4EC !important;
    }

    [data-testid="stMainBlockContainer"] {
        padding-top: 3rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* Use Georgia and dark green for page text. */
    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp h4,
    .stApp h5,
    .stApp h6,
    .stApp p,
    .stApp label,
    .stApp input,
    .stApp textarea,
    .stApp button,
    .stApp summary,
    .stApp a,
    .stApp li,
    .stApp table,
    .stApp th,
    .stApp td,
    .stApp [data-testid="stMarkdownContainer"],
    .stApp [data-testid="stCaptionContainer"],
    .stApp [data-testid="stText"],
    .stApp [data-testid="stMetricLabel"],
    .stApp [data-testid="stMetricValue"],
    .stApp [data-testid="stMetricDelta"],
    .stApp [data-testid="stWidgetLabel"] {
        font-family: Georgia, "Times New Roman", serif !important;
        color: #234638 !important;
    }

    .stApp button span,
    .stApp label span,
    .stApp summary span,
    .stApp [data-testid="stMetric"] span {
        color: #234638 !important;
    }

    /* Style the title. */
    .vestra-title {
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(3rem, 7vw, 5rem);
        font-weight: 500;
        letter-spacing: 0.14em;
        color: #234638;
        margin-bottom: 0.4rem;
        line-height: 1.2;
    }

    .vestra-subtitle {
        font-family: Georgia, "Times New Roman", serif;
        color: #234638;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* Give each agent a sage card. */
    .agent-card {
        background-color: #E5EBDD;
        border: 1px solid #D2DDCA;
        border-radius: 14px;
        padding: 1.2rem;
        min-height: 140px;
        margin-bottom: 1rem;
    }

    .agent-card h4 {
        margin: 0 0 0.6rem 0;
        font-size: 1.15rem;
    }

    .agent-card p {
        margin: 0;
        font-size: 0.95rem;
    }

    /* Keep metrics light with dark text. */
    [data-testid="stMetric"] {
        background-color: #E5EBDD;
        border: 1px solid #D2DDCA;
        border-radius: 14px;
        padding: 1rem;
    }

    /* Style expandable sections. */
    [data-testid="stExpander"] {
        background-color: #FBF9F3;
        border: 1px solid #D2DDCA;
        border-radius: 12px;
    }

    [data-testid="stExpander"] summary:hover {
        background-color: #E5EBDD !important;
        color: #234638 !important;
    }

    /* Keep tabs dark green in every state. */
    .stTabs [data-baseweb="tab"],
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] span {
        font-family: Georgia, "Times New Roman", serif !important;
        color: #234638 !important;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #E5EBDD !important;
        color: #234638 !important;
        border-radius: 8px;
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #234638 !important;
        font-weight: 700;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #234638 !important;
    }

    .stTabs [data-baseweb="tab-border"] {
        background-color: #D2DDCA !important;
    }

    /* Keep buttons light with dark text. */
    .stApp button[kind],
    .stButton > button {
        background-color: #E5EBDD !important;
        color: #234638 !important;
        border-color: #8FA98B !important;
        border-radius: 8px;
    }

    .stApp button[kind]:hover,
    .stButton > button:hover {
        background-color: #D2DDCA !important;
        color: #234638 !important;
        border-color: #234638 !important;
    }

    /* Style the radio selection dots. */
    [data-testid="stRadio"] [role="radio"] {
        accent-color: #234638;
    }

    /* Keep notices readable on light backgrounds. */
    [data-testid="stAlert"] {
        background-color: #E5EBDD !important;
        color: #234638 !important;
        border: 1px solid #8FA98B;
    }

    /* Keep code and JSON text readable. */
    .stApp pre,
    .stApp code,
    .stApp pre span,
    .stApp code span,
    [data-testid="stJson"] {
        font-family: Georgia, "Times New Roman", serif !important;
        background-color: #E5EBDD !important;
        color: #234638 !important;
    }

    /* Style our tables. */
    .vestra-table-wrap {
        overflow-x: auto;
        margin: 1rem 0;
        border: 1px solid #D2DDCA;
        border-radius: 12px;
    }

    .vestra-table {
        width: 100%;
        border-collapse: collapse;
        background-color: #FBF9F3;
        font-family: Georgia, "Times New Roman", serif;
        color: #234638;
    }

    .vestra-table th {
        background-color: #E5EBDD;
        text-align: left;
        padding: 0.9rem;
        border-bottom: 1px solid #D2DDCA;
    }

    .vestra-table td {
        padding: 0.9rem;
        border-bottom: 1px solid #E5EBDD;
    }

    .vestra-table tbody tr:hover {
        background-color: #EEF1E7;
    }

    hr {
        border-color: #D2DDCA !important;
    }
    
         /* Keep section headers sage, including when not hovered. */
    [data-testid="stExpander"] details {
        background: #FBF9F3 !important;
    }

    [data-testid="stExpander"] details > summary,
    [data-testid="stExpander"] details > summary:hover,
    [data-testid="stExpander"] details > summary:focus,
    [data-testid="stExpander"] details > summary:active {
        background: #E5EBDD !important;
        color: #234638 !important;
    }

    [data-testid="stExpander"] details > summary * {
        background-color: transparent !important;
        color: #234638 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Show our title and subtitle.
st.markdown(
    '<div class="vestra-title">VESTRA</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="vestra-subtitle">'
    'Movement intelligence. Four perspectives. Shared deliberation.'
    '</div>',
    unsafe_allow_html=True,
)

# Create the main sections.
tabs = st.tabs([
    "Movement",
    "Agent discussion",
    "New information",
    "Safety escalation",
    "Model performance",
])


with tabs[0]:
    st.subheader("Movement analysis")
    summary = read_report("movement_summary.json")

    if summary is not None:
        # Show the prediction and window details.
        columns = st.columns(3)

        columns[0].metric(
            "Movement pattern",
            summary["predicted_pattern"],
        )
        columns[1].metric(
            "Model probability estimate",
            f"{summary['model_probability']:.1%}",
        )
        columns[2].metric(
            "Window duration",
            f"{summary['window_seconds']} seconds",
        )

        st.caption(
            f"Recording: {summary['recording_id']} "
            f"· Window: {summary['window_id']}"
        )

        # Read the sensor measurements.
        path = DATA / "synthetic_motion.csv"

        if path.exists():
            motion = pd.read_csv(path)

            # Select the recording used by the model.
            recording = motion[
                motion["recording_id"] == summary["recording_id"]
            ].copy()

            if not recording.empty:
                # Select the five-second window.
                start = (
                    recording["timestamp_s"].min()
                    + summary["window_id"] * summary["window_seconds"]
                )
                end = start + summary["window_seconds"]

                window = recording[
                    (recording["timestamp_s"] >= start)
                    & (recording["timestamp_s"] < end)
                ]

                # Plot acceleration.
                chart = px.line(
                    window,
                    x="timestamp_s",
                    y=[
                        "accel_x_m_s2",
                        "accel_y_m_s2",
                        "accel_z_m_s2",
                    ],
                    title="Simulated acceleration",
                    labels={
                        "timestamp_s": "Time (seconds)",
                        "value": "Acceleration (m/s²)",
                        "variable": "Axis",
                    },
                    color_discrete_sequence=CHART_COLORS,
                )
                st.plotly_chart(
                    style_chart(chart),
                    use_container_width=True,
                    theme=None,
                )

                # Plot turning speed.
                chart = px.line(
                    window,
                    x="timestamp_s",
                    y=[
                        "gyro_x_deg_s",
                        "gyro_y_deg_s",
                        "gyro_z_deg_s",
                    ],
                    title="Simulated turning speed",
                    labels={
                        "timestamp_s": "Time (seconds)",
                        "value": "Turning speed (degrees/second)",
                        "variable": "Axis",
                    },
                    color_discrete_sequence=CHART_COLORS,
                )
                st.plotly_chart(
                    style_chart(chart),
                    use_container_width=True,
                    theme=None,
                )

        # Show the feature values in a matching table.
        with st.expander("View movement features"):
            features = pd.DataFrame(
                list(summary["features"].items()),
                columns=["Feature", "Value"],
            )
            show_table(features)


with tabs[1]:
    st.subheader("Four perspectives")

    # Introduce the agents.
    columns = st.columns(4)
    roles = [
        ("Risk Prevention", "Immediate safety"),
        ("Long-Term Optimization", "Progress and independence"),
        ("Alternative Strategies", "Other permitted approaches"),
        ("Practicality and Human Impact", "Comfort and preferences"),
    ]

    for column, role in zip(columns, roles):
        with column:
            st.markdown(
                '<div class="agent-card">'
                f'<h4>{role[0]}</h4>'
                f'<p>{role[1]}</p>'
                '</div>',
                unsafe_allow_html=True,
            )

    # Keep real and scripted discussions separate.
    mode = st.radio(
        "Saved discussion",
        ["Live AI agents", "Scripted demo"],
        horizontal=True,
    )

    filename = (
        "live_negotiation_history.json"
        if mode == "Live AI agents"
        else "negotiation_history.json"
    )

    history = read_report(filename)

    if history is not None:
        # Describe the type of run.
        if mode == "Live AI agents":
            st.caption("Saved model-generated discussion")
        else:
            st.caption("Prepared demonstration responses")

        # Check whether the run completed.
        complete = (
            mode == "Scripted demo"
            or history.get("run_status") == "COMPLETE"
        )

        if not complete:
            st.error("This run is incomplete. Showing saved progress.")

        # Show the shared scenario.
        with st.expander("Scenario and supporting evidence"):
            scenario = history["context"]["scenario"]
            participant = scenario["patient_context"]

            st.write("Scenario:", scenario["scenario_id"])

            # Show the participant context as readable text.
            for key, value in participant.items():
                label = key.replace("_", " ").title()

                if isinstance(value, list):
                    st.markdown(f"**{label}**")

                    for item in value:
                        st.write("-", str(item))

                elif isinstance(value, dict):
                    st.markdown(f"**{label}**")

                    for item_key, item_value in value.items():
                        item_label = item_key.replace("_", " ").title()
                        st.write(f"{item_label}: {item_value}")

                else:
                    st.write(f"{label}: {value}")

            # Show each evidence item.
            st.markdown("**Supporting evidence**")

            for evidence_id, text in scenario["evidence"].items():
                st.write(f"{evidence_id}: {text}")

        # Show independent first recommendations.
        st.subheader("Initial recommendations")
        show_answers(history["initial_recommendations"])

        initial = history.get("initial_disagreement")

        if initial is not None:
            st.metric(
                "Initial conflicting pairs",
                initial["conflict_count"],
            )

        # Show each discussion round.
        for discussion in history["rounds"]:
            st.subheader(
                f"Discussion round {discussion['round_number']}"
            )

            for exchange in discussion["exchanges"]:
                st.markdown(
                    f"**{agent_name(exchange['agent_name'])}**"
                )
                st.write(exchange["message"])

                st.write(
                    "Revised recommendation:",
                    action_name(
                        exchange["recommendation"]["recommended_action"]
                    ),
                )

                st.caption(
                    "Action or option changed: "
                    + str(exchange["position_changed"])
                )
                st.divider()

            st.write(
                "Remaining conflicting pairs:",
                discussion["disagreement"]["conflict_count"],
            )

        # Show the stopping reason.
        stopping = history.get("stopping")

        if complete and stopping is not None:
            st.subheader("Discussion outcome")
            st.markdown(f"**{outcome_name(stopping['outcome'])}**")
            st.write(stopping["reason"])

            if stopping["proposed_action"] is not None:
                st.write(
                    "Proposed next action:",
                    action_name(stopping["proposed_action"]),
                )


with tabs[2]:
    st.subheader("How new evidence changes recommendations")
    report = read_report("new_information_comparison.json")

    if report is not None:
        # Show the new evidence.
        evidence = report["after_context"]["scenario"]["evidence"]
        st.markdown("**New simulated plan information**")
        st.write(evidence["E8"])
        st.caption(
            "Independent reevaluation before and after clarification"
        )

        # Compare each agent's recommendations.
        rows = []

        for change in report["changes"]:
            rows.append({
                "Agent": agent_name(change["agent_name"]),
                "Before": action_name(change["before_action"]),
                "After": action_name(change["after_action"]),
                "Choice changed": change["choice_changed"],
                "Needs information after": (
                    change["after_needs_information"]
                ),
            })

        show_table(pd.DataFrame(rows))

        # Show the revised explanations.
        st.subheader("Updated recommendations")
        show_answers(report["after_recommendations"])

        st.write(
            "Outcome:",
            outcome_name(report["after_stopping"]["outcome"]),
        )


with tabs[3]:
    st.subheader("Mandatory escalation")
    report = read_report("safety_injection.json")

    if report is not None:
        # Show the simulated stop instruction.
        evidence = report["updated_context"]["scenario"]["evidence"]
        st.write(evidence["E9"])

        # Compare the outcomes.
        columns = st.columns(2)

        columns[0].metric(
            "Before safety event",
            outcome_name(
                report["before_safety_event"]["outcome"]
            ),
        )
        columns[1].metric(
            "After safety event",
            outcome_name(
                report["after_safety_event"]["outcome"]
            ),
        )

        st.write("Reason:", report["after_safety_event"]["reason"])
        st.write("Additional model calls:", report["new_llm_calls"])
        st.write(
            "The safety gate stops discussion immediately, "
            "even when previous recommendations agree."
        )


with tabs[4]:
    st.subheader("Movement classifier performance")
    report = read_report("motion_evaluation.json")

    if report is not None:
        # Show accuracy and dataset sizes.
        columns = st.columns(3)

        columns[0].metric(
            "Accuracy",
            f"{report['accuracy']:.1%}",
        )
        columns[1].metric(
            "Training windows",
            report["training_windows"],
        )
        columns[2].metric(
            "Test windows",
            report["test_windows"],
        )

        st.caption("Evaluation on held-out simulated recordings")

        # Show scores for each movement pattern.
        labels = report["confusion_matrix_labels"]
        metrics = report["classification_report"]
        rows = []

        for label in labels:
            rows.append({
                "Pattern": label,
                "Precision": metrics[label]["precision"],
                "Recall": metrics[label]["recall"],
                "F1": metrics[label]["f1-score"],
                "Test windows": metrics[label]["support"],
            })

        show_table(pd.DataFrame(rows))

        # Show the confusion matrix.
        matrix = pd.DataFrame(
            report["confusion_matrix"],
            index=labels,
            columns=labels,
        )

        st.subheader("Confusion matrix")
        st.caption("Rows: actual pattern · Columns: predicted pattern")
        show_table(matrix, include_index=True)

# Compare the single agent with the four-agent team.
st.divider()
st.header("Single agent vs. four-agent negotiation")

comparison = read_report("baseline_comparison.json")

if comparison is not None:
    # Read both approaches from the saved comparison.
    baseline = comparison["baseline"]
    team = comparison["multi_agent"]
    answer = baseline["recommendation"]

    st.caption("Same simulated scenario · One saved run per approach")

    # Show the two outcomes side by side.
    left, right = st.columns(2)

    with left:
        st.subheader("Single agent")
        st.write("One agent considers all four objectives.")

        st.metric(
            "Proposed action",
            action_name(answer["recommended_action"]),
        )
        st.write(answer["explanation"])

        st.write("Outcome:", outcome_name(baseline["outcome"]))
        st.write("Model calls:", baseline["model_calls"])
        st.write(
            "Processing time:",
            f"{baseline['elapsed_seconds']:.1f} seconds",
        )

    with right:
        st.subheader("Four-agent team")
        st.write("Four agents exchange and challenge recommendations.")

        st.metric(
            "Outcome",
            outcome_name(team["stopping"]["outcome"]),
        )

        for response in team["final_recommendations"]:
            st.write(
                agent_name(response["agent_name"]),
                "→",
                action_name(response["recommended_action"]),
            )

        st.write("Discussion rounds:", team["discussion_rounds"])
        st.write("Model calls:", team["model_calls"])
        st.write("Stopping reason:", team["stopping"]["reason"])

    # Explain what this experiment actually demonstrates.
    st.subheader("What this comparison shows")
    st.write(
        "The single agent produces one proposal. "
        "The team makes competing priorities visible and can preserve "
        "disagreement instead of selecting a majority winner."
    )

    # Keep the experiment's limits available for inspection.
    with st.expander("Evaluation scope"):
        for limitation in comparison["limitations"]:
            st.write("-", limitation)

# Run the real agents directly from the dashboard.
import subprocess
import sys

st.divider()
st.header("Run a live negotiation")

st.write(
    "Start a fresh run on the simulated negotiation scenario. "
    "Each agent generates an independent recommendation. "
    "If disagreement remains and the stopping rules permit it, "
    "the agents respond to each other's arguments."
)

st.caption(
    "Uses your signed-in model connection. "
    "Makes 4 initial calls and up to 12 discussion calls. "
    "This replaces the saved live negotiation report."
)

# Show a completion message after refreshing the page.
if st.session_state.get("live_run_finished", False):
    st.success(
        "Live negotiation completed. "
        "Open Agent discussion → Live AI agents to inspect the new run."
    )
    st.session_state["live_run_finished"] = False

# Run only when the button is clicked.
if st.button("Run live negotiation", key="run_live_negotiation"):
    # Show progress while the real model calls run.
    with st.status(
        "Running the four agents...",
        expanded=True,
    ) as status:
        output_box = st.empty()
        output_lines = []

        try:
            # Use the same Python environment as the dashboard.
            command = [
                sys.executable,
                "-u",
                "-m",
                "vertigoai.live_negotiation",
            ]

            # Start the existing live negotiation script.
            # No shell is used.
            with subprocess.Popen(
                command,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            ) as process:
                # Display completed calls and discussion replies.
                for line in process.stdout:
                    output_lines.append(line.rstrip())

                    # Keep the progress display manageable.
                    output_box.code(
                        "\n".join(output_lines[-60:]),
                        language="text",
                    )

                return_code = process.wait()

            # Verify that the saved run actually completed.
            complete = False
            report_path = RESULTS / "live_negotiation_history.json"

            if return_code == 0 and report_path.exists():
                saved_run = json.loads(
                    report_path.read_text(encoding="utf-8")
                )
                complete = saved_run.get("run_status") == "COMPLETE"

            if complete:
                status.update(
                    label="Live negotiation completed",
                    state="complete",
                    expanded=True,
                )

                # Refresh every section with the new results.
                st.session_state["live_run_finished"] = True
                st.rerun()

            else:
                status.update(
                    label="The run did not complete",
                    state="error",
                    expanded=True,
                )
                st.error(
                    "Review the output above. "
                    "An incomplete run is not a final decision."
                )

        except (OSError, ValueError) as error:
            status.update(
                label="Could not complete the live run",
                state="error",
                expanded=True,
            )
            st.error(str(error))