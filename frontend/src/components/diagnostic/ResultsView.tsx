"use client";

import * as React from "react";
import Link from "next/link";

import type {
  DiagnosticStatusResponse,
  DiagnosticTier,
  GapFinding,
  KeyFinding,
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

const tierCopy: Record<
  DiagnosticTier,
  { label: string; line: string }
> = {
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

function SeverityDot({ severity }: { severity?: GapFinding["severity"] }) {
  const cls =
    severity === "high"
      ? "bg-rose-500"
      : severity === "medium"
        ? "bg-amber-500"
        : "bg-vendoroo-muted";
  return (
    <span
      className={`mt-1.5 size-2 shrink-0 rounded-full ${cls}`}
      title={severity ? `${severity} severity` : "Severity not specified"}
    />
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

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-12 bg-vendoroo-page px-4 py-12 sm:px-6">
      <header className="flex flex-col items-center gap-8 text-center sm:flex-row sm:items-start sm:justify-between sm:text-left">
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center">
          <ScoreRing score={score} />
          <div>
            <p className="text-xs font-medium uppercase tracking-widest text-vendoroo-muted">
              Operations score
            </p>
            <p
              className={`mt-1 text-4xl font-semibold tabular-nums ${scoreColor(score)}`}
            >
              {score}
              <span className="text-lg font-normal text-vendoroo-muted">/100</span>
            </p>
          </div>
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
              Detailed findings will appear here once the assessment enriches this
              record.
            </p>
          )}
        </div>
      </section>

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
                  <p className="mt-1 text-sm text-vendoroo-muted">{g.description}</p>
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

function ScoreRing({ score }: { score: number }) {
  const size = 140;
  const stroke = 10;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;
  const strokeColor = ringColor(score);

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
        stroke={strokeColor}
        strokeWidth={stroke}
        strokeDasharray={c}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
    </svg>
  );
}
