"use client";

import * as React from "react";
import Link from "next/link";

import type {
  DiagnosticInsight,
  DiagnosticStatusResponse,
  DiagnosticTier,
} from "@/lib/types";
import { getDiagnostic, getDiagnosticPdfUrl, getDiagnosticReportUrl } from "@/lib/api";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { AlertTriangle, ArrowRight, Download, FileText } from "lucide-react";

const tierCopy: Record<DiagnosticTier, { label: string; line: string }> = {
  engage: {
    label: "Engage",
    line: "Foundational signals indicate room to formalize vendors, policies, and response cadence.",
  },
  direct: {
    label: "Direct",
    line: "Core operations run; tightening direction, spend controls, and SLAs will raise consistency.",
  },
  command: {
    label: "Command",
    line: "Mature controls and coverage—optimization shifts toward scale, margin, and premium service.",
  },
};

function scoreFromDiagnostic(d: DiagnosticStatusResponse): number {
  if (typeof d.overall_score === "number") return clampScore(d.overall_score);
  const s = d.scores;
  if (!s) return 0;
  if (typeof s.overall === "number") return clampScore(s.overall);
  const vals = Object.values(s).filter(
    (v): v is number => typeof v === "number"
  );
  if (!vals.length) return 0;
  return clampScore(vals.reduce((a, b) => a + b, 0) / vals.length);
}

function clampScore(n: number) {
  return Math.max(0, Math.min(100, Math.round(n)));
}

function ringColor(score: number) {
  if (score >= 70) return "#34ba49";
  if (score >= 50) return "#fdbb00";
  return "#f43f5e";
}

function ScoreRingDark({ score, color }: { score: number; color: string }) {
  const size = 110;
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;

  return (
    <div className="relative">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#333"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={c}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-3xl font-semibold tabular-nums text-white">{score}</span>
      </div>
    </div>
  );
}

function CategoryBar({ name, score, tier, tierCss }: {
  name: string;
  score: number;
  tier: string;
  tierCss: string;
}) {
  const fillColor = tierCss === "ready" ? "bg-vendoroo-success"
    : tierCss === "needs-work" ? "bg-amber-500"
    : "bg-rose-500";
  const pillColor = tierCss === "ready" ? "text-emerald-700 bg-emerald-50"
    : tierCss === "needs-work" ? "text-amber-700 bg-amber-50"
    : "text-rose-700 bg-rose-50";

  return (
    <div className="flex items-center gap-3">
      <span className="w-40 shrink-0 text-sm text-vendoroo-smoke">{name}</span>
      <span className="w-8 shrink-0 text-right text-sm font-semibold tabular-nums text-vendoroo-text">
        {score}
      </span>
      <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-vendoroo-border">
        <div
          className={`absolute inset-y-0 left-0 rounded-full ${fillColor} transition-all duration-700 ease-out`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className={`shrink-0 rounded-md px-2 py-0.5 text-[10px] font-semibold ${pillColor}`}>
        {tier}
      </span>
    </div>
  );
}

const INSIGHT_ICONS: Record<string, string> = {
  scale: "📊",
  clock: "⏱",
  vendors: "🔧",
  moon: "🌙",
  alert: "⚠️",
  dollar: "💰",
  target: "🎯",
};

function QuickResults({
  data,
  score,
}: {
  data: DiagnosticStatusResponse;
  score: number;
}) {
  const insights: DiagnosticInsight[] = data.summary?.insights ?? [];
  const categoryScores = data.summary?.category_scores ?? [];
  const doorCount = data.summary?.door_count ?? 0;
  const staffCount = data.summary?.staff_count ?? 0;
  const staffLabel = data.summary?.staff_label ?? "staff";
  const vendorCount = data.summary?.vendor_count ?? 0;
  const tradesCovered = data.summary?.trades_covered ?? 0;
  const tradesRequired = data.summary?.trades_required ?? 8;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 bg-vendoroo-page px-4 py-12 sm:px-6">

      {/* ── Score ring — current only, no projection ── */}
      <div className="overflow-hidden rounded-2xl bg-[#222] px-6 py-10 text-center shadow-lg sm:px-10">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-neutral-500">
          Operations snapshot
        </p>
        <div className="mt-6 flex justify-center">
          <ScoreRingDark score={score} color={ringColor(score)} />
        </div>
        <p className="mx-auto mt-6 max-w-sm text-sm leading-relaxed text-neutral-400">
          Based on {doorCount} doors, {staffCount} {staffLabel}, and {vendorCount} vendors
          across {tradesCovered} of {tradesRequired} core trades.
        </p>
      </div>

      {/* ── Free trial banner ── */}
      <div className="rounded-xl border border-vendoroo-main/20 bg-vendoroo-tint/10 px-5 py-4 text-center">
        <p className="text-sm font-semibold text-vendoroo-main-dark">
          You qualify for a 90-day free trial
        </p>
        <p className="mt-1 text-xs text-vendoroo-muted">
          Complete your full diagnostic or book a call to get started.
        </p>
      </div>

      {/* ── Insights ── */}
      {insights.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-vendoroo-main">
            What we see in your operation
          </h2>
          <div className="mt-4 flex flex-col gap-4">
            {insights.map((insight, i) => (
              <div
                key={i}
                className="rounded-xl border border-vendoroo-border bg-vendoroo-surface px-5 py-4 shadow-sm"
              >
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 shrink-0 text-lg" aria-hidden>
                    {INSIGHT_ICONS[insight.icon] ?? "📋"}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-vendoroo-text">
                      {insight.title}
                    </p>
                    <p className="mt-1 text-sm leading-relaxed text-vendoroo-muted">
                      {insight.detail}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Categories we can actually score ── */}
      {categoryScores.length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-vendoroo-text">
            Categories scored from your survey
          </h2>
          <div className="mt-3 space-y-2.5">
            {categoryScores.map((cat) => (
              <CategoryBar
                key={cat.key}
                name={cat.name}
                score={cat.score}
                tier={cat.tier}
                tierCss={cat.tier_css}
              />
            ))}
          </div>
        </section>
      )}

      {/* ── Full diagnostic upsell ── */}
      <div className="rounded-xl bg-vendoroo-light px-5 py-5">
        <p className="text-sm font-medium text-vendoroo-text">Want the full picture?</p>
        <p className="mt-1 text-sm leading-relaxed text-vendoroo-muted">
          Upload your work order history and policy documents. We&apos;ll analyze your
          actual data — response times, vendor performance, completion rates, policy gaps —
          and deliver a comprehensive report with specific recommendations.
        </p>
      </div>

      {/* ── CTAs ── */}
      <div className="flex flex-col gap-3 border-t border-vendoroo-border pt-8">
        <Link
          href="/diagnostic/full"
          className={cn(
            buttonVariants({
              className:
                "inline-flex gap-2 rounded-full px-8 py-5 text-sm font-medium uppercase tracking-[-0.02em]",
            })
          )}
        >
          Get your full data-driven analysis
          <ArrowRight className="size-4" />
        </Link>
        <a
          href="https://vendoroo.ai/contact"
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            buttonVariants({
              variant: "outline",
              className:
                "inline-flex rounded-full border-vendoroo-border px-8 py-4 text-sm font-medium uppercase tracking-[-0.02em] text-vendoroo-text hover:bg-vendoroo-light",
            })
          )}
        >
          Book a call
        </a>
      </div>
    </div>
  );
}

export function ResultsView({ id }: { id: string }) {
  const [data, setData] = React.useState<DiagnosticStatusResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    try {
      const res = await getDiagnostic(id);
      setData(res);
      if (res.status === "failed") {
        setError(res.error ?? "This diagnostic could not be completed. Please start again.");
      } else {
        setError(null);
      }
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Unable to load diagnostic results."
      );
    }
  }, [id]);

  React.useEffect(() => {
    void load();
  }, [load]);

  React.useEffect(() => {
    if (!data || data.status !== "processing") return;
    const t = window.setInterval(() => {
      void load();
    }, 2500);
    return () => window.clearInterval(t);
  }, [data, load]);

  if (error && !data) {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <p className="text-vendoroo-muted">{error}</p>
        <Link
          href="/diagnostic"
          className={cn(
            buttonVariants({
              className:
                "mt-6 inline-flex rounded-full px-8 py-4 text-sm font-medium uppercase tracking-[-0.02em]",
            })
          )}
        >
          Return to diagnostic
        </Link>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="mx-auto flex max-w-lg flex-col items-center gap-4 px-4 py-24 text-center">
        <div
          className="size-10 animate-spin rounded-full border-2 border-vendoroo-main border-t-transparent"
          aria-hidden
        />
        <p className="text-sm text-vendoroo-muted">Retrieving your assessment…</p>
      </div>
    );
  }

  if (data.status === "processing" || data.status === "pending") {
    return (
      <div className="mx-auto max-w-lg px-4 py-24 text-center">
        <p className="text-lg text-vendoroo-text">Processing your diagnostic…</p>
        <p className="mt-2 text-sm text-vendoroo-muted">
          Models are scoring vendor coverage, policy discipline, and response
          readiness. This usually finishes within a minute.
        </p>
      </div>
    );
  }

  if (data.status === "failed") {
    return (
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <p className="text-vendoroo-muted">
          {error ?? "This diagnostic could not be completed."}
        </p>
        <Link
          href="/diagnostic"
          className="mt-6 inline-flex h-12 items-center justify-center rounded-full bg-[#222] px-8 text-sm font-medium uppercase tracking-[-0.02em] text-white transition-colors hover:bg-[#039cac]"
        >
          Start over
        </Link>
      </div>
    );
  }

  // ── Derived data ──
  const score = scoreFromDiagnostic(data);
  // Quick path gets its own focused rendering
  if (data.diagnostic_type === "quick") {
    return <QuickResults data={data} score={score} />;
  }

  const projectedScore = clampScore(data.summary?.projected_score ?? score);
  const tier: DiagnosticTier = data.tier ?? "engage";
  const tierInfo = tierCopy[tier];
  const findings = data.key_findings ?? [];
  const gaps = data.gaps ?? [];
  const categoryScores = data.summary?.category_scores ?? [];
  const isFullComplete = Boolean(data.pdf_url);
  const pdfHref = getDiagnosticPdfUrl(id);
  const reportHref = getDiagnosticReportUrl(id);

  const worstCategories = [...categoryScores]
    .sort((a, b) => a.score - b.score)
    .slice(0, 3);

  const PAIN_LABELS: Record<string, string> = {
    vendor_reliability: "vendor reliability",
    response_times: "response times",
    cost_control: "cost control",
    compliance_documentation: "compliance/documentation",
    scaling_team: "scaling the team",
    owner_communication: "owner communication",
    after_hours_coverage: "after-hours coverage",
    reporting_visibility: "reporting/visibility",
  };
  const painPoints = data.summary?.pain_points ?? [];
  const painLabels = painPoints.map((p) => PAIN_LABELS[p] ?? p).filter(Boolean);

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-8 bg-vendoroo-page px-4 py-12 sm:px-6">

      {/* ── Before → After hero (the golden nugget) ── */}
      <div className="overflow-hidden rounded-2xl bg-[#222] px-6 py-10 text-center shadow-lg sm:px-10">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-neutral-500">
          Operations readiness
        </p>

        <div className="mt-6 flex items-center justify-center gap-6 sm:gap-10">
          <div className="flex flex-col items-center">
            <ScoreRingDark score={score} color={ringColor(score)} />
            <span className="mt-2 text-[11px] font-medium uppercase tracking-wider text-neutral-500">
              Today
            </span>
          </div>

          <div className="flex flex-col items-center gap-1">
            <span className="text-2xl text-neutral-600" aria-hidden>
              →
            </span>
          </div>

          <div className="flex flex-col items-center">
            <ScoreRingDark score={projectedScore} color="#039cac" />
            <span className="mt-2 text-[11px] font-semibold uppercase tracking-wider text-[#FDBB00]">
              With Vendoroo
            </span>
          </div>
        </div>

        <div className="mt-8">
          <span className="inline-block rounded-full bg-vendoroo-main px-4 py-1.5 text-xs font-bold uppercase tracking-widest text-white">
            {tierInfo.label}
          </span>
          <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-neutral-400">
            {tierInfo.line}
          </p>
        </div>
      </div>

      {/* ── Free trial qualifying banner ── */}
      <div className="rounded-xl border border-vendoroo-main/20 bg-vendoroo-tint/10 px-5 py-4 text-center">
        <p className="text-sm font-semibold text-vendoroo-main-dark">
          You qualify for a 90-day free trial
        </p>
        <p className="mt-1 text-xs text-vendoroo-muted">
          Complete your full diagnostic or book a call to get started.
        </p>
      </div>

      {/* ── Areas that need attention (worst 3 categories) ── */}
      {worstCategories.length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-vendoroo-text">
            Areas that need attention
          </h2>
          <div className="mt-3 space-y-2.5">
            {worstCategories.map((cat) => (
              <CategoryBar
                key={cat.key}
                name={cat.name}
                score={cat.score}
                tier={cat.tier}
                tierCss={cat.tier_css}
              />
            ))}
          </div>
          {categoryScores.length > 3 && (
            <p className="mt-2 text-xs text-vendoroo-muted">
              + {categoryScores.length - 3} more categories in your full report
            </p>
          )}
        </section>
      )}

      {/* ── Findings preview (titles only) ── */}
      {findings.length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-vendoroo-text">
            {findings.length} finding{findings.length !== 1 ? "s" : ""} identified
          </h2>
          <ul className="mt-3 space-y-1.5">
            {findings.map((f, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-vendoroo-smoke">
                <span className={`size-1.5 shrink-0 rounded-full ${
                  f.color?.includes("red") ? "bg-rose-500"
                  : f.color?.includes("amber") ? "bg-amber-500"
                  : f.color?.includes("green") ? "bg-emerald-500"
                  : "bg-vendoroo-main"
                }`} />
                {f.title}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ── Gaps stat ── */}
      {gaps.length > 0 && (
        <div className="flex items-center gap-3 rounded-xl border border-vendoroo-border bg-vendoroo-surface px-5 py-4 shadow-sm">
          <span className="flex size-10 items-center justify-center rounded-full bg-rose-50 text-rose-600">
            <AlertTriangle className="size-5" />
          </span>
          <div>
            <p className="text-sm font-medium text-vendoroo-text">
              {gaps.length} operational gap{gaps.length !== 1 ? "s" : ""} identified
            </p>
            {painLabels.length > 0 ? (
              <p className="text-xs text-vendoroo-muted">
                Prioritized by your focus areas: {painLabels.join(" · ")}
              </p>
            ) : (
              <p className="text-xs text-vendoroo-muted">
                Each gap includes a specific remediation plan from your AI Adoption Advisor
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── CTAs ── */}
      <div className="flex flex-col gap-3 border-t border-vendoroo-border pt-8">
        {/* Full diagnostic: show report + PDF links */}
        {isFullComplete && (
          <>
            <a
              href={reportHref}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                buttonVariants({
                  className:
                    "inline-flex gap-2 rounded-full px-8 py-5 text-sm font-medium uppercase tracking-[-0.02em]",
                })
              )}
            >
              <FileText className="size-4" />
              View full report
            </a>
            <a
              href={pdfHref}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                buttonVariants({
                  variant: "outline",
                  className:
                    "inline-flex gap-2 rounded-full border-vendoroo-border px-8 py-4 text-sm font-medium uppercase tracking-[-0.02em] text-vendoroo-text hover:bg-vendoroo-light",
                })
              )}
            >
              <Download className="size-4" />
              Download PDF
            </a>
          </>
        )}

        {/* Always: Book a call */}
        <a
          href="https://vendoroo.ai/contact"
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            buttonVariants({
              variant: isFullComplete ? "outline" : "default",
              className: cn(
                "inline-flex rounded-full px-8 text-sm font-medium uppercase tracking-[-0.02em]",
                isFullComplete
                  ? "border-vendoroo-border py-4 text-vendoroo-text hover:bg-vendoroo-light"
                  : "py-5"
              ),
            })
          )}
        >
          Book a call
        </a>

      </div>

      {/* ── What's in the full report ── */}
      <div className="rounded-xl bg-vendoroo-light px-5 py-4">
        <p className="text-xs font-medium text-vendoroo-smoke">
          Your full report includes
        </p>
        <p className="mt-1 text-xs leading-relaxed text-vendoroo-muted">
          8 category scores · benchmark comparisons · impact projections ·
          gap analysis with remediation plans · tier recommendation ·
          AI adoption roadmap · downloadable PDF
        </p>
      </div>
    </div>
  );
}
