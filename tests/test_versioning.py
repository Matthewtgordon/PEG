import json
import uuid
import sys
import os
from pathlib import Path

# Add the repository root to the Python path to find the scripts package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.migrate_knowledge import migrate_file


def test_migration_script(tmp_path: Path):
    """
    Tests that the migration script correctly adds a version field
    and unique IDs to a sample knowledge file.
    """
    # 1. Create a sample pre-migration file in a temporary directory
    sample_data = {
        "knowledge_items": [
            {"topic": "X", "tag": "test", "content": "Content for X"},
            {"topic": "Y", "tag": "test", "content": "Content for Y"}
        ]
    }
    file_to_migrate = tmp_path / "TestKnowledge.json"
    with file_to_migrate.open('w') as f:
        json.dump(sample_data, f, indent=2)

    # 2. Run the migration script on the sample file
    migrate_file(file_to_migrate)

    # 3. Read the migrated file and assert changes
    with file_to_migrate.open('r') as f:
        migrated_data = json.load(f)

    # Assert that the version field was added
    assert 'version' in migrated_data
    assert migrated_data['version'] == 'v1.0.0'

    # Assert that all items now have a unique 'id' field
    items = migrated_data.get('knowledge_items', [])
    assert len(items) == 2
    for item in items:
        assert 'id' in item
        # Check that the ID is a valid UUID
        try:
            uuid.UUID(item['id'])
        except ValueError:
            assert False, f"ID '{item['id']}' is not a valid UUID."
