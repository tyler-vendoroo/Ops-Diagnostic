"""AI Interpretation — Stage 3 of the WO Processing Pipeline.

Takes computed metrics from wo_processor.py and generates narrative insights.
The AI never sees the raw spreadsheet data — only pre-computed numbers.
"""
import json
import time
from typing import Optional

import anthropic

from app.config import settings

ANTHROPIC_API_KEY = settings.anthropic_api_key
ANTHROPIC_MODEL = settings.anthropic_model


def build_interpretation_prompt(metrics: dict, client_info: dict) -> tuple[str, str]:
    """
    Build the AI prompt for generating narrative insights from computed metrics.
    Returns (system_prompt, user_prompt).
    """

    system = """You are a senior property management operations analyst writing findings for a client-facing Operations Analysis report. You write specific, data-driven insights that reference actual numbers from the computed metrics.

Write in a tone that is informative and constructive, not alarmist. Frame findings as opportunities, not failures. The audience is a property management company evaluating Vendoroo for AI maintenance coordination.

IMPORTANT CONTEXT — read carefully before interpreting metrics:
- "First response time" is the time from a RESIDENT submitting a work order to receiving their first acknowledgment. It is NOT about when a vendor gets dispatched. Frame it as resident experience and communication speed.
- "Concentrated trades" (>25% of volume in one trade) is an operational pattern, not a risk. High HVAC volume in summer is normal seasonality. Do NOT frame trade concentration as a failure — explain what drives it and what it means operationally.
- "Concentrated portfolio" (few owners with many doors, or high top-vendor %) is a BUSINESS/REVENUE risk — losing one owner or vendor means losing significant revenue or coverage. Do NOT frame this as a maintenance or work order risk.
- "Open WO rate" is the percentage of all work orders that remain unresolved. High rates indicate backlogs or data export timing. Do not conflate with poor performance unless the rate is clearly anomalous.
- Do NOT conflate maintenance metrics with business strategy metrics. Keep each finding to its correct domain.

RULES:
- Reference specific numbers from the metrics (not vague statements)
- Generate exactly 4-6 key findings
- Each finding must be 2-3 sentences maximum. Title must be 5 words or fewer.
- Focus on the specific data point and its operational implication.
- Do not write lengthy explanations or multi-paragraph findings.
- Connect findings to operational impact where possible
- Never use the word "mold" — use "water damage" or "moisture accumulation"
- Do not invent data or metrics not provided
- If a metric is null or unavailable, note what it means operationally (not as a data problem)

OUTPUT FORMAT:
Return a JSON array of finding objects:
[
  {
    "title": "Short Title (max 5 words)",
    "body": "2-3 sentence finding with specific numbers",
    "severity": "high" | "medium" | "low",
    "related_gap": "response_time" | "vendor_coverage" | "open_wo_rate" | "after_hours" | "emergency_protocol" | "nte_governance" | "communication_channels" | "category_concentration" | "repeat_units" | "volume_high" | "reactive_maintenance" | "seasonal_pattern" | null
  }
]"""

    seasonal_line = "Insufficient data for seasonal analysis (need 6+ months)"
    if metrics.get("seasonal_data"):
        seasonal_line = f"Seasonal spikes detected: {metrics['seasonal_data']['spikes']}"

    user = f"""Analyze these computed work order metrics for {client_info.get('company_name', 'the client')} ({client_info.get('door_count', 'N/A')} doors, {client_info.get('property_count', 'N/A')} properties, {client_info.get('operational_model', 'N/A')} model).

COMPUTED METRICS:

Volume & Benchmarking:
- Monthly maintenance WO volume: {metrics.get('monthly_avg', 'N/A')} (excluding {metrics.get('recurring_wos', 0)} recurring/scheduled)
- WOs per door per year: {metrics.get('wo_per_door_annual', 'N/A')} (assessment: {metrics.get('volume_assessment', 'N/A')}, benchmarks: <3 low/well-maintained, 3-6 normal, >6 high/aging)
- Data range: {metrics.get('months_spanned', 'N/A')} months ({metrics.get('date_range_days', 'N/A')} days)

Core Operational Metrics:
- Open WO rate: {metrics.get('open_wo_rate_pct', 'N/A')}% ({metrics.get('open_wo_count', 'N/A')} open across {client_info.get('door_count', 'N/A')} doors)
- Median completion time: {metrics.get('median_completion_days', 'N/A')} days
- First response time: {metrics.get('avg_first_response_hours', 'N/A')} hours (method: {metrics.get('response_time_method', 'N/A')}) — {metrics.get('response_time_note', '')}

Vendor Analysis:
- Unique external vendors: {metrics.get('unique_vendors', 'N/A')}
- Top vendor handles: {metrics.get('top_vendor_pct', 'N/A')}% of WOs
- Trades covered: {metrics.get('trades_covered_count', 'N/A')} of {metrics.get('trades_required_count', 'N/A')} required
- Missing trades: {metrics.get('missing_trades', [])}
- Internal staff handled: {metrics.get('internal_pct', 'N/A')}% of WOs ({metrics.get('internal_count', 0)} total)

Trade & Category Analysis:
- Concentrated trades (>25% of volume): {metrics.get('concentrated_trades', {})}
- High-volume trades (anomalous per-door rate): {metrics.get('high_volume_trades', {})}
- Repeat units (3+ WOs): {len(metrics.get('repeat_units', {}))} units flagged. Top units: {dict(list(metrics.get('repeat_units', {}).items())[:3])}

After Hours & Emergencies:
- After-hours volume: {metrics.get('after_hours_pct', 'N/A')}% ({metrics.get('after_hours_count', 0)} WOs)
- Emergency WOs: {metrics.get('emergency_count', 0)} ({metrics.get('emergency_after_hours', 0)} after hours)

Reactive vs. Preventive:
- Reactive maintenance: {metrics.get('reactive_pct', 'N/A')}% of WOs are reactive (resident or staff initiated)
- Estimate-heavy workload: {metrics.get('estimate_heavy_pct', 0)}% of WOs in estimate/approval status
- Unit turns: {metrics.get('unit_turn_count', 0)} turnover-related WOs
- Source distribution: {metrics.get('source_distribution', {})}

Seasonal Patterns:
- {seasonal_line}

Cost & NTE:
- Cost data: {'Available' if metrics.get('cost_data_available') else 'Not available'}, median ${metrics.get('median_cost', 'N/A')} per WO
- NTE from PMS: {metrics.get('pms_ntes', 'Not available')}

Data Quality:
- {metrics.get('data_quality', [])}

CLIENT GOAL: {client_info.get('primary_goal', 'not specified')}

Generate 3-5 key findings for the Operations Analysis report. Prioritize findings that are:
1. Most relevant to the client's stated goal
2. Supported by the strongest data (not based on sparse or low-quality fields)
3. Actionable during Vendoroo onboarding
If volume is high, explain what it signals operationally. If specific trades have anomalous volume, connect it to potential root causes (aging systems, deferred maintenance, seasonal patterns)."""

    return system, user


def interpret_wo_metrics(metrics: dict, client_info: dict) -> list[dict]:
    """
    Call Claude to generate narrative findings from computed WO metrics.
    Returns a list of finding dicts with title, body, severity, related_gap.
    Includes a simple 3-attempt retry loop with 1s backoff on transient errors.
    """
    system_prompt, user_prompt = build_interpretation_prompt(metrics, client_info)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            break
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(1)
    else:
        raise RuntimeError(f"Claude API failed after 3 attempts: {last_error}") from last_error

    # Parse the JSON response
    text = response.content[0].text.strip()

    # Handle markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    try:
        findings = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: try to extract JSON array from the response
        import re
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            findings = json.loads(match.group())
        else:
            findings = [{
                "title": "Analysis Complete",
                "body": "Work order metrics have been computed. See the detailed metrics in the report.",
                "severity": "medium",
                "related_gap": None,
            }]

    return findings
