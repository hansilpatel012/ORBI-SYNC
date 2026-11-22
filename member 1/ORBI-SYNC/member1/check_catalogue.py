import json
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "member1" / "output"

with open(OUT / "trajectories.json") as f:
    trajectories = json.load(f)["trajectories"]

socrates = pd.read_csv(
    OUT / "socrates.csv",
    dtype=str
)

def normalize(value):
    return str(value).strip().split(".")[0].zfill(5)

our_ids = {
    normalize(s["norad_id"])
    for s in trajectories
}

socrates_ids = (
    set(socrates["NORAD_CAT_ID_1"].dropna().map(normalize))
    | set(socrates["NORAD_CAT_ID_2"].dropna().map(normalize))
)

common = our_ids.intersection(socrates_ids)

print("Our satellite count:", len(our_ids))
print("SOCRATES unique objects:", len(socrates_ids))
print("Common satellite IDs:", len(common))

print("\nFirst 20 common IDs:")
for norad_id in sorted(common)[:20]:
    print(norad_id)

print("\nOur IDs absent from SOCRATES:")
for norad_id in sorted(our_ids - socrates_ids)[:20]:
    print(norad_id)