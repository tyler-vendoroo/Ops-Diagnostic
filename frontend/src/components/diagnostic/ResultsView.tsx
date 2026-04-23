"use client";

import * as React from "react";
import Link from "next/link";

import type {
  DiagnosticInsight,
  DiagnosticStatusResponse,
  DiagnosticTier,
} from "@/lib/types";
import { getDiagnostic } from "@/lib/api";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ArrowRight } from "lucide-react";

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
          You qualify for 90 days free
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

      {/* ── Hidden category explanation ── */}
      <div className="rounded-lg border border-vendoroo-border/60 bg-vendoroo-light/50 px-4 py-3">
        <p className="text-xs leading-relaxed text-vendoroo-muted">
          Your overall score includes 3 additional categories —{" "}
          <span className="font-medium text-vendoroo-smoke">Documentation Quality</span>,{" "}
          <span className="font-medium text-vendoroo-smoke">Policy Completeness</span>, and{" "}
          <span className="font-medium text-vendoroo-smoke">Operational Consistency</span>{" "}
          — that require your actual documents and work order data to score accurately.{" "}
          <Link href="/diagnostic/full" className="font-medium text-vendoroo-main hover:underline">
            Upload your files
          </Link>{" "}
          to get the full picture.
        </p>
      </div>

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

function StatCard({ value, label, isBad }: { value: string; label: string; isBad: boolean }) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-vendoroo-border bg-vendoroo-surface px-3 py-5 text-center">
      <span className={`text-xl font-bold tabular-nums ${isBad ? "text-rose-500" : "text-emerald-500"}`}>
        {value}
      </span>
      <span className="mt-1 text-[10px] font-medium uppercase tracking-wider text-vendoroo-muted">
        {label}
      </span>
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
  const gaps = data.gaps ?? [];
  const woMetrics = data.summary?.wo_metrics ?? {};
  const benchmarkRows = data.summary?.benchmark_rows ?? [];
  const repeatUnitsObj = data.summary?.repeat_units ?? {};
  const repeatUnits = Object.entries(repeatUnitsObj)
    .sort(([, a], [, b]) => ((b as { wo_count?: number }).wo_count ?? 0) - ((a as { wo_count?: number }).wo_count ?? 0))
    .filter(([addr]) => addr && addr !== "Unknown" && addr.trim() !== "");

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-10 bg-vendoroo-page px-4 py-12 sm:px-6">

      {/* ── 1. Hero card ── */}
      <div className="overflow-hidden rounded-2xl bg-[#1a1a2e] px-6 py-10 text-center shadow-xl sm:px-10">
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-neutral-500">
          Operations Analysis
        </p>
        <p className="mt-2 text-lg font-semibold text-white">
          {data.summary?.company_name}
        </p>

        <div className="mt-8 flex items-center justify-center gap-6 sm:gap-10">
          <div className="flex flex-col items-center">
            <ScoreRingDark score={score} color={ringColor(score)} />
            <span className="mt-2 text-[11px] font-medium uppercase tracking-wider text-neutral-500">
              Today
            </span>
          </div>
          <span className="text-2xl text-neutral-600" aria-hidden>→</span>
          <div className="flex flex-col items-center">
            <ScoreRingDark score={projectedScore} color="#039cac" />
            <span className="mt-2 text-[11px] font-semibold uppercase tracking-wider text-[#039cac]">
              With Vendoroo
            </span>
          </div>
        </div>

        <p className="mx-auto mt-8 max-w-md text-xs leading-relaxed text-neutral-500">
          Based on {(woMetrics.total_work_orders ?? 0).toLocaleString()} work orders
          {woMetrics.months_spanned ? ` across ${Math.round(woMetrics.months_spanned)} months` : ""}
          {" · "}{data.summary?.door_count ?? 0} doors
          {" · "}{data.summary?.staff_count ?? 0} {data.summary?.staff_label ?? "staff"}
        </p>
      </div>

      {/* ── 2. Benchmark table ── */}
      {benchmarkRows.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-vendoroo-main">
            Current Operations Analysis
          </h2>
          <p className="mt-1 text-xs text-vendoroo-muted">
            Your performance compared to similar portfolios using AI maintenance coordination
          </p>
          <div className="mt-4 overflow-hidden rounded-xl border border-vendoroo-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#1a1a2e] text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
                  <th className="px-4 py-3">Metric</th>
                  <th className="px-4 py-3">Your Current</th>
                  <th className="px-4 py-3">Vendoroo Avg.</th>
                  <th className="px-4 py-3">Top Performers</th>
                </tr>
              </thead>
              <tbody>
                {benchmarkRows.map((row, i) => (
                  <tr key={i} className={i % 2 === 0 ? "bg-vendoroo-surface" : "bg-vendoroo-light/30"}>
                    <td className="px-4 py-3 text-xs font-medium text-vendoroo-smoke">{row.metric}</td>
                    <td className={`px-4 py-3 text-xs font-semibold ${
                      row.current_css === "val-bad" ? "text-rose-500" :
                      row.current_css === "val-good" ? "text-emerald-500" :
                      "text-vendoroo-text"
                    }`}>
                      {row.current_value}
                    </td>
                    <td className="px-4 py-3 text-xs text-vendoroo-muted">{row.vendoroo_avg}</td>
                    <td className="px-4 py-3 text-xs font-medium text-emerald-500">{row.top_performers}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="border-t border-vendoroo-border bg-vendoroo-light/50 px-4 py-2">
              <p className="text-[10px] italic text-vendoroo-muted">
                Based on uploaded work order history.
              </p>
            </div>
          </div>
        </section>
      )}

      {/* ── 3. Three headline stat cards ── */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard
          value={woMetrics.avg_first_response_hours != null
            ? `${woMetrics.avg_first_response_hours}hr`
            : "N/A"}
          label="Avg. First Response"
          isBad={woMetrics.avg_first_response_hours != null && woMetrics.avg_first_response_hours > 4}
        />
        <StatCard
          value={`${woMetrics.open_wo_rate_pct ?? 0}%`}
          label="Open WO Rate"
          isBad={(woMetrics.open_wo_rate_pct ?? 0) > 15}
        />
        <StatCard
          value={`${woMetrics.trades_covered_count ?? 0}/${woMetrics.trades_required_count ?? 8}`}
          label="Core Trade Coverage"
          isBad={(woMetrics.trades_covered_count ?? 0) < (woMetrics.trades_required_count ?? 8)}
        />
      </div>

      {/* ── 4. Gap cards ── */}
      {gaps.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-vendoroo-main">
            {gaps.length} Operational Gap{gaps.length !== 1 ? "s" : ""} Identified
          </h2>
          <div className="mt-4 space-y-3">
            {gaps.map((gap, i) => (
              <div key={i} className="rounded-xl border border-vendoroo-border bg-vendoroo-surface px-5 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`size-2 shrink-0 rounded-full ${
                      gap.severity === "High Priority" ? "bg-rose-500" : "bg-amber-500"
                    }`} />
                    <span className="text-sm font-medium text-vendoroo-text">{gap.title}</span>
                  </div>
                  <span className={`rounded-md px-2 py-0.5 text-[10px] font-semibold ${
                    gap.severity === "High Priority"
                      ? "bg-rose-50 text-rose-700"
                      : "bg-amber-50 text-amber-700"
                  }`}>
                    {gap.severity}
                  </span>
                </div>
                {gap.detail && (
                  <p className="mt-2 text-xs leading-relaxed text-vendoroo-muted">
                    {gap.detail}
                  </p>
                )}
                <div className="mt-3 flex items-center gap-2 rounded-lg bg-vendoroo-light/60 px-3 py-2">
                  <svg className="size-3.5 shrink-0 text-vendoroo-muted" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                  <span className="text-[11px] text-vendoroo-muted">
                    Remediation plan available in your full report
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── 5. Staffing insight ── */}
      {data.summary?.staff_count != null && data.summary?.door_count != null && (
        <div className="rounded-xl border border-vendoroo-border bg-vendoroo-surface px-5 py-5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-vendoroo-main">
            Staffing Analysis
          </h3>
          {(() => {
            const doorsPerStaff = Math.round((data.summary?.door_count ?? 0) / Math.max(1, data.summary?.staff_count ?? 1));
            const benchmark = data.summary?.operational_model === "tech" ? 120 : 175;
            const staffRole = (data.summary?.staff_label ?? "coordinators").slice(0, -1);
            return (
              <>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-2xl font-bold tabular-nums text-vendoroo-text">
                    {doorsPerStaff}
                  </span>
                  <span className="text-sm text-vendoroo-muted">doors per {staffRole}</span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-vendoroo-muted">
                  {doorsPerStaff > benchmark * 1.15
                    ? `Industry benchmark is ${benchmark} doors per ${staffRole}. Your team is managing significantly more — that pressure shows up in response times and open work order rates.`
                    : doorsPerStaff < benchmark * 0.85
                    ? `Industry benchmark is ${benchmark} doors per ${staffRole}. You have capacity to grow your portfolio without adding headcount.`
                    : `You're tracking with the industry benchmark of ${benchmark} doors per ${staffRole}.`}
                </p>
              </>
            );
          })()}
        </div>
      )}

      {/* ── 6. Cost per door comparison — only shown when user entered actual cost ── */}
      {data.summary?.cost_source === "based on your input" && data.summary?.current_cost_per_door != null && (
        <div className="rounded-xl border border-vendoroo-border bg-vendoroo-surface px-5 py-5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-vendoroo-main">
            Coordination Cost Analysis
          </h3>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold tabular-nums text-vendoroo-text">
              ${(data.summary.current_cost_per_door as number).toFixed(2)}
            </span>
            <span className="text-sm text-vendoroo-muted">per door / month</span>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-vendoroo-muted">
            {`Your ${data.summary.staff_count ?? ""} ${data.summary.staff_label ?? "staff"} cost ~$${((data.summary.annual_cost_per_staff ?? 0) as number).toLocaleString()}/year each, which works out to $${(data.summary.current_cost_per_door as number).toFixed(2)} per door per month. Vendoroo starts at $3/door/month.`}
          </p>
        </div>
      )}

      {/* ── 7. Repeat units table (top 3) ── */}
      {repeatUnits.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-vendoroo-main">
            Units with Highest WO Volume
          </h2>
          <div className="mt-4 overflow-hidden rounded-xl border border-vendoroo-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#1a1a2e] text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
                  <th className="px-4 py-3 w-16">WOs</th>
                  <th className="px-4 py-3">Unit Address</th>
                  <th className="px-4 py-3">Top Trades</th>
                  <th className="px-4 py-3 w-24">Span</th>
                </tr>
              </thead>
              <tbody>
                {repeatUnits.slice(0, 3).map(([address, info], i) => (
                  <tr key={i} className={i % 2 === 0 ? "bg-vendoroo-surface" : "bg-vendoroo-light/30"}>
                    <td className="px-4 py-3 text-lg font-bold tabular-nums text-rose-500">
                      {(info as { wo_count?: number }).wo_count}
                    </td>
                    <td className="px-4 py-3 text-xs text-vendoroo-smoke">{address}</td>
                    <td className="px-4 py-3 text-xs text-vendoroo-muted">
                      {((info as { primary_trades?: string[] }).primary_trades ?? []).join(", ") || "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-vendoroo-muted">
                      {(info as { span_days?: number }).span_days ? `${(info as { span_days?: number }).span_days} days` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {repeatUnits.length > 3 && (
              <div className="border-t border-vendoroo-border bg-vendoroo-light/50 px-4 py-2">
                <p className="text-[10px] text-vendoroo-muted">
                  + {repeatUnits.length - 3} more units in your full report
                </p>
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── 7. Locked report CTA ── */}
      <div className="overflow-hidden rounded-2xl border border-vendoroo-border bg-gradient-to-b from-vendoroo-surface to-vendoroo-light p-6 sm:p-8">
        <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-vendoroo-main/10">
          <svg className="size-6 text-vendoroo-main" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-vendoroo-text">
          Your full report is ready
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-vendoroo-muted">
          We&apos;ve prepared a comprehensive analysis with specific remediation plans for each gap.
          Book a call and your advisor will walk you through the findings.
        </p>
        <ul className="mt-4 space-y-2">
          {[
            "Detailed remediation plan for each gap",
            "Document analysis (lease & PMA review)",
            "Projected operational impact with Vendoroo",
            "Work order analysis and trade distribution",
            "Your recommended path and AI adoption program",
          ].map((item, i) => (
            <li key={i} className="flex items-center gap-2 text-xs text-vendoroo-smoke">
              <svg className="size-3.5 shrink-0 text-vendoroo-main" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              {item}
            </li>
          ))}
        </ul>
        <a
          href="https://vendoroo.ai/contact"
          target="_blank"
          rel="noopener noreferrer"
          className="mt-6 inline-flex w-full items-center justify-center rounded-full bg-vendoroo-main px-8 py-4 text-sm font-semibold uppercase tracking-wider text-white shadow-lg transition-colors hover:bg-vendoroo-main/90"
        >
          Book a call to access your full report
        </a>
      </div>
    </div>
  );
}
