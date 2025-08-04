#
# This script provides a class-based system for programmatically managing
# the Knowledge.json file. It is aligned with the official schemas/knowledge.schema.json.
# It allows for structured, auditable updates by ingesting "fragments" of new
# information into the 'knowledge_items' list.
#
import json
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from typing import List, Dict, Any
import jsonschema

# --- Utility Functions (Placeholders) ---
def json_load(path: Path):
    """Loads a JSON file with error handling."""
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)

def json_dump_pretty(data: dict, path: Path):
    """Saves a dictionary to a JSON file with pretty printing."""
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def utcnow_iso():
    """Returns the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()

# --- Core KnowledgeStore Class ---

class KnowledgeStore:
    """
    Maintains the master Knowledge.json file according to the defined schema.
    """
    def __init__(self, path: str = "Knowledge.json", schema_path: str = "schemas/knowledge.schema.json"):
        self.path = Path(path)
        self.schema_path = Path(schema_path)
        self.store = self._load()

    def _load(self):
        """Loads the knowledge store or creates a valid default structure."""
        if self.path.exists():
            return json_load(self.path)
        return {
            "version": "1.0.0",
            "metadata": {},
            "knowledge_items": []
        }

    def _validate_store(self) -> bool:
        """Validates the current store against the schema."""
        if not self.schema_path.exists():
            print(f"Warning: Schema file not found at {self.schema_path}. Cannot validate.")
            return True # Don't fail if schema is missing
        try:
            schema = json_load(self.schema_path)
            jsonschema.validate(instance=self.store, schema=schema)
            return True
        except jsonschema.ValidationError as e:
            print(f"Error: Knowledge store fails schema validation. {e.message}")
            return False

    def save(self):
        """Validates and saves the current state of the knowledge store."""
        if not self._validate_store():
            print("Save aborted due to validation failure.")
            return

        self.store.setdefault("metadata", {})
        self.store["metadata"]["updated_at"] = utcnow_iso()
        json_dump_pretty(self.store, self.path)

    def _find_item(self, **kwargs):
        """Finds a knowledge item by arbitrary key-value pairs."""
        for item in self.store.get("knowledge_items", []):
            if all(item.get(key) == value for key, value in kwargs.items()):
                return item
        return None

    def ingest_fragment(self, fragment: dict) -> bool:
        """
        Ingests a single fragment to add or update a knowledge item.
        Returns True on success, False on failure.
        """
        operation = fragment.get("operation")
        payload = fragment.get("payload")

        if not (operation and payload and "id" in payload):
            print(f"Warning: Invalid fragment format. Skipping: {fragment}")
            return False

        # Duplicate Guard: Check for existing topic/tag combo on 'add'
        if operation == "add" and 'topic' in payload and 'tag' in payload:
            if self._find_item(topic=payload['topic'], tag=payload['tag']):
                print(f"Warning: Duplicate item with topic '{payload['topic']}' and tag '{payload['tag']}' already exists. Skipping add.")
                return False

        existing_item = self._find_item(id=payload["id"])
        
        success = False
        if operation in ("add", "update"):
            if existing_item:
                print(f"Updating item: {payload['id']}")
                existing_item.update(payload)
                success = True
            else:
                print(f"Adding new item: {payload['id']}")
                self.store["knowledge_items"].append(payload)
                success = True
        elif operation == "delete" and existing_item:
            print(f"Deleting item: {payload['id']}")
            self.store["knowledge_items"].remove(existing_item)
            success = True
        else:
            print(f"Warning: Operation '{operation}' on item '{payload['id']}' could not be completed.")
            success = False

        # Operation Logging: Add an audit entry on success
        if success:
            self.store.setdefault("metadata", {}).setdefault("operation_log", []).append({
                "timestamp": utcnow_iso(),
                "operation": operation,
                "item_id": payload["id"]
            })
        
        return success

    def update_from_session(self, fragments: List[Dict]):
        """Public workflow to update the store from a list of session fragments."""
        applied_count = 0
        for f in fragments:
            if self.ingest_fragment(f):
                applied_count += 1
        
        if applied_count > 0:
            self.save()
            print(f"Knowledge store updated with {applied_count} fragments and saved to {self.path}.")
        else:
            print("No new fragments were applied to the knowledge store.")

# --- Example Usage ---
if __name__ == '__main__':
    ks = KnowledgeStore("Knowledge.json")

    # Example fragment that aligns with the schema
    session_fragment_example = {
      "operation": "add",
      "payload": {
        "id": str(uuid4()),
        "topic": "New Test Topic from Script",
        "tag": "#TESTING_SCRIPT",
        "tier": "knowledge",
        "content": "This is a new knowledge item added programmatically."
      },
      "timestamp": utcnow_iso()
    }

    ks.update_from_session([session_fragment_example])
