# Train a model to recognize simulated movement patterns.

import json
from pathlib import Path

# Joblib saves the trained model.
import joblib

# Pandas reads and organizes our data.
import pandas as pd

# Random Forest learns patterns using decision trees.
from sklearn.ensemble import RandomForestClassifier

# These tools measure how well the model performs.
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

# This tool separates training data from test data.
from sklearn.model_selection import train_test_split


# Find the main project folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Choose where to read the movement features.
INPUT_PATH = PROJECT_ROOT / "data" / "motion_features.csv"

# Choose where to save the model and results.
RESULTS_FOLDER = PROJECT_ROOT / "results"
MODEL_PATH = RESULTS_FOLDER / "motion_model.joblib"
REPORT_PATH = RESULTS_FOLDER / "motion_evaluation.json"

# Keep the movement labels in a fixed order.
LABELS = ["STEADY", "VARIABLE", "TRANSITION"]

# These columns identify the data.
# They must not be used to predict the movement pattern.
EXCLUDED_COLUMNS = [
    "recording_id",
    "window_id",
    "pattern_label",
    "simulated",
]


def main():
    # Read the features we created earlier.
    data = pd.read_csv(INPUT_PATH)

    # Count the labels in each recording.
    labels_per_recording = data.groupby(
        "recording_id"
    )["pattern_label"].nunique()

    # Each recording should have only one movement label.
    if not labels_per_recording.eq(1).all():
        raise ValueError("Each recording must have one pattern label.")

    # Create a table with one row for each recording.
    recordings = data[
        ["recording_id", "pattern_label"]
    ].drop_duplicates()

    # Put 80% of recordings in training and 20% in testing.
    # Keep all three patterns in both groups.
    train_ids, test_ids = train_test_split(
        recordings["recording_id"],
        test_size=0.20,
        random_state=42,
        stratify=recordings["pattern_label"],
    )

    # Get all windows from the training recordings.
    train_data = data[
        data["recording_id"].isin(train_ids)
    ].copy()

    # Get all windows from the test recordings.
    test_data = data[
        data["recording_id"].isin(test_ids)
    ].copy()

    # A recording must not appear in both groups.
    if set(train_ids) & set(test_ids):
        raise ValueError("Training and testing recordings overlap.")

    # Choose the movement features used by the model.
    feature_columns = [
        column
        for column in data.columns
        if column not in EXCLUDED_COLUMNS
    ]

    # X contains the movement measurements.
    X_train = train_data[feature_columns]
    X_test = test_data[feature_columns]

    # y contains the correct movement labels.
    y_train = train_data["pattern_label"]
    y_test = test_data["pattern_label"]

    # Create a Random Forest with 100 decision trees.
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        n_jobs=-1,
    )

    # Train the model using the training windows.
    model.fit(X_train, y_train)

    # Predict labels for windows the model has not trained on.
    predictions = model.predict(X_test)

    # Calculate the fraction of correct predictions.
    accuracy = accuracy_score(y_test, predictions)

    # Calculate precision, recall, and F1 for each pattern.
    metrics = classification_report(
        y_test,
        predictions,
        labels=LABELS,
        output_dict=True,
        zero_division=0,
    )

    # Count correct predictions and mistakes.
    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=LABELS,
    )

    # Create the results folder if it does not exist.
    RESULTS_FOLDER.mkdir(parents=True, exist_ok=True)

    # Save the model and the order of its input features.
    joblib.dump(
        {
            "model": model,
            "feature_columns": feature_columns,
            "simulated_training_data": True,
        },
        MODEL_PATH,
    )

    # Collect the results and the recording IDs.
    report = {
        "simulated_data": True,
        "accuracy": accuracy,
        "classification_report": metrics,
        "confusion_matrix": matrix.tolist(),
        "confusion_matrix_labels": LABELS,
        "train_recording_ids": sorted(train_ids.tolist()),
        "test_recording_ids": sorted(test_ids.tolist()),
        "training_windows": len(train_data),
        "test_windows": len(test_data),
        "note": (
            "Simulated pattern recognition only; "
            "not clinical validation."
        ),
    }

    # Save the results as a JSON file.
    REPORT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    # Show how much data was used.
    print(f"Training recordings: {len(train_ids)}")
    print(f"Test recordings: {len(test_ids)}")
    print(f"Training windows: {len(train_data)}")
    print(f"Test windows: {len(test_data)}")

    # Show the percentage of correct predictions.
    print(f"Accuracy: {accuracy:.2%}")

    # Show precision, recall, and F1 for each pattern.
    print("\nResults for each pattern:")
    print(
        classification_report(
            y_test,
            predictions,
            labels=LABELS,
            zero_division=0,
        )
    )

    # Rows show actual labels.
    # Columns show the model's predicted labels.
    print("Confusion matrix: rows = actual, columns = predicted")
    print(
        pd.DataFrame(
            matrix,
            index=LABELS,
            columns=LABELS,
        ).to_string()
    )

    # Show where the model and results were saved.
    print(f"\nModel saved: {MODEL_PATH}")
    print(f"Evaluation saved: {REPORT_PATH}")

    # These results only describe our simulated dataset.
    print("SIMULATED RESULTS ONLY — not medical effectiveness.")


# Run the program.
if __name__ == "__main__":
    main()
