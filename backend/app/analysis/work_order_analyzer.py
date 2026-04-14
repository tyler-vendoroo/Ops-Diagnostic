"""Analyze work order data to compute operational metrics."""
from datetime import datetime, timedelta
from typing import Optional
import statistics

from app.models.input_data import WorkOrder
from app.models.analysis import WorkOrderMetrics


def _is_after_hours(dt: datetime) -> bool:
    """Check if a datetime falls outside business hours (M-F 8am-6pm)."""
    if dt.weekday() >= 5:  # Saturday/Sunday
        return True
    return dt.hour < 8 or dt.hour >= 18


def _hours_between(start: datetime, end: datetime) -> float:
    """Calculate hours between two datetimes."""
    return (end - start).total_seconds() / 3600


def _days_between(start: datetime, end: datetime) -> float:
    """Calculate days between two datetimes."""
    return (end - start).total_seconds() / 86400


def analyze_work_orders(work_orders: list[WorkOrder], door_count: int = 0) -> WorkOrderMetrics:
    """Compute metrics from work order data.

    Args:
        work_orders: List of parsed work order records
        door_count: Total doors/units in the portfolio (for open WO rate)

    Returns:
        WorkOrderMetrics with computed values
    """
    if not work_orders:
        return WorkOrderMetrics()

    total = len(work_orders)

    # Date range for monthly average
    dates = [wo.created_date for wo in work_orders]
    min_date = min(dates)
    max_date = max(dates)
    months_span = max(1, (max_date - min_date).days / 30.44)
    monthly_avg = total / months_span

    # Completion times (for closed WOs with both dates)
    completion_days = []
    for wo in work_orders:
        if wo.completed_date and wo.created_date:
            days = _days_between(wo.created_date, wo.completed_date)
            if 0 <= days < 365:  # Sanity check
                completion_days.append(days)

    avg_completion = statistics.median(completion_days) if completion_days else None
    completion_std = statistics.stdev(completion_days) if len(completion_days) > 1 else None

    # First response time — do NOT estimate or guess.
    # The AI-powered analyzer in document_analyzer.py handles this with
    # transparent methodology. The pure-logic module should not produce
    # a made-up number that conflicts with the AI analysis.
    avg_response_hours = None

    # Open work order rate = total open WOs / door count × 100
    # This is a portfolio health metric, not a throughput metric.
    cancelled_statuses = {"cancelled", "voided", "duplicate", "rejected", "withdrawn"}
    completed_statuses = {"completed", "closed", "done", "resolved", "paid", "invoiced", "bill created", "finished"}
    open_count = sum(
        1 for wo in work_orders
        if wo.status.lower().strip() not in completed_statuses
        and wo.status.lower().strip() not in cancelled_statuses
        and wo.completed_date is None
    )
    open_rate = (open_count / door_count * 100) if door_count > 0 else 0.0

    # After-hours percentage
    after_hours_count = sum(1 for wo in work_orders if _is_after_hours(wo.created_date))
    after_hours_pct = (after_hours_count / total * 100) if total else 0

    # Resolved without vendor
    no_vendor_count = sum(
        1 for wo in work_orders
        if wo.completed_date is not None
        and (wo.vendor_name is None or wo.vendor_name.strip() == "")
    )
    completed_count = sum(1 for wo in work_orders if wo.completed_date is not None)
    resolved_no_vendor_pct = (no_vendor_count / completed_count * 100) if completed_count else 0

    return WorkOrderMetrics(
        total_work_orders=total,
        monthly_avg_work_orders=round(monthly_avg, 1),
        avg_first_response_hours=round(avg_response_hours, 1) if avg_response_hours else None,
        median_completion_days=round(avg_completion, 1) if avg_completion else None,
        completed_count=completed_count,
        open_wo_rate_pct=round(open_rate, 1),
        open_wo_count=open_count,
        after_hours_pct=round(after_hours_pct, 1),
        after_hours_count=after_hours_count,
        months_spanned=round(months_span),
        date_range_days=max(1, (max_date - min_date).days),
        internal_count=no_vendor_count,
        internal_pct=round(resolved_no_vendor_pct, 1),
    )
