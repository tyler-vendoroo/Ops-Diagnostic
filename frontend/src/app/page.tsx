import Link from "next/link";
import { Suspense } from "react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  BarChart3,
  ClipboardList,
  FileStack,
  Pill,
  Search,
} from "lucide-react";

import { LandingRefTracker } from "./landing-ref-tracker";

const howSteps = [
  {
    n: "Step 1",
    title: "Tell us about your operation",
    body: "5 questions about your portfolio, vendors, policies, and goals. Takes 2 minutes.",
    icon: ClipboardList,
  },
  {
    n: "Step 2",
    title: "We run the diagnostics",
    body: "Our scoring engine compares you against benchmarks from thousands of work orders.",
    icon: BarChart3,
  },
  {
    n: "Step 3",
    title: "Get your prescription",
    body: "A personalized report with your gaps, projected improvements, and a recommended plan.",
    icon: FileStack,
  },
] as const;

const reportBullets = [
  {
    icon: BarChart3,
    text: "Your operations score — benchmarked against property managers already using AI coordination",
  },
  {
    icon: Search,
    text: "Key findings — the 3–4 things about your operation we can see from your data",
  },
  {
    icon: ClipboardList,
    text: "Gap analysis — exactly what needs to change before AI can run your maintenance",
  },
  {
    icon: Pill,
    text: "Your prescription — which Vendoroo plan fits your goals and portfolio",
  },
] as const;

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
              <span>Vendoroo · AI Diagnostics</span>
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
              Answer 5 questions. In under two minutes we&apos;ll show you how
              your vendors, policies, and response times compare to the property
              managers already running AI-powered maintenance.
            </p>

            <div className="mt-10">
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
        </section>

        {/* How it works */}
        <section className="border-b border-vendoroo-border bg-vendoroo-page py-16 sm:py-20">
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
        <section className="bg-vendoroo-surface py-16 sm:py-20">
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
                <ul className="mt-6 flex flex-col gap-3 text-sm text-vendoroo-smoke">
                  <li>🩺 5 survey questions</li>
                  <li>⏱ Under 2 minutes</li>
                  <li>📄 Estimated benchmarks</li>
                </ul>
                <p className="mt-6 text-sm leading-relaxed text-vendoroo-muted">
                  Best for: a fast read on where you stand and what to
                  prioritize.
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
                <ul className="mt-6 flex flex-col gap-3 text-sm text-vendoroo-smoke">
                  <li>📊 Upload your PMS data</li>
                  <li>⏱ Under 5 minutes</li>
                  <li>📄 Data-backed benchmarks</li>
                </ul>
                <p className="mt-6 text-sm leading-relaxed text-vendoroo-muted">
                  Best for: a precise diagnosis from your actual work order
                  history, policies, and vendor data.
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
        <section className="border-t border-vendoroo-border bg-vendoroo-light/60 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <h2 className="text-center text-2xl font-normal tracking-[-0.04em] text-vendoroo-text sm:text-3xl">
              What&apos;s in your diagnostic report
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-center text-sm leading-relaxed text-vendoroo-muted sm:text-base">
              Same structure as the sample report from our events—score,
              benchmarks, gaps, and a clear next step.
            </p>

            {/* Report mockup */}
            <div className="mx-auto mt-12 max-w-2xl overflow-hidden rounded-xl border border-vendoroo-border bg-white shadow-lg">
              <div className="border-b border-vendoroo-border bg-vendoroo-light/80 px-4 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-vendoroo-muted">
                Sample preview — Vendoroo ops diagnostic
              </div>
              <div className="p-5 sm:p-6 space-y-5">

                {/* Score + tier */}
                <div className="flex items-center gap-5">
                  <div className="relative shrink-0 size-20">
                    <svg viewBox="0 0 100 100" className="size-full -rotate-90">
                      <circle cx="50" cy="50" r="42" fill="none" stroke="#e1e3e4" strokeWidth="10" />
                      <circle cx="50" cy="50" r="42" fill="none" stroke="#fdbb00" strokeWidth="10"
                        strokeDasharray="145 264" strokeLinecap="round" />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-xl font-semibold tabular-nums text-vendoroo-text">54</span>
                      <span className="text-[9px] font-medium text-vendoroo-muted">/100</span>
                    </div>
                  </div>
                  <div>
                    <span className="inline-block rounded-full bg-vendoroo-main px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">Direct</span>
                    <p className="mt-1 text-xs text-vendoroo-muted leading-relaxed">Core operations run — tightening spend controls and SLAs will raise consistency.</p>
                  </div>
                </div>

                {/* Category bars */}
                <div className="space-y-2.5">
                  {[
                    { name: "Response Efficiency", score: 38, fill: "bg-rose-500", pill: "text-rose-700 bg-rose-50", tier: "Not Ready" },
                    { name: "Vendor Coverage",     score: 58, fill: "bg-amber-500", pill: "text-amber-700 bg-amber-50", tier: "Needs Work" },
                    { name: "Policy Completeness", score: 25, fill: "bg-rose-500", pill: "text-rose-700 bg-rose-50", tier: "Not Ready" },
                    { name: "Scalability Ops",     score: 74, fill: "bg-[#34ba49]", pill: "text-emerald-700 bg-emerald-50", tier: "Ready" },
                  ].map((cat) => (
                    <div key={cat.name} className="flex items-center gap-2">
                      <span className="w-36 shrink-0 text-[11px] text-vendoroo-smoke">{cat.name}</span>
                      <span className="w-6 shrink-0 text-right text-[11px] font-semibold tabular-nums text-vendoroo-text">{cat.score}</span>
                      <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-vendoroo-border">
                        <div className={`absolute inset-y-0 left-0 rounded-full ${cat.fill}`} style={{ width: `${cat.score}%` }} />
                      </div>
                      <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${cat.pill}`}>{cat.tier}</span>
                    </div>
                  ))}
                </div>

                {/* Sample finding */}
                <div className="rounded-lg border border-vendoroo-border bg-vendoroo-surface px-4 py-3">
                  <div className="flex items-start gap-2.5">
                    <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md bg-rose-50 text-rose-600">
                      <svg className="size-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" /></svg>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-vendoroo-text">Response Time Gap</p>
                      <p className="mt-0.5 text-[11px] text-vendoroo-muted leading-relaxed">Average first response of 8 hrs — Vendoroo's average is under 10 min.</p>
                    </div>
                  </div>
                </div>

                <p className="text-[11px] text-vendoroo-muted/70 text-center">
                  Sample data — your report reflects your real inputs.
                </p>
              </div>
            </div>

            <div className="mx-auto mt-12 grid max-w-3xl gap-6 sm:grid-cols-2">
              {reportBullets.map(({ icon: Icon, text }) => (
                <div key={text} className="flex gap-3 text-left">
                  <span className="mt-0.5 shrink-0 text-vendoroo-main">
                    <Icon className="size-5" strokeWidth={1.75} aria-hidden />
                  </span>
                  <p className="text-sm leading-relaxed text-vendoroo-smoke">
                    {text}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="bg-vendoroo-surface py-16 sm:py-20">
          <div className="mx-auto max-w-2xl px-4 text-center sm:px-6">
            <p className="text-xl font-normal leading-snug tracking-[-0.03em] text-vendoroo-text sm:text-2xl">
              Every operation has a number. The best operators already know theirs.
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
