"""Work Order Processing Pipeline — Stage 2.

Three-stage architecture:
  Stage 1: Column mapping from PMS config (pms_mappings.py) OR auto-detection (column_mapper.py)
  Stage 2: THIS FILE — pandas pipeline, all math, all metrics
  Stage 3: AI interpretation of computed metrics (ai_interpretation.py)

Python does the math. AI does the interpretation. AI never sees raw spreadsheet data.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from app.utils.date_parsing import auto_parse_dates
from app.config import CORE_TRADES
from app.parsers.pms_mappings import (
    PMS_CONFIGS, STATUS_NORMALIZE, TRADE_KEYWORDS,
    EMERGENCY_KEYWORDS, EMERGENCY_PRIORITIES, INSPECTION_KEYWORDS,
    CATEGORY_NORMALIZE, TRADE_COVERAGE_MAP, VENDOR_TRADE_KEYWORDS,
)
from app.parsers.column_mapper import (
    STANDARD_FIELDS,
    auto_load, rule_based_mapping, ai_mapping_fallback,
    auto_parse_currency, auto_normalize_status,
)


def _safe_str(series):
    """Convert a Series to string dtype so .str accessor works even with NaN/numeric values."""
    return series.fillna("").astype(str)


def _resolve_unknown_status(std):
    """Reconcile ambiguous/open statuses using close-date fallback.

    Rules:
    1) Blank/unknown raw statuses are resolved by close-date presence.
    2) Any non-cancelled WO with a close_date is treated as completed for metrics.
       This prevents stale status labels (e.g. in_progress) from inflating open WO rate.
    """
    has_close = std["close_date"].notna()

    # Rule 1: blank/unknown statuses -> completed/open fallback
    unknown_mask = std["status"] == "unknown"
    raw_blank = _safe_str(std["raw_status"]).str.strip() == ""
    blank_unknown = unknown_mask & raw_blank
    if blank_unknown.any():
        std.loc[blank_unknown & has_close, "status"] = "completed"
        std.loc[blank_unknown & ~has_close, "status"] = "open"

    # Rule 2: close date wins for non-cancelled rows
    needs_completion_reconcile = has_close & ~std["status"].isin(["completed", "cancelled"])
    if needs_completion_reconcile.any():
        std.loc[needs_completion_reconcile, "status"] = "completed"


def load_work_orders(uploaded_file, pms_platform):
    """
    Load and normalize a work order export into a standardized DataFrame.
    Returns (df, config, load_warnings).

    NOTE: uploaded_file is a Streamlit UploadedFile object (file-like), not a path.
    """
    config = PMS_CONFIGS.get(pms_platform)
    if not config:
        raise ValueError(f"Unsupported PMS platform: {pms_platform}. Supported: {list(PMS_CONFIGS.keys())}")

    warnings = []

    # Detect actual file type from uploaded file name — ALWAYS trust the extension
    file_name = getattr(uploaded_file, "name", "") or ""
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

    # Prioritize actual file extension over PMS config's expected file_type
    if ext in ("xlsx", "xls"):
        engine = "xlrd" if ext == "xls" else "openpyxl"
        df = pd.read_excel(uploaded_file, skiprows=config["skip_rows"], engine=engine)
    elif ext == "csv":
        df = pd.read_csv(uploaded_file, skiprows=config["skip_rows"])
    elif ext == "tsv":
        df = pd.read_csv(uploaded_file, skiprows=config["skip_rows"], sep='\t')
    elif config["file_type"] == "csv":
        # No extension detected, fall back to config's expected type
        df = pd.read_csv(uploaded_file, skiprows=config["skip_rows"])
    elif config["file_type"] in ("xlsx", "xls"):
        engine = "xlrd" if config["file_type"] == "xls" else "openpyxl"
        df = pd.read_excel(uploaded_file, skiprows=config["skip_rows"], engine=engine)
    else:
        raise ValueError(f"Unsupported file type: '{ext}'. Expected csv, xlsx, or xls.")

    # Drop trailing null rows
    if config.get("drop_trailing_nulls"):
        wo_num_col = config["columns"]["wo_number"]
        if wo_num_col in df.columns:
            df = df.dropna(subset=[wo_num_col], how="all")

    # Validate required columns exist
    required = ["wo_number", "unit", "status", "created_date", "description"]
    for field in required:
        col_name = config["columns"].get(field)
        if col_name and col_name not in df.columns:
            warnings.append(f"Required column '{col_name}' (mapped as '{field}') not found in export.")

    # Track which optional columns are missing (for graceful degradation)
    optional_fields = ["category", "source", "requested_by", "assigned_to", "amount"]
    missing_fields = []
    for field in optional_fields:
        col_name = config["columns"].get(field)
        if not col_name or col_name not in df.columns:
            missing_fields.append(field)
    if missing_fields:
        warnings.append(f"Optional columns not found: {', '.join(missing_fields)}. Analysis will adapt.")

    # Store missing fields on config for downstream use
    config["_missing_fields"] = set(missing_fields)
    config["_columns_found"] = len([c for c in config["columns"].values() if c and c in df.columns])
    config["_columns_expected"] = len([c for c in config["columns"].values() if c])

    return df, config, warnings


def normalize_dataframe(df, config, client_info):
    """
    Normalize a raw PMS DataFrame into standardized columns.
    Returns standardized DataFrame with consistent column names.
    Gracefully handles missing columns (legacy export formats).
    """
    cols = config["columns"]
    parsing = config["parsing"]
    missing = config.get("_missing_fields", set())

    std = pd.DataFrame()

    # ── Helper: safe column get (returns NaN series if column missing) ──
    def _col(field_key):
        col_name = cols.get(field_key)
        if col_name and col_name in df.columns:
            return df[col_name]
        return pd.Series(np.nan, index=df.index)

    # ── Map columns ──
    std["wo_number"] = _col("wo_number")
    std["unit"] = _col("unit")
    std["property"] = _col("property") if "property" in cols else pd.Series(np.nan, index=df.index)
    std["vendor"] = _col("vendor")
    std["raw_status"] = _col("status")
    std["amount"] = _col("amount")
    std["description"] = _col("description")
    std["assigned_to"] = _col("assigned_to")
    std["requested_by"] = _col("requested_by")
    std["raw_source"] = _col("source")

    # Assigned PM (may not exist in all PMS)
    if cols.get("assigned_pm") and cols["assigned_pm"] in df.columns:
        std["assigned_pm"] = df[cols["assigned_pm"]]

    # ── Build unit_label: property address + unit for display ──
    has_property = std["property"].notna().any() and not (std["property"] == std["unit"]).all()
    if has_property:
        def _build_label(row):
            prop = str(row["property"]).strip() if pd.notna(row["property"]) else ""
            unit = str(row["unit"]).strip() if pd.notna(row["unit"]) else ""
            if not prop:
                return unit or "Unknown"
            if unit and len(unit) <= 10 and " " not in unit and unit != prop:
                return f"{prop}, Unit {unit}"
            return prop
        std["unit_label"] = std.apply(_build_label, axis=1)
    else:
        std["unit_label"] = std["unit"].fillna("Unknown").astype(str)

    # ── Category: fallback chain ──
    std["raw_category"] = pd.Series(dtype=object, index=df.index)
    for field_key in config["category_fallback_chain"]:
        if field_key == "description_keywords":
            break  # Handle separately after normalization
        col_name = cols.get(field_key)
        if col_name and col_name in df.columns:
            mask = std["raw_category"].isna()
            if mask.any():
                std.loc[mask, "raw_category"] = df.loc[mask, col_name]

    # ── Priority (if PMS has it) ──
    priority_field = config.get("priority_field")
    if priority_field and cols.get(priority_field) and cols[priority_field] in df.columns:
        std["priority"] = df[cols[priority_field]]
    elif priority_field and priority_field in df.columns:
        std["priority"] = df[priority_field]
    else:
        std["priority"] = None

    # ── Bonus fields (gracefully handle missing) ──
    for bonus in ["maintenance_limit", "recurring", "scheduled_start", "resident_requested", "canceled_on"]:
        col_name = cols.get(bonus)
        if col_name and col_name in df.columns:
            std[bonus] = df[col_name]

    # ── Parse dates (shared flexible parser only) ──
    std["created_date"] = auto_parse_dates(_col("created_date"))
    std["close_date"] = auto_parse_dates(_col("close_date"))
    if parsing.get("zero_means_null"):
        std.loc[std["created_date"] == pd.Timestamp(0), "created_date"] = pd.NaT
        std.loc[std["close_date"] == pd.Timestamp(0), "close_date"] = pd.NaT
        if "amount" in std.columns:
            std.loc[std["amount"] == 0, "amount"] = np.nan

    # Bonus date fields
    if "scheduled_start" in std.columns:
        std["scheduled_start"] = auto_parse_dates(std["scheduled_start"])
        if parsing.get("zero_means_null"):
            std.loc[std["scheduled_start"] == pd.Timestamp(0), "scheduled_start"] = pd.NaT

    # ── Parse currency ──
    if parsing.get("currency_strip") and std["amount"].dtype == object:
        for char in parsing["currency_strip"]:
            std["amount"] = std["amount"].astype(str).str.replace(char, "", regex=False)
        std["amount"] = pd.to_numeric(std["amount"], errors="coerce")

    # ── Normalize statuses ──
    std["status"] = std["raw_status"].astype(str).str.lower().str.strip().map(STATUS_NORMALIZE).fillna("unknown")
    _resolve_unknown_status(std)

    # ── Classify source ──
    std["source"] = classify_source(std, config)

    # ── Detect internal staff ──
    std["is_internal"] = detect_internal_staff(std, config, client_info)

    # ── Classify trade ──
    std["trade"] = classify_trades(std, config)

    # ── Detect emergencies ──
    std["is_emergency"] = detect_emergencies(std)

    # ── Detect after-hours (only when time-of-day data is available) ──
    from app.parsers.column_mapper import has_time_component
    std["is_after_hours"] = False
    has_time_data = False
    if std["created_date"].notna().any():
        if has_time_component(std["created_date"]):
            has_time_data = True
            std["hour"] = std["created_date"].dt.hour
            std["weekday"] = std["created_date"].dt.weekday
            std["is_after_hours"] = (std["hour"] < 8) | (std["hour"] >= 18) | (std["weekday"] >= 5)
        else:
            # Date-only: can detect weekend WOs but NOT time-of-day
            std["weekday"] = std["created_date"].dt.weekday
            std["is_after_hours"] = std["weekday"] >= 5
    config["_has_time_data"] = has_time_data

    # ── Detect inspections (by trade, description, vendor name, and status) ──
    std["is_inspection"] = std["trade"] == "Inspections"
    if std["description"].notna().any():
        desc_lower = _safe_str(std["description"]).str.lower().str.strip()
        kw_pattern = "|".join(INSPECTION_KEYWORDS)
        std["is_inspection"] = std["is_inspection"] | desc_lower.str.contains(kw_pattern, na=False)
    if std["vendor"].notna().any():
        vendor_lower = _safe_str(std["vendor"]).str.lower().str.strip()
        std["is_inspection"] = std["is_inspection"] | vendor_lower.str.contains("inspection", na=False)
    if std["raw_status"].notna().any():
        raw_status_lower = _safe_str(std["raw_status"]).str.lower().str.strip()
        std["is_inspection"] = std["is_inspection"] | raw_status_lower.str.contains("inspection", na=False)

    # ── Filter: separate maintenance from non-maintenance ──
    # Maintenance = not an inspection AND not cancelled/rejected/duplicate
    std["is_cancelled"] = std["status"] == "cancelled"
    std["is_maintenance"] = ~std["is_inspection"] & ~std["is_cancelled"]

    # Also flag recurring/scheduled WOs
    std["is_recurring"] = std["source"] == "recurring"
    # Check for dedicated "Recurring" column (e.g. AppFolio Yes/No)
    if "recurring" in std.columns:
        recurring_vals = std["recurring"].astype(str).str.lower().str.strip()
        std["is_recurring"] = std["is_recurring"] | recurring_vals.isin(["yes", "true", "1", "y"])

    return std


def classify_source(std, config):
    """Classify each WO source into: resident, recurring, staff_created, unit_turn, data_not_available."""
    source_config = config["source_classification"]
    missing = config.get("_missing_fields", set())

    # If source column is missing, do not infer distribution from other fields.
    # Spec requirement: report "Source tracking not available."
    source_col_missing = "source" in missing
    requester_col_missing = "requested_by" in missing
    if source_col_missing:
        return pd.Series("data_not_available", index=std.index)

    result = pd.Series("unknown", index=std.index)

    # Only try to match source values if the column has data
    if not source_col_missing and std["raw_source"].notna().any():
        raw = _safe_str(std["raw_source"]).str.lower().str.strip()
        for val in source_config.get("recurring_values", []):
            result[raw == val.lower()] = "recurring"
        for val in source_config.get("resident_values", []):
            result[raw == val.lower()] = "resident"
        for val in source_config.get("internal_values", []):
            result[raw == val.lower()] = "staff_created"
        for val in source_config.get("unit_turn_values", []):
            result[raw == val.lower()] = "unit_turn"

    # Override with recurring field if available (AppFolio)
    if "recurring" in std.columns:
        recurring_mask = std["recurring"].astype(str).str.lower().str.strip() == "yes"
        result[recurring_mask] = "recurring"

    # Source column exists but some rows are null — use requester as fallback
    if not source_col_missing:
        null_source = std["raw_source"].isna()
        if not requester_col_missing:
            no_requester = std["requested_by"].isna()
            result[null_source & no_requester & (result == "unknown")] = "staff_created"
            result[null_source & ~no_requester & (result == "unknown")] = "resident"

    return result


def detect_internal_staff(std, config, client_info):
    """Detect which WOs were handled by internal staff rather than external vendors."""
    method = config["internal_staff_detection"]["method"]
    missing = config.get("_missing_fields", set())

    if method == "vendor_equals_assignee":
        # If assignee column is missing, we can't detect internal staff this way
        if "assigned_to" in missing or std["assigned_to"].isna().all():
            return pd.Series(False, index=std.index)
        vendor = _safe_str(std["vendor"]).str.lower().str.strip()
        assignee = _safe_str(std["assigned_to"]).str.lower().str.strip()
        return (vendor == assignee) & (vendor != "")

    elif method == "vendor_name_patterns":
        company = client_info.get("company_name", "").lower()
        vendor = _safe_str(std["vendor"]).str.lower().str.strip()
        is_company = vendor.str.contains(company, na=False) if company else pd.Series(False, index=std.index)

        internal_patterns = ["maintenance team", "in-house", "internal", "staff", "company maintenance"]
        is_pattern = vendor.str.contains("|".join(internal_patterns), na=False, case=False)

        return is_company | is_pattern

    return pd.Series(False, index=std.index)


def _ai_classify_trades(std, unclassified_mask):
    """Batch-classify unclassified WOs using Claude API.

    Builds unique (vendor, description_snippet) pairs and sends them in a
    single API call. Returns a Series indexed to the unclassified rows.
    Only called when keyword matching leaves >30% of WOs unclassified.
    """
    import os
    import json
    import logging

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return pd.Series(dtype=object, index=std[unclassified_mask].index)

    try:
        import anthropic

        unclassified = std[unclassified_mask]

        def _pair(row):
            vendor = str(row.get("vendor", "") or "").strip()[:50]
            desc = str(row.get("description", "") or "").strip()[:80]
            return (vendor, desc)

        pairs = unclassified.apply(_pair, axis=1)
        unique_pairs = list(dict.fromkeys(pairs.tolist()))  # preserve order, deduplicate

        if not unique_pairs:
            return pd.Series(dtype=object, index=unclassified.index)

        trade_options = [
            "HVAC", "Plumbing", "Electrical", "Appliance Repair", "Pest Control",
            "Roofing", "Landscaping", "Locksmith", "Painting", "Flooring",
            "General Handyman", "Cleaning Service", "Garage Doors", "Drywall",
            "Restoration", "Junk Removal", "Smoke Detectors", "Inspections",
            "Foundation", "Other",
        ]

        rows_text = "\n".join(
            f'{i + 1}. vendor="{v}" description="{d}"'
            for i, (v, d) in enumerate(unique_pairs)
        )

        prompt = (
            "Classify each property management work order into exactly one trade category.\n\n"
            f"Available categories: {', '.join(trade_options)}\n\n"
            f"Work orders:\n{rows_text}\n\n"
            "Return ONLY a JSON array of strings, one per work order, in the same order. "
            'Example: ["HVAC", "Plumbing", "Other"]'
        )

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            timeout=30.0,
            messages=[{"role": "user", "content": prompt}],
        )

        classifications = json.loads(response.content[0].text.strip())
        pair_to_trade = {
            pair: classifications[i]
            for i, pair in enumerate(unique_pairs)
            if i < len(classifications)
        }

        result = pairs.map(lambda p: pair_to_trade.get(p))
        return result

    except Exception as exc:
        import logging as _logging
        _logging.warning("AI trade classification failed: %s", exc)
        return pd.Series(dtype=object, index=std[unclassified_mask].index)


def classify_trades(std, config):
    """Classify each WO into a standard trade category using the fallback chain."""
    result = std["raw_category"].astype("object").copy()
    # Treat blank placeholder values as missing so fallback classification can run.
    # Use None (not np.nan) so pandas never re-infers the Series as float64.
    result = result.apply(lambda v: str(v).strip() if pd.notna(v) else None)
    result = result.replace({
        "": None,
        "nan": None,
        "none": None,
        "null": None,
        "n/a": None,
        "na": None,
    })
    # Normalize explicit categories from source when available.
    result = result.apply(lambda v: CATEGORY_NORMALIZE.get(v, v) if v is not None else None)
    # Guarantee object dtype — any of the apply() calls above can re-infer float64
    # when every value is None/NaN, which breaks the string assignment loops below.
    result = result.astype(object)

    # Where raw_category is null, try vendor name keywords
    needs_classification = result.isna()
    if needs_classification.any():
        vendor_lower = _safe_str(std.loc[needs_classification, "vendor"]).str.lower().str.strip()
        for trade, keywords in TRADE_KEYWORDS["vendor_name"].items():
            for kw in keywords:
                match = vendor_lower.str.contains(kw, na=False, case=False)
                assign_mask = needs_classification & match.reindex(result.index, fill_value=False)
                if assign_mask.any():
                    result.loc[assign_mask] = trade
                    needs_classification = result.isna()
                    if not needs_classification.any():
                        break
            if not needs_classification.any():
                break

    # Where still null, try description keywords
    still_needs = result.isna()
    if still_needs.any():
        desc_lower = _safe_str(std.loc[still_needs, "description"]).str.lower().str.strip()
        for trade, keywords in TRADE_KEYWORDS["description"].items():
            for kw in keywords:
                match = desc_lower.str.contains(kw, na=False, case=False)
                assign_mask = still_needs & match.reindex(result.index, fill_value=False)
                if assign_mask.any():
                    result.loc[assign_mask] = trade
                    still_needs = result.isna()
                    if not still_needs.any():
                        break
            if not still_needs.any():
                break

    # AI classification when keyword matching leaves >30% unclassified
    still_unclassified = result.isna()
    if len(result) > 0 and still_unclassified.sum() / len(result) > 0.30:
        ai_result = _ai_classify_trades(std, still_unclassified)
        if ai_result is not None and len(ai_result) > 0:
            result.update(ai_result)

    # Default: Other
    result = result.fillna("Other")
    result = result.apply(lambda v: CATEGORY_NORMALIZE.get(v, v) if pd.notna(v) else v)

    return result


def detect_emergencies(std):
    """Flag emergency WOs based on priority field and description keywords."""
    is_emergency = pd.Series(False, index=std.index)

    # Check priority field (if available)
    if "priority" in std.columns and std["priority"].notna().any():
        priority_lower = std["priority"].astype(str).str.lower().str.strip()
        for p in EMERGENCY_PRIORITIES:
            is_emergency |= priority_lower.str.contains(p, na=False)

    # Check description keywords
    if std["description"].notna().any():
        desc_lower = _safe_str(std["description"]).str.lower().str.strip()
        for kw in EMERGENCY_KEYWORDS:
            is_emergency |= desc_lower.str.contains(kw, na=False)

    return is_emergency


def calculate_first_response(std):
    """
    Calculate first response time using the transparent 4-method hierarchy.
    Returns (median_hours, method_name, method_note).
    """
    # Method 1: Scheduled Start field (AppFolio)
    if "scheduled_start" in std.columns:
        valid = std[std["scheduled_start"].notna() & std["created_date"].notna()]
        if len(valid) >= 5:
            delta = (valid["scheduled_start"] - valid["created_date"]).dt.total_seconds() / 3600
            delta = delta[delta > 0]
            if len(delta) >= 5:
                return (
                    round(delta.median(), 1),
                    "vendor_assignment",
                    "Estimated from scheduled start timestamps (proxy for first action)"
                )

    # Method 2: Close date on fast-turnaround WOs as proxy (NOT true first response)
    valid = std[std["close_date"].notna() & std["created_date"].notna()]
    if len(valid) >= 5:
        delta_hours = (valid["close_date"] - valid["created_date"]).dt.total_seconds() / 3600
        fast = delta_hours[(delta_hours > 0) & (delta_hours < 48)]
        if len(fast) >= 5:
            return (
                round(fast.median(), 1),
                "fast_close_proxy",
                "Estimated from median close time for fast-turnaround WOs (under 48 hrs). "
                "This is NOT true first response time — it reflects how quickly simple jobs are closed, "
                "not when a resident first received acknowledgment."
            )

    # Method 3: Not calculable
    return (
        None,
        "not_calculable",
        "Work order export does not include response time, vendor assignment, or status change timestamps. First response time cannot be calculated from available data. Vendoroo's average first response is under 10 minutes."
    )


def build_trade_chart(maint, total_maintenance_count):
    """
    Build trade distribution chart that always sums to exactly 100%.

    Rules:
    1. Denominator is ALWAYS total_maintenance_count (including uncategorized WOs)
    2. 6 required trades always appear (even at 0%)
    3. Any additional trade ≥3% is shown
    4. "Other" is the remainder: 100% - sum(shown trades)
    """
    REQUIRED_TRADES = ["HVAC", "Plumbing", "Electrical", "Handyperson", "Pest Control", "Appliances"]
    SHOW_THRESHOLD = 3.0

    # Apply category normalization before counting
    cats = maint["trade"].apply(
        lambda c: CATEGORY_NORMALIZE.get(c, c) if pd.notna(c) else None
    )
    counts = cats.value_counts()

    shown = {}
    required_trade_variants = {
        "Handyperson": ["General Handyman", "Handyperson"],
        "Appliances": ["Appliance Repair", "Appliances"],
    }
    for t in REQUIRED_TRADES:
        if t in required_trade_variants:
            shown[t] = int(sum(int(counts.get(v, 0)) for v in required_trade_variants[t]))
        else:
            shown[t] = int(counts.get(t, 0))
    for trade, count in counts.items():
        if not trade:
            continue
        trade_name = str(trade).strip()
        # "Other" is always synthesized from the remainder below; skip raw category rows
        # named "Other" to avoid duplicate "Other" bars and downstream sum drift.
        if trade_name.lower() == "other":
            continue
        if trade_name not in shown and (count / total_maintenance_count * 100) >= SHOW_THRESHOLD:
            shown[trade_name] = int(count)

    # Sort by count descending
    shown = dict(sorted(shown.items(), key=lambda x: x[1], reverse=True))

    chart = []
    running_pct = 0.0
    for trade, count in shown.items():
        pct = round(count / total_maintenance_count * 100, 1)
        running_pct += pct
        chart.append({"trade": trade, "count": count, "pct": pct})

    other_pct = round(max(0.0, 100.0 - running_pct), 1)
    other_count = total_maintenance_count - sum(d["count"] for d in chart)
    chart.append({"trade": "Other", "count": other_count, "pct": other_pct})

    # Force exact 100.0% sum after rounding for report validation.
    total_pct = round(sum(item["pct"] for item in chart), 1)
    if total_pct != 100.0:
        chart[-1]["pct"] = round(chart[-1]["pct"] + (100.0 - total_pct), 1)

    return chart


def check_trade_coverage(maintenance_categories):
    """Check which required trades are covered by PMS category data."""
    actual_cats = set()
    for c in maintenance_categories:
        if pd.isna(c):
            continue
        value = str(c).strip()
        normalized = CATEGORY_NORMALIZE.get(value, CATEGORY_NORMALIZE.get(value.lower(), value.lower()))
        actual_cats.add(normalized.lower())
    covered = []
    missing = []
    for required_trade, variants in TRADE_COVERAGE_MAP.items():
        variants_lower = [str(v).strip().lower() for v in variants]
        if any(v in actual_cats for v in variants_lower):
            covered.append(required_trade)
        else:
            missing.append(required_trade)
    return covered, missing


def check_vendor_trade_coverage(vendor_names):
    """Supplement trade coverage using vendor name keyword detection."""
    vendor_lower = [v.lower() for v in vendor_names if pd.notna(v)]
    covered = set()
    for trade, keywords in VENDOR_TRADE_KEYWORDS.items():
        for v in vendor_lower:
            if any(kw in v for kw in keywords):
                covered.add(trade)
                break
    return covered


def compute_metrics(std, client_info, config=None):
    """
    Compute all metrics from the standardized DataFrame.
    Returns a dict of all computed values ready for AI interpretation and report generation.
    """
    door_count = client_info.get("door_count", 0)

    missing = config.get("_missing_fields", set()) if config else set()

    # ── Filter to maintenance-only for core metrics ──
    # Maintenance = not inspection, not cancelled, not recurring
    maint = std[std["is_maintenance"] & ~std["is_recurring"]]
    all_wos = std

    # ── Volume ──
    total_wos = len(all_wos)
    cancelled_count = int(std["is_cancelled"].sum())
    inspection_count = int((std["is_inspection"] & ~std["is_cancelled"]).sum())
    maintenance_wos = len(maint)
    recurring_wos = int((std["is_recurring"] & std["is_maintenance"]).sum())
    total_filtered = cancelled_count + inspection_count + recurring_wos

    # ── Date Range (Fix 1) ──
    date_range_days = 0
    date_range_start = None
    date_range_end = None
    if std["created_date"].notna().any():
        date_range_start = std["created_date"].min()
        date_range_end = std["created_date"].max()
        date_range_days = (date_range_end - date_range_start).days
    months_spanned = max(date_range_days / 30.44, 1)
    monthly_avg = round(maintenance_wos / months_spanned)

    # ── Data Reliability (Fix 7) ──
    if date_range_days < 90:
        data_reliability = "low"
        reliability_warning = f"Only {date_range_days} days of data. Metrics are preliminary. 12 months recommended."
    elif date_range_days < 180:
        data_reliability = "moderate"
        reliability_warning = f"{date_range_days} days of data. 12 months recommended for full reliability."
    else:
        data_reliability = "high"
        reliability_warning = None

    # ── Open WO Rate ──
    open_statuses = ["open", "in_progress"]
    open_wos = maint[maint["status"].isin(open_statuses)]
    open_wo_count = len(open_wos)
    open_wo_rate = round((open_wo_count / door_count) * 100, 1) if door_count > 0 else None

    # ── Completion Time ──
    completed = maint[maint["status"] == "completed"]
    median_completion_days = None
    if completed["close_date"].notna().any() and completed["created_date"].notna().any():
        valid = completed[completed["close_date"].notna() & completed["created_date"].notna()]
        delta = (valid["close_date"] - valid["created_date"]).dt.total_seconds() / 86400
        delta = delta[delta >= 0]
        if len(delta) > 0:
            median_completion_days = round(delta.median(), 1)

    # ── First Response Time ──
    response_hours, response_method, response_note = calculate_first_response(maint)

    # ── Vendor Analysis (Fix 3: count from filtered maintenance set) ──
    external = maint[maint["vendor"].notna()]

    def _normalize_vendor_name(name: str) -> str:
        if not name or not isinstance(name, str):
            return ""
        n = name.strip().lower()
        for suffix in [" llc", " inc", " inc.", " corp", " corp.", " co", " co.",
                       " ltd", " ltd.", " company", " services", " service",
                       " & sons", " and sons", " group", " enterprises"]:
            if n.endswith(suffix):
                n = n[:-len(suffix)].strip()
        return n.rstrip(".,;")

    _vendor_series = external["vendor"].dropna().astype(str)
    _normalized = _vendor_series.apply(_normalize_vendor_name)
    _normalized = _normalized[_normalized != ""]
    unique_vendors = _normalized.nunique()
    dispatched_vendor_names = sorted(
        external["vendor"].dropna().astype(str).str.strip().unique().tolist()
    )
    vendor_concentration = external["vendor"].value_counts(normalize=True).head(5) * 100
    top_vendor_pct = round(vendor_concentration.iloc[0], 1) if len(vendor_concentration) > 0 else 0

    # ── Internal Staff ──
    internal_count = int(maint["is_internal"].sum())
    internal_pct = round((internal_count / len(maint)) * 100, 1) if len(maint) > 0 else 0

    # ── Trade Distribution (Fix 2: sums to 100%, required trades always shown) ──
    trade_chart = build_trade_chart(maint, maintenance_wos) if maintenance_wos > 0 else []
    trade_distribution = {}
    for item in trade_chart:
        trade = item["trade"]
        trade_distribution[trade] = round(trade_distribution.get(trade, 0.0) + float(item["pct"]), 1)

    # Legacy trade_counts for other calculations
    trade_counts = maint["trade"].value_counts()

    # ── Trade Coverage (Fix 4: normalized matching + vendor name detection) ──
    raw_categories = maint["raw_category"].tolist() if "raw_category" in maint.columns else []
    category_covered, category_missing = check_trade_coverage(raw_categories)
    vendor_covered = check_vendor_trade_coverage(maint["vendor"].tolist())
    all_covered = set(category_covered) | vendor_covered
    # Separate core vs specialty trade coverage
    core_trades_lower = [t.lower() for t in CORE_TRADES]
    specialty_trades_set = set(TRADE_COVERAGE_MAP.keys()) - set(core_trades_lower)

    # Core coverage: only count trades that are in CORE_TRADES
    covered_core = [t for t in core_trades_lower if t in all_covered]
    missing_core = [t for t in core_trades_lower if t not in all_covered]

    # Specialty coverage: bonus, never penalized
    covered_specialty = [t for t in specialty_trades_set if t in all_covered]

    # covered_trades includes both for display; counts are core-only
    covered_trades = covered_core + covered_specialty
    missing_trades = missing_core  # Only report missing CORE trades

    # Category concentration (>25%)
    concentrated = {k: round(v, 1) for k, v in trade_distribution.items() if v > 25 and k != "Other"}

    # ── Repeat Units — group by property+unit key to avoid cross-property collisions ──
    if len(maint) > 0:
        prop_key = _safe_str(maint.get("property", pd.Series("", index=maint.index))).str.strip().str.lower()
        unit_key = _safe_str(maint.get("unit", pd.Series("", index=maint.index))).str.strip().str.lower()
        repeat_group_key = np.where(prop_key != "", prop_key + "||" + unit_key, unit_key)
    else:
        repeat_group_key = pd.Series("", index=maint.index)
    group_series = pd.Series(repeat_group_key, index=maint.index)
    unit_counts = group_series.value_counts()
    repeat_units = {}
    for group_key, count in unit_counts[unit_counts >= 3].head(5).items():
        unit_wos = maint[group_series == group_key]
        unit_trades = [
            t for t in unit_wos["trade"].value_counts().index.tolist()
            if str(t).strip()
        ][:3]
        unit_cost = unit_wos["amount"].sum() if unit_wos["amount"].notna().any() else None
        unit_first = unit_wos["created_date"].min()
        unit_last = unit_wos["created_date"].max()
        unit_span_days = (unit_last - unit_first).days if pd.notna(unit_first) and pd.notna(unit_last) else None

        # Use unit_label for display (includes property address when available)
        display_label = str(unit_wos["unit"].iloc[0]) if len(unit_wos) > 0 else "Unknown"
        if "unit_label" in unit_wos.columns:
            label_vals = unit_wos["unit_label"].dropna()
            label_vals = label_vals[label_vals.astype(str).str.strip() != ""]
            if len(label_vals) > 0:
                display_label = str(label_vals.iloc[0])

        # If label is just a bare number or unknown, try to prepend the property name
        if display_label.strip().isdigit() or display_label in ("Unknown", ""):
            if "property" in unit_wos.columns:
                prop_vals = unit_wos["property"].dropna()
                prop_vals = prop_vals[prop_vals.astype(str).str.strip() != ""]
                if len(prop_vals) > 0:
                    prop = str(prop_vals.iloc[0]).strip()
                    unit_val = display_label if display_label not in ("Unknown", "") else ""
                    display_label = f"{prop}, Unit {unit_val}" if unit_val else prop

        # Skip groups where we couldn't determine a meaningful label (blank unit data quality issue)
        if not display_label or display_label.strip() in ("", "Unknown", "nan"):
            continue

        repeat_units[display_label] = {
            "wo_count": int(count),
            "primary_trades": unit_trades,
            "total_cost": round(float(unit_cost), 2) if unit_cost and unit_cost > 0 else None,
            "span_days": int(unit_span_days) if unit_span_days is not None else None,
            "first_wo": unit_first.strftime("%b %d") if pd.notna(unit_first) else None,
            "last_wo": unit_last.strftime("%b %d") if pd.notna(unit_last) else None,
        }

    # ── Emergency Analysis ──
    emergencies = maint[maint["is_emergency"]]
    emergency_count = len(emergencies)
    emergency_after_hours = len(emergencies[emergencies["is_after_hours"]])

    # ── After-Hours Analysis (exclude inspections — they inflate the number) ──
    after_hours_count = int(maint["is_after_hours"].sum())
    after_hours_pct = round((after_hours_count / len(maint)) * 100, 1) if len(maint) > 0 else 0

    # ── Source Distribution ──
    source_all_unavailable = (maint["source"] == "data_not_available").all() if len(maint) > 0 else True
    if source_all_unavailable:
        source_pcts = {"note": "Source tracking not available in this export. Communication channel analysis requires the Source column."}
    else:
        source_counts = maint["source"].value_counts()
        # Filter out data_not_available from the distribution
        source_counts = source_counts[source_counts.index != "data_not_available"]
        source_pcts = (source_counts / source_counts.sum() * 100).round(1).to_dict() if len(source_counts) > 0 else {}

    # ── Cost Analysis ──
    cost_data = maint[maint["amount"].notna() & (maint["amount"] > 0)]
    avg_cost = round(float(cost_data["amount"].mean()), 2) if len(cost_data) > 0 else None
    median_cost = round(float(cost_data["amount"].median()), 2) if len(cost_data) > 0 else None
    cost_data_available = len(cost_data) > 0

    # ── NTE from PMS (if available) ──
    ntes = None
    if "maintenance_limit" in maint.columns:
        limits = maint["maintenance_limit"].dropna().unique()
        if len(limits) > 0:
            ntes = sorted([float(l) for l in limits])

    # ── Data Quality Assessment ──
    data_quality = assess_data_quality(maint, std, config)

    # ── Volume Benchmarking (WOs per door) ──
    wo_per_door_monthly = round(monthly_avg / door_count, 3) if door_count > 0 else None
    wo_per_door_annual = round(wo_per_door_monthly * 12, 1) if wo_per_door_monthly else None
    if wo_per_door_annual:
        if wo_per_door_annual < 3:
            volume_assessment = "low"
        elif wo_per_door_annual <= 6:
            volume_assessment = "normal"
        else:
            volume_assessment = "high"
    else:
        volume_assessment = None

    # ── Category Volume Anomalies ──
    high_volume_trades = {}
    if door_count > 0 and months_spanned > 0:
        for trade_name, count in trade_counts.items():
            rate_per_door_annual = (count / door_count / months_spanned) * 12
            if rate_per_door_annual > 0.36:
                high_volume_trades[trade_name] = {
                    "count": int(count),
                    "rate_per_door_annual": round(rate_per_door_annual, 2),
                    "pct_of_total": round(count / len(maint) * 100, 1),
                }

    # ── Reactive vs. Preventive Ratio ──
    if source_all_unavailable:
        reactive_pct = None  # Can't determine without source data
    else:
        reactive_count = len(maint[maint["source"].isin(["resident", "staff_created"])])
        reactive_pct = round(reactive_count / len(maint) * 100, 1) if len(maint) > 0 else None

    # Estimate-heavy detection
    estimate_count = len(maint[_safe_str(maint["raw_status"]).str.lower().str.strip().isin(
        ["estimating", "estimate requested", "estimated", "pending owner approval"]
    )])
    estimate_pct = round(estimate_count / len(maint) * 100, 1) if len(maint) > 0 else 0

    # Unit turn detection (AppFolio)
    unit_turn_count = len(maint[maint["source"] == "unit_turn"]) if "unit_turn" in maint["source"].values else 0

    # ── Seasonal Patterns ──
    seasonal_data = None
    if maint["created_date"].notna().any():
        monthly_volumes = maint.groupby(maint["created_date"].dt.to_period("M")).size()
        if len(monthly_volumes) >= 6:
            avg_monthly = monthly_volumes.mean()
            seasonal_spikes = {}
            for period, vol in monthly_volumes.items():
                if vol > avg_monthly * 1.5:
                    month_mask = maint["created_date"].dt.to_period("M") == period
                    month_trades = maint[month_mask]["trade"].value_counts().head(3)
                    seasonal_spikes[str(period)] = {
                        "volume": int(vol),
                        "vs_avg": round(vol / avg_monthly, 1),
                        "top_trades": month_trades.to_dict(),
                    }
            if seasonal_spikes:
                seasonal_data = {
                    "avg_monthly": round(float(avg_monthly), 1),
                    "spikes": seasonal_spikes,
                }

    # ── Internal staff availability ──
    internal_available = "assigned_to" not in missing
    if not internal_available:
        internal_count = 0
        internal_pct = 0.0

    return {
        "total_wos": total_wos,
        "maintenance_wos": maintenance_wos,
        "recurring_wos": recurring_wos,
        "cancelled_count": cancelled_count,
        "inspection_count": inspection_count,
        "non_maintenance_note": (
            f"{cancelled_count} cancelled/rejected, {inspection_count} inspections, "
            f"and {recurring_wos} recurring WOs filtered from core metrics"
        ) if total_filtered > 0 else None,
        "total_filtered": total_filtered,
        "monthly_avg": monthly_avg,
        "date_range_days": date_range_days,
        "date_range_start": date_range_start.strftime("%B %d, %Y") if date_range_start else None,
        "date_range_end": date_range_end.strftime("%B %d, %Y") if date_range_end else None,
        "date_range_start_short": date_range_start.strftime("%b %d") if date_range_start else None,
        "date_range_end_short": date_range_end.strftime("%b %d") if date_range_end else None,
        "date_range_year": date_range_end.strftime("%Y") if date_range_end else None,
        "months_spanned": round(months_spanned, 1),
        "data_reliability": data_reliability,
        "reliability_warning": reliability_warning,
        "wo_per_door_monthly": wo_per_door_monthly,
        "wo_per_door_annual": wo_per_door_annual,
        "volume_assessment": volume_assessment,
        "open_wo_count": open_wo_count,
        "open_wo_rate_pct": open_wo_rate,
        "median_completion_days": median_completion_days,
        "completed_count": len(completed),
        "avg_first_response_hours": response_hours,
        "response_time_method": response_method,
        "response_time_note": response_note,
        "unique_vendors": unique_vendors,
        "top_vendor_pct": top_vendor_pct,
        "vendor_concentration": vendor_concentration.to_dict(),
        "dispatched_vendor_names": dispatched_vendor_names,
        "covered_trades": covered_trades,
        "missing_trades": missing_trades,
        "trades_covered_count": len(covered_core),
        "trades_required_count": len(CORE_TRADES),
        "specialty_trades_covered": covered_specialty,
        "internal_count": internal_count,
        "internal_pct": internal_pct,
        "trade_distribution": trade_distribution,
        "trade_chart": trade_chart,
        "concentrated_trades": concentrated,
        "high_volume_trades": high_volume_trades,
        "repeat_units": repeat_units,
        "emergency_count": emergency_count,
        "emergency_after_hours": emergency_after_hours,
        "after_hours_count": after_hours_count,
        "after_hours_pct": after_hours_pct,
        "after_hours_time_available": config.get("_has_time_data", True) if config else True,
        "source_distribution": source_pcts,
        "reactive_pct": reactive_pct,
        "estimate_heavy_pct": estimate_pct,
        "unit_turn_count": unit_turn_count,
        "seasonal_data": seasonal_data,
        "avg_cost": avg_cost,
        "median_cost": median_cost,
        "cost_data_available": cost_data_available,
        "pms_ntes": ntes,
        "data_quality": data_quality,
        "status_counts": {
            "completed": int((std["status"] == "completed").sum()),
            "open": int((std["status"] == "open").sum()),
            "in_progress": int((std["status"] == "in_progress").sum()),
            "cancelled": int((std["status"] == "cancelled").sum()),
            "unknown": int((std["status"] == "unknown").sum()),
        },
        "trade_distribution_sum": round(sum(trade_distribution.values()), 1) if trade_distribution else 0.0,
    }


def assess_data_quality(maint, all_wos, config=None):
    """Assess data quality issues that affect analysis reliability."""
    issues = []
    missing = config.get("_missing_fields", set()) if config else set()

    if len(maint) == 0:
        return ["No maintenance work orders found after filtering."]

    # Flag missing columns
    if "category" in missing:
        issues.append("Maintenance Category column not found. Trade classification uses description keywords only (lower confidence).")
    if "source" in missing:
        issues.append("Source column not found. Communication channel analysis not available.")
    if "assigned_to" in missing:
        issues.append("Work Order Assignee column not found. Internal staff detection not available.")
    if "requested_by" in missing:
        issues.append("Requested By column not found. Resident-initiated request identification not available.")
    if "amount" in missing:
        issues.append("Amount column not found. Cost analysis not available.")

    if maint["created_date"].isna().sum() > 0:
        pct = round(maint["created_date"].isna().sum() / len(maint) * 100, 1)
        issues.append(f"Missing created dates on {pct}% of WOs (affects response time and volume calculations)")

    close_null_completed = maint[(maint["status"] == "completed") & maint["close_date"].isna()]
    if len(close_null_completed) > 0:
        issues.append(f"{len(close_null_completed)} completed WOs have no close date (affects completion time calculation)")

    vendor_null = maint[maint["vendor"].isna() & ~maint["status"].isin(["open"])]
    if len(vendor_null) > len(maint) * 0.2:
        issues.append(f"{len(vendor_null)} non-open WOs have no vendor assigned (affects vendor coverage analysis)")

    if maint["description"].isna().sum() > len(maint) * 0.1:
        pct = round(maint["description"].isna().sum() / len(maint) * 100, 1)
        issues.append(f"{pct}% of WOs have no description (affects trade classification and emergency detection)")

    cost_available = maint["amount"].notna() & (maint["amount"] > 0)
    if cost_available.sum() < len(maint) * 0.1 and "amount" not in missing:
        issues.append("Less than 10% of WOs have cost data (NTE analysis will be limited)")

    if maint["created_date"].notna().any():
        range_days = (maint["created_date"].max() - maint["created_date"].min()).days
        if range_days < 180:
            issues.append(f"Data spans only {range_days} days. 12+ months recommended for reliable benchmarks.")

    cat_null = maint["raw_category"].isna().sum()
    if cat_null > len(maint) * 0.5 and "category" not in missing:
        pct = round(cat_null / len(maint) * 100, 1)
        issues.append(f"{pct}% of WOs have no category (trade classification relies on vendor name and description keywords)")

    # Check for unmapped statuses
    unknown_count = int((all_wos["status"] == "unknown").sum())
    if unknown_count > 0:
        unmapped_statuses = all_wos[all_wos["status"] == "unknown"]["raw_status"].value_counts().head(5)
        unmapped_str = ", ".join(f"{s} ({c})" for s, c in unmapped_statuses.items())
        issues.append(f"{unknown_count} WOs have unmapped statuses: {unmapped_str}")

    return issues


def _load_agnostic(uploaded_file):
    """
    Load a work order file using auto-detection (no PMS config needed).
    Returns (df, mapping, load_warnings).
    """
    import os
    warnings = []
    mapping_method = "rule-based"

    df = auto_load(uploaded_file)
    load_meta = df.attrs.get("load_metadata", {})

    # Step 1: Rule-based column mapping
    mapping, unmatched, missing_required = rule_based_mapping(df.columns)

    # Step 2: Structural detection for critical missing fields
    if missing_required:
        already_mapped_cols = set(mapping.values())
        for col in df.columns:
            if col in already_mapped_cols:
                continue
            # Auto-detect date columns
            if "created_date" in missing_required:
                try:
                    parsed = auto_parse_dates(df[col].head(20))
                    if parsed.notna().sum() / max(len(parsed), 1) > 0.5:
                        col_lower = str(col).lower()
                        if any(kw in col_lower for kw in ["creat", "open", "start", "submit", "request"]):
                            mapping["created_date"] = col
                            missing_required.remove("created_date")
                            already_mapped_cols.add(col)
                            continue
                except Exception:
                    pass
            # Auto-detect status columns (low cardinality, status-like values)
            if "status" in missing_required:
                try:
                    uniq = df[col].dropna().nunique()
                    if 2 <= uniq <= 30:
                        from app.parsers.pms_mappings import STATUS_NORMALIZE
                        vals_lower = df[col].dropna().astype(str).str.lower().str.strip().unique()
                        matches = sum(1 for v in vals_lower if v in STATUS_NORMALIZE)
                        if matches >= 2:
                            mapping["status"] = col
                            missing_required.remove("status")
                            already_mapped_cols.add(col)
                            continue
                except Exception:
                    pass

    # Step 3: AI fallback for remaining missing required fields
    if missing_required:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            ai_map = ai_mapping_fallback(df, missing_required, api_key)
            mapping.update(ai_map)
            if ai_map:
                mapping_method = "rule-based + AI fallback"
            # Recalculate what's still missing
            missing_required = [
                f for f in missing_required if f not in ai_map
            ]

    # Step 4: Validate mapped columns
    bad_fields = []
    for field, col in list(mapping.items()):
        if col not in df.columns:
            bad_fields.append(field)
            del mapping[field]
    if bad_fields:
        warnings.append(f"Mapped columns not found in data: {', '.join(bad_fields)}")

    if missing_required:
        warnings.append(
            f"Could not identify columns for: {', '.join(missing_required)}. "
            f"Analysis will adapt to available data."
        )

    mapping_info = {
        "method": mapping_method,
        "mapped_count": len(mapping),
        "expected_count": len([k for k in STANDARD_FIELDS.keys() if k != "property"]),
        "missing_required": list(missing_required),
        "load_metadata": load_meta,
    }
    return df, mapping, warnings, mapping_info


def _normalize_agnostic(df, mapping, client_info):
    """
    Normalize a DataFrame using auto-detected column mapping.
    Mirrors normalize_dataframe() but without PMS config dependency.
    """
    std = pd.DataFrame()

    def _col(field):
        col_name = mapping.get(field)
        if col_name and col_name in df.columns:
            return df[col_name]
        return pd.Series(np.nan, index=df.index)

    # Map columns
    std["wo_number"] = _col("wo_number")
    std["unit"] = _col("unit")
    std["property"] = _col("property")
    std["vendor"] = _col("vendor")
    std["raw_status"] = _col("status")
    std["amount"] = _col("amount")
    std["description"] = _col("description")
    std["assigned_to"] = _col("assigned_to")
    std["requested_by"] = _col("requested_by")
    std["raw_source"] = _col("source")
    std["raw_category"] = _col("category")
    std["priority"] = _col("priority")

    # Build unit_label: prefer property address, fall back to unit
    has_property = std["property"].notna().any() and not (std["property"] == std["unit"]).all()
    if has_property:
        def _build_label(row):
            prop = str(row["property"]).strip() if pd.notna(row["property"]) else ""
            unit = str(row["unit"]).strip() if pd.notna(row["unit"]) else ""
            if not prop:
                return unit or "Unknown"
            # If unit is a short code (not an address), append it
            if unit and len(unit) <= 10 and " " not in unit and unit != prop:
                return f"{prop}, Unit {unit}"
            return prop
        std["unit_label"] = std.apply(_build_label, axis=1)
    else:
        # No separate property column — use unit as-is
        std["unit_label"] = std["unit"].fillna("Unknown").astype(str)

    # Parse dates with auto-detection
    std["created_date"] = auto_parse_dates(_col("created_date"))
    std["close_date"] = auto_parse_dates(_col("close_date"))

    # Parse currency
    if std["amount"].dtype == object or std["amount"].dtype == "O":
        std["amount"] = auto_parse_currency(std["amount"])
    else:
        std["amount"] = pd.to_numeric(std["amount"], errors="coerce")

    # Normalize statuses
    std["status"] = auto_normalize_status(std["raw_status"])
    _resolve_unknown_status(std)

    # Track missing fields for downstream
    missing_fields = set()
    for field in ["category", "source", "requested_by", "assigned_to", "amount"]:
        if field not in mapping or _col(field).isna().all():
            missing_fields.add(field)

    # Build a minimal config-like dict for downstream compatibility
    compat_config = {
        "_missing_fields": missing_fields,
        "source_classification": {
            "recurring_values": ["recurring", "scheduled", "preventive", "pm"],
            "resident_values": ["tenant", "resident", "tenant portal", "online portal", "portal", "tenant request"],
            "internal_values": ["internal", "staff", "manager", "phone", "manual", "office"],
            "unit_turn_values": ["unit turn", "turnover", "make ready", "turn"],
        },
        "internal_staff_detection": {"method": "vendor_name_patterns"},
    }

    # Classify source
    std["source"] = classify_source(std, compat_config)

    # Detect internal staff
    std["is_internal"] = detect_internal_staff(std, compat_config, client_info)

    # Classify trade
    std["trade"] = classify_trades(std, compat_config)

    # Detect emergencies
    std["is_emergency"] = detect_emergencies(std)

    # Detect after-hours (guard against date-only timestamps)
    from app.parsers.column_mapper import has_time_component
    std["is_after_hours"] = False
    has_time_data = False
    if std["created_date"].notna().any():
        if has_time_component(std["created_date"]):
            has_time_data = True
            std["hour"] = std["created_date"].dt.hour
            std["weekday"] = std["created_date"].dt.weekday
            std["is_after_hours"] = (std["hour"] < 8) | (std["hour"] >= 18) | (std["weekday"] >= 5)
        else:
            # Date-only: can detect weekend WOs but NOT time-of-day
            std["weekday"] = std["created_date"].dt.weekday
            std["is_after_hours"] = std["weekday"] >= 5

    compat_config["_has_time_data"] = has_time_data

    # Detect inspections
    std["is_inspection"] = std["trade"] == "Inspections"
    if std["description"].notna().any():
        desc_lower = _safe_str(std["description"]).str.lower().str.strip()
        kw_pattern = "|".join(INSPECTION_KEYWORDS)
        std["is_inspection"] = std["is_inspection"] | desc_lower.str.contains(kw_pattern, na=False)
    # Fallback: vendor name contains "inspection"
    if std["vendor"].notna().any():
        vendor_lower = _safe_str(std["vendor"]).str.lower().str.strip()
        std["is_inspection"] = std["is_inspection"] | vendor_lower.str.contains("inspection", na=False)
    # Fallback: raw status indicates inspection (e.g. "Inspection Pending PM Review")
    if std["raw_status"].notna().any():
        raw_status_lower = _safe_str(std["raw_status"]).str.lower().str.strip()
        std["is_inspection"] = std["is_inspection"] | raw_status_lower.str.contains("inspection", na=False)

    # Filter
    std["is_cancelled"] = std["status"] == "cancelled"
    std["is_maintenance"] = ~std["is_inspection"] & ~std["is_cancelled"]

    # Detect recurring WOs
    std["is_recurring"] = std["source"] == "recurring"
    # Check for a dedicated "Recurring" column (e.g. AppFolio Yes/No)
    for col in df.columns:
        if str(col).lower().strip() == "recurring" and col in df.columns:
            recurring_vals = df[col].astype(str).str.lower().str.strip()
            std["is_recurring"] = std["is_recurring"] | recurring_vals.isin(["yes", "true", "1", "y"])
            break
    # Do not infer recurring WOs when source tracking is unavailable.
    # Spec requirement: recurring filtering depends on explicit source data.

    return std, compat_config


def _build_validation_summary(file_name, file_format, header_row, metrics, config=None, mapping_info=None):
    """Build Section 12 validation summary and human-readable log block."""
    missing_fields = sorted(list(config.get("_missing_fields", set()))) if config else []
    status_counts = metrics.get("status_counts", {})

    if mapping_info:
        mapped = mapping_info.get("mapped_count", 0)
        expected = mapping_info.get("expected_count", 0)
        mapping_method = mapping_info.get("method", "rule-based")
    else:
        mapped = config.get("_columns_found", 0) if config else 0
        expected = config.get("_columns_expected", 0) if config else 0
        mapping_method = "pms-config"

    date_range = (
        f"{metrics.get('date_range_start', 'N/A')} to {metrics.get('date_range_end', 'N/A')} "
        f"({metrics.get('date_range_days', 0)} days)"
    )

    lines = [
        "=== DATA VALIDATION ===",
        f"File: {file_name}",
        f"Format: {file_format}",
        f"Rows loaded: {metrics.get('total_wos', 0)}",
        f"Header row detected at: row {header_row}",
        f"Columns mapped: {mapped} of {expected} (method: {mapping_method})",
        f"Missing columns: {missing_fields if missing_fields else 'None'}",
        f"Date range: {date_range}",
        "",
        "Filtering:",
        f"  Cancelled/Dup/Rejected: {metrics.get('cancelled_count', 0)}",
        f"  Inspections: {metrics.get('inspection_count', 0)}",
        f"  Recurring: {metrics.get('recurring_wos', 0)}",
        f"  Total filtered: {metrics.get('total_filtered', 0)}",
        f"  Maintenance WOs: {metrics.get('maintenance_wos', 0)}",
        "",
        "Status mapping:",
        f"  completed: {status_counts.get('completed', 0)}",
        f"  open: {status_counts.get('open', 0)}",
        f"  in_progress: {status_counts.get('in_progress', 0)}",
        f"  cancelled: {status_counts.get('cancelled', 0)} (already filtered)",
        f"  unknown: {status_counts.get('unknown', 0)}",
        "",
        f"Trade distribution sum: {metrics.get('trade_distribution_sum', 0.0)}% (must be 100.0%)",
        f"Vendor count: {metrics.get('unique_vendors', 0)}",
        f"Trade coverage: {metrics.get('trades_covered_count', 0)} of {metrics.get('trades_required_count', len(CORE_TRADES))}",
    ]
    return {
        "file": file_name,
        "format": file_format,
        "header_row_detected": header_row,
        "columns_mapped": mapped,
        "columns_expected": expected,
        "mapping_method": mapping_method,
        "missing_columns": missing_fields,
        "date_range_start": metrics.get("date_range_start"),
        "date_range_end": metrics.get("date_range_end"),
        "date_range_days": metrics.get("date_range_days"),
        "filtering": {
            "cancelled_dup_rejected": metrics.get("cancelled_count", 0),
            "inspections": metrics.get("inspection_count", 0),
            "recurring": metrics.get("recurring_wos", 0),
            "total_filtered": metrics.get("total_filtered", 0),
            "maintenance_wos": metrics.get("maintenance_wos", 0),
        },
        "status_mapping": status_counts,
        "trade_distribution_sum": metrics.get("trade_distribution_sum", 0.0),
        "vendor_count": metrics.get("unique_vendors", 0),
        "trade_coverage": {
            "covered": metrics.get("trades_covered_count", 0),
            "required": metrics.get("trades_required_count", 12),
        },
        "log_block": "\n".join(lines),
    }


def process_work_orders_agnostic(uploaded_file, client_info):
    """
    Full agnostic pipeline: auto-detect columns → normalize → compute metrics.
    Used when PMS platform is unknown or not in PMS_CONFIGS.
    """
    df, mapping, load_warnings, mapping_info = _load_agnostic(uploaded_file)
    std, config = _normalize_agnostic(df, mapping, client_info)
    metrics = compute_metrics(std, client_info, config)
    metrics["load_warnings"] = load_warnings
    metrics["pms_platform"] = "auto_detected"
    metrics["column_mapping"] = mapping
    metrics["column_mapping_info"] = mapping_info
    file_name = getattr(uploaded_file, "name", "uploaded_file")
    load_meta = mapping_info.get("load_metadata", {})
    validation = _build_validation_summary(
        file_name=file_name,
        file_format=load_meta.get("file_format", "Unknown"),
        header_row=load_meta.get("header_row_detected", 0),
        metrics=metrics,
        config=config,
        mapping_info=mapping_info,
    )
    metrics["validation"] = validation
    return metrics


def process_work_orders(uploaded_file, pms_platform, client_info):
    """
    Full pipeline: load → normalize → compute metrics.

    If the PMS platform has a known config, uses the structured path.
    Otherwise, falls back to auto-detection via column_mapper.

    Args:
        uploaded_file: raw bytes, BytesIO, or file-like object
        pms_platform: "AppFolio" | "RentVine" | etc., or None/"Other"
        client_info: dict with company_name, door_count, property_count, etc.

    Returns:
        dict with all computed metrics ready for Stage 3 (AI interpretation)
    """
    import io as _io

    # Normalize platform key
    pms_key = pms_platform.lower().replace(" ", "") if pms_platform else None

    # Check for a known PMS config
    config = PMS_CONFIGS.get(pms_key) if pms_key else None

    def _should_fallback_to_agnostic(metrics_dict):
        """Detect suspicious structured-path outputs and trigger agnostic retry."""
        if not metrics_dict:
            return True
        # If a structured parse yielded no usable created dates, date-range math is invalid.
        if (metrics_dict.get("date_range_days") or 0) <= 0:
            return True
        # If all rows are treated as maintenance and dates are missing, structured mapping likely mismatched.
        if metrics_dict.get("maintenance_wos", 0) >= metrics_dict.get("total_wos", 0) and (
            metrics_dict.get("date_range_start") is None or metrics_dict.get("date_range_end") is None
        ):
            return True
        return False

    if config:
        # ── Structured PMS path ──
        # Extract raw bytes
        if isinstance(uploaded_file, bytes):
            file_bytes = uploaded_file
        elif isinstance(uploaded_file, _io.BytesIO):
            file_bytes = uploaded_file.getvalue()
        elif hasattr(uploaded_file, "read"):
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
            file_bytes = uploaded_file.read()
        else:
            raise ValueError(f"Cannot read uploaded file: {type(uploaded_file)}")

        buf = _io.BytesIO(file_bytes)
        try:
            df, loaded_config, warnings = load_work_orders(buf, pms_key)
            std = normalize_dataframe(df, loaded_config, client_info)
            metrics = compute_metrics(std, client_info, loaded_config)
            metrics["load_warnings"] = warnings
            metrics["pms_platform"] = pms_key
            file_name = getattr(uploaded_file, "name", "uploaded_file")
            file_ext = file_name.rsplit(".", 1)[-1].upper() if "." in file_name else "UNKNOWN"
            validation = _build_validation_summary(
                file_name=file_name,
                file_format=file_ext,
                header_row=loaded_config.get("skip_rows", 0),
                metrics=metrics,
                config=loaded_config,
                mapping_info=None,
            )
            metrics["validation"] = validation

            if _should_fallback_to_agnostic(metrics):
                agnostic_metrics = process_work_orders_agnostic(file_bytes, client_info)
                agnostic_metrics["pms_platform"] = pms_key
                agnostic_metrics.setdefault("load_warnings", [])
                agnostic_metrics["load_warnings"].append(
                    "Structured PMS mapping produced invalid date range; auto-detected parser was used."
                )
                return agnostic_metrics
            return metrics
        except Exception:
            # If the declared PMS path fails (e.g., JSON payload with no extension),
            # fall back to the agnostic parser.
            metrics = process_work_orders_agnostic(file_bytes, client_info)
            metrics["pms_platform"] = pms_key
            return metrics
    else:
        # ── Agnostic auto-detection path ──
        metrics = process_work_orders_agnostic(uploaded_file, client_info)
        if pms_key:
            metrics["pms_platform"] = pms_key
        return metrics
