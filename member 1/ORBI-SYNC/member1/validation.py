import json
import requests
import pandas as pd

from pathlib import Path
from io import BytesIO


# ==========================================
# PROJECT PATHS
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIR = PROJECT_ROOT / "member1" / "output"

CONJUNCTION_FILE = OUTPUT_DIR / "conjunction.json"

TRAJECTORY_FILE = OUTPUT_DIR / "trajectories.json"

SOCRATES_FILE = OUTPUT_DIR / "socrates.csv"

REPORT_FILE = OUTPUT_DIR / "validation_report.json"


# Official CelesTrak SOCRATES CSV
SOCRATES_URL = (
    "https://celestrak.org/SOCRATES/sort-minRange.csv"
)

# Comparison tolerance (initial project settings)
TCA_TOLERANCE_HOURS = 6.0


# ==========================================
# LOAD OUR CONJUNCTION DATA
# ==========================================

def load_our_conjunctions():

    with open(CONJUNCTION_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data.get("conjunctions", [])


# ==========================================
# DOWNLOAD SOCRATES DATA
# ==========================================

def download_socrates():

    print("\nDownloading CelesTrak SOCRATES data...")

    response = requests.get(
        SOCRATES_URL,
        timeout=60
    )

    response.raise_for_status()

    # Read CSV directly from downloaded content
    df = pd.read_csv(BytesIO(response.content))

    if df.empty:
        raise ValueError("SOCRATES returned an empty CSV.")

    df.columns = df.columns.str.strip()

    required_columns = [
        "NORAD_CAT_ID_1",
        "NORAD_CAT_ID_2",
        "TCA",
        "TCA_RANGE",
        "TCA_RELATIVE_SPEED"
    ]

    missing = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"SOCRATES CSV missing columns: {missing}"
        )

    df["NORAD_CAT_ID_1"] = (
        df["NORAD_CAT_ID_1"].astype(str).str.strip()
    )

    df["NORAD_CAT_ID_2"] = (
        df["NORAD_CAT_ID_2"].astype(str).str.strip()
    )

    df["TCA"] = pd.to_datetime(
        df["TCA"], utc=True, errors="coerce"
    )

    df["TCA_RANGE"] = pd.to_numeric(
        df["TCA_RANGE"], errors="coerce"
    )

    df["TCA_RELATIVE_SPEED"] = pd.to_numeric(
        df["TCA_RELATIVE_SPEED"], errors="coerce"
    )

    df = df.dropna(
        subset=[
            "NORAD_CAT_ID_1",
            "NORAD_CAT_ID_2",
            "TCA",
            "TCA_RANGE"
        ]
    )

    df.to_csv(SOCRATES_FILE, index=False)

    print("SOCRATES records downloaded:", len(df))
    print("Saved:", SOCRATES_FILE)

    return df


# ==========================================
# NORMALIZE SATELLITE PAIR
# ==========================================

def pair_key(id1, id2):

    return tuple(sorted([str(id1), str(id2)]))


# ==========================================
# VALIDATE OUR CONJUNCTIONS
# ==========================================

def validate_conjunctions(our_data, socrates_data):

    print("\nComparing conjunction records...")

    socrates_data = socrates_data.copy()

    # Group reference events by NORAD pair
    socrates_pairs = {}

    for _, row in socrates_data.iterrows():

        key = pair_key(
            row["NORAD_CAT_ID_1"],
            row["NORAD_CAT_ID_2"]
        )

        socrates_pairs.setdefault(key, []).append(row)

    report = []

    for event in our_data:

        id1 = event["object_1"]["norad_id"]
        id2 = event["object_2"]["norad_id"]

        key = pair_key(id1, id2)

        our_tca = pd.to_datetime(
            event["tca_utc"], utc=True
        )

        our_distance = float(
            event["miss_distance_km"]
        )

        our_speed = float(
            event["relative_velocity_km_s"]
        )

        candidates = socrates_pairs.get(key, [])

        if not candidates:

            report.append({
                "object_1": id1,
                "object_2": id2,
                "our_miss_distance_km": our_distance,
                "status": "PAIR_NOT_FOUND_IN_SOCRATES"
            })

            continue

        # Find the SOCRATES event with closest TCA
        best = min(
            candidates,
            key=lambda row: abs(
                (row["TCA"] - our_tca).total_seconds()
            )
        )

        time_difference = abs(
            (best["TCA"] - our_tca).total_seconds()
        ) / 3600

        distance_difference = abs(
            float(best["TCA_RANGE"]) - our_distance
        )

        speed_difference = abs(
            float(best["TCA_RELATIVE_SPEED"]) - our_speed
        )

        timing_match = (
            time_difference <= TCA_TOLERANCE_HOURS
        )

        report.append({

            "object_1": id1,

            "object_2": id2,

            "our_tca": our_tca.isoformat(),

            "socrates_tca": best["TCA"].isoformat(),

            "our_miss_distance_km": our_distance,

            "socrates_miss_distance_km": float(
                best["TCA_RANGE"]
            ),

            "our_relative_velocity_km_s": our_speed,

            "socrates_relative_velocity_km_s": float(
                best["TCA_RELATIVE_SPEED"]
            ),

            "tca_difference_hours": round(
                time_difference, 4
            ),

            "distance_difference_km": round(
                distance_difference, 6
            ),

            "speed_difference_km_s": round(
                speed_difference, 6
            ),

            "status": (
                "PAIR_AND_TCA_MATCH"
                if timing_match
                else "PAIR_FOUND_TCA_DIFFERS"
            )
        })

    return report


# ==========================================
# BASIC JSON STRUCTURE VALIDATION
# ==========================================

def validate_json_files():

    print("\nChecking JSON files...")

    with open(TRAJECTORY_FILE, "r", encoding="utf-8") as file:
        trajectory = json.load(file)

    with open(CONJUNCTION_FILE, "r", encoding="utf-8") as file:
        conjunction = json.load(file)

    assert "metadata" in trajectory
    assert "timestamps_utc" in trajectory
    assert "trajectories" in trajectory

    assert "metadata" in conjunction
    assert "conjunctions" in conjunction

    assert len(trajectory["timestamps_utc"]) > 0

    for satellite in trajectory["trajectories"]:

        assert "norad_id" in satellite
        assert "positions_km" in satellite
        assert "velocities_km_s" in satellite

        assert (
            len(satellite["positions_km"])
            == len(trajectory["timestamps_utc"])
        )

        assert (
            len(satellite["velocities_km_s"])
            == len(trajectory["timestamps_utc"])
        )

    for event in conjunction["conjunctions"]:

        assert "object_1" in event
        assert "object_2" in event
        assert "tca_utc" in event
        assert "miss_distance_km" in event
        assert "relative_velocity_km_s" in event

    print("Trajectory JSON structure: VALID")
    print("Conjunction JSON structure: VALID")

    return len(trajectory["trajectories"]), len(
        conjunction["conjunctions"]
    )


# ==========================================
# MAIN FUNCTION
# ==========================================

def main():

    print("\n================================")
    print("MEMBER 1 VALIDATION STARTED")
    print("================================")

    satellite_count, conjunction_count = (
        validate_json_files()
    )

    our_data = load_our_conjunctions()

    socrates_data = download_socrates()

    comparison = validate_conjunctions(
        our_data,
        socrates_data
    )

    matched = sum(
        item["status"] == "PAIR_AND_TCA_MATCH"
        for item in comparison
    )

    pair_found = sum(
        item["status"] != "PAIR_NOT_FOUND_IN_SOCRATES"
        for item in comparison
    )

    final_report = {

        "metadata": {

            "our_satellite_count": satellite_count,

            "our_conjunction_count": conjunction_count,

            "socrates_record_count": len(socrates_data),

            "matched_pairs": pair_found,

            "matched_pair_and_tca": matched,

            "tca_tolerance_hours": TCA_TOLERANCE_HOURS
        },

        "comparisons": comparison
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as file:

        json.dump(
            final_report,
            file,
            indent=4
        )

    print("\n================================")
    print("VALIDATION COMPLETED")
    print("================================")

    print("Our satellites:", satellite_count)
    print("Our conjunctions:", conjunction_count)

    print("SOCRATES records:", len(socrates_data))

    print("Matching pairs:", pair_found)

    print("Pair and TCA matches:", matched)

    print("\nValidation report saved at:")
    print(REPORT_FILE)


if __name__ == "__main__":
    main()