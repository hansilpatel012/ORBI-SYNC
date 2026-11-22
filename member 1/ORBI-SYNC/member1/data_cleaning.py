import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Automatically locate project directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Input and output paths
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "combined_tle.txt"

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TLE_OUTPUT = OUTPUT_DIR / "cleaned_tle.txt"
CSV_OUTPUT = OUTPUT_DIR / "tle_metadata.csv"


# Validate TLE checksum
def check_checksum(line):

    if len(line) != 69 or not line[-1].isdigit():
        return False

    total = 0

    for char in line[:68]:

        if char.isdigit():
            total += int(char)

        elif char == "-":
            total += 1

    return total % 10 == int(line[-1])


# Extract epoch from TLE
def get_epoch(line1):

    try:

        year = int(line1[18:20])
        day = float(line1[20:32])

        if year >= 57:
            year += 1900
        else:
            year += 2000

        if not 1 <= day < 367:
            return None

        epoch = (
            datetime(year, 1, 1, tzinfo=timezone.utc)
            + timedelta(days=day - 1)
        )

        return epoch

    except (ValueError, OverflowError):
        return None


# Load TLE records
def load_tle_file():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"TLE file not found: {INPUT_FILE}"
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        return [
            line.strip()
            for line in file
            if line.strip()
        ]


# Main cleaning function
def clean_tle_data():

    lines = load_tle_file()

    valid_objects = []
    rejected = 0

    current_time = datetime.now(timezone.utc)

    for i in range(0, len(lines) - 2, 3):

        name = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]

        # Check TLE structure
        if not (
            line1.startswith("1 ")
            and line2.startswith("2 ")
            and len(line1) == 69
            and len(line2) == 69
        ):
            rejected += 1
            continue

        # Check satellite IDs
        id1 = line1[2:7]
        id2 = line2[2:7]

        if id1 != id2:
            rejected += 1
            continue

        # Check checksums
        if not (
            check_checksum(line1)
            and check_checksum(line2)
        ):
            rejected += 1
            continue

        # Extract epoch
        epoch = get_epoch(line1)

        if epoch is None or epoch > current_time:
            rejected += 1
            continue

        # Calculate TLE age in hours
        tle_age_hours = (
            current_time - epoch
        ).total_seconds() / 3600

        valid_objects.append({
            "name": name,
            "norad_id": id1,
            "line1": line1,
            "line2": line2,
            "epoch": epoch.isoformat(),
            "tle_age_hours": round(tle_age_hours, 2)
        })

    # Remove duplicate satellite records
    df = pd.DataFrame(valid_objects)

    if not df.empty:

        df = df.drop_duplicates(
            subset="norad_id",
            keep="first"
        )

    # Save cleaned TLE file
    with open(TLE_OUTPUT, "w", encoding="utf-8") as file:

        for _, row in df.iterrows():

            file.write(row["name"] + "\n")
            file.write(row["line1"] + "\n")
            file.write(row["line2"] + "\n")

    # Save metadata CSV
    df.to_csv(CSV_OUTPUT, index=False)

    # Display summary
    print("\n================================")
    print("TLE CLEANING COMPLETED")
    print("================================")

    print("Total input records:", len(lines) // 3)
    print("Valid unique objects:", len(df))
    print("Rejected records:", rejected)

    if not df.empty:

        print("\nSatellite TLE Age:")

        print(
            df[["name", "norad_id", "tle_age_hours"]]
            .to_string(index=False)
        )

    print("\nGenerated files:")
    print(TLE_OUTPUT)
    print(CSV_OUTPUT)


if __name__ == "__main__":
    clean_tle_data()