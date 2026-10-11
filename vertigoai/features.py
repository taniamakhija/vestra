# Turn motion recordings into features for model training.

from pathlib import Path

import numpy as np
import pandas as pd


# Find our project folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Choose the input and output files.
INPUT_PATH = PROJECT_ROOT / "data" / "synthetic_motion.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "motion_features.csv"

# Each window contains five seconds of data.
WINDOW_SECONDS = 5
SAMPLE_RATE = 20
SAMPLES_PER_WINDOW = WINDOW_SECONDS * SAMPLE_RATE

# List the acceleration columns.
ACCEL_COLUMNS = [
    "accel_x_m_s2",
    "accel_y_m_s2",
    "accel_z_m_s2",
]

# List the turning-speed columns.
GYRO_COLUMNS = [
    "gyro_x_deg_s",
    "gyro_y_deg_s",
    "gyro_z_deg_s",
]


def extract_features(window):
    # Read the three acceleration values for each measurement.
    acceleration = window[ACCEL_COLUMNS].to_numpy()

    # Read the three turning-speed values.
    turning = window[GYRO_COLUMNS].to_numpy()

    # Combine the three directions into one size.
    # Acceleration still includes gravity.
    acceleration_size = np.linalg.norm(acceleration, axis=1)
    turning_size = np.linalg.norm(turning, axis=1)

    # Find how much acceleration changes between measurements.
    acceleration_changes = np.linalg.norm(
        np.diff(acceleration, axis=0),
        axis=1,
    )

    # Find how much turning speed changes between measurements.
    turning_changes = np.linalg.norm(
        np.diff(turning, axis=0),
        axis=1,
    )

    # Store the numbers that describe this window.
    features = {
        "acceleration_mean": acceleration_size.mean(),
        "acceleration_std": acceleration_size.std(),
        "acceleration_max": acceleration_size.max(),
        "turning_mean": turning_size.mean(),
        "turning_std": turning_size.std(),
        "turning_max": turning_size.max(),
        "acceleration_change_mean": acceleration_changes.mean(),
        "turning_change_mean": turning_changes.mean(),
    }

    # Also measure variation in each separate direction.
    for column in ACCEL_COLUMNS + GYRO_COLUMNS:
        features[f"{column}_std"] = window[column].std(ddof=0)

    return features


def main():
    # Read the saved sensor data.
    data = pd.read_csv(INPUT_PATH)

    # Start a list for our five-second windows.
    feature_rows = []

    # Handle each recording separately.
    # This prevents windows from joining different recordings.
    for recording_id, recording in data.groupby("recording_id"):
        recording = recording.sort_values("timestamp_s").copy()

        # Check that sensor values are valid numbers.
        sensor_values = recording[
            ACCEL_COLUMNS + GYRO_COLUMNS
        ].to_numpy(dtype=float)

        if not np.isfinite(sensor_values).all():
            raise ValueError(f"Invalid sensor values: {recording_id}")

        # Read and check the times.
        times = recording["timestamp_s"].to_numpy(dtype=float)

        if not np.isfinite(times).all():
            raise ValueError(f"Invalid timestamps: {recording_id}")

        # This first version expects evenly spaced measurements.
        if not np.allclose(
            np.diff(times),
            1 / SAMPLE_RATE,
            atol=0.000001,
            rtol=0,
        ):
            raise ValueError(f"Unexpected sample spacing: {recording_id}")

        # Start counting time from the beginning of this recording.
        elapsed = times - times[0]

        # Assign each measurement to a five-second window.
        recording["window_id"] = np.floor(
            (elapsed + 0.000000001) / WINDOW_SECONDS
        ).astype(int)

        # Process one window at a time.
        for window_id, window in recording.groupby("window_id"):
            # Skip an incomplete window at the end.
            if len(window) != SAMPLES_PER_WINDOW:
                continue

            # Each training window needs one movement label.
            if (
                window["pattern_label"].isna().any()
                or window["pattern_label"].nunique() != 1
            ):
                raise ValueError("A window must have one movement label.")

            # Calculate the movement features.
            features = extract_features(window)

            # Keep IDs so we can split recordings safely later.
            features["recording_id"] = recording_id
            features["window_id"] = int(window_id)

            # Keep the label for training.
            features["pattern_label"] = window["pattern_label"].iloc[0]

            # Keep the synthetic-data marker.
            features["simulated"] = bool(window["simulated"].all())

            # Add this window to our list.
            feature_rows.append(features)

    # Check that we found complete windows.
    if not feature_rows:
        raise ValueError("No complete five-second windows were found.")

    # Turn the feature rows into a table.
    feature_table = pd.DataFrame(feature_rows)

    # Save the table for the training step.
    feature_table.to_csv(OUTPUT_PATH, index=False)

    # Show what we created.
    print(f"Saved: {OUTPUT_PATH}")
    print(f"Five-second windows: {len(feature_table)}")
    print("Windows per pattern:")
    print(feature_table["pattern_label"].value_counts().to_string())
    print("SYNTHETIC DATA ONLY — these are not medical predictions.")


# Run the program.
if __name__ == "__main__":
    main()