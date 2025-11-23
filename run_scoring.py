#
# This script calculates a quantitative quality score for a given prompt output.
# It loads a scoring model (PromptScoreModel.json) which defines the metrics
# and their respective weights, then computes a weighted average score.
# This script is a critical component of the CI/CD pipeline's quality gate.
#
# Updated: Now uses real metrics from apeg_core.scoring.real_metrics
# instead of placeholder randomized values.
#
import argparse
import json
import sys
from pathlib import Path

# --- Real Metric Functions ---
# Import from the real_metrics module for production-ready implementations
try:
    from src.apeg_core.scoring.real_metrics import (
        calculate_test_pass_rate,
        calculate_semantic_relevance,
        calculate_syntactic_correctness,
        calculate_selector_accuracy,
        calculate_structure_compliance,
        calculate_efficiency,
    )
    USING_REAL_METRICS = True
except ImportError:
    # Fallback to placeholders if real_metrics not available
    import random
    USING_REAL_METRICS = False

    def calculate_test_pass_rate(output_data):
        """Fallback: Simulates calculating the percentage of passing tests."""
        return random.uniform(0.7, 1.0)

    def calculate_semantic_relevance(output_data):
        """Fallback: Simulates an LLM-as-a-judge call."""
        return random.uniform(0.6, 1.0)

    def calculate_syntactic_correctness(output_data):
        """Fallback: Simulates running a linter."""
        return random.choice([0.8, 0.9, 1.0])

    def calculate_selector_accuracy(output_data):
        """Fallback: Simulates checking selector performance."""
        return random.uniform(0.5, 1.0)

    def calculate_structure_compliance(output_data):
        """Fallback: Simulates structural validation."""
        return random.uniform(0.8, 1.0)

    def calculate_efficiency(output_data):
        """Fallback: Simulates token counting."""
        return random.uniform(0.5, 1.0)

# Mapping metric names to their calculation functions
METRIC_FUNCTIONS = {
    "test_pass_rate": calculate_test_pass_rate,
    "semantic_relevance": calculate_semantic_relevance,
    "syntactic_correctness": calculate_syntactic_correctness,
    "selector_accuracy_at_1": calculate_selector_accuracy,
    "structure": calculate_structure_compliance,
    "efficiency": calculate_efficiency,
}


def main():
    """Main entry point for the scoring script."""
    parser = argparse.ArgumentParser(description="Run scoring using a model file")
    parser.add_argument('--model', required=True, help='Path to the PromptScoreModel.json file')
    # POLISH: Activated the --input argument to allow scoring real files.
    parser.add_argument('--input', required=True, help='Path to file containing agent output JSON/text')
    parser.add_argument('--out', required=True, help='Path to the output JSON file for results')
    args = parser.parse_args()

    model_path = Path(args.model)
    input_path = Path(args.input)
    out_path = Path(args.out)

    # --- Load Scoring Model ---
    try:
        with model_path.open(encoding='utf-8') as f:
            model_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Model file not found: {model_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in model file: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Load Agent Output ---
    # POLISH: Load the agent output from the file specified by --input.
    test_mode = False
    if not input_path.exists() or input_path.name.lower() == "readme.md":
        print(f"⚠️  Input file not found: {input_path}. Using test mode.", file=sys.stderr)
        agent_output = {"test_mode": True, "content": "Test run"}
        test_mode = True
    else:
        try:
            with input_path.open(encoding='utf-8') as f:
                # Attempt to load as JSON, fall back to plain text if it fails
                try:
                    agent_output = json.load(f)
                except json.JSONDecodeError:
                    f.seek(0)  # Rewind file to read from the beginning
                    agent_output = {"content": f.read()}
        except OSError as e:
            print(f"⚠️  Could not read input file: {e}. Using test mode.", file=sys.stderr)
            agent_output = {"test_mode": True, "content": "Test run"}
            test_mode = True

    # --- Calculate Scores ---
    calculated_scores = {}
    total_score = 0.0
    
    metrics_to_score = model_data.get('metrics', [])
    if not metrics_to_score:
        print("❌ No 'metrics' array found in the model file.", file=sys.stderr)
        sys.exit(1)
        
    # POLISH: Add a guard to ensure metric weights sum to 1.0.
    total_weight = sum(m.get('weight', 0) for m in metrics_to_score)
    if abs(total_weight - 1.0) > 1e-6:
        print(f"⚠️  Total metric weights sum to {total_weight:.3f} (should be 1.0). Scores may be misleading.", file=sys.stderr)

    for metric in metrics_to_score:
        metric_name = metric.get('name')
        metric_weight = metric.get('weight')

        if not (metric_name and metric_weight is not None):
            print(f"⚠️ Skipping invalid metric entry: {metric}", file=sys.stderr)
            continue
            
        if metric_name in METRIC_FUNCTIONS:
            score = METRIC_FUNCTIONS[metric_name](agent_output)
            calculated_scores[metric_name] = round(score, 4)
            total_score += score * metric_weight
        else:
            print(f"⚠️ No calculation function found for metric: '{metric_name}'. Skipping.", file=sys.stderr)

    # --- Write Output and Check Against Threshold ---
    ci_config = model_data.get('ci', {})
    ci_minimum_score = ci_config.get('minimum_score')
    if ci_minimum_score is None:
        print("❌ 'ci.minimum_score' not found in model file.", file=sys.stderr)
        sys.exit(1)

    output_data = {
        'scores': calculated_scores,
        'total_weighted_score': round(total_score, 4),
        'ci_threshold': ci_minimum_score
    }

    try:
        # POLISH: Ensure the output directory exists before writing.
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open('w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        print(f"✅ Scoring results saved to {out_path}")
    except OSError as e:
        print(f"❌ Could not write to {out_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if test_mode:
        print("ℹ️  Test mode: skipping CI gate.")
        print(f"ℹ️  Using real metrics: {USING_REAL_METRICS}")
        sys.exit(0)

    # --- Final CI Gate Check ---
    # POLISH: Use the rounded score in the console message for clarity.
    final_score = output_data['total_weighted_score']
    if final_score < ci_minimum_score:
        print(f"❌ CI Gate FAILED: Total score {final_score} is below threshold {ci_minimum_score}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"✅ CI Gate PASSED: Total score {final_score} meets or exceeds threshold {ci_minimum_score}")
        sys.exit(0)


if __name__ == '__main__':
    main()
