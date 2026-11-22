import json
import hashlib
from pathlib import Path


# ==========================================
# DETECT PROJECT ROOT
# ==========================================

SCRIPT_DIR = Path(__file__).resolve().parent

if (SCRIPT_DIR / "data" / "processed" / "cleaned_tle.txt").exists():
    PROJECT_ROOT = SCRIPT_DIR
else:
    PROJECT_ROOT = SCRIPT_DIR.parent


# ==========================================
# FILE PATHS
# ==========================================

TLE_FILE = (
    PROJECT_ROOT / "data" / "processed" / "cleaned_tle.txt"
)

TRAJECTORY_FILE = (
    PROJECT_ROOT / "member1" / "output" / "trajectories.json"
)


# ==========================================
# CHECK FILES
# ==========================================

print("Project root:", PROJECT_ROOT)
print("TLE file:", TLE_FILE)
print("Trajectory file:", TRAJECTORY_FILE)

if not TLE_FILE.exists():
    raise FileNotFoundError(f"TLE file not found: {TLE_FILE}")

if not TRAJECTORY_FILE.exists():
    raise FileNotFoundError(
        f"Trajectory file not found: {TRAJECTORY_FILE}"
    )


# ==========================================
# LOAD TRAJECTORY METADATA
# ==========================================

with open(TRAJECTORY_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)


# ==========================================
# CALCULATE CURRENT TLE HASH
# ==========================================

with open(TLE_FILE, "rb") as f:
    current_hash = hashlib.sha256(f.read()).hexdigest()


saved_hash = data["metadata"].get("tle_sha256")


# ==========================================
# DISPLAY RESULTS
# ==========================================

print("\n========== TLE HASH VERIFICATION ==========")

print("Saved TLE hash:  ", saved_hash)
print("Current TLE hash:", current_hash)

if saved_hash is None:
    print("\nRESULT: No saved TLE hash found.")
elif saved_hash == current_hash:
    print("\nRESULT: TLE FILES MATCH")
else:
    print("\nRESULT: TLE FILES DO NOT MATCH")

print("\n===========================================")