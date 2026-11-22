import json
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "member1" / "output"

with open(OUT / "conjunction.json") as f:
    our_data = json.load(f)["conjunctions"]

socrates = pd.read_csv(
    OUT / "socrates.csv",
    dtype={
        "NORAD_CAT_ID_1": str,
        "NORAD_CAT_ID_2": str
    }
)

def clean_id(value):
    return str(value).strip().split(".")[0].zfill(5)

socrates_ids = set(
    socrates["NORAD_CAT_ID_1"].dropna().map(clean_id)
) | set(
    socrates["NORAD_CAT_ID_2"].dropna().map(clean_id)
)

print("SOCRATES unique objects:", len(socrates_ids))

matches = 0

for event in our_data:

    id1 = clean_id(event["object_1"]["norad_id"])
    id2 = clean_id(event["object_2"]["norad_id"])

    id1_exists = id1 in socrates_ids
    id2_exists = id2 in socrates_ids

    pair_exists = (
        (socrates["NORAD_CAT_ID_1"].map(clean_id) == id1) &
        (socrates["NORAD_CAT_ID_2"].map(clean_id) == id2)
    ) | (
        (socrates["NORAD_CAT_ID_1"].map(clean_id) == id2) &
        (socrates["NORAD_CAT_ID_2"].map(clean_id) == id1)
    )

    found = pair_exists.any()

    if found:
        matches += 1

    print(
        id1, "<->", id2,
        "| Object IDs present:", id1_exists and id2_exists,
        "| Exact pair present:", found
    )

print("\n================================")
print("DIAGNOSTIC SUMMARY")
print("================================")
print("Our conjunctions:", len(our_data))
print("Exact pairs found:", matches)
print("Exact pairs not found:", len(our_data) - matches)