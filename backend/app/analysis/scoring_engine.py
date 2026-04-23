"""Scoring engine: computes 8 category scores and overall readiness score."""
from app.models.analysis import (
    CategoryScore,
    DocumentAnalysis,
    GapFinding,
    KeyFinding,
    ImpactProjection,
    StaffingProjection,
    VendorMetrics,
    WorkOrderMetrics,
    PortfolioMetrics,
)
from app.models.input_data import ClientInfo
from app.config import DEFAULT_CATEGORY_WEIGHTS, REQUIRED_TRADES, CORE_TRADES, SPECIALTY_TRADES
from app.config.benchmarks import VENDOROO_AVG, TOP_PERFORMERS, STAFFING_BENCHMARKS


def _clamp(value: float, low: float = 0, high: float = 100) -> int:
    """Clamp a value to an integer in [low, high]."""
    return int(max(low, min(high, round(value))))


def _tier(score: int) -> str:
    """Return tier label for a score."""
    if score >= 70:
        return "Ready"
    if score >= 50:
        return "Needs Work"
    return "Not Ready"


def _tier_css(tier: str) -> str:
    """Return CSS class for a tier."""
    return {"Ready": "ready", "Needs Work": "needs-work", "Not Ready": "not-ready"}[tier]


def _tier_color(tier: str) -> str:
    """Return CSS color variable for a tier."""
    return {"Ready": "var(--green)", "Needs Work": "var(--amber)", "Not Ready": "var(--red)"}[tier]


# ── Individual Category Scorers ──────────────────────────

def score_policy_completeness(doc: DocumentAnalysis) -> int:
    """Score based on documentation of policies, approval rules, and SOPs.

    Base of 25 even without docs (prospect has some policies, just not shared).
    Documents add up to 75 more points.
    """
    score = 25  # Base: every PM company has some policies
    # PMA present and quality
    if doc.pma and doc.pma.status != "Not Provided":
        score += 15  # Base for providing PMA
        score += min(12, doc.pma_quality_score * 1.2)  # Quality bonus
    # Lease present and quality
    if doc.lease and doc.lease.status != "Not Provided":
        score += 12
        score += min(10, doc.lease_quality_score * 1.0)
    # NTE defined
    if doc.nte_threshold:
        score += 10
    if doc.nte_is_tiered:
        score += 8
    # Emergency authorization
    if doc.has_emergency_protocols:
        score += 8
    return _clamp(score)


def score_vendor_coverage(vendor_metrics: VendorMetrics, wo_metrics: WorkOrderMetrics = None) -> int:
    """Score vendor coverage. Core trades are the denominator; specialty trades are a bonus.

    Core trades (80 pts): Vendoroo's 8 recommended trades every PM company needs.
    Specialty trades (20 pts): portfolio-dependent — not penalized for missing.
    """
    core_set = {t.lower() for t in CORE_TRADES}
    specialty_set = {t.lower() for t in SPECIALTY_TRADES}

    # Prefer wo_metrics as source of truth (has normalized trade names)
    if wo_metrics and wo_metrics.covered_trades is not None:
        covered_trades = {t.lower().replace("_", " ") for t in (wo_metrics.covered_trades or [])}

        core_covered = len(covered_trades & core_set)
        specialty_covered = len(covered_trades & specialty_set)

        core_pct = core_covered / len(CORE_TRADES) if CORE_TRADES else 0
        core_score = round(core_pct * 80)

        max_specialty = len(SPECIALTY_TRADES)
        specialty_score = round((specialty_covered / max_specialty) * 20) if max_specialty else 0

        return _clamp(core_score + specialty_score)

    # Fallback: vendor_metrics (legacy path)
    if vendor_metrics and vendor_metrics.trades_missing is not None:
        missing_set = {t.lower() for t in (vendor_metrics.trades_missing or [])}
        core_missing = len(missing_set & core_set)
        core_covered = len(CORE_TRADES) - core_missing

        core_pct = core_covered / len(CORE_TRADES) if CORE_TRADES else 0
        core_score = round(core_pct * 80)

        specialty_missing = len(missing_set & specialty_set)
        specialty_covered = max(0, len(SPECIALTY_TRADES) - specialty_missing)
        max_specialty = len(SPECIALTY_TRADES)
        specialty_score = round((specialty_covered / max_specialty) * 20) if max_specialty else 0

        return _clamp(core_score + specialty_score)

    return 50  # Default when no data


def score_response_efficiency(wo_metrics: WorkOrderMetrics, model: str) -> int:
    """Score based on response and completion times vs benchmarks."""
    score = 10  # Baseline

    # First response time (0-50 pts) — primary signal
    if wo_metrics.avg_first_response_hours is not None:
        hrs = wo_metrics.avg_first_response_hours
        if hrs <= 1:
            score += 50
        elif hrs <= 4:
            score += 40
        elif hrs <= 12:
            score += 25
        elif hrs <= 24:
            score += 10
        # > 24 hrs: 0

    # Completion time (0-40 pts) — secondary signal
    if wo_metrics.median_completion_days is not None:
        days = wo_metrics.median_completion_days
        if days <= 2:
            score += 40
        elif days <= 4:
            score += 30
        elif days <= 7:
            score += 20
        elif days <= 14:
            score += 10
        # > 14 days: 0

    # open_wo_rate captured in operational_consistency, not here
    return _clamp(score)


def score_documentation_quality(doc: DocumentAnalysis) -> int:
    """Score based on document clarity and completeness.

    Base of 30 even without docs (every PM company has some documentation).
    Providing docs for review adds significant points.
    """
    score = 30  # Base: they have docs, just maybe not shared yet
    # PMA quality (0-25)
    if doc.pma and doc.pma.status != "Not Provided":
        score += 10  # Provided it
        score += _clamp(doc.pma_quality_score * 1.5, 0, 15)  # Quality
    # Lease quality (0-20)
    if doc.lease and doc.lease.status != "Not Provided":
        score += 8
        score += _clamp(doc.lease_quality_score * 1.2, 0, 12)
    # Emergency docs (0-15)
    score += _clamp(doc.emergency_readiness_score * 3, 0, 15)
    return _clamp(score)


def score_operational_consistency(wo_metrics: WorkOrderMetrics) -> int:
    """Score based on workflow repeatability and consistency."""
    score = 50  # Base score

    # Completion time consistency — use open WO rate as proxy
    # (low open rate + reasonable completion time = consistent ops)
    if wo_metrics.median_completion_days is not None:
        if wo_metrics.median_completion_days < 3:
            score += 25
        elif wo_metrics.median_completion_days < 7:
            score += 15
        elif wo_metrics.median_completion_days < 14:
            score += 5

    # Sufficient data volume suggests consistent processes
    if wo_metrics.months_spanned >= 12:
        score += 10
    elif wo_metrics.months_spanned >= 6:
        score += 5

    # Reasonable open WO rate suggests good follow-through
    if wo_metrics.open_wo_rate_pct < 10:
        score += 15
    elif wo_metrics.open_wo_rate_pct < 20:
        score += 5

    return _clamp(score)


def score_after_hours_readiness(wo_metrics: WorkOrderMetrics, doc: DocumentAnalysis) -> int:
    """Score based on after-hours coverage capability."""
    score = 5  # Base

    # Coverage quality via after_hours_pct (set by survey adapter from method):
    # 24/7→30%, answering_service→25%, on_call→20%, voicemail→15%, none→10%
    pct = wo_metrics.after_hours_pct or 0
    if pct >= 30:
        score += 55   # 24/7 coverage
    elif pct >= 25:
        score += 45   # answering service
    elif pct >= 20:
        score += 35   # on-call rotation
    elif pct >= 15:
        score += 20   # voicemail only
    else:
        score += 10   # none / unknown

    if doc.has_emergency_protocols:
        score += 20
    if doc.has_defined_slas:
        score += 15
    if doc.has_escalation_procedures:
        score += 10

    return _clamp(score)


def score_emergency_protocols(doc: DocumentAnalysis) -> int:
    """Score based on emergency classification, triage, and escalation.

    Base of 15 — most companies handle emergencies somehow, just not formally.
    """
    score = 15  # Base: they handle emergencies, just informally

    if doc.has_emergency_protocols:
        score += 25
    if doc.has_defined_slas:
        score += 20
    if doc.has_escalation_procedures:
        score += 20

    # Quality of emergency documentation
    score += _clamp(doc.emergency_readiness_score * 2, 0, 20)

    return _clamp(score)


def score_scalability_potential(
    portfolio: PortfolioMetrics,
    wo_metrics: WorkOrderMetrics,
    vendor_metrics: VendorMetrics,
    model: str,
) -> int:
    """Score based on growth potential and AI leverage opportunity."""
    benchmarks = STAFFING_BENCHMARKS.get(model, STAFFING_BENCHMARKS["va"])
    score = 0

    # Doors-per-staff ratio vs benchmark (lower = more room to scale)
    if portfolio.doors_per_staff > 0:
        headroom = benchmarks["vendoroo_benchmark"] / portfolio.doors_per_staff
        if headroom > 2:
            score += 30  # Lots of scale potential
        elif headroom > 1.5:
            score += 25
        elif headroom > 1:
            score += 15
        else:
            score += 5

    # WO volume manageable
    wo_per_door_annual = wo_metrics.wo_per_door_annual
    if wo_per_door_annual is None:
        wo_per_door_annual = (wo_metrics.monthly_avg_work_orders / max(1, portfolio.total_doors)) * 12
    if wo_per_door_annual < 9.6:
        score += 25
    elif wo_per_door_annual < 14.4:
        score += 15
    else:
        score += 5

    # Vendor network can support growth — prefer wo_metrics as source of truth
    vendor_count = wo_metrics.unique_vendors if wo_metrics.unique_vendors else vendor_metrics.total_vendors
    if vendor_count >= 15:
        score += 25
    elif vendor_count >= 10:
        score += 15
    elif vendor_count >= 5:
        score += 10

    # Process standardization indicator — use median completion as proxy
    if wo_metrics.median_completion_days is not None and wo_metrics.median_completion_days < 7:
        score += 20
    else:
        score += 10

    return _clamp(score)


# ── Main Scoring Function ────────────────────────────────

def calculate_all_scores(
    wo_metrics: WorkOrderMetrics,
    vendor_metrics: VendorMetrics,
    portfolio: PortfolioMetrics,
    doc_analysis: DocumentAnalysis,
    client_info: ClientInfo,
) -> list[CategoryScore]:
    """Calculate all 8 category scores."""
    model = client_info.operational_model

    scores_raw = {
        "policy_completeness": ("Policy Completeness", score_policy_completeness(doc_analysis)),
        "vendor_coverage": ("Vendor Coverage", score_vendor_coverage(vendor_metrics, wo_metrics)),
        "response_efficiency": ("Response Efficiency", score_response_efficiency(wo_metrics, model)),
        "documentation_quality": ("Documentation Quality", score_documentation_quality(doc_analysis)),
        "operational_consistency": ("Operational Consistency", score_operational_consistency(wo_metrics)),
        "after_hours_readiness": ("After Hours Readiness", score_after_hours_readiness(wo_metrics, doc_analysis)),
        "emergency_protocols": ("Emergency Protocols", score_emergency_protocols(doc_analysis)),
        "scalability_potential": ("Scalability Potential", score_scalability_potential(portfolio, wo_metrics, vendor_metrics, model)),
    }

    categories = []
    for key, (name, score) in scores_raw.items():
        tier = _tier(score)
        categories.append(CategoryScore(
            name=name,
            key=key,
            score=score,
            tier=tier,
            tier_css=_tier_css(tier),
            color=_tier_color(tier),
        ))

    return categories


def calculate_overall_score(
    categories: list[CategoryScore],
    weights: dict[str, float] = None,
) -> int:
    """Calculate weighted overall readiness score."""
    if weights is None:
        weights = DEFAULT_CATEGORY_WEIGHTS
    total = sum(cat.score * weights.get(cat.key, 0.125) for cat in categories)
    return _clamp(total)


# ── Key Findings Generator ───────────────────────────────

def generate_key_findings(
    wo_metrics: WorkOrderMetrics,
    vendor_metrics: VendorMetrics,
    portfolio: PortfolioMetrics,
    doc_analysis: DocumentAnalysis,
    client_info: ClientInfo,
) -> list[KeyFinding]:
    """Generate key findings based on the prospect's specific operational data.

    Each finding is conditional on actual metrics. No artificial cap —
    the count reflects how many actionable observations the data supports.
    """
    findings = []
    model = client_info.operational_model
    benchmarks = VENDOROO_AVG.get(model, VENDOROO_AVG["va"])
    staff_benchmark = STAFFING_BENCHMARKS.get(model, STAFFING_BENCHMARKS["va"])

    # ── Staff label helpers (singular/plural aware) ──
    if model == "pod":
        staff_label_s, staff_label_p = "pod", "pods"
    elif model == "tech":
        staff_label_s, staff_label_p = "technician", "technicians"
    else:
        staff_label_s, staff_label_p = "coordinator", "coordinators"

    staff_count = client_info.staff_count
    staff_word = staff_label_s if staff_count == 1 else staff_label_p

    doors_per = portfolio.doors_per_staff
    benchmark_per = staff_benchmark["current_benchmark"]
    vendoroo_per = staff_benchmark["vendoroo_benchmark"]
    scale_doors = staff_count * vendoroo_per
    optimize_staff = max(1, round(client_info.door_count / vendoroo_per))

    # ── 1. Response Time ──
    if wo_metrics.avg_first_response_hours is not None:
        hrs = wo_metrics.avg_first_response_hours
        if hrs > 12:
            findings.append(KeyFinding(
                title="Response Time Gap",
                description=(
                    f"Your average first response of {hrs} hours means most requests wait "
                    f"until the next business day. Vendoroo's average is under 10 minutes. "
                    f"This gap compounds after hours, where every evening request adds "
                    f"8 to 12 hours before a vendor is even contacted."
                ),
                color="var(--red)",
            ))
        elif hrs > 4:
            findings.append(KeyFinding(
                title="Response Time Gap",
                description=(
                    f"Your average first response of {hrs} hours is common for teams "
                    f"managing dispatch manually. Vendoroo's average is under 10 minutes — "
                    f"AI triage and auto-dispatch eliminate the queue between request and action."
                ),
                color="var(--amber)",
            ))
        elif hrs > 1:
            findings.append(KeyFinding(
                title="Response Time Opportunity",
                description=(
                    f"Your average first response of {hrs} hours shows reasonable urgency. "
                    f"AI coordination can compress this to under 10 minutes by eliminating "
                    f"the manual triage step between resident request and vendor contact."
                ),
                color="var(--amber)",
            ))
        else:
            findings.append(KeyFinding(
                title="Strong Response Time",
                description=(
                    f"Your average first response of {hrs} hours is already fast. "
                    f"AI coordination maintains this speed 24/7 — including nights, "
                    f"weekends, and holidays when manual teams typically slow down."
                ),
                color="var(--green)",
            ))

    # ── 2. Open WO Rate ──
    if wo_metrics.open_wo_rate_pct is not None:
        rate = wo_metrics.open_wo_rate_pct
        if rate > 20:
            findings.append(KeyFinding(
                title="High Open Work Order Rate",
                description=(
                    f"Your open work order rate of {rate}% means roughly 1 in 5 requests "
                    f"is unresolved at any given time. Vendoroo clients average {benchmarks['open_wo_rate_pct']}%. "
                    f"AI follow-up sequences and automated vendor check-ins close the loop "
                    f"on stalled work orders without manual chasing."
                ),
                color="var(--red)",
            ))
        elif rate > 15:
            findings.append(KeyFinding(
                title="Open Work Order Rate",
                description=(
                    f"Your open work order rate of {rate}% is above the Vendoroo average "
                    f"of {benchmarks['open_wo_rate_pct']}%. Automated follow-up and vendor "
                    f"accountability tracking can reduce this by 40-60%."
                ),
                color="var(--amber)",
            ))
        elif rate <= 5:
            findings.append(KeyFinding(
                title="Excellent Completion Rate",
                description=(
                    f"Your open work order rate of {rate}% is at or below top performer "
                    f"levels. AI coordination helps maintain this as you scale by ensuring "
                    f"no work order falls through the cracks during high-volume periods."
                ),
                color="var(--green)",
            ))

    # ── 3. Vendor Coverage ──
    covered = wo_metrics.trades_covered_count
    required = wo_metrics.trades_required_count or 12
    if wo_metrics.missing_trades:
        missing_str = ", ".join(wo_metrics.missing_trades[:4])
        missing_count = len(wo_metrics.missing_trades)
        findings.append(KeyFinding(
            title="Vendor Coverage Gaps",
            description=(
                f"You have {wo_metrics.unique_vendors} vendors covering "
                f"{covered} of {required} required trades. "
                f"Missing coverage in {missing_str} "
                f"{'creates a single point' if missing_count == 1 else 'creates single points'} "
                f"of failure during peak demand or vendor unavailability."
            ),
            color="var(--red)" if missing_count >= 3 else "var(--amber)",
        ))
    elif wo_metrics.unique_vendors > 0 and covered >= required:
        findings.append(KeyFinding(
            title="Strong Vendor Coverage",
            description=(
                f"You have {wo_metrics.unique_vendors} vendors covering all "
                f"{required} required trades. AI coordination maximizes this network "
                f"by routing each job to the best-fit vendor based on trade, "
                f"availability, and past performance."
            ),
            color="var(--green)",
        ))

    # ── 4. After Hours Coverage ──
    if wo_metrics.after_hours_pct is not None and wo_metrics.after_hours_pct > 0:
        ah_pct = wo_metrics.after_hours_pct
        if not doc_analysis.has_emergency_protocols and ah_pct > 15:
            findings.append(KeyFinding(
                title="After Hours Exposure",
                description=(
                    f"{ah_pct}% of your maintenance requests come in after hours, "
                    f"but you have no written emergency protocols. Without documented "
                    f"triage criteria, after-hours decisions rely on individual judgment — "
                    f"AI needs clear rules to handle these consistently."
                ),
                color="var(--red)",
            ))
        elif ah_pct > 25:
            findings.append(KeyFinding(
                title="Heavy After Hours Volume",
                description=(
                    f"{ah_pct}% of your maintenance requests come in after hours. "
                    f"This is above typical ranges and suggests residents are actively "
                    f"submitting evenings and weekends. AI triage handles this volume "
                    f"24/7 without adding staff or answering service costs."
                ),
                color="var(--amber)",
            ))

    # ── 5. Emergency Protocols ──
    if not doc_analysis.has_emergency_protocols:
        findings.append(KeyFinding(
            title="No Written Emergency Protocols",
            description=(
                "Without documented emergency criteria, triage decisions rely on "
                "individual judgment. This creates inconsistency — what one person "
                "escalates as urgent, another might queue until morning. "
                "AI needs explicit rules to classify and route emergencies correctly."
            ),
            color="var(--red)",
        ))

    # ── 6. NTE Governance ──
    if doc_analysis.nte_threshold and not doc_analysis.nte_is_tiered:
        findings.append(KeyFinding(
            title="Flat Maintenance Limit (NTE)",
            description=(
                f"Your {doc_analysis.nte_threshold} maintenance limit (NTE) applies uniformly "
                f"across all work types. A $200 faucet repair and a $200 HVAC diagnostic "
                f"face the same approval rules. Tiered limits by trade and urgency let AI "
                f"auto-approve routine work while flagging exceptions."
            ),
            color="var(--amber)",
        ))
    elif not doc_analysis.nte_threshold:
        findings.append(KeyFinding(
            title="No Maintenance Limits Defined",
            description=(
                "Without defined maintenance limits (NTEs), you find out what a job costs "
                "after it's done. Defined limits let AI auto-approve routine work under "
                "threshold and flag anything above — so you're only reviewing the exceptions."
            ),
            color="var(--red)",
        ))

    # ── 7. Documentation ──
    has_both_docs = (
        doc_analysis.pma and doc_analysis.pma.status != "Not Provided"
        and doc_analysis.lease and doc_analysis.lease.status != "Not Provided"
    )
    if has_both_docs:
        findings.append(KeyFinding(
            title="Strong Documentation Base",
            description=(
                "Your PMA and lease templates are well-structured with clear maintenance "
                "responsibility language. This gives Vendoroo a strong starting point for "
                "Maintenance Book configuration with minimal policy clarification needed."
            ),
            color="var(--green)",
        ))
    # For quick diagnostic: no docs is the default state, not a finding.
    # Only flag documentation gaps in the full path where docs were uploaded and found lacking.

    # ── 8. Scalability ──
    if client_info.door_count < scale_doors:
        growth_pct = round((scale_doors - client_info.door_count) / client_info.door_count * 100)
        findings.append(KeyFinding(
            title="Scale Opportunity",
            description=(
                f"With {staff_count} {staff_word} managing {client_info.door_count} doors "
                f"({int(doors_per)} doors/{staff_label_s}), AI coordination could extend "
                f"your current team to {scale_doors}+ doors — a {growth_pct}% increase "
                f"without adding headcount."
            ),
            color="var(--blue)",
        ))
    elif staff_count > optimize_staff and optimize_staff < staff_count:
        fte_savings = staff_count - optimize_staff
        findings.append(KeyFinding(
            title="Staffing Optimization",
            description=(
                f"With {staff_count} {staff_word} managing {client_info.door_count} doors "
                f"({int(doors_per)} doors/{staff_label_s}), AI coordination could support "
                f"the same portfolio with {optimize_staff} {staff_label_s if optimize_staff == 1 else staff_label_p}, "
                f"freeing {fte_savings} FTE{'s' if fte_savings != 1 else ''} for growth or redeployment."
            ),
            color="var(--blue)",
        ))
    else:
        findings.append(KeyFinding(
            title="High Operational Efficiency",
            description=(
                f"At {int(doors_per)} doors/{staff_label_s}, you are already operating "
                f"above the industry benchmark of {benchmark_per}. AI coordination "
                f"protects this efficiency as you grow — maintaining response times and "
                f"consistency that would otherwise degrade with added volume."
            ),
            color="var(--green)",
        ))

    # ── 9. SLA Definition ──
    if not doc_analysis.has_defined_slas:
        findings.append(KeyFinding(
            title="No Defined SLAs",
            description=(
                "Without explicit service level agreements, there is no measurable "
                "standard for vendor performance. AI coordination enforces SLAs "
                "automatically — tracking response times, flagging misses, and "
                "escalating before deadlines are breached."
            ),
            color="var(--amber)",
        ))

    # ── 10. Property Concentration ──
    if client_info.property_count and client_info.property_count > 0:
        dpp = client_info.door_count / client_info.property_count
        if dpp >= 10:
            findings.append(KeyFinding(
                title="Concentrated Portfolio",
                description=(
                    f"Your portfolio averages {round(dpp)} doors per property "
                    f"({client_info.door_count} doors across {client_info.property_count} "
                    f"{'property' if client_info.property_count == 1 else 'properties'}). "
                    f"At this concentration, a single building event — HVAC failure, "
                    f"water intrusion, pest issue — can generate many concurrent work orders. "
                    f"Vendor capacity and triage speed matter more at higher ratios."
                ),
                color="var(--amber)" if dpp < 50 else "var(--red)",
            ))

    return findings


# ── Gap Analysis Generator ───────────────────────────────

def generate_gaps(
    categories: list[CategoryScore],
    wo_metrics: WorkOrderMetrics,
    vendor_metrics: VendorMetrics,
    doc_analysis: DocumentAnalysis,
    client_info: ClientInfo,
) -> list[GapFinding]:
    """Generate gap findings with data-driven details and recommendations.

    Every detail sentence references actual values from the analysis.
    No hardcoded fiction. If we don't have data, say so.
    """
    gaps = []
    score_map = {cat.key: cat.score for cat in categories}

    def _severity(score: int) -> tuple[str, bool]:
        is_high = score < 50
        return ("High Priority" if is_high else "Medium Priority"), is_high

    def _colors(is_high: bool) -> dict:
        return {
            "severity_color": "var(--red)" if is_high else "var(--amber)",
            "severity_bg": "var(--red-light)" if is_high else "var(--amber-light)",
            "severity_border": "var(--red)" if is_high else "var(--amber)",
        }

    # ── Emergency Protocol ──
    if score_map.get("emergency_protocols", 0) < 70:
        sev, is_high = _severity(score_map["emergency_protocols"])
        if doc_analysis.has_emergency_protocols:
            detail = (
                "Emergency authorization exists in your PMA but lacks specific classification "
                "criteria. Without defined triage rules by urgency level, after-hours handling "
                "depends on individual judgment."
            )
        elif doc_analysis.pma and doc_analysis.pma.status not in ("Not Documented", "Not Provided"):
            detail = (
                "Your PMA was reviewed but contains no emergency authorization language. "
                "Without documented criteria, after-hours triage relies on answering service "
                "judgment with no escalation rules."
            )
        else:
            detail = (
                "No policy documents were provided for emergency protocol assessment. "
                "Your Advisor will work with you to define emergency categories and "
                "escalation paths during onboarding."
            )
        gaps.append(GapFinding(
            title="Emergency Protocol",
            severity=sev, **_colors(is_high),
            detail=detail,
            recommendation=(
                "Your Advisor works with you to define emergency categories, response SLAs, "
                "and escalation paths during onboarding. These are encoded directly into your "
                "Maintenance Book so your AI teammate knows exactly how to handle emergencies."
            ),
        ))

    # ── Vendor Coverage ──
    if score_map.get("vendor_coverage", 0) < 70:
        sev, is_high = _severity(score_map["vendor_coverage"])
        covered = wo_metrics.trades_covered_count
        required = wo_metrics.trades_required_count or 12
        vendor_count = wo_metrics.unique_vendors

        if wo_metrics.missing_trades:
            missing_str = ", ".join(wo_metrics.missing_trades[:4])
            detail = (
                f"{vendor_count} vendors covering {covered} of {required} required trades. "
                f"Missing: {missing_str}."
            )
        elif not vendor_count:
            detail = (
                "No vendor assignment data found in work order history. "
                "Vendor coverage could not be assessed from the uploaded data."
            )
        else:
            detail = (
                f"{vendor_count} vendors detected but trade classification could not confirm "
                f"coverage across all {required} required trades."
            )
        gaps.append(GapFinding(
            title="Vendor Coverage",
            severity=sev, **_colors(is_high),
            detail=detail,
            recommendation=(
                "Your Advisor maps your existing vendor network against required trades and "
                "identifies specific gaps. You can fill those during onboarding, or Vendoroo "
                "can assist through our vendor recruitment product."
            ),
        ))

    # ── Response Time SLAs ──
    if score_map.get("response_efficiency", 0) < 70:
        sev, is_high = _severity(score_map["response_efficiency"])
        hrs = wo_metrics.avg_first_response_hours
        if hrs is not None:
            detail = (
                f"Average first response of {hrs} hours compared to Vendoroo's average "
                f"of under 10 minutes. "
            )
            if hrs > 12:
                detail += "Most requests wait until the next business day before a vendor is contacted."
            elif hrs > 4:
                detail += "Requests submitted in the afternoon often roll to the next morning."
        else:
            detail = (
                "Response time could not be measured from the available data. "
                "No defined response time targets were identified."
            )
        gaps.append(GapFinding(
            title="Response Time SLAs",
            severity=sev, **_colors(is_high),
            detail=detail,
            recommendation=(
                "Your Advisor helps you define SLA targets by urgency level and configures "
                "your AI teammate to meet them — including vendor-specific expectations so "
                "the right vendor responds within the right timeframe."
            ),
        ))

    # ── NTE Governance ──
    if doc_analysis.nte_threshold and not doc_analysis.nte_is_tiered:
        gaps.append(GapFinding(
            title="Maintenance Limit (NTE) Governance",
            severity="Medium Priority",
            severity_color="var(--amber)",
            severity_bg="var(--amber-light)",
            severity_border="var(--amber)",
            detail=f"Single {doc_analysis.nte_threshold} maintenance limit across all work types. No differentiation by trade, property, or urgency.",
            recommendation=(
                "Your Advisor guides you on structuring tiered maintenance limits — "
                "different thresholds by trade, property type, and urgency. Your AI teammate "
                "then enforces these automatically on every work order."
            ),
        ))

    # ── After Hours ──
    if score_map.get("after_hours_readiness", 0) < 70:
        sev, is_high = _severity(score_map["after_hours_readiness"])
        ah_pct = wo_metrics.after_hours_pct
        if ah_pct and ah_pct > 0:
            detail = f"{ah_pct}% of maintenance requests occur after hours. "
            if not doc_analysis.has_emergency_protocols:
                detail += (
                    "No documented triage criteria exist for after-hours handling, "
                    "so urgent issues queue until the next business day."
                )
            else:
                detail += (
                    "Emergency protocols exist but after-hours coverage may not include "
                    "AI triage and automated dispatch."
                )
        else:
            detail = (
                "After-hours coverage could not be fully assessed. "
                "Time-of-day data may not be available in the work order export."
            )
        gaps.append(GapFinding(
            title="After Hours Operations",
            severity=sev, **_colors(is_high),
            detail=detail,
            recommendation=(
                "Your Advisor configures Rooceptionist for 24/7 intelligent call handling "
                "with AI triage and troubleshooting. For full emergency dispatch, RescueRoo "
                "extends your team's capabilities to true 24/7."
            ),
        ))

    # ── Policy Documentation ──
    if score_map.get("policy_completeness", 0) < 70:
        sev_score = score_map["policy_completeness"]
        is_minor = sev_score >= 50
        sev = "Low Priority" if is_minor else "Medium Priority"

        has_pma = doc_analysis.pma and doc_analysis.pma.status not in ("Not Provided", "Not Documented")
        has_lease = doc_analysis.lease and doc_analysis.lease.status not in ("Not Provided", "Not Documented")

        if has_pma and has_lease:
            detail = (
                f"PMA status: {doc_analysis.pma.status}. "
                f"Lease status: {doc_analysis.lease.status}. "
            )
            missing_findings = [f for f in (doc_analysis.pma.findings or []) if not f.is_positive]
            if missing_findings:
                detail += f"{len(missing_findings)} area(s) need clarification in the PMA."
        elif has_pma:
            detail = (
                f"PMA reviewed ({doc_analysis.pma.status}). "
                f"Lease agreement was not provided — maintenance responsibility language "
                f"will need clarification during onboarding."
            )
        elif has_lease:
            detail = (
                f"Lease reviewed ({doc_analysis.lease.status}). "
                f"PMA was not provided — vendor authority, NTE rules, and approval workflows "
                f"will need to be documented during onboarding."
            )
        else:
            detail = (
                "No policy documents were provided for review. Your PMA and lease templates "
                "will be assessed during onboarding to configure your Maintenance Book."
            )

        gaps.append(GapFinding(
            title="Policy Documentation",
            severity=sev,
            severity_color="var(--green)" if is_minor else "var(--amber)",
            severity_bg="var(--green-light)" if is_minor else "var(--amber-light)",
            severity_border="var(--green)" if is_minor else "var(--amber)",
            detail=detail,
            recommendation=(
                "Any unclear or missing policies are clarified during onboarding. Your Advisor "
                "ensures every policy decision is documented in your Maintenance Book before go-live."
            ),
        ))

    # ── Open WO Rate ──
    if wo_metrics.open_wo_rate_pct and wo_metrics.open_wo_rate_pct > 20:
        is_high = wo_metrics.open_wo_rate_pct > 30
        benchmark = VENDOROO_AVG.get(client_info.operational_model, VENDOROO_AVG["va"])
        gaps.append(GapFinding(
            title="Open Work Order Backlog",
            severity="High Priority" if is_high else "Medium Priority",
            **_colors(is_high),
            detail=(
                f"Open work order rate of {wo_metrics.open_wo_rate_pct}% — "
                f"{wo_metrics.open_wo_count or 'unknown'} open across "
                f"{client_info.door_count} doors. Vendoroo clients average "
                f"{benchmark['open_wo_rate_pct']}%."
            ),
            recommendation=(
                "AI follow-up sequences and automated vendor check-ins close the loop on "
                "stalled work orders. Your Advisor configures escalation rules so no work order "
                "goes stale without action."
            ),
        ))

    # ── Property Concentration ──
    if client_info.property_count and client_info.property_count > 0:
        dpp = client_info.door_count / client_info.property_count
        if dpp > 30:
            is_high = dpp > 100
            gaps.append(GapFinding(
                title="Property Concentration Risk",
                severity="High Priority" if is_high else "Medium Priority",
                severity_color="var(--red)" if is_high else "var(--amber)",
                severity_bg="var(--red-light)" if is_high else "var(--amber-light)",
                severity_border="var(--red)" if is_high else "var(--amber)",
                detail=(
                    f"{round(dpp)} doors per property on average "
                    f"({client_info.door_count} doors across "
                    f"{client_info.property_count} "
                    f"{'property' if client_info.property_count == 1 else 'properties'}). "
                    f"A single building event — water intrusion, HVAC failure, pest — "
                    f"can trigger concurrent requests across many units. Standard vendor "
                    f"agreements rarely account for this volume at one location."
                ),
                recommendation=(
                    "Your Advisor reviews your vendor agreements for capacity clauses and "
                    "configures triage rules that handle concurrent building-wide events — "
                    "batching related requests, routing to high-capacity vendors, and "
                    "escalating automatically when volume spikes from a single property."
                ),
            ))

    return gaps  # No artificial cap — count reflects the data


# ── Impact Projections ───────────────────────────────────

def generate_impact_projections(
    wo_metrics: WorkOrderMetrics,
    client_info: ClientInfo,
    recommended_tier: str = "direct",
) -> list[ImpactProjection]:
    """Generate the projected impact table rows."""
    model = client_info.operational_model
    benchmarks = VENDOROO_AVG.get(model, VENDOROO_AVG["va"])
    top = TOP_PERFORMERS.get(model, TOP_PERFORMERS["va"])

    projections = []

    def _format_improvement(current, projected):
        if current is None or projected is None:
            return None
        if projected >= current:
            return "Already meeting benchmark"
        pct = round((1 - projected / current) * 100)
        return f"{pct}%"

    def _project_completion_time(current_days):
        if current_days is None:
            return None, None
        benchmark_days = benchmarks.get("avg_completion_days", 3.0)
        reduced = current_days * 0.625
        projected = max(benchmark_days, reduced)  # don't project below Vendoroo benchmark
        projected = min(current_days, projected)  # never project worse than current
        return round(projected, 1), _format_improvement(current_days, projected)

    def _project_open_wo_rate(current_pct):
        if current_pct is None:
            return None, None
        projected = min(current_pct, max(5.0, current_pct * 0.6))
        return round(projected, 1), _format_improvement(current_pct, projected)

    def _project_after_hours():
        projected = "24/7 AI Triage*"
        if recommended_tier == "command":
            note = "Daytime emergency handling included: add RescueRoo for full 24/7 emergency dispatch."
        else:
            note = "Full emergency coverage available with RescueRoo add-on ($1.50/door/mo)."
        return projected, note, "100%"

    # First Response Time
    current_resp = f"{wo_metrics.avg_first_response_hours} hrs" if wo_metrics.avg_first_response_hours else "N/A"
    if wo_metrics.avg_first_response_hours:
        improvement_pct = round((1 - (benchmarks["avg_first_response_minutes"] / 60) / wo_metrics.avg_first_response_hours) * 100)
        improvement_pct = max(0, improvement_pct)
    else:
        improvement_pct = None
    projections.append(ImpactProjection(
        metric="First Response Time",
        current_value=current_resp,
        projected_value="< 10 min",
        benchmark_range="< 10 min avg.",
        improvement=f"{improvement_pct}%" if improvement_pct else None,
    ))

    # Work Order Completion (bounded projection)
    current_comp = f"{wo_metrics.median_completion_days} days" if wo_metrics.median_completion_days else "N/A"
    projected_days, comp_improvement = _project_completion_time(wo_metrics.median_completion_days)
    proj_comp = f"{projected_days} days" if projected_days is not None else "N/A"
    projections.append(ImpactProjection(
        metric="Work Order Completion",
        current_value=current_comp,
        projected_value=proj_comp,
        benchmark_range=f"{benchmarks['completion_decrease_pct']} - {top['completion_decrease_pct']}% decrease",
        improvement=comp_improvement,
    ))

    # Open WO Rate (bounded projection)
    projected_open, open_improvement = _project_open_wo_rate(wo_metrics.open_wo_rate_pct)
    projections.append(ImpactProjection(
        metric="Open WO Rate",
        current_value=f"{wo_metrics.open_wo_rate_pct}%",
        projected_value=f"{projected_open}%" if projected_open is not None else "N/A",
        benchmark_range=f"{top['open_wo_rate_pct']} - {benchmarks['open_wo_rate_pct']}%",
        improvement=open_improvement,
    ))

    # After Hours Coverage (RescueRoo nuance)
    after_projected, after_note, after_improvement = _project_after_hours()
    if wo_metrics.after_hours_time_available and wo_metrics.after_hours_pct:
        ah_current = f"{wo_metrics.after_hours_pct}% after-hours volume"
        ah_is_bad = False
    elif wo_metrics.after_hours_time_available:
        ah_current = "No after-hours data available"
        ah_is_bad = True
    else:
        ah_current = "No after-hours coverage detected"
        ah_is_bad = True
    projections.append(ImpactProjection(
        metric="After-Hours Availability",
        current_value=ah_current,
        current_is_bad=ah_is_bad,
        projected_value=after_projected,
        benchmark_range="AI triage benchmark",
        improvement=after_improvement,
        note=after_note,
    ))

    # Vendor Coverage
    current_trades = wo_metrics.trades_covered_count
    required_trades = wo_metrics.trades_required_count or len(CORE_TRADES)
    current_coverage_pct = round(current_trades / required_trades * 100) if required_trades else 0
    projections.append(ImpactProjection(
        metric="Vendor Coverage",
        current_value=f"{current_trades}/{required_trades} core trades",
        current_is_bad=current_coverage_pct < 80,
        projected_value=f"{required_trades}/{required_trades} core trades" if current_trades < required_trades else f"{current_trades}/{required_trades} core trades",
        benchmark_range="100% of core trades",
        improvement=f"{100 - current_coverage_pct}%" if current_coverage_pct < 100 else "Already meeting benchmark",
    ))

    # Resident Satisfaction (use industry average as baseline — we don't collect this directly)
    _industry_baseline = 72
    projections.append(ImpactProjection(
        metric="Resident Satisfaction",
        current_value=f"Industry avg: {_industry_baseline}%",
        current_is_bad=False,
        projected_value=f"{benchmarks['resident_satisfaction_pct']}%",
        benchmark_range=f"{benchmarks['resident_satisfaction_pct']} - {top['resident_satisfaction_pct']}%+",
        improvement=f"+{benchmarks['resident_satisfaction_pct'] - _industry_baseline}%",
        note="Based on industry average baseline of 72% (NARPM 2024 survey).",
    ))

    return projections


def generate_staffing_projection(
    client_info: ClientInfo,
    portfolio: PortfolioMetrics,
) -> StaffingProjection:
    """Generate staffing and scale projection."""
    model = client_info.operational_model
    benchmarks = STAFFING_BENCHMARKS.get(model, STAFFING_BENCHMARKS["va"])

    scale_doors = client_info.staff_count * benchmarks["vendoroo_benchmark"]
    optimize_staff = max(1, round(client_info.door_count / benchmarks["vendoroo_benchmark"]))
    fte_savings = max(0, client_info.staff_count - optimize_staff)

    # Generate model-specific narratives for Scale / Optimize / Elevate paths
    if model == "pod":
        scale_narrative = (
            f"Your pods can take on more doors without adding a pod member. "
            f"Scale from {client_info.staff_count} pods to managing {scale_doors} doors "
            f"with the same team structure."
        )
        optimize_narrative = (
            f"Consolidate from {client_info.staff_count} pods to {optimize_staff} at current "
            f"door count, remove the coordinator role from each pod and let AI handle "
            f"coordination, or flatten your org entirely by transitioning from pods to "
            f"individual PMs each managing more doors with AI handling all coordination."
        )
        elevate_narrative = (
            "Your pod structure already delivers better quality than solo coordinators; "
            "AI makes that quality consistent 24/7 and frees pod members to focus on "
            "owner relationships."
        )
    elif model == "tech":
        scale_narrative = (
            f"Your {client_info.staff_count} technicians can support {scale_doors}+ doors "
            f"with AI handling triage, scheduling, and coordination."
        )
        optimize_narrative = (
            f"Manage your current {client_info.door_count} doors with "
            f"{optimize_staff} technician{'s' if optimize_staff != 1 else ''}, "
            f"saving {fte_savings} FTE{'s' if fte_savings != 1 else ''} in coordination overhead."
        )
        elevate_narrative = (
            "Elevate technician expertise by removing administrative burden. "
            "AI handles all scheduling, tenant communication, and follow-up so techs "
            "focus on repairs and owner relationships."
        )
    else:  # va (default)
        scale_narrative = (
            f"Your {client_info.staff_count} coordinators can support {scale_doors}+ doors "
            f"with AI handling triage, communication, and vendor dispatch."
        )
        optimize_narrative = (
            f"Manage your current {client_info.door_count} doors with "
            f"{optimize_staff} coordinator{'s' if optimize_staff != 1 else ''}, "
            f"saving {fte_savings} FTE{'s' if fte_savings != 1 else ''} in coordination overhead."
        )
        elevate_narrative = (
            "Elevate service quality with instant response times, 24/7 coverage, "
            "and consistent processes across your entire portfolio."
        )

    return StaffingProjection(
        current_staff=client_info.staff_count,
        current_doors=client_info.door_count,
        doors_per_staff=int(portfolio.doors_per_staff),
        staff_benchmark=benchmarks["current_benchmark"],
        scale_doors=scale_doors,
        optimize_staff=optimize_staff,
        fte_savings=fte_savings,
        scale_narrative=scale_narrative,
        optimize_narrative=optimize_narrative,
        elevate_narrative=elevate_narrative,
    )


# ── Tier Recommendation ─────────────────────────────────

def recommend_tier(goal, category_scores, gaps, client_info=None):
    """Recommend a Vendoroo service tier based on goal, scores, and gaps.

    goal: "scale" | "optimize" | "elevate"
    category_scores: dict of category key -> score (0-100)
    gaps: list of gap name strings
    client_info: dict with door_count, property_count, operational_model
    Returns: "engage" | "direct" | "command"
    """
    if client_info is None:
        client_info = {}

    below_50_count = sum(1 for s in category_scores.values() if s < 50)
    normalized_gaps = {str(g).strip().lower().replace(" ", "_") for g in gaps}

    # Override 1: Everything is bad (5+ of 8 below 50) → start with fundamentals
    if below_50_count >= 5:
        return "engage"

    # Override 2: 50/50 split (exactly half below 50)
    if below_50_count == 4:
        return "direct"

    # Override 3: Only response time + satisfaction gaps
    response_only_gaps = {
        "response_time",
        "response_time_slas",
        "resident_satisfaction",
        "resident_satisfaction_gap",
    }
    if normalized_gaps and normalized_gaps.issubset(response_only_gaps):
        return "engage"

    # Property concentration: high ratio signals multifamily
    doors_per_property = client_info.get("door_count", 0) / max(client_info.get("property_count", 1), 1)
    high_concentration = doors_per_property > 25
    is_tech_model = client_info.get("operational_model", "") == "tech"

    # Override 6: High property concentration + Tech model → Engage
    # Multifamily with onsite techs primarily needs the comms desk, not vendor dispatch
    if high_concentration and is_tech_model and below_50_count <= 2:
        return "engage"

    # Goal-based recommendation with score awareness
    if goal == "elevate":
        if below_50_count >= 3:
            return "direct"
        return "engage"
    elif goal == "scale":
        if below_50_count >= 3 or (
            {"vendor_coverage", "open_wo_rate", "response_time_slas"} & normalized_gaps
        ):
            return "direct"
        return "engage"
    elif goal == "optimize":
        if below_50_count >= 4:
            return "engage"
        if below_50_count >= 2:
            return "direct"
        return "direct"

    return "direct"  # fallback


# ── Projected Score Calculator ───────────────────────────

_GAP_POINT_MAP = {
    "response_time": 6,
    "Response Time SLAs": 6,
    "vendor_coverage": 4,
    "Vendor Coverage": 4,
    "emergency_protocol": 5,
    "Emergency Protocol": 5,
    "nte_governance": 3,
    "NTE Governance": 3,
    "Maintenance Limit (NTE) Governance": 3,
    "after_hours": 5,
    "After Hours Operations": 5,
    "policy_documentation": 2,
    "Policy Documentation": 2,
    "Open Work Order Backlog": 4,
}


def calculate_projected_score(current_score, gaps):
    """Calculate projected readiness score after addressing gaps.

    Improvement is proportional — diminishing returns as score increases.
    A prospect at 40 has more room to improve than one at 70.
    Max improvement capped at 25 points. Max projected score capped at 90.
    """
    raw_improvement = sum(_GAP_POINT_MAP.get(gap, 0) for gap in gaps)

    # Diminishing returns: the higher you already are, the less each gap is worth
    # At score 40: you get 100% of the improvement
    # At score 60: you get ~80%
    # At score 80: you get ~50%
    headroom_factor = max(0.3, (100 - current_score) / 60)
    adjusted_improvement = round(raw_improvement * headroom_factor)

    # Hard caps
    adjusted_improvement = min(25, adjusted_improvement)  # Max 25-point jump
    projected = current_score + adjusted_improvement
    projected = min(90, projected)  # Never above 90

    return max(current_score, projected)


# ── Cost Estimates ───────────────────────────────────────

_TIER_PRICES = {
    "engage": 3.00,
    "direct": 6.00,
    "command": 8.50,
}

_NEXT_TIER = {
    "engage": "direct",
    "direct": "command",
    "command": "command",
}

_RESCUEROO_PRICE = 1.50
_MONTHLY_MINIMUM = 400


def calculate_cost_estimates(door_count, recommended_tier):
    """Calculate monthly cost estimates for recommended and next tier.

    door_count: int, number of doors in the portfolio
    recommended_tier: "engage" | "direct" | "command"
    Returns: dict with recommended_cost, recommended_tier_name, next_tier_cost,
             next_tier_name, rescueroo_cost
    """
    rec_price = _TIER_PRICES.get(recommended_tier, _TIER_PRICES["direct"])
    next_tier = _NEXT_TIER.get(recommended_tier, "command")
    next_price = _TIER_PRICES[next_tier]

    recommended_cost = max(_MONTHLY_MINIMUM, door_count * rec_price)
    next_tier_cost = max(_MONTHLY_MINIMUM, door_count * next_price)
    rescueroo_cost = max(_MONTHLY_MINIMUM, door_count * _RESCUEROO_PRICE)

    return {
        "recommended_cost": recommended_cost,
        "recommended_tier_name": recommended_tier,
        "next_tier_cost": next_tier_cost,
        "next_tier_name": next_tier,
        "rescueroo_cost": rescueroo_cost,
    }


# ── Goal Card Data ───────────────────────────────────────

from math import ceil


def get_goal_card_data(operational_model, staff_count, door_count, goal):
    """Generate goal card display data for scale, optimize, and elevate paths.

    operational_model: "va" | "tech" | "pod"
    staff_count: int, current maintenance staff count
    door_count: int, total doors managed
    goal: "scale" | "optimize" | "elevate" (the user's selected goal)
    Returns: dict with scale_data, optimize_data, elevate_data, each containing
             stat_value, stat_label, description, best_tier
    """
    benchmarks = STAFFING_BENCHMARKS.get(operational_model, STAFFING_BENCHMARKS["va"])

    if operational_model == "va":
        va_benchmark = benchmarks.get("vendoroo_benchmark", 350)
        scale_doors = staff_count * va_benchmark
        optimize_reduction = staff_count - ceil(door_count / va_benchmark)

        scale_data = {
            "stat_value": f"{scale_doors}+",
            "stat_label": "doors with current staff",
            "description": (
                f"Your {staff_count} coordinators can support {scale_doors}+ doors "
                f"with AI handling triage, communication, and vendor dispatch."
            ),
            "best_tier": "direct",
        }
        optimize_data = {
            "stat_value": f"{max(0, optimize_reduction)}",
            "stat_label": "fewer FTEs needed",
            "description": (
                f"Manage your current {door_count} doors with "
                f"{max(1, ceil(door_count / va_benchmark))} coordinators, "
                f"saving {max(0, optimize_reduction)} FTEs in coordination overhead."
            ),
            "best_tier": "command",
        }
        elevate_data = {
            "stat_value": "24/7",
            "stat_label": "coverage with instant response",
            "description": (
                "Elevate service quality with instant response times, 24/7 coverage, "
                "and consistent processes across your entire portfolio."
            ),
            "best_tier": "engage",
        }

    elif operational_model == "tech":
        tech_benchmark = benchmarks.get("vendoroo_benchmark", 300)
        scale_doors = staff_count * tech_benchmark
        optimize_reduction = staff_count - ceil(door_count / tech_benchmark)

        scale_data = {
            "stat_value": f"{scale_doors}+",
            "stat_label": "doors with current technicians",
            "description": (
                f"Your {staff_count} technicians can support {scale_doors}+ doors "
                f"with AI handling triage, scheduling, and coordination."
            ),
            "best_tier": "direct",
        }
        optimize_data = {
            "stat_value": f"{max(0, optimize_reduction)}",
            "stat_label": "fewer FTEs needed",
            "description": (
                f"Manage your current {door_count} doors with "
                f"{max(1, ceil(door_count / tech_benchmark))} technicians, "
                f"saving {max(0, optimize_reduction)} FTEs in coordination overhead."
            ),
            "best_tier": "command",
        }
        elevate_data = {
            "stat_value": "24/7",
            "stat_label": "coverage with instant response",
            "description": (
                "Elevate technician expertise by removing administrative burden. "
                "AI handles all scheduling, tenant communication, and follow-up."
            ),
            "best_tier": "engage",
        }

    elif operational_model == "pod":
        pod_benchmark = benchmarks.get("vendoroo_benchmark", 550)
        scale_doors = staff_count * pod_benchmark
        optimize_pods = ceil(door_count / pod_benchmark)
        pods_saved = max(0, staff_count - optimize_pods)

        scale_data = {
            "stat_value": f"{scale_doors}+",
            "stat_label": "doors with current pods",
            "description": (
                f"Your {staff_count} pods can take on more doors without adding "
                f"a pod member, scaling to {scale_doors}+ doors with the same "
                f"team structure."
            ),
            "best_tier": "direct",
        }
        optimize_data = {
            "stat_value": f"{pods_saved}",
            "stat_label": "fewer pods needed",
            "description": (
                f"Consolidate from {staff_count} pods to {optimize_pods}, "
                f"flatten pods by removing the coordinator role and letting AI "
                f"handle coordination, or transition to individual PMs each "
                f"managing more doors."
            ),
            "best_tier": "command",
        }
        elevate_data = {
            "stat_value": "24/7",
            "stat_label": "consistent quality coverage",
            "description": (
                "Your pod structure already delivers better quality than solo "
                "coordinators; AI makes that quality consistent 24/7 and frees "
                "pod members to focus on owner relationships."
            ),
            "best_tier": "engage",
        }

    else:
        # Fallback to VA model
        return get_goal_card_data("va", staff_count, door_count, goal)

    return {
        "scale_data": scale_data,
        "optimize_data": optimize_data,
        "elevate_data": elevate_data,
    }
