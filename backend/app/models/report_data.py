"""Master ReportData model — the single contract between analysis and templates."""
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field

from app.models.analysis import (
    CategoryScore,
    DocumentSection,
    GapFinding,
    ImpactProjection,
    KeyFinding,
    StaffingProjection,
    WorkOrderMetrics,
)


class BenchmarkRow(BaseModel):
    """A row in the operations benchmark table."""
    metric: str
    current_value: str
    current_css: str  # "val-bad", "val-good", "val-neutral"
    vendoroo_avg: str
    top_performers: str
    top_css: str = "val-good"


class TimelineStep(BaseModel):
    """A step in the onboarding timeline."""
    day: str  # "Day 1", "Days 1-3"
    title: str
    description: str
    is_last: bool = False


class PathCard(BaseModel):
    """A Scale/Optimize/Elevate path card on the Projected Impact page."""
    path_number: int  # 1, 2, 3
    name: str  # "Scale", "Optimize", "Elevate"
    description: str
    stat_value: str  # "1,050+", "2 FTEs", "94%+"
    stat_label: str  # "doors with current team"
    best_tier: str  # "Direct or Command"
    is_selected: bool = False


class TierCard(BaseModel):
    """A tier card (Engage/Direct/Command) on the Your Path page."""
    name: str  # "Engage", "Direct", "Command"
    subtitle: str
    price: str  # "$3"
    price_unit: str  # "/ unit / month"
    roos: str  # "3 dedicated ROOs"
    features: list[str]  # base features
    new_features: list[str] = Field(default_factory=list)  # starred features
    is_recommended: bool = False


class GapTierRow(BaseModel):
    """A row in the gap-to-tier mapping table."""
    gap_name: str
    engage: str  # "check", "dash"
    direct: str  # "check", "dash"
    command: str  # "check", "dash", or custom like "check_plus" with extra text
    command_note: str = ""  # e.g. "+RescueRoo"


class OutcomeStat(BaseModel):
    """A stat in the outcome card."""
    value: str  # "$3,846"
    label: str  # "Estimated monthly cost at Direct (641 doors x $6)"


class PhaseCard(BaseModel):
    """A phase card in the AI Adoption Program page."""
    phase_number: int  # 1, 2, 3
    name: str  # "Learning", "Adoption", "Optimization"
    timeframe: str  # "Days 0 to 30"
    description: str
    milestone: str
    is_current: bool = False  # Phase 1 gets yellow border


class ReportData(BaseModel):
    """Complete data model for rendering the report template.

    Every field the Jinja2 template needs lives here.
    """

    # ── Dual Score System ──
    projected_score: int = 93
    projected_score_dashoffset: float = 22.0
    projected_score_color: str = "#039cac"  # Teal — always teal for projected
    current_score_color: str = "#FDBB00"    # Set dynamically via _ring_color()

    # ── Goal ──
    primary_goal: str = "scale"
    primary_goal_display: str = "Scale"
    goal_description: str = "Grow portfolio without adding headcount"

    # ── Tier Recommendation ──
    recommended_tier: str = "direct"
    recommended_tier_display: str = "Direct"

    # ── Staff (model-aware) ──
    staff_label: str = "coordinators"
    staff_count: int = 0
    doors_per_staff: float = 0
    staff_benchmark: int = 175

    # ── Cover Page ──
    company_name: str
    door_count: int
    property_count: int
    pms_platform: str
    operational_model_display: str
    overall_score: int  # 0-100
    score_ring_dashoffset: float  # Pre-calculated SVG dashoffset
    monthly_work_orders: str  # Formatted: "187"
    avg_response_time: str  # Formatted: "14.2 hrs"
    open_wo_rate: str  # Formatted: "18.3%"
    vendor_count: str  # Formatted: "22 vendors"
    report_date: str  # "March 2026"

    # ── Executive Summary ──
    executive_summary: str  # Narrative paragraph
    score_description: str  # Description below score card
    category_scores: list[CategoryScore]

    # ── Work Order Metrics (for Page 4: WO Analysis) ──
    wo_metrics: Optional[WorkOrderMetrics] = None

    # ── Current Operations Analysis ──
    benchmark_rows: list[BenchmarkRow]
    benchmark_footnote: str
    key_findings: list[KeyFinding]

    # ── Policy & Documentation Review ──
    document_sections: list[DocumentSection]

    # ── What We Address Together (Page 5) ──
    gaps: list[GapFinding]
    aaa_intro: str = ""  # AI Adoption Advisor intro paragraph for page 5
    gap_count: int = 0
    top_gap: str = ""

    # ── Projected Impact (Page 6) ──
    impact_intro: str
    impact_rows: list[ImpactProjection]
    staffing: StaffingProjection
    paths_intro: str = ""  # "Your AI teammate supports three different strategic paths..."
    paths_footnote: str = ""  # footnote below path cards
    current_state_label: str = ""  # e.g. "3 Coordinators"
    current_state_detail: str = ""  # e.g. "342 doors (114 doors/coordinator) | Benchmark: ..."
    path_cards: list[PathCard] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    wo_analysis_period: str = ""

    # ── Your Path with Vendoroo (Page 7) ──
    tier_cards: list[TierCard] = Field(default_factory=list)
    gap_tier_rows: list[GapTierRow] = Field(default_factory=list)
    outcome_title: str = ""  # "Based on your analysis: Direct is the recommended starting point"
    outcome_description: str = ""
    outcome_stats: list[OutcomeStat] = Field(default_factory=list)
    tier_footnote: str = ""  # pricing footnote

    # ── AI Adoption Program (Page 8) ──
    aaa_value_amount: str = "$2,500"
    aaa_value_description: str = ""
    completed_items: list[str]
    phase_cards: list[PhaseCard] = Field(default_factory=list)

    # ── Legacy / Recommended Path Forward ──
    timeline_steps: list[TimelineStep] = Field(default_factory=list)
    standard_days: str = ""  # "10-14 Days"
    accelerated_days: str = ""  # "5-10 Days"

    # ── Footer ──
    footer_text: str  # "Vendoroo Operations Analysis * Company * ..."

    @staticmethod
    def calculate_dashoffset(score: int, circumference: float = 314.16) -> float:
        """Calculate SVG stroke-dashoffset for a score ring."""
        return circumference * (1 - score / 100)
