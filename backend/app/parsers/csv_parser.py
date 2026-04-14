"""Parse CSV/Excel uploads into Pydantic models."""
import io
from datetime import datetime
from typing import Optional

import pandas as pd

from app.models.input_data import WorkOrder, Vendor, Property
from app.parsers.field_mapper import map_columns
from app.utils.date_parsing import auto_parse_datetime_value


def _detect_header_row(file_bytes: bytes, encoding: str = "utf-8") -> int:
    """Detect which row contains the actual column headers.

    Many PMS exports (especially AppFolio) have title rows, filter descriptions,
    and blank rows before the actual data. We find the row with the most
    non-empty cells that looks like a header row.
    """
    try:
        text = file_bytes.decode(encoding)
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1")

    lines = text.split("\n")
    best_row = 0
    best_score = 0

    # Known header keywords that indicate the real header row
    header_keywords = {
        "work order", "date created", "status", "vendor", "category",
        "unit", "description", "amount", "property", "trade", "phone",
        "email", "address", "maintenance",
    }

    for i, line in enumerate(lines[:20]):  # Only check first 20 rows
        line_lower = line.lower()
        # Count how many header keywords appear in this line
        score = sum(1 for kw in header_keywords if kw in line_lower)
        # Also check for comma-separated fields (real data rows have many commas)
        comma_count = line.count(",")
        if score > best_score and comma_count >= 3:
            best_score = score
            best_row = i

    return best_row


def _detect_excel_header_row(file_bytes: bytes, engine: str = "openpyxl") -> int:
    """Detect which row contains actual column headers in an Excel file.

    PMS exports (RentVine, AppFolio, etc.) often have title rows, date-filter
    descriptions, and blank rows before the real column headers. We read the
    first 20 rows with no header and score each row by how many cells look
    like header labels (non-numeric strings with known keywords).
    """
    try:
        preview = pd.read_excel(
            io.BytesIO(file_bytes), header=None, nrows=20, engine=engine
        )
    except Exception:
        return 0

    header_keywords = {
        "work order", "date", "status", "vendor", "category", "unit",
        "description", "amount", "property", "trade", "phone", "email",
        "address", "maintenance", "created", "closed", "completed",
        "assigned", "priority", "source", "requested", "number",
        "contractor", "cost", "paid", "type", "name", "notes",
    }

    best_row = 0
    best_score = 0

    for i, row in preview.iterrows():
        non_null = row.dropna()
        if len(non_null) < 3:
            continue  # Skip rows with too few values (blanks / title rows)

        score = 0
        string_count = 0
        for val in non_null:
            val_str = str(val).strip().lower()
            if val_str and not val_str.replace(".", "").replace("-", "").isdigit():
                string_count += 1
            for kw in header_keywords:
                if kw in val_str:
                    score += 1
                    break  # One keyword match per cell is enough

        # Good header rows: mostly strings, multiple keyword hits
        if score > best_score and string_count >= 3:
            best_score = score
            best_row = i

    return best_row


def _read_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Read a CSV or Excel file into a DataFrame.

    Handles PMS-specific quirks:
    - Header rows (AppFolio puts title/filter info before data)
    - Multi-line quoted fields
    - Various encodings
    """
    lower = filename.lower()
    if lower.endswith((".xlsx", ".xls")):
        engine = "xlrd" if lower.endswith(".xls") else "openpyxl"
        # Detect header row: PMS exports often have title/filter rows before data
        header_row = _detect_excel_header_row(file_bytes, engine)
        df = pd.read_excel(io.BytesIO(file_bytes), header=header_row, engine=engine)
        df = df.dropna(how="all").dropna(axis=1, how="all")
        return df

    # CSV handling with header detection
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            # Detect where the real header row is
            header_row = _detect_header_row(file_bytes, encoding)

            df = pd.read_csv(
                io.BytesIO(file_bytes),
                encoding=encoding,
                header=header_row,
                engine="python",
                on_bad_lines="skip",
                quoting=1,  # QUOTE_ALL — handles multi-line quoted fields
            )

            # Drop fully empty rows and columns
            df = df.dropna(how="all").dropna(axis=1, how="all")

            # If the first row after header looks like another header or blank, skip it
            if len(df) > 0:
                first_row = df.iloc[0]
                if all(pd.isna(v) or str(v).strip() == "" for v in first_row):
                    df = df.iloc[1:].reset_index(drop=True)

            return df

        except UnicodeDecodeError:
            continue
        except Exception:
            continue

    raise ValueError(f"Could not parse {filename}. Please ensure it is a valid CSV or Excel file.")


def _safe_datetime(val) -> Optional[datetime]:
    """Safely parse a value to datetime."""
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, pd.Timestamp):
        return val.to_pydatetime()
    return auto_parse_datetime_value(val)


def _safe_float(val) -> Optional[float]:
    """Safely parse a value to float."""
    if pd.isna(val) or val is None:
        return None
    try:
        # Handle currency strings like "$500.00"
        if isinstance(val, str):
            val = val.replace("$", "").replace(",", "").strip()
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_str(val) -> Optional[str]:
    """Safely convert to string, returning None for empty/NaN."""
    if pd.isna(val) or val is None:
        return None
    s = str(val).strip()
    return s if s else None


def parse_work_orders(file_bytes: bytes, filename: str) -> list[WorkOrder]:
    """Parse work order CSV/Excel into WorkOrder models."""
    df = _read_file(file_bytes, filename)

    # Map columns
    required = [
        "work_order_id", "created_date", "completed_date", "status",
        "category", "description", "vendor_name", "cost", "priority",
        "property_name", "unit",
    ]
    col_map = map_columns(list(df.columns), required)

    if "work_order_id" not in col_map and "created_date" not in col_map:
        # Try using index as ID if we at least have dates
        if "created_date" in col_map:
            col_map["work_order_id"] = None  # Will use index
        else:
            raise ValueError(
                f"Could not identify work order columns. Found: {list(df.columns)}. "
                f"Need at minimum: a date column and an ID column."
            )

    work_orders = []
    for idx, row in df.iterrows():
        wo_id = str(row[col_map["work_order_id"]]) if col_map.get("work_order_id") else str(idx)
        created = _safe_datetime(row.get(col_map.get("created_date", ""), None))

        if created is None:
            continue  # Skip rows without a valid creation date

        work_orders.append(WorkOrder(
            work_order_id=wo_id,
            created_date=created,
            completed_date=_safe_datetime(row.get(col_map.get("completed_date", ""), None)),
            status=_safe_str(row.get(col_map.get("status", ""), "unknown")) or "unknown",
            category=_safe_str(row.get(col_map.get("category", ""), None)),
            description=_safe_str(row.get(col_map.get("description", ""), None)),
            vendor_name=_safe_str(row.get(col_map.get("vendor_name", ""), None)),
            cost=_safe_float(row.get(col_map.get("cost", ""), None)),
            priority=_safe_str(row.get(col_map.get("priority", ""), None)),
            property_name=_safe_str(row.get(col_map.get("property_name", ""), None)),
            unit=_safe_str(row.get(col_map.get("unit", ""), None)),
        ))

    return work_orders


def parse_vendors(file_bytes: bytes, filename: str) -> list[Vendor]:
    """Parse vendor CSV/Excel into Vendor models."""
    df = _read_file(file_bytes, filename)

    required = ["vendor_name", "trade", "phone", "email", "active", "assignment_count"]
    col_map = map_columns(list(df.columns), required)

    # Must have at least a vendor name column
    if "vendor_name" not in col_map:
        # Try first column as vendor name
        col_map["vendor_name"] = df.columns[0]

    vendors = []
    for _, row in df.iterrows():
        name = _safe_str(row.get(col_map.get("vendor_name", ""), None))
        if not name:
            continue

        active_val = row.get(col_map.get("active", ""), True)
        if isinstance(active_val, str):
            active = active_val.lower() in ("true", "yes", "active", "1", "y")
        else:
            active = bool(active_val) if not pd.isna(active_val) else True

        vendors.append(Vendor(
            vendor_name=name,
            trade=_safe_str(row.get(col_map.get("trade", ""), None)),
            phone=_safe_str(row.get(col_map.get("phone", ""), None)),
            email=_safe_str(row.get(col_map.get("email", ""), None)),
            active=active,
            assignment_count=int(_safe_float(row.get(col_map.get("assignment_count", ""), None)) or 0),
        ))

    return vendors


def parse_properties(file_bytes: bytes, filename: str) -> list[Property]:
    """Parse properties CSV/Excel into Property models."""
    df = _read_file(file_bytes, filename)

    required = ["property_name", "address", "unit_count", "property_type", "occupancy_rate"]
    col_map = map_columns(list(df.columns), required)

    if "property_name" not in col_map:
        col_map["property_name"] = df.columns[0]

    properties = []
    for _, row in df.iterrows():
        name = _safe_str(row.get(col_map.get("property_name", ""), None))
        if not name:
            continue

        unit_count = _safe_float(row.get(col_map.get("unit_count", ""), 1))
        occ_rate = _safe_float(row.get(col_map.get("occupancy_rate", ""), None))

        properties.append(Property(
            property_name=name,
            address=_safe_str(row.get(col_map.get("address", ""), None)),
            unit_count=int(unit_count) if unit_count else 1,
            property_type=_safe_str(row.get(col_map.get("property_type", ""), None)),
            occupancy_rate=occ_rate / 100 if occ_rate and occ_rate > 1 else occ_rate,
        ))

    return properties
