#!/usr/bin/env python3
"""
Diagnostic output validator — runs presets and checks every output for logical consistency.

This catches: wrong math, mismatched counts, nonsensical text, threshold errors.

Usage:
    python validate_diagnostic.py                    # Run all presets against localhost
    python validate_diagnostic.py --api https://...  # Run against production
    python validate_diagnostic.py --preset mid       # Run one preset
    python validate_diagnostic.py --verbose          # Show all checks, not just failures
"""

import argparse
import json
import sys
import requests
from dataclasses import dataclass, field

DEFAULT_API = "http://localhost:8000"

# ── Presets ────────────────────────────────────────────────────

PRESETS = {
    "best_case": {
        "desc": "500 doors, 3 staff, all trades, all policies, fast response, 24/7 coverage",
        "doors": 500, "properties": 20, "staff": 3, "pms": "AppFolio",
        "model": "va", "goal": "scale", "vendors": 30,
        "trades": ["plumbing", "electrical", "rooter", "appliance_repair",
                   "handyperson", "hvac", "roofing", "pest_control",
                   "painting", "flooring", "landscaping", "pool_spa", "locksmith", "cleaning_turnover"],
        "emergency": "yes", "ntes": "yes", "slas": "yes",
        "response_time": "under_1hr", "completion_time": "1_3days",
        "after_hours": "24_7_coverage",
    },
    "worst_case": {
        "desc": "200 doors, 8 staff, 3 trades, no policies, next-day response, voicemail",
        "doors": 200, "properties": 40, "staff": 8, "pms": "Other",
        "model": "va", "goal": "optimize", "vendors": 5,
        "trades": ["plumbing", "electrical", "hvac"],
        "emergency": "no", "ntes": "no", "slas": "no",
        "response_time": "next_day", "completion_time": "14plus",
        "after_hours": "voicemail_only",
    },
    "mid_range": {
        "desc": "350 doors, 2 staff, 6 core trades, some policies, 4-12hr response, answering service",
        "doors": 350, "properties": 30, "staff": 2, "pms": "Buildium",
        "model": "va", "goal": "scale", "vendors": 15,
        "trades": ["plumbing", "electrical", "hvac", "appliance_repair",
                   "handyperson", "roofing"],
        "emergency": "unsure", "ntes": "yes", "slas": "no",
        "response_time": "4_12hrs", "completion_time": "3_7days",
        "after_hours": "answering_service",
    },
    "small_portfolio": {
        "desc": "50 doors, 1 staff, 4 trades, no policies",
        "doors": 50, "properties": 10, "staff": 1, "pms": "Rentvine",
        "model": "va", "goal": "elevate", "vendors": 8,
        "trades": ["plumbing", "electrical", "hvac", "handyperson"],
        "emergency": "no", "ntes": "no", "slas": "no",
        "response_time": "same_day", "completion_time": "7_14days",
        "after_hours": "on_call_rotation",
    },
    "tech_model": {
        "desc": "400 doors, 4 techs, 10 trades, all policies, fast response",
        "doors": 400, "properties": 5, "staff": 4, "pms": "Yardi Voyager",
        "model": "tech", "goal": "optimize", "vendors": 20,
        "trades": ["plumbing", "electrical", "rooter", "appliance_repair",
                   "handyperson", "hvac", "roofing", "pest_control",
                   "painting", "flooring"],
        "emergency": "yes", "ntes": "yes", "slas": "yes",
        "response_time": "1_4hrs", "completion_time": "1_3days",
        "after_hours": "24_7_coverage",
    },
    "overstaffed": {
        "desc": "100 doors, 5 staff = 20 doors/person, way below benchmark",
        "doors": 100, "properties": 10, "staff": 5, "pms": "AppFolio",
        "model": "va", "goal": "optimize", "vendors": 10,
        "trades": ["plumbing", "electrical", "hvac", "appliance_repair",
                   "handyperson", "roofing", "pest_control", "rooter"],
        "emergency": "yes", "ntes": "yes", "slas": "yes",
        "response_time": "under_1hr", "completion_time": "1_3days",
        "after_hours": "24_7_coverage",
    },
    "stretched": {
        "desc": "600 doors, 2 staff = 300 doors/person, way above benchmark",
        "doors": 600, "properties": 50, "staff": 2, "pms": "AppFolio",
        "model": "va", "goal": "scale", "vendors": 20,
        "trades": ["plumbing", "electrical", "hvac", "appliance_repair",
                   "handyperson", "hvac", "roofing", "pest_control"],
        "emergency": "no", "ntes": "no", "slas": "no",
        "response_time": "next_day", "completion_time": "14plus",
        "after_hours": "voicemail_only",
    },
    "all_core_no_specialty": {
        "desc": "All 8 core trades, 0 specialty — should be full core coverage",
        "doors": 300, "properties": 20, "staff": 2, "pms": "AppFolio",
        "model": "va", "goal": "scale", "vendors": 16,
        "trades": ["plumbing", "electrical", "rooter", "appliance_repair",
                   "handyperson", "hvac", "roofing", "pest_control"],
        "emergency": "no", "ntes": "no", "slas": "no",
        "response_time": "4_12hrs", "completion_time": "3_7days",
        "after_hours": "answering_service",
    },
    "4_core_2_specialty": {
        "desc": "4 core + 2 specialty — should say 4 of 8 core, not 6 of 8",
        "doors": 300, "properties": 20, "staff": 2, "pms": "AppFolio",
        "model": "va", "goal": "scale", "vendors": 12,
        "trades": ["plumbing", "electrical", "hvac", "handyperson",
                   "painting", "landscaping"],
        "emergency": "no", "ntes": "no", "slas": "no",
        "response_time": "4_12hrs", "completion_time": "3_7days",
        "after_hours": "answering_service",
    },
    "disqualified": {
        "desc": "15 doors — should be blocked by under-25 gate",
        "doors": 15, "properties": 5, "staff": 1, "pms": "Other",
        "model": "va", "goal": "scale", "vendors": 3,
        "trades": ["plumbing", "electrical"],
        "emergency": "no", "ntes": "no", "slas": "no",
        "response_time": "next_day", "completion_time": "14plus",
        "after_hours": "none",
    },
}

# ── Benchmark references for validation ────────────────────────

STAFFING_BENCHMARKS = {
    "va": {"current_benchmark": 175, "vendoroo_benchmark": 350},
    "tech": {"current_benchmark": 120, "vendoroo_benchmark": 250},
}

CORE_TRADES = {"plumbing", "electrical", "rooter", "appliance_repair",
               "handyperson", "hvac", "roofing", "pest_control"}

# Note: frontend uses underscores, backend uses spaces — normalize both ways
CORE_TRADES_NORMALIZED = {t.replace("_", " ") for t in CORE_TRADES} | CORE_TRADES

SPECIALTY_TRADES = {"painting", "flooring", "landscaping", "pool_spa",
                    "locksmith", "cleaning_turnover"}

RESPONSE_TIME_MAP = {
    "under_1hr": 0.5, "1_4hrs": 2.5, "4_12hrs": 8.0,
    "same_day": 6.0, "next_day": 18.0,
}

# ── Validation engine ──────────────────────────────────────────

@dataclass
class Check:
    name: str
    passed: bool
    detail: str

@dataclass
class PresetResult:
    preset: str
    desc: str
    success: bool = True
    checks: list = field(default_factory=list)
    error: str = None
    raw: dict = None

    def add(self, name: str, passed: bool, detail: str = ""):
        self.checks.append(Check(name, passed, detail))
        if not passed:
            self.success = False


def run_quick(api: str, preset_name: str, cfg: dict) -> PresetResult:
    """Run a quick diagnostic and validate the output."""
    result = PresetResult(preset=preset_name, desc=cfg["desc"])

    payload = {
        "lead": {
            "name": f"Validate {preset_name}",
            "email": f"validate_{preset_name}@test.com",
            "company": f"Test {preset_name}",
            "terms_accepted": True,
        },
        "survey": {
            "door_count": cfg["doors"],
            "property_count": cfg["properties"],
            "pms_platform": cfg["pms"],
            "staff_count": cfg["staff"],
            "vendor_count": cfg["vendors"],
            "trades_covered": cfg["trades"],
            "has_written_emergency_protocols": cfg["emergency"],
            "has_defined_ntes": cfg["ntes"],
            "ntes_are_tiered": cfg["ntes"] == "yes",
            "has_defined_slas": cfg["slas"],
            "estimated_response_time": cfg["response_time"],
            "estimated_completion_time": cfg["completion_time"],
            "after_hours_method": cfg["after_hours"],
            "primary_goal": cfg["goal"],
            "pain_points": [],
        },
        "client_info": {
            "company_name": f"Test {preset_name}",
            "door_count": cfg["doors"],
            "property_count": cfg["properties"],
            "pms_platform": cfg["pms"],
            "operational_model": cfg["model"],
            "staff_count": cfg["staff"],
            "primary_goal": cfg["goal"],
        },
    }

    try:
        resp = requests.post(f"{api}/api/v1/diagnostic/quick", json=payload, timeout=30)
    except Exception as e:
        result.error = f"Request failed: {e}"
        result.success = False
        return result

    if resp.status_code != 200:
        result.error = f"HTTP {resp.status_code}: {resp.text[:300]}"
        result.success = False
        return result

    data = resp.json()
    result.raw = data
    validate_quick_output(result, data, cfg)
    return result


def validate_quick_output(result: PresetResult, data: dict, cfg: dict):
    """Run all validation checks on a quick diagnostic output."""

    scores = data.get("scores", {})
    summary = data.get("summary", {})
    findings = data.get("key_findings", [])
    gaps = data.get("gaps", [])
    overall = data.get("overall_score")
    tier = data.get("tier")
    category_scores = summary.get("category_scores", [])
    insights = summary.get("insights", [])

    doors = cfg["doors"]
    staff = cfg["staff"]
    model = cfg["model"]
    doors_per = doors / max(1, staff)
    benchmark = STAFFING_BENCHMARKS.get(model, {}).get("current_benchmark", 175)

    input_trades = set(cfg["trades"])
    input_core = input_trades & CORE_TRADES
    input_specialty = input_trades & SPECIALTY_TRADES

    # ── Basic structural checks ──

    result.add("has_overall_score",
               overall is not None and isinstance(overall, (int, float)),
               f"overall_score = {overall}")

    result.add("score_range_0_100",
               overall is not None and 0 <= overall <= 100,
               f"overall_score = {overall}")

    result.add("has_summary",
               summary is not None and len(summary) > 0,
               f"summary keys: {list(summary.keys()) if summary else 'none'}")

    # ── Quick path should NOT have tier ──

    result.add("no_tier_on_quick",
               tier is None,
               f"tier = {tier} (should be None for quick diagnostic)")

    # ── Quick path should NOT have projected score ──

    projected = summary.get("projected_score")
    result.add("no_projected_score_on_quick",
               projected is None,
               f"projected_score = {projected} (should be None for quick)")

    # ── Quick path should NOT show document-dependent categories ──

    doc_categories = {"documentation_quality", "policy_completeness", "operational_consistency"}
    shown_keys = {cat["key"] for cat in category_scores}
    doc_shown = shown_keys & doc_categories
    result.add("no_fake_doc_categories",
               len(doc_shown) == 0,
               f"Document-dependent categories shown: {doc_shown}" if doc_shown else "None shown")

    # ── Trade count accuracy ──

    summary_trades_covered = summary.get("trades_covered")
    summary_trades_required = summary.get("trades_required")

    if summary_trades_covered is not None:
        result.add("core_trade_count_matches_input",
                   summary_trades_covered == len(input_core),
                   f"Summary says {summary_trades_covered} core trades covered, "
                   f"but input has {len(input_core)} core trades: {input_core}")

    if summary_trades_required is not None:
        result.add("required_trades_is_8",
                   summary_trades_required == 8,
                   f"trades_required = {summary_trades_required} (should be 8)")

    # ── Vendor coverage score should reflect core trades ──

    vc_score = scores.get("vendor_coverage")
    if vc_score is not None:
        core_pct = len(input_core) / 8
        # Core coverage gives up to 80 points, specialty up to 20
        expected_core_points = round(core_pct * 80)
        specialty_pct = len(input_specialty) / max(1, len(SPECIALTY_TRADES))
        expected_specialty_points = round(specialty_pct * 20)
        expected_total = min(100, expected_core_points + expected_specialty_points)

        # Allow ±10 tolerance for rounding and edge cases
        result.add("vendor_coverage_score_reasonable",
                   abs(vc_score - expected_total) <= 10,
                   f"Vendor coverage score = {vc_score}, expected ~{expected_total} "
                   f"({len(input_core)}/8 core = {expected_core_points}pts, "
                   f"{len(input_specialty)}/{len(SPECIALTY_TRADES)} specialty = {expected_specialty_points}pts)")

    # ── Staffing insight accuracy ──

    for insight in insights:
        title = insight.get("title", "")
        detail = insight.get("detail", "")

        # Check staffing ratio claims
        if "doors per" in title.lower():
            claimed_ratio = None
            for word in title.split():
                try:
                    claimed_ratio = int(word)
                    break
                except ValueError:
                    continue

            if claimed_ratio is not None:
                result.add("staffing_ratio_correct",
                           claimed_ratio == int(doors_per),
                           f"Insight claims {claimed_ratio} doors/staff, "
                           f"actual is {int(doors_per)} ({doors} doors / {staff} staff)")

        # Check benchmark references
        if "benchmark" in detail.lower() and str(benchmark) in detail:
            result.add("benchmark_value_correct",
                       True,
                       f"Correctly references benchmark of {benchmark}")

        # Validate staffing framing
        if "right at" in detail.lower() or "near" in detail.lower():
            ratio_pct = doors_per / benchmark
            result.add("near_benchmark_framing_accurate",
                       0.85 <= ratio_pct <= 1.15,
                       f"Says 'near benchmark' but ratio is {doors_per}/{benchmark} = {ratio_pct:.0%}")

        if "stretched" in title.lower():
            result.add("stretched_framing_accurate",
                       doors_per > benchmark * 1.15,
                       f"Says 'stretched' but {int(doors_per)} doors/staff vs {benchmark} benchmark "
                       f"= {doors_per/benchmark:.0%}")

        if "capacity to grow" in title.lower() or "capacity to grow" in detail.lower():
            result.add("growth_capacity_framing_accurate",
                       doors_per < benchmark * 0.85,
                       f"Says 'capacity to grow' but {int(doors_per)} doors/staff vs {benchmark} benchmark "
                       f"= {doors_per/benchmark:.0%}")

        # Check response time claims
        if "hour average first response" in title.lower():
            expected_hrs = RESPONSE_TIME_MAP.get(cfg["response_time"])
            if expected_hrs is not None:
                claimed_hrs = None
                for part in title.replace("-", " ").split():
                    try:
                        claimed_hrs = float(part)
                        break
                    except ValueError:
                        continue

                if claimed_hrs is not None:
                    result.add("response_time_matches_input",
                               abs(claimed_hrs - expected_hrs) < 0.1,
                               f"Insight claims {claimed_hrs}hr, expected {expected_hrs}hr "
                               f"from input '{cfg['response_time']}'")

        # Check trade coverage claims
        if "no vendor coverage for" in title.lower():
            # Verify the missing trades mentioned are actually missing from core
            for trade_name in CORE_TRADES:
                display_name = trade_name.replace("_", " ").title()
                if display_name.lower() in title.lower():
                    result.add(f"missing_trade_{trade_name}_actually_missing",
                               trade_name not in input_trades,
                               f"Says missing {display_name} but it was in input trades")

        if "across all core trades" in title.lower():
            result.add("full_coverage_claim_accurate",
                       len(input_core) >= 8,
                       f"Claims full core coverage but only {len(input_core)}/8 core trades selected")

    # ── After-hours insight matches input ──

    after_method = cfg["after_hours"]
    after_insight_found = False
    for insight in insights:
        title = insight.get("title", "").lower()
        if "after-hours" in title or "after hours" in title or "answering service" in title or "on-call" in title:
            after_insight_found = True

            if after_method in ("voicemail_only", "none"):
                result.add("after_hours_insight_matches_voicemail",
                           "wait" in title or "morning" in title or "voicemail" in insight.get("detail", "").lower(),
                           f"After-hours method is {after_method} but insight title is: {insight['title']}")

            elif after_method == "answering_service":
                result.add("after_hours_insight_matches_answering",
                           "answering" in title or "can't act" in title,
                           f"After-hours method is {after_method} but insight title is: {insight['title']}")

            elif after_method == "on_call_rotation":
                result.add("after_hours_insight_matches_oncall",
                           "on-call" in title or "rotation" in title,
                           f"After-hours method is {after_method} but insight title is: {insight['title']}")

            elif after_method == "24_7_coverage":
                # Should NOT show an after-hours insight if they have 24/7
                result.add("no_after_hours_insight_with_247",
                           False,
                           f"Has 24/7 coverage but still showing after-hours insight: {insight['title']}")

    if after_method == "24_7_coverage":
        result.add("no_after_hours_insight_with_247",
                   not after_insight_found,
                   "Should not show after-hours insight when method is 24/7 coverage")

    # ── Policy insights match inputs ──

    for insight in insights:
        title = insight.get("title", "").lower()

        if "emergency protocol" in title and cfg["emergency"] == "yes":
            result.add("no_emergency_insight_when_has_protocols",
                       False,
                       "Says no emergency protocols but input says yes")

        if "not-to-exceed" in title or "nte" in title.lower():
            if cfg["ntes"] == "yes":
                # Should only show flat NTE insight, not "no NTE"
                result.add("nte_insight_matches_input",
                           "flat" in title,
                           f"Has NTEs but showing: {insight['title']}")

        if "vendor accountability" in title or "sla" in title:
            if cfg["slas"] == "yes":
                result.add("no_sla_insight_when_has_slas",
                           False,
                           "Says no SLAs but input says yes")

    # ── Score sanity checks ──

    if overall is not None:
        # Best case should score high
        if cfg.get("emergency") == "yes" and cfg.get("ntes") == "yes" and cfg.get("slas") == "yes":
            if len(input_core) >= 7 and cfg["response_time"] in ("under_1hr", "1_4hrs"):
                result.add("best_case_scores_high",
                           overall >= 65,
                           f"Has all policies, good coverage, fast response but scores only {overall}")

        # Worst case should score low
        if cfg.get("emergency") == "no" and cfg.get("ntes") == "no" and cfg.get("slas") == "no":
            if len(input_core) <= 3 and cfg["response_time"] in ("next_day",):
                result.add("worst_case_scores_low",
                           overall <= 50,
                           f"No policies, poor coverage, slow response but scores {overall}")

    # ── Findings should not reference documents on quick path ──

    for f in findings:
        title = f.get("title", "").lower() if isinstance(f, dict) else str(f).lower()
        desc = f.get("description", "").lower() if isinstance(f, dict) else ""

        result.add(f"finding_no_doc_reference: {title[:30]}",
                   "your pma" not in desc and "your lease" not in desc
                   and "pma and lease" not in desc and "documents were reviewed" not in desc,
                   f"Finding '{title}' references uploaded documents on quick path: {desc[:80]}")

    # ── Gaps should not reference documents on quick path ──

    for g in gaps:
        detail = g.get("detail", "").lower() if isinstance(g, dict) else ""

        result.add(f"gap_no_doc_fiction: {g.get('title', '?')[:30]}",
                   "templates are solid" not in detail
                   and "pma reviewed" not in detail
                   and "lease reviewed" not in detail
                   and "well-structured" not in detail,
                   f"Gap references document analysis on quick path: {detail[:80]}")


def print_results(results: list[PresetResult], verbose: bool = False):
    """Print validation results."""
    total_presets = len(results)
    passed_presets = sum(1 for r in results if r.success)
    total_checks = sum(len(r.checks) for r in results)
    passed_checks = sum(sum(1 for c in r.checks if c.passed) for r in results)

    print(f"\n{'='*70}")
    print(f"  DIAGNOSTIC VALIDATION RESULTS")
    print(f"  {passed_presets}/{total_presets} presets passed | {passed_checks}/{total_checks} checks passed")
    print(f"{'='*70}\n")

    for r in results:
        status = "✅" if r.success else "❌"
        print(f"{status} {r.preset}: {r.desc}")

        if r.error:
            print(f"   ⚠️  ERROR: {r.error}")
            continue

        failed = [c for c in r.checks if not c.passed]
        passed = [c for c in r.checks if c.passed]

        if verbose:
            for c in passed:
                print(f"   ✅ {c.name}")
                if c.detail:
                    print(f"      {c.detail}")

        for c in failed:
            print(f"   ❌ {c.name}")
            if c.detail:
                print(f"      {c.detail}")

        if not verbose and not failed:
            print(f"   All {len(passed)} checks passed")

        print()

    # Summary
    if passed_presets == total_presets:
        print("🎉 All presets passed validation.\n")
    else:
        failed_presets = [r.preset for r in results if not r.success]
        print(f"🔴 {len(failed_presets)} preset(s) failed: {', '.join(failed_presets)}\n")


def main():
    parser = argparse.ArgumentParser(description="Validate diagnostic outputs at scale")
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--preset", choices=list(PRESETS.keys()), help="Run one preset")
    parser.add_argument("--verbose", action="store_true", help="Show all checks")
    args = parser.parse_args()

    presets_to_run = {args.preset: PRESETS[args.preset]} if args.preset else PRESETS

    print(f"\nRunning {len(presets_to_run)} preset(s) against {args.api}...")

    results = []
    for name, cfg in presets_to_run.items():
        print(f"  Running {name}...", end=" ", flush=True)
        r = run_quick(args.api, name, cfg)
        print("done" if r.success else "FAILED")
        results.append(r)

    print_results(results, verbose=args.verbose)

    sys.exit(0 if all(r.success for r in results) else 1)


if __name__ == "__main__":
    main()
