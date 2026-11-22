"""
ORBI-SYNC - MEMBER 1
Optimized Adaptive Satellite Conjunction Detection

Run from project root:
    python member1/collision_detection.py

Input:
    data/processed/cleaned_tle.txt
    member1/output/trajectories.json

Output:
    member1/output/conjunction.json
"""

import json
import hashlib
import sys

from pathlib import Path
from datetime import datetime, timedelta, timezone

import numpy as np
from scipy.spatial import cKDTree
from scipy.optimize import minimize_scalar
from skyfield.api import EarthSatellite, load


# ============================================================
# CONFIGURATION
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

TRAJECTORY_FILE = SCRIPT_DIR / "output" / "trajectories.json"
TLE_FILE = PROJECT_ROOT / "data" / "processed" / "cleaned_tle.txt"

OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "conjunction.json"

SCREENING_DISTANCE_KM = 1000.0
CLOSE_APPROACH_THRESHOLD_KM = 10.0

REFINEMENT_TOLERANCE_SECONDS = 0.001

PROGRESS_INTERVAL = 500
REFINEMENT_PROGRESS_INTERVAL = 100


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalize_id(value):

    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value


def parse_timestamp(value):

    value = str(value).strip()

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    result = datetime.fromisoformat(value)

    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)

    return result.astimezone(timezone.utc)


def calculate_sha256(path):

    digest = hashlib.sha256()

    with open(path, "rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def fail(message):

    print("\nERROR:", message)
    sys.exit(1)


# ============================================================
# LOAD TRAJECTORIES
# ============================================================

def load_trajectories():

    if not TRAJECTORY_FILE.exists():
        fail("trajectories.json not found.")

    with open(
        TRAJECTORY_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    required = {
        "metadata",
        "timestamps_utc",
        "trajectories"
    }

    if not required.issubset(data):
        fail("Invalid trajectories.json structure.")

    metadata = data["metadata"]

    timestamps = [
        parse_timestamp(t)
        for t in data["timestamps_utc"]
    ]

    trajectories = data["trajectories"]

    if len(timestamps) < 3:
        fail("Insufficient timestamps.")

    if not trajectories:
        fail("No satellite trajectories found.")

    if any(
        timestamps[i] >= timestamps[i + 1]
        for i in range(len(timestamps) - 1)
    ):
        fail("Timestamps are not strictly increasing.")

    for satellite in trajectories:

        satellite["norad_id"] = normalize_id(
            satellite["norad_id"]
        )

        satellite["_positions"] = np.asarray(
            satellite["positions_km"],
            dtype=float
        )

        satellite["_velocities"] = np.asarray(
            satellite["velocities_km_s"],
            dtype=float
        )

        expected_shape = (len(timestamps), 3)

        if satellite["_positions"].shape != expected_shape:
            fail(
                f"Invalid position array for "
                f"{satellite['norad_id']}"
            )

        if satellite["_velocities"].shape != expected_shape:
            fail(
                f"Invalid velocity array for "
                f"{satellite['norad_id']}"
            )

        if not np.all(
            np.isfinite(satellite["_positions"])
        ):
            fail(
                f"Non-finite positions for "
                f"{satellite['norad_id']}"
            )

        if not np.all(
            np.isfinite(satellite["_velocities"])
        ):
            fail(
                f"Non-finite velocities for "
                f"{satellite['norad_id']}"
            )

    ids = [
        item["norad_id"]
        for item in trajectories
    ]

    if len(ids) != len(set(ids)):
        fail("Duplicate satellite NORAD IDs found.")

    print("Trajectory data loaded successfully.")

    return metadata, timestamps, trajectories


# ============================================================
# LOAD TLE DATA
# ============================================================

def load_tle_satellites(timescale):

    if not TLE_FILE.exists():
        fail("cleaned_tle.txt not found.")

    lines = [
        line.strip()
        for line in TLE_FILE.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    if len(lines) % 3 != 0:
        fail("Invalid TLE file: incomplete satellite records.")

    satellites = {}

    for index in range(0, len(lines), 3):

        name = lines[index]
        line1 = lines[index + 1]
        line2 = lines[index + 2]

        if (
            not line1.startswith("1 ")
            or not line2.startswith("2 ")
        ):
            fail(f"Invalid TLE format near {name}.")

        norad_id = normalize_id(line1[2:7])

        satellite = EarthSatellite(
            line1,
            line2,
            name,
            timescale
        )

        satellites[norad_id] = {
            "name": name,
            "satellite": satellite
        }

    print("TLE records loaded:", len(satellites))

    return satellites


# ============================================================
# VERIFY TLE CONSISTENCY
# ============================================================

def verify_tle_hash(metadata):

    stored_hash = metadata.get("tle_sha256")

    if not stored_hash:

        fail(
            "No TLE hash found in trajectory metadata. "
            "Regenerate trajectories using the updated "
            "orbital_propagation.py."
        )

    current_hash = calculate_sha256(TLE_FILE)

    if stored_hash.lower() != current_hash.lower():

        fail(
            "TLE hash mismatch. Regenerate trajectories.json "
            "using the current cleaned_tle.txt."
        )

    print("TLE SHA-256 CHECK: PASSED")


# ============================================================
# PIPELINE DIAGNOSTICS
# ============================================================

def diagnose_pipeline(
    timestamps,
    trajectories,
    tle_satellites,
    timescale
):

    print("\n========== PIPELINE DIAGNOSTICS ==========\n")

    intervals = [
        (
            timestamps[i + 1] - timestamps[i]
        ).total_seconds()

        for i in range(len(timestamps) - 1)
    ]

    print("1. TIMESTAMP CHECK")

    print("Minimum interval:", min(intervals), "seconds")
    print("Maximum interval:", max(intervals), "seconds")
    print("Average interval:", np.mean(intervals), "seconds")

    print("First timestamp:", timestamps[0].isoformat())
    print("Last timestamp:", timestamps[-1].isoformat())

    trajectory_ids = {
        item["norad_id"]
        for item in trajectories
    }

    tle_ids = set(tle_satellites.keys())

    common_ids = trajectory_ids.intersection(tle_ids)
    missing_ids = trajectory_ids.difference(tle_ids)

    print("\n2. SATELLITE ID CHECK")

    print("Trajectory satellites:", len(trajectory_ids))
    print("TLE satellites:", len(tle_ids))
    print("Common satellite IDs:", len(common_ids))
    print("Missing TLE IDs:", len(missing_ids))

    if missing_ids:
        fail("Some trajectory satellites have no matching TLE.")

    print("\n3. POSITION CONSISTENCY CHECK")

    skyfield_time = timescale.from_datetime(
        timestamps[0]
    )

    differences = []

    for item in trajectories[:5]:

        norad_id = item["norad_id"]

        satellite = tle_satellites[norad_id]["satellite"]

        calculated = np.asarray(
            satellite.at(skyfield_time).position.km
        )

        stored = item["_positions"][0]

        difference = np.linalg.norm(
            calculated - stored
        )

        differences.append(difference)

        print(
            f"NORAD: {norad_id} | "
            f"Position difference: {difference:.6g} km"
        )

    print(
        "Mean difference:",
        f"{np.mean(differences):.6g} km"
    )

    print(
        "Maximum difference:",
        f"{np.max(differences):.6g} km"
    )

    print("\n========== DIAGNOSTICS COMPLETED ==========\n")


# ============================================================
# FAST COLLISION SCREENING
# ============================================================

def screen_close_pairs(timestamps, trajectories):

    satellite_ids = [
        item["norad_id"]
        for item in trajectories
    ]

    position_arrays = [
        item["_positions"]
        for item in trajectories
    ]

    samples_by_pair = {}

    total_steps = len(timestamps)

    print("Starting fast collision screening...")

    for step in range(total_steps):

        positions = np.stack(
            [array[step] for array in position_arrays]
        )

        tree = cKDTree(positions)

        pairs = tree.query_pairs(
            r=SCREENING_DISTANCE_KM,
            output_type="ndarray"
        )

        if len(pairs) > 0:

            distances = np.linalg.norm(
                positions[pairs[:, 0]]
                - positions[pairs[:, 1]],
                axis=1
            )

            for pair_indices, distance in zip(
                pairs,
                distances
            ):

                first_id = satellite_ids[int(pair_indices[0])]
                second_id = satellite_ids[int(pair_indices[1])]

                pair = tuple(
                    sorted((first_id, second_id))
                )

                samples_by_pair.setdefault(
                    pair, []
                ).append(
                    (step, float(distance))
                )

        if (step + 1) % PROGRESS_INTERVAL == 0:

            print(
                f"Screened {step + 1}/"
                f"{total_steps} timestamps",
                flush=True
            )

    print(
        "\nCandidate pairs found:",
        len(samples_by_pair)
    )

    return samples_by_pair


# ============================================================
# IDENTIFY SEPARATE ENCOUNTER EVENTS
# ============================================================

def identify_candidate_events(
    samples_by_pair,
    total_steps
):
    events = []

    for pair, samples in samples_by_pair.items():

        samples.sort(key=lambda x: x[0])

        runs = []
        current_run = []

        # Group consecutive timestamps into continuous runs.
        for sample in samples:

            if (
                current_run
                and sample[0] != current_run[-1][0] + 1
            ):
                runs.append(current_run)
                current_run = []

            current_run.append(sample)

        if current_run:
            runs.append(current_run)

        # Keep only the minimum-distance sample per run.
        for run in runs:

            best_sample = min(
                run,
                key=lambda sample: sample[1]
            )

            events.append({
                "pair": pair,
                "best_step": best_sample[0],
                "sampled_distance_km": float(
                    best_sample[1]
                )
            })

    events.sort(
        key=lambda event: (
            event["pair"],
            event["best_step"]
        )
    )

    return events


# ============================================================
# EXACT SGP4 SEPARATION
# ============================================================

def separation_at_seconds(
    elapsed_seconds,
    start_time,
    satellite_a,
    satellite_b,
    timescale
):

    instant = start_time + timedelta(
        seconds=float(elapsed_seconds)
    )

    skyfield_time = timescale.from_datetime(
        instant
    )

    position_a = np.asarray(
        satellite_a.at(skyfield_time).position.km
    )

    position_b = np.asarray(
        satellite_b.at(skyfield_time).position.km
    )

    return float(
        np.linalg.norm(position_a - position_b)
    )


# ============================================================
# OPTIMIZED CLOSE APPROACH REFINEMENT
# ============================================================

def refine_close_approach(
    event,
    timestamps,
    tle_satellites,
    timescale
):

    first_id, second_id = event["pair"]

    satellite_a = tle_satellites[first_id]["satellite"]
    satellite_b = tle_satellites[second_id]["satellite"]

    start_time = timestamps[0]

    best_step = event["best_step"]

    center_elapsed = (
        timestamps[best_step] - start_time
    ).total_seconds()

    total_duration = (
        timestamps[-1] - start_time
    ).total_seconds()

    left_step = max(0, best_step - 1)
    right_step = min(
        len(timestamps) - 1,
        best_step + 1
    )

    left = (
        timestamps[left_step] - start_time
    ).total_seconds()

    right = (
        timestamps[right_step] - start_time
    ).total_seconds()

    boundary_warning = (
        best_step == 0
        or best_step == len(timestamps) - 1
    )

    def distance(elapsed):

        return separation_at_seconds(
            elapsed,
            start_time,
            satellite_a,
            satellite_b,
            timescale
        )

    # Evaluate the center and both endpoints.
    candidates = [
        (left, distance(left)),
        (center_elapsed, distance(center_elapsed)),
        (right, distance(right))
    ]

    if right > left:

        result = minimize_scalar(
            distance,
            bounds=(left, right),
            method="bounded",
            options={
                "xatol": REFINEMENT_TOLERANCE_SECONDS
            }
        )

        if result.success and np.isfinite(result.fun):

            candidates.append(
                (float(result.x), float(result.fun))
            )

            method = "neighbor_bracket_bounded_minimization"

        else:

            method = "sampled_bracket_fallback"
            boundary_warning = True

    else:

        method = "sampled_point_fallback"
        boundary_warning = True

    best_elapsed, best_distance = min(
        candidates,
        key=lambda item: item[1]
    )

    if (
        best_elapsed <= 0.1
        or total_duration - best_elapsed <= 0.1
    ):

        boundary_warning = True

    return {

        "tca": start_time + timedelta(
            seconds=best_elapsed
        ),

        "miss_distance_km": float(best_distance),

        "boundary_warning": boundary_warning,

        "refinement_window_seconds": float(
            right - left
        ),

        "refinement_method": method
    }


# ============================================================
# SAVE CONJUNCTION RESULTS
# ============================================================

def detect_conjunctions(
    timestamps,
    trajectories,
    tle_satellites,
    timescale,
    metadata
):

    samples_by_pair = screen_close_pairs(
        timestamps,
        trajectories
    )

    candidate_events = identify_candidate_events(
        samples_by_pair,
        len(timestamps)
    )

    total_events = len(candidate_events)

    print(
        "\nCandidate encounter events:",
        total_events
    )

    print("\nStarting optimized refinement...\n")

    names = {
        item["norad_id"]: item["name"]
        for item in trajectories
    }

    conjunctions = []

    boundary_warning_count = 0

    for event_index, event in enumerate(
        candidate_events,
        start=1
    ):

        first_id, second_id = event["pair"]

        refined = refine_close_approach(
            event,
            timestamps,
            tle_satellites,
            timescale
        )

        if refined["boundary_warning"]:

            boundary_warning_count += 1

            print(
                f"WARNING: Refined minimum for "
                f"{first_id}-{second_id} may be near "
                f"a search-window or data boundary."
            )

        miss_distance = refined["miss_distance_km"]

        if miss_distance <= CLOSE_APPROACH_THRESHOLD_KM:

            name_a = names.get(
                first_id,
                tle_satellites[first_id]["name"]
            )

            name_b = names.get(
                second_id,
                tle_satellites[second_id]["name"]
            )

            record = {

                "norad_id_1": first_id,

                "norad_id_2": second_id,

                "satellite_1": name_a,

                "satellite_2": name_b,

                "tca_utc": (
                    refined["tca"]
                    .isoformat()
                    .replace("+00:00", "Z")
                ),

                "miss_distance_km": round(
                    float(miss_distance),
                    6
                ),

                "sampled_distance_km": round(
                    float(event["sampled_distance_km"]),
                    6
                ),

                "refinement_window_seconds": (
                    refined["refinement_window_seconds"]
                ),

                "refinement_method": (
                    refined["refinement_method"]
                ),

                "refinement_boundary_warning": (
                    refined["boundary_warning"]
                )
            }

            conjunctions.append(record)

            print(
                f"Close approach: "
                f"{first_id}-{second_id} | "
                f"{miss_distance:.6f} km"
            )

        if (
            event_index % REFINEMENT_PROGRESS_INTERVAL == 0
            or event_index == total_events
        ):

            print(
                f"Refined {event_index}/{total_events} events",
                flush=True
            )

    conjunctions.sort(
        key=lambda item: item["miss_distance_km"]
    )

    output = {

        "metadata": {

            "generated_at_utc": (
                datetime.now(timezone.utc).isoformat()
            ),

            "screening_distance_km": (
                SCREENING_DISTANCE_KM
            ),

            "close_approach_threshold_km": (
                CLOSE_APPROACH_THRESHOLD_KM
            ),

            "total_satellites": len(trajectories),

            "total_timestamps": len(timestamps),

            "candidate_pairs": len(samples_by_pair),

            "candidate_encounter_events": total_events,

            "close_approaches": len(conjunctions),

            "boundary_warning_events": boundary_warning_count,

            "tle_sha256": metadata.get("tle_sha256"),

            "refinement_method": (
                "continuous-run local minima, "
                "neighboring timestamp bracket, "
                "bounded scalar minimization"
            ),

            "note": (
                "TLE/SGP4 screening results only. "
                "Collision probability is not calculated "
                "because orbital covariance data are not included."
            )
        },

        "conjunctions": conjunctions
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=4
        )

    print("\n================================")
    print("COLLISION DETECTION COMPLETED")
    print("================================")

    print("Candidate pairs:", len(samples_by_pair))
    print("Candidate encounter events:", total_events)
    print("Close approaches:", len(conjunctions))
    print("Boundary warnings:", boundary_warning_count)

    print("\nSaved at:")
    print(OUTPUT_FILE)


# ============================================================
# MAIN
# ============================================================

def main():

    print("ORBI-SYNC - MEMBER 1")
    print("OPTIMIZED COLLISION DETECTION")
    print("-------------------------------")

    metadata, timestamps, trajectories = (
        load_trajectories()
    )

    timescale = load.timescale()

    tle_satellites = load_tle_satellites(
        timescale
    )

    verify_tle_hash(metadata)

    diagnose_pipeline(
        timestamps,
        trajectories,
        tle_satellites,
        timescale
    )

    detect_conjunctions(
        timestamps,
        trajectories,
        tle_satellites,
        timescale,
        metadata
    )


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:

        print("\nProcess interrupted.")

        sys.exit(130)

    except Exception as error:

        print("\nUNEXPECTED ERROR:", error)

        raise