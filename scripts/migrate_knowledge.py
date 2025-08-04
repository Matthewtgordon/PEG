import json
import uuid
import argparse
from pathlib import Path


def migrate_file(file_path: Path):
    """
    Adds a version field and unique IDs to a PEG knowledge file.
    This is intended as a one-time migration script.
    """
    if not file_path.exists():
        print(f"Error: File not found at {file_path}")
        return

    with file_path.open('r+') as f:
        data = json.load(f)

        # Add version field if it doesn't exist
        if 'version' not in data:
            data['version'] = 'v1.0.0'
            print(f"Added version 'v1.0.0' to {file_path.name}")

        # Ensure 'knowledge_items' is a list
        items = data.get('knowledge_items', [])
        if not isinstance(items, list):
            print(f"Warning: 'knowledge_items' in {file_path.name} is not a list. Skipping ID migration.")
            return

        # Add unique ID to each item if it doesn't have one
        migrated_count = 0
        for item in items:
            if 'id' not in item:
                item['id'] = str(uuid.uuid4())
                migrated_count += 1

        if migrated_count > 0:
            print(f"Added unique IDs to {migrated_count} items in {file_path.name}")

        # Write the updated data back to the file
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()

    print(f"Migration complete for {file_path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate PEG knowledge files to add versioning and IDs.")
    parser.add_argument("file", type=str, help="The path to the JSON file to migrate (e.g., Knowledge.json).")
    args = parser.parse_args()

    migrate_file(Path(args.file))
