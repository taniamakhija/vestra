# Combine the movement prediction and scenario for the agents.

import json
from pathlib import Path


# Find the main project folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Find the settings file.
CONFIG_PATH = PROJECT_ROOT / "config" / "vertigoai.json"

# Find the simulated scenario.
SCENARIO_PATH = PROJECT_ROOT / "data" / "sample_scenario.json"

# Find the saved movement prediction.
MOVEMENT_PATH = PROJECT_ROOT / "results" / "movement_summary.json"

# Choose where to save the shared input.
OUTPUT_PATH = PROJECT_ROOT / "results" / "agent_context.json"


def read_json(path):
    # Read the file as text.
    text = path.read_text(encoding="utf-8")

    # Turn the text into Python data.
    return json.loads(text)


def build_context():
    # Read the permitted actions and rules.
    domain = read_json(CONFIG_PATH)

    # Read the participant's simulated situation.
    scenario = read_json(SCENARIO_PATH)

    # Read the movement model's prediction.
    movement = read_json(MOVEMENT_PATH)

    # Check that the scenario is simulated.
    if scenario.get("simulated") is not True:
        raise ValueError("The scenario must be marked as simulated.")

    # Check that the movement data is simulated.
    if movement.get("simulated") is not True:
        raise ValueError("The movement summary must be simulated.")

    # Replace the handwritten summary with the model's output.
    scenario["movement_summary"] = movement

    # Keep the other evidence from the scenario.
    evidence = dict(scenario["evidence"])

    # Use the model's prediction as the movement evidence.
    evidence["E1"] = (
        f"The model classified a simulated five-second window as "
        f"{movement['predicted_pattern']}. "
        f"Its probability estimate was "
        f"{movement['model_probability']:.1%}. "
        "This does not establish danger or clinical benefit."
    )

    # Put the updated evidence back into the scenario.
    scenario["evidence"] = evidence

    # Every agent will receive these same settings and scenario.
    return {
        "domain": domain,
        "scenario": scenario,
    }


def main():
    # Create the shared input.
    context = build_context()

    # Create the results folder if needed.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save the shared input as JSON.
    OUTPUT_PATH.write_text(
        json.dumps(context, indent=2),
        encoding="utf-8",
    )

    # Show the movement prediction.
    movement = context["scenario"]["movement_summary"]
    print("Movement pattern:", movement["predicted_pattern"])

    # Show which actions the agents may choose.
    print("Permitted actions:")

    for action in context["domain"]["actions"]:
        print("-", action)

    # Show where the file was saved.
    print("Shared input saved:", OUTPUT_PATH)
    print("All four agents will receive this same input.")


# Run the program.
if __name__ == "__main__":
    main()