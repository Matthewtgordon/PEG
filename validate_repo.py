#
# This script validates the integrity of the PEG project repository.
# It checks for the presence of all required configuration files,
# ensures they are valid JSON, and validates key files against their schemas
# and versioning rules as defined in the project RFCs.
# This is a critical first step in the CI/CD pipeline.
#
import json
import sys
import re
from pathlib import Path
import jsonschema

# Note: Using ASCII-only output for cross-platform compatibility

def load_json(path: Path):
    """Safely loads a JSON file."""
    with path.open(encoding='utf-8') as f:
        return json.load(f)

def validate_json(path: Path):
    """Validates that a file is well-formed JSON."""
    try:
        load_json(path)
        return True
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON decode error in {path}: {e}")
        return False

def validate_schema(data: dict, schema_path: Path):
    """Validates data against a JSON schema."""
    if not schema_path.exists():
        print(f"WARNING: Schema file not found: {schema_path}. Skipping schema validation.")
        return True
    schema = load_json(schema_path)
    try:
        jsonschema.validate(instance=data, schema=schema)
        return True
    except jsonschema.ValidationError as e:
        print(f"ERROR: Schema validation error for {schema_path.stem}: {e.message}")
        return False

def validate_version_field(data: dict, filename: str):
    """Explicitly validates the 'version' field using a Semantic Versioning pattern."""
    if 'version' not in data:
        print(f"ERROR: Missing required 'version' field in {filename}.")
        return False

    version = data['version']
    semver_pattern = re.compile(r'^\d+\.\d+\.\d+$')
    if not isinstance(version, str) or not semver_pattern.match(version):
        print(f"ERROR: Invalid SemVer format for 'version' in {filename}. Expected 'X.Y.Z', found '{version}'.")
        return False
    return True

def validate_apeg_structure():
    """Validate APEG package structure and core modules."""
    errors = []
    warnings = []

    print("\nStep 3: Validating APEG package structure...")

    # Check package structure
    apeg_core = Path("src/apeg_core")
    if not apeg_core.exists():
        errors.append("src/apeg_core/ directory not found")
        return errors, warnings  # Can't continue without package

    # Check core modules
    required_modules = [
        "src/apeg_core/__init__.py",
        "src/apeg_core/orchestrator.py",
        "src/apeg_core/decision/__init__.py",
        "src/apeg_core/decision/bandit_selector.py",
        "src/apeg_core/decision/loop_guard.py",
        "src/apeg_core/agents/__init__.py",
        "src/apeg_core/agents/base_agent.py",
        "src/apeg_core/scoring/__init__.py",
        "src/apeg_core/scoring/evaluator.py",
        "src/apeg_core/logging/__init__.py",
        "src/apeg_core/logging/logbook_adapter.py",
        "src/apeg_core/connectors/__init__.py",
    ]

    for module_path in required_modules:
        if not Path(module_path).exists():
            errors.append(f"Missing core module: {module_path}")

    # Check for .env (should NOT be committed)
    if Path(".env").exists():
        errors.append(".env file is committed (SECURITY RISK)")

    # Check for .env.sample (should exist as template)
    if not Path(".env.sample").exists():
        warnings.append(".env.sample not found (recommended for documentation)")

    # Check placeholder tracking
    if not Path("docs/APEG_PLACEHOLDERS.md").exists():
        warnings.append("docs/APEG_PLACEHOLDERS.md not found")

    # Verify imports work
    try:
        import sys
        sys.path.insert(0, 'src')
        from apeg_core import APEGOrchestrator
        from apeg_core.decision import choose_macro, detect_loop
        from apeg_core.agents import get_agent
        print("  OK: APEG imports successful")
    except ImportError as e:
        errors.append(f"APEG import failed: {e}")

    return errors, warnings

def main():
    """Main validation function to run all checks."""
    print("--- Running Repository Validation ---")
    
    # CORRECTION: Added Modules.json to the list of required files.
    repo_files = [
        'Knowledge.json',
        'Rules.json',
        'Logbook.json',
        'SessionConfig.json',
        'WorkflowGraph.json',
        'TagEnum.json',
        'Tasks.json',
        'Tests.json',
        'Journal.json',
        'PromptScoreModel.json',
        'PromptModules.json',
        'Modules.json'
    ]
    
    all_valid = True
    
    print("\nStep 1: Checking for file presence and JSON format...")
    for filename in repo_files:
        path = Path(filename)
        if not path.exists():
            print(f"ERROR: Missing required file: {filename}")
            all_valid = False
            continue

        if not validate_json(path):
            all_valid = False
    
    print("\nStep 2: Validating versioned files against schema and SemVer format...")
    versioned_files_to_check = {
        'Knowledge.json': Path('schemas/knowledge.schema.json'),
    }

    for filename, schema_path in versioned_files_to_check.items():
        file_path = Path(filename)
        if file_path.exists():
            data = load_json(file_path)
            if not validate_version_field(data, filename):
                all_valid = False
            if not validate_schema(data, schema_path):
                all_valid = False

    # Validate APEG structure
    apeg_errors, apeg_warnings = validate_apeg_structure()

    # Print APEG errors
    for error in apeg_errors:
        print(f"  ERROR: {error}")
        all_valid = False

    # Print APEG warnings (don't fail validation)
    for warning in apeg_warnings:
        print(f"  WARNING: {warning}")

    print("\n--- Validation Complete ---")
    if all_valid:
        print("OK: All repository configuration files are valid.")
    else:
        print("\nERROR: Repository validation failed. Please fix the errors listed above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
