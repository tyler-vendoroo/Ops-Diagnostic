import Link from "next/link";
import { Suspense } from "react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  BarChart3,
  ClipboardList,
  FileStack,
} from "lucide-react";

import { LandingRefTracker } from "./landing-ref-tracker";

const howSteps = [
  {
    n: "Step 1",
    title: "Tell us about your operation",
    body: "5 steps covering your portfolio, vendors, policies, and goals.",
    icon: ClipboardList,
  },
  {
    n: "Step 2",
    title: "We run the diagnostics",
    body: "Benchmarked against AI-managed portfolios.",
    icon: BarChart3,
  },
  {
    n: "Step 3",
    title: "Get your prescription",
    body: "Gaps, projections, and a recommended plan.",
    icon: FileStack,
  },
] as const;

/** Static marketing preview — mirrors results layout; no API or interactivity. */
function DiagnosticReportPreviewMockup() {
  return (
    <div className="mx-auto mt-12 max-w-2xl overflow-hidden rounded-xl border border-vendoroo-border bg-vendoroo-surface shadow-lg">
      <div className="border-b border-vendoroo-border bg-vendoroo-light/80 px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-vendoroo-muted">
        SAMPLE PREVIEW — VENDOROO OPS DIAGNOSTIC
      </div>

      <div className="px-4 py-5 sm:px-6 sm:py-6">
        {/* Section 1: Score header */}
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center">
          <div className="relative shrink-0 size-[100px]">
            <svg
              viewBox="0 0 100 100"
              className="size-full -rotate-90"
              aria-hidden
            >
              <circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                className="stroke-vendoroo-border"
                strokeWidth="8"
              />
              <circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                className="stroke-[#fdbb00]"
                strokeWidth="8"
                strokeDasharray="142.5 264"
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-semibold tabular-nums leading-none text-vendoroo-text">
                54
              </span>
              <span className="mt-0.5 text-xs font-medium text-vendoroo-muted">
                /100
              </span>
            </div>
          </div>
          <div className="w-full text-center sm:flex-1 sm:text-left">
            <p className="text-xs font-medium uppercase tracking-wide text-vendoroo-muted">
              Operations score
            </p>
            <p className="mt-1 flex items-baseline gap-1 text-3xl font-semibold tabular-nums text-vendoroo-text">
              <span>54</span>
              <span className="text-lg font-normal text-vendoroo-muted">/100</span>
            </p>
            <span className="mt-3 inline-block rounded-full bg-vendoroo-main px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white">
              Direct
            </span>
            <p className="mt-2 text-sm leading-snug text-vendoroo-muted">
              Core operations run — tightening spend controls and SLAs will raise
              consistency.
            </p>
          </div>
        </div>

        <div className="my-6 border-t border-vendoroo-border" />

        {/* Section 2: Before → After */}
        <div className="rounded-xl bg-[#222] px-4 py-5 sm:px-5">
          <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6">
            <div className="flex flex-col items-center gap-2">
              <div className="relative size-[60px]">
                <svg
                  viewBox="0 0 100 100"
                  className="size-full -rotate-90"
                  aria-hidden
                >
                  <circle
                    cx="50"
                    cy="50"
                    r="42"
                    fill="none"
                    className="stroke-white/20"
                    strokeWidth="7"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="42"
                    fill="none"
                    className="stroke-[#fdbb00]"
                    strokeWidth="7"
                    strokeDasharray="142.5 264"
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-sm font-semibold tabular-nums text-white">
                    54
                  </span>
                </div>
              </div>
              <span className="text-xs text-vendoroo-muted">Current</span>
            </div>
            <span className="text-lg text-white/40" aria-hidden>
              →
            </span>
            <div className="flex flex-col items-center gap-2">
              <div className="relative size-[60px]">
                <svg
                  viewBox="0 0 100 100"
                  className="size-full -rotate-90"
                  aria-hidden
                >
                  <circle
                    cx="50"
                    cy="50"
                    r="42"
                    fill="none"
                    className="stroke-white/20"
                    strokeWidth="7"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="42"
                    fill="none"
                    className="stroke-[#039cac]"
                    strokeWidth="7"
                    strokeDasharray="206 264"
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-sm font-semibold tabular-nums text-white">
                    78
                  </span>
                </div>
              </div>
              <span className="text-xs font-medium text-[#FDBB00]">
                With Vendoroo
              </span>
            </div>
          </div>
        </div>

        <div className="my-6 border-t border-vendoroo-border" />

        {/* Section 3: Category breakdown */}
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 sm:flex-nowrap sm:gap-3">
            <span className="w-full shrink-0 text-xs text-vendoroo-smoke sm:w-40 sm:min-w-0">
              Response Efficiency
            </span>
            <span className="w-8 shrink-0 text-right text-xs font-semibold tabular-nums text-vendoroo-text sm:w-7">
              38
            </span>
            <div className="relative h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-vendoroo-border">
              <div className="absolute inset-y-0 left-0 w-[38%] rounded-full bg-rose-500" />
            </div>
            <span className="shrink-0 rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-medium text-rose-600">
              Not Ready
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 sm:flex-nowrap sm:gap-3">
            <span className="w-full shrink-0 text-xs text-vendoroo-smoke sm:w-40 sm:min-w-0">
              Vendor Coverage
            </span>
            <span className="w-8 shrink-0 text-right text-xs font-semibold tabular-nums text-vendoroo-text sm:w-7">
              58
            </span>
            <div className="relative h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-vendoroo-border">
              <div className="absolute inset-y-0 left-0 w-[58%] rounded-full bg-amber-500" />
            </div>
            <span className="shrink-0 rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">
              Needs Work
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 sm:flex-nowrap sm:gap-3">
            <span className="w-full shrink-0 text-xs text-vendoroo-smoke sm:w-40 sm:min-w-0">
              Policy Completeness
            </span>
            <span className="w-8 shrink-0 text-right text-xs font-semibold tabular-nums text-vendoroo-text sm:w-7">
              25
            </span>
            <div className="relative h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-vendoroo-border">
              <div className="absolute inset-y-0 left-0 w-[25%] rounded-full bg-rose-500" />
            </div>
            <span className="shrink-0 rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-medium text-rose-600">
              Not Ready
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 sm:flex-nowrap sm:gap-3">
            <span className="w-full shrink-0 text-xs text-vendoroo-smoke sm:w-40 sm:min-w-0">
              Scalability
            </span>
            <span className="w-8 shrink-0 text-right text-xs font-semibold tabular-nums text-vendoroo-text sm:w-7">
              74
            </span>
            <div className="relative h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-vendoroo-border">
              <div className="absolute inset-y-0 left-0 w-[74%] rounded-full bg-[#34ba49]" />
            </div>
            <span className="shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-vendoroo-success">
              Ready
            </span>
          </div>
          <p className="pt-1 text-xs text-vendoroo-muted">
            + 4 more categories in your report
          </p>
        </div>

        <div className="my-6 border-t border-vendoroo-border" />

        {/* Section 4: Key finding */}
        <div>
          <div className="rounded-lg border border-vendoroo-border border-l-4 border-l-amber-500 bg-vendoroo-surface px-4 py-3">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md bg-amber-50 text-amber-600">
                <AlertTriangle className="size-4" strokeWidth={2} aria-hidden />
              </div>
              <div className="min-w-0">
                <p className="font-medium text-vendoroo-text">Response Time Gap</p>
                <p className="mt-1 text-sm leading-relaxed text-vendoroo-muted">
                  Average first response of 8 hrs — Vendoroo&apos;s average is under
                  10 min.
                </p>
              </div>
            </div>
          </div>
          <p className="mt-2 text-xs text-vendoroo-muted">
            + 2-5 more findings based on your data
          </p>
        </div>
      </div>

      {/* Section 5: CTA teaser */}
      <div className="border-t border-vendoroo-border bg-vendoroo-light px-4 py-3 text-xs text-vendoroo-muted sm:px-6">
        Your report includes: gap analysis · impact projections · tier
        recommendation · downloadable PDF
      </div>

      <p className="border-t border-vendoroo-border px-4 py-3 text-center text-[11px] text-vendoroo-muted/80 sm:px-6">
        Sample data — your report reflects your real inputs.
      </p>
    </div>
  );
}

export default function Home() {
  return (
    <>
      <Suspense fallback={null}>
        <LandingRefTracker />
      </Suspense>

      <div className="flex flex-1 flex-col">
        {/* Hero */}
        <section className="relative isolate overflow-hidden bg-vendoroo-surface">
          <div
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_120%_80%_at_50%_-40%,rgba(3,156,172,0.14),transparent_55%)]"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute -right-24 -top-24 size-[min(100vw,28rem)] rounded-full bg-[radial-gradient(circle_at_center,rgba(179,225,230,0.5),transparent_68%)] blur-2xl"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.3] [background-image:linear-gradient(to_right,#e1e3e4_1px,transparent_1px),linear-gradient(to_bottom,#e1e3e4_1px,transparent_1px)] [background-size:28px_28px] [mask-image:radial-gradient(ellipse_85%_55%_at_50%_35%,#000_50%,transparent_100%)]"
            aria-hidden
          />

          <div className="relative mx-auto max-w-4xl px-4 pb-10 pt-14 text-center sm:px-6 sm:pb-14 sm:pt-20">
            <div className="inline-flex items-center gap-2 rounded-full border border-vendoroo-border bg-vendoroo-surface/90 px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-vendoroo-main-dark shadow-sm backdrop-blur-sm">
              <span aria-hidden>🩺</span>
              <span>NARPM Broker-Owner 2026 · Complimentary Diagnostic</span>
            </div>

            <h1 className="mt-8 text-balance font-normal leading-[1.05] tracking-[-0.05em] text-vendoroo-text">
              <span className="block text-[2rem] sm:text-5xl md:text-[3.25rem]">
                Every operation has a score.
              </span>
              <span className="mt-2 block text-[2rem] sm:text-5xl md:text-[3.25rem]">
                What&apos;s yours?
              </span>
            </h1>

            <p className="mx-auto mt-8 max-w-2xl text-pretty text-base leading-relaxed text-vendoroo-muted sm:text-lg">
              5 steps. Under two minutes. We&apos;ll show you how your operation
              compares to property managers already running AI-powered
              maintenance.
            </p>

            <div className="mt-10 flex flex-col items-center">
              <Link
                href="/diagnostic"
                className={cn(
                  buttonVariants({
                    size: "lg",
                    className:
                      "h-14 min-w-[280px] rounded-full px-12 text-sm font-semibold uppercase tracking-[-0.02em] shadow-lg shadow-vendoroo-text/10",
                  })
                )}
              >
                Start your diagnostic
              </Link>
              <a
                href="/sample-report.pdf"
                target="_blank"
                rel="noopener noreferrer"
                className="mt-4 inline-block text-sm font-medium text-vendoroo-main transition-colors hover:text-vendoroo-main-dark"
              >
                See a sample report →
              </a>
            </div>
          </div>

          {/* Social proof — single strip, no cards */}
          <div className="border-y border-vendoroo-border/80 bg-vendoroo-light/90 py-4">
            <p className="mx-auto max-w-5xl px-4 text-center text-xs font-medium leading-relaxed text-vendoroo-smoke sm:text-sm">
              <span>12,000+ work orders analyzed</span>
              <span className="mx-2 text-vendoroo-border sm:mx-3" aria-hidden>
                ·
              </span>
              <span>200+ portfolios scored</span>
              <span className="mx-2 text-vendoroo-border sm:mx-3" aria-hidden>
                ·
              </span>
              <span>Avg. score: 54/100</span>
            </p>
          </div>

          <div className="border-b border-vendoroo-main/15 bg-vendoroo-tint/15 py-3">
            <p className="mx-auto max-w-5xl px-4 text-center text-xs font-medium text-vendoroo-main-dark sm:text-sm">
              Qualifying companies at NARPM Broker-Owner eligible for a 90-day
              free trial.{" "}
              <Link
                href="/diagnostic"
                className="font-semibold underline underline-offset-2 hover:text-vendoroo-main"
              >
                Complete your diagnostic to find out →
              </Link>
            </p>
          </div>
        </section>

        {/* How it works */}
        <section className="border-b border-vendoroo-border bg-vendoroo-page py-12 sm:py-16">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <h2 className="text-center text-2xl font-normal tracking-[-0.04em] text-vendoroo-text sm:text-3xl">
              How it works
            </h2>
            <div className="mt-12 grid gap-10 md:grid-cols-3 md:gap-8">
              {howSteps.map(({ n, title, body, icon: Icon }) => (
                <div key={title} className="text-center md:text-left">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-vendoroo-main">
                    {n}
                  </p>
                  <div className="mt-4 flex justify-center md:justify-start">
                    <span className="inline-flex size-11 items-center justify-center rounded-full bg-vendoroo-tint/60 text-vendoroo-main-dark ring-1 ring-vendoroo-main/15">
                      <Icon className="size-5" strokeWidth={1.75} aria-hidden />
                    </span>
                  </div>
                  <h3 className="mt-4 text-lg font-semibold tracking-tight text-vendoroo-text">
                    {title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-vendoroo-muted">
                    {body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Two paths */}
        <section className="bg-vendoroo-surface py-12 sm:py-16">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <h2 className="text-center text-2xl font-normal tracking-[-0.04em] text-vendoroo-text sm:text-3xl">
              Choose your depth
            </h2>
            <div className="mt-12 grid gap-6 md:grid-cols-2 md:gap-8">
              <div className="relative flex flex-col rounded-2xl border-2 border-vendoroo-main bg-vendoroo-surface p-8 shadow-md ring-2 ring-vendoroo-main/10">
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-vendoroo-main px-4 py-1 text-[10px] font-bold uppercase tracking-widest text-white">
                  Most popular
                </span>
                <h3 className="text-lg font-bold uppercase tracking-wide text-vendoroo-text">
                  Quick diagnostic
                </h3>
                <p className="mt-4 text-sm leading-relaxed text-vendoroo-muted">
                  Survey-based. Estimated benchmarks in under 2 minutes.
                </p>
                <Link
                  href="/diagnostic/quick"
                  className={cn(
                    buttonVariants({
                      className:
                        "mt-auto w-full rounded-full py-6 text-sm font-semibold uppercase tracking-[-0.02em] md:mt-8",
                    })
                  )}
                >
                  Start quick diagnostic
                </Link>
              </div>

              <div className="flex flex-col rounded-2xl border border-vendoroo-border bg-vendoroo-page/50 p-8 shadow-sm">
                <h3 className="text-lg font-bold uppercase tracking-wide text-vendoroo-text">
                  Full diagnostic
                </h3>
                <p className="mt-4 text-sm leading-relaxed text-vendoroo-muted">
                  Upload your PMS data. Data-grounded analysis in under 5
                  minutes.
                </p>
                <Link
                  href="/diagnostic/full"
                  className={cn(
                    buttonVariants({
                      variant: "outline",
                      className:
                        "mt-auto w-full rounded-full border-vendoroo-border py-6 text-sm font-semibold uppercase tracking-[-0.02em] text-vendoroo-text hover:bg-vendoroo-light md:mt-8",
                    })
                  )}
                >
                  Start full diagnostic
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* What you'll get */}
        <section className="border-t border-vendoroo-border bg-vendoroo-light/60 py-10 sm:py-14">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <h2 className="text-center text-2xl font-normal tracking-[-0.04em] text-vendoroo-text sm:text-3xl">
              What you&apos;ll get
            </h2>

            <DiagnosticReportPreviewMockup />
          </div>
        </section>

        {/* Final CTA */}
        <section className="bg-vendoroo-surface py-16 sm:py-20">
          <div className="mx-auto max-w-2xl px-4 text-center sm:px-6">
            <p className="text-xl font-normal leading-snug tracking-[-0.03em] text-vendoroo-text sm:text-2xl">
              Every operation has a number. The best operators already know theirs.
            </p>
            <p className="mt-4 text-sm font-medium text-vendoroo-main">
              Qualifying companies eligible for a 90-day free trial.
            </p>
            <Link
              href="/diagnostic"
              className={cn(
                buttonVariants({
                  size: "lg",
                  className:
                    "mt-10 inline-flex h-14 min-w-[280px] rounded-full px-12 text-sm font-semibold uppercase tracking-[-0.02em]",
                })
              )}
            >
              Start your diagnostic
            </Link>
          </div>
        </section>
      </div>
    </>
  );
}
