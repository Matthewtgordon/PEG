#!/usr/bin/env python3
"""
Analyze quality trends from historical CI metrics.

This script processes historical CI artifacts to identify patterns,
regressions, and improvement opportunities.
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any


def load_metrics_history(metrics_dir: Path) -> list[dict[str, Any]]:
    """Load all historical metric files from directory."""
    history = []

    if not metrics_dir.exists():
        return history

    for metric_file in sorted(metrics_dir.glob("*.json")):
        try:
            data = json.loads(metric_file.read_text())
            # Add filename as identifier
            data["_source_file"] = metric_file.name
            history.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    return history


def calculate_trend(values: list[float]) -> dict[str, Any]:
    """Calculate trend statistics for a series of values."""
    if len(values) < 2:
        return {
            "direction": "insufficient_data",
            "change": 0,
            "mean": values[0] if values else 0,
            "std_dev": 0,
        }

    # Calculate basic statistics
    mean_val = statistics.mean(values)
    std_dev = statistics.stdev(values) if len(values) > 1 else 0

    # Calculate trend direction (simple linear)
    first_half = values[: len(values) // 2]
    second_half = values[len(values) // 2 :]

    first_avg = statistics.mean(first_half) if first_half else 0
    second_avg = statistics.mean(second_half) if second_half else 0

    change = second_avg - first_avg

    if abs(change) < 0.01:
        direction = "stable"
    elif change > 0:
        direction = "improving"
    else:
        direction = "declining"

    return {
        "direction": direction,
        "change": round(change, 4),
        "mean": round(mean_val, 4),
        "std_dev": round(std_dev, 4),
        "latest": values[-1] if values else 0,
        "min": min(values) if values else 0,
        "max": max(values) if values else 0,
    }


def analyze_metric_trends(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze trends for each metric across history."""
    # Extract metric values per metric name
    metric_series: dict[str, list[float]] = {}

    for run in history:
        metrics = run.get("metrics", {})
        for metric_name, metric_data in metrics.items():
            if metric_name not in metric_series:
                metric_series[metric_name] = []

            score = metric_data.get("score", 0) if isinstance(metric_data, dict) else 0
            metric_series[metric_name].append(score)

    # Calculate trend for each metric
    trends = {}
    for metric_name, values in metric_series.items():
        trends[metric_name] = calculate_trend(values)

    return trends


def detect_anomalies(history: list[dict[str, Any]], threshold: float = 2.0) -> list[dict[str, Any]]:
    """Detect anomalous runs based on score deviation."""
    anomalies = []

    if len(history) < 3:
        return anomalies

    # Calculate baseline from historical scores
    scores = [run.get("total_score", 0) for run in history]
    mean_score = statistics.mean(scores)
    std_dev = statistics.stdev(scores) if len(scores) > 1 else 0

    for i, run in enumerate(history):
        score = run.get("total_score", 0)
        if std_dev > 0:
            z_score = (score - mean_score) / std_dev
            if abs(z_score) > threshold:
                anomalies.append({
                    "index": i,
                    "source": run.get("_source_file", "unknown"),
                    "score": score,
                    "z_score": round(z_score, 2),
                    "type": "low" if z_score < 0 else "high",
                })

    return anomalies


def generate_suggestions(trends: dict[str, Any], anomalies: list[dict[str, Any]]) -> list[str]:
    """Generate actionable improvement suggestions."""
    suggestions = []

    # Check declining metrics
    for metric_name, trend in trends.items():
        if trend.get("direction") == "declining":
            change = abs(trend.get("change", 0))
            suggestions.append(
                f"- **{metric_name}**: Declining trend detected (change: -{change:.2%}). "
                f"Consider investigating recent changes affecting this metric."
            )

    # Check high variance metrics
    for metric_name, trend in trends.items():
        std_dev = trend.get("std_dev", 0)
        if std_dev > 0.1:  # High variance threshold
            suggestions.append(
                f"- **{metric_name}**: High variance detected (std_dev: {std_dev:.2%}). "
                f"This metric may need stabilization."
            )

    # Check for consistent low performers
    for metric_name, trend in trends.items():
        mean = trend.get("mean", 1)
        if mean < 0.7:
            suggestions.append(
                f"- **{metric_name}**: Consistently low scores (mean: {mean:.2%}). "
                f"Consider dedicated improvement effort."
            )

    # Anomaly-based suggestions
    low_anomalies = [a for a in anomalies if a.get("type") == "low"]
    if len(low_anomalies) > 2:
        suggestions.append(
            f"- **Quality Stability**: {len(low_anomalies)} anomalously low scores detected. "
            f"Consider reviewing CI stability and test reliability."
        )

    if not suggestions:
        suggestions.append("- All metrics are stable or improving. Continue current practices.")

    return suggestions


def generate_report(
    metrics_dir: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Generate comprehensive trend analysis report."""
    history = load_metrics_history(metrics_dir)

    if not history:
        return {
            "status": "no_data",
            "message": "No historical metrics found for analysis",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    trends = analyze_metric_trends(history)
    anomalies = detect_anomalies(history)
    suggestions = generate_suggestions(trends, anomalies)

    # Calculate overall health score
    improving_count = sum(1 for t in trends.values() if t.get("direction") == "improving")
    declining_count = sum(1 for t in trends.values() if t.get("direction") == "declining")

    if declining_count > improving_count:
        health = "needs_attention"
    elif improving_count > declining_count:
        health = "healthy"
    else:
        health = "stable"

    report = {
        "status": "success",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "data_points": len(history),
        "overall_health": health,
        "trends": trends,
        "anomalies": anomalies,
        "suggestions": suggestions,
        "summary": {
            "improving_metrics": improving_count,
            "declining_metrics": declining_count,
            "stable_metrics": len(trends) - improving_count - declining_count,
            "anomaly_count": len(anomalies),
        },
    }

    # Write report
    output_path.write_text(json.dumps(report, indent=2))
    print(f"Trend report generated: {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Analyze CI quality trends")
    parser.add_argument(
        "--metrics-dir",
        required=True,
        help="Directory containing historical metric JSON files",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for trend report JSON",
    )
    args = parser.parse_args()

    report = generate_report(
        metrics_dir=Path(args.metrics_dir),
        output_path=Path(args.output),
    )

    # Print summary
    print(f"\nOverall Health: {report.get('overall_health', 'unknown')}")
    print(f"Data Points Analyzed: {report.get('data_points', 0)}")

    if suggestions := report.get("suggestions", []):
        print("\nSuggestions:")
        for suggestion in suggestions:
            print(suggestion)


if __name__ == "__main__":
    main()
