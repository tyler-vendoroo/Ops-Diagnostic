"""Analyze vendor data to compute coverage and network metrics."""
from app.models.input_data import Vendor
from app.models.analysis import VendorMetrics
from app.config import REQUIRED_TRADES


def _normalize_trade(trade: str) -> str:
    """Normalize trade name for comparison."""
    trade = trade.lower().strip()
    # Map common variations
    mappings = {
        "hvac/r": "hvac", "heating": "hvac", "air conditioning": "hvac",
        "ac": "hvac", "heating and cooling": "hvac",
        "electric": "electrical", "electrician": "electrical",
        "plumber": "plumbing", "pipe": "plumbing",
        "handyman": "general handyman", "general": "general handyman",
        "maintenance": "general handyman",
        "exterminator": "pest control", "extermination": "pest control",
        "lawn": "landscaping", "yard": "landscaping", "grounds": "landscaping",
        "lock": "locksmith", "key": "locksmith",
        "roof": "roofing", "roofer": "roofing",
        "paint": "painting", "painter": "painting",
        "floor": "flooring", "carpet": "flooring",
        "appliance": "appliance repair", "appliances": "appliance repair",
        "clean": "cleaning", "janitorial": "cleaning", "maid": "cleaning",
    }
    for key, value in mappings.items():
        if key in trade:
            return value
    return trade


def analyze_vendors(vendors: list[Vendor]) -> VendorMetrics:
    """Compute vendor coverage metrics.

    Args:
        vendors: List of parsed vendor records

    Returns:
        VendorMetrics with computed values
    """
    if not vendors:
        return VendorMetrics()

    active_vendors = [v for v in vendors if v.active]
    total = len(active_vendors)

    # Trade coverage analysis
    trade_map: dict[str, list[str]] = {}  # normalized_trade → [vendor_names]
    for v in active_vendors:
        if v.trade:
            norm = _normalize_trade(v.trade)
            trade_map.setdefault(norm, []).append(v.vendor_name)

    trades_covered = sorted(trade_map.keys())
    unique_trades = len(trades_covered)

    # Check against required trades
    required_normalized = [t.lower() for t in REQUIRED_TRADES]
    covered_set = set(trades_covered)
    trades_missing = [t for t in REQUIRED_TRADES if t.lower() not in covered_set]

    # Trades with backup (2+ vendors)
    trades_with_backup = sum(1 for vendors_list in trade_map.values() if len(vendors_list) >= 2)

    # Vendor concentration (Herfindahl index)
    # Based on assignment counts if available, otherwise assume equal
    total_assignments = sum(v.assignment_count or 1 for v in active_vendors)
    if total_assignments > 0:
        shares = [(v.assignment_count or 1) / total_assignments for v in active_vendors]
        hhi = sum(s ** 2 for s in shares)
    else:
        hhi = 1.0 / max(1, total)  # Equal distribution

    # Contact completeness
    has_contact = sum(
        1 for v in active_vendors
        if (v.phone and v.phone.strip()) or (v.email and v.email.strip())
    )
    contact_pct = (has_contact / total * 100) if total else 0

    return VendorMetrics(
        total_vendors=total,
        unique_trades=unique_trades,
        trades_covered=trades_covered,
        trades_missing=trades_missing,
        trades_with_backup=trades_with_backup,
        vendor_concentration_index=round(hhi, 3),
        contact_completeness_pct=round(contact_pct, 1),
    )
