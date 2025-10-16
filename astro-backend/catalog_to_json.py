import csv
import json

def csv_to_json(csv_file, json_file):
    data = []
    with open(csv_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    
    with open(json_file, mode='w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

# Example usage
csv_to_json(r"C:\Users\olsen\Documents\astro-backend\catalog_v1.csv", r"C:\Users\olsen\Documents\astro-backend\catalog_v1.json")