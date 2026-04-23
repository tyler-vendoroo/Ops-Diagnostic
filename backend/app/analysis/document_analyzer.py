"""Analyze lease, PMA, and work order data using Claude API.

All three document types use Claude for extraction to ensure consistent,
structured output regardless of input format or PMS source.

Updated with deep SFR property management domain expertise:
- WO analyzer: trade classification hierarchy, internal team detection, repeat unit analysis
- Lease analyzer: 16 standard SFR maintenance policy area assessments
- PMA analyzer: extracted config values for Maintenance Book pre-build
"""
import json
import time
from typing import Optional

import anthropic

from app.config import settings
from app.models.analysis import DocumentAnalysis, DocumentSection, DocumentFinding

ANTHROPIC_API_KEY = settings.anthropic_api_key
ANTHROPIC_MODEL = settings.anthropic_model


# ═══════════════════════════════════════════════════════════════════
# WORK ORDER ANALYSIS — AI-powered field normalization & metrics
# ═══════════════════════════════════════════════════════════════════

WO_SYSTEM_PROMPT = """You are a senior property management operations analyst with 15+ years of experience analyzing maintenance work order data across every major PMS platform. You specialize in evaluating maintenance operations.

You are analyzing a work order export from a property management software system. Your job is to normalize this data (which may come from AppFolio, Buildium, RentManager, RentVine, Propertyware, Yardi, or others) into a consistent set of metrics for an Operations Analysis.

IMPORTANT: Never use the word "mold" in any output. Use "water damage" or "moisture accumulation" instead.

FIELD IDENTIFICATION
Different PMS systems use different column names, date formats, and status values. Before analyzing, identify:
- Which column contains work order dates (may be called: Created, Date, Opened, Submitted, Request Date)
- Which column contains status (may be: Status, State, Stage, Work Order Status)
- Which column contains vendor names (may be: Vendor, Assigned To, Contractor, Technician, Service Provider)
- Which column contains cost/amount (may be: Amount, Cost, Total, Invoice Amount, Actual Cost)
- Which column contains category/type (may be: Category, Type, Trade, Issue Type, Maintenance Type)
- Which column contains descriptions (may be: Description, Notes, Issue, Problem, Details, Summary)
- Which column contains property/address (may be: Property, Address, Unit, Location)

STATUS NORMALIZATION
Map all PMS-specific statuses to exactly one of these four values:
- open: New, Pending, Submitted, Assigned, Waiting, On Hold, Received, Requested
- in_progress: In Progress, Scheduled, In Transit, Work Started, Vendor Assigned, Parts Ordered
- completed: Completed, Closed, Done, Resolved, Paid, Invoiced, Bill Created, Finished, Cancelled Completed
- cancelled: Cancelled, Voided, Duplicate, Rejected, Withdrawn

TRADE CLASSIFICATION (use this hierarchy, stop at first match)
1. VENDOR NAME CLASSIFICATION: If vendor name contains a trade keyword, that overrides everything else.
   - fence, fencing, gate → Fence/Gates
   - roof, roofing → Roofing
   - hvac, heating, cooling, air conditioning → HVAC
   - plumb, plumbing → Plumbing
   - carpet → Carpet Clean
   - glass, window → Window & Glass Repair
   - electric, electrical → Electrical
   - appliance → Appliance Repair
   - landscape, lawn → Landscaping
   - pest, exterminator → Pest Control
   - locksmith, lock, rekey → Locksmith
   - garage door → Garage Doors
   - gutter → Gutters
   - restoration, fire damage, flood damage → Flood & Fire Restoration

2. WORK ORDER ISSUE/CATEGORY FIELD: If the PMS has a category or issue type field, use it.

3. DESCRIPTION KEYWORD ANALYSIS:
   - toilet, leak, faucet, pipe, water heater → Plumbing
   - drain clog, sewer, rooter → Rooter/Drain
   - outlet, breaker, wiring, switch, electrical panel → Electrical
   - washer, dryer, fridge, refrigerator, dishwasher, oven, stove, microwave, garbage disposal → Appliance Repair
   - furnace, thermostat, AC, no cooling, no heat, HVAC → HVAC
   - window broken, cracked glass → Window & Glass Repair
   - fence damaged, gate broken → Fence/Gates
   - roof leak, shingles, flashing → Roofing
   - pest, ants, termites, roaches, mice, rats → Pest Control
   - tree trimming, branches, tree removal → Tree Trimming
   - trash removal, junk haul, debris → Trash/Hauling

4. DEFAULT: If no match, classify as General Handyman.

Never classify trades using vague words like: repair, fix, service, work, job, maintenance, issue, problem.

INTERNAL MAINTENANCE TEAM DETECTION
These vendor names indicate internal staff, not external vendors:
- Names matching the client/property management company name
- "Maintenance Team", "In-House", "Internal", "Staff", "Company Maintenance"
- "Property Management" when it matches the client company
Flag these as internal and track their volume separately.

EMERGENCY WORK ORDER DETECTION
Flag work orders as emergency if they match any of:
- Priority field: Emergency, Urgent, Critical, After Hours, P1
- Description keywords: flood, fire, gas leak, sewage backup, no heat (winter), no hot water, no AC (summer extreme), ceiling collapse, electrical fire, carbon monoxide, burst pipe, broken window (security), lockout (safety concern)
- Created outside business hours (before 8am, after 6pm, weekends) AND contain urgency language

NTE / COST ANALYSIS
- Identify the cost/amount field and compute average cost per completed work order
- Flag any work orders with $0 or blank costs as potential NTE gaps
- If NTE or authorization amounts are visible, note the range and any inconsistencies
- Flag any work orders over $500 without clear approval indicators

AFTER-HOURS ANALYSIS
- Calculate what percentage of work orders were created outside M-F 8am-6pm
- Identify whether after-hours WOs have different completion patterns (longer time to first action, different vendors)
- Note if there is any evidence of after-hours dispatch capability vs. queuing until next business day

DATA QUALITY ASSESSMENT
Be specific about what is missing and how it affects analysis accuracy:
- Missing dates (prevents response time calculation)
- Blank vendor fields (affects vendor coverage analysis)
- No cost data (prevents NTE analysis)
- Inconsistent status values (affects open WO rate)
- Duplicate entries (inflates volume metrics)
- Short date range (less than 6 months reduces reliability)

KEY OBSERVATIONS
Generate 3-5 specific, data-driven insights. Examples of good observations:
- "High concentration of HVAC work orders (34%) suggests aging systems across the portfolio"
- "Top 2 vendors handle 61% of all work orders, creating significant single-vendor dependency"
- "23% of work orders created after hours but average first response for these is 14+ hours, indicating no after-hours dispatch capability"
- "Plumbing WOs average $380 per job while the flat NTE appears to be $500, leaving minimal margin for unexpected scope"
Bad observations (too vague, avoid these):
- "The portfolio has a mix of maintenance needs"
- "Some vendors are used more than others"
- "Response times could be improved"

CALCULATION PRECISION
- Use MEDIAN (not mean) for completion time and response time to avoid outlier distortion
- For open WO rate: count ALL currently open work orders (any status that is not completed or cancelled, regardless of creation date) and divide by the total door count. Open WO Rate = (total open WOs / total doors) × 100. This is a portfolio health metric, not a throughput metric. It measures how much unresolved maintenance is sitting per door. The door count comes from the client_info input, not from the WO data. If door count is not available in the data, flag it as required input and set open_wo_rate_pct to null.
- For monthly averages, calculate the actual number of months spanned by the data (not assume 12)

FIRST RESPONSE TIME — TRANSPARENT METHODOLOGY
First response time is the most valuable metric for the readiness report but also the hardest to calculate accurately from a standard WO export. Use this hierarchy and STOP at the first method that works. Report which method was used.

Method 1 (Best): DEDICATED RESPONSE FIELD
Look for columns named: Actual Start Date, First Response Date, Response Date, Start Date.
If found: calculate median hours between Created Date and this field.
Report as: "Calculated from [field name]"

Method 2: VENDOR ASSIGNMENT TIMESTAMP
Look for columns named: Vendor Assigned Date, Date Assigned, Assigned Date, Scheduled Date, Dispatch Date.
If found: calculate median hours between Created Date and this field.
Report as: "Estimated from vendor assignment timestamps (proxy for first action)"

Method 3: STATUS CHANGE TIMESTAMP
If the export has a Last Updated or Modified Date field, AND there are work orders where this date differs from Created Date by less than 48 hours, use the median of those gaps.
Report as: "Estimated from status change timestamps (less reliable)"

Method 4: NOT CALCULABLE
If none of the above fields exist, DO NOT ESTIMATE. Do not use the 15% heuristic or any other guess.
Set avg_first_response_hours to null.
Set response_time_method to "not_calculable".
Set response_time_note to a specific explanation of what fields are missing: "Work order export does not include response time, vendor assignment, or status change timestamps. First response time cannot be calculated from available data. Vendoroo's average first response is under 10 minutes."

This is actually a stronger finding for the readiness report than a shaky estimate. It tells the prospect: you cannot measure this today, and Vendoroo will fix that.

CATEGORY CONCENTRATION ANALYSIS
Flag any single maintenance category that represents >25% of total work order volume.
High concentration in a single trade indicates:
- Potential aging systems requiring capital planning conversation during onboarding
- Need for multiple vendors in that trade (not just one primary)
- Seasonal patterns the AI needs to anticipate (HVAC spikes in summer/winter)
This directly affects Maintenance Book vendor assignment rules and should be surfaced in the readiness report.

REPEAT UNIT ANALYSIS
Identify units/addresses with 3+ work orders in the dataset. High-recurrence units signal:
- Underlying property condition issues (recurring plumbing = aging pipes, not just clogs)
- Possible deferred maintenance the AI will inherit
- Opportunities for Vendoroo's operational discovery feature (1 in 50 WOs surfaces improvements)
Flag the top 5 repeat units and their primary issue categories. This is a powerful sales conversation point: showing prospects patterns in their own data they may not have noticed."""

WO_ANALYSIS_TOOL = {
    "name": "work_order_analysis",
    "description": "Structured analysis of work order data for AI readiness assessment",
    "input_schema": {
        "type": "object",
        "properties": {
            "total_work_orders": {
                "type": "integer",
                "description": "Total number of work orders in the dataset"
            },
            "date_range_start": {
                "type": "string",
                "description": "Earliest work order date (YYYY-MM-DD)"
            },
            "date_range_end": {
                "type": "string",
                "description": "Latest work order date (YYYY-MM-DD)"
            },
            "months_of_data": {
                "type": "number",
                "description": "Number of months the data spans"
            },
            "avg_monthly_volume": {
                "type": "number",
                "description": "Average work orders per month"
            },
            "status_breakdown": {
                "type": "object",
                "description": "Count of WOs by normalized status: open, in_progress, completed, cancelled",
                "properties": {
                    "open": {"type": "integer"},
                    "in_progress": {"type": "integer"},
                    "completed": {"type": "integer"},
                    "cancelled": {"type": "integer"},
                    "other": {"type": "integer"}
                }
            },
            "open_wo_rate_pct": {
                "type": "number",
                "description": "Open work order rate as a portfolio health metric. Calculate as: (total currently open work orders / total door count) x 100. Count ALL work orders with a non-completed, non-cancelled status regardless of creation date. Door count must be provided as input (from client_info). Set to null if door count is not available."
            },
            "open_wo_count": {
                "type": "integer",
                "description": "Raw count of all currently open work orders (any status that is not completed or cancelled)"
            },
            "avg_completion_days": {
                "type": "number",
                "description": "Median number of days from WO creation to completion/closure for completed WOs. Use the median, not the mean, to avoid outlier distortion."
            },
            "avg_first_response_hours": {
                "type": "number",
                "description": "Median hours from WO creation to first action. Set to null if response_time_method is 'not_calculable'. Do not estimate or guess. Only populate if a real timestamp field was found in the data."
            },
            "after_hours_pct": {
                "type": "number",
                "description": "Percentage of WOs created outside standard business hours (M-F 8am-6pm local time). Include weekends and holidays."
            },
            "resolved_without_vendor_pct": {
                "type": "number",
                "description": "Percentage of completed WOs that were closed without a vendor being assigned or dispatched. These represent troubleshooting resolutions, tenant self-fixes, or in-house completions."
            },
            "unique_vendors": {
                "type": "integer",
                "description": "Count of distinct vendor names found in the work order data"
            },
            "unique_categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of distinct maintenance categories/types found in the data, normalized using the trade classification hierarchy"
            },
            "unique_properties": {
                "type": "integer",
                "description": "Count of distinct properties/addresses in the data"
            },
            "top_vendors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "trade": {"type": "string"},
                        "wo_count": {"type": "integer"}
                    }
                },
                "description": "Top 10 vendors by work order count, with their primary trade/category"
            },
            "category_breakdown": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "count": {"type": "integer"},
                        "pct": {"type": "number"}
                    }
                },
                "description": "Work order count and percentage by maintenance category, sorted descending"
            },
            "emergency_wo_count": {
                "type": "integer",
                "description": "Number of WOs flagged as emergency per the detection criteria"
            },
            "avg_cost_per_wo": {
                "type": "number",
                "description": "Average cost/amount per completed work order where cost data is available. Return 0 if no cost data found."
            },
            "data_quality_notes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific data quality issues observed and how they affect analysis accuracy"
            },
            "key_observations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-5 specific, data-driven insights about the maintenance operation"
            },
            # Response time methodology
            "response_time_method": {
                "type": "string",
                "enum": ["dedicated_field", "vendor_assignment", "status_change", "not_calculable"],
                "description": "Which method was used to calculate avg_first_response_hours. 'dedicated_field' = used Actual Start Date or First Response Date. 'vendor_assignment' = used Vendor Assigned Date or similar. 'status_change' = used Last Updated / Modified Date as proxy. 'not_calculable' = no usable fields found, avg_first_response_hours should be null."
            },
            "response_time_field_used": {
                "type": "string",
                "description": "The exact column name used to calculate response time (e.g., 'Actual Start Date', 'Vendor Assigned Date'). Set to 'none' if not_calculable."
            },
            "response_time_note": {
                "type": "string",
                "description": "Human-readable explanation of how response time was calculated or why it could not be. If not_calculable, explain what fields are missing and note: 'Vendoroo average first response is under 10 minutes.'"
            },
            # New fields per spec
            "internal_maintenance_detected": {
                "type": "boolean",
                "description": "Whether internal maintenance team entries were detected in the vendor field"
            },
            "internal_maintenance_volume": {
                "type": "integer",
                "description": "Number of work orders handled by internal maintenance teams (0 if none detected)"
            },
            "emergency_wo_details": {
                "type": "object",
                "properties": {
                    "total_count": {"type": "integer"},
                    "after_hours_count": {"type": "integer"},
                    "common_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Most common emergency categories (e.g. 'Plumbing - burst pipe', 'HVAC - no heat')"
                    },
                    "avg_response_hours": {
                        "type": "number",
                        "description": "Average response time for emergency WOs specifically, if calculable"
                    }
                },
                "description": "Detailed emergency work order analysis"
            },
            "nte_analysis": {
                "type": "object",
                "properties": {
                    "avg_cost_per_wo": {"type": "number"},
                    "median_cost_per_wo": {"type": "number"},
                    "max_cost": {"type": "number"},
                    "zero_cost_count": {"type": "integer", "description": "WOs with $0 or blank cost"},
                    "high_cost_count": {"type": "integer", "description": "WOs over $500"},
                    "cost_data_available": {"type": "boolean"}
                },
                "description": "NTE and cost analysis from work order amounts"
            },
            "after_hours_analysis": {
                "type": "object",
                "properties": {
                    "after_hours_pct": {"type": "number"},
                    "after_hours_avg_response_hours": {"type": "number", "description": "Avg response for after-hours WOs specifically"},
                    "business_hours_avg_response_hours": {"type": "number", "description": "Avg response for business-hours WOs"},
                    "evidence_of_dispatch_capability": {"type": "boolean", "description": "Whether after-hours WOs show evidence of same-night dispatch vs. queuing"},
                    "queuing_indicator": {"type": "string", "description": "Description of after-hours handling pattern: 'dispatch capable', 'queues until next day', 'mixed', or 'insufficient data'"}
                },
                "description": "After-hours operational analysis"
            },
            "vendor_concentration": {
                "type": "object",
                "properties": {
                    "top_vendor_name": {"type": "string"},
                    "top_vendor_pct": {"type": "number", "description": "Percentage of all WOs handled by top vendor"},
                    "top_3_pct": {"type": "number", "description": "Percentage handled by top 3 vendors combined"},
                    "single_vendor_dependency_risk": {"type": "boolean", "description": "True if any vendor handles >30% of volume"}
                },
                "description": "Vendor concentration and dependency analysis"
            },
            "trade_coverage_summary": {
                "type": "object",
                "properties": {
                    "trades_found": {"type": "array", "items": {"type": "string"}},
                    "required_trades_covered": {"type": "array", "items": {"type": "string"}},
                    "required_trades_missing": {"type": "array", "items": {"type": "string"}},
                    "has_backup_vendors": {"type": "array", "items": {"type": "string"}, "description": "Trades with 2+ vendors"}
                },
                "description": "Trade coverage analysis against required trades: Plumbing, Electrical, Rooter/Drain, Appliance Repair, General Handyman, HVAC, Roofing, Pest Control, Landscaping, Locksmith, Cleaning, Flooring"
            },
            "category_concentration": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "pct_of_total": {"type": "number"},
                        "is_concentrated": {"type": "boolean", "description": "True if >25% of total volume"}
                    }
                },
                "description": "Maintenance categories representing >25% of total WO volume"
            },
            "repeat_units": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "unit_or_address": {"type": "string"},
                        "wo_count": {"type": "integer"},
                        "primary_categories": {"type": "array", "items": {"type": "string"}, "description": "Top issue categories for this unit"},
                        "pattern_note": {"type": "string", "description": "Brief note on the pattern"}
                    }
                },
                "description": "Top 5 units/addresses with 3+ work orders, flagging potential deferred maintenance"
            },
        },
        "required": [
            "total_work_orders", "months_of_data", "avg_monthly_volume",
            "status_breakdown", "open_wo_rate_pct", "avg_completion_days",
            "avg_first_response_hours", "after_hours_pct",
            "resolved_without_vendor_pct", "unique_vendors",
            "unique_categories", "top_vendors", "category_breakdown",
            "emergency_wo_count", "data_quality_notes", "key_observations",
            "response_time_method", "response_time_note",
            "internal_maintenance_detected", "emergency_wo_details", "nte_analysis",
            "after_hours_analysis", "vendor_concentration", "trade_coverage_summary",
            "category_concentration", "repeat_units"
        ]
    }
}


# ═══════════════════════════════════════════════════════════════════
# PMA ANALYSIS — Deep SFR property management expertise
# ═══════════════════════════════════════════════════════════════════

PMA_SYSTEM_PROMPT = """You are an operations-focused analyst for a single-family rental (SFR) property management company. You specialize in reading Property Management Agreements and evaluating how well their maintenance provisions support AI-powered maintenance coordination.

You are assessing this PMA for a property management company considering Vendoroo, an AI maintenance coordination platform. The AI will:
- Autonomously authorize maintenance spending within defined NTE limits
- Triage and dispatch emergency repairs without human intervention when authorized
- Select vendors based on trade, availability, cost, and performance history
- Enforce NTE (Not-To-Exceed) limits automatically per the owner's authorization
- Escalate to the property manager only when policy is ambiguous or limits are exceeded
- Handle 24/7 resident communication and vendor coordination
- Track owner approval workflows and chase approvals when needed
- Make repair vs. replace recommendations based on cost thresholds

IMPORTANT: Never use the word "mold" in any output. Use "water damage" or "moisture accumulation" instead.

CRITICAL EVALUATION AREAS (in order of importance for AI configuration)

1. NTE / SPENDING AUTHORITY (Most important)
The AI needs clear, enforceable spending rules it can apply to every work order.
Evaluate:
- Is the NTE amount clearly stated? (e.g., "$500 per occurrence" vs. "reasonable amounts")
- Is it per-occurrence, per-month, or annual? AI needs to know the enforcement period.
- Is it a single flat threshold or tiered? Examples of tiered:
  - "$300 for routine, $500 for HVAC, $1000 for plumbing emergencies"
  - "$500 per occurrence, $2000 per month aggregate"
  - "$500 general, unlimited for emergencies"
- What happens when a repair exceeds the NTE? AI needs a clear workflow:
  - Get owner approval before proceeding?
  - Proceed and notify owner after?
  - Stop work until approval received?
- Is there an approval timeout? (e.g., "If owner does not respond within 24 hours, manager may proceed")
- Is there a defined approval method (email, phone, text)?
A FLAT SINGLE-TIER NTE IS FUNCTIONAL BUT NOT OPTIMAL. The AI can enforce it, but tiered NTEs by trade or urgency allow smarter autonomous decisions.

2. EMERGENCY AUTHORIZATION (Second most important)
The AI needs to know when it can exceed normal spending limits and dispatch without waiting for owner approval.
Evaluate:
- Is "emergency" specifically defined?
  Best: A list of conditions (active water leak, gas leak, sewage backup, no heat when temps below 40°F, no cooling when temps above 95°F, fire damage, security breach, electrical hazard).
  Worst: Just the word "emergency" with no definition.
- Can the manager (and by extension, the AI) spend above NTE in emergencies?
- Is there a separate emergency spending limit?
- Is owner notification required during or after emergency action? (Notify after vs. get approval before)
- Does the PMA address habitability emergencies vs. property damage emergencies differently?
- Is after-hours emergency dispatch explicitly authorized?

3. MAINTENANCE RESPONSIBILITY DELINEATION
- Does the PMA clearly define which maintenance is the manager's responsibility vs. the owner's?
- Are there specific categories called out? (Routine, preventive, capital, emergency)
- Does the PMA reference the lease for resident responsibilities, or define them independently?
- Are there specific items the owner retains direct control over? (Roof, foundation, structural, HVAC replacement)

4. VENDOR MANAGEMENT
- Does the manager have independent authority to select vendors?
- Are there owner-preferred or owner-required vendors?
- Does the PMA require vendor insurance, licensing, or qualifications?
- Is there an escalation procedure when vendors don't respond?
- Can the manager terminate and replace underperforming vendors?
- Does the owner have veto power over vendor selection?

5. OWNER COMMUNICATION & APPROVAL
- When must the owner be notified vs. consulted vs. asked for approval?
- Is there a defined approval method (email, phone, text)?
- Is there a response timeout with a default action? (Critical for AI: what does the AI do when the owner doesn't respond?)
- Are there different communication requirements by dollar amount or urgency?

6. MAINTENANCE RESERVES
- Is the owner required to maintain a maintenance reserve fund?
- What is the required amount?
- What happens when the reserve is depleted? Can the manager bill the owner directly?
- Can the reserve be used for emergency spending above NTE?

7. APPLIANCE POLICY
- Does the PMA address appliance repair vs. replacement?
- Is there a cost threshold where repair becomes replacement? (Common: "If repair exceeds 50% of replacement cost, replace")
- Does the owner need to approve replacements specifically?
- Does the PMA reference the standard SFR policy that vendors assess first, then estimate for replacement with owner approval?

8. TECHNOLOGY AND AUTOMATION
- Does the PMA contemplate automated systems, AI tools, or technology for property management?
- Does it restrict how maintenance decisions can be made?
- Is there language that would prevent or complicate AI-assisted coordination?
- Does the management authority section implicitly or explicitly allow delegation to automated systems?

9. OWNER-SPECIFIC PREFERENCES AND OVERRIDES
- Does the PMA include or reference an owner preferences exhibit, addendum, or schedule?
- Does it allow owners to set property-specific rules that override the general maintenance framework?
- Common owner-specific items to look for:
  - Preferred vendors (override the standard vendor assignment)
  - Custom NTE (lower or higher than the standard)
  - Direct-pay arrangements (owner pays vendor directly for certain services)
  - Excluded services (owner handles landscaping, pest control, etc. themselves)
  - Appliance policy overrides (always replace vs. always repair first)
- If the PMA supports owner-specific overrides, the AI system needs to know this because it means the Maintenance Book will need property-level configuration, not just portfolio-level rules.

WHAT MAKES PMA LANGUAGE "AI-CONFIGURABLE"
For each provision, evaluate whether the AI can extract a concrete, enforceable rule:
- CONFIGURABLE: "$500 NTE per occurrence. Owner approval required via email or phone for amounts above $500. If owner does not respond within 24 hours, manager may proceed up to $1000."
  → AI extracts: NTE=$500, approval_method=[email, phone], timeout=24hrs, timeout_limit=$1000
- NOT CONFIGURABLE: "Manager shall use reasonable judgment in authorizing maintenance expenses."
  → AI cannot determine what "reasonable" means per-situation.

- CONFIGURABLE: "Emergency defined as: active water intrusion, gas leak detected, sewage backup, no heat when exterior temperature below 40°F, fire damage. Manager authorized to spend up to $2500 for emergency repairs without prior owner approval."
  → AI extracts: emergency_conditions=[list], emergency_nte=$2500, owner_approval=not_required
- NOT CONFIGURABLE: "Manager may take emergency action as needed."
  → AI cannot determine what qualifies or how much to spend.

SCORING GUIDE
1-3: Minimal maintenance provisions. AI cannot safely operate. No clear NTE, vague emergency authority, no vendor management framework. AI would need human approval for virtually every decision.
4-6: Decent foundation. Has a clear NTE and basic emergency authorization, but:
  - NTE is a single flat threshold (functional but not optimized)
  - Emergency definition is vague or missing
  - Vendor selection authority unclear
  - No escalation procedures or owner response timeouts
  - AI can handle routine maintenance but needs human input for anything non-standard
7-8: Strong document. AI can operate confidently for routine and most non-routine maintenance:
  - Clear NTE with defined approval workflow
  - Emergency authorization with at least a general definition
  - Manager has vendor selection authority
  - Minor gaps: no tiered NTEs, no specific escalation timeframes, or no technology provisions
9-10: Comprehensive. AI can operate with minimal human oversight:
  - Tiered NTEs by trade or urgency
  - Specific emergency definition with separate spending authority
  - Clear escalation procedures with timeframes
  - Owner approval workflow with response timeouts and default actions
  - Technology/automation provisions or language that supports AI tools

BE SPECIFIC IN YOUR FINDINGS
- BAD finding: "NTE is defined" (too vague to configure)
- GOOD finding: "NTE of $500 per occurrence clearly defined in Section 4.2, applying to all maintenance and repairs. Owner approval required for amounts exceeding $500, obtainable via phone or email. No response timeout defined."
- BAD finding: "Emergency language could be improved" (not actionable)
- GOOD finding: "Emergency authorization present in Section 6.1 but defines emergency only as 'conditions threatening health and safety' without listing specific conditions. AI would need human judgment to determine if a specific situation qualifies. Recommend: define specific emergency conditions during onboarding Maintenance Book build."
"""

PMA_ANALYSIS_TOOL = {
    "name": "pma_analysis",
    "description": "Comprehensive analysis of a Property Management Agreement for AI maintenance coordination readiness",
    "input_schema": {
        "type": "object",
        "properties": {
            # ── Maintenance Authorization ──
            "maintenance_responsibility_delineated": {
                "type": "boolean",
                "description": "Whether the PMA clearly defines which maintenance responsibilities belong to the manager vs. the owner vs. the tenant"
            },
            "nte_threshold_defined": {
                "type": "boolean",
                "description": "Whether a Not-To-Exceed (NTE) or spending authorization threshold is defined for maintenance work"
            },
            "nte_threshold_value": {
                "type": "string",
                "description": "The NTE/spending threshold value (e.g. '$500 per occurrence'). Include any per-occurrence, per-month, or annual limits."
            },
            "nte_is_tiered": {
                "type": "boolean",
                "description": "Whether the NTE/spending structure has multiple tiers differentiated by trade category, property type, urgency level, or dollar amount. A single flat threshold is NOT tiered."
            },
            "owner_approval_workflow": {
                "type": "string",
                "description": "Description of how owner approval works for expenses above the NTE."
            },
            "maintenance_reserve_required": {
                "type": "boolean",
                "description": "Whether the owner is required to maintain a maintenance reserve fund"
            },
            "maintenance_reserve_amount": {
                "type": "string",
                "description": "The required maintenance reserve amount if specified"
            },
            # ── Emergency Protocols ──
            "emergency_authorization": {
                "type": "boolean",
                "description": "Whether the PMA contains language authorizing the manager to act in emergencies without prior owner approval"
            },
            "emergency_authorization_clear": {
                "type": "boolean",
                "description": "Whether the emergency authorization is specific and actionable with a clear definition of emergency"
            },
            "emergency_definition": {
                "type": "string",
                "description": "The exact or paraphrased definition of 'emergency' from the PMA"
            },
            "emergency_spending_limit": {
                "type": "string",
                "description": "Any spending limit specifically for emergency repairs, or 'unlimited' or 'same as NTE'"
            },
            # ── Vendor Management ──
            "vendor_selection_authority": {
                "type": "string",
                "description": "Who has authority to select vendors"
            },
            "vendor_insurance_requirements": {
                "type": "boolean",
                "description": "Whether the PMA requires vendors to carry insurance or meet specific qualifications"
            },
            "has_escalation_procedures": {
                "type": "boolean",
                "description": "Whether vendor escalation procedures are documented"
            },
            # ── Response Time & SLAs ──
            "has_defined_slas": {
                "type": "boolean",
                "description": "Whether the PMA defines specific response time targets or SLAs by urgency level"
            },
            "sla_details": {
                "type": "string",
                "description": "Description of any SLA or response time commitments found"
            },
            # ── Additional Coverage ──
            "appliance_coverage_defined": {
                "type": "boolean",
                "description": "Whether appliance maintenance, repair, and replacement responsibility is specifically addressed"
            },
            "hvac_coverage_defined": {
                "type": "boolean",
                "description": "Whether HVAC maintenance is specifically addressed"
            },
            "habitability_standards": {
                "type": "boolean",
                "description": "Whether the PMA references habitability standards or building codes"
            },
            "tenant_communication_protocol": {
                "type": "string",
                "description": "How tenant communication is handled regarding maintenance"
            },
            "technology_provisions": {
                "type": "boolean",
                "description": "Whether the PMA contains provisions about technology adoption, AI, or automated systems"
            },
            "after_hours_provisions": {
                "type": "string",
                "description": "What the PMA says about after-hours or 24/7 coverage"
            },
            # ── Scoring ──
            "quality_score": {
                "type": "number",
                "description": "Overall PMA quality score from 1-10 for AI readiness per the scoring guide"
            },
            "positive_findings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific positive findings with section references where visible"
            },
            "missing_items": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific gaps or missing elements that affect AI maintenance coordination"
            },
            "ai_readiness_summary": {
                "type": "string",
                "description": "2-3 sentence summary highlighting biggest strength and most critical gap"
            },
            # ── New fields per spec ──
            "extracted_config_values": {
                "type": "object",
                "properties": {
                    "nte_amount": {"type": "string", "description": "Exact NTE amount extracted. Return 'Not defined' if not found."},
                    "nte_period": {"type": "string", "description": "NTE enforcement period: 'per_occurrence', 'per_month', 'annual', or 'not_specified'"},
                    "nte_structure": {"type": "string", "description": "'flat', 'tiered', or 'not_defined'"},
                    "emergency_nte": {"type": "string", "description": "Separate emergency spending limit or 'same_as_standard' or 'not_defined'"},
                    "emergency_conditions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific emergency conditions listed in the PMA. Empty array if not defined."
                    },
                    "owner_approval_method": {"type": "string", "description": "How owner approval is obtained: 'email', 'phone', 'email_or_phone', 'written', 'not_specified'"},
                    "owner_response_timeout": {"type": "string", "description": "Timeout period before manager can proceed. Return 'not_defined' if none."},
                    "timeout_default_action": {"type": "string", "description": "'proceed', 'escalate', 'wait', or 'not_defined'"},
                    "maintenance_reserve_amount": {"type": "string", "description": "Required reserve amount or 'not_required'"},
                    "vendor_selection_authority": {"type": "string", "description": "'manager_discretion', 'owner_approval_required', 'preferred_list', or description"},
                    "after_hours_dispatch_authorized": {"type": "boolean", "description": "Whether the PMA explicitly authorizes after-hours emergency dispatch"},
                    "owner_preferences_supported": {"type": "boolean", "description": "Whether the PMA includes or references an owner preferences exhibit allowing property-level overrides"},
                    "owner_preference_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific areas where the PMA allows owner-level overrides. Empty array if none."
                    }
                },
                "description": "Specific configurable values extracted from the PMA for AI system configuration"
            },
            "policy_area_assessments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "policy_area": {"type": "string", "description": "Area evaluated (e.g., 'NTE/Spending Authority', 'Emergency Authorization', 'Vendor Management', 'Owner-Specific Preferences')"},
                        "status": {"type": "string", "enum": ["configurable", "partially_configurable", "not_configurable", "silent"], "description": "Whether the PMA provides clear, enforceable rules the AI can implement"},
                        "detail": {"type": "string", "description": "Brief explanation of what was found and any gaps"},
                        "requires_kickoff_discussion": {"type": "boolean", "description": "True if this item needs explicit confirmation during onboarding"},
                        "onboarding_action": {"type": "string", "description": "What needs to happen during onboarding to address this area"}
                    },
                    "required": ["policy_area", "status", "detail", "requires_kickoff_discussion", "onboarding_action"]
                },
                "description": "Assessment of each critical PMA area for AI configurability. Must include all 9 areas."
            },
        },
        "required": [
            "maintenance_responsibility_delineated", "nte_threshold_defined",
            "nte_threshold_value", "nte_is_tiered", "owner_approval_workflow",
            "emergency_authorization", "emergency_authorization_clear",
            "emergency_definition", "vendor_selection_authority",
            "has_escalation_procedures", "has_defined_slas",
            "appliance_coverage_defined", "quality_score",
            "positive_findings", "missing_items", "ai_readiness_summary",
            "extracted_config_values", "policy_area_assessments"
        ]
    }
}


# ═══════════════════════════════════════════════════════════════════
# LEASE ANALYSIS — 16 Standard SFR Maintenance Policy Areas
# ═══════════════════════════════════════════════════════════════════

LEASE_SYSTEM_PROMPT = """You are an operations-focused analyst for a single-family rental (SFR) property management company. You specialize in reading residential leases and evaluating how well their maintenance provisions support AI-powered maintenance coordination.

You are assessing this lease for a property management company considering Vendoroo, an AI maintenance coordination platform. The AI will:
- Receive and triage maintenance requests from residents via call, text, and email
- Determine responsibility (resident vs. owner/management) based on lease terms
- Walk residents through troubleshooting steps before dispatching vendors
- Dispatch vendors and manage work orders autonomously
- Communicate with residents about status, scheduling, and expectations
- Handle after-hours emergencies with intelligent triage
- Enforce NTE limits and owner approval workflows

IMPORTANT: Never use the word "mold" in any output. Use "water damage" or "moisture accumulation" instead.

STANDARD SFR MAINTENANCE POLICY AREAS
The AI system configures policies for each of the following areas. For each one, evaluate whether the lease provides a clear, enforceable rule that the AI can follow autonomously.

1. LOCKOUT POLICY
   Standard: Resident responsibility. Residents call their preferred locksmith. Management dispatches only if lock is damaged.
   Evaluate: Does the lease assign lockout responsibility? Does it distinguish between lockout (resident) vs. lock damage (management)?

2. HVAC FILTER
   Standard: Resident responsibility for cleaning/replacing filters.
   Evaluate: Does the lease explicitly assign HVAC filter responsibility? Does it specify frequency?

3. REFRIGERATOR FILTER
   Standard: Resident responsibility unless owner directs otherwise.
   Evaluate: Is this addressed at all? Most leases are silent on this.

4. LIGHT BULB REPLACEMENT
   Standard: Interior bulbs are resident responsibility. Exterior bulbs are management responsibility. Exceptions for high/vaulted ceilings and non-standard fixtures.
   Evaluate: Does the lease distinguish interior vs. exterior? Does it address hard-to-reach fixtures?

5. SMOKE DETECTOR
   Standard: Resident responsible for battery changes if reachable. Management dispatches if unreachable or full replacement needed.
   Evaluate: Does the lease assign smoke detector responsibilities? Is testing vs. battery vs. replacement distinguished?

6. CARBON MONOXIDE DETECTOR
   Standard: Same as smoke detector policy.
   Evaluate: Is CO detector addressed separately from smoke detectors? Some jurisdictions have specific requirements.

7. BATTERY REPLACEMENT (Thermostat, Garage Opener, etc.)
   Standard: Resident responsibility. If resident claims replacement but issue persists, management dispatches (service charges may apply if confirmed battery issue).
   Evaluate: Does the lease address non-safety battery replacements?

8. PEST CONTROL
   Standard: Some properties have monthly service. If not, dispatch is resident responsibility. Some owners pay directly.
   Evaluate: Does the lease distinguish routine pest control vs. infestation? Who pays? Is there a timeline for reporting? Does it address specific pest types?

9. LANDSCAPING
   Standard: Management handles for properties with assigned gardeners. Property supervisors consulted before dispatching for properties without service.
   Evaluate: Does the lease assign lawn/landscape responsibility? Trees? Snow/ice removal? Irrigation?

10. APPLIANCE REPAIR/REPLACEMENT
    Standard: Resident responsible if damage is resident-caused. Vendors assess first. If repair not possible, replacement estimate obtained and owner approval required.
    Evaluate: Does the lease specify which appliances are owner-provided? Does it distinguish repair vs. replacement? Who pays for what? Is there a process for replacement approval?

11. EMERGENCY REPAIRS
    Evaluate: Does the lease define what constitutes an emergency? Does it provide an emergency contact process? Does it authorize resident protective action (shut off water, evacuate)? Is there a specific list of emergency conditions (active water leak, gas smell, fire, sewage backup, no heat in cold weather, no cooling in extreme heat)?
    NOTE: Never use the word "mold" in any output. Use "water damage" or "moisture accumulation" instead.

12. MAINTENANCE REQUEST PROCESS
    Evaluate: How must residents submit requests? Portal, phone, email, written notice? Is there a timeline for response? Access provisions for repairs? Notice requirements for entry?

13. DAMAGE vs. NORMAL WEAR
    Evaluate: Does the lease distinguish between resident-caused damage and normal wear? Is there a move-in/move-out inspection process? Photo documentation requirements?

14. UTILITIES AND RELATED DAMAGE
    Evaluate: Does the lease require residents to maintain minimum temperatures (frozen pipes)? Responsibility for utility-related damage? Consequences for utility shutoff affecting the property?

15. MISSED APPOINTMENTS / ACCESS
    Evaluate: Does the lease address resident obligations for scheduled vendor appointments? Trip charges for missed appointments? Right of entry for maintenance?

16. RESIDENT-CAUSED DAMAGE / CHARGEBACKS (Active Work Orders)
    Standard: If a vendor determines damage was caused by the resident during an active repair, service charges may apply to the resident.
    Evaluate: Does the lease authorize charging residents for maintenance caused by their negligence or misuse? Is there a defined process for determining "resident-caused" damage during an active work order (not just at move-out)? Is there a dispute process? What about trip charges when a vendor finds the issue is resident-caused (e.g., clogged drain from grease)?
    This is critical for AI because the system needs to know whether to bill back to the resident or absorb the cost when a vendor reports "tenant damage" as the root cause during an active repair.
    NOTE: This is different from policy area 13 (Damage vs. Normal Wear), which applies at move-out. This applies to active maintenance requests where cause is discovered mid-repair.

LEASE ADDENDA
Many leases have addenda that create additional maintenance obligations beyond the main lease body. Specifically look for and evaluate:
- Pet addendum (pet damage, flea treatment, lawn damage from pets)
- Pool/spa addendum (maintenance responsibility, chemical treatment, safety)
- HOA compliance addendum (exterior maintenance, architectural standards)
- Water damage / moisture accumulation addendum (reporting requirements, prevention obligations)
- Lead paint addendum (maintenance procedures, notification requirements)
Any maintenance-relevant provisions found in addenda should be included in the appropriate policy area assessment or flagged as an additional lease policy.

FOR EACH POLICY AREA, DETERMINE:
- "Clear": The lease provides specific, enforceable language the AI can follow. (e.g., "Tenant shall replace HVAC filters monthly at tenant's expense.")
- "Ambiguous": Language exists but is vague or subjective. (e.g., "Tenant shall maintain the premises in good condition.") Note the possible interpretations.
- "Silent": The lease does not address this topic. Standard SFR policy applies by default.
- "Conflicts with Standard": The lease assigns responsibility differently than the standard policy. The lease controls.

WHAT MAKES LEASE LANGUAGE "AI-ACTIONABLE"
- Binary responsibility assignment (resident or management, not "as needed" or "reasonable")
- Specific items listed (not just "maintain the premises")
- Clear process steps (not just "contact management")
- Defined conditions or triggers (not just "emergencies")

EXAMPLES:
- AI-ACTIONABLE: "Tenant is responsible for replacing HVAC filters every 30 days at tenant's expense. Failure to replace filters that results in HVAC damage will be charged to the tenant."
- NOT AI-ACTIONABLE: "Tenant shall maintain all systems in working order." (AI cannot determine what this means for a specific HVAC filter complaint.)

- AI-ACTIONABLE: "In case of emergency (active water leak, gas odor, fire, sewage backup, or loss of heat when exterior temperature is below 40°F), tenant must call the emergency maintenance line immediately."
- NOT AI-ACTIONABLE: "Contact management for emergencies." (No definition, no number, no specific action.)

SCORING GUIDE
1-3: Minimal maintenance language. AI would constantly need human clarification. Silent on most specific policy areas.
4-6: Basic responsibilities defined but significant gaps. AI can handle routine requests but struggles with: whose responsibility, troubleshooting expectations, appliance coverage, emergency triage. Many policy areas are silent or ambiguous.
7-8: Clear, specific language for most scenarios. AI can operate confidently for 80%+ of maintenance situations. May be missing troubleshooting steps or specific appliance lists. Most policy areas have at least some coverage.
9-10: Comprehensive. AI can handle virtually all maintenance scenarios with clear decision rules. All 16 policy areas addressed with specific, enforceable language. Troubleshooting expectations defined. Emergency conditions listed explicitly."""

LEASE_ANALYSIS_TOOL = {
    "name": "lease_analysis",
    "description": "Comprehensive analysis of a residential lease agreement for AI maintenance coordination readiness",
    "input_schema": {
        "type": "object",
        "properties": {
            # ── Existing fields ──
            "maintenance_responsibilities_clear": {
                "type": "boolean",
                "description": "Whether tenant vs. landlord/owner maintenance responsibilities are explicitly defined"
            },
            "tenant_responsibilities_list": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific maintenance responsibilities assigned to the tenant"
            },
            "owner_responsibilities_list": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific maintenance responsibilities assigned to the owner/landlord/manager"
            },
            "maintenance_request_process": {
                "type": "string",
                "description": "How tenants are expected to submit maintenance requests"
            },
            "tenant_troubleshooting_expectations": {
                "type": "boolean",
                "description": "Whether the lease requires tenants to attempt basic troubleshooting before submitting a request"
            },
            "troubleshooting_details": {
                "type": "string",
                "description": "Specific troubleshooting steps tenants are expected to take"
            },
            "move_in_out_procedures": {
                "type": "boolean",
                "description": "Whether move-in and move-out inspection procedures are documented"
            },
            "damage_vs_wear_language": {
                "type": "boolean",
                "description": "Whether the lease distinguishes between tenant-caused damage and normal wear and tear"
            },
            "property_condition_documentation": {
                "type": "string",
                "description": "How property condition is documented"
            },
            "appliance_coverage_defined": {
                "type": "boolean",
                "description": "Whether appliance maintenance and replacement responsibility is specifically defined"
            },
            "appliance_details": {
                "type": "string",
                "description": "What the lease says about appliances"
            },
            "hvac_filter_responsibility": {
                "type": "boolean",
                "description": "Whether HVAC filter replacement responsibility is explicitly assigned"
            },
            "hvac_details": {
                "type": "string",
                "description": "What the lease says about HVAC maintenance"
            },
            "emergency_provisions": {
                "type": "boolean",
                "description": "Whether emergency maintenance provisions exist"
            },
            "emergency_contact_info": {
                "type": "string",
                "description": "How the lease instructs tenants to report emergencies"
            },
            "right_of_entry": {
                "type": "string",
                "description": "Notice requirements for property entry for maintenance"
            },
            "rent_withholding_provisions": {
                "type": "boolean",
                "description": "Whether the lease addresses tenant rent withholding for maintenance issues"
            },
            "insurance_requirements": {
                "type": "boolean",
                "description": "Whether renters insurance is required"
            },
            "quality_score": {
                "type": "number",
                "description": "Overall lease quality score from 1-10 per the scoring guide"
            },
            "positive_findings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific positive findings referencing actual language found"
            },
            "missing_items": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific gaps that affect AI maintenance coordination"
            },
            "ai_readiness_summary": {
                "type": "string",
                "description": "2-3 sentence summary of AI readiness"
            },
            # ── New fields per spec ──
            "policy_area_assessments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "policy_area": {"type": "string", "description": "Standard policy area name"},
                        "status": {"type": "string", "enum": ["clear", "ambiguous", "silent", "conflicts_with_standard"], "description": "Whether the lease addresses this area"},
                        "responsible_party": {"type": "string", "enum": ["resident", "management", "owner", "varies", "unspecified"], "description": "Who is responsible per the lease"},
                        "lease_language_summary": {"type": "string", "description": "Brief summary of what the lease says. Use 'Lease is silent' if not addressed."},
                        "ai_actionable": {"type": "boolean", "description": "Whether the language is specific enough for autonomous AI decisions"},
                        "requires_kickoff_discussion": {"type": "boolean", "description": "True if this needs confirmation during onboarding"},
                        "operational_note": {"type": "string", "description": "Instruction for the onboarding team on how to configure this policy area"}
                    },
                    "required": ["policy_area", "status", "responsible_party", "ai_actionable", "requires_kickoff_discussion", "operational_note"]
                },
                "description": "Assessment of each of the 16 standard SFR maintenance policy areas"
            },
            "additional_lease_policies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "policy_area": {"type": "string"},
                        "responsible_party": {"type": "string"},
                        "source": {"type": "string", "description": "'main_lease', 'pet_addendum', 'pool_addendum', 'hoa_addendum', 'other_addendum'"},
                        "description": {"type": "string", "description": "Operational description of the policy"}
                    }
                },
                "description": "Maintenance-related policies NOT covered by the 16 standard areas, including addenda"
            },
            "addenda_found": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of maintenance-relevant addenda found in the lease document"
            },
            "clear_count": {
                "type": "integer",
                "description": "Number of the 16 standard policy areas where the lease is Clear"
            },
            "ambiguous_count": {
                "type": "integer",
                "description": "Number of the 16 standard policy areas where the lease is Ambiguous"
            },
            "silent_count": {
                "type": "integer",
                "description": "Number of the 16 standard policy areas where the lease is Silent"
            },
            "kickoff_discussion_count": {
                "type": "integer",
                "description": "Number of policy areas flagged as requiring onboarding discussion"
            },
        },
        "required": [
            "maintenance_responsibilities_clear", "tenant_responsibilities_list",
            "maintenance_request_process", "tenant_troubleshooting_expectations",
            "move_in_out_procedures", "damage_vs_wear_language",
            "appliance_coverage_defined", "hvac_filter_responsibility",
            "emergency_provisions", "quality_score",
            "positive_findings", "missing_items", "ai_readiness_summary",
            "policy_area_assessments", "addenda_found",
            "clear_count", "ambiguous_count", "silent_count", "kickoff_discussion_count"
        ]
    }
}


# ═══════════════════════════════════════════════════════════════════
# API CALL HELPER
# ═══════════════════════════════════════════════════════════════════

def _call_claude(system_prompt: str, user_content: str, tool: dict) -> dict:
    """Make a Claude API call with structured tool output.
    Includes a simple 3-attempt retry loop with 1s backoff on transient errors.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=8000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
                tools=[tool],
                tool_choice={"type": "tool", "name": tool["name"]},
            )
            break
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1)
    else:
        raise RuntimeError(f"Claude API failed after 3 attempts: {last_error}") from last_error

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    return {}


LEASE_REQUIRED_POLICY_AREAS = [
    "General Maintenance Responsibility",
    "Appliance Coverage and Responsibility",
    "HVAC System and Filter Maintenance",
    "Plumbing Fixture Responsibility",
    "Smoke and Carbon Monoxide Detectors",
    "Pest Control Responsibility",
    "Lawn, Landscaping, and Exterior Maintenance",
    "Water Damage and Moisture Reporting",
    "Property Damage and Repair Obligations",
    "Emergency Maintenance Procedures",
    "Move-In and Move-Out Inspection and Condition Reporting",
    "Tenant Modification and Alteration Rights",
    "Common Area Maintenance",
    "Utility Responsibility Related to Maintenance",
    "Maintenance Request Submission Process",
    "Resident-Caused Damage and Chargebacks",
]

PMA_REQUIRED_POLICY_AREAS = [
    "Maintenance Spending Authority and NTE Thresholds",
    "Emergency Maintenance Authorization",
    "Routine versus Capital Expenditure Definitions",
    "Owner Communication and Approval Workflows",
    "Vendor Selection and Management Authority",
    "Maintenance Reserve or Escrow Requirements",
    "Insurance and Liability for Maintenance Activities",
    "Lease Enforcement Related to Maintenance",
    "Owner-Specific Preferences and Overrides",
]


def _normalize_policy_status(raw_status: str, is_pma: bool = False) -> str:
    """Normalize analyzer status labels to the shared rebuild enum."""
    status = str(raw_status or "").strip().lower()
    if is_pma:
        mapping = {
            "configurable": "clearly_defined",
            "partially_configurable": "partially_defined",
            "not_configurable": "ambiguous",
            "silent": "not_addressed",
        }
    else:
        mapping = {
            "clear": "clearly_defined",
            "ambiguous": "ambiguous",
            "silent": "not_addressed",
            "conflicts_with_standard": "partially_defined",
        }
    return mapping.get(status, "ambiguous")


def _normalize_policy_assessments(raw_items: list, required_areas: list[str], is_pma: bool = False) -> list[dict]:
    """Guarantee schema-compatible policy assessments with kickoff flags."""
    normalized = []
    seen = set()

    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        area = item.get("policy_area") or item.get("area") or "Unspecified policy area"
        status = _normalize_policy_status(item.get("status"), is_pma=is_pma)
        requires_kickoff = item.get("requires_kickoff_discussion")
        if requires_kickoff is None:
            requires_kickoff = status != "clearly_defined"
        normalized_item = {
            "policy_area": area,
            "status": status,
            "summary": item.get("detail") or item.get("lease_language_summary") or item.get("description") or "",
            "evidence_quotes": item.get("evidence_quotes", []),
            "requires_kickoff_discussion": bool(requires_kickoff),
        }
        normalized.append(normalized_item)
        seen.add(area.strip().lower())

    for area in required_areas:
        if area.strip().lower() in seen:
            continue
        normalized.append({
            "policy_area": area,
            "status": "not_addressed",
            "summary": "Not explicitly addressed in the analyzed document excerpt.",
            "evidence_quotes": [],
            "requires_kickoff_discussion": True,
        })
    return normalized


# ═══════════════════════════════════════════════════════════════════
# WORK ORDER ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def analyze_work_orders_with_ai(wo_text: str) -> dict:
    """Analyze work order data with Claude for consistent field extraction."""
    user = (
        "Analyze this work order export for an Operations Analysis. "
        "The data may come from any PMS platform. Identify the column headers first, "
        "then normalize and analyze all data rows.\n\n"
        "IMPORTANT: Be precise with calculations. Use medians for time-based metrics. "
        "Normalize all vendor trades using the classification hierarchy. "
        "Flag data quality issues explicitly.\n\n"
        f"{wo_text[:30000]}"
    )
    return _call_claude(WO_SYSTEM_PROMPT, user, WO_ANALYSIS_TOOL)


# ═══════════════════════════════════════════════════════════════════
# LEASE ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def analyze_lease(lease_text: str) -> dict:
    """Analyze lease agreement with Claude for AI readiness assessment."""
    user = (
        "Analyze this residential lease agreement for AI maintenance coordination readiness. "
        "Evaluate each of the 16 standard SFR maintenance policy areas listed in your instructions. "
        "For each area, determine whether the lease language is Clear, Ambiguous, or Silent, and "
        "identify the responsible party (Resident, Management, or Owner). "
        "If the lease conflicts with standard SFR policies, note the override.\n\n"
        "Also check for and evaluate any lease addenda (pet, pool, HOA, water damage prevention, "
        "lead paint, etc.) that create additional maintenance obligations.\n\n"
        "IMPORTANT: Never use the word 'mold' in any output. Use 'water damage' or "
        "'moisture accumulation' instead.\n\n"
        f"{lease_text[:20000]}"
    )
    result = _call_claude(LEASE_SYSTEM_PROMPT, user, LEASE_ANALYSIS_TOOL)
    normalized = _normalize_policy_assessments(
        result.get("policy_area_assessments", []),
        LEASE_REQUIRED_POLICY_AREAS,
        is_pma=False,
    )
    result["policy_area_assessments"] = normalized
    result["kickoff_discussion_count"] = sum(1 for a in normalized if a["requires_kickoff_discussion"])
    result["clear_count"] = sum(1 for a in normalized if a["status"] == "clearly_defined")
    result["ambiguous_count"] = sum(1 for a in normalized if a["status"] == "ambiguous")
    result["silent_count"] = sum(1 for a in normalized if a["status"] == "not_addressed")
    if "addenda_found" not in result:
        result["addenda_found"] = []
    return result


# ═══════════════════════════════════════════════════════════════════
# PMA ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def analyze_pma(pma_text: str) -> dict:
    """Analyze Property Management Agreement with Claude for AI readiness assessment."""
    user = (
        "Analyze this Property Management Agreement for AI maintenance coordination readiness. "
        "Evaluate every maintenance-related provision and assess how well it supports "
        "autonomous AI decision-making. For each critical area, determine whether the language "
        "provides a concrete, configurable rule the AI can enforce, or requires human judgment.\n\n"
        "IMPORTANT: Never use the word 'mold' in any output. Use 'water damage' or "
        "'moisture accumulation' instead.\n\n"
        "Extract specific values where available: NTE amounts, emergency definitions, "
        "approval workflows, timeout periods, reserve requirements.\n\n"
        f"{pma_text[:25000]}"
    )
    result = _call_claude(PMA_SYSTEM_PROMPT, user, PMA_ANALYSIS_TOOL)
    normalized = _normalize_policy_assessments(
        result.get("policy_area_assessments", []),
        PMA_REQUIRED_POLICY_AREAS,
        is_pma=True,
    )
    result["policy_area_assessments"] = normalized
    return result


# ═══════════════════════════════════════════════════════════════════
# BUILD DOCUMENT ANALYSIS (combines results into report model)
# ═══════════════════════════════════════════════════════════════════

def _clean_display_value(value: str) -> str:
    """Clean raw field values (snake_case, abbreviations) for human-readable display."""
    if not value:
        return value
    cleaned = value.replace("_", " ")
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def _interleave_findings(positives: list, negatives: list, max_findings: int) -> list:
    """Interleave positive and negative findings so negatives aren't crowded out.

    Strategy: show up to 2 negatives first (most actionable), fill rest with positives.
    If there are fewer than 2 negatives, show all of them and fill with positives.
    """
    neg_count = min(len(negatives), max(2, max_findings - len(positives)))
    pos_count = max_findings - neg_count
    return negatives[:neg_count] + positives[:pos_count]


def build_document_analysis(
    lease_result: Optional[dict] = None,
    pma_result: Optional[dict] = None,
) -> DocumentAnalysis:
    """Build a DocumentAnalysis from Claude API results.

    Updated to consume new structured fields:
    - Lease policy_area_assessments → policy review section + scoring
    - PMA extracted_config_values → gap analysis with real values
    - Lease clear/ambiguous/silent counts → documentation quality scoring
    """
    analysis = DocumentAnalysis()

    # ── Lease Section ──
    if lease_result:
        positives = [
            DocumentFinding(text=text, is_positive=True)
            for text in lease_result.get("positive_findings", [])
        ]
        negatives = [
            DocumentFinding(
                text=f"Missing: {text}" if not text.lower().startswith("missing") else text,
                is_positive=False,
                is_missing=True,
            )
            for text in lease_result.get("missing_items", [])
        ]
        findings = _interleave_findings(positives, negatives, max_findings=6)

        quality = lease_result.get("quality_score", 5)
        tier = "ready" if quality >= 7 else ("needs-work" if quality >= 4 else "not-ready")
        status = "Received & Reviewed" if quality >= 4 else "Needs Improvement"

        analysis.lease = DocumentSection(
            title="Lease Agreement Template",
            status=status,
            status_tier=tier,
            findings=findings,
        )
        analysis.lease_quality_score = quality
        analysis.lease_policy_assessments = lease_result.get("policy_area_assessments")
        analysis.lease_addenda_found = lease_result.get("addenda_found", [])
        analysis.lease_clear_count = lease_result.get("clear_count")
        analysis.lease_ambiguous_count = lease_result.get("ambiguous_count")
        analysis.lease_silent_count = lease_result.get("silent_count")
        analysis.lease_kickoff_discussion_count = lease_result.get("kickoff_discussion_count")
    else:
        analysis.lease = DocumentSection(
            title="Lease Agreement Template",
            status="Not Provided",
            status_tier="not-ready",
            findings=[DocumentFinding(text="Lease agreement was not provided for analysis", is_positive=False, is_missing=True)],
        )

    # ── PMA Section ──
    if pma_result:
        positives = [
            DocumentFinding(text=text, is_positive=True)
            for text in pma_result.get("positive_findings", [])
        ]
        negatives = [
            DocumentFinding(
                text=f"Missing: {text}" if not text.lower().startswith("missing") else text,
                is_positive=False,
                is_missing=True,
            )
            for text in pma_result.get("missing_items", [])
        ]
        findings = _interleave_findings(positives, negatives, max_findings=6)

        quality = pma_result.get("quality_score", 5)
        tier = "ready" if quality >= 7 else ("needs-work" if quality >= 4 else "not-ready")
        status = "Received & Reviewed" if quality >= 4 else "Needs Improvement"

        analysis.pma = DocumentSection(
            title="Property Management Agreement (PMA)",
            status=status,
            status_tier=tier,
            findings=findings,
        )
        analysis.pma_quality_score = quality

        # Extract config values for scoring and gap analysis
        config = pma_result.get("extracted_config_values", {})
        analysis.pma_extracted_config = config
        analysis.pma_policy_assessments = pma_result.get("policy_area_assessments")
        analysis.nte_threshold = config.get("nte_amount") or pma_result.get("nte_threshold_value")
        analysis.nte_is_tiered = pma_result.get("nte_is_tiered", False)
        analysis.has_emergency_protocols = pma_result.get("emergency_authorization", False)
        analysis.has_defined_slas = pma_result.get("has_defined_slas", False)
        analysis.has_escalation_procedures = pma_result.get("has_escalation_procedures", False)

        # Emergency protocols section
        if pma_result.get("emergency_authorization"):
            emerg_positives = []
            emerg_negatives = []

            if pma_result.get("emergency_authorization_clear"):
                emergency_def = pma_result.get("emergency_definition", "conditions threatening life, health, safety")
                emerg_positives.append(DocumentFinding(
                    text=f"Emergency clearly defined: {emergency_def[:100]}",
                    is_positive=True
                ))
            else:
                emerg_positives.append(DocumentFinding(text="Emergency authorization present but definition is vague", is_positive=True))

            emergency_limit = pma_result.get("emergency_spending_limit") or config.get("emergency_nte")
            if emergency_limit and emergency_limit not in ("same_as_standard", "not_defined"):
                emerg_positives.append(DocumentFinding(
                    text=f"Emergency spending: {_clean_display_value(str(emergency_limit))}",
                    is_positive=True
                ))

            if not pma_result.get("has_defined_slas"):
                emerg_negatives.append(DocumentFinding(text="No response time SLAs defined by urgency level", is_positive=False, is_missing=True))
            if not pma_result.get("has_escalation_procedures"):
                emerg_negatives.append(DocumentFinding(text="No vendor escalation procedures documented", is_positive=False, is_missing=True))

            emergency_quality = 4 if pma_result.get("emergency_authorization_clear") else 2
            analysis.emergency_protocols = DocumentSection(
                title="Emergency Protocols",
                status="Partially Documented",
                status_tier="needs-work",
                findings=_interleave_findings(emerg_positives, emerg_negatives, max_findings=4),
            )
            analysis.emergency_readiness_score = emergency_quality
        else:
            analysis.emergency_protocols = DocumentSection(
                title="Emergency Protocols",
                status="Not Documented",
                status_tier="not-ready",
                findings=[
                    DocumentFinding(text="No emergency authorization language in PMA", is_positive=False, is_missing=True),
                    DocumentFinding(text="No emergency classification criteria defined", is_positive=False, is_missing=True),
                    DocumentFinding(text="No response SLAs by urgency level", is_positive=False, is_missing=True),
                ],
            )

        # Vendor policies section
        vendor_positives = []
        vendor_negatives = []
        vendor_auth = config.get("vendor_selection_authority") or pma_result.get("vendor_selection_authority")
        if vendor_auth:
            vendor_positives.append(DocumentFinding(
                text=f"Vendor selection: {_clean_display_value(vendor_auth[:80])}",
                is_positive=True
            ))
        if pma_result.get("vendor_insurance_requirements"):
            vendor_positives.append(DocumentFinding(text="Vendor insurance/qualification requirements specified", is_positive=True))
        if not pma_result.get("has_escalation_procedures"):
            vendor_negatives.append(DocumentFinding(text="No vendor escalation or backup procedures", is_positive=False, is_missing=True))

        vendor_findings = _interleave_findings(vendor_positives, vendor_negatives, max_findings=4)
        analysis.vendor_policies = DocumentSection(
            title="Vendor Management Policies",
            status="Partially Documented" if vendor_findings else "Not Documented",
            status_tier="needs-work" if vendor_findings else "not-ready",
            findings=vendor_findings,
        )

        # Maintenance SOPs section
        sop_positives = []
        sop_negatives = []
        reserve_amt = config.get("maintenance_reserve_amount") or pma_result.get("maintenance_reserve_amount")
        if pma_result.get("maintenance_reserve_required") and reserve_amt:
            sop_positives.append(DocumentFinding(
                text=f"Maintenance reserve required ({_clean_display_value(str(reserve_amt))})",
                is_positive=True
            ))
        approval_workflow = pma_result.get("owner_approval_workflow")
        if approval_workflow:
            sop_positives.append(DocumentFinding(
                text=f"Owner approval workflow: {_clean_display_value(str(approval_workflow)[:80])}",
                is_positive=True
            ))
        sop_negatives.append(DocumentFinding(text="No standardized troubleshooting steps by issue type", is_positive=False, is_missing=True))
        sop_negatives.append(DocumentFinding(text="No resident communication templates or cadences", is_positive=False, is_missing=True))

        analysis.maintenance_sops = DocumentSection(
            title="Maintenance SOPs",
            status="Partially Documented",
            status_tier="needs-work",
            findings=_interleave_findings(sop_positives, sop_negatives, max_findings=4),
        )

    else:
        analysis.pma = DocumentSection(
            title="Property Management Agreement (PMA)",
            status="Not Provided",
            status_tier="not-ready",
            findings=[DocumentFinding(text="PMA was not provided for analysis", is_positive=False, is_missing=True)],
        )

    return analysis
