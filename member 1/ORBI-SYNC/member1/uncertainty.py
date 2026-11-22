import json
import pandas as pd
import numpy as np

from pathlib import Path
from datetime import datetime, timezone


# ==========================================
# PROJECT CONFIGURATION
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

METADATA_FILE = (
    PROJECT_ROOT / "data" / "processed" / "tle_metadata.csv"
)

CONJUNCTION_FILE = (
    PROJECT_ROOT / "member1" / "output" / "conjunction.json"
)

OUTPUT_DIR = PROJECT_ROOT / "member1" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

UNCERTAINTY_FILE = OUTPUT_DIR / "uncertainty.json"


# ==========================================
# UNCERTAINTY MODEL ASSUMPTIONS
# ==========================================

BASE_UNCERTAINTY_KM = 0.1

GROWTH_RATE_KM_PER_HOUR = 0.0041667


# ==========================================
# LOAD TLE METADATA
# ==========================================

def load_metadata():

    if not METADATA_FILE.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {METADATA_FILE}"
        )

    df = pd.read_csv(
        METADATA_FILE,
        dtype={"norad_id": str}
    )

    if df.empty:
        raise ValueError("TLE metadata is empty.")

    return df


# ==========================================
# CALCULATE UNCERTAINTY
# ==========================================

def calculate_uncertainty(age_hours):

    uncertainty = (
        BASE_UNCERTAINTY_KM
        + GROWTH_RATE_KM_PER_HOUR * age_hours
    )

    return round(float(uncertainty), 6)


# ==========================================
# GENERATE SATELLITE UNCERTAINTY
# ==========================================

def generate_uncertainty():

    df = load_metadata()

    satellite_uncertainties = {}

    for _, row in df.iterrows():

        norad_id = str(row["norad_id"]).strip()

        age_hours = float(row["tle_age_hours"])

        if not np.isfinite(age_hours) or age_hours < 0:
            continue

        uncertainty = calculate_uncertainty(
            age_hours
        )

        satellite_uncertainties[norad_id] = {

            "name": row["name"],

            "norad_id": norad_id,

            "tle_age_hours": age_hours,

            "uncertainty_scale_km": uncertainty
        }

    return satellite_uncertainties


# ==========================================
# ADD UNCERTAINTY TO CONJUNCTIONS
# ==========================================

def update_conjunctions(satellite_uncertainties):

    if not CONJUNCTION_FILE.exists():
        raise FileNotFoundError(
            f"Conjunction file not found: {CONJUNCTION_FILE}"
        )

    with open(CONJUNCTION_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    updated_count = 0

    for event in data.get("conjunctions", []):

        id1 = str(
            event["object_1"]["norad_id"]
        ).strip()

        id2 = str(
            event["object_2"]["norad_id"]
        ).strip()

        if (
            id1 not in satellite_uncertainties
            or id2 not in satellite_uncertainties
        ):
            continue

        uncertainty1 = satellite_uncertainties[id1][
            "uncertainty_scale_km"
        ]

        uncertainty2 = satellite_uncertainties[id2][
            "uncertainty_scale_km"
        ]

        # Combined uncertainty using RSS
        relative_uncertainty = float(
            np.sqrt(
                uncertainty1 ** 2
                + uncertainty2 ** 2
            )
        )

        event["uncertainty"] = {

            "object_1_uncertainty_km": uncertainty1,

            "object_2_uncertainty_km": uncertainty2,

            "relative_uncertainty_km": round(
                relative_uncertainty, 6
            ),

            "method": "RSS heuristic"
        }

        updated_count += 1

    data["metadata"]["uncertainty_model"] = (
        "Linear TLE age-based heuristic"
    )

    data["metadata"]["uncertainty_updated_at"] = (
        datetime.now(timezone.utc).isoformat()
    )

    with open(CONJUNCTION_FILE, "w", encoding="utf-8") as file:

        json.dump(data, file, indent=4)

    return updated_count


# ==========================================
# MAIN FUNCTION
# ==========================================

def main():

    print("\n================================")
    print("UNCERTAINTY ESTIMATION STARTED")
    print("================================")

    uncertainties = generate_uncertainty()

    updated_count = update_conjunctions(
        uncertainties
    )

    output_data = {

        "metadata": {

            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "model": "Linear TLE age-based heuristic",

            "base_uncertainty_km": BASE_UNCERTAINTY_KM,

            "growth_rate_km_per_hour": (
                GROWTH_RATE_KM_PER_HOUR
            ),

            "total_satellites": len(uncertainties),

            "updated_conjunctions": updated_count
        },

        "satellite_uncertainties": list(
            uncertainties.values()
        )
    }

    with open(UNCERTAINTY_FILE, "w", encoding="utf-8") as file:

        json.dump(
            output_data,
            file,
            indent=4
        )

    print("\n================================")
    print("UNCERTAINTY ESTIMATION COMPLETED")
    print("================================")

    print(
        "Satellites processed:",
        len(uncertainties)
    )

    print(
        "Conjunctions updated:",
        updated_count
    )

    print("\nGenerated files:")
    print(UNCERTAINTY_FILE)
    print(CONJUNCTION_FILE)


if __name__ == "__main__":
    main()