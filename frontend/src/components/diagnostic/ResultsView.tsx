"use client";

import * as React from "react";
import Link from "next/link";

import type {
  DiagnosticStatusResponse,
  DiagnosticSummary,
  DiagnosticTier,
  GapFinding,
  ImpactRow,
  KeyFinding,
  CategoryScoreEntry,
  CostEstimates,
} from "@/lib/types";
import { getDiagnostic, getDiagnosticPdfUrl } from "@/lib/api";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Activity,
  ArrowRight,
  ClipboardList,
  Download,
  Gauge,
  ShieldCheck,
} from "lucide-react";

const RESULTS_SOURCE_KEY = "vendoroo_diagnostic_results_source";

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

const TIER_DETAILS: Record<
  DiagnosticTier,
  { subtitle: string; price: string; features: string[] }
> = {
  engage: {
    subtitle: "AI Communication Desk",
    price: "$3",
    features: [
      "AI phone answering & triage",
      "Smart troubleshooting before dispatch",
      "Work order creation & tracking",
      "Resident communication management",
    ],
  },
  direct: {
    subtitle: "AI Maintenance Coordination",
    price: "$6",
    features: [
      "Everything in Engage",
      "Vendor dispatch & scheduling",
      "NTE enforcement & approval workflows",
      "Owner communication & updates",
    ],
  },
  command: {
    subtitle: "Full AI Operations",
    price: "$8.50",
    features: [
      "Everything in Direct",
      "Predictive maintenance scheduling",
      "Budget forecasting & cost analysis",
      "Portfolio-wide reporting & insights",
    ],
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

function scoreColor(score: number) {
  if (score >= 70) return "text-vendoroo-success";
  if (score >= 50) return "text-amber-600";
  return "text-rose-600";
}

function ringColor(score: number) {
  if (score >= 70) return "#34ba49";
  if (score >= 50) return "#fdbb00";
  return "#f43f5e";
}

const findingIcons = [Activity, ShieldCheck, Gauge, ClipboardList];

function SeverityDot({ severity }: { severity?: string }) {
  const s = (severity ?? "").toLowerCase();
  const cls = s.includes("high")
    ? "bg-rose-500"
    : s.includes("medium")
      ? "bg-amber-500"
      : "bg-vendoroo-muted";
  return (
    <span
      className={`mt-1.5 size-2 shrink-0 rounded-full ${cls}`}
      title={severity ? `${severity} severity` : "Severity not specified"}
    />
  );
}

function ScoreRing({
  score,
  color,
  size = 100,
}: {
  score: number;
  color: string;
  size?: number;
}) {
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="shrink-0"
      aria-hidden
    >
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke="#e1e3e4"
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
      <text
        x={size / 2}
        y={size / 2 + 6}
        textAnchor="middle"
        fontSize="18"
        fontWeight="600"
        fill="currentColor"
        className="fill-vendoroo-text"
      >
        {score}
      </text>
    </svg>
  );
}

function CategoryBar({
  name,
  score,
  tier,
  tierCss,
}: {
  name: string;
  score: number;
  tier: string;
  tierCss: string;
}) {
  const fillColor =
    tierCss === "ready"
      ? "bg-[#34ba49]"
      : tierCss === "needs-work"
        ? "bg-amber-500"
        : "bg-rose-500";
  const pillColor =
    tierCss === "ready"
      ? "text-emerald-700 bg-emerald-50"
      : tierCss === "needs-work"
        ? "text-amber-700 bg-amber-50"
        : "text-rose-700 bg-rose-50";
  return (
    <div className="flex items-center gap-3">
      <span className="w-44 shrink-0 text-sm text-vendoroo-text">{name}</span>
      <span className="w-8 shrink-0 text-right text-sm font-semibold tabular-nums text-vendoroo-text">
        {score}
      </span>
      <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-vendoroo-border">
        <div
          className={`absolute inset-y-0 left-0 rounded-full ${fillColor} transition-all duration-700 ease-out`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span
        className={`shrink-0 rounded-md px-2 py-0.5 text-xs font-medium ${pillColor}`}
      >
        {tier}
      </span>
    </div>
  );
}

function toTitleCase(key: string) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function ImpactTable({ rows }: { rows: ImpactRow[] }) {
  if (!rows.length) return null;
  const notes = rows
    .map((r, i) => (r.note ? { idx: i + 1, note: r.note } : null))
    .filter(Boolean) as { idx: number; note: string }[];

  return (
    <div className="overflow-x-auto rounded-xl border border-vendoroo-border">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="bg-vendoroo-surface border-b border-vendoroo-border">
            <th className="px-4 py-3 text-left font-medium text-vendoroo-muted">
              Metric
            </th>
            <th className="px-4 py-3 text-left font-medium text-vendoroo-muted">
              Current
            </th>
            <th className="px-4 py-3 text-left font-medium text-vendoroo-muted">
              Projected
            </th>
            <th className="px-4 py-3 text-left font-medium text-vendoroo-muted">
              Improvement
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-vendoroo-border bg-vendoroo-surface">
          {rows.map((row, i) => (
            <tr key={`${row.metric}-${i}`}>
              <td className="px-4 py-3 font-medium text-vendoroo-text">
                {row.metric}
                {notes.find((n) => n.idx === i + 1) ? (
                  <sup className="ml-0.5 text-vendoroo-muted">
                    {notes.findIndex((n) => n.idx === i + 1) + 1}
                  </sup>
                ) : null}
              </td>
              <td
                className={`px-4 py-3 tabular-nums ${
                  row.current_is_bad !== false
                    ? "text-rose-600"
                    : "text-vendoroo-text"
                }`}
              >
                {row.current_value}
              </td>
              <td className="px-4 py-3 tabular-nums text-[#34ba49] font-medium">
                {row.projected_value}
              </td>
              <td className="px-4 py-3">
                {row.improvement &&
                row.improvement !== "Already meeting benchmark" ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                    ↑ {row.improvement}
                  </span>
                ) : row.improvement === "Already meeting benchmark" ? (
                  <span className="text-xs text-vendoroo-muted">
                    Already meeting benchmark
                  </span>
                ) : (
                  <span className="text-xs text-vendoroo-muted">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {notes.length > 0 && (
        <div className="border-t border-vendoroo-border bg-vendoroo-surface px-4 py-3 space-y-1">
          {notes.map((n, i) => (
            <p key={i} className="text-xs text-vendoroo-muted">
              <sup>{i + 1}</sup> {n.note}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

function TierRecommendation({
  tier,
  costs,
  doorCount,
}: {
  tier: DiagnosticTier;
  costs: CostEstimates | undefined;
  doorCount: number;
}) {
  const details = TIER_DETAILS[tier];
  const monthly = costs?.recommended_cost ?? null;
  const annual = monthly !== null ? Math.round(monthly * 12) : null;

  return (
    <div className="rounded-xl border-2 border-vendoroo-main bg-vendoroo-surface p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <span className="inline-block rounded-full bg-vendoroo-main px-3 py-0.5 text-xs font-semibold uppercase tracking-wider text-white">
            Recommended
          </span>
          <h3 className="mt-2 text-xl font-semibold text-vendoroo-text capitalize">
            {tier}
          </h3>
          <p className="text-sm text-vendoroo-muted">{details.subtitle}</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-vendoroo-text tabular-nums">
            {details.price}
            <span className="text-sm font-normal text-vendoroo-muted">
              /door/mo
            </span>
          </p>
          {monthly !== null && (
            <p className="text-sm text-vendoroo-muted tabular-nums">
              ~${monthly.toLocaleString()}/mo
              {annual !== null ? ` · $${annual.toLocaleString()}/yr` : ""}
            </p>
          )}
          <p className="text-xs text-vendoroo-muted mt-0.5">
            {doorCount} doors
          </p>
        </div>
      </div>
      <ul className="mt-4 space-y-2">
        {details.features.map((feat) => (
          <li key={feat} className="flex items-center gap-2 text-sm text-vendoroo-text">
            <span className="text-[#34ba49] font-bold">✓</span>
            {feat}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ResultsView({ id }: { id: string }) {
  const [data, setData] = React.useState<DiagnosticStatusResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [fromQuick, setFromQuick] = React.useState(false);

  React.useEffect(() => {
    if (typeof sessionStorage !== "undefined") {
      setFromQuick(sessionStorage.getItem(RESULTS_SOURCE_KEY) === "quick");
    }
  }, []);

  const load = React.useCallback(async () => {
    try {
      const res = await getDiagnostic(id);
      setData(res);
      if (res.status === "failed") {
        setError("This diagnostic could not be completed. Please start again.");
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

  const score = scoreFromDiagnostic(data);
  const tier: DiagnosticTier = data.tier ?? "engage";
  const tierInfo = tierCopy[tier];
  const findings = (data.key_findings ?? []).slice(0, 4);
  const gaps = data.gaps ?? [];
  const showPdf = Boolean(data.pdf_url);
  const pdfHref = getDiagnosticPdfUrl(id);
  const summary: DiagnosticSummary | undefined = data.summary;

  const projectedScore = summary ? clampScore(summary.projected_score) : null;
  const currentRingColor = ringColor(score);
  const projectedRingColor = "#039cac";

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-12 bg-vendoroo-page px-4 py-12 sm:px-6">

      {/* Section 1 — Score header */}
      <header className="flex flex-col items-center gap-6 text-center sm:flex-row sm:items-start sm:justify-between sm:text-left">
        <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center">
          {summary && projectedScore !== null ? (
            <div className="flex items-center gap-3">
              <div className="flex flex-col items-center gap-1">
                <ScoreRing score={score} color={currentRingColor} size={100} />
                <p className="text-xs text-vendoroo-muted">Current</p>
              </div>
              <ArrowRight className="size-5 shrink-0 text-vendoroo-muted" />
              <div className="flex flex-col items-center gap-1">
                <ScoreRing score={projectedScore} color={projectedRingColor} size={100} />
                <p className="text-xs text-vendoroo-muted">With Vendoroo</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-4">
              <ScoreRing score={score} color={currentRingColor} size={100} />
              <div>
                <p className="text-xs font-medium uppercase tracking-widest text-vendoroo-muted">
                  Operations score
                </p>
                <p
                  className={`mt-1 text-4xl font-semibold tabular-nums ${scoreColor(score)}`}
                >
                  {score}
                  <span className="text-lg font-normal text-vendoroo-muted">
                    /100
                  </span>
                </p>
              </div>
            </div>
          )}
        </div>
        <div className="w-full max-w-sm rounded-xl border border-vendoroo-border bg-vendoroo-surface px-5 py-4 text-left shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wider text-vendoroo-main">
            {tierInfo.label}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-vendoroo-smoke">
            {tierInfo.line}
          </p>
        </div>
      </header>

      {/* Section 2 — Category breakdown */}
      <section aria-labelledby="categories-heading">
        <h2
          id="categories-heading"
          className="text-base font-medium tracking-tight text-vendoroo-text"
        >
          Category breakdown
        </h2>
        <div className="mt-4 space-y-3">
          {summary?.category_scores?.length ? (
            summary.category_scores.map((cat: CategoryScoreEntry) => (
              <CategoryBar
                key={cat.key}
                name={cat.name}
                score={cat.score}
                tier={cat.tier}
                tierCss={cat.tier_css}
              />
            ))
          ) : data.scores && Object.keys(data.scores).length > 0 ? (
            Object.entries(data.scores).map(([key, val]) => (
              <div key={key} className="flex items-center gap-3">
                <span className="w-44 shrink-0 text-sm text-vendoroo-text">
                  {toTitleCase(key)}
                </span>
                <span className="w-8 shrink-0 text-right text-sm font-semibold tabular-nums text-vendoroo-text">
                  {val}
                </span>
                <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-vendoroo-border">
                  <div
                    className="absolute inset-y-0 left-0 rounded-full bg-vendoroo-main transition-all duration-700 ease-out"
                    style={{ width: `${val}%` }}
                  />
                </div>
              </div>
            ))
          ) : null}
        </div>
      </section>

      {/* Section 3 — Key findings */}
      <section aria-labelledby="findings-heading">
        <h2
          id="findings-heading"
          className="text-base font-medium tracking-tight text-vendoroo-text"
        >
          Key findings
        </h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {findings.length ? (
            findings.map((f: KeyFinding, i: number) => {
              const Icon = findingIcons[i % findingIcons.length];
              return (
                <Card
                  key={`${f.title}-${i}`}
                  className="border-vendoroo-border bg-vendoroo-surface shadow-sm ring-0"
                >
                  <CardHeader className="flex flex-row items-start gap-3 space-y-0">
                    <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-vendoroo-tint/80 text-vendoroo-main-dark">
                      <Icon className="size-4" aria-hidden />
                    </div>
                    <div>
                      <CardTitle className="text-base text-vendoroo-text">
                        {f.title}
                      </CardTitle>
                      {f.category ? (
                        <CardDescription className="text-xs uppercase tracking-wide text-vendoroo-muted">
                          {f.category}
                        </CardDescription>
                      ) : null}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-relaxed text-vendoroo-muted">
                      {f.description}
                    </p>
                  </CardContent>
                </Card>
              );
            })
          ) : (
            <p className="text-sm text-vendoroo-muted">
              Detailed findings will appear here once the assessment enriches
              this record.
            </p>
          )}
        </div>
      </section>

      {/* Section 4 — Projected impact */}
      {summary?.impact_rows?.length ? (
        <section aria-labelledby="impact-heading">
          <h2
            id="impact-heading"
            className="text-base font-medium tracking-tight text-vendoroo-text"
          >
            Projected impact
          </h2>
          <div className="mt-4">
            <ImpactTable rows={summary.impact_rows} />
          </div>
        </section>
      ) : null}

      {/* Section 5 — Gaps to address */}
      <section aria-labelledby="gaps-heading">
        <h2
          id="gaps-heading"
          className="text-base font-medium tracking-tight text-vendoroo-text"
        >
          Gaps to address
        </h2>
        <ul className="mt-4 space-y-3">
          {gaps.length ? (
            gaps.map((g: GapFinding, i: number) => (
              <li
                key={`${g.title}-${i}`}
                className="flex gap-3 rounded-lg border border-vendoroo-border bg-vendoroo-surface px-4 py-3 shadow-sm"
              >
                <SeverityDot severity={g.severity} />
                <div>
                  <p className="font-medium text-vendoroo-text">{g.title}</p>
                  <p className="mt-1 text-sm text-vendoroo-muted">
                    {g.description || g.detail}
                  </p>
                  {g.recommendation ? (
                    <p className="mt-1.5 text-xs text-vendoroo-main">
                      {g.recommendation}
                    </p>
                  ) : null}
                </div>
              </li>
            ))
          ) : (
            <li className="text-sm text-vendoroo-muted">
              No structural gaps were flagged in this pass.
            </li>
          )}
        </ul>
      </section>

      {/* Section 6 — Recommended plan */}
      <section aria-labelledby="plan-heading">
        <h2
          id="plan-heading"
          className="text-base font-medium tracking-tight text-vendoroo-text"
        >
          Recommended plan
        </h2>
        <div className="mt-4">
          <TierRecommendation
            tier={tier}
            costs={summary?.cost_estimates}
            doorCount={summary?.door_count ?? 0}
          />
        </div>
      </section>

      {/* Section 7 — CTAs */}
      <section className="flex flex-col gap-3 border-t border-vendoroo-border pt-10 sm:flex-row sm:flex-wrap">
        {showPdf ? (
          <a
            href={pdfHref}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              buttonVariants({
                className:
                  "inline-flex gap-2 rounded-full px-8 py-4 text-sm font-medium uppercase tracking-[-0.02em]",
              })
            )}
          >
            <Download className="size-4" />
            Download full report
          </a>
        ) : null}
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
        {fromQuick ? (
          <Link
            href="/diagnostic/full"
            className={cn(
              buttonVariants({
                variant: "secondary",
                className:
                  "inline-flex gap-2 rounded-full bg-vendoroo-light px-8 py-4 text-sm font-medium uppercase tracking-[-0.02em] text-vendoroo-text hover:bg-vendoroo-border/60",
              })
            )}
          >
            Get a full data-driven analysis
            <ArrowRight className="size-4" />
          </Link>
        ) : null}
      </section>
    </div>
  );
}
