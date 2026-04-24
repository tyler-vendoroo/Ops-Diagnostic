"""PMS-agnostic column mapping with auto-detection and AI fallback.

Two-step approach:
1. Rule-based detection: Check headers against a known alias dictionary
2. AI fallback: If required fields still missing, send headers + sample rows to Claude

The processor never needs to know which PMS the file came from.
"""

import os
import io
import csv
import json
import pandas as pd
import numpy as np
from app.utils.date_parsing import auto_parse_dates


# ── Standard fields the processor needs ──────────────────────
STANDARD_FIELDS = {
    "wo_number":    {"required": True,  "description": "Unique work order identifier"},
    "unit":         {"required": True,  "description": "Unit number or identifier"},
    "property":     {"required": False, "description": "Property address or name"},
    "vendor":       {"required": True,  "description": "Vendor or contractor name"},
    "status":       {"required": True,  "description": "Current work order status"},
    "created_date": {"required": True,  "description": "Date/time the WO was created"},
    "close_date":   {"required": True,  "description": "Date/time the WO was completed or closed"},
    "amount":       {"required": False, "description": "Cost or amount paid"},
    "description":  {"required": True,  "description": "Work order description or notes"},
    "category":     {"required": False, "description": "Trade or maintenance category"},
    "assigned_to":  {"required": False, "description": "Internal staff assignee"},
    "requested_by": {"required": False, "description": "Person who submitted the request"},
    "source":       {"required": False, "description": "Channel or source (portal, phone, email, recurring)"},
    "priority":     {"required": False, "description": "Priority or urgency level"},
}

# ── Alias dictionary: lowercase variants → standard field ────
COLUMN_ALIASES = {
    # wo_number
    "wo_number":                "wo_number",
    "work order number":        "wo_number",
    "work order #":             "wo_number",
    "work order id":            "wo_number",
    "wo #":                     "wo_number",
    "wo id":                    "wo_number",
    "wo num":                   "wo_number",
    "order number":             "wo_number",
    "order #":                  "wo_number",
    "order id":                 "wo_number",
    "id":                       "wo_number",
    "number":                   "wo_number",
    "ticket":                   "wo_number",
    "ticket #":                 "wo_number",
    "ticket number":            "wo_number",
    "ticket id":                "wo_number",
    "task id":                  "wo_number",
    "request #":                "wo_number",
    "request number":           "wo_number",
    "service request":          "wo_number",
    "sr #":                     "wo_number",
    "maintenance request #":    "wo_number",
    "wo#":                      "wo_number",
    "wo entity id":             "wo_number",

    # unit (short identifier — apartment number, unit code)
    "unit":                     "unit",
    "unit name":                "unit",
    "unit number":              "unit",
    "unit #":                   "unit",
    "unit id":                  "unit",
    "rental unit":              "unit",
    "apt":                      "unit",
    "apt #":                    "unit",
    "apartment":                "unit",
    "suite":                    "unit",

    # property (full address or property name)
    "property":                 "property",
    "property address":         "property",
    "property name":            "property",
    "address":                  "property",
    "location":                 "property",
    "building":                 "property",
    "building address":         "property",
    "site":                     "property",
    "site address":             "property",
    "street address":           "property",
    "full address":             "property",
    "rental address":           "property",
    "unit address":             "property",

    # vendor
    "vendor":                   "vendor",
    "vendor name":              "vendor",
    "contractor":               "vendor",
    "contractor name":          "vendor",
    "service provider":         "vendor",
    "assigned vendor":          "vendor",
    "technician":               "vendor",
    "tech":                     "vendor",
    "maintenance tech":         "vendor",
    "repair person":            "vendor",
    "company":                  "vendor",
    "service company":          "vendor",
    "vendors":                  "vendor",

    # status
    "status":                   "status",
    "work order status":        "status",
    "wo status":                "status",
    "order status":             "status",
    "current status":           "status",
    "state":                    "status",
    "ticket status":            "status",
    "request status":           "status",
    "task status":              "status",

    # created_date
    "date created":             "created_date",
    "created at":               "created_date",
    "created date":             "created_date",
    "created":                  "created_date",
    "create date":              "created_date",
    "open date":                "created_date",
    "opened":                   "created_date",
    "opened date":              "created_date",
    "date opened":              "created_date",
    "submitted":                "created_date",
    "submitted date":           "created_date",
    "date submitted":           "created_date",
    "request date":             "created_date",
    "date requested":           "created_date",
    "reported date":            "created_date",
    "entry date":               "created_date",
    "start date":               "created_date",

    # close_date
    "date closed":              "close_date",
    "closed date":              "close_date",
    "closed":                   "close_date",
    "close date":               "close_date",
    "completed on":             "close_date",
    "completed date":           "close_date",
    "date completed":           "close_date",
    "completion date":          "close_date",
    "resolved date":            "close_date",
    "date resolved":            "close_date",
    "finish date":              "close_date",
    "end date":                 "close_date",
    "actual end date":          "close_date",

    # amount
    "amount":                   "amount",
    "amount paid":              "amount",
    "total amount":             "amount",
    "cost":                     "amount",
    "total cost":               "amount",
    "invoice amount":           "amount",
    "price":                    "amount",
    "total price":              "amount",
    "estimated amount":         "amount",
    "actual cost":              "amount",
    "bill amount":              "amount",
    "charge":                   "amount",
    "expense":                  "amount",
    "payment":                  "amount",
    "invoice total":            "amount",

    # description
    "description":              "description",
    "short description":        "description",
    "job description":          "description",
    "work description":         "description",
    "details":                  "description",
    "notes":                    "description",
    "summary":                  "description",
    "issue":                    "description",
    "issue description":        "description",
    "problem":                  "description",
    "problem description":      "description",
    "request description":      "description",
    "wo description":           "description",
    "task description":         "description",
    "scope of work":            "description",
    "scope":                    "description",
    "comments":                 "description",
    "work performed":           "description",
    "resolution":               "description",

    # category
    "category":                 "category",
    "maintenance category":     "category",
    "work order category":      "category",
    "type":                     "category",
    "work type":                "category",
    "work order type":          "source",
    "trade":                    "category",
    "vendor trade":             "category",
    "service type":             "category",
    "issue type":               "category",
    "work order issue":         "category",
    "maintenance type":         "category",
    "repair type":              "category",
    "job type":                 "category",
    "task type":                "category",
    "classification":           "category",
    "subcategory":              "category",

    # assigned_to
    "assigned to":              "assigned_to",
    "assignee":                 "assigned_to",
    "assigned user":            "assigned_to",
    "work order assignee":      "assigned_to",
    "assigned manager":         "assigned_to",
    "property manager":         "assigned_to",
    "property manager - assigned manager": "assigned_to",
    "manager":                  "assigned_to",
    "coordinator":              "assigned_to",
    "assigned staff":           "assigned_to",
    "responsible person":       "assigned_to",
    "owner":                    "assigned_to",

    # requested_by
    "requested by":             "requested_by",
    "requester":                "requested_by",
    "requesting resident":      "requested_by",
    "resident":                 "requested_by",
    "resident name":            "requested_by",
    "tenant":                   "requested_by",
    "tenant name":              "requested_by",
    "reported by":              "requested_by",
    "submitted by":             "requested_by",
    "caller":                   "requested_by",
    "contact":                  "requested_by",

    # source
    "source":                   "source",
    "work order source":        "source",
    "channel":                  "source",
    "origin":                   "source",
    "request source":           "source",
    "entry method":             "source",
    "how received":             "source",
    "received via":             "source",
    "submission method":        "source",

    # priority
    "priority":                 "priority",
    "urgency":                  "priority",
    "severity":                 "priority",
    "priority level":           "priority",
    "urgency level":            "priority",
    "emergency":                "priority",
    "rush":                     "priority",
}


# ═══════════════════════════════════════════════════════════════
# File Loading
# ═══════════════════════════════════════════════════════════════

_ALIAS_SET = set(COLUMN_ALIASES.keys())


def find_header_row(raw_df):
    """
    Find the row that contains column headers using alias-based scoring.
    For each candidate row, score cells against known COLUMN_ALIASES.
    Exact alias match = 3 pts, header-like string = 1 pt.
    Returns the row index with the highest score.
    """
    best_row = 0
    best_score = -1

    for i in range(min(20, len(raw_df))):
        row = raw_df.iloc[i]
        non_null = row.dropna()
        if len(non_null) < 3:
            continue
        score = 0
        for v in non_null:
            if not isinstance(v, str):
                continue
            v_clean = v.lower().strip()
            if v_clean in _ALIAS_SET:
                score += 3  # Strong signal: exact alias match
            elif len(v) < 50 and not v.replace('.', '').replace('-', '').replace(',', '').isdigit():
                score += 1  # Weak signal: looks like a header
        if score > best_score:
            best_score = score
            best_row = i

    return best_row


def _extract_file_bytes(uploaded_file):
    """Return (file_bytes, file_name) from uploaded input."""
    file_name = getattr(uploaded_file, "name", "") if uploaded_file is not None else ""
    if isinstance(uploaded_file, bytes):
        return uploaded_file, file_name
    if isinstance(uploaded_file, io.BytesIO):
        return uploaded_file.getvalue(), file_name
    if hasattr(uploaded_file, "read"):
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        return uploaded_file.read(), file_name
    raise ValueError(f"Cannot read uploaded file: {type(uploaded_file)}")


def _detect_delimited_header_row(text, delimiter):
    """Detect header row index for CSV/TSV text."""
    lines = text.splitlines()
    best_row = 0
    best_score = -1

    for i, line in enumerate(lines[:20]):
        if delimiter not in line:
            continue
        try:
            fields = next(csv.reader([line], delimiter=delimiter))
        except Exception:
            fields = [f.strip().strip('"') for f in line.split(delimiter)]
        if len(fields) < 3:
            continue

        score = 0
        for field in fields:
            f = str(field).strip().lower()
            if not f:
                continue
            if f in _ALIAS_SET:
                score += 3
            elif len(f) < 50 and not f.replace(".", "").replace("-", "").replace(",", "").isdigit():
                score += 1
        if score > best_score:
            best_score = score
            best_row = i
    return best_row


def _score_header_record(fields):
    """Score a delimited record as a potential header row."""
    if len(fields) < 3:
        return -1

    score = 0
    for field in fields:
        f = str(field).strip().lower()
        if not f:
            continue
        if f in _ALIAS_SET:
            score += 3
        elif len(f) < 50 and not f.replace(".", "").replace("-", "").replace(",", "").isdigit():
            score += 1
    return score


def _load_delimited_with_header(text, delimiter):
    """Load CSV/TSV by detecting header from parsed records (handles multiline cells)."""
    records = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    if not records:
        return pd.DataFrame(), 0

    best_idx = 0
    best_score = -1
    for i, record in enumerate(records[:30]):
        score = _score_header_record(record)
        if score > best_score:
            best_score = score
            best_idx = i

    header = [str(h).strip() for h in records[best_idx]]
    data_rows = records[best_idx + 1:]
    if not data_rows:
        return pd.DataFrame(columns=header), best_idx

    max_len = max(len(header), max(len(r) for r in data_rows))
    if len(header) < max_len:
        header = header + [f"Unnamed: {i}" for i in range(len(header), max_len)]

    normalized_rows = []
    for row in data_rows:
        if len(row) < max_len:
            row = row + [""] * (max_len - len(row))
        elif len(row) > max_len:
            row = row[:max_len]
        normalized_rows.append(row)

    df = pd.DataFrame(normalized_rows, columns=header[:max_len])
    return df, best_idx


def _load_json_rows(json_obj):
    """Flatten RentVine-style JSON payloads into a DataFrame."""
    rows = []

    if isinstance(json_obj, list):
        rows = json_obj
    elif isinstance(json_obj, dict):
        if isinstance(json_obj.get("rows"), list):
            for row in json_obj["rows"]:
                if isinstance(row, dict) and isinstance(row.get("data"), dict):
                    rows.append(row["data"])
                elif isinstance(row, dict):
                    rows.append(row)
        elif isinstance(json_obj.get("data"), list):
            rows = json_obj["data"]
        else:
            rows = [json_obj]

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.dropna(how="all").dropna(axis=1, how="all")


def auto_load(uploaded_file):
    """
    Load a work order export, auto-detecting format and header row.
    Handles: CSV, XLSX, XLS, TSV
    Handles: metadata header rows (skips non-data rows at top)

    Args:
        uploaded_file: Streamlit UploadedFile or file path string

    Returns: DataFrame
    """
    file_bytes, file_name = _extract_file_bytes(uploaded_file)
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    metadata = {
        "file_format": None,
        "header_row_detected": 0,
    }

    # Prefer extension-informed strategy order, then fallback.
    strategy_order = []
    if ext in ("xlsx", "xls", "csv", "tsv", "json"):
        strategy_order.append(ext)
    strategy_order.extend(["xlsx", "xls", "json", "csv", "tsv"])
    ordered = []
    for s in strategy_order:
        if s not in ordered:
            ordered.append(s)

    errors = []
    for strategy in ordered:
        try:
            buf = io.BytesIO(file_bytes)
            if strategy == "xlsx":
                raw = pd.read_excel(buf, header=None, nrows=20, engine="openpyxl")
                header_row = find_header_row(raw)
                buf = io.BytesIO(file_bytes)
                df = pd.read_excel(buf, skiprows=header_row, engine="openpyxl")
                metadata["file_format"] = "XLSX"
                metadata["header_row_detected"] = int(header_row)
            elif strategy == "xls":
                raw = pd.read_excel(buf, header=None, nrows=20, engine="xlrd")
                header_row = find_header_row(raw)
                buf = io.BytesIO(file_bytes)
                df = pd.read_excel(buf, skiprows=header_row, engine="xlrd")
                metadata["file_format"] = "XLS"
                metadata["header_row_detected"] = int(header_row)
            elif strategy == "json":
                payload = json.loads(file_bytes.decode("utf-8", errors="replace"))
                df = _load_json_rows(payload)
                metadata["file_format"] = "JSON"
                metadata["header_row_detected"] = 0
            elif strategy == "tsv":
                text = file_bytes.decode("utf-8", errors="replace")
                df, header_row = _load_delimited_with_header(text, "\t")
                metadata["file_format"] = "TSV"
                metadata["header_row_detected"] = int(header_row)
            else:
                # CSV
                text = file_bytes.decode("utf-8", errors="replace")
                df, header_row = _load_delimited_with_header(text, ",")
                metadata["file_format"] = "CSV"
                metadata["header_row_detected"] = int(header_row)

            if len(df.columns) >= 3 and len(df) > 0:
                break  # Successful parse
        except Exception as e:
            errors.append(f"{strategy}: {e}")
            continue
    else:
        raise ValueError(f"Could not parse file. Tried: {'; '.join(errors)}")

    # Drop fully empty rows/columns
    df = df.dropna(how='all').dropna(axis=1, how='all')
    metadata["rows_loaded"] = int(len(df))
    df.attrs["load_metadata"] = metadata

    return df


# ═══════════════════════════════════════════════════════════════
# Rule-Based Column Mapping
# ═══════════════════════════════════════════════════════════════

# Higher-priority aliases that should override first-match for a given field
_PREFERRED_ALIASES = {
    "category": {"trade", "vendor trade", "maintenance category", "category"},
}


def rule_based_mapping(columns):
    """
    Map column names to standard fields using the alias dictionary.
    Returns: (mapping dict, unmatched columns, missing required fields)
    """
    mapping = {}
    used_columns = set()

    for col in columns:
        col_lower = str(col).lower().strip()
        if col_lower in COLUMN_ALIASES:
            standard = COLUMN_ALIASES[col_lower]
            if standard not in mapping:  # First match wins
                mapping[standard] = col
                used_columns.add(col)
            elif standard in _PREFERRED_ALIASES and col_lower in _PREFERRED_ALIASES[standard]:
                # Upgrade: this column is a better match than the current one
                old_col = mapping[standard]
                used_columns.discard(old_col)
                mapping[standard] = col
                used_columns.add(col)

    unmatched = [col for col in columns if col not in used_columns]

    missing_required = []
    for field, info in STANDARD_FIELDS.items():
        if info["required"] and field not in mapping:
            missing_required.append(field)

    return mapping, unmatched, missing_required


# ═══════════════════════════════════════════════════════════════
# AI Fallback Mapping
# ═══════════════════════════════════════════════════════════════

AI_MAPPING_PROMPT = """You are mapping columns from a property management work order export to standard field names.

STANDARD FIELDS (map each column to one of these, or null if no match):
- wo_number: Unique work order identifier (number, ID, ticket)
- unit: Unit number or short identifier (apt number, unit code)
- property: Property address or name (full address, building name, location)
- vendor: Vendor or contractor name
- status: Current work order status (open, closed, in progress, etc.)
- created_date: When the work order was created
- close_date: When it was completed or closed
- amount: Cost, amount paid, invoice total
- description: Work order description, notes, scope
- category: Trade or maintenance category (plumbing, HVAC, etc.)
- assigned_to: Internal staff person assigned
- requested_by: Person who submitted the request (resident, tenant)
- source: How the request came in (portal, phone, email, recurring)
- priority: Priority or urgency level

HERE ARE THE COLUMN NAMES AND 3 SAMPLE ROWS:

{header_and_samples}

Return ONLY a JSON object mapping standard_field_name to the exact column header string.
If a standard field has no matching column, set its value to null.
Example: {{"wo_number": "WO #", "unit": "Property Address", "vendor": "Contractor", "status": "Current Status"}}
Do not include any other text."""


def ai_mapping_fallback(df, missing_fields, api_key=None):
    """
    Use Claude AI to map remaining unmapped columns.
    Only called when rule-based mapping can't find required fields.

    Returns: dict of {standard_field: column_name}
    """
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {}

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        sample = df.head(3).to_string(index=False)
        header_and_samples = f"COLUMNS: {list(df.columns)}\n\nSAMPLE DATA:\n{sample}"

        prompt = AI_MAPPING_PROMPT.format(header_and_samples=header_and_samples)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            timeout=15.0,
            messages=[{"role": "user", "content": prompt}],
        )

        ai_text = response.content[0].text.strip()
        ai_mapping = json.loads(ai_text)

        # Validate: only keep mappings where column actually exists
        # and reject duplicate column assignments
        validated = {}
        used_cols = set()
        for field, col in ai_mapping.items():
            if col and col in df.columns and field in STANDARD_FIELDS:
                if col not in used_cols:
                    validated[field] = col
                    used_cols.add(col)

        return validated

    except Exception as e:
        import logging
        logging.warning(f"AI column mapping failed: {e}")
        return {}


# ═══════════════════════════════════════════════════════════════
# Auto-Detection Utilities
# ═══════════════════════════════════════════════════════════════

def has_time_component(dt_series):
    """Return True if the datetime series contains meaningful time-of-day data.

    Date-only exports (e.g. "03/16/2026") get parsed as midnight (00:00:00).
    This function distinguishes real time data from date-only data.
    """
    valid = dt_series.dropna()
    if len(valid) == 0:
        return False
    times = valid.dt.time
    midnight = pd.Timestamp("00:00:00").time()
    midnight_pct = (times == midnight).sum() / len(times)
    # If >95% are midnight, timestamps are date-only
    return midnight_pct <= 0.95


def auto_parse_currency(series):
    """Parse currency values regardless of format ($, commas, etc.)."""
    if pd.api.types.is_numeric_dtype(series):
        return series

    cleaned = series.astype(str).str.replace(r'[$,\s]', '', regex=True)
    cleaned = cleaned.str.replace(r'^\((.*)\)$', r'-\1', regex=True)
    return pd.to_numeric(cleaned, errors='coerce')


def auto_normalize_status(status_series):
    """Normalize status values, handling unknowns with fuzzy matching."""
    from app.parsers.pms_mappings import STATUS_NORMALIZE

    safe = status_series.fillna("").astype(str).str.lower().str.strip()
    normalized = safe.map(STATUS_NORMALIZE)

    # For unmapped values, try substring matching
    unmapped_mask = normalized.isna() & (safe != "")
    if unmapped_mask.any():
        unmapped_values = safe[unmapped_mask].unique()
        for raw_lower in unmapped_values:
            if not raw_lower:
                continue
            for known, norm in STATUS_NORMALIZE.items():
                if known in raw_lower or raw_lower in known:
                    normalized[safe == raw_lower] = norm
                    break

    return normalized.fillna("unknown")
