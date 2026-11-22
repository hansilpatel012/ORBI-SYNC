import json
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "member1" / "output"

with open(OUT / "conjunction.json") as f:
    our_events = json.load(f)["conjunctions"]

socrates = pd.read_csv(
    OUT / "socrates.csv",
    dtype=str
)

def clean(value):
    return str(value).strip().split(".")[0].zfill(5)

# Build SOCRATES pair lookup
socrates_pairs = set()

for _, row in socrates.iterrows():

    id1 = clean(row["NORAD_CAT_ID_1"])
    id2 = clean(row["NORAD_CAT_ID_2"])

    socrates_pairs.add(tuple(sorted([id1, id2])))

# Check our conjunction pairs
both_present = 0
exact_matches = 0

print("\n========== PAIR OVERLAP ==========\n")

for event in our_events:

    id1 = clean(event["object_1"]["norad_id"])
    id2 = clean(event["object_2"]["norad_id"])

    key = tuple(sorted([id1, id2]))

    first_present = (
        id1 in set(socrates["NORAD_CAT_ID_1"].map(clean))
        or id1 in set(socrates["NORAD_CAT_ID_2"].map(clean))
    )

    second_present = (
        id2 in set(socrates["NORAD_CAT_ID_1"].map(clean))
        or id2 in set(socrates["NORAD_CAT_ID_2"].map(clean))
    )

    if first_present and second_present:
        both_present += 1

    if key in socrates_pairs:
        exact_matches += 1

    print(
        id1, "<->", id2,
        "| Both objects present:", first_present and second_present,
        "| Exact pair:", key in socrates_pairs
    )

print("\n========== SUMMARY ==========")
print("Our conjunctions:", len(our_events))
print("Both objects present:", both_present)
print("Exact pair matches:", exact_matches)
print("No exact pair match:", len(our_events) - exact_matches)