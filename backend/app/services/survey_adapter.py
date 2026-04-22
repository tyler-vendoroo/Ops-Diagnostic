"""SurveyAdapter: converts SurveyResponse + ClientInfo into analysis-ready metrics."""

from app.models.survey import SurveyResponse
from app.models.input_data import ClientInfo
from app.models.analysis import (
    WorkOrderMetrics,
    VendorMetrics,
    PortfolioMetrics,
    DocumentAnalysis,
    DocumentSection,
    DocumentFinding,
)
from app.config import REQUIRED_TRADES, ALL_TRADES


# ── Lookup tables ────────────────────────────────────────

_TRADE_NORMALIZE: dict[str, str] = {
    # Frontend IDs → canonical backend names
    "plumbing": "plumbing",
    "electrical": "electrical",
    "rooter": "rooter",
    "appliance_repair": "appliance repair",
    "handyperson": "handyperson",
    "hvac": "hvac",
    "roofing": "roofing",
    "pest_control": "pest control",
    "painting": "painting",
    "flooring": "flooring",
    "landscaping": "landscaping",
    "pool_spa": "pool/spa",
    "locksmith": "locksmith",
    "cleaning_turnover": "cleaning/turnover",
    # Legacy / alternate spellings
    "general_handyman": "handyperson",
    "general handyman": "handyperson",
    "appliance repair": "appliance repair",
    "pest control": "pest control",
    "pool/spa": "pool/spa",
    "cleaning/turnover": "cleaning/turnover",
    "cleaning": "cleaning/turnover",
}

_RESPONSE_TIME_MAP: dict[str, float] = {
    "under_1hr": 0.5,
    "1_4hrs": 2.5,
    "4_12hrs": 8.0,
    "same_day": 6.0,
    "next_day": 18.0,
    "unsure": 12.0,
}

_COMPLETION_TIME_MAP: dict[str, float] = {
    "1_3days": 2.0,
    "3_7days": 5.0,
    "7_14days": 10.0,
    "14plus": 21.0,
    "unsure": 7.0,
}

_AFTER_HOURS_PCT_MAP: dict[str, float] = {
    "24_7_coverage": 30.0,
    "answering_service": 25.0,
    "on_call_rotation": 20.0,
    "voicemail_only": 15.0,
    "none": 10.0,
}


class SurveyAdapter:
    """Adapts survey responses into the analysis models consumed by the scoring engine."""

    def build_wo_metrics(
        self,
        survey: SurveyResponse,
        client_info: ClientInfo,
    ) -> WorkOrderMetrics:
        """Build a WorkOrderMetrics object from survey answers."""
        door_count = client_info.door_count

        # Monthly WO volume
        monthly_wos: float
        if survey.estimated_monthly_wos is not None:
            monthly_wos = float(survey.estimated_monthly_wos)
        else:
            monthly_wos = door_count * 0.8

        # Response and completion times
        avg_response_hours = _RESPONSE_TIME_MAP.get(
            survey.estimated_response_time or "", 12.0
        )
        median_completion_days = _COMPLETION_TIME_MAP.get(
            survey.estimated_completion_time or "", 7.0
        )

        # After-hours coverage → expressed as a pct of WOs
        after_hours_pct = _AFTER_HOURS_PCT_MAP.get(
            survey.after_hours_method or "", 15.0
        )

        # Open WO rate
        open_wo_rate_pct: float
        if survey.estimated_open_rate is not None:
            open_wo_rate_pct = survey.estimated_open_rate * 100.0
        else:
            open_wo_rate_pct = 15.0  # industry default assumption

        # Vendor / trade coverage pulled from the survey
        vendor_count = survey.vendor_count or 0
        trades_covered = survey.trades_covered or []
        covered_set = {_TRADE_NORMALIZE.get(t.lower(), t.lower().replace("_", " ")) for t in trades_covered}
        missing_trades = [t for t in REQUIRED_TRADES if t not in covered_set]

        return WorkOrderMetrics(
            monthly_avg_work_orders=monthly_wos,
            avg_first_response_hours=avg_response_hours,
            response_time_method="survey",
            median_completion_days=median_completion_days,
            open_wo_rate_pct=open_wo_rate_pct,
            after_hours_pct=after_hours_pct,
            after_hours_time_available=(survey.after_hours_method not in ("none", None)),
            unique_vendors=vendor_count,
            covered_trades=list(covered_set),
            missing_trades=missing_trades,
            trades_covered_count=len(covered_set),
            trades_required_count=len(REQUIRED_TRADES),
            # Reasonable assumptions to keep scalability scorer happy
            months_spanned=6.0,
            data_reliability="low",
            reliability_warning="Estimated from survey — no work order data provided.",
        )

    def build_vendor_metrics(
        self,
        survey: SurveyResponse,
    ) -> VendorMetrics:
        """Build a VendorMetrics object from survey answers."""
        trades_covered = survey.trades_covered or []
        covered_set = {_TRADE_NORMALIZE.get(t.lower(), t.lower().replace("_", " ")) for t in trades_covered}
        missing = [t for t in REQUIRED_TRADES if t not in covered_set]

        return VendorMetrics(
            total_vendors=survey.vendor_count or 0,
            unique_trades=len(covered_set),
            trades_covered=list(covered_set),
            trades_missing=missing,
            # We have no backup-vendor data from the survey
            trades_with_backup=0,
            vendor_concentration_index=0.5,  # unknown, assume moderate
            contact_completeness_pct=50.0,   # unknown, assume partial
        )

    def build_portfolio_metrics(
        self,
        survey: SurveyResponse,
        client_info: ClientInfo,
    ) -> PortfolioMetrics:
        """Build a PortfolioMetrics object from survey + client info."""
        door_count = client_info.door_count
        property_count = client_info.property_count or survey.property_count or 1
        staff_count = client_info.staff_count or survey.staff_count or 1

        avg_units = door_count / max(1, property_count)
        doors_per_staff = door_count / max(1, staff_count)

        return PortfolioMetrics(
            total_doors=door_count,
            total_properties=property_count,
            avg_units_per_property=round(avg_units, 1),
            doors_per_staff=round(doors_per_staff, 1),
        )

    def build_document_analysis(
        self,
        survey: SurveyResponse,
    ) -> DocumentAnalysis:
        """Build a DocumentAnalysis object from survey policy questions."""
        # Emergency protocols
        emergency_answer = (survey.has_written_emergency_protocols or "").lower()
        if emergency_answer == "yes":
            has_emergency = True
            emergency_status = "Received & Reviewed"
            emergency_tier = "ready"
            emergency_readiness_score = 8.0
            emergency_findings = [
                DocumentFinding(
                    text="Written emergency protocols exist",
                    is_positive=True,
                )
            ]
        elif emergency_answer == "unsure":
            has_emergency = False
            emergency_status = "Partially Documented"
            emergency_tier = "needs-work"
            emergency_readiness_score = 4.0
            emergency_findings = [
                DocumentFinding(
                    text="Emergency protocols may exist but are not confirmed",
                    is_positive=False,
                )
            ]
        else:  # "no" or missing
            has_emergency = False
            emergency_status = "Not Documented"
            emergency_tier = "not-ready"
            emergency_readiness_score = 0.0
            emergency_findings = [
                DocumentFinding(
                    text="No written emergency protocols",
                    is_positive=False,
                    is_missing=True,
                )
            ]

        emergency_section = DocumentSection(
            title="Emergency Protocols",
            status=emergency_status,
            status_tier=emergency_tier,
            findings=emergency_findings,
        )

        # NTE (Not-to-Exceed thresholds)
        has_nte = (survey.has_defined_ntes or "").lower() == "yes"
        nte_threshold = "$500" if has_nte else None
        nte_is_tiered = survey.ntes_are_tiered if has_nte else False

        # SLAs
        has_slas = (survey.has_defined_slas or "").lower() == "yes"

        return DocumentAnalysis(
            emergency_protocols=emergency_section,
            has_emergency_protocols=has_emergency,
            emergency_readiness_score=emergency_readiness_score,
            has_defined_slas=has_slas,
            has_escalation_procedures=has_emergency,  # assume written protocols include escalation
            nte_threshold=nte_threshold,
            nte_is_tiered=nte_is_tiered,
        )

    def adapt(
        self,
        survey: SurveyResponse,
        client_info: ClientInfo,
    ) -> tuple[WorkOrderMetrics, VendorMetrics, PortfolioMetrics, DocumentAnalysis]:
        """Convert survey + client info into the four analysis metrics objects.

        Returns: (wo_metrics, vendor_metrics, portfolio_metrics, doc_analysis)
        """
        wo_metrics = self.build_wo_metrics(survey, client_info)
        vendor_metrics = self.build_vendor_metrics(survey)
        portfolio_metrics = self.build_portfolio_metrics(survey, client_info)
        doc_analysis = self.build_document_analysis(survey)
        return wo_metrics, vendor_metrics, portfolio_metrics, doc_analysis
