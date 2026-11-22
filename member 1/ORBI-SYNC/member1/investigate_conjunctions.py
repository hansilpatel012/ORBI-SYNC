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

socrates["TCA"] = pd.to_datetime(
    socrates["TCA"], utc=True, errors="coerce"
)

socrates["NORAD_CAT_ID_1"] = (
    socrates["NORAD_CAT_ID_1"].str.strip()
)

socrates["NORAD_CAT_ID_2"] = (
    socrates["NORAD_CAT_ID_2"].str.strip()
)

print("\n========== CONJUNCTION INVESTIGATION ==========\n")

for event in our_events:

    id1 = str(event["object_1"]["norad_id"]).zfill(5)
    id2 = str(event["object_2"]["norad_id"]).zfill(5)

    our_tca = pd.to_datetime(
        event["tca_utc"], utc=True
    )

    our_distance = float(event["miss_distance_km"])

    pair_mask = (
        (
            (socrates["NORAD_CAT_ID_1"] == id1) &
            (socrates["NORAD_CAT_ID_2"] == id2)
        )
        |
        (
            (socrates["NORAD_CAT_ID_1"] == id2) &
            (socrates["NORAD_CAT_ID_2"] == id1)
        )
    )

    exact = socrates[pair_mask]

    print("----------------------------------------")
    print("Pair:", id1, "<->", id2)
    print("Our TCA:", our_tca)
    print("Our miss distance:", our_distance, "km")

    if not exact.empty:

        print("Exact SOCRATES pair found:", len(exact))

    else:

        print("Exact SOCRATES pair: NOT FOUND")

        # Inspect other events involving either object
        related = socrates[
            (socrates["NORAD_CAT_ID_1"].isin([id1, id2])) |
            (socrates["NORAD_CAT_ID_2"].isin([id1, id2]))
        ].copy()

        related = related.dropna(subset=["TCA"])

        if not related.empty:

            related["time_difference_hours"] = (
                related["TCA"] - our_tca
            ).abs().dt.total_seconds() / 3600

            nearest = related.sort_values(
                "time_difference_hours"
            ).head(3)

            print("Nearest SOCRATES events involving either object:")

            print(
                nearest[
                    [
                        "NORAD_CAT_ID_1",
                        "NORAD_CAT_ID_2",
                        "TCA",
                        "time_difference_hours"
                    ]
                ].to_string(index=False)
            )

        else:
            print("No related SOCRATES events found.")

print("\n========== INVESTIGATION FINISHED ==========")