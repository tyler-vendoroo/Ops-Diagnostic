"""Two-layer validation for deterministic metrics and AI outputs."""
from __future__ import annotations

import re
from typing import Any

from app.models.analysis import CategoryScore, DocumentAnalysis, GapFinding, KeyFinding, WorkOrderMetrics, ImpactProjection


def build_metrics_layer(
    wo_metrics: WorkOrderMetrics,
    category_scores: list[CategoryScore],
    overall_score: int,
    projected_score: int,
    recommended_tier: str,
    goal: str,
    cost_monthly: float,
    gaps: list[GapFinding],
    impact_rows: list[ImpactProjection],
    vendor_merged: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic metrics payload for validation and reporting."""
    scores = {cat.key: cat.score for cat in category_scores}
    scores["overall"] = overall_score
    scores["projected"] = projected_score

    projections = {}
    for row in impact_rows:
        key = row.metric.lower().replace(" ", "_")
        projections[key] = {
            "current": row.current_value,
            "projected": row.projected_value,
            "improvement": row.improvement,
            "note": row.note,
        }

    metrics_layer = {
        "wo": {
            "total_rows": wo_metrics.total_work_orders,
            "maintenance_wos": wo_metrics.maintenance_wos,
            "filtered_count": wo_metrics.cancelled_count + wo_metrics.inspection_count + wo_metrics.recurring_wos,
            "monthly_avg": wo_metrics.monthly_avg_work_orders,
            "wo_per_door_annual": wo_metrics.wo_per_door_annual,
            "volume_assessment": wo_metrics.volume_assessment,
            "date_range_start": wo_metrics.date_range_start,
            "date_range_end": wo_metrics.date_range_end,
            "date_range_days": wo_metrics.date_range_days,
            "open_wo_count": wo_metrics.open_wo_count,
            "open_wo_rate_pct": wo_metrics.open_wo_rate_pct,
            "median_completion_days": wo_metrics.median_completion_days,
            "avg_first_response_hours": wo_metrics.avg_first_response_hours,
            "response_time_method": wo_metrics.response_time_method,
            "unique_vendors": wo_metrics.unique_vendors,
            "top_vendor_pct": wo_metrics.top_vendor_pct,
            "trades_covered_count": wo_metrics.trades_covered_count,
            "trades_required_count": wo_metrics.trades_required_count,
            "missing_trades": wo_metrics.missing_trades,
            "trade_distribution": wo_metrics.trade_distribution or {},
            "after_hours_pct": wo_metrics.after_hours_pct,
            "after_hours_count": wo_metrics.after_hours_count,
            "emergency_count": wo_metrics.emergency_count,
            "reactive_pct": wo_metrics.reactive_pct,
            "repeat_units": wo_metrics.repeat_units or {},
        },
        "vendor_merged": vendor_merged or {
            "total_vendors": wo_metrics.unique_vendors,
            "trades_covered_count": wo_metrics.trades_covered_count,
            "missing_trades": wo_metrics.missing_trades,
            "single_vendor_trades": [],
            "data_source": "work_orders_only",
        },
        "scores": scores,
        "recommendation": {
            "tier": recommended_tier,
            "goal": goal,
            "cost_monthly": cost_monthly,
            "gaps_addressed": [g.title for g in gaps],
        },
        "projections": projections,
    }
    return metrics_layer


def build_ai_layer(
    operational_signals: list[dict],
    lease_result: dict[str, Any] | None,
    pma_result: dict[str, Any] | None,
    key_findings: list[KeyFinding],
    exec_narrative: str,
    gaps: list[GapFinding],
) -> dict[str, Any]:
    """Build AI layer payload for validation and tracing."""
    return {
        "operational_signals": operational_signals or [],
        "lease_analysis": lease_result or {},
        "pma_analysis": pma_result or {},
        "key_findings": [{"title": f.title, "body": f.description, "color": f.color} for f in key_findings],
        "exec_narrative": exec_narrative or "",
        "gap_recommendations": [
            {"gap": g.title, "severity": g.severity, "detail": g.detail, "advisor_response": g.recommendation}
            for g in gaps
        ],
    }


def validate_metrics(metrics: dict[str, Any], client_info: dict[str, Any]) -> list[str]:
    errors = []
    wo = metrics.get("wo", {})
    trade_distribution = wo.get("trade_distribution", {})
    trade_sum = sum(trade_distribution.values()) if trade_distribution else 0.0
    if abs(trade_sum - 100.0) > 0.2:
        errors.append(f"Trade distribution sums to {trade_sum}%, not 100%")

    required_6 = ["HVAC", "Plumbing", "Electrical", "Handyperson", "Pest Control", "Appliances"]
    for trade in required_6:
        if trade not in trade_distribution:
            errors.append(f"Required trade {trade} missing from distribution")

    door_count = client_info.get("door_count", 0) or 0
    if door_count > 0:
        expected_rate = round((wo.get("open_wo_count", 0) / door_count) * 100, 1)
        actual_rate = wo.get("open_wo_rate_pct")
        if actual_rate is not None and abs(actual_rate - expected_rate) > 0.2:
            errors.append(f"Open WO rate mismatch: {actual_rate} vs expected {expected_rate}")

    if metrics.get("scores", {}).get("projected", 0) <= metrics.get("scores", {}).get("overall", 0):
        errors.append("Projected score must be greater than current score")
    if metrics.get("scores", {}).get("projected", 0) > 95:
        errors.append("Projected score exceeds cap of 95")
    if (wo.get("date_range_days") or 0) < 1:
        errors.append("Date range is zero or negative")
    return errors


def validate_ai_layer(ai_layer: dict[str, Any]) -> list[str]:
    errors = []
    signals = ai_layer.get("operational_signals", [])
    if len(signals) < 4 or len(signals) > 6:
        errors.append(f"Expected 4-6 operational signals, got {len(signals)}")
    for signal in signals:
        title = signal.get("title", "")
        body = signal.get("body", "")
        severity = signal.get("severity")
        if len(title.split()) > 5:
            errors.append(f"Signal title too long: {title}")
        if body.count(".") > 4:
            errors.append(f"Signal body too long: {title}")
        if severity not in ("high", "medium", "low"):
            errors.append(f"Invalid signal severity: {severity}")

    all_text = str(ai_layer).lower()
    if "mold" in all_text and "model" not in all_text:
        errors.append("Found banned term 'mold' in AI output")
    return errors


def validate_cross_layer(metrics: dict[str, Any], ai_layer: dict[str, Any]) -> list[str]:
    """Spot-check AI text references against deterministic metrics."""
    errors = []
    vendor_count = str(metrics.get("vendor_merged", {}).get("total_vendors", ""))
    signals = ai_layer.get("operational_signals", [])
    for signal in signals:
        body = (signal.get("body") or "").lower()
        if "vendor" in body:
            nums = re.findall(r"\d+", signal.get("body") or "")
            if vendor_count and nums and vendor_count not in nums:
                errors.append(f"Signal '{signal.get('title')}' may reference wrong vendor count")
    return errors

