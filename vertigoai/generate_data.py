# create synthetic movement data for our demo

# Path helps us find folders and save files.
from pathlib import Path

# NumPy helps us create numbers and random changes.
import numpy as np

# Pandas puts our data into a table.
import pandas as pd


# Find the main project folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Choose where to save the data.
OUTPUT_PATH = PROJECT_ROOT / "data" / "synthetic_motion.csv"

# Take 20 measurements every second.
SAMPLE_RATE = 20

# Each recording lasts 30 seconds.
RECORDING_SECONDS = 30

# Create 30 recordings for each pattern.
RECORDINGS_PER_PATTERN = 30

# These are fake movement labels, not medical labels.
PATTERNS = ("STEADY", "VARIABLE", "TRANSITION")


def generate_recording(rng, pattern, recording_id):
    # Work out how many measurements we need.
    sample_count = SAMPLE_RATE * RECORDING_SECONDS

    # Create the time for each measurement.
    time = np.arange(sample_count) / SAMPLE_RATE

    # Pick how quickly the movement repeats.
    frequency = rng.uniform(0.3, 0.7)

    # Pick where the movement starts in its cycle.
    phase = rng.uniform(0, 2 * np.pi)

    # Create a smooth movement that goes back and forth.
    wave = np.sin(2 * np.pi * frequency * time + phase)

    if pattern == "STEADY":
        # Choose a small movement size.
        amplitude = rng.uniform(0.04, 0.10)

        # Keep the movement size the same over time.
        envelope = np.full(sample_count, amplitude)

        # Add a small amount of random variation.
        noise_scale = 0.025

    elif pattern == "VARIABLE":
        # Choose a larger movement size.
        amplitude = rng.uniform(0.20, 0.40)

        # Make the movement size rise and fall over time.
        envelope = amplitude * (
            1 + 0.4 * np.sin(2 * np.pi * 0.15 * time)
        )

        # Add more random variation.
        noise_scale = 0.08

    else:
        # Choose the size of the movement bursts.
        amplitude = rng.uniform(0.18, 0.32)

        # Create short bursts with quieter gaps between them.
        envelope = amplitude * (
            0.15 + 0.85 * np.sin(2 * np.pi * 0.25 * time) ** 8
        )

        # Add some random variation.
        noise_scale = 0.04

    # Combine the movement size with the back-and-forth pattern.
    motion = envelope * wave

    def noise(scale):
        # Create random changes to add to the measurements.
        return rng.normal(0, scale, sample_count)

    # Put all the measurements into a table.
    return pd.DataFrame(
        {
            # Give every row the ID of its recording.
            "recording_id": recording_id,

            # Store the time in seconds.
            "timestamp_s": time,

            # Create fake acceleration values in three directions.
            # Acceleration is measured in meters per second squared.
            "accel_x_m_s2": motion + noise(noise_scale),

            "accel_y_m_s2": (
                0.7
                * envelope
                * np.cos(2 * np.pi * frequency * time + phase)
                + noise(noise_scale)
            ),

            # Add a simple gravity value to the vertical direction.
            "accel_z_m_s2": (
                9.81 + 0.3 * motion + noise(noise_scale)
            ),

            # Create fake turning speeds in three directions.
            # Turning speed is measured in degrees per second.
            "gyro_x_deg_s": 40 * motion + noise(1.0),
            "gyro_y_deg_s": 25 * motion + noise(1.0),
            "gyro_z_deg_s": 15 * motion + noise(1.0),

            # Store the movement pattern for model training later.
            "pattern_label": pattern,

            # Mark every row as fake data.
            "simulated": True,
        }
    )


def main():
    # Use the same starting number to recreate the same data.
    rng = np.random.default_rng(42)

    # Start an empty list to hold our recordings.
    recordings = []

    # Go through each of the three movement patterns.
    for pattern in PATTERNS:

        # Create 30 separate recordings for this pattern.
        for index in range(RECORDINGS_PER_PATTERN):

            # Give the recording a name, such as steady_000.
            recording_id = f"{pattern.lower()}_{index:03d}"

            # Create the recording.
            recording = generate_recording(
                rng,
                pattern,
                recording_id,
            )

            # Add it to our list.
            recordings.append(recording)

    # Join all the recordings into one table.
    dataset = pd.concat(recordings, ignore_index=True)

    # Create the data folder if it does not exist.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save the table without an extra row-number column.
    dataset.to_csv(OUTPUT_PATH, index=False)

    # Show where the file was saved.
    print(f"Saved: {OUTPUT_PATH}")

    # Show the total number of measurements.
    print(f"Rows: {len(dataset):,}")

    # Show how many separate recordings we created.
    print(
        "Independent recordings:",
        dataset["recording_id"].nunique(),
    )

    # Remind us that this data is only for the demo.
    print("SYNTHETIC DATA ONLY — labels are not clinical assessments.")


# Run main when we run this file.
if __name__ == "__main__":
    main()