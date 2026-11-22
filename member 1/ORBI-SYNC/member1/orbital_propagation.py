import json
import hashlib
import numpy as np

from pathlib import Path
from datetime import datetime, timedelta, timezone

from skyfield.api import EarthSatellite, load


# ==========================================
# PROJECT CONFIGURATION
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "cleaned_tle.txt"

OUTPUT_DIR = PROJECT_ROOT / "member1" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "trajectories.json"

INTERVAL_SECONDS = 60
DURATION_DAYS = 3


# ==========================================
# TLE FILE HASH
# ==========================================

def calculate_tle_hash():

    with open(INPUT_FILE, "rb") as file:
        file_hash = hashlib.sha256(file.read()).hexdigest()

    return file_hash


# ==========================================
# LOAD CLEANED TLE DATA
# ==========================================

def load_tle_data():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Cleaned TLE file not found: {INPUT_FILE}"
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        lines = [
            line.strip()
            for line in file
            if line.strip()
        ]

    satellites = []

    for i in range(0, len(lines) - 2, 3):

        name = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]

        if (
            line1.startswith("1 ")
            and line2.startswith("2 ")
            and len(line1) == 69
            and len(line2) == 69
        ):

            satellites.append({
                "name": name,
                "norad_id": line1[2:7].strip(),
                "line1": line1,
                "line2": line2
            })

    print("TLE records loaded:", len(satellites))

    if not satellites:
        raise ValueError("No valid TLE records available.")

    return satellites


# ==========================================
# GENERATE FUTURE TIMESTAMPS
# ==========================================

def generate_timestamps():

    # IMPORTANT:
    # Remove microseconds so the exact same timestamps
    # are used during propagation and JSON validation.

    start_time = datetime.now(timezone.utc).replace(
        microsecond=0
    )

    total_steps = (
        DURATION_DAYS * 24 * 60 * 60
    ) // INTERVAL_SECONDS

    timestamps = [
        start_time + timedelta(
            seconds=i * INTERVAL_SECONDS
        )
        for i in range(total_steps + 1)
    ]

    return timestamps


# ==========================================
# ORBITAL PROPAGATION
# ==========================================

def propagate_satellites():

    satellites = load_tle_data()

    # Record the exact TLE dataset used.
    tle_hash = calculate_tle_hash()

    print("\nInitializing Skyfield...")

    ts = load.timescale()

    timestamps = generate_timestamps()

    # Convert exact UTC timestamps into Skyfield time.
    skyfield_times = ts.from_datetimes(timestamps)

    print("Prediction timestamps:", len(timestamps))
    print("Starting timestamp:", timestamps[0].isoformat())
    print("Ending timestamp:", timestamps[-1].isoformat())

    all_trajectories = []

    successful = 0
    failed = 0

    # ======================================
    # PROCESS EVERY SATELLITE
    # ======================================

    for index, sat_data in enumerate(satellites, start=1):

        name = sat_data["name"]
        norad_id = sat_data["norad_id"]

        print(
            f"\nProcessing {index}/{len(satellites)}: {name}"
        )

        try:

            satellite = EarthSatellite(
                sat_data["line1"],
                sat_data["line2"],
                name,
                ts
            )

            # Propagate orbit at all timestamps.
            geocentric = satellite.at(skyfield_times)

            # Extract position and velocity.
            positions = geocentric.position.km.T
            velocities = geocentric.velocity.km_per_s.T

            # Convert values into JSON-compatible lists.
            position_data = [
                [round(float(v), 6) for v in row]
                if np.isfinite(row).all()
                else None
                for row in positions
            ]

            velocity_data = [
                [round(float(v), 9) for v in row]
                if np.isfinite(row).all()
                else None
                for row in velocities
            ]

            trajectory = {
                "name": name,
                "norad_id": norad_id,
                "positions_km": position_data,
                "velocities_km_s": velocity_data
            }

            all_trajectories.append(trajectory)

            successful += 1

            print("Propagation successful!")

        except Exception as error:

            failed += 1

            print("Propagation failed:", error)

    # ======================================
    # VERIFY PROPAGATION RESULTS
    # ======================================

    if successful == 0:
        raise RuntimeError(
            "Propagation failed for every satellite."
        )

    # ======================================
    # SAVE TIMESTAMPS
    # ======================================

    # Preserve the exact timestamps used for propagation.
    timestamp_strings = [
        t.isoformat().replace("+00:00", "Z")
        for t in timestamps
    ]

    # ======================================
    # PREPARE OUTPUT JSON
    # ======================================

    output_data = {

        "metadata": {

            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "start_time_utc": timestamp_strings[0],

            "end_time_utc": timestamp_strings[-1],

            "duration_days": DURATION_DAYS,

            "interval_seconds": INTERVAL_SECONDS,

            "coordinate_frame": "GCRS",

            "position_unit": "km",

            "velocity_unit": "km/s",

            "total_satellites": successful,

            "failed_satellites": failed,

            "tle_sha256": tle_hash

        },

        "timestamps_utc": timestamp_strings,

        "trajectories": all_trajectories
    }

    # ======================================
    # SAVE TRAJECTORY JSON
    # ======================================

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:

        json.dump(
            output_data,
            file,
            separators=(",", ":")
        )

    # ======================================
    # FINAL SUMMARY
    # ======================================

    print("\n================================")
    print("ORBITAL PROPAGATION COMPLETED")
    print("================================")

    print("Total input satellites:", len(satellites))
    print("Successful:", successful)
    print("Failed:", failed)

    print("Duration:", DURATION_DAYS, "days")
    print("Interval:", INTERVAL_SECONDS, "seconds")

    print("Timestamps:", len(timestamps))

    print("TLE SHA-256:", tle_hash)

    print("\nOutput saved at:")
    print(OUTPUT_FILE)


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    propagate_satellites()