import json
import pandas as pd

def messier_json_to_csv(json_file, csv_file):
    # Load JSON
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # If data is a list, convert directly
    if isinstance(data, list):
        df = pd.DataFrame(data)
    # If data is a dict with a "data" key, use that
    elif isinstance(data, dict) and "data" in data:
        df = pd.DataFrame.from_dict(data["data"], orient="index")
    else:
        raise ValueError("Unexpected JSON structure")

    # Save to CSV
    df.to_csv(csv_file, index_label="MessierKey")

# Example usage
messier_json_to_csv(
    r"C:\Users\olsen\Documents\astro-backend\catalog.json",
    r"C:\Users\olsen\Documents\astro-backend\catalog.csv"
)


