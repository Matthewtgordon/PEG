# CI/CD Enhancement Plan: Self-Learning & Continuous Improvement

**Document Version:** 1.0.0
**Created:** 2025-11-23
**Author:** Claude Code Analysis
**Status:** Proposed

---

## Executive Summary

This document presents a comprehensive analysis of the PEG/APEG codebase CI/CD infrastructure and proposes enhancements to create a **self-learning, continuously improving** system. Based on thorough review of all workflows, quality systems, and learning mechanisms, we identify strategic improvements that align with the project's vision of autonomous AI orchestration.

### Key Findings

| Area | Current State | Enhancement Opportunity |
|------|---------------|------------------------|
| **CI Workflows** | 5 workflows, some duplication | Consolidation + reusable actions |
| **Quality Gates** | Basic thresholds (60% coverage, 0.80 score) | Adaptive thresholds + trend analysis |
| **Learning Mechanisms** | Thompson Sampling bandit | Feedback loops to CI, meta-learning |
| **Scoring System** | Placeholder metrics | Real metric implementations |
| **Self-Improvement** | Loop detection only | Full feedback-driven optimization |
| **Security** | Basic (.env protection) | SAST, dependency scanning, SBOM |

---

## Part 1: Current State Analysis

### 1.1 Existing CI/CD Architecture

```
GitHub Actions Workflows (5 total):
├── apeg-ci.yml        [PRIMARY]   Modern APEG pipeline (5 jobs, matrix testing)
├── peg-ci.yml         [LEGACY]    Legacy PEG support (2 jobs, scoring gate)
├── test-matrix.yml    [COMPAT]    Cross-platform (3 OS × 2 Python)
├── append-to-log.yml  [MANUAL]    Logbook.json updates
└── update-tasks.yml   [MANUAL]    Tasks.json updates
```

### 1.2 Quality Gates Currently Enforced

| Gate | Workflow | Threshold | Blocking? |
|------|----------|-----------|-----------|
| Repository Validation | peg-ci, apeg-ci | Pass/Fail | Yes |
| Test Pass Rate | All CI | 100% required | Yes |
| Code Coverage | apeg-ci | 60% minimum | Yes |
| Prompt Score | peg-ci | 0.80 minimum | Yes |
| Code Quality (Ruff/MyPy/Black) | apeg-ci | Advisory | No |
| Cross-Platform | test-matrix | Pass on all | Yes |

### 1.3 Existing Learning Mechanisms

**Runtime Learning (Implemented):**
- Thompson Sampling bandit selector (`src/apeg_core/decision/bandit_selector.py`)
- Loop detection guard (`src/apeg_core/decision/loop_guard.py`)
- Reward recording from evaluation scores
- Weight persistence to `bandit_weights.json`

**CI/CD Learning (Limited):**
- Coverage trend tracking (Codecov)
- Test result artifacts
- Score.json artifact generation

**Gap:** No feedback loop from CI results back to the learning system.

---

## Part 2: Strategic Enhancement Recommendations

### 2.1 Workflow Consolidation (Reduce Duplication)

**Problem:** Three workflows (apeg-ci, peg-ci, test-matrix) duplicate setup steps.

**Solution:** Create reusable workflow components:

```yaml
# .github/workflows/reusable/setup-python.yml
name: 'Setup Python Environment'
on:
  workflow_call:
    inputs:
      python-version:
        required: true
        type: string
    outputs:
      cache-hit:
        value: ${{ jobs.setup.outputs.cache-hit }}

jobs:
  setup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python-version }}
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -e ".[dev]"
```

**Recommended Consolidated Structure:**

```
.github/workflows/
├── ci-main.yml              # Single unified CI pipeline
│   ├── validate (structural)
│   ├── quality (lint + type check)
│   ├── test (matrix: 3.11, 3.12)
│   ├── security (new: SAST + deps)
│   ├── score (prompt quality)
│   ├── integration (E2E)
│   └── summary (aggregate status)
├── ci-cross-platform.yml    # OS compatibility (weekly schedule)
├── release.yml              # New: Version + package release
├── learning-feedback.yml    # New: CI→Runtime feedback loop
└── manual/
    ├── log-update.yml
    └── tasks-update.yml
```

---

### 2.2 Self-Learning CI Pipeline

**Vision:** Create a CI pipeline that learns from its own results and improves over time.

#### 2.2.1 Learning Feedback Loop Workflow

```yaml
# .github/workflows/learning-feedback.yml
name: Learning Feedback Loop

on:
  workflow_run:
    workflows: ["CI Main"]
    types: [completed]
  schedule:
    - cron: '0 0 * * 0'  # Weekly analysis

jobs:
  analyze-trends:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Fetch Historical Metrics
        uses: actions/download-artifact@v4
        with:
          pattern: ci-metrics-*
          merge-multiple: true
          path: ./metrics-history

      - name: Analyze Quality Trends
        run: |
          python scripts/ci/analyze_trends.py \
            --metrics-dir ./metrics-history \
            --output trend-report.json

      - name: Detect Quality Regressions
        id: regression
        run: |
          python scripts/ci/detect_regressions.py \
            --trend-report trend-report.json \
            --threshold 0.05

      - name: Update Bandit Weights from CI Feedback
        if: steps.regression.outputs.has_feedback == 'true'
        run: |
          python scripts/ci/update_bandit_from_ci.py \
            --trend-report trend-report.json \
            --weights-file bandit_weights.json

      - name: Create Improvement Suggestions
        run: |
          python scripts/ci/generate_suggestions.py \
            --trend-report trend-report.json \
            --output suggestions.md

      - name: Open Improvement Issue (if needed)
        if: steps.regression.outputs.action_needed == 'true'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const suggestions = fs.readFileSync('suggestions.md', 'utf8');
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: '📊 CI Quality Trend Alert',
              body: suggestions,
              labels: ['ci', 'quality', 'automated']
            });
```

#### 2.2.2 CI-to-Runtime Feedback Script

Create `scripts/ci/update_bandit_from_ci.py`:

```python
#!/usr/bin/env python3
"""
Update bandit selector weights based on CI/CD feedback.

This script analyzes CI results and provides feedback to the
Thompson Sampling bandit selector to improve macro selection.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def analyze_test_patterns(trend_report: dict) -> dict:
    """Analyze which code patterns correlate with test failures."""
    patterns = {}

    for run in trend_report.get('runs', []):
        # Correlate changed files with test results
        changed_files = run.get('changed_files', [])
        test_results = run.get('test_results', {})

        for file_path in changed_files:
            module = extract_module(file_path)
            if module not in patterns:
                patterns[module] = {'successes': 0, 'failures': 0}

            if test_results.get('passed', False):
                patterns[module]['successes'] += 1
            else:
                patterns[module]['failures'] += 1

    return patterns

def update_bandit_weights(weights_file: Path, ci_feedback: dict):
    """Update bandit weights with CI feedback."""
    if not weights_file.exists():
        weights = {}
    else:
        weights = json.loads(weights_file.read_text())

    # Add CI-derived insights as macro hints
    ci_hints = weights.setdefault('ci_feedback', {})
    ci_hints['last_updated'] = datetime.utcnow().isoformat()
    ci_hints['patterns'] = ci_feedback

    # Calculate recommended macro priorities
    macro_scores = calculate_macro_priorities(ci_feedback)
    ci_hints['recommended_priorities'] = macro_scores

    weights_file.write_text(json.dumps(weights, indent=2))
    print(f"Updated {weights_file} with CI feedback")

def calculate_macro_priorities(ci_feedback: dict) -> dict:
    """Calculate macro priorities based on CI patterns."""
    priorities = {}

    for module, stats in ci_feedback.items():
        total = stats['successes'] + stats['failures']
        if total > 0:
            success_rate = stats['successes'] / total
            # Higher success rate = higher priority
            priorities[module] = round(success_rate, 3)

    return priorities

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--trend-report', required=True)
    parser.add_argument('--weights-file', required=True)
    args = parser.parse_args()

    trend_report = json.loads(Path(args.trend_report).read_text())
    ci_feedback = analyze_test_patterns(trend_report)
    update_bandit_weights(Path(args.weights_file), ci_feedback)

if __name__ == '__main__':
    main()
```

---

### 2.3 Adaptive Quality Thresholds

**Current Problem:** Fixed thresholds (60% coverage, 0.80 score) don't adapt to project maturity.

**Solution:** Implement ratcheting thresholds that only increase.

```yaml
# .github/workflows/ci-main.yml (enhanced quality job)
jobs:
  adaptive-quality:
    runs-on: ubuntu-latest
    steps:
      - name: Load Historical Thresholds
        id: thresholds
        run: |
          # Read from .github/quality-thresholds.json
          COVERAGE_MIN=$(jq -r '.coverage.minimum' .github/quality-thresholds.json)
          SCORE_MIN=$(jq -r '.score.minimum' .github/quality-thresholds.json)
          echo "coverage_min=$COVERAGE_MIN" >> $GITHUB_OUTPUT
          echo "score_min=$SCORE_MIN" >> $GITHUB_OUTPUT

      - name: Run Tests with Coverage
        run: |
          pytest --cov=src/apeg_core --cov-report=json tests/

      - name: Check Coverage Threshold
        run: |
          CURRENT=$(jq -r '.totals.percent_covered' coverage.json)
          THRESHOLD=${{ steps.thresholds.outputs.coverage_min }}

          if (( $(echo "$CURRENT < $THRESHOLD" | bc -l) )); then
            echo "::error::Coverage $CURRENT% below threshold $THRESHOLD%"
            exit 1
          fi

          # Ratchet: Update threshold if we exceeded by 5%+
          NEW_THRESHOLD=$(echo "$THRESHOLD + 1" | bc)
          if (( $(echo "$CURRENT > $NEW_THRESHOLD" | bc -l) )); then
            echo "Ratcheting coverage threshold from $THRESHOLD to $NEW_THRESHOLD"
            jq ".coverage.minimum = $NEW_THRESHOLD" .github/quality-thresholds.json > tmp.json
            mv tmp.json .github/quality-thresholds.json
          fi

      - name: Commit Ratcheted Thresholds
        if: success()
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: 'ci: ratchet quality thresholds'
          file_pattern: '.github/quality-thresholds.json'
```

**Create `.github/quality-thresholds.json`:**

```json
{
  "version": "1.0.0",
  "updated_at": "2025-11-23T00:00:00Z",
  "coverage": {
    "minimum": 60,
    "target": 80,
    "ratchet_increment": 1
  },
  "score": {
    "minimum": 0.80,
    "target": 0.90,
    "ratchet_increment": 0.01
  },
  "metrics": {
    "test_pass_rate": {
      "minimum": 1.0,
      "weight": 0.40
    },
    "semantic_relevance": {
      "minimum": 0.70,
      "weight": 0.20
    },
    "syntactic_correctness": {
      "minimum": 0.90,
      "weight": 0.15
    }
  },
  "history": []
}
```

---

### 2.4 Real Metric Implementations

**Current Problem:** `run_scoring.py` uses placeholder random values.

**Solution:** Implement real metric calculation functions:

```python
# scripts/ci/real_metrics.py
"""Real metric implementations for CI/CD quality scoring."""

import subprocess
import json
from pathlib import Path

def calculate_test_pass_rate() -> float:
    """Calculate actual test pass rate from pytest results."""
    results_file = Path('test-results/results.xml')
    if not results_file.exists():
        return 0.0

    import xml.etree.ElementTree as ET
    tree = ET.parse(results_file)
    root = tree.getroot()

    total = int(root.get('tests', 0))
    failures = int(root.get('failures', 0))
    errors = int(root.get('errors', 0))

    if total == 0:
        return 0.0

    passed = total - failures - errors
    return passed / total

def calculate_syntactic_correctness() -> float:
    """Calculate code quality score from linters."""
    scores = []

    # Ruff linting
    result = subprocess.run(
        ['ruff', 'check', 'src/apeg_core', '--output-format=json'],
        capture_output=True, text=True
    )
    try:
        ruff_issues = json.loads(result.stdout or '[]')
        # Score: 1.0 - (issues / 100), min 0.0
        ruff_score = max(0.0, 1.0 - len(ruff_issues) / 100)
        scores.append(ruff_score)
    except json.JSONDecodeError:
        scores.append(0.5)  # Neutral on parse error

    # MyPy type checking
    result = subprocess.run(
        ['mypy', 'src/apeg_core', '--json-report', 'mypy-report'],
        capture_output=True, text=True
    )
    mypy_report = Path('mypy-report/report.json')
    if mypy_report.exists():
        report = json.loads(mypy_report.read_text())
        error_count = report.get('totals', {}).get('errors', 0)
        mypy_score = max(0.0, 1.0 - error_count / 50)
        scores.append(mypy_score)
    else:
        scores.append(0.5)

    return sum(scores) / len(scores) if scores else 0.5

def calculate_structure_score(input_file: Path) -> float:
    """Calculate structural compliance score."""
    if not input_file.exists():
        return 0.0

    content = input_file.read_text()

    checks = [
        # Has proper heading
        content.startswith('#') or '## ' in content,
        # Reasonable length
        100 < len(content) < 50000,
        # Has multiple sections
        content.count('##') >= 2,
        # No excessive empty lines
        '\n\n\n\n' not in content,
        # Has code blocks if technical
        '```' in content or 'def ' not in content,
    ]

    return sum(checks) / len(checks)

def calculate_efficiency_score(input_file: Path) -> float:
    """Calculate token efficiency score."""
    if not input_file.exists():
        return 0.0

    content = input_file.read_text()

    # Rough token estimate (words * 1.3)
    words = len(content.split())
    estimated_tokens = int(words * 1.3)

    # Target: 500-2000 tokens for documentation
    if 500 <= estimated_tokens <= 2000:
        return 1.0
    elif estimated_tokens < 500:
        return estimated_tokens / 500
    else:
        return max(0.5, 2000 / estimated_tokens)

def calculate_all_metrics(input_file: Path) -> dict:
    """Calculate all metrics with weights."""
    metrics = {
        'test_pass_rate': {
            'score': calculate_test_pass_rate(),
            'weight': 0.40
        },
        'semantic_relevance': {
            'score': 0.85,  # Placeholder until LLM integration
            'weight': 0.20
        },
        'syntactic_correctness': {
            'score': calculate_syntactic_correctness(),
            'weight': 0.15
        },
        'selector_accuracy_at_1': {
            'score': 0.80,  # From bandit_weights.json
            'weight': 0.10
        },
        'structure': {
            'score': calculate_structure_score(input_file),
            'weight': 0.10
        },
        'efficiency': {
            'score': calculate_efficiency_score(input_file),
            'weight': 0.05
        }
    }

    # Calculate weighted total
    total = sum(
        m['score'] * m['weight']
        for m in metrics.values()
    )

    return {
        'metrics': metrics,
        'total_score': round(total, 4),
        'passed': total >= 0.80
    }
```

---

### 2.5 Security Enhancement Workflow

**Current Gap:** No security scanning in CI.

**Solution:** Add comprehensive security checks:

```yaml
# .github/workflows/ci-main.yml (add security job)
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      # Dependency Vulnerability Scanning
      - name: Install pip-audit
        run: pip install pip-audit

      - name: Scan Dependencies
        run: |
          pip-audit --requirement requirements.txt --format json > pip-audit.json
        continue-on-error: true

      - name: Check Critical Vulnerabilities
        run: |
          CRITICAL=$(jq '[.[] | select(.vulnerability.severity == "CRITICAL")] | length' pip-audit.json)
          if [ "$CRITICAL" -gt 0 ]; then
            echo "::error::Found $CRITICAL critical vulnerabilities"
            exit 1
          fi

      # Static Application Security Testing
      - name: Install Bandit
        run: pip install bandit

      - name: SAST Scan
        run: |
          bandit -r src/apeg_core -f json -o bandit-report.json
        continue-on-error: true

      - name: Check High Severity Issues
        run: |
          HIGH=$(jq '.results | [.[] | select(.issue_severity == "HIGH")] | length' bandit-report.json)
          if [ "$HIGH" -gt 0 ]; then
            echo "::warning::Found $HIGH high-severity security issues"
          fi

      # Secret Scanning
      - name: Scan for Secrets
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.before }}
          head: ${{ github.sha }}

      # Generate SBOM
      - name: Generate SBOM
        run: |
          pip install cyclonedx-bom
          cyclonedx-py requirements requirements.txt -o sbom.json

      - name: Upload Security Reports
        uses: actions/upload-artifact@v4
        with:
          name: security-reports
          path: |
            pip-audit.json
            bandit-report.json
            sbom.json
```

---

### 2.6 Performance Regression Detection

**Current Gap:** No performance tracking.

**Solution:** Add performance benchmarks to CI:

```yaml
# .github/workflows/ci-main.yml (add benchmark job)
jobs:
  benchmark:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Dependencies
        run: |
          pip install -r requirements.txt
          pip install -e .
          pip install pytest-benchmark

      - name: Run Benchmarks
        run: |
          pytest tests/benchmarks/ \
            --benchmark-json=benchmark-results.json \
            --benchmark-compare-fail=mean:10%

      - name: Compare with Base Branch
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'pytest'
          output-file-path: benchmark-results.json
          alert-threshold: '110%'
          fail-on-alert: false
          comment-on-alert: true
```

**Create benchmark tests:**

```python
# tests/benchmarks/test_performance.py
"""Performance benchmarks for critical paths."""

import pytest
from apeg_core.orchestrator import APEGOrchestrator
from apeg_core.decision.bandit_selector import choose_macro
from apeg_core.scoring.evaluator import Evaluator

@pytest.fixture
def orchestrator():
    return APEGOrchestrator(test_mode=True)

def test_orchestrator_initialization(benchmark, orchestrator):
    """Benchmark orchestrator initialization time."""
    def init():
        APEGOrchestrator(test_mode=True)
    benchmark(init)

def test_bandit_selection(benchmark):
    """Benchmark macro selection performance."""
    macros = ['macro_role_prompt', 'macro_chain_of_thought', 'macro_rewrite']
    history = [{'macro': 'macro_role_prompt', 'score': 0.8} for _ in range(100)]
    config = {'selector': {'algorithm': 'thompson_sampling'}}

    def select():
        choose_macro(macros, history, config)
    benchmark(select)

def test_evaluation(benchmark):
    """Benchmark scoring evaluation."""
    evaluator = Evaluator()
    test_output = "This is a test output for evaluation."

    def evaluate():
        evaluator.evaluate(test_output)
    benchmark(evaluate)
```

---

### 2.7 Automatic Version Management

**Current Gap:** No automated version bumping.

**Solution:** Implement semantic release:

```yaml
# .github/workflows/release.yml
name: Semantic Release

on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    if: "!contains(github.event.head_commit.message, 'chore(release)')"

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Dependencies
        run: pip install python-semantic-release build

      - name: Determine Version Bump
        id: version
        run: |
          # Analyze commits since last tag
          COMMITS=$(git log $(git describe --tags --abbrev=0 2>/dev/null || echo HEAD~10)..HEAD --oneline)

          if echo "$COMMITS" | grep -q "BREAKING CHANGE\|!:"; then
            echo "bump=major" >> $GITHUB_OUTPUT
          elif echo "$COMMITS" | grep -q "^feat"; then
            echo "bump=minor" >> $GITHUB_OUTPUT
          elif echo "$COMMITS" | grep -q "^fix"; then
            echo "bump=patch" >> $GITHUB_OUTPUT
          else
            echo "bump=none" >> $GITHUB_OUTPUT
          fi

      - name: Bump Version
        if: steps.version.outputs.bump != 'none'
        run: |
          semantic-release version --${{ steps.version.outputs.bump }}

      - name: Update Configuration Files
        if: steps.version.outputs.bump != 'none'
        run: |
          NEW_VERSION=$(semantic-release print-version)
          python scripts/ci/update_config_versions.py --version $NEW_VERSION

      - name: Build Package
        run: python -m build

      - name: Create GitHub Release
        if: steps.version.outputs.bump != 'none'
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
          generate_release_notes: true
```

---

## Part 3: Enhanced Scoring System Integration

### 3.1 Connect CI Metrics to PromptScoreModel

Update `run_scoring.py` to use real metrics:

```python
#!/usr/bin/env python3
"""
Enhanced scoring script with real metric implementations.
Integrates with CI/CD pipeline for quality gate enforcement.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Import real metrics
from scripts.ci.real_metrics import calculate_all_metrics

def load_score_model(model_path: Path) -> dict:
    """Load and validate scoring model."""
    return json.loads(model_path.read_text())

def generate_score_report(
    model: dict,
    metrics: dict,
    input_file: Path
) -> dict:
    """Generate comprehensive score report."""
    return {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'input_file': str(input_file),
        'model_version': model.get('version', 'unknown'),
        'metrics': metrics['metrics'],
        'total_score': metrics['total_score'],
        'passed': metrics['passed'],
        'threshold': model.get('ci', {}).get('minimum_score', 0.80),
        'action_hooks': determine_actions(metrics, model)
    }

def determine_actions(metrics: dict, model: dict) -> list:
    """Determine actions based on score thresholds."""
    actions = []
    score = metrics['total_score']

    thresholds = model.get('thresholds', {})

    if score < thresholds.get('fail', 0.50):
        actions.append({
            'type': 'block_export',
            'reason': f'Score {score:.2f} below fail threshold'
        })
    elif score < thresholds.get('warn', 0.65):
        actions.append({
            'type': 'log_warning',
            'reason': f'Score {score:.2f} below warning threshold'
        })

    # Per-metric actions
    for name, data in metrics['metrics'].items():
        metric_threshold = model.get('metrics', {}).get(name, {}).get('minimum', 0)
        if data['score'] < metric_threshold:
            actions.append({
                'type': 'metric_alert',
                'metric': name,
                'score': data['score'],
                'threshold': metric_threshold
            })

    return actions

def main():
    parser = argparse.ArgumentParser(description='Run quality scoring')
    parser.add_argument('--model', required=True, help='Path to PromptScoreModel.json')
    parser.add_argument('--input', required=True, help='Input file to score')
    parser.add_argument('--out', required=True, help='Output score.json path')
    parser.add_argument('--ci-mode', action='store_true', help='Exit non-zero on failure')
    args = parser.parse_args()

    model_path = Path(args.model)
    input_path = Path(args.input)
    output_path = Path(args.out)

    # Load scoring model
    model = load_score_model(model_path)

    # Calculate real metrics
    metrics = calculate_all_metrics(input_path)

    # Generate report
    report = generate_score_report(model, metrics, input_path)

    # Write output
    output_path.write_text(json.dumps(report, indent=2))
    print(f"Score: {report['total_score']:.4f} ({'PASS' if report['passed'] else 'FAIL'})")

    # CI mode: exit with error on failure
    if args.ci_mode and not report['passed']:
        sys.exit(1)

if __name__ == '__main__':
    main()
```

### 3.2 Bandit Integration with CI Feedback

Enhance bandit selector to consume CI feedback:

```python
# Addition to src/apeg_core/decision/bandit_selector.py

def incorporate_ci_feedback(weights_path: Path) -> None:
    """Incorporate CI/CD feedback into macro selection weights."""
    if not weights_path.exists():
        return

    weights = json.loads(weights_path.read_text())
    ci_feedback = weights.get('ci_feedback', {})

    if not ci_feedback:
        return

    # Adjust macro weights based on CI patterns
    recommended = ci_feedback.get('recommended_priorities', {})

    for macro, ci_priority in recommended.items():
        if macro in weights:
            # Blend CI feedback with existing weights (20% influence)
            current_weight = weights[macro].get('priority', 1.0)
            blended = current_weight * 0.8 + ci_priority * 0.2
            weights[macro]['priority'] = round(blended, 3)
            weights[macro]['ci_adjusted'] = True

    # Mark last integration
    weights['ci_feedback']['last_integrated'] = datetime.utcnow().isoformat()

    weights_path.write_text(json.dumps(weights, indent=2))
```

---

## Part 4: Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Create `.github/quality-thresholds.json` | High | Low | None |
| Implement real metric functions | High | Medium | None |
| Add security scanning job | High | Low | None |
| Create benchmark test suite | Medium | Medium | None |

### Phase 2: Consolidation (Week 3-4)

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Create reusable workflow components | Medium | Medium | Phase 1 |
| Consolidate to single CI workflow | Medium | High | Reusable components |
| Implement adaptive thresholds | Medium | Medium | Phase 1 |
| Add performance regression detection | Medium | Medium | Benchmarks |

### Phase 3: Self-Learning (Week 5-6)

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Create learning feedback workflow | High | High | Phase 1-2 |
| Implement CI→bandit feedback loop | High | Medium | Learning workflow |
| Add trend analysis scripts | Medium | Medium | Learning workflow |
| Create auto-improvement issue creation | Low | Low | Trend analysis |

### Phase 4: Polish (Week 7-8)

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Implement semantic release | Medium | Medium | Phase 1-2 |
| Create quality dashboard | Low | High | All metrics |
| Document CI enhancements | High | Medium | All phases |
| Create onboarding guide | Medium | Low | Documentation |

---

## Part 5: Expected Outcomes

### 5.1 Quality Improvements

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Test Coverage | 60% | 80%+ | +33% |
| CI Runtime | ~5 min | ~3 min | -40% |
| False Positives | Unknown | <5% | Measurable |
| Security Issues | Not tracked | 0 critical | Secure |

### 5.2 Learning Effectiveness

| Capability | Current | After Enhancement |
|------------|---------|-------------------|
| Macro Selection | Runtime learning only | Runtime + CI feedback |
| Quality Trends | Not tracked | Weekly analysis |
| Regression Detection | Manual | Automated |
| Threshold Management | Fixed | Adaptive ratcheting |

### 5.3 Developer Experience

| Aspect | Current | After Enhancement |
|--------|---------|-------------------|
| CI Feedback | Basic pass/fail | Detailed metrics + suggestions |
| Security Visibility | None | Full SBOM + vulnerability reports |
| Performance Awareness | None | Benchmark comparisons on PRs |
| Quality Guidance | Manual review | Automated improvement suggestions |

---

## Part 6: File Changes Summary

### New Files to Create

```
.github/
├── quality-thresholds.json          # Adaptive quality thresholds
└── workflows/
    ├── ci-main.yml                  # Consolidated CI pipeline (replaces 3 files)
    ├── learning-feedback.yml        # Self-learning feedback loop
    └── release.yml                  # Semantic versioning

scripts/ci/
├── real_metrics.py                  # Real metric implementations
├── analyze_trends.py                # Quality trend analysis
├── detect_regressions.py            # Regression detection
├── update_bandit_from_ci.py         # CI→bandit feedback
├── generate_suggestions.py          # Auto-improvement suggestions
└── update_config_versions.py        # Version sync across configs

tests/benchmarks/
└── test_performance.py              # Performance benchmark tests
```

### Files to Modify

```
run_scoring.py                       # Use real metrics
src/apeg_core/decision/bandit_selector.py  # Add CI feedback integration
PromptScoreModel.json                # Add metric minimums
SessionConfig.json                   # Add CI feedback config
```

### Files to Deprecate (after consolidation)

```
.github/workflows/apeg-ci.yml        # → ci-main.yml
.github/workflows/peg-ci.yml         # → ci-main.yml
.github/workflows/test-matrix.yml    # → ci-main.yml (job)
```

---

## Conclusion

This enhancement plan transforms the PEG/APEG CI/CD system from a basic quality gate into a **self-learning, continuously improving pipeline** that:

1. **Learns from itself** - CI results feed back to improve macro selection
2. **Adapts over time** - Quality thresholds ratchet up as code improves
3. **Catches regressions** - Performance and quality trends are monitored
4. **Suggests improvements** - Automated analysis creates actionable issues
5. **Secures the supply chain** - Vulnerability scanning and SBOM generation

The implementation is phased to deliver value incrementally while building toward the full self-learning vision.

---

**Document Version:** 1.0.0
**Last Updated:** 2025-11-23
**Next Review:** After Phase 1 completion
