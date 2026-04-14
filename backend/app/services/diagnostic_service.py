"""DiagnosticService: orchestrates the quick diagnostic pipeline."""

import uuid
import logging
from dataclasses import dataclass, field

from app.models.survey import SurveyResponse
from app.models.input_data import ClientInfo
from app.models.analysis import CategoryScore
from app.models.lead import LeadCapture
from app.services.survey_adapter import SurveyAdapter
from app.services.lead_service import LeadService
from app.services.email_service import EmailService
from app.analysis.scoring_engine import (
    calculate_all_scores,
    calculate_overall_score,
    generate_key_findings,
    generate_gaps,
    recommend_tier,
)
from app.db.database import AsyncSessionLocal
from app.db import models as db_models

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

        # ── Step 5: PDF Generation ───────────────────────────────────────────
        pdf_bytes: bytes | None = None
        try:
            pdf_bytes = await self._generate_pdf(
                survey, client_info, category_scores, overall_score,
                tier, key_findings, gaps, wo_metrics,
            )
        except Exception as exc:
            logger.warning(
                "PDF generation failed for diagnostic %s — continuing without PDF. Error: %s",
                diagnostic_id,
                exc,
            )

        # ── Step 6: Persist to DB ────────────────────────────────────────────
        key_findings_serialized = [f.model_dump() for f in key_findings]
        gaps_serialized = [g.model_dump() for g in gaps]

        try:
            await self._store_result(
                diagnostic_id=diagnostic_id,
                lead_id=lead_id,
                scores=scores_dict,
                overall_score=overall_score,
                tier=tier,
                pdf_bytes=pdf_bytes,
            )
        except Exception as exc:
            logger.error(
                "DB write failed for diagnostic %s: %s",
                diagnostic_id,
                exc,
            )
            # Non-fatal — still return the result

        # ── Step 7: Send emails ──────────────────────────────────────────────
        if lead is not None:
            await self._email_service.send_diagnostic_results(
                lead_email=lead.email,
                lead_name=lead.name,
                diagnostic_id=diagnostic_id,
                overall_score=float(overall_score),
                tier=tier,
                key_findings=key_findings_serialized,
                pdf_bytes=pdf_bytes,
            )
            await self._email_service.send_sales_notification(
                lead_name=lead.name,
                lead_email=lead.email,
                lead_company=lead.company,
                overall_score=float(overall_score),
                tier=tier,
            )

        return DiagnosticResult(
            diagnostic_id=diagnostic_id,
            scores=scores_dict,
            overall_score=float(overall_score),
            tier=tier,
            key_findings=key_findings_serialized,
            gaps=gaps_serialized,
            pdf_bytes=pdf_bytes,
            status="complete",
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
    ) -> bytes:
        """Build a minimal ReportData and render the PDF.

        We construct only the fields required for a quick diagnostic render.
        Missing / optional fields use their model defaults.
        """
        import asyncio
        from datetime import date
        from app.models.report_data import ReportData, BenchmarkRow
        from app.report.generator import generate_pdf
        from app.analysis.scoring_engine import (
            generate_impact_projections,
            generate_staffing_projection,
        )

        portfolio_metrics = self._adapter.build_portfolio_metrics(survey, client_info)

        impact_rows = generate_impact_projections(wo_metrics, client_info, tier)
        staffing = generate_staffing_projection(client_info, portfolio_metrics)

        score_dashoffset = ReportData.calculate_dashoffset(overall_score)
        report_date = date.today().strftime("%B %Y")

        tier_display = tier.capitalize()

        report_data = ReportData(
            # Cover page
            company_name=client_info.company_name,
            door_count=client_info.door_count,
            property_count=client_info.property_count,
            pms_platform=client_info.pms_platform,
            operational_model_display=client_info.operational_model_display or client_info.operational_model,
            overall_score=overall_score,
            score_ring_dashoffset=score_dashoffset,
            monthly_work_orders=str(int(wo_metrics.monthly_avg_work_orders)),
            avg_response_time=f"{wo_metrics.avg_first_response_hours} hrs"
                if wo_metrics.avg_first_response_hours else "N/A",
            open_wo_rate=f"{wo_metrics.open_wo_rate_pct}%",
            vendor_count=f"{wo_metrics.unique_vendors} vendors",
            report_date=report_date,
            # Scores and summary
            category_scores=category_scores,
            recommended_tier=tier,
            recommended_tier_display=tier_display,
            primary_goal=client_info.primary_goal or "scale",
            primary_goal_display=client_info.primary_goal_display or "Scale",
            goal_description=client_info.goal_description or "Grow portfolio without adding headcount",
            staff_count=client_info.staff_count,
            doors_per_staff=int(portfolio_metrics.doors_per_staff),
            executive_summary=(
                f"{client_info.company_name} scored {overall_score}/100 on the Vendoroo Operations "
                f"Readiness Diagnostic. Based on {client_info.door_count} doors across "
                f"{client_info.property_count} properties, the analysis identified "
                f"{len(gaps)} operational gap(s). Recommended tier: {tier_display}."
            ),
            score_description=(
                f"Your score of {overall_score} places you in the "
                f"{'Ready' if overall_score >= 70 else 'Needs Work' if overall_score >= 50 else 'Not Ready'} "
                f"tier. Addressing the identified gaps could raise your score by 20–30 points."
            ),
            # Operations
            benchmark_rows=[],
            benchmark_footnote="Estimated from survey data — upload work order history for full analysis.",
            key_findings=key_findings,
            # Docs
            document_sections=[],
            # Gaps
            gaps=gaps,
            # Impact
            impact_intro="Based on your survey responses, here is your projected operational impact with Vendoroo.",
            impact_rows=impact_rows,
            staffing=staffing,
            # Required non-optional fields
            completed_items=[],
            footer_text=f"Vendoroo Operations Analysis \u2022 {client_info.company_name} \u2022 {report_date}",
        )

        # generate_pdf is sync; run in executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        pdf_bytes = await loop.run_in_executor(None, generate_pdf, report_data)
        return pdf_bytes

    async def _store_result(
        self,
        diagnostic_id: str,
        scores: dict,
        overall_score: int,
        tier: str,
        pdf_bytes: bytes | None,
        lead_id: str | None = None,
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
                tier=tier,
                pdf_data=pdf_bytes,  # raw bytes; None if generation failed
                pdf_path=None,
                error=None,
            )
            session.add(record)
            await session.commit()
