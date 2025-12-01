import json
import csv

INPUT_JSON = "class_ast.json"  # Your JSON file
OUTPUT_CSV = "class_ast.csv"   # Output Excel-compatible CSV file

def flatten_json(obj, parent_key='', sep='.'):
    """
    Flatten hierarchical JSON for Excel-friendly CSV output.
    Nested children are flattened with keys like 'children.0.name'.
    """
    items = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            items.extend(flatten_json(v, new_key, sep=sep))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            items.extend(flatten_json(v, new_key, sep=sep))
    else:
        items.append((parent_key, obj))
    return items

def main():
    with open(INPUT_JSON, "r") as f:
        data = json.load(f)

    # Flatten each top-level object
    rows = []
    for obj in data:
        flat = dict(flatten_json(obj))
        rows.append(flat)

    # Collect all column headers
    all_keys = set()
    for row in rows:
        all_keys.update(row.keys())
    all_keys = sorted(all_keys)

    # Write to CSV
    with open(OUTPUT_CSV, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"JSON data written to {OUTPUT_CSV} successfully.")

if __name__ == "__main__":
    main()
