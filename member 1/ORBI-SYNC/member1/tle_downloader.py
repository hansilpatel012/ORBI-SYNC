import requests
from pathlib import Path

# Automatically locate ORBI-SYNC project folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Output directory
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "combined_tle.txt"

BASE_URL = "https://celestrak.org/NORAD/elements/gp.php"

SOURCES = {
    "Space Stations": {"GROUP": "STATIONS"},
    "Cartosat": {"NAME": "CARTOSAT"},
    "Resourcesat": {"NAME": "RESOURCESAT"},
    "INSAT": {"NAME": "INSAT"},
    "Cosmos Debris": {"NAME": "COSMOS 2251 DEB"}
}


def download_tle(source_name, params):

    params["FORMAT"] = "TLE"

    print(f"\nDownloading {source_name}...")

    try:
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        return response.text.strip()

    except requests.RequestException as error:
        print(f"Download failed: {error}")
        return ""


def extract_records(raw_data):

    lines = [
        line.strip()
        for line in raw_data.splitlines()
        if line.strip()
    ]

    records = []

    for i in range(0, len(lines) - 2, 3):

        name = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]

        if (
            line1.startswith("1 ")
            and line2.startswith("2 ")
            and len(line1) == 69
            and len(line2) == 69
            and line1[2:7] == line2[2:7]
        ):
            records.append((name, line1, line2))

    return records


def main():

    all_objects = {}

    for source_name, params in SOURCES.items():

        raw_data = download_tle(
            source_name,
            params.copy()
        )

        records = extract_records(raw_data)

        print("Objects found:", len(records))

        for record in records:

            name, line1, line2 = record
            norad_id = line1[2:7]

            all_objects[norad_id] = record

    # Limit initial dataset to 200 unique objects
    selected_objects = list(all_objects.values())[:200]

    # Save downloaded TLE records
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:

        for name, line1, line2 in selected_objects:

            file.write(name + "\n")
            file.write(line1 + "\n")
            file.write(line2 + "\n")

    print("\n================================")
    print("TLE DOWNLOAD COMPLETED")
    print("================================")

    print("Total unique objects:", len(selected_objects))
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    main()