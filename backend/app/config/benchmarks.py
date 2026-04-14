"""Vendoroo benchmark data by operational model and portfolio size.

Benchmarks are derived from Vendoroo client performance data.
Segmented by operational model and door count range.
Updated quarterly by CS/Ops team.
"""

# Vendoroo average benchmarks (median across all clients)
VENDOROO_AVG = {
    "va": {  # VA/Coordinator model
        "avg_first_response_minutes": 10,
        "avg_completion_days": 3.0,
        "open_wo_rate_pct": 9.8,
        "resident_satisfaction_pct": 94,
        "resolved_without_vendor_pct": 9.6,
        "doors_per_coordinator": 350,
        "completion_decrease_pct": 37.5,
    },
    "tech": {  # Technician model
        "avg_first_response_minutes": 15,
        "avg_completion_days": 2.5,
        "open_wo_rate_pct": 8.5,
        "resident_satisfaction_pct": 95,
        "resolved_without_vendor_pct": 15.0,
        "doors_per_tech": 200,
        "completion_decrease_pct": 40.0,
    },
    "pod": {  # Pod model (small team: PM + coordinator, sometimes tech)
        "avg_first_response_minutes": 10,
        "avg_completion_days": 3.0,
        "open_wo_rate_pct": 9.8,
        "resident_satisfaction_pct": 94,
        "resolved_without_vendor_pct": 9.6,
        "doors_per_pod": 550,
        "completion_decrease_pct": 37.5,
    },
}

# Top performer benchmarks (90th percentile)
TOP_PERFORMERS = {
    "va": {
        "avg_first_response_minutes": 10,
        "avg_completion_days": 2.0,
        "open_wo_rate_pct": 5.0,
        "resident_satisfaction_pct": 98,
        "resolved_without_vendor_pct": 15.0,
        "completion_decrease_pct": 50.0,
    },
    "tech": {
        "avg_first_response_minutes": 10,
        "avg_completion_days": 1.5,
        "open_wo_rate_pct": 4.0,
        "resident_satisfaction_pct": 98,
        "resolved_without_vendor_pct": 20.0,
        "completion_decrease_pct": 55.0,
    },
    "pod": {
        "avg_first_response_minutes": 10,
        "avg_completion_days": 2.0,
        "open_wo_rate_pct": 5.0,
        "resident_satisfaction_pct": 98,
        "resolved_without_vendor_pct": 15.0,
        "completion_decrease_pct": 50.0,
    },
}

# Doors-per-staff benchmarks by model (used for staffing projections)
STAFFING_BENCHMARKS = {
    "va": {
        "current_benchmark": 175,     # Industry average doors/coordinator
        "vendoroo_benchmark": 350,    # With Vendoroo AI coordination
    },
    "tech": {
        "current_benchmark": 120,
        "vendoroo_benchmark": 250,
    },
    "pod": {
        "current_benchmark": 300,     # Industry average doors/pod
        "current_ratio": 300,         # Doors per pod currently
        "vendoroo_benchmark": 550,    # With Vendoroo AI coordination
        "vendoroo_ratio": 550,        # Doors per pod with Vendoroo
        "top_performer_ratio": 600,   # Top performers doors/pod
    },
}

# Portfolio size bucket thresholds
SIZE_BUCKETS = {
    "small": (0, 200),
    "medium": (200, 500),
    "large": (500, 1000),
    "enterprise": (1000, float("inf")),
}

def get_size_bucket(door_count: int) -> str:
    """Return the portfolio size bucket for a given door count."""
    for bucket, (low, high) in SIZE_BUCKETS.items():
        if low <= door_count < high:
            return bucket
    return "enterprise"
