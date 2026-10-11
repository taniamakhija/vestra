# Use our trained model to create a movement summary.

import json
from pathlib import Path

import joblib
import pandas as pd


# Find the main project folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Find the files we created earlier.
FEATURES_PATH = PROJECT_ROOT / "data" / "motion_features.csv"
MODEL_PATH = PROJECT_ROOT / "results" / "motion_model.joblib"
REPORT_PATH = PROJECT_ROOT / "results" / "motion_evaluation.json"

# Choose where to save the prediction.
OUTPUT_PATH = PROJECT_ROOT / "results" / "movement_summary.json"


def main():
    # Load the model we trained.
    saved_model = joblib.load(MODEL_PATH)
    model = saved_model["model"]
    feature_columns = saved_model["feature_columns"]

    # Read the movement features.
    features = pd.read_csv(FEATURES_PATH)

    # Read the list of test recordings.
    report_text = REPORT_PATH.read_text(encoding="utf-8")
    report = json.loads(report_text)
    test_ids = report["test_recording_ids"]

    # Keep only windows from the test recordings.
    test_windows = features[
        features["recording_id"].isin(test_ids)
    ].copy()

    # Choose a VARIABLE example for our demo.
    candidates = test_windows[
        test_windows["pattern_label"] == "VARIABLE"
    ].copy()

    # Put the examples in a fixed order.
    candidates = candidates.sort_values(
        ["recording_id", "window_id"]
    )

    # Stop if no matching example exists.
    if candidates.empty:
        raise ValueError("No VARIABLE test window was found.")

    # Select one five-second window.
    selected = candidates.iloc[[0]]
    row = selected.iloc[0]

    # Give the model only the movement features.
    model_input = selected[feature_columns]

    # Predict the movement pattern.
    prediction = str(model.predict(model_input)[0])

    # Get the model's probability estimates.
    probabilities = model.predict_proba(model_input)[0]

    # Match each pattern with its probability estimate.
    probability_by_pattern = {}

    for label, probability in zip(model.classes_, probabilities):
        probability_by_pattern[str(label)] = float(probability)

    # Save the feature values used by the model.
    feature_values = {}

    for column in feature_columns:
        feature_values[column] = float(row[column])

    # Get the estimate for the predicted pattern.
    predicted_probability = probability_by_pattern[prediction]

    # Create the summary we will give to the agents.
    summary = {
        "simulated": True,
        "recording_id": str(row["recording_id"]),
        "window_id": int(row["window_id"]),
        "window_seconds": 5,
        "predicted_pattern": prediction,
        "model_probability": predicted_probability,
        "probabilities_by_pattern": probability_by_pattern,
        "features": feature_values,
        "selection_note": (
            "A VARIABLE window was deliberately selected "
            "from the held-out test recordings."
        ),
        "interpretation": (
            "This prediction describes a simulated movement pattern. "
            "It does not determine safety or choose an intervention."
        ),
        "probability_note": (
            "These estimates are not calibrated clinical confidence."
        ),
    }

    # Save the summary.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    # Show the selected recording and window.
    print("Recording:", summary["recording_id"])
    print("Window:", summary["window_id"])

    # Show the prediction and its probability estimate.
    print("Predicted pattern:", prediction)
    print(f"Model probability: {predicted_probability:.2%}")

    # Show where the summary was saved.
    print("Summary saved:", OUTPUT_PATH)
    print("SIMULATED DATA ONLY — not a clinical assessment.")


# Run the program.
if __name__ == "__main__":
    main()