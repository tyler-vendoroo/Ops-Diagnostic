"""PMS-specific column mappings, status normalization, and classification configs.

Each PMS platform has different column names, date formats, and export quirks.
This config-driven approach means adding a new PMS requires only a new dict entry.
"""

PMS_CONFIGS = {

    "rentvine": {
        "file_type": "csv",
        "skip_rows": 3,  # Row 0: "Work Orders", Row 1: date filter, Row 2: blank
        "drop_trailing_nulls": False,
        "columns": {
            "wo_number":    "Work Order Number",
            "unit":         "Unit",
            "vendor":       "Vendor",
            "status":       "Work Order Status",
            "created_date": "Date Created",
            "close_date":   "Date Closed",
            "amount":       "Amount Paid",
            "description":  "Description",
            "category":     "Maintenance Category",
            "assigned_to":  "Work Order Assignee",
            "assigned_pm":  "Property Manager - Assigned Manager",
            "requested_by": "Requested By",
            "source":       "Source",
        },
        "parsing": {
            "date_format_created": "%m-%d-%Y %I:%M %p",
            "date_format_closed":  "%m-%d-%Y",
            "dates_are_native": False,
            "currency_strip": "$,",
            "zero_means_null": False,
        },
        "source_classification": {
            "recurring_values": ["Recurring"],
            "resident_values":  ["Portal"],
        },
        "internal_staff_detection": {
            "method": "vendor_equals_assignee",
        },
        "category_fallback_chain": ["category", "description_keywords"],
        "priority_field": None,
        "first_response_fields": [],
    },


    "appfolio": {
        "file_type": "xlsx",
        "skip_rows": 0,  # Sanitized export — headers at row 0
        "drop_trailing_nulls": True,
        "columns": {
            "wo_number":      "Work Order Number",
            "property":       "Property",
            "unit":           "Unit",
            "vendor":         "Vendor",
            "status":         "Status",
            "created_date":   "Created At",
            "close_date":     "Completed On",
            "amount":         "Amount",
            "description":    "Job Description",
            "category":       "Vendor Trade",
            "category_alt":   "Work Order Issue",
            "assigned_to":    "Assigned User",
            "requested_by":   "Primary Resident",
            "source":         "Work Order Type",
            "priority":       "Priority",
            "recurring":      "Recurring",
            "scheduled_start": "Scheduled Start",
            "created_by":     "Created By",
        },
        "parsing": {
            "date_format_created": None,
            "date_format_closed":  None,
            "dates_are_native": True,
            "currency_strip": "$,",
            "zero_means_null": True,
        },
        "source_classification": {
            "recurring_values": [],
            "resident_values":  ["Resident"],
            "internal_values":  ["Internal"],
            "unit_turn_values": ["Unit Turn"],
        },
        "internal_staff_detection": {
            "method": "vendor_name_patterns",
            "company_name_required": True,
        },
        "category_fallback_chain": ["category", "category_alt", "description_keywords"],
        "priority_field": "priority",
        "first_response_fields": ["scheduled_start"],
    },
}


# Status normalization map (universal across all PMS platforms)
STATUS_NORMALIZE = {
    # → "open"
    "new": "open", "pending": "open", "submitted": "open", "requested": "open",
    "pending vendor assignment": "open", "pending tenant response": "open",
    "pending owner approval": "open", "open": "open", "open - scheduled": "open",
    "estimating": "open", "estimate requested": "open",

    # → "in_progress"
    "in progress": "in_progress", "scheduled": "in_progress", "assigned": "in_progress",
    "vendor assigned": "in_progress", "work started": "in_progress", "waiting": "in_progress",
    "estimated": "in_progress", "inspection pending pm review": "in_progress",

    # → "completed"
    "completed": "completed", "closed": "completed", "done": "completed",
    "resolved": "completed", "bill created": "completed",
    "invoice received": "completed", "(vendor) completed - pending invoice": "completed",
    "complete - pending invoice": "completed", "owner to pay": "completed",
    "invoiced": "completed", "paid": "completed",
    "ready to bill": "completed",
    "completed no need to bill": "completed",
    "work done": "completed",

    # → "cancelled"
    "cancelled": "cancelled", "canceled": "cancelled", "voided": "cancelled",
    "duplicate": "cancelled", "rejected": "cancelled",

    # → "open" (paused/held)
    "on hold": "open",
}


# Trade classification keywords (used when PMS category field is empty)
TRADE_KEYWORDS = {
    "vendor_name": {
        "HVAC":            ["hvac", "heating", "cooling", "air conditioning", "air maxx"],
        "Plumbing":        ["plumb", "plumbing", "drain", "jet plumbing"],
        "Electrical":      ["electric", "electrical", "alchemy electric"],
        "Appliance Repair": ["appliance", "black & white appliance"],
        "Landscaping":     ["landscape", "lawn", "tree", "monster tree"],
        "Pest Control":    ["pest", "exterminator"],
        "Locksmith":       ["locksmith", "lock", "rekey"],
        "Roofing":         ["roof", "roofing"],
        "Painting":        ["paint", "painting", "hickey painting"],
        "Carpet Clean":    ["carpet"],
        "Garage Doors":    ["garage door"],
        "Gutters":         ["gutter"],
        "Fence/Gates":     ["fence", "fencing", "gate"],
        "Window & Glass":  ["glass", "window"],
        "Restoration":     ["restoration", "fire damage", "flood damage"],
        "Drywall":         ["drywall"],
        "General Handyman": ["handyman", "handy", "need a hand"],
        "Junk Removal":    ["junk", "hauling", "trash removal"],
        "Cleaning Service": ["cleaning", "clean", "maid"],
    },
    "description": {
        "Plumbing":        ["toilet", "leak", "faucet", "pipe", "water heater", "shower", "plumbing"],
        "Rooter/Drain":    ["drain clog", "sewer", "rooter", "clogged drain"],
        "Electrical":      ["outlet", "breaker", "wiring", "switch", "electrical panel"],
        "Appliance Repair": ["washer", "dryer", "fridge", "refrigerator", "dishwasher", "oven",
                            "stove", "microwave", "garbage disposal"],
        "HVAC":            ["furnace", "thermostat", "ac ", "no cooling", "no heat", "hvac",
                           "air conditioning", "heater"],
        "Window & Glass":  ["window broken", "cracked glass"],
        "Fence/Gates":     ["fence damaged", "gate broken"],
        "Roofing":         ["roof leak", "shingles", "flashing"],
        "Pest Control":    ["pest", "ants", "termites", "roaches", "mice", "rats"],
        "Painting":        ["paint", "painting", "patch n paint"],
        "Smoke Detectors": ["smoke detector", "carbon monoxide", "co detector"],
        "Inspections":     ["property survey", "inspection", "walkthrough"],
        "Doors/Windows":   ["door", "window", "screen"],
        "Pool":            ["pool", "spa"],
    },
}

# Emergency detection keywords
EMERGENCY_KEYWORDS = [
    "flood", "fire", "gas leak", "sewage backup", "sewage", "no heat",
    "no hot water", "no ac", "no cooling", "ceiling collapse", "electrical fire",
    "carbon monoxide", "burst pipe", "broken window security", "lockout safety",
    "water damage", "moisture accumulation", "active leak", "emergency",
]

# Emergency priority values (from PMS priority fields)
EMERGENCY_PRIORITIES = ["emergency", "urgent", "critical", "after hours", "p1"]

# Inspection keywords (filtered from maintenance metrics)
INSPECTION_KEYWORDS = [
    "walkthrough", "inspection", "property survey",
    "lease renewal property walkthrough", "move-in inspection",
    "move-out inspection", "annual inspection",
]

# Category normalization — merge PMS category variants into canonical trade names
CATEGORY_NORMALIZE = {
    "HVAC/Plumbing": "hvac",
    "Water Heater Repair/Replacement": "plumbing",
    "General Contractor": "handyperson",
    "Handyman": "handyperson",
    "Handyperson": "handyperson",
    "General Handyman": "handyperson",
    "Rooter/Drain": "rooter",
    "Drain": "rooter",
    "Sewer": "rooter",
    "Appliances": "appliance repair",
    "Appliance Repair": "appliance repair",
    "Plumbing": "plumbing",
    "Electrical": "electrical",
    "HVAC": "hvac",
    "Roofing": "roofing",
    "Pest Control": "pest control",
    "Landscaping": "landscaping",
    "Locksmith": "locksmith",
    "Keys/Locks": "locksmith",
    "Cleaning Service": "cleaning/turnover",
    "Cleaning": "cleaning/turnover",
    "Painting": "painting",
    "Flooring": "flooring",
    "Carpet Clean": "flooring",
    "Pool/Spa": "pool/spa",
    "Pool": "pool/spa",
}

# Trade coverage map — maps canonical trade names to PMS category variants
TRADE_COVERAGE_MAP = {
    "plumbing":          ["Plumbing", "HVAC/Plumbing", "Water Heater Repair/Replacement"],
    "electrical":        ["Electrical"],
    "rooter":            ["Rooter/Drain", "Drain", "Sewer"],
    "appliance repair":  ["Appliances", "Appliance Repair"],
    "handyperson":       ["Handyperson", "General Contractor", "Handyman", "General Handyman"],
    "hvac":              ["HVAC", "HVAC/Plumbing"],
    "roofing":           ["Roofing"],
    "pest control":      ["Pest Control"],
    "painting":          ["Painting"],
    "flooring":          ["Flooring", "Carpet Clean"],
    "landscaping":       ["Landscaping"],
    "pool/spa":          ["Pool/Spa", "Pool"],
    "locksmith":         ["Keys/Locks", "Locksmith"],
    "cleaning/turnover": ["Cleaning Service", "Cleaning", "Reno Custom Cleaning", "Smart Clean"],
}

# Vendor name keyword detection for trade coverage (supplements category-based matching)
VENDOR_TRADE_KEYWORDS = {
    "rooter":            ["rooter", "drain", "sewer", "clog"],
    "roofing":           ["roof", "roofing"],
    "locksmith":         ["lock", "key", "locksmith"],
    "hvac":              ["heating", "air conditioning", "hvac", "cooling"],
    "plumbing":          ["plumbing", "plumb"],
    "electrical":        ["electric"],
    "pest control":      ["pest", "exterminator"],
    "landscaping":       ["lawn", "landscape", "tree"],
    "appliance repair":  ["appliance"],
    "handyperson":       ["handyman", "handyperson", "handy", "maintenance"],
    "cleaning/turnover": ["cleaning", "clean", "maid", "janitorial", "turnover"],
    "flooring":          ["flooring", "floor", "carpet", "tile"],
    "pool/spa":          ["pool", "spa", "jacuzzi"],
}
