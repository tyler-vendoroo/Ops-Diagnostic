"""DiagnosticService: orchestrates the quick diagnostic pipeline."""

import io
import uuid
import logging
import asyncio
import functools
from dataclasses import dataclass, field

from app.models.survey import SurveyResponse
from app.models.input_data import ClientInfo, Vendor
from app.models.analysis import CategoryScore, WorkOrderMetrics
from app.models.lead import LeadCapture
from app.services.survey_adapter import SurveyAdapter
from app.services.lead_service import LeadService
from app.services.email_service import EmailService
from app.analysis.scoring_engine import (
    calculate_all_scores,
    calculate_overall_score,
    calculate_projected_score,
    calculate_cost_estimates,
    get_goal_card_data,
    generate_key_findings,
    generate_gaps,
    recommend_tier,
    generate_impact_projections,
    generate_staffing_projection,
)
from app.db.database import AsyncSessionLocal
from app.db import models as db_models
from sqlalchemy import select
from app.config import CORE_TRADES
from app.config.benchmarks import STAFF_COST_BENCHMARKS

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticResult:
    """Output of a completed quick diagnostic run."""
    diagnostic_id: str
    scores: dict                    # {category_key: score_int}
    overall_score: float
    tier: str                       # "engage" | "direct" | "command"
    key_findings: list              # list of KeyFinding dicts
    gaps: list                      # list of GapFinding dicts
    pdf_bytes: bytes | None = None
    status: str = "complete"
    summary: dict | None = None


class DiagnosticService:
    """Orchestrates quick and full diagnostic flows."""

    def __init__(self):
        self._adapter = SurveyAdapter()
        self._lead_service = LeadService()
        self._email_service = EmailService()

    async def run_quick_diagnostic(
        self,
        survey: SurveyResponse,
        client_info: ClientInfo,
        lead: LeadCapture | None = None,
    ) -> DiagnosticResult:
        """Run the full quick diagnostic pipeline.

        Steps:
        1. Capture lead in DB (if provided)
        2. Convert survey answers → analysis metrics
        3. Score all 8 categories
        4. Generate findings, gaps, tier
        5. Build ReportData + attempt PDF generation
        6. Persist result in DB
        7. Send result and sales notification emails
        8. Return DiagnosticResult
        """
        diagnostic_id = str(uuid.uuid4())

        # ── Step 1: Lead capture ─────────────────────────────────────────────
        lead_id: str | None = None
        if lead is not None:
            try:
                lead_id = await self._lead_service.create_lead(lead)
                await self._lead_service.update_status(lead_id, "diagnostic_started")
            except Exception as exc:
                logger.error("Lead capture failed for diagnostic %s: %s", diagnostic_id, exc)

        # ── Step 2: Survey → Metrics ─────────────────────────────────────────
        wo_metrics, vendor_metrics, portfolio_metrics, doc_analysis = (
            self._adapter.adapt(survey, client_info)
        )

        # ── Step 3: Score ────────────────────────────────────────────────────
        category_scores: list[CategoryScore] = calculate_all_scores(
            wo_metrics,
            vendor_metrics,
            portfolio_metrics,
            doc_analysis,
            client_info,
        )
        overall_score: int = calculate_overall_score(category_scores)
        scores_dict = {cat.key: cat.score for cat in category_scores}

        # ── Step 4: Findings, Gaps, Tier ─────────────────────────────────────
        key_findings = generate_key_findings(
            wo_metrics,
            vendor_metrics,
            portfolio_metrics,
            doc_analysis,
            client_info,
        )

        gaps = generate_gaps(
            category_scores,
            wo_metrics,
            vendor_metrics,
            doc_analysis,
            client_info,
        )

        # Float gaps that match the user's stated pain points to the top
        _PAIN_TO_GAP = {
            "vendor_reliability": "Vendor Coverage",
            "response_times": "Response Time SLAs",
            "cost_control": "NTE Governance",
            "compliance_documentation": "Policy Documentation",
            "after_hours_coverage": "After Hours Operations",
        }
        _pain_gap_titles = {_PAIN_TO_GAP[p] for p in (survey.pain_points or []) if p in _PAIN_TO_GAP}
        if _pain_gap_titles:
            gaps = sorted(gaps, key=lambda g: (0 if g.title in _pain_gap_titles else 1))

        gap_titles = [g.title for g in gaps]
        tier = recommend_tier(
            goal=client_info.primary_goal or "scale",
            category_scores=scores_dict,
            gaps=gap_titles,
            client_info={
                "door_count": client_info.door_count,
                "property_count": client_info.property_count,
                "operational_model": client_info.operational_model,
            },
        )

        # ── Step 4b: Build quick-specific insight summary ────────────────────
        # Quick diagnostic only shows categories we can actually score from survey
        # data. No projected score, no tier, no pricing — just real observations.
        summary: dict | None = None
        try:
            from app.config.benchmarks import STAFFING_BENCHMARKS

            _model = client_info.operational_model
            _staff_label_s = {"va": "coordinator", "tech": "technician", "pod": "pod"}.get(_model, "staff member")
            _staff_label_p = {"va": "coordinators", "tech": "technicians", "pod": "pods"}.get(_model, "staff")
            _doors_per = int(client_info.door_count / max(1, client_info.staff_count))
            _bench = STAFFING_BENCHMARKS.get(_model, STAFFING_BENCHMARKS["va"])
            _benchmark_per = _bench.get("current_benchmark", 175)

            QUICK_SCOREABLE = {
                "vendor_coverage", "response_efficiency",
                "after_hours_readiness", "emergency_protocols", "scalability_potential",
            }
            quick_categories = [
                {
                    "name": cat.name,
                    "key": cat.key,
                    "score": cat.score,
                    "tier": cat.tier,
                    "tier_css": cat.tier_css,
                }
                for cat in category_scores
                if cat.key in QUICK_SCOREABLE
            ]

            insights = []

            # Staffing ratio insight
            if _doors_per > _benchmark_per * 1.2:
                insights.append({
                    "icon": "scale",
                    "title": "Your team is stretched thin",
                    "detail": (
                        f"At {_doors_per} doors per {_staff_label_s}, you're above the industry benchmark "
                        f"of {_benchmark_per}. That means more things slip through the cracks — missed "
                        f"follow-ups, slow responses, reactive instead of proactive. AI coordination absorbs "
                        f"the dispatch workload so your team isn't buried in logistics."
                    ),
                })
            elif _doors_per < _benchmark_per * 0.85:
                insights.append({
                    "icon": "scale",
                    "title": "Capacity to grow without adding headcount",
                    "detail": (
                        f"At {_doors_per} doors per {_staff_label_s}, your team has room to take on more doors. "
                        f"AI coordination lets each {_staff_label_s} manage {_benchmark_per}+ doors without "
                        f"sacrificing response quality — that's growth without a new hire."
                    ),
                })
            else:
                insights.append({
                    "icon": "scale",
                    "title": f"{_doors_per} doors per {_staff_label_s}",
                    "detail": (
                        f"You're right at the industry benchmark of {_benchmark_per}. AI coordination holds "
                        f"this ratio steady as you grow — so adding 100 doors doesn't mean adding another "
                        f"{_staff_label_s}."
                    ),
                })

            # Cost per door insight
            _cost_defaults = STAFF_COST_BENCHMARKS.get(_model, STAFF_COST_BENCHMARKS["va"])
            _annual_cost = client_info.annual_cost_per_staff or _cost_defaults["annual_loaded_cost"]
            _total_staff_cost = _annual_cost * client_info.staff_count
            _cost_per_door_monthly = round(_total_staff_cost / 12 / max(1, client_info.door_count), 2)
            _cost_source = "based on your input" if client_info.annual_cost_per_staff else "industry estimate"
            _vendoroo_start = 3.00
            if _cost_per_door_monthly > _vendoroo_start:
                insights.append({
                    "icon": "dollar",
                    "title": f"${_cost_per_door_monthly:.2f}/door/month in coordination costs",
                    "detail": (
                        f"Your {client_info.staff_count} {_staff_label_p} cost ~${_annual_cost:,.0f}/year each "
                        f"({_cost_source}), which works out to ${_cost_per_door_monthly:.2f} per door per month. "
                        f"Vendoroo starts at $3/door/month — and scales without adding headcount."
                    ),
                })
            else:
                insights.append({
                    "icon": "dollar",
                    "title": f"${_cost_per_door_monthly:.2f}/door/month in coordination costs",
                    "detail": (
                        f"At ${_cost_per_door_monthly:.2f}/door/month ({_cost_source}), your coordination "
                        f"costs are efficient. Vendoroo maintains this efficiency as you grow — "
                        f"adding doors without adding staff."
                    ),
                })

            # Response time insight
            _avg_hrs = wo_metrics.avg_first_response_hours
            if _avg_hrs and _avg_hrs > 4:
                insights.append({
                    "icon": "clock",
                    "title": f"{_avg_hrs}-hour average first response",
                    "detail": (
                        "Vendoroo clients average under 10 minutes from resident request to first acknowledgment. "
                        "Faster first response means fewer follow-up calls, fewer owner complaints, "
                        "and higher resident retention."
                    ),
                })
            elif _avg_hrs and _avg_hrs > 1:
                insights.append({
                    "icon": "clock",
                    "title": f"{_avg_hrs}-hour average first response",
                    "detail": (
                        "Solid, but AI coordination gets this under 10 minutes. Residents get an instant "
                        "acknowledgment with troubleshooting steps — before a coordinator is even involved."
                    ),
                })

            # Trade coverage insight — count only core trades, not specialty
            _core_set = {t.lower() for t in CORE_TRADES}
            _covered_set = {t.lower() for t in (wo_metrics.covered_trades or [])}
            _core_covered = len(_covered_set & _core_set)
            _core_required = len(CORE_TRADES)  # always 8
            if wo_metrics.missing_trades:
                _missing_str = ", ".join(t.title() for t in wo_metrics.missing_trades[:4])
                insights.append({
                    "icon": "vendors",
                    "title": f"No vendor coverage for {_missing_str}",
                    "detail": (
                        f"You have {wo_metrics.unique_vendors} vendors across {_core_covered} of {_core_required} "
                        f"core trades. When a {wo_metrics.missing_trades[0].replace('_', ' ')} issue comes in, "
                        f"your team has to scramble to find someone — that delays resolution and frustrates residents."
                    ),
                })
            elif wo_metrics.unique_vendors and wo_metrics.unique_vendors > 0:
                insights.append({
                    "icon": "vendors",
                    "title": f"{wo_metrics.unique_vendors} vendors across all core trades",
                    "detail": (
                        f"Full coverage across Vendoroo's {_core_required} core trades. AI coordination routes "
                        "each job to the best-fit vendor based on trade, location, availability, and past "
                        "performance — no manual matchmaking."
                    ),
                })

            # After-hours insight
            _after_method = survey.after_hours_method or "none"
            if _after_method in ("voicemail_only", "none"):
                insights.append({
                    "icon": "moon",
                    "title": "After-hours requests wait until morning",
                    "detail": (
                        "Residents with a midnight water heater issue hit voicemail. That's a bad experience "
                        "and a liability risk. Vendoroo's Rooceptionist answers 24/7 — triaging urgency, "
                        "walking residents through troubleshooting, and only escalating true emergencies to you."
                    ),
                })
            elif _after_method == "answering_service":
                insights.append({
                    "icon": "moon",
                    "title": "Your answering service answers — but can't act",
                    "detail": (
                        "They take the message, but they can't determine if it's urgent, troubleshoot with "
                        "the resident, or contact a vendor. AI triage does all three — resolving routine issues "
                        "overnight and escalating real emergencies immediately."
                    ),
                })
            elif _after_method == "on_call_rotation":
                insights.append({
                    "icon": "moon",
                    "title": "On-call rotation for after-hours",
                    "detail": (
                        "Your team takes turns being on call, which works until it doesn't — burnout, missed "
                        "calls, inconsistent triage decisions. AI handles the first line of after-hours response "
                        "so on-call staff only get woken up for true emergencies."
                    ),
                })

            # Emergency protocol insight
            if not doc_analysis.has_emergency_protocols:
                insights.append({
                    "icon": "alert",
                    "title": "No written emergency protocols",
                    "detail": (
                        "Without documented criteria, what counts as an emergency depends on who answers the "
                        "phone. That's how you end up with a plumber dispatched at 2am for a dripping faucet — "
                        "or a burst pipe that waits until Monday."
                    ),
                })

            # NTE insight
            if not doc_analysis.nte_threshold:
                insights.append({
                    "icon": "dollar",
                    "title": "No maintenance limits (NTEs) defined",
                    "detail": (
                        "Without NTEs, you find out what a job costs after it's done. Defined limits let AI "
                        "auto-approve routine work under threshold and flag anything above — so you're only "
                        "reviewing the exceptions, not every invoice."
                    ),
                })
            elif doc_analysis.nte_threshold and not doc_analysis.nte_is_tiered:
                insights.append({
                    "icon": "dollar",
                    "title": f"Flat {doc_analysis.nte_threshold} maintenance limit across all trades",
                    "detail": (
                        "A faucet repair and an HVAC compressor replacement hit the same approval threshold. "
                        "Tiered NTEs by trade and urgency let routine work flow through automatically while "
                        "high-cost jobs get the review they deserve."
                    ),
                })

            # SLA insight
            if not doc_analysis.has_defined_slas:
                insights.append({
                    "icon": "target",
                    "title": "No vendor accountability framework",
                    "detail": (
                        "Without defined expectations, you don't know a vendor is slow until a resident "
                        "complains. AI tracks vendor response and completion times automatically — surfacing "
                        "patterns before they become problems."
                    ),
                })

            summary = {
                "insights": insights[:6],
                "category_scores": quick_categories,
                "company_name": client_info.company_name,
                "door_count": client_info.door_count,
                "staff_count": client_info.staff_count,
                "staff_label": _staff_label_p,
                "primary_goal": client_info.primary_goal or "scale",
                "operational_model": _model,
                "vendor_count": wo_metrics.unique_vendors,
                "trades_covered": _core_covered,
                "trades_required": _core_required,
                "pain_points": list(survey.pain_points or []),
                "pms_platform": client_info.pms_platform or "",
                "current_cost_per_door": _cost_per_door_monthly,
                "annual_cost_per_staff": _annual_cost,
                "cost_source": _cost_source,
            }
        except Exception as exc:
            logger.warning(
                "Summary computation failed for diagnostic %s — continuing without summary. Error: %s",
                diagnostic_id,
                exc,
            )

        # ── Step 5: No PDF on quick path ────────────────────────────────────
        # Quick diagnostic produces a web preview only.
        # PDF is generated only in the full diagnostic path.
        pdf_bytes: bytes | None = None
        html_report: str | None = None

        # ── Step 6: Persist to DB ────────────────────────────────────────────
        key_findings_serialized = [f.model_dump() for f in key_findings]
        gaps_serialized = [g.model_dump() for g in gaps]

        try:
            await self._store_result(
                diagnostic_id=diagnostic_id,
                lead_id=lead_id,
                scores=scores_dict,
                overall_score=overall_score,
                tier=None,  # No tier on quick path — not enough data to recommend pricing
                pdf_bytes=pdf_bytes,
                html_report=html_report,
                key_findings=key_findings_serialized,
                gaps=gaps_serialized,
                summary=summary,
            )
            if lead_id is not None:
                await self._lead_service.update_status(lead_id, "diagnostic_complete")
        except Exception as exc:
            logger.error(
                "DB write failed for diagnostic %s: %s",
                diagnostic_id,
                exc,
            )
            # Non-fatal — still return the result

        # ── Step 7: Send emails (DISABLED) ──────────────────────────────────
        # if lead is not None:
        #     await self._email_service.send_diagnostic_results(
        #         lead_email=lead.email,
        #         lead_name=lead.name,
        #         diagnostic_id=diagnostic_id,
        #         overall_score=float(overall_score),
        #         tier=tier,
        #         key_findings=key_findings_serialized,
        #         pdf_bytes=pdf_bytes,
        #     )
        #     await self._email_service.send_sales_notification(
        #         lead_name=lead.name,
        #         lead_email=lead.email,
        #         lead_company=lead.company,
        #         overall_score=float(overall_score),
        #         tier=tier,
        #     )

        return DiagnosticResult(
            diagnostic_id=diagnostic_id,
            scores=scores_dict,
            overall_score=float(overall_score),
            tier=None,  # No tier recommendation on quick path — not enough data
            key_findings=key_findings_serialized,
            gaps=gaps_serialized,
            pdf_bytes=pdf_bytes,
            status="complete",
            summary=summary,
        )

    async def run_full_diagnostic(
        self,
        diagnostic_id: str,
        work_order_bytes: bytes,
        work_order_filename: str,
        client_info: dict,
        lease_bytes: bytes | None = None,
        pma_bytes: bytes | None = None,
        vendor_directory_bytes: bytes | None = None,
        lead_id: str | None = None,
    ) -> None:
        """Full path: uploaded documents → complete analysis → full PDF. Phase 2 backend."""
        try:
            loop = asyncio.get_event_loop()
            client_info_dict = client_info  # keep raw dict for functions that need it

            # ── Step 0: Mark lead as started ─────────────────────────────────
            if lead_id is not None:
                try:
                    await self._lead_service.update_status(lead_id, "diagnostic_started")
                except Exception as exc:
                    logger.warning("Could not update lead status for %s: %s", lead_id, exc)

            # ── Step 1: Build ClientInfo ─────────────────────────────────────
            ci = ClientInfo(
                company_name=client_info_dict.get("company_name") or "Unknown Company",
                door_count=int(client_info_dict.get("door_count") or 100),
                property_count=int(client_info_dict.get("property_count") or 1),
                pms_platform=client_info_dict.get("pms_platform") or "Other",
                operational_model=client_info_dict.get("operational_model") or "va",
                operational_model_display=client_info_dict.get("operational_model_display") or "",
                staff_count=int(client_info_dict.get("staff_count") or 1),
                primary_goal=client_info_dict.get("primary_goal") or "scale",
                primary_goal_display=client_info_dict.get("primary_goal_display") or "Scale",
                goal_description=client_info_dict.get("goal_description") or "Grow portfolio without adding headcount",
            )

            # ── Step 2: Process work orders ──────────────────────────────────
            from app.parsers.wo_processor import process_work_orders

            wo_file = io.BytesIO(work_order_bytes)
            wo_file.name = work_order_filename

            wo_metrics_dict: dict = await loop.run_in_executor(
                None,
                functools.partial(
                    process_work_orders, wo_file, ci.pms_platform, client_info_dict
                ),
            )

            wo_metrics = WorkOrderMetrics(
                total_work_orders=wo_metrics_dict.get("total_wos", 0),
                maintenance_wos=wo_metrics_dict.get("maintenance_wos", 0),
                recurring_wos=wo_metrics_dict.get("recurring_wos", 0),
                inspection_count=wo_metrics_dict.get("inspection_count", 0),
                cancelled_count=wo_metrics_dict.get("cancelled_count", 0),
                monthly_avg_work_orders=wo_metrics_dict.get("monthly_avg", 0),
                date_range_days=wo_metrics_dict.get("date_range_days", 0),
                date_range_start=wo_metrics_dict.get("date_range_start"),
                date_range_end=wo_metrics_dict.get("date_range_end"),
                date_range_start_short=wo_metrics_dict.get("date_range_start_short"),
                date_range_end_short=wo_metrics_dict.get("date_range_end_short"),
                date_range_year=wo_metrics_dict.get("date_range_year"),
                months_spanned=wo_metrics_dict.get("months_spanned", 0),
                data_reliability=wo_metrics_dict.get("data_reliability"),
                reliability_warning=wo_metrics_dict.get("reliability_warning"),
                wo_per_door_monthly=wo_metrics_dict.get("wo_per_door_monthly"),
                wo_per_door_annual=wo_metrics_dict.get("wo_per_door_annual"),
                volume_assessment=wo_metrics_dict.get("volume_assessment"),
                open_wo_count=wo_metrics_dict.get("open_wo_count", 0),
                open_wo_rate_pct=wo_metrics_dict.get("open_wo_rate_pct", 0),
                median_completion_days=wo_metrics_dict.get("median_completion_days"),
                completed_count=wo_metrics_dict.get("completed_count", 0),
                avg_first_response_hours=wo_metrics_dict.get("avg_first_response_hours"),
                response_time_method=wo_metrics_dict.get("response_time_method"),
                response_time_note=wo_metrics_dict.get("response_time_note"),
                unique_vendors=wo_metrics_dict.get("unique_vendors", 0),
                top_vendor_pct=wo_metrics_dict.get("top_vendor_pct", 0),
                vendor_concentration=wo_metrics_dict.get("vendor_concentration"),
                covered_trades=wo_metrics_dict.get("covered_trades", []),
                missing_trades=wo_metrics_dict.get("missing_trades", []),
                trades_covered_count=wo_metrics_dict.get("trades_covered_count", 0),
                trades_required_count=wo_metrics_dict.get("trades_required_count", len(CORE_TRADES)),
                internal_count=wo_metrics_dict.get("internal_count", 0),
                internal_pct=wo_metrics_dict.get("internal_pct", 0),
                trade_distribution=wo_metrics_dict.get("trade_distribution"),
                trade_chart=wo_metrics_dict.get("trade_chart", []),
                concentrated_trades=wo_metrics_dict.get("concentrated_trades"),
                high_volume_trades=wo_metrics_dict.get("high_volume_trades"),
                repeat_units=wo_metrics_dict.get("repeat_units"),
                emergency_count=wo_metrics_dict.get("emergency_count", 0),
                emergency_after_hours=wo_metrics_dict.get("emergency_after_hours", 0),
                after_hours_count=wo_metrics_dict.get("after_hours_count", 0),
                after_hours_pct=wo_metrics_dict.get("after_hours_pct", 0),
                after_hours_time_available=wo_metrics_dict.get("after_hours_time_available", True),
                source_distribution=wo_metrics_dict.get("source_distribution"),
                reactive_pct=wo_metrics_dict.get("reactive_pct"),
                estimate_heavy_pct=wo_metrics_dict.get("estimate_heavy_pct", 0),
                unit_turn_count=wo_metrics_dict.get("unit_turn_count", 0),
                seasonal_data=wo_metrics_dict.get("seasonal_data"),
                avg_cost=wo_metrics_dict.get("avg_cost"),
                median_cost=wo_metrics_dict.get("median_cost"),
                cost_data_available=wo_metrics_dict.get("cost_data_available", False),
                pms_ntes=wo_metrics_dict.get("pms_ntes"),
                data_quality=wo_metrics_dict.get("data_quality", []),
                pms_platform=wo_metrics_dict.get("pms_platform"),
                load_warnings=wo_metrics_dict.get("load_warnings", []),
            )

            # ── Step 3: AI interpretation ────────────────────────────────────
            from app.analysis.ai_interpretation import interpret_wo_metrics

            ai_findings = []
            try:
                ai_findings = await loop.run_in_executor(
                    None,
                    functools.partial(interpret_wo_metrics, wo_metrics_dict, client_info_dict),
                )
            except Exception as e:
                logger.warning("AI interpretation failed: %s", e)
            wo_metrics.ai_findings = ai_findings

            # ── Step 4: Vendor directory ─────────────────────────────────────
            from app.parsers.vendor_directory import process_vendor_directory, merge_vendor_data

            vendor_directory_data = None
            if vendor_directory_bytes is not None:
                vendor_file = io.BytesIO(vendor_directory_bytes)
                try:
                    vendor_directory_data = await loop.run_in_executor(
                        None,
                        functools.partial(process_vendor_directory, vendor_file),
                    )
                    if "error" in vendor_directory_data:
                        logger.warning(
                            "Vendor directory issue: %s. Using work order data only.",
                            vendor_directory_data["error"],
                        )
                        vendor_directory_data = None
                except Exception as e:
                    logger.warning("Vendor directory processing error: %s. Using work order data only.", e)
                    vendor_directory_data = None

            merged_vendor = merge_vendor_data(wo_metrics_dict, vendor_directory_data)

            if vendor_directory_data and "error" not in vendor_directory_data:
                wo_metrics.covered_trades = merged_vendor.get("trades_covered", wo_metrics.covered_trades)
                wo_metrics.missing_trades = merged_vendor.get("missing_trades", wo_metrics.missing_trades)
                wo_metrics.trades_covered_count = merged_vendor.get(
                    "trades_covered_count", wo_metrics.trades_covered_count
                )
                if merged_vendor.get("total_vendors"):
                    wo_metrics.unique_vendors = merged_vendor["total_vendors"]

            if vendor_directory_data and "error" not in vendor_directory_data:
                dir_vendors = vendor_directory_data.get("vendors", {})
                vendors = [
                    Vendor(
                        vendor_name=name,
                        trade=data["trades"][0] if data.get("trades") else None,
                        active=(
                            data.get("status", "active").lower().strip()
                            not in ("inactive", "suspended", "terminated")
                        ),
                    )
                    for name, data in dir_vendors.items()
                ]
            elif wo_metrics.vendor_concentration:
                vendors = [
                    Vendor(vendor_name=name, active=True)
                    for name in wo_metrics.vendor_concentration.keys()
                ]
            else:
                vendors = []

            # ── Step 5: Analyze vendors + portfolio ──────────────────────────
            from app.analysis.vendor_analyzer import analyze_vendors
            from app.analysis.portfolio_analyzer import analyze_portfolio

            vendor_metrics = analyze_vendors(vendors)
            portfolio_metrics = analyze_portfolio([], ci)

            # ── Step 6: Document analysis ────────────────────────────────────
            from app.parsers.pdf_extractor import extract_text_from_pdf
            from app.analysis.document_analyzer import analyze_lease, analyze_pma, build_document_analysis

            lease_result = None
            pma_result = None

            if pma_bytes is not None:
                try:
                    pma_text = extract_text_from_pdf(pma_bytes)
                    if pma_text and len(pma_text.strip()) > 100:
                        pma_result = await loop.run_in_executor(
                            None, functools.partial(analyze_pma, pma_text)
                        )
                    else:
                        logger.warning("PMA appears to be scanned/image-based; skipping AI analysis.")
                except Exception as e:
                    logger.warning("PMA analysis failed: %s", e)

            if lease_bytes is not None:
                try:
                    lease_text = extract_text_from_pdf(lease_bytes)
                    if lease_text and len(lease_text.strip()) > 100:
                        lease_result = await loop.run_in_executor(
                            None, functools.partial(analyze_lease, lease_text)
                        )
                    else:
                        logger.warning("Lease appears to be scanned/image-based; skipping AI analysis.")
                except Exception as e:
                    logger.warning("Lease analysis failed: %s", e)

            doc_analysis = build_document_analysis(lease_result, pma_result)

            # ── Step 7: Score + findings + tier ──────────────────────────────
            category_scores: list[CategoryScore] = calculate_all_scores(
                wo_metrics, vendor_metrics, portfolio_metrics, doc_analysis, ci
            )
            overall_score: int = calculate_overall_score(category_scores)
            scores_dict = {cat.key: cat.score for cat in category_scores}

            key_findings = generate_key_findings(
                wo_metrics, vendor_metrics, portfolio_metrics, doc_analysis, ci
            )
            gaps = generate_gaps(
                category_scores, wo_metrics, vendor_metrics, doc_analysis, ci
            )

            gap_titles = [g.title for g in gaps]
            tier = recommend_tier(
                goal=ci.primary_goal or "scale",
                category_scores=scores_dict,
                gaps=gap_titles,
                client_info={
                    "door_count": ci.door_count,
                    "property_count": ci.property_count,
                    "operational_model": ci.operational_model,
                },
            )

            # ── Step 8: Build benchmark rows ─────────────────────────────────
            from app.models.report_data import BenchmarkRow

            benchmark_rows = [
                BenchmarkRow(
                    metric="Avg. First Response",
                    current_value=(
                        f"{wo_metrics.avg_first_response_hours} hrs"
                        if wo_metrics.avg_first_response_hours
                        else "N/A"
                    ),
                    current_css=(
                        "val-bad"
                        if wo_metrics.avg_first_response_hours
                        and wo_metrics.avg_first_response_hours > 4
                        else "val-good"
                        if wo_metrics.avg_first_response_hours
                        and wo_metrics.avg_first_response_hours <= 1
                        else "val-neutral"
                    ),
                    vendoroo_avg="< 10 min",
                    top_performers="< 10 min",
                ),
                BenchmarkRow(
                    metric="Avg. Completion Time",
                    current_value=(
                        f"{wo_metrics.median_completion_days} days"
                        if wo_metrics.median_completion_days
                        else "N/A"
                    ),
                    current_css=(
                        "val-bad"
                        if wo_metrics.median_completion_days
                        and wo_metrics.median_completion_days > 5
                        else "val-good"
                    ),
                    vendoroo_avg="40% decrease",
                    top_performers="50% decrease",
                ),
                BenchmarkRow(
                    metric="Open Work Order Rate",
                    current_value=f"{wo_metrics.open_wo_rate_pct}%",
                    current_css=(
                        "val-bad" if wo_metrics.open_wo_rate_pct > 15 else "val-good"
                    ),
                    vendoroo_avg="15%",
                    top_performers="< 10%",
                ),
                BenchmarkRow(
                    metric="Vendor Coverage",
                    current_value=(
                        f"{wo_metrics.trades_covered_count}/{wo_metrics.trades_required_count} core trades"
                    ),
                    current_css=(
                        "val-bad" if wo_metrics.trades_covered_count < wo_metrics.trades_required_count else "val-good"
                    ),
                    vendoroo_avg=f"{wo_metrics.trades_required_count}/{wo_metrics.trades_required_count} core trades",
                    top_performers=f"{wo_metrics.trades_required_count}/{wo_metrics.trades_required_count} + specialty",
                ),
                BenchmarkRow(
                    metric="After-Hours Coverage",
                    current_value=(
                        f"{wo_metrics.after_hours_pct}% of WOs after-hours"
                        if wo_metrics.after_hours_time_available
                        else "Not measured"
                    ),
                    current_css="val-neutral",
                    vendoroo_avg="24/7 AI triage + troubleshooting",
                    top_performers="24/7 AI triage + emergency dispatch",
                ),
            ]

            # ── Step 9: Generate PDF ──────────────────────────────────────────
            from datetime import date
            from app.models.report_data import ReportData, TierCard, GapTierRow
            from app.report.generator import generate_pdf, render_html
            from app.report.builder import _GAP_TIER_MAP

            staffing = generate_staffing_projection(ci, portfolio_metrics)
            impact_rows = generate_impact_projections(wo_metrics, ci, tier)
            score_dashoffset = ReportData.calculate_dashoffset(overall_score)
            report_date = date.today().strftime("%B %Y")
            tier_display = tier.capitalize()

            # Mask pricing for event-sourced diagnostics (Fix 10)
            _is_event = bool(getattr(ci, "event_source", None))
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

            # Only show gap-tier rows for gaps this prospect actually has (Fix 12)
            _actual_gap_titles = {
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
                if gap_name in _actual_gap_titles
            ]

            aaa_value_amount = "Complimentary"  # Fix 9

            weak_areas = [cat.name.lower() for cat in category_scores if cat.tier == "Not Ready"]
            strong_areas = [cat.name.lower() for cat in category_scores if cat.tier == "Ready"]

            summary_parts = [
                f"{ci.company_name} operates a {ci.door_count}-door portfolio"
                f" using a {ci.operational_model_display or ci.operational_model} model"
                f" with {ci.staff_count} staff. Based on our analysis of your PMS data"
            ]
            if pma_bytes:
                summary_parts.append(", property management agreement")
            if lease_bytes:
                summary_parts.append(", and lease agreements")
            summary_parts.append(f", your portfolio scores {overall_score}/100 on operational readiness.")
            if weak_areas:
                summary_parts.append(
                    f" Key areas for improvement include {', '.join(weak_areas[:3])}."
                )
            if strong_areas:
                summary_parts.append(
                    f" Your {' and '.join(strong_areas[:2])} "
                    f"{'are' if len(strong_areas) > 1 else 'is a'} strong "
                    f"foundation{'s' if len(strong_areas) > 1 else ''} to build on."
                )
            executive_summary = "".join(summary_parts)

            if overall_score >= 70:
                score_description = (
                    "Your portfolio is well-positioned for AI-powered maintenance coordination. "
                    "Minor optimizations during onboarding will maximize effectiveness."
                )
            elif overall_score >= 50:
                score_description = (
                    "Your portfolio has a solid foundation but key operational gaps will reduce "
                    "AI effectiveness without remediation. The good news: Vendoroo's onboarding "
                    "process addresses all identified gaps before go-live."
                )
            else:
                score_description = (
                    "Your portfolio has significant opportunities for improvement through "
                    "AI-powered maintenance coordination. Vendoroo's onboarding process "
                    "is designed to address each gap systematically before go-live."
                )

            doc_sections = []
            if doc_analysis.pma:
                doc_sections.append(doc_analysis.pma)
            if doc_analysis.lease:
                doc_sections.append(doc_analysis.lease)
            doc_sections.append(doc_analysis.emergency_protocols)
            doc_sections.append(doc_analysis.vendor_policies)
            doc_sections.append(doc_analysis.maintenance_sops)

            key_findings_serialized = [f.model_dump() for f in key_findings]
            gaps_serialized = [g.model_dump() for g in gaps]

            projected_score_full = calculate_projected_score(overall_score, gap_titles)

            report_data = ReportData(
                company_name=ci.company_name,
                door_count=ci.door_count,
                property_count=ci.property_count,
                pms_platform=ci.pms_platform,
                operational_model_display=ci.operational_model_display or ci.operational_model,
                overall_score=overall_score,
                score_ring_dashoffset=score_dashoffset,
                projected_score=projected_score_full,
                projected_score_dashoffset=ReportData.calculate_dashoffset(projected_score_full),
                monthly_work_orders=str(int(wo_metrics.monthly_avg_work_orders or 0)),
                avg_response_time=(
                    f"{wo_metrics.avg_first_response_hours} hrs"
                    if wo_metrics.avg_first_response_hours
                    else "N/A"
                ),
                open_wo_rate=f"{wo_metrics.open_wo_rate_pct}%",
                vendor_count=f"{wo_metrics.unique_vendors} vendors",
                report_date=report_date,
                category_scores=category_scores,
                recommended_tier=tier,
                recommended_tier_display=tier_display,
                primary_goal=ci.primary_goal or "scale",
                primary_goal_display=ci.primary_goal_display or "Scale",
                goal_description=ci.goal_description or "Grow portfolio without adding headcount",
                staff_count=ci.staff_count,
                doors_per_staff=int(portfolio_metrics.doors_per_staff or 0),
                executive_summary=executive_summary,
                score_description=score_description,
                benchmark_rows=benchmark_rows,
                benchmark_footnote="Based on uploaded work order history.",
                key_findings=key_findings_serialized,
                document_sections=doc_sections,
                gaps=gaps_serialized,
                impact_intro=(
                    "Based on your work order history, here is your projected operational "
                    "impact with Vendoroo."
                ),
                impact_rows=impact_rows,
                staffing=staffing,
                completed_items=[],
                tier_cards=tier_cards,
                gap_tier_rows=gap_tier_rows,
                aaa_value_amount=aaa_value_amount,
                footer_text=(
                    f"Vendoroo Operations Analysis \u2022 {ci.company_name} \u2022 {report_date}"
                ),
                wo_metrics=wo_metrics,
            )

            html_report: str | None = None
            pdf_bytes: bytes | None = None
            try:
                html_report = render_html(report_data)
                pdf_bytes = await loop.run_in_executor(None, generate_pdf, report_data)
            except Exception as exc:
                logger.warning(
                    "PDF generation failed for full diagnostic %s — continuing without PDF. Error: %s",
                    diagnostic_id,
                    exc,
                )

            # ── Step 9b: Build summary for API/frontend ───────────────────────
            staff_label_map = {"va": "coordinators", "tech": "technicians", "pod": "pods"}
            costs_full = calculate_cost_estimates(ci.door_count, tier)
            impact_rows_summary = generate_impact_projections(wo_metrics, ci, tier)
            staffing_summary = generate_staffing_projection(ci, portfolio_metrics)
            goal_data_full = get_goal_card_data(
                ci.operational_model, ci.staff_count, ci.door_count,
                ci.primary_goal or "scale",
            )

            full_summary = {
                "category_scores": [
                    {"name": cat.name, "key": cat.key, "score": cat.score, "tier": cat.tier, "tier_css": cat.tier_css}
                    for cat in category_scores
                ],
                "projected_score": projected_score_full,
                "impact_rows": [row.model_dump() for row in impact_rows_summary],
                "cost_estimates": costs_full,
                "staffing": staffing_summary.model_dump(),
                "paths": {
                    "scale": goal_data_full["scale_data"],
                    "optimize": goal_data_full["optimize_data"],
                    "elevate": goal_data_full["elevate_data"],
                },
                "company_name": ci.company_name,
                "door_count": ci.door_count,
                "staff_count": ci.staff_count,
                "staff_label": staff_label_map.get(ci.operational_model, "coordinators"),
                "primary_goal": ci.primary_goal or "scale",
                "operational_model": ci.operational_model,
                "has_lease": lease_result is not None,
                "has_pma": pma_result is not None,
                "has_vendor_directory": vendor_directory_data is not None,
                "wo_metrics": {
                    "total_work_orders": wo_metrics.total_work_orders,
                    "maintenance_wos": wo_metrics.maintenance_wos,
                    "monthly_avg": wo_metrics.monthly_avg_work_orders,
                    "avg_first_response_hours": wo_metrics.avg_first_response_hours,
                    "median_completion_days": wo_metrics.median_completion_days,
                    "open_wo_rate_pct": wo_metrics.open_wo_rate_pct,
                    "open_wo_count": wo_metrics.open_wo_count,
                    "unique_vendors": wo_metrics.unique_vendors,
                    "trades_covered_count": wo_metrics.trades_covered_count,
                    "trades_required_count": wo_metrics.trades_required_count,
                    "covered_trades": wo_metrics.covered_trades,
                    "missing_trades": wo_metrics.missing_trades,
                    "after_hours_pct": wo_metrics.after_hours_pct,
                    "months_spanned": wo_metrics.months_spanned,
                    "date_range_start_short": wo_metrics.date_range_start_short,
                    "date_range_end_short": wo_metrics.date_range_end_short,
                },
                "benchmark_rows": [
                    {
                        "metric": row.metric,
                        "current_value": row.current_value,
                        "current_css": row.current_css,
                        "vendoroo_avg": row.vendoroo_avg,
                        "top_performers": row.top_performers,
                    }
                    for row in benchmark_rows
                ],
                "repeat_units": wo_metrics_dict.get("repeat_units", {}),
                "current_cost_per_door": round(
                    (ci.annual_cost_per_staff or STAFF_COST_BENCHMARKS.get(ci.operational_model, STAFF_COST_BENCHMARKS["va"])["annual_loaded_cost"])
                    * ci.staff_count / 12 / max(1, ci.door_count), 2
                ),
                "annual_cost_per_staff": ci.annual_cost_per_staff or STAFF_COST_BENCHMARKS.get(ci.operational_model, STAFF_COST_BENCHMARKS["va"])["annual_loaded_cost"],
            }

            # ── Step 10: Update existing DB record ────────────────────────────
            try:
                await self._update_result(
                    diagnostic_id=diagnostic_id,
                    lead_id=lead_id,
                    scores=scores_dict,
                    overall_score=overall_score,
                    tier=tier,
                    pdf_bytes=pdf_bytes,
                    html_report=html_report,
                    key_findings=key_findings_serialized,
                    gaps=gaps_serialized,
                    summary=full_summary,
                )
                if lead_id is not None:
                    await self._lead_service.update_status(lead_id, "diagnostic_complete")
            except Exception as exc:
                logger.error(
                    "DB update failed for full diagnostic %s: %s", diagnostic_id, exc
                )

            # ── Step 11: Send emails (DISABLED) ──────────────────────────────
            # if lead_id is not None:
            #     try:
            #         async with AsyncSessionLocal() as session:
            #             lead_record = await session.get(db_models.Lead, lead_id)
            #         if lead_record is not None:
            #             await self._email_service.send_diagnostic_results(
            #                 lead_email=lead_record.email,
            #                 lead_name=lead_record.name,
            #                 diagnostic_id=diagnostic_id,
            #                 overall_score=float(overall_score),
            #                 tier=tier,
            #                 key_findings=key_findings_serialized,
            #                 pdf_bytes=pdf_bytes,
            #             )
            #             await self._email_service.send_sales_notification(
            #                 lead_name=lead_record.name,
            #                 lead_email=lead_record.email,
            #                 lead_company=lead_record.company,
            #                 overall_score=float(overall_score),
            #                 tier=tier,
            #             )
            #     except Exception as exc:
            #         logger.warning(
            #             "Email send failed for full diagnostic %s: %s", diagnostic_id, exc
            #         )

        except Exception as exc:
            logger.error(
                "Full diagnostic failed for %s: %s", diagnostic_id, exc, exc_info=True
            )
            try:
                async with AsyncSessionLocal() as session:
                    record = await session.get(db_models.Diagnostic, diagnostic_id)
                    if record is not None:
                        record.status = "failed"
                        record.error = str(exc)
                        await session.commit()
            except Exception as db_exc:
                logger.error(
                    "Could not write failure status for diagnostic %s: %s",
                    diagnostic_id,
                    db_exc,
                )

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _generate_pdf(
        self,
        survey: SurveyResponse,
        client_info: ClientInfo,
        category_scores: list,
        overall_score: int,
        tier: str,
        key_findings: list,
        gaps: list,
        wo_metrics,
    ) -> tuple[bytes, str]:
        """Build a fully-populated ReportData via builder and render the PDF + HTML."""
        import asyncio
        from app.report.builder import build_report_data
        from app.report.generator import generate_pdf, render_html

        portfolio_metrics = self._adapter.build_portfolio_metrics(survey, client_info)
        doc_analysis = self._adapter.build_document_analysis(survey)

        report_data = build_report_data(
            client_info=client_info,
            category_scores=category_scores,
            overall_score=overall_score,
            tier=tier,
            key_findings=key_findings,
            gaps=gaps,
            wo_metrics=wo_metrics,
            portfolio_metrics=portfolio_metrics,
            doc_analysis=doc_analysis,
        )

        html_report = render_html(report_data)
        loop = asyncio.get_event_loop()
        pdf_bytes = await loop.run_in_executor(None, generate_pdf, report_data)
        return pdf_bytes, html_report

    async def _store_result(
        self,
        diagnostic_id: str,
        scores: dict,
        overall_score: int,
        tier: str,
        pdf_bytes: bytes | None,
        key_findings: list | None = None,
        gaps: list | None = None,
        lead_id: str | None = None,
        summary: dict | None = None,
        html_report: str | None = None,
    ) -> None:
        """Persist the diagnostic result to the database."""
        async with AsyncSessionLocal() as session:
            scores_payload = dict(scores)
            scores_payload["overall"] = overall_score

            record = db_models.Diagnostic(
                id=diagnostic_id,
                lead_id=lead_id,
                diagnostic_type="quick",
                status="complete",
                scores=scores_payload,
                key_findings=key_findings or [],
                gaps=gaps or [],
                summary=summary,
                tier=tier,
                pdf_data=pdf_bytes,
                html_report=html_report,
                pdf_path=None,
                error=None,
            )
            session.add(record)
            await session.commit()

    async def _update_result(
        self,
        diagnostic_id: str,
        scores: dict,
        overall_score: int,
        tier: str,
        pdf_bytes: bytes | None,
        key_findings: list | None = None,
        gaps: list | None = None,
        lead_id: str | None = None,
        summary: dict | None = None,
        html_report: str | None = None,
    ) -> None:
        """Update an existing diagnostic record in the database (used by full diagnostic)."""
        async with AsyncSessionLocal() as session:
            record = await session.get(db_models.Diagnostic, diagnostic_id)
            if record is None:
                # Fall back to insert if the record was never pre-created
                scores_payload = dict(scores)
                scores_payload["overall"] = overall_score
                record = db_models.Diagnostic(
                    id=diagnostic_id,
                    lead_id=lead_id,
                    diagnostic_type="full",
                    status="complete",
                    scores=scores_payload,
                    key_findings=key_findings or [],
                    gaps=gaps or [],
                    tier=tier,
                    pdf_data=pdf_bytes,
                    html_report=html_report,
                    pdf_path=None,
                    error=None,
                    summary=summary,
                )
                session.add(record)
            else:
                scores_payload = dict(scores)
                scores_payload["overall"] = overall_score
                record.status = "complete"
                record.scores = scores_payload
                record.key_findings = key_findings or []
                record.gaps = gaps or []
                record.tier = tier
                record.pdf_data = pdf_bytes
                record.html_report = html_report
                record.pdf_path = None
                record.error = None
                record.summary = summary
                if lead_id is not None:
                    record.lead_id = lead_id
            await session.commit()
