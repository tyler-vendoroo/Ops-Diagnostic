"""Report data builder — pure deterministic assembly, no AI calls."""
from datetime import date

from app.models.analysis import (
    DocumentAnalysis,
    DocumentFinding,
    DocumentSection,
    PortfolioMetrics,
    WorkOrderMetrics,
)
from app.models.input_data import ClientInfo
from app.models.report_data import (
    BenchmarkRow,
    GapTierRow,
    OutcomeStat,
    PathCard,
    PhaseCard,
    ReportData,
    TierCard,
)
from app.config.benchmarks import (
    STAFFING_BENCHMARKS,
    TOP_PERFORMERS,
    VENDOROO_AVG,
)
from app.analysis.scoring_engine import (
    calculate_cost_estimates,
    calculate_projected_score,
    generate_impact_projections,
    generate_staffing_projection,
    get_goal_card_data,
)


# ── Gap-to-tier mapping ──────────────────────────────────────────────────────

_GAP_TIER_MAP = {
    "Emergency Protocol":     {"engage": "dash", "direct": "check", "command": "check", "note": ""},
    "Vendor Coverage":        {"engage": "dash", "direct": "check", "command": "check", "note": ""},
    "Response Time SLAs":     {"engage": "check", "direct": "check", "command": "check", "note": ""},
    "NTE Governance":                     {"engage": "dash", "direct": "check", "command": "check", "note": ""},
    "Maintenance Limit (NTE) Governance": {"engage": "dash", "direct": "check", "command": "check", "note": ""},
    "After Hours Operations": {"engage": "check", "direct": "check", "command": "check", "note": "+RescueRoo"},
    "Policy Documentation":   {"engage": "dash", "direct": "check", "command": "check", "note": ""},
}

# ── AAA value by tier ────────────────────────────────────────────────────────

_AAA_VALUE_MAP = {
    "engage": "Complimentary",
    "direct": "Complimentary",
    "command": "Complimentary",
}

# ── Tier price map (mirrors scoring_engine) ──────────────────────────────────

_TIER_PRICES = {"engage": 3.00, "direct": 6.00, "command": 8.50}


def build_report_data(
    client_info: ClientInfo,
    category_scores: list,
    overall_score: int,
    tier: str,
    key_findings: list,
    gaps: list,
    wo_metrics: WorkOrderMetrics,
    portfolio_metrics: PortfolioMetrics,
    doc_analysis: DocumentAnalysis,
) -> ReportData:
    """Assemble a fully-populated ReportData from analysis outputs.

    Pure deterministic computation — no AI calls.
    """

    # ── Computed constants ────────────────────────────────────────────────────

    model = client_info.operational_model
    benchmarks = VENDOROO_AVG.get(model, VENDOROO_AVG["va"])
    top = TOP_PERFORMERS.get(model, TOP_PERFORMERS["va"])
    staff_benchmarks = STAFFING_BENCHMARKS.get(model, STAFFING_BENCHMARKS["va"])

    report_date = date.today().strftime("%B %Y")
    tier_display = tier.capitalize()

    STAFF_LABEL_MAP = {"va": "coordinators", "tech": "technicians", "pod": "pods"}
    staff_label = STAFF_LABEL_MAP.get(model, "coordinators")
    staff_label_singular = staff_label.rstrip("s")

    projected_score = calculate_projected_score(overall_score, [g.title for g in gaps])
    projected_score_dashoffset = ReportData.calculate_dashoffset(projected_score)
    current_score_dashoffset = ReportData.calculate_dashoffset(overall_score)

    if overall_score >= 70:
        current_score_color = "#22C55E"
    elif overall_score >= 50:
        current_score_color = "#F59E0B"
    else:
        current_score_color = "#EF4444"

    impact_rows = generate_impact_projections(wo_metrics, client_info, tier)
    staffing = generate_staffing_projection(client_info, portfolio_metrics)
    costs = calculate_cost_estimates(client_info.door_count, tier)

    # ── Executive summary ─────────────────────────────────────────────────────

    executive_summary = (
        f"{client_info.company_name} scored {overall_score}/100 on the Vendoroo Operations "
        f"Readiness Diagnostic. Based on {client_info.door_count} doors across "
        f"{client_info.property_count} properties, the analysis identified "
        f"{len(gaps)} operational gap(s). Recommended tier: {tier_display}."
    )
    score_tier_label = (
        "Ready" if overall_score >= 70 else "Needs Work" if overall_score >= 50 else "Not Ready"
    )
    score_description = (
        f"Your score of {overall_score} places you in the {score_tier_label} tier. "
        f"Addressing the identified gaps could raise your score to {projected_score}."
    )

    # ── Benchmark rows ────────────────────────────────────────────────────────

    # 1. First Response Time
    if wo_metrics.avg_first_response_hours is not None:
        resp_val = f"{wo_metrics.avg_first_response_hours} hrs"
        resp_css = "val-bad" if wo_metrics.avg_first_response_hours > 1 else "val-good"
    else:
        resp_val = "N/A"
        resp_css = "val-neutral"

    # 2. WO Completion
    if wo_metrics.median_completion_days is not None:
        comp_val = f"{wo_metrics.median_completion_days} days"
        comp_css = (
            "val-bad"
            if wo_metrics.median_completion_days > benchmarks["avg_completion_days"]
            else "val-good"
        )
    else:
        comp_val = "N/A"
        comp_css = "val-neutral"

    # 3. Open WO Rate
    open_rate_val = f"{wo_metrics.open_wo_rate_pct}%"
    open_rate_css = (
        "val-bad"
        if (wo_metrics.open_wo_rate_pct or 0) > benchmarks["open_wo_rate_pct"]
        else "val-good"
    )

    # 4. Vendor Coverage
    vendor_cov_val = f"{wo_metrics.trades_covered_count}/{wo_metrics.trades_required_count} trades"
    vendor_cov_css = (
        "val-bad"
        if wo_metrics.trades_covered_count < wo_metrics.trades_required_count
        else "val-good"
    )

    # 5. After Hours
    after_val = f"{wo_metrics.after_hours_pct}%"
    after_css = "val-bad" if (wo_metrics.after_hours_pct or 0) < 20 else "val-good"

    benchmark_rows = [
        BenchmarkRow(
            metric="First Response Time",
            current_value=resp_val,
            current_css=resp_css,
            vendoroo_avg=f"< {benchmarks['avg_first_response_minutes']} min",
            top_performers=f"< {top['avg_first_response_minutes']} min",
        ),
        BenchmarkRow(
            metric="WO Completion",
            current_value=comp_val,
            current_css=comp_css,
            vendoroo_avg=f"{benchmarks['avg_completion_days']} days",
            top_performers=f"{top['avg_completion_days']} days",
        ),
        BenchmarkRow(
            metric="Open Work Order Rate",
            current_value=open_rate_val,
            current_css=open_rate_css,
            vendoroo_avg=f"{benchmarks['open_wo_rate_pct']}%",
            top_performers=f"{top['open_wo_rate_pct']}%",
        ),
        BenchmarkRow(
            metric="Vendor Coverage",
            current_value=vendor_cov_val,
            current_css=vendor_cov_css,
            vendoroo_avg="100% required trades",
            top_performers="100% required trades",
        ),
        BenchmarkRow(
            metric="After Hours Operations",
            current_value=after_val,
            current_css=after_css,
            vendoroo_avg="24/7 AI triage",
            top_performers="24/7 + dispatch",
        ),
    ]

    # ── Document sections ─────────────────────────────────────────────────────

    # 1. Emergency Protocols — use doc_analysis.emergency_protocols directly
    emergency_section = doc_analysis.emergency_protocols

    # 2. NTE Thresholds — build from nte_threshold and nte_is_tiered
    if doc_analysis.nte_threshold:
        nte_status = "Received & Reviewed"
        nte_tier = "ready"
        nte_findings = [
            DocumentFinding(
                text=f"NTE threshold set at {doc_analysis.nte_threshold}"
                + (" (tiered by trade/priority)" if doc_analysis.nte_is_tiered else ""),
                is_positive=True,
            )
        ]
    else:
        nte_status = "Not Documented"
        nte_tier = "not-ready"
        nte_findings = [
            DocumentFinding(
                text="No NTE threshold defined",
                is_positive=False,
                is_missing=True,
            )
        ]
    nte_section = DocumentSection(
        title="NTE Thresholds",
        status=nte_status,
        status_tier=nte_tier,
        findings=nte_findings,
    )

    # 3. SLA Targets — build from has_defined_slas
    if doc_analysis.has_defined_slas:
        sla_status = "Received & Reviewed"
        sla_tier = "ready"
        sla_findings = [
            DocumentFinding(
                text="SLA targets are defined",
                is_positive=True,
            )
        ]
    else:
        sla_status = "Not Documented"
        sla_tier = "not-ready"
        sla_findings = [
            DocumentFinding(
                text="No SLA targets defined",
                is_positive=False,
                is_missing=True,
            )
        ]
    sla_section = DocumentSection(
        title="SLA Targets",
        status=sla_status,
        status_tier=sla_tier,
        findings=sla_findings,
    )

    document_sections = [emergency_section, nte_section, sla_section]

    # ── Path cards ────────────────────────────────────────────────────────────

    goal = client_info.primary_goal or "scale"
    goal_card_data = get_goal_card_data(model, client_info.staff_count, client_info.door_count, goal)

    scale_d = goal_card_data["scale_data"]
    optimize_d = goal_card_data["optimize_data"]
    elevate_d = goal_card_data["elevate_data"]

    path_cards = [
        PathCard(
            path_number=1,
            name="Scale",
            description=scale_d["description"],
            stat_value=scale_d["stat_value"],
            stat_label=scale_d["stat_label"],
            best_tier=scale_d["best_tier"].capitalize(),
            is_selected=(goal == "scale"),
        ),
        PathCard(
            path_number=2,
            name="Optimize",
            description=optimize_d["description"],
            stat_value=optimize_d["stat_value"],
            stat_label=optimize_d["stat_label"],
            best_tier=optimize_d["best_tier"].capitalize(),
            is_selected=(goal == "optimize"),
        ),
        PathCard(
            path_number=3,
            name="Elevate",
            description=elevate_d["description"],
            stat_value=elevate_d["stat_value"],
            stat_label=elevate_d["stat_label"],
            best_tier=elevate_d["best_tier"].capitalize(),
            is_selected=(goal == "elevate"),
        ),
    ]

    # ── Current state labels ──────────────────────────────────────────────────

    current_state_label = (
        f"{client_info.staff_count} {staff_label.capitalize()}"
    )
    current_state_detail = (
        f"{client_info.door_count} doors "
        f"({int(portfolio_metrics.doors_per_staff or 0)} doors/{staff_label_singular}) "
        f"| Benchmark: {staff_benchmarks['current_benchmark']} doors/{staff_label_singular}"
    )

    # ── Tier cards ────────────────────────────────────────────────────────────

    _is_event = bool(getattr(client_info, "event_source", None))
    _price_unit = "Contact your advisor" if _is_event else "/ unit / month"

    tier_cards = [
        TierCard(
            name="Engage",
            subtitle="AI-Powered Communication Desk",
            price="—" if _is_event else "$3",
            price_unit=_price_unit,
            roos="Dedicated AI team",
            features=[
                "AI-powered resident communication",
                "Work order intake & triage",
                "Vendor dispatch coordination",
                "24/7 AI response (business hours human oversight)",
            ],
            new_features=[],
            is_recommended=(tier == "engage"),
        ),
        TierCard(
            name="Direct",
            subtitle="Full Maintenance Operations Layer",
            price="—" if _is_event else "$6",
            price_unit=_price_unit,
            roos="Expanded AI team",
            features=[
                "Everything in Engage",
                "NTE governance & vendor authorization",
                "After-hours triage & escalation",
                "Vendor performance tracking",
            ],
            new_features=[
                "Emergency protocol management",
                "Owner approval workflows",
            ],
            is_recommended=(tier == "direct"),
        ),
        TierCard(
            name="Command",
            subtitle="Strategic Operations Command Center",
            price="—" if _is_event else "$8.50",
            price_unit=_price_unit,
            roos="Full command team",
            features=[
                "Everything in Direct",
                "Full portfolio oversight",
                "Predictive maintenance coordination",
                "Owner communication & reporting",
            ],
            new_features=[
                "Custom SLA configuration",
                "Dedicated success manager",
            ],
            is_recommended=(tier == "command"),
        ),
    ]

    # ── Gap tier rows — only include gaps the prospect actually has ────────────

    actual_gap_titles = {
        g.title if hasattr(g, "title") else g.get("title", "")
        for g in gaps
    }
    gap_tier_rows = [
        GapTierRow(
            gap_name=gap_name,
            engage=mapping["engage"],
            direct=mapping["direct"],
            command=mapping["command"],
            command_note=mapping["note"],
        )
        for gap_name, mapping in _GAP_TIER_MAP.items()
        if gap_name in actual_gap_titles
    ]

    # ── Outcome stats ─────────────────────────────────────────────────────────

    tier_price = _TIER_PRICES.get(tier, 6.00)
    outcome_stats = [
        OutcomeStat(
            value=f"${costs['recommended_cost']:,.0f}",
            label=f"Estimated monthly ({client_info.door_count} doors × ${tier_price:.2f})",
        ),
        OutcomeStat(
            value=f"${costs['recommended_cost'] * 12:,.0f}",
            label="Estimated annual investment",
        ),
        OutcomeStat(
            value=str(projected_score),
            label="Projected readiness score",
        ),
    ]

    # ── Outcome title / description ───────────────────────────────────────────

    outcome_title = (
        f"Based on your analysis: {tier_display} is the recommended starting point"
    )
    outcome_description = (
        f"Your portfolio of {client_info.door_count} doors with a primary goal of "
        f"{client_info.primary_goal_display or goal.capitalize()} aligns best with the "
        f"{tier_display} tier. Addressing {len(gaps)} identified gap(s) is expected to "
        f"raise your readiness score from {overall_score} to {projected_score}."
    )

    # ── Phase cards ───────────────────────────────────────────────────────────

    phase_cards = [
        PhaseCard(
            phase_number=1,
            name="Learning",
            timeframe="Days 0 to 30",
            description=(
                "Your AI teammate learns your portfolio, vendors, and workflows. "
                "We configure routing rules, NTE thresholds, and escalation paths."
            ),
            milestone="First 50 work orders handled autonomously",
            is_current=True,
        ),
        PhaseCard(
            phase_number=2,
            name="Adoption",
            timeframe="Days 31 to 90",
            description=(
                "Your team shifts from doing to overseeing. Response times drop, "
                "vendor dispatch accelerates, and resident satisfaction climbs."
            ),
            milestone="80%+ of routine WOs resolved without coordinator touch",
            is_current=False,
        ),
        PhaseCard(
            phase_number=3,
            name="Optimization",
            timeframe="Day 90+",
            description=(
                "Continuous improvement through data. Monthly reviews identify "
                "new automation opportunities and portfolio expansion potential."
            ),
            milestone=f"Portfolio ready to scale to {staffing.scale_doors}+ doors",
            is_current=False,
        ),
    ]

    # ── AAA value ─────────────────────────────────────────────────────────────

    aaa_value_amount = _AAA_VALUE_MAP.get(tier, "$2,500")

    # ── Completed items ───────────────────────────────────────────────────────

    completed_items = [
        "Operations readiness assessment completed",
        f"Scored across {len(category_scores)} operational categories",
        f"{len(gaps)} gap(s) identified with remediation recommendations",
        f"Tier recommendation: {tier_display} based on {goal} goal",
        f"Projected score improvement: {overall_score} → {projected_score}",
    ]

    # ── Staff benchmark (key: current_benchmark) ──────────────────────────────

    staff_benchmark_val = staff_benchmarks["current_benchmark"]

    # ── Assemble ReportData ───────────────────────────────────────────────────

    return ReportData(
        # Cover
        company_name=client_info.company_name,
        door_count=client_info.door_count,
        property_count=client_info.property_count,
        pms_platform=client_info.pms_platform,
        operational_model_display=(
            client_info.operational_model_display or client_info.operational_model
        ),
        overall_score=overall_score,
        score_ring_dashoffset=current_score_dashoffset,
        current_score_color=current_score_color,
        projected_score=projected_score,
        projected_score_dashoffset=projected_score_dashoffset,
        monthly_work_orders=str(int(wo_metrics.monthly_avg_work_orders or 0)),
        avg_response_time=(
            f"{wo_metrics.avg_first_response_hours} hrs"
            if wo_metrics.avg_first_response_hours is not None
            else "N/A"
        ),
        open_wo_rate=f"{wo_metrics.open_wo_rate_pct}%",
        vendor_count=f"{wo_metrics.unique_vendors} vendors",
        report_date=report_date,
        # Summary
        executive_summary=executive_summary,
        score_description=score_description,
        category_scores=category_scores,
        recommended_tier=tier,
        recommended_tier_display=tier_display,
        primary_goal=client_info.primary_goal or "scale",
        primary_goal_display=client_info.primary_goal_display or "Scale",
        goal_description=client_info.goal_description or "Grow portfolio without adding headcount",
        staff_count=client_info.staff_count,
        doors_per_staff=int(portfolio_metrics.doors_per_staff or 0),
        # Operations
        benchmark_rows=benchmark_rows,
        benchmark_footnote=(
            "Estimated from survey data — upload work order history for full analysis."
        ),
        # Documents
        document_sections=document_sections,
        # Gaps
        key_findings=key_findings,
        gaps=gaps,
        # Impact
        impact_intro=(
            "Based on your survey responses, here is your projected operational impact "
            "with Vendoroo."
        ),
        impact_rows=impact_rows,
        staffing=staffing,
        wo_metrics=wo_metrics,
        # Path
        current_state_label=current_state_label,
        current_state_detail=current_state_detail,
        path_cards=path_cards,
        paths_footnote=(
            "Projections based on Vendoroo client benchmarks. "
            "Actual results vary by portfolio composition."
        ),
        # Tiers
        tier_cards=tier_cards,
        gap_tier_rows=gap_tier_rows,
        outcome_title=outcome_title,
        outcome_description=outcome_description,
        outcome_stats=outcome_stats,
        tier_footnote=(
            "$400/month minimum applies. "
            "RescueRoo add-on: $1.50/door/month for 24/7 emergency dispatch."
        ),
        # AI adoption
        completed_items=completed_items,
        phase_cards=phase_cards,
        aaa_value_amount=aaa_value_amount,
        # Staff
        staff_label=staff_label,
        staff_benchmark=staff_benchmark_val,
        # Footer
        footer_text=f"Vendoroo Operations Analysis \u2022 {client_info.company_name} \u2022 {report_date}",
    )
