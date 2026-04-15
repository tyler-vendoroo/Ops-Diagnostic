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
                We already know what&apos;s wrong
              </span>
              <span className="mt-2 block text-[2rem] sm:text-5xl md:text-[3.25rem]">
                with your maintenance operation.
              </span>
            </h1>

            <p className="mx-auto mt-8 max-w-2xl text-pretty text-base leading-relaxed text-vendoroo-muted sm:text-lg">
              Answer 5 questions. In under two minutes we&apos;ll show you your
              vendor gaps, policy blind spots, and how you compare to the
              property managers already running AI-powered maintenance.
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
              <div className="grid gap-6 p-6 sm:grid-cols-[1fr_1.2fr] sm:gap-8">
                <div className="flex flex-col items-center justify-center">
                  <div className="relative size-28">
                    <svg viewBox="0 0 100 100" className="size-full -rotate-90">
                      <circle
                        cx="50"
                        cy="50"
                        r="42"
                        fill="none"
                        stroke="#e1e3e4"
                        strokeWidth="10"
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r="42"
                        fill="none"
                        stroke="#039cac"
                        strokeWidth="10"
                        strokeDasharray="175 264"
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-2xl font-semibold tabular-nums text-vendoroo-text">
                        54
                      </span>
                      <span className="text-[10px] font-medium uppercase text-vendoroo-muted">
                        /100
                      </span>
                    </div>
                  </div>
                  <p className="mt-3 text-center text-xs font-semibold text-vendoroo-main-dark">
                    Engage
                  </p>
                </div>
                <div className="space-y-3">
                  <div className="h-2 w-full rounded-full bg-vendoroo-border">
                    <div className="h-2 w-[62%] rounded-full bg-vendoroo-main" />
                  </div>
                  <div className="h-2 w-full rounded-full bg-vendoroo-border">
                    <div className="h-2 w-[45%] rounded-full bg-vendoroo-warn" />
                  </div>
                  <div className="h-2 w-full rounded-full bg-vendoroo-border">
                    <div className="h-2 w-[78%] rounded-full bg-vendoroo-success" />
                  </div>
                  <p className="pt-2 text-xs leading-relaxed text-vendoroo-muted">
                    Illustrative preview — your report reflects your real inputs.
                  </p>
                </div>
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
              Every property manager has blind spots.
              <br />
              Most just don&apos;t know where to look.
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
