"""Pydantic models for analysis results, scoring, and report components."""
from typing import Optional
from pydantic import BaseModel, Field


# ── Metrics ──────────────────────────────────────────────

class WorkOrderMetrics(BaseModel):
    """Computed metrics from work order data (from wo_processor pipeline)."""
    # Volume
    total_work_orders: int = 0
    maintenance_wos: int = 0
    recurring_wos: int = 0
    inspection_count: int = 0
    cancelled_count: int = 0
    monthly_avg_work_orders: float = 0.0
    date_range_days: int = 0
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    date_range_start_short: Optional[str] = None
    date_range_end_short: Optional[str] = None
    date_range_year: Optional[str] = None
    months_spanned: float = 0.0
    data_reliability: Optional[str] = None  # "low" / "moderate" / "high"
    reliability_warning: Optional[str] = None

    # Volume Benchmarking
    wo_per_door_monthly: Optional[float] = None
    wo_per_door_annual: Optional[float] = None
    volume_assessment: Optional[str] = None  # "low" / "normal" / "high"

    # Open WO Rate
    open_wo_count: Optional[int] = 0
    open_wo_rate_pct: Optional[float] = 0.0

    # Completion
    median_completion_days: Optional[float] = None
    completed_count: int = 0

    # Response Time
    avg_first_response_hours: Optional[float] = None
    response_time_method: Optional[str] = None
    response_time_note: Optional[str] = None

    # Vendors
    unique_vendors: int = 0
    top_vendor_pct: float = 0.0
    vendor_concentration: Optional[dict] = None
    covered_trades: list[str] = Field(default_factory=list)
    missing_trades: list[str] = Field(default_factory=list)
    specialty_trades_covered: list[str] = Field(default_factory=list)
    trades_covered_count: int = 0
    trades_required_count: int = 12

    # Internal Staff
    internal_count: int = 0
    internal_pct: float = 0.0

    # Trades
    trade_distribution: Optional[dict] = None
    trade_chart: list[dict] = Field(default_factory=list)
    concentrated_trades: Optional[dict] = None
    high_volume_trades: Optional[dict] = None

    # Repeat Units
    repeat_units: Optional[dict] = None

    # Emergencies
    emergency_count: int = 0
    emergency_after_hours: int = 0

    # After Hours
    after_hours_count: int = 0
    after_hours_pct: float = 0.0
    after_hours_time_available: bool = True

    # Source
    source_distribution: Optional[dict] = None

    # Maintenance Mix (honest 3-way split: proactive / resident-initiated / unclassified)
    maintenance_mix: Optional[dict] = None
    # Reactive vs Preventive (backward compat — equals resident_initiated_pct)
    reactive_pct: Optional[float] = None
    estimate_heavy_pct: float = 0.0
    unit_turn_count: int = 0

    # Seasonal
    seasonal_data: Optional[dict] = None

    # Cost
    avg_cost: Optional[float] = None
    median_cost: Optional[float] = None
    cost_data_available: bool = False

    # NTE from PMS
    pms_ntes: Optional[list] = None

    # Data Quality
    data_quality: list[str] = Field(default_factory=list)

    # Pipeline metadata
    pms_platform: Optional[str] = None
    load_warnings: list[str] = Field(default_factory=list)

    # AI-generated findings (from Stage 3)
    ai_findings: list[dict] = Field(default_factory=list)


class VendorMetrics(BaseModel):
    """Computed metrics from vendor data."""
    total_vendors: int = 0
    unique_trades: int = 0
    trades_covered: list[str] = Field(default_factory=list)
    trades_missing: list[str] = Field(default_factory=list)
    trades_with_backup: int = 0
    vendor_concentration_index: float = 0.0  # Herfindahl (0-1, lower=better)
    contact_completeness_pct: float = 0.0


class PortfolioMetrics(BaseModel):
    """Computed metrics from portfolio data."""
    total_doors: int = 0
    total_properties: int = 0
    avg_units_per_property: float = 0.0
    doors_per_staff: float = 0.0


# ── Document Analysis (from Claude API) ──────────────────

class DocumentFinding(BaseModel):
    """A single finding from document analysis."""
    text: str
    is_positive: bool  # True = green bullet, False = red bullet
    is_missing: bool = False  # True = "Missing: ..." prefix


class DocumentSection(BaseModel):
    """Analysis results for a single document type."""
    title: str  # "Property Management Agreement (PMA)"
    status: str  # "Received & Reviewed", "Not Documented", "Partially Documented"
    status_tier: str  # "ready", "needs-work", "not-ready"
    findings: list[DocumentFinding] = Field(default_factory=list)


class DocumentAnalysis(BaseModel):
    """Full document analysis results from Claude API."""
    pma: Optional[DocumentSection] = None
    lease: Optional[DocumentSection] = None
    emergency_protocols: DocumentSection = Field(
        default_factory=lambda: DocumentSection(
            title="Emergency Protocols",
            status="Not Documented",
            status_tier="not-ready",
            findings=[]
        )
    )
    vendor_policies: DocumentSection = Field(
        default_factory=lambda: DocumentSection(
            title="Vendor Management Policies",
            status="Not Documented",
            status_tier="not-ready",
            findings=[]
        )
    )
    maintenance_sops: DocumentSection = Field(
        default_factory=lambda: DocumentSection(
            title="Maintenance SOPs",
            status="Not Documented",
            status_tier="not-ready",
            findings=[]
        )
    )
    # Quality scores from Claude (0-10 scale, used in scoring engine)
    pma_quality_score: float = 0.0
    lease_quality_score: float = 0.0
    emergency_readiness_score: float = 0.0
    has_emergency_protocols: bool = False
    has_defined_slas: bool = False
    has_escalation_procedures: bool = False
    nte_threshold: Optional[str] = None  # e.g. "$500"
    nte_is_tiered: bool = False
    # Lease analysis detail fields
    lease_policy_assessments: Optional[list] = None
    lease_additional_policies: Optional[list] = None
    lease_addenda_found: Optional[list] = None
    lease_clear_count: Optional[int] = None
    lease_ambiguous_count: Optional[int] = None
    lease_silent_count: Optional[int] = None
    lease_kickoff_discussion_count: Optional[int] = None
    # PMA analysis detail fields
    pma_extracted_config: Optional[dict] = None
    pma_policy_assessments: Optional[list] = None


# ── Scoring ──────────────────────────────────────────────

class CategoryScore(BaseModel):
    """Score for a single readiness category."""
    name: str  # Display name: "Policy Completeness"
    key: str   # Internal key: "policy_completeness"
    score: int  # 0-100
    tier: str   # "Ready", "Needs Work", "Not Ready"
    tier_css: str  # "ready", "needs-work", "not-ready"
    color: str  # CSS color variable: "var(--green)"


# ── Key Findings ─────────────────────────────────────────

class KeyFinding(BaseModel):
    """A key finding for the operations analysis page."""
    title: str
    description: str
    color: str  # CSS color: "var(--red)", "var(--amber)", "var(--green)", "var(--blue)"


# ── Gap Analysis ─────────────────────────────────────────

class GapFinding(BaseModel):
    """An identified readiness gap with recommendation."""
    title: str
    severity: str  # "High Priority", "Medium Priority", "Low Priority"
    severity_color: str  # "var(--red)", "var(--amber)", "var(--green)"
    severity_bg: str  # "var(--red-light)", "var(--amber-light)", "var(--green-light)"
    severity_border: str  # "var(--red)", "var(--amber)", "var(--green)"
    detail: str
    recommendation: str


# ── Projected Impact ─────────────────────────────────────

class ImpactProjection(BaseModel):
    """A single row in the projected impact table."""
    metric: str
    current_value: str
    current_is_bad: bool = True
    projected_value: str
    benchmark_range: str
    improvement: Optional[str] = None  # e.g. "99%", None for N/A
    note: Optional[str] = None


class StaffingProjection(BaseModel):
    """Staffing and scale projection data."""
    current_staff: int
    current_doors: int
    doors_per_staff: int
    staff_benchmark: int
    scale_doors: int  # Option A: doors with current staff
    optimize_staff: int  # Option B: staff for current doors
    fte_savings: int
    scale_narrative: str = ""     # Path 1: Scale description
    optimize_narrative: str = ""  # Path 2: Optimize description
    elevate_narrative: str = ""   # Path 3: Elevate description
