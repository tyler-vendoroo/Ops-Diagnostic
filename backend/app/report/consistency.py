"""Cross-page data consistency checks for Operations Analysis report."""
from __future__ import annotations

import re
from typing import Any

from app.models.report_data import ReportData


def _extract_first_int(text: str) -> int | None:
    match = re.search(r"(\d+)", str(text))
    return int(match.group(1)) if match else None


def validate_report_consistency(report_data: ReportData) -> list[str]:
    """Return a list of cross-page mismatch messages."""
    mismatches: list[str] = []
    wo = report_data.wo_metrics
    if wo is None:
        return ["wo_metrics missing from report data"]

    # Cover stats
    cover_vendor_count = _extract_first_int(report_data.vendor_count)
    if cover_vendor_count != wo.unique_vendors:
        mismatches.append(
            f"Vendor count mismatch: cover={cover_vendor_count}, wo_metrics={wo.unique_vendors}"
        )

    expected_open_rate = f"{wo.open_wo_rate_pct}%"
    if report_data.open_wo_rate != expected_open_rate:
        mismatches.append(
            f"Open WO rate mismatch: cover={report_data.open_wo_rate}, wo_metrics={expected_open_rate}"
        )

    expected_response = (
        f"{wo.avg_first_response_hours} hrs" if wo.avg_first_response_hours is not None else "N/A"
    )
    if report_data.avg_response_time != expected_response:
        mismatches.append(
            f"First response mismatch: cover={report_data.avg_response_time}, wo_metrics={expected_response}"
        )

    expected_monthly = str(int(wo.monthly_avg_work_orders))
    if report_data.monthly_work_orders != expected_monthly:
        mismatches.append(
            f"Monthly WOs mismatch: cover={report_data.monthly_work_orders}, wo_metrics={expected_monthly}"
        )

    # Benchmarks
    for row in report_data.benchmark_rows:
        metric = row.metric.strip().lower()
        if "open work order rate" in metric:
            if row.current_value != expected_open_rate:
                mismatches.append(
                    f"Benchmark open WO mismatch: benchmark={row.current_value}, wo_metrics={expected_open_rate}"
                )
        if "vendor coverage" in metric:
            expected_vendor_cov = f"{wo.trades_covered_count}/{wo.trades_required_count} trades"
            if row.current_value != expected_vendor_cov:
                mismatches.append(
                    f"Benchmark vendor coverage mismatch: benchmark={row.current_value}, wo_metrics={expected_vendor_cov}"
                )
        if "first response" in metric:
            if row.current_value != expected_response:
                mismatches.append(
                    f"Benchmark first response mismatch: benchmark={row.current_value}, wo_metrics={expected_response}"
                )

    # Impact rows
    for row in report_data.impact_rows:
        metric = row.metric.strip().lower()
        if "first response" in metric and row.current_value != expected_response:
            mismatches.append(
                f"Impact first response mismatch: impact={row.current_value}, wo_metrics={expected_response}"
            )
        if "open wo rate" in metric and row.current_value != expected_open_rate:
            mismatches.append(
                f"Impact open WO mismatch: impact={row.current_value}, wo_metrics={expected_open_rate}"
            )
        if "vendor coverage" in metric:
            expected_vendor_cov = f"{wo.trades_covered_count}/{wo.trades_required_count} trades"
            if row.current_value != expected_vendor_cov:
                mismatches.append(
                    f"Impact vendor coverage mismatch: impact={row.current_value}, wo_metrics={expected_vendor_cov}"
                )

    # Gaps: check numbers where expected to appear
    for gap in report_data.gaps:
        title = gap.title.strip().lower()
        detail = gap.detail
        if "vendor coverage" in title:
            expected_vendor_count = str(wo.unique_vendors)
            if expected_vendor_count not in detail:
                mismatches.append(
                    f"Gap vendor count mismatch: expected vendor count {expected_vendor_count} in '{gap.title}' detail"
                )
            expected_cov = f"{wo.trades_covered_count} of {wo.trades_required_count}"
            if expected_cov not in detail:
                mismatches.append(
                    f"Gap trade coverage mismatch: expected '{expected_cov}' in '{gap.title}' detail"
                )
        if "response time" in title and wo.avg_first_response_hours is not None:
            expected_hours = str(wo.avg_first_response_hours)
            if expected_hours not in detail:
                mismatches.append(
                    f"Gap response mismatch: expected {expected_hours} in '{gap.title}' detail"
                )
        if "after hours" in title:
            expected_after = str(wo.after_hours_pct)
            if expected_after and expected_after not in detail and expected_after not in gap.recommendation:
                mismatches.append(
                    f"Gap after-hours mismatch: expected {expected_after}% reference in '{gap.title}'"
                )

    return mismatches

