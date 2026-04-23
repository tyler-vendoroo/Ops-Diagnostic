"""
Test quick diagnostic pipeline: SurveyAdapter → scoring engine → findings → gaps → insights.

Run: cd backend && python -m pytest tests/test_quick_diagnostic.py -v
"""

import sys
import os
import pytest

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.survey import SurveyResponse
from app.models.input_data import ClientInfo
from app.services.survey_adapter import SurveyAdapter
from app.analysis.scoring_engine import (
    calculate_all_scores,
    calculate_overall_score,
    calculate_projected_score,
    generate_key_findings,
    generate_gaps,
    recommend_tier,
    score_vendor_coverage,
    score_response_efficiency,
    score_after_hours_readiness,
    score_emergency_protocols,
    score_scalability_potential,
)
from app.config import REQUIRED_TRADES
try:
    from app.config import CORE_TRADES, SPECIALTY_TRADES
except ImportError:
    CORE_TRADES = REQUIRED_TRADES
    SPECIALTY_TRADES = []

from app.config.benchmarks import STAFFING_BENCHMARKS


# ── Helpers ────────────────────────────────────────────────────

def make_survey(**overrides) -> SurveyResponse:
    """Create a SurveyResponse with sensible defaults, overriding as needed."""
    defaults = {
        "door_count": 300,
        "property_count": 20,
        "pms_platform": "AppFolio",
        "staff_count": 2,
        "vendor_count": 15,
        "trades_covered": ["plumbing", "electrical", "hvac", "appliance_repair",
                           "handyperson", "roofing"],
        "has_written_emergency_protocols": "no",
        "has_defined_ntes": "no",
        "ntes_are_tiered": False,
        "has_defined_slas": "no",
        "estimated_response_time": "4_12hrs",
        "estimated_completion_time": "3_7days",
        "after_hours_method": "answering_service",
        "primary_goal": "scale",
        "pain_points": [],
    }
    defaults.update(overrides)
    return SurveyResponse(**defaults)


def make_client_info(**overrides) -> ClientInfo:
    """Create a ClientInfo with sensible defaults."""
    defaults = {
        "company_name": "Test PM Company",
        "door_count": 300,
        "property_count": 20,
        "pms_platform": "AppFolio",
        "operational_model": "va",
        "staff_count": 2,
        "primary_goal": "scale",
    }
    defaults.update(overrides)
    return ClientInfo(**defaults)


def run_pipeline(survey_overrides=None, client_overrides=None):
    """Run the full quick diagnostic pipeline and return all outputs."""
    survey = make_survey(**(survey_overrides or {}))
    client = make_client_info(**(client_overrides or {}))

    adapter = SurveyAdapter()
    wo_metrics, vendor_metrics, portfolio_metrics, doc_analysis = adapter.adapt(survey, client)

    categories = calculate_all_scores(wo_metrics, vendor_metrics, portfolio_metrics, doc_analysis, client)
    overall = calculate_overall_score(categories)
    scores_dict = {cat.key: cat.score for cat in categories}
    scores_dict["overall"] = overall

    findings = generate_key_findings(wo_metrics, vendor_metrics, portfolio_metrics, doc_analysis, client)
    gaps = generate_gaps(categories, wo_metrics, vendor_metrics, doc_analysis, client)
    gap_titles = [g.title for g in gaps]
    projected = calculate_projected_score(overall, gap_titles)
    category_scores_for_tier = {cat.key: cat.score for cat in categories}
    tier = recommend_tier(
        goal=client.primary_goal,
        category_scores=category_scores_for_tier,
        gaps=gap_titles,
        client_info={"door_count": client.door_count, "property_count": client.property_count, "operational_model": client.operational_model},
    )

    return {
        "survey": survey,
        "client": client,
        "wo_metrics": wo_metrics,
        "vendor_metrics": vendor_metrics,
        "portfolio_metrics": portfolio_metrics,
        "doc_analysis": doc_analysis,
        "categories": categories,
        "scores": scores_dict,
        "overall": overall,
        "findings": findings,
        "gaps": gaps,
        "gap_titles": gap_titles,
        "projected": projected,
        "tier": tier,
    }


# ── Trade Coverage Tests ───────────────────────────────────────

class TestTradeCoverage:
    """Verify trade counting and scoring is accurate."""

    def test_all_8_core_no_specialty(self):
        """All 8 core trades selected, 0 specialty → should count as 8/8 core."""
        r = run_pipeline(survey_overrides={
            "trades_covered": ["plumbing", "electrical", "rooter", "appliance_repair",
                               "handyperson", "hvac", "roofing", "pest_control"],
            "vendor_count": 16,
        })
        assert r["wo_metrics"].trades_covered_count == 8, \
            f"Expected 8 trades covered, got {r['wo_metrics'].trades_covered_count}"
        assert len(r["wo_metrics"].missing_trades) == 0, \
            f"Expected 0 missing trades, got {r['wo_metrics'].missing_trades}"

    def test_4_core_2_specialty(self):
        """4 core + 2 specialty → should count as 4/8 core, NOT 6/8."""
        r = run_pipeline(survey_overrides={
            "trades_covered": ["plumbing", "electrical", "hvac", "handyperson",
                               "painting", "landscaping"],
            "vendor_count": 12,
        })
        core_set = {t.lower() for t in CORE_TRADES}
        covered = {t.lower() for t in (r["wo_metrics"].covered_trades or [])}
        core_covered = len(covered & core_set)

        assert core_covered == 4, \
            f"Expected 4 core trades covered, got {core_covered}. " \
            f"Covered: {covered}. Core: {core_set}"

        missing = r["wo_metrics"].missing_trades
        assert len(missing) == 4, \
            f"Expected 4 missing core trades, got {len(missing)}: {missing}"

    def test_0_trades(self):
        """No trades selected → 0/8, all core missing."""
        r = run_pipeline(survey_overrides={
            "trades_covered": [],
            "vendor_count": 0,
        })
        assert r["wo_metrics"].trades_covered_count == 0
        assert len(r["wo_metrics"].missing_trades) >= 8

    def test_vendor_coverage_score_all_core(self):
        """All 8 core trades → vendor coverage score should be >= 80."""
        r = run_pipeline(survey_overrides={
            "trades_covered": ["plumbing", "electrical", "rooter", "appliance_repair",
                               "handyperson", "hvac", "roofing", "pest_control"],
            "vendor_count": 20,
        })
        vc = r["scores"].get("vendor_coverage", 0)
        assert vc >= 80, f"All 8 core trades but vendor coverage only {vc}"

    def test_vendor_coverage_score_half_core(self):
        """4/8 core trades → vendor coverage should be around 40-50, not 75+."""
        r = run_pipeline(survey_overrides={
            "trades_covered": ["plumbing", "electrical", "hvac", "handyperson"],
            "vendor_count": 8,
        })
        vc = r["scores"].get("vendor_coverage", 0)
        assert vc <= 60, f"Only 4/8 core trades but vendor coverage is {vc}"

    def test_specialty_trades_add_bonus_not_penalty(self):
        """All 8 core + 0 specialty should score >= 80. Adding specialty should only increase."""
        r_core_only = run_pipeline(survey_overrides={
            "trades_covered": ["plumbing", "electrical", "rooter", "appliance_repair",
                               "handyperson", "hvac", "roofing", "pest_control"],
            "vendor_count": 16,
        })
        r_core_plus = run_pipeline(survey_overrides={
            "trades_covered": ["plumbing", "electrical", "rooter", "appliance_repair",
                               "handyperson", "hvac", "roofing", "pest_control",
                               "painting", "landscaping"],
            "vendor_count": 20,
        })
        vc_core = r_core_only["scores"]["vendor_coverage"]
        vc_plus = r_core_plus["scores"]["vendor_coverage"]
        assert vc_plus >= vc_core, \
            f"Adding specialty trades decreased score: {vc_core} → {vc_plus}"


# ── Staffing Ratio Tests ──────────────────────────────────────

class TestStaffingRatio:
    """Verify staffing ratio calculations and framing logic."""

    def test_ratio_math(self):
        """doors / staff should be computed correctly."""
        r = run_pipeline(client_overrides={"door_count": 500, "staff_count": 4})
        doors_per = r["client"].door_count / r["client"].staff_count
        assert doors_per == 125.0

    def test_125_is_below_175_benchmark(self):
        """125 doors/coordinator is 71% of 175 benchmark — NOT 'right at'."""
        benchmark = STAFFING_BENCHMARKS.get("va", {}).get("current_benchmark", 175)
        doors_per = 125
        ratio = doors_per / benchmark
        assert ratio < 0.85, \
            f"125/{benchmark} = {ratio:.2f}, should be < 0.85 (below benchmark)"

    def test_200_is_above_175_benchmark(self):
        """200 doors/coordinator is 114% of 175 — in the 'tracking with' band."""
        benchmark = STAFFING_BENCHMARKS.get("va", {}).get("current_benchmark", 175)
        doors_per = 200
        ratio = doors_per / benchmark
        assert 0.85 <= ratio <= 1.15, \
            f"200/{benchmark} = {ratio:.2f}, should be in 0.85-1.15 band"

    def test_300_is_stretched(self):
        """300 doors/coordinator is 171% of 175 — should be 'stretched'."""
        benchmark = STAFFING_BENCHMARKS.get("va", {}).get("current_benchmark", 175)
        doors_per = 300
        ratio = doors_per / benchmark
        assert ratio > 1.15, \
            f"300/{benchmark} = {ratio:.2f}, should be > 1.15 (stretched)"

    def test_tech_model_uses_tech_benchmark(self):
        """Tech model should use 120 benchmark, not 175."""
        benchmark = STAFFING_BENCHMARKS.get("tech", {}).get("current_benchmark", 120)
        assert benchmark == 120, f"Tech benchmark should be 120, got {benchmark}"

    def test_50_doors_1_staff_is_below_benchmark(self):
        """50 doors / 1 coordinator = 50, which is 29% of 175."""
        benchmark = STAFFING_BENCHMARKS.get("va", {}).get("current_benchmark", 175)
        ratio = 50 / benchmark
        assert ratio < 0.85, \
            f"50/{benchmark} = {ratio:.2f}, should trigger 'capacity to grow'"


# ── Response Time Tests ────────────────────────────────────────

class TestResponseTime:
    """Verify response time mapping and scoring."""

    def test_under_1hr_maps_correctly(self):
        r = run_pipeline(survey_overrides={"estimated_response_time": "under_1hr"})
        assert r["wo_metrics"].avg_first_response_hours == 0.5

    def test_next_day_maps_correctly(self):
        r = run_pipeline(survey_overrides={"estimated_response_time": "next_day"})
        assert r["wo_metrics"].avg_first_response_hours == 18.0

    def test_fast_response_scores_high(self):
        r = run_pipeline(survey_overrides={"estimated_response_time": "under_1hr"})
        assert r["scores"]["response_efficiency"] >= 70, \
            f"Under 1hr response but efficiency only {r['scores']['response_efficiency']}"

    def test_slow_response_scores_low(self):
        r = run_pipeline(survey_overrides={"estimated_response_time": "next_day"})
        assert r["scores"]["response_efficiency"] <= 40, \
            f"Next-day response but efficiency is {r['scores']['response_efficiency']}"


# ── After Hours Tests ──────────────────────────────────────────

class TestAfterHours:
    """Verify after-hours scoring."""

    def test_247_scores_high(self):
        r = run_pipeline(survey_overrides={"after_hours_method": "24_7_coverage"})
        assert r["scores"]["after_hours_readiness"] >= 60, \
            f"24/7 coverage but after hours score only {r['scores']['after_hours_readiness']}"

    def test_voicemail_scores_low(self):
        r = run_pipeline(survey_overrides={"after_hours_method": "voicemail_only"})
        assert r["scores"]["after_hours_readiness"] <= 50, \
            f"Voicemail only but after hours score is {r['scores']['after_hours_readiness']}"


# ── Policy Tests ───────────────────────────────────────────────

class TestPolicies:
    """Verify policy-based scoring."""

    def test_all_policies_yes(self):
        """Emergency yes, NTEs yes, SLAs yes → emergency protocols should score high."""
        r = run_pipeline(survey_overrides={
            "has_written_emergency_protocols": "yes",
            "has_defined_ntes": "yes",
            "ntes_are_tiered": True,
            "has_defined_slas": "yes",
        })
        assert r["scores"]["emergency_protocols"] >= 60, \
            f"All policies yes but emergency score only {r['scores']['emergency_protocols']}"

    def test_no_policies(self):
        """All policies no → emergency protocols should score low."""
        r = run_pipeline(survey_overrides={
            "has_written_emergency_protocols": "no",
            "has_defined_ntes": "no",
            "has_defined_slas": "no",
        })
        assert r["scores"]["emergency_protocols"] <= 40, \
            f"No policies but emergency score is {r['scores']['emergency_protocols']}"


# ── Overall Score Tests ────────────────────────────────────────

class TestOverallScore:
    """Verify overall score behaves sensibly across scenarios."""

    def test_best_case_scores_high(self):
        """Everything good → overall should be >= 65."""
        r = run_pipeline(
            survey_overrides={
                "trades_covered": ["plumbing", "electrical", "rooter", "appliance_repair",
                                   "handyperson", "hvac", "roofing", "pest_control"],
                "vendor_count": 20,
                "has_written_emergency_protocols": "yes",
                "has_defined_ntes": "yes",
                "ntes_are_tiered": True,
                "has_defined_slas": "yes",
                "estimated_response_time": "under_1hr",
                "after_hours_method": "24_7_coverage",
            },
            client_overrides={"door_count": 500, "staff_count": 3},
        )
        assert r["overall"] >= 65, \
            f"Best case but overall only {r['overall']}. Scores: {r['scores']}"

    def test_worst_case_scores_low(self):
        """Everything bad → overall should be <= 45."""
        r = run_pipeline(
            survey_overrides={
                "trades_covered": ["plumbing"],
                "vendor_count": 2,
                "has_written_emergency_protocols": "no",
                "has_defined_ntes": "no",
                "has_defined_slas": "no",
                "estimated_response_time": "next_day",
                "after_hours_method": "none",
            },
            client_overrides={"door_count": 200, "staff_count": 8},
        )
        assert r["overall"] <= 45, \
            f"Worst case but overall is {r['overall']}. Scores: {r['scores']}"

    def test_overall_between_0_and_100(self):
        """Overall score should always be in range."""
        for preset in ["under_1hr", "next_day"]:
            r = run_pipeline(survey_overrides={"estimated_response_time": preset})
            assert 0 <= r["overall"] <= 100, f"Overall {r['overall']} out of range"


# ── Projected Score Tests ──────────────────────────────────────

class TestProjectedScore:
    """Verify projected score caps and diminishing returns."""

    def test_projected_never_above_90(self):
        """Projected score should never exceed 90."""
        r = run_pipeline(survey_overrides={
            "trades_covered": ["plumbing"],
            "vendor_count": 2,
            "has_written_emergency_protocols": "no",
            "has_defined_ntes": "no",
            "has_defined_slas": "no",
            "estimated_response_time": "next_day",
            "after_hours_method": "none",
        })
        assert r["projected"] <= 90, \
            f"Projected score {r['projected']} exceeds cap of 90"

    def test_projected_never_below_current(self):
        """Projected should never be lower than current."""
        r = run_pipeline()
        assert r["projected"] >= r["overall"], \
            f"Projected {r['projected']} < current {r['overall']}"

    def test_max_25_point_jump(self):
        """Projected should never jump more than 25 points."""
        r = run_pipeline(survey_overrides={
            "trades_covered": ["plumbing"],
            "vendor_count": 2,
            "has_written_emergency_protocols": "no",
            "has_defined_ntes": "no",
            "has_defined_slas": "no",
            "estimated_response_time": "next_day",
            "after_hours_method": "none",
        })
        jump = r["projected"] - r["overall"]
        assert jump <= 25, \
            f"Score jump of {jump} ({r['overall']} → {r['projected']}) exceeds max of 25"


# ── Findings Tests ─────────────────────────────────────────────

class TestFindings:
    """Verify findings are data-driven and logically consistent."""

    def test_no_document_references_on_quick(self):
        """Findings should never reference PMA, lease, or uploaded documents."""
        r = run_pipeline()
        for f in r["findings"]:
            desc = f.description.lower() if hasattr(f, "description") else (f.get("description", "") or "").lower()
            assert "your pma" not in desc, f"Finding references PMA: {f}"
            assert "your lease" not in desc, f"Finding references lease: {f}"
            assert "pma and lease templates are solid" not in desc, \
                f"Hardcoded fiction in finding: {f}"

    def test_strong_vendor_coverage_finding_when_all_trades(self):
        """All core trades covered → should get a positive vendor finding."""
        r = run_pipeline(survey_overrides={
            "trades_covered": ["plumbing", "electrical", "rooter", "appliance_repair",
                               "handyperson", "hvac", "roofing", "pest_control"],
            "vendor_count": 20,
        })
        titles = [
            (f.title if hasattr(f, "title") else f.get("title", ""))
            for f in r["findings"]
        ]
        assert "Strong Vendor Coverage" in titles or \
               not any("Vendor Coverage Gaps" in t for t in titles), \
            f"All core trades covered but got negative vendor finding: {titles}"

    def test_vendor_gap_finding_when_missing_trades(self):
        """Missing core trades → should get a vendor gap finding."""
        r = run_pipeline(survey_overrides={
            "trades_covered": ["plumbing", "electrical"],
            "vendor_count": 4,
        })
        titles = [
            (f.title if hasattr(f, "title") else f.get("title", ""))
            for f in r["findings"]
        ]
        assert any("Vendor" in t and ("Gap" in t or "Coverage" in t) for t in titles), \
            f"Missing 6 core trades but no vendor gap finding: {titles}"


# ── Gaps Tests ─────────────────────────────────────────────────

class TestGaps:
    """Verify gap details are data-driven."""

    def test_no_hardcoded_fiction_in_gaps(self):
        """Gap details should never contain hardcoded document claims."""
        r = run_pipeline()
        for g in r["gaps"]:
            detail = (g.detail if hasattr(g, "detail") else g.get("detail", "") or "").lower()
            assert "templates are solid" not in detail, \
                f"Hardcoded fiction in gap '{g}': {detail}"
            assert "well-structured" not in detail, \
                f"Hardcoded fiction in gap '{g}': {detail}"

    def test_gaps_produced_for_worst_case(self):
        """Worst-case scenario should produce gaps."""
        r = run_pipeline(survey_overrides={
            "trades_covered": ["plumbing"],
            "vendor_count": 2,
            "has_written_emergency_protocols": "no",
            "has_defined_ntes": "no",
            "has_defined_slas": "no",
            "estimated_response_time": "next_day",
            "after_hours_method": "none",
        })
        assert len(r["gaps"]) >= 1, "Expected at least 1 gap for worst-case scenario"


# ── Tier Tests ─────────────────────────────────────────────────

class TestTier:
    """Verify tier recommendation logic."""

    def test_tier_is_valid_value(self):
        """Tier should always be one of the three valid values."""
        r = run_pipeline()
        assert r["tier"] in ("engage", "direct", "command"), \
            f"Invalid tier: {r['tier']}"

    def test_worst_case_tier_is_engage(self):
        """Worst case should be 'engage' tier."""
        r = run_pipeline(
            survey_overrides={
                "trades_covered": ["plumbing"],
                "vendor_count": 2,
                "has_written_emergency_protocols": "no",
                "has_defined_ntes": "no",
                "has_defined_slas": "no",
                "estimated_response_time": "next_day",
                "after_hours_method": "none",
            },
            client_overrides={"door_count": 200, "staff_count": 8},
        )
        assert r["tier"] == "engage", \
            f"Worst case should be 'engage', got '{r['tier']}'"


# ── Cross-Consistency Tests ────────────────────────────────────

class TestCrossConsistency:
    """Verify outputs are internally consistent."""

    def test_high_vendor_score_no_vendor_gap(self):
        """If vendor coverage scores >= 70, there should be no vendor coverage gap."""
        r = run_pipeline(survey_overrides={
            "trades_covered": ["plumbing", "electrical", "rooter", "appliance_repair",
                               "handyperson", "hvac", "roofing", "pest_control"],
            "vendor_count": 20,
        })
        vc = r["scores"]["vendor_coverage"]
        gap_titles = [
            (g.title if hasattr(g, "title") else g.get("title", ""))
            for g in r["gaps"]
        ]
        if vc >= 70:
            assert "Vendor Coverage" not in gap_titles, \
                f"Vendor coverage score is {vc} but still has Vendor Coverage gap"

    def test_low_response_has_response_gap(self):
        """If response efficiency < 70, should have a response time gap."""
        r = run_pipeline(survey_overrides={"estimated_response_time": "next_day"})
        re_score = r["scores"]["response_efficiency"]
        gap_titles = [
            (g.title if hasattr(g, "title") else g.get("title", ""))
            for g in r["gaps"]
        ]
        if re_score < 70:
            assert "Response Time SLAs" in gap_titles, \
                f"Response efficiency is {re_score} but no Response Time SLA gap"

    def test_findings_and_gaps_dont_contradict(self):
        """A finding saying 'Strong Vendor Coverage' should not coexist with a Vendor Coverage gap."""
        r = run_pipeline(survey_overrides={
            "trades_covered": ["plumbing", "electrical", "rooter", "appliance_repair",
                               "handyperson", "hvac", "roofing", "pest_control"],
            "vendor_count": 20,
        })
        finding_titles = [
            (f.title if hasattr(f, "title") else f.get("title", ""))
            for f in r["findings"]
        ]
        gap_titles = [
            (g.title if hasattr(g, "title") else g.get("title", ""))
            for g in r["gaps"]
        ]

        if "Strong Vendor Coverage" in finding_titles:
            assert "Vendor Coverage" not in gap_titles, \
                "Finding says 'Strong Vendor Coverage' but gap says 'Vendor Coverage'"
