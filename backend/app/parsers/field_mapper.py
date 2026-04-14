"""Maps PMS-specific column names to canonical field names.

Supports AppFolio, Buildium, RentManager out of the box,
with fuzzy fallback for other PMS systems.
"""
from difflib import SequenceMatcher

# Canonical field → list of known column name variants (lowercase)
FIELD_MAPPINGS = {
    # Work Order fields
    "work_order_id": [
        "wo_id", "work order #", "wo number", "id", "workorderid",
        "work order id", "wo #", "wo id", "workorder_id", "wo_number",
        "work order number", "ticket", "ticket #", "ticket id",
        "service request id", "maintenance request id",
    ],
    "created_date": [
        "date created", "created", "open date", "date opened", "createdat",
        "created_date", "opened", "request date", "submitted date",
        "date submitted", "wo date", "work order date", "created date",
    ],
    "completed_date": [
        "date completed", "completed", "close date", "closed_date",
        "completed_date", "date closed", "closed date", "resolved date",
        "completion date", "finish date", "actual end date",
    ],
    "status": [
        "status", "wo status", "state", "current status", "wo_status",
        "work order status", "condition",
    ],
    "category": [
        "type", "category", "maintenance type", "work type", "wo_category",
        "work order type", "issue type", "service type", "trade",
        "maintenance category", "problem type",
    ],
    "description": [
        "description", "details", "work description", "summary",
        "issue description", "problem description", "notes",
    ],
    "vendor_name": [
        "vendor", "assigned vendor", "vendor name", "technician",
        "assigned to", "contractor", "service provider", "vendor_name",
    ],
    "cost": [
        "total cost", "cost", "amount", "invoice amount", "total",
        "wo cost", "expense", "charge", "price", "total amount",
        "amount paid", "estimated amount",
    ],
    "priority": [
        "priority", "urgency", "severity", "priority level",
    ],
    "property_name": [
        "property", "property name", "building", "location",
        "property_name", "building name", "site",
    ],
    "unit": [
        "unit", "unit #", "unit number", "apt", "apartment",
        "suite", "unit_number", "apt #",
    ],

    # Vendor fields
    "trade": [
        "trade", "specialty", "service type", "trade type",
        "vendor type", "category", "skill", "profession",
    ],
    "phone": [
        "phone", "phone number", "tel", "telephone", "contact phone",
        "phone #", "mobile",
    ],
    "email": [
        "email", "email address", "e-mail", "contact email",
    ],
    "active": [
        "active", "status", "is active", "active status", "enabled",
    ],
    "assignment_count": [
        "assignments", "wo count", "work orders", "jobs",
        "assignment count", "total assignments",
    ],

    # Property fields
    "address": [
        "address", "street address", "location", "property address",
        "full address",
    ],
    "unit_count": [
        "units", "unit count", "# units", "number of units",
        "total units", "doors", "unit_count",
    ],
    "property_type": [
        "type", "property type", "building type", "category",
    ],
    "occupancy_rate": [
        "occupancy", "occupancy rate", "occupied %", "occupancy %",
        "occupancy_rate",
    ],
}


def _normalize(col: str) -> str:
    """Normalize a column name for comparison."""
    return col.strip().lower().replace("_", " ").replace("-", " ")


def _fuzzy_match(col: str, candidates: list[str], threshold: float = 0.7) -> bool:
    """Check if col fuzzy-matches any candidate above threshold."""
    col_norm = _normalize(col)
    for candidate in candidates:
        ratio = SequenceMatcher(None, col_norm, candidate).ratio()
        if ratio >= threshold:
            return True
    return False


def map_columns(df_columns: list[str], required_fields: list[str]) -> dict[str, str]:
    """Map DataFrame column names to canonical field names.

    Args:
        df_columns: Column names from the uploaded file
        required_fields: List of canonical field names to map

    Returns:
        Dict mapping canonical_name → actual_column_name
        Only includes successfully mapped fields.
    """
    mapping = {}
    used_columns = set()

    for field in required_fields:
        if field not in FIELD_MAPPINGS:
            continue

        candidates = FIELD_MAPPINGS[field]
        matched = False

        # Pass 1: exact match (case-insensitive)
        for col in df_columns:
            if col in used_columns:
                continue
            col_norm = _normalize(col)
            if col_norm in candidates or col_norm == field:
                mapping[field] = col
                used_columns.add(col)
                matched = True
                break

        if matched:
            continue

        # Pass 2: fuzzy match
        for col in df_columns:
            if col in used_columns:
                continue
            if _fuzzy_match(col, candidates):
                mapping[field] = col
                used_columns.add(col)
                break

    return mapping
