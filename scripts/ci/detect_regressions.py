#!/usr/bin/env python3
"""
Detect quality regressions from trend analysis.

This script analyzes trend reports to identify actionable regressions
and determines if automated feedback or alerts are needed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_trend_report(report_path: Path) -> dict[str, Any]:
    """Load trend report from JSON file."""
    if not report_path.exists():
        return {}

    try:
        return json.loads(report_path.read_text())
    except json.JSONDecodeError:
        return {}


def detect_metric_regressions(
    trends: dict[str, Any],
    threshold: float = 0.05,
) -> list[dict[str, Any]]:
    """
    Detect significant regressions in individual metrics.

    Args:
        trends: Dictionary of metric trends
        threshold: Minimum change to consider a regression

    Returns:
        List of detected regressions with details
    """
    regressions = []

    for metric_name, trend in trends.items():
        direction = trend.get("direction", "stable")
        change = trend.get("change", 0)
        latest = trend.get("latest", 0)
        mean = trend.get("mean", 0)

        # Declining trend with significant change
        if direction == "declining" and abs(change) >= threshold:
            regressions.append({
                "metric": metric_name,
                "type": "declining_trend",
                "severity": "high" if abs(change) > threshold * 2 else "medium",
                "change": change,
                "latest_score": latest,
                "historical_mean": mean,
                "recommendation": f"Investigate recent changes affecting {metric_name}",
            })

        # Below minimum threshold
        if latest < 0.6:  # Hard-coded minimum acceptable score
            regressions.append({
                "metric": metric_name,
                "type": "below_threshold",
                "severity": "critical" if latest < 0.5 else "high",
                "latest_score": latest,
                "threshold": 0.6,
                "recommendation": f"Immediate attention needed for {metric_name}",
            })

    return regressions


def detect_overall_regression(report: dict[str, Any]) -> dict[str, Any] | None:
    """Detect overall quality regression."""
    summary = report.get("summary", {})
    health = report.get("overall_health", "unknown")

    declining = summary.get("declining_metrics", 0)
    total = declining + summary.get("improving_metrics", 0) + summary.get("stable_metrics", 0)

    if total == 0:
        return None

    # More than half metrics declining = overall regression
    if declining > total / 2:
        return {
            "type": "overall_quality_decline",
            "severity": "critical",
            "declining_count": declining,
            "total_metrics": total,
            "health_status": health,
            "recommendation": "Multiple metrics declining. Review recent changes and test coverage.",
        }

    # High anomaly count
    anomaly_count = summary.get("anomaly_count", 0)
    data_points = report.get("data_points", 1)
    if data_points > 0 and anomaly_count / data_points > 0.2:
        return {
            "type": "quality_instability",
            "severity": "high",
            "anomaly_rate": round(anomaly_count / data_points, 2),
            "recommendation": "High rate of quality anomalies. Investigate CI stability.",
        }

    return None


def determine_actions(
    regressions: list[dict[str, Any]],
    overall: dict[str, Any] | None,
) -> dict[str, Any]:
    """Determine what actions should be taken based on regressions."""
    actions = {
        "has_feedback": len(regressions) > 0 or overall is not None,
        "action_needed": False,
        "create_issue": False,
        "update_bandit": False,
        "alert_level": "none",
    }

    # Check for critical issues
    critical_count = sum(1 for r in regressions if r.get("severity") == "critical")
    high_count = sum(1 for r in regressions if r.get("severity") == "high")

    if critical_count > 0 or (overall and overall.get("severity") == "critical"):
        actions["action_needed"] = True
        actions["create_issue"] = True
        actions["alert_level"] = "critical"
    elif high_count > 1:
        actions["action_needed"] = True
        actions["create_issue"] = True
        actions["alert_level"] = "high"
    elif high_count > 0 or len(regressions) > 2:
        actions["alert_level"] = "medium"
        actions["update_bandit"] = True

    # If any regression, update bandit weights
    if regressions:
        actions["update_bandit"] = True

    return actions


def main():
    parser = argparse.ArgumentParser(description="Detect quality regressions")
    parser.add_argument(
        "--trend-report",
        required=True,
        help="Path to trend analysis report JSON",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.05,
        help="Minimum change threshold for regression detection",
    )
    args = parser.parse_args()

    report = load_trend_report(Path(args.trend_report))

    if not report or report.get("status") != "success":
        print("No valid trend report found")
        # Output for GitHub Actions
        print("::set-output name=has_feedback::false")
        print("::set-output name=action_needed::false")
        sys.exit(0)

    # Detect regressions
    trends = report.get("trends", {})
    regressions = detect_metric_regressions(trends, args.threshold)
    overall = detect_overall_regression(report)

    # Determine actions
    actions = determine_actions(regressions, overall)

    # Output results
    print(f"\nRegression Analysis Results:")
    print(f"  Metric regressions: {len(regressions)}")
    print(f"  Overall regression: {'Yes' if overall else 'No'}")
    print(f"  Alert level: {actions['alert_level']}")

    if regressions:
        print("\nDetected Regressions:")
        for r in regressions:
            print(f"  - {r['metric']}: {r['type']} ({r['severity']})")

    # GitHub Actions outputs
    print(f"\n::set-output name=has_feedback::{str(actions['has_feedback']).lower()}")
    print(f"::set-output name=action_needed::{str(actions['action_needed']).lower()}")
    print(f"::set-output name=create_issue::{str(actions['create_issue']).lower()}")
    print(f"::set-output name=update_bandit::{str(actions['update_bandit']).lower()}")
    print(f"::set-output name=alert_level::{actions['alert_level']}")

    # Write detailed results
    results_path = Path("regression-results.json")
    results_path.write_text(json.dumps({
        "regressions": regressions,
        "overall": overall,
        "actions": actions,
    }, indent=2))

    # Exit with error if critical action needed
    if actions["alert_level"] == "critical":
        sys.exit(1)


if __name__ == "__main__":
    main()
