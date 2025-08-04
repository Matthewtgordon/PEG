<<<<<<< Updated upstream
# PEG
Build autonomous, resilient and observable AI agents with built-in workflow orchestration, security, statefulness and telemetry.
=======
# PEGGPT
This repository contains configuration files and prompts for PEGGPT.
## Active Configuration
The active session configuration is stored in `SessionConfig.json`.
## Archived Configurations

Older session configuration files are stored in the `archived_configs` folder. For example, `SessionConfig_Old_4.30.json` has been moved there for reference.
=======
This repository contains prompt engineering resources and configurations.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
=======
# PEGGPT Repository

This repository contains configuration files, prompts, and workflow definitions for the **Prompt Engineering Guide (PEG)** system. PEG orchestrates prompt generation and agent coordination using a set of JSON and text assets. These files define knowledge bases, workflow graphs, session settings, and utilities for API calls.

## File Overview

| File | Purpose |
| ---- | ------- |
| `Knowledge.json` | Persistent knowledge base with facts and rules referenced by the orchestrator. |
| `Logbook.json` | Consolidated changelog and journal tracking session events and mutations. |
| `PromptEngineer.txt` | Main prompt logic describing the PEG workflow with macro definitions and export routine. |
| `PromptModules.json` | Tool configuration for calling external APIs such as OpenAI and GitHub. |
| `SessionConfig.json` | Current session settings controlling modes, scoring, and schema links. |
| `TagEnum.json` | Standardized tag definitions used for routing, scoring, and prompt validation. |
| `Tasks.json` | Checklist items and notes used by PEG during intake and prep phases. |
| `Tests.json` | Example prompts and edge cases for validating agents and macros. |
| `WorkflowGraph.json` | Node graph describing the execution flow from intake to export. |
| `knowledge.schema.json` | JSON schema applied to `Knowledge.json` during validation. |

## Using the Configurations

The PEG orchestrator loads these files as part of its startup routine. Update the JSON files as needed to refine prompts, add new agents, or adjust workflows. The `SessionConfig.json` file controls which modules are enabled and links schema files for validation. `PromptModules.json` specifies API endpoints and authentication headers and is referenced whenever PEG makes external calls.

### Environment Variables

Certain operations require API credentials set as environment variables:

- `OPENAI_API_KEY` – Token for the OpenAI API used by the `openai_chat` tool.
- `GITHUB_PAT` – Personal access token used for GitHub API operations when `github_api` or `github_write` modules are enabled.

Ensure these variables are exported in your shell before running any scripts that interact with external services.

### Setup

1. Clone the repository.
2. Export the required environment variables:
   ```bash
   export OPENAI_API_KEY="<your-openai-key>"
   export GITHUB_PAT="<your-github-token>"
   ```
3. Modify the JSON configuration files to suit your workflow. `SessionConfig.json` and `PromptModules.json` are typically edited most frequently.
4. Run your PEG-based tooling or scripts. They will read from the configuration files in this directory.

This README provides a high-level overview. Review the comments within each file for additional context.

# PEGGPT

This repository contains configuration and assets for the PEG prompt engineering system, including JSON files for tasks, workflows, knowledge, and an optional `Journal.json` diary used for extended logging.

## Environment Variables

To enable GitHub API access, provide a personal access token via the `GITHUB_PAT` environment variable. The token is used by modules defined in `PromptModules.json`.

For OpenAI integration, set the `OPENAI_API_KEY` environment variable.

## Validating the Configuration

Run `validate_repo.py` before executing any agent workflows to ensure all JSON files are present and conform to `knowledge.schematx.json`. Install dependencies from `requirements.txt` first.

```bash
pip install -r requirements.txt
python validate_repo.py
```
The script exits with a non-zero status if validation fails.

## Running the Scoring Script

The repository includes a helper script `run_scoring.py` that reads a scoring model and outputs a JSON report. Use it by providing a model file and an output location:

Onboarding Guide for AI Assistants
This document outlines the core conventions and architecture of the PEG (Promptable Engineer GPT) project. Adherence to these principles is required for all development.

1. Core Philosophy
The PEG system is a "builder of tools." Its primary function is to orchestrate other agents and systems to produce high-quality, structured outputs. It operates on a principle of "evidence-based adoption," meaning all changes must be validated against tests (Tests.json) and quality metrics (PromptScoreModel.json) before being accepted.

2. Key File Conventions
WorkflowGraph.json: The single source of truth for agent orchestration. It defines the nodes (steps) and edges (transitions) of any process.

Knowledge.json: The agent's active memory. Contains facts, principles, and rules the agent must follow.
Rules.json: A subset of knowledge that defines strict, non-negotiable enforcement policies.
Logbook.json / Journal.json: The historical record. Logbook.json is for automated, machine-generated audit entries. Journal.json is for human-readable narrative and context.
/src/ directory: Contains the Python code that acts as the "brain" or execution engine for the agent.

3. Placeholder and Secret Conventions
Placeholders in Agent_Prompts.json: Prompts stored in this file use bracketed, uppercase placeholders (e.g., [DIRECTIVE_NAME]). When using one of these prompts, you must replace the placeholder with the appropriate value.
Secrets in Configuration: API keys and other secrets are never stored directly in files. They are referenced using the format <env:SECRET_NAME> (e.g., <env:OPENAI_API_KEY>). The execution environment is responsible for substituting these placeholders with actual secrets.

4. The CI/CD Pipeline (peg-ci.yml)
All commits are subject to an automated validation pipeline that:
Ensures all required files exist and are valid JSON (validate_repo.py).
Runs a suite of behavioral tests (pytest).
Scores the output against a quality model (run_scoring.py).
A commit will fail if any of these checks do not pass. Your primary goal is to ensure the CI pipeline is always passing.

```bash
python run_scoring.py --model PromptScoreModel.json --out score.json
```
The script calculates a simple average from dummy scoring values and compares it against `ci_minimum_score` defined in the model file. It exits with a non-zero status if the calculated score is below this threshold.

Session Log: PEG System Recovery (July 30, 2025)
This log details the analysis, corrections, and key decisions made during our session to restore the integrity of the PEG project.

Objective: To diagnose and fix CI/CD failures by auditing and correcting all core system files based on the project's design documents and RFCs.

Key Finding: The primary source of instability was a "system drift," where multiple files contained conflicting or outdated logic, and the CI pipeline was not correctly configured to catch these errors.

File-by-File Corrections:

PromptEngineer.txt:

Problem: Lacked critical sections for versioning ("Mutation Discipline") and quality control ("Adoption Gate").

Correction: We created a new, canonical version that merges the best features of previous versions, including logic for the adoption gate, mutation discipline, and feedback loops for the learning modules.

validate_repo.py:

Problem: The script was missing several critical files from its checklist and was using an incorrect path for the knowledge schema.

Correction: We updated the script to validate all required files (including Rules.json, PromptScoreModel.json, and Modules.json), corrected the schema path, and added a powerful new check to ensure that all workflows in the graph reference valid, defined modules.

GitHub Actions (peg-ci.yml, update-tasks.yml, append-to-log.yml):

Problem: The main CI workflow was failing because it wasn't providing the required inputs to the scoring script and wasn't installing all necessary dependencies. Additionally, there was no automated way to update Tasks.json or the log files.

Correction: We corrected the peg-ci.yml file to properly install dependencies from requirements.txt and to provide the correct arguments to the scoring script. We also created two new, powerful manual workflows to allow you to safely update your Tasks.json and log files directly from the GitHub website without any manual file editing.

Knowledge.json & schemas/knowledge.schema.json:

Problem: Knowledge.json was missing the required unique id fields and contained duplicated, incorrect sections. The schema file that validates it also had errors and was out of sync.

Correction: We created a clean, corrected version of Knowledge.json with unique IDs and a proper structure. We then created a new, strict schema that is now in perfect alignment with the data file and the system's requirements.

Rules.json & schemas/rules.schema.json:

Problem: Rules.json did not exist, causing CI failures.

Correction: We created a new Rules.json file with a standardized structure and also created a corresponding schema to ensure its long-term integrity.

/src/ Directory (Python Scripts):

Problem: The Python scripts (orchestrator.py, loop_guard.py, bandit_selector.py, knowledge_update.py) were not correctly integrated. They contained placeholder logic and were not correctly passing data between each other.

Correction: We performed a major refactoring of all Python scripts to ensure they work together as a cohesive system. The orchestrator now correctly executes the workflow graph, and the learning modules are properly connected to receive real feedback.

Outstanding Action Items & Next Steps
Here is the list of tasks that we identified but did not complete. This is the starting point for your next session.

Finalize the Orchestrator Integration:

Task: The src/orchestrator.py script is now a functional graph engine, but it still uses a simulated score. The final step is to replace the placeholder scoring function with a real call to the run_scoring.py script. This will make the agent's learning loop fully operational.

Rename Core Files for Clarity:
Task: We agreed that renaming PromptModules.json to API_Connectors.json and Modules.json to Prompt_Modules.json would improve clarity.
Impact: This would require coordinated changes in validate_repo.py and src/orchestrator.py.

Filesystem and Dependency Map
This map provides a clear reference for how the different parts of the PEG system interact.
WorkflowGraph.json (The Blueprint)
Reads Modules.json to know which modules to execute for each step.
Is executed by src/orchestrator.py.
src/orchestrator.py (The Brain)
Reads WorkflowGraph.json to know what to do.
Reads SessionConfig.json for settings.
Reads Modules.json to get the details of each macro.
Calls src/bandit_selector.py and src/loop_guard.py for intelligent decision-making.
Calls run_scoring.py to get a quality score for its work.
Modules.json (The Toolbox)
Defines the available macros.
Reads PromptModules.json to know which API connectors to use.
PromptModules.json (The Phonebook)
Defines how to connect to external services like OpenAI.
Knowledge.json / Rules.json (The Memory)
Contain the agent's knowledge and rules.
Are read by the orchestrator and can be updated by src/knowledge_update.py.
CI Workflow (.github/workflows/peg-ci.yml) (The Quality Gate)
Uses requirements.txt to set up its environment.
Runs validate_repo.py to check the integrity of all other files.

## Plugin Development Guide
Describe plugins in `src/plugin_manager.py` and register them via entry points under the namespaces defined in `config/plugins.json`.

## Connector Development Guide
Connectors inherit from `BaseConnector` and implement `connect`, `_query`, and `disconnect`. See examples in `src/connectors/`.

## Security Best Practices
Use the `SandboxExecutor` for running untrusted code and keep API keys in environment variables. Limit resources and prefer least privilege.

## Memory System Usage
`MemoryManager` provides short-term buffers and long-term summaries. Use task or agent identifiers as namespaces.

## Troubleshooting Guide
If tests fail or plugins do not load, run `pytest -q` and ensure your environment variables are set. Use `scripts/setup_dev_environment.sh` to prepare a clean environment.
>>>>>>> Stashed changes
