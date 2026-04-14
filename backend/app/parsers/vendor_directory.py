"""Vendor Directory Processor.

Processes an optional vendor directory upload to enrich the WO processor output.
Answers questions WO data can't: which vendors are available (not just dispatched),
which trades have backup coverage, and where single points of failure exist.

The vendor directory SUPPLEMENTS the WO processor — it never replaces it.
"""

import pandas as pd
import numpy as np

from app.parsers.column_mapper import auto_load
from app.parsers.pms_mappings import CATEGORY_NORMALIZE
from app.utils.date_parsing import auto_parse_dates


# ── Required trades (same as WO processor) ───────────────────
REQUIRED_TRADES_12 = [
    "Plumbing", "Electrical", "Rooter/Drain", "Appliance Repair",
    "General Handyman", "HVAC", "Roofing", "Pest Control",
    "Landscaping", "Locksmith", "Cleaning Service", "Flooring",
]


# ── Vendor Directory Column Aliases ──────────────────────────
VENDOR_COLUMN_ALIASES = {
    # vendor_name
    "vendor name":          "vendor_name",
    "vendor":               "vendor_name",
    "name":                 "vendor_name",
    "company":              "vendor_name",
    "company name":         "vendor_name",
    "contractor":           "vendor_name",
    "contractor name":      "vendor_name",
    "business name":        "vendor_name",
    "service provider":     "vendor_name",
    "provider":             "vendor_name",
    "provider name":        "vendor_name",
    "dba":                  "vendor_name",

    # trade
    "trade":                "trade",
    "trade type":           "trade",
    "vendor trade":         "trade",
    "service type":         "trade",
    "category":             "trade",
    "specialty":            "trade",
    "service category":     "trade",
    "work type":            "trade",
    "trade/specialty":      "trade",
    "type of service":      "trade",
    "services":             "trade",
    "skill":                "trade",
    "discipline":           "trade",
    "maintenance category": "trade",

    # phone
    "phone":                "phone",
    "phone number":         "phone",
    "telephone":            "phone",
    "mobile":               "phone",
    "cell":                 "phone",
    "contact phone":        "phone",
    "work phone":           "phone",
    "primary phone":        "phone",

    # email
    "email":                "email",
    "email address":        "email",
    "e-mail":               "email",
    "contact email":        "email",

    # insurance_exp
    "insurance expiration": "insurance_exp",
    "insurance exp":        "insurance_exp",
    "ins expiration":       "insurance_exp",
    "insurance expires":    "insurance_exp",
    "coi expiration":       "insurance_exp",
    "coi exp":              "insurance_exp",
    "insurance":            "insurance_exp",
    "gl expiration":        "insurance_exp",
    "wc expiration":        "insurance_exp",

    # license
    "license":              "license",
    "license number":       "license",
    "license #":            "license",
    "contractor license":   "license",
    "certification":        "license",
    "cert #":               "license",

    # preferred
    "preferred":            "preferred",
    "tier":                 "preferred",
    "priority":             "preferred",
    "designation":          "preferred",
    "vendor tier":          "preferred",
    "backup":               "preferred",
    "primary":              "preferred",
    "rank":                 "preferred",
    "preferred vendor":     "preferred",

    # service_area
    "service area":         "service_area",
    "properties":           "service_area",
    "assigned properties":  "service_area",
    "coverage area":        "service_area",
    "region":               "service_area",
    "zone":                 "service_area",
    "territory":            "service_area",

    # nte
    "nte":                  "nte",
    "not to exceed":        "nte",
    "max amount":           "nte",
    "rate":                 "nte",
    "hourly rate":          "nte",
    "service fee":          "nte",
    "dispatch fee":         "nte",
    "trip charge":          "nte",

    # status
    "status":               "status",
    "vendor status":        "status",
    "active":               "status",
    "active/inactive":      "status",

    # notes
    "notes":                "notes",
    "comments":             "notes",
    "vendor notes":         "notes",
    "additional info":      "notes",
}

# ── Trade Normalization Map ──────────────────────────────────
TRADE_NORMALIZE = {
    "hvac/plumbing": "HVAC",
    "heating and cooling": "HVAC",
    "heating & cooling": "HVAC",
    "air conditioning": "HVAC",
    "hvac": "HVAC",
    "plumbing": "Plumbing",
    "plumber": "Plumbing",
    "drain": "Rooter/Drain",
    "rooter": "Rooter/Drain",
    "rooter/drain": "Rooter/Drain",
    "sewer": "Rooter/Drain",
    "electrical": "Electrical",
    "electrician": "Electrical",
    "electric": "Electrical",
    "appliance": "Appliance Repair",
    "appliance repair": "Appliance Repair",
    "appliances": "Appliance Repair",
    "handyman": "General Handyman",
    "handyperson": "General Handyman",
    "general handyman": "General Handyman",
    "general maintenance": "General Handyman",
    "general contractor": "General Handyman",
    "roofing": "Roofing",
    "roof": "Roofing",
    "roofer": "Roofing",
    "pest control": "Pest Control",
    "pest": "Pest Control",
    "exterminator": "Pest Control",
    "landscaping": "Landscaping",
    "landscape": "Landscaping",
    "lawn care": "Landscaping",
    "lawn": "Landscaping",
    "tree service": "Landscaping",
    "locksmith": "Locksmith",
    "lock": "Locksmith",
    "keys": "Locksmith",
    "keys/locks": "Locksmith",
    "cleaning": "Cleaning Service",
    "cleaning service": "Cleaning Service",
    "janitorial": "Cleaning Service",
    "maid service": "Cleaning Service",
    "flooring": "Flooring",
    "carpet": "Flooring",
    "tile": "Flooring",
    "painting": "Painting",
    "painter": "Painting",
    "garage door": "Garage Doors",
    "garage doors": "Garage Doors",
    "fencing": "Fencing",
    "fence": "Fencing",
    "glass": "Window & Glass",
    "window": "Window & Glass",
    "windows": "Window & Glass",
    "gutters": "Gutters",
    "gutter": "Gutters",
    "drywall": "Drywall",
    "restoration": "Restoration",
    "fire/water damage": "Restoration",
    "water damage": "Restoration",
    "junk removal": "Junk Removal",
    "hauling": "Junk Removal",
    "trash": "Junk Removal",
    "pool": "Pool",
    "spa": "Pool",
}


def normalize_vendor_trade(trade_value):
    """Normalize a trade value from a vendor directory to standard names."""
    if pd.isna(trade_value):
        return None
    trade = str(trade_value).strip()
    trade_lower = trade.lower().strip()
    normalized = TRADE_NORMALIZE.get(trade_lower, trade)
    return CATEGORY_NORMALIZE.get(normalized, normalized)


def classify_trade_from_name(vendor_name):
    """When no trade column exists, classify from vendor name keywords."""
    if pd.isna(vendor_name):
        return "Unknown"

    name_lower = str(vendor_name).lower()

    patterns = {
        "HVAC": ["hvac", "heating", "cooling", "air conditioning", "furnace"],
        "Plumbing": ["plumb", "plumbing"],
        "Rooter/Drain": ["rooter", "drain", "sewer"],
        "Electrical": ["electric"],
        "Appliance Repair": ["appliance"],
        "General Handyman": ["handyman", "handy", "maintenance"],
        "Roofing": ["roof", "roofing"],
        "Pest Control": ["pest", "exterminator", "termite"],
        "Landscaping": ["landscape", "lawn", "tree"],
        "Locksmith": ["lock", "key", "locksmith"],
        "Cleaning Service": ["clean", "janitorial", "maid"],
        "Flooring": ["floor", "carpet", "tile"],
        "Painting": ["paint"],
        "Garage Doors": ["garage door"],
        "Fencing": ["fence", "fencing"],
        "Restoration": ["restoration", "fire damage", "flood"],
        "Junk Removal": ["junk", "haul", "trash"],
        "Pool": ["pool", "spa"],
    }

    for trade, keywords in patterns.items():
        for kw in keywords:
            if kw in name_lower:
                return trade

    return "Unknown"


def _map_vendor_columns(columns):
    """Map vendor directory columns using alias dictionary."""
    mapping = {}
    for col in columns:
        col_lower = str(col).lower().strip()
        if col_lower in VENDOR_COLUMN_ALIASES:
            standard = VENDOR_COLUMN_ALIASES[col_lower]
            if standard not in mapping:
                mapping[standard] = col
    return mapping


def process_vendor_directory(uploaded_file):
    """
    Process a vendor directory export.
    Returns structured vendor data ready to merge with WO processor output.

    Args:
        uploaded_file: Streamlit UploadedFile or file path

    Returns: dict with vendor data, trade coverage, risks
    """
    try:
        df = auto_load(uploaded_file)
    except Exception as e:
        return {"error": f"Failed to load vendor directory: {e}"}

    # Map columns
    mapping = _map_vendor_columns(df.columns)

    if "vendor_name" not in mapping:
        return {
            "error": "Cannot identify vendor name column",
            "columns_found": list(df.columns),
        }

    # Build standardized DataFrame
    std = pd.DataFrame()
    for field, col in mapping.items():
        std[field] = df[col]

    # Handle missing trade column
    has_trade = "trade" in std.columns and std["trade"].notna().any()

    # Normalize trades
    if has_trade:
        std["normalized_trade"] = std["trade"].apply(normalize_vendor_trade)
    else:
        std["normalized_trade"] = std["vendor_name"].apply(classify_trade_from_name)

    # Build vendor dict
    vendors = {}
    for _, row in std.iterrows():
        name = str(row.get("vendor_name", "")).strip()
        if not name or name.lower() == "nan":
            continue

        trade = row.get("normalized_trade", "Unknown")

        if name not in vendors:
            vendors[name] = {
                "trades": [],
                "phone": row.get("phone") if pd.notna(row.get("phone")) else None,
                "email": row.get("email") if pd.notna(row.get("email")) else None,
                "insurance_exp": row.get("insurance_exp") if pd.notna(row.get("insurance_exp")) else None,
                "preferred": row.get("preferred") if pd.notna(row.get("preferred")) else None,
                "nte": row.get("nte") if pd.notna(row.get("nte")) else None,
                "status": str(row.get("status", "active")) if pd.notna(row.get("status")) else "active",
            }

        if trade and trade != "Unknown" and trade not in vendors[name]["trades"]:
            vendors[name]["trades"].append(trade)

    # Trade coverage from directory
    all_directory_trades = set()
    for v in vendors.values():
        all_directory_trades.update(v["trades"])

    covered = [t for t in REQUIRED_TRADES_12 if t in all_directory_trades]
    missing = [t for t in REQUIRED_TRADES_12 if t not in all_directory_trades]

    # Single-vendor trades (required trades with only 1 vendor)
    trade_vendor_count = {}
    for v_name, v_data in vendors.items():
        for t in v_data["trades"]:
            trade_vendor_count[t] = trade_vendor_count.get(t, 0) + 1
    single_vendor_trades = [
        t for t, c in trade_vendor_count.items()
        if c == 1 and t in REQUIRED_TRADES_12
    ]

    # Expired insurance
    expired_insurance = []
    today = pd.Timestamp.now()
    for v_name, v_data in vendors.items():
        exp = v_data.get("insurance_exp")
        if exp:
            exp_date = auto_parse_dates(pd.Series([exp])).iloc[0]
            if pd.notna(exp_date) and exp_date < today:
                expired_insurance.append(v_name)

    # Inactive vendors
    inactive = [
        v for v, d in vendors.items()
        if d.get("status") and str(d["status"]).lower().strip()
        in ("inactive", "suspended", "terminated", "no")
    ]

    return {
        "vendors": vendors,
        "vendor_count": len(vendors),
        "active_count": len(vendors) - len(inactive),
        "inactive_count": len(inactive),
        "inactive_vendors": inactive,
        "trades_covered": covered,
        "trades_covered_count": len(covered),
        "missing_trades": missing,
        "single_vendor_trades": single_vendor_trades,
        "expired_insurance": expired_insurance,
        "has_trade_data": has_trade,
        "trade_classification_method": "directory" if has_trade else "vendor_name_keywords",
    }


def merge_vendor_data(wo_metrics, vendor_directory):
    """
    Combine WO-derived vendor data with vendor directory data.
    Vendor directory enriches but never overwrites WO actuals.

    Args:
        wo_metrics: dict from WO processor (compute_metrics output)
        vendor_directory: dict from process_vendor_directory, or None

    Returns: dict with combined vendor profile
    """
    combined = {
        # From WO processor (actuals)
        "dispatched_vendors": wo_metrics.get("unique_vendors", 0),
        "dispatched_vendor_names": wo_metrics.get("dispatched_vendor_names", []),
        "dispatched_vendor_list": wo_metrics.get("vendor_concentration", {}),
        "trades_from_dispatches": wo_metrics.get("covered_trades", []),

        # From vendor directory (when provided)
        "available_vendors": None,
        "available_vendor_list": None,
        "trades_from_directory": None,

        # Merged outputs (what the report uses)
        "total_vendors": None,
        "trades_covered": None,
        "trades_covered_count": None,
        "missing_trades": None,
        "single_vendor_trades": None,
        "vendors_not_dispatched": None,
        "data_source": None,
    }

    if vendor_directory is None or "error" in vendor_directory:
        # No directory: use WO data only
        combined["total_vendors"] = wo_metrics.get("unique_vendors", 0)
        combined["trades_covered"] = wo_metrics.get("covered_trades", [])
        combined["trades_covered_count"] = wo_metrics.get("trades_covered_count", 0)
        combined["missing_trades"] = wo_metrics.get("missing_trades", [])
        combined["single_vendor_trades"] = []
        combined["data_source"] = "work_orders_only"
    else:
        dir_vendors = vendor_directory.get("vendors", {})
        dir_trades = set(vendor_directory.get("trades_covered", []))

        combined["available_vendors"] = len(dir_vendors)
        combined["available_vendor_list"] = dir_vendors
        combined["trades_from_directory"] = sorted(list(dir_trades))

        # Total = union of dispatched + directory vendor names
        dispatched_names = set(wo_metrics.get("dispatched_vendor_names", []))
        dir_names = set(dir_vendors.keys())
        all_names = dispatched_names | dir_names
        combined["total_vendors"] = len(all_names)

        # Trade coverage = union of WO-derived + directory-derived
        wo_trades = set(wo_metrics.get("covered_trades", []))
        all_trades = wo_trades | dir_trades
        combined["trades_covered"] = sorted(list(all_trades))
        combined["trades_covered_count"] = len(all_trades)

        # Missing = required trades not in either source
        required = set(REQUIRED_TRADES_12)
        combined["missing_trades"] = sorted(list(required - all_trades))

        # Single vendor trades
        combined["single_vendor_trades"] = vendor_directory.get("single_vendor_trades", [])

        # Vendors in directory but never dispatched
        dispatched_lower = set(n.lower().strip() for n in dispatched_names)
        combined["vendors_not_dispatched"] = [
            v for v in dir_names
            if v.lower().strip() not in dispatched_lower
        ]

        combined["data_source"] = "work_orders_and_directory"

    return combined
